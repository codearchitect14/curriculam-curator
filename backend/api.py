"""FastAPI application with curriculum building routes."""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from agent import CurriculumAgent
import config
from config import CORS_ORIGINS, TEST_SET_DIR, validate_api_keys
from youtube_client import YouTubeClient
from curator import CurriculumCurator
from evaluator import CurriculumEvaluator
from models import (
    AgentProgressEvent,
    Curriculum,
    EvaluateRequest,
    EvalResult,
    FollowUpRequest,
    FollowUpResponse,
    Persona,
    TestPersonaItem,
)
from utils import load_persona_from_file

logger = logging.getLogger(__name__)

app = FastAPI(title="Curriculum Builder API")
executor = ThreadPoolExecutor(max_workers=4)

def _ensure_keys() -> None:
    """Validate API keys or raise HTTP 503."""
    try:
        validate_api_keys()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Return consistent error JSON for HTTP exceptions."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(ValidationError)
async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Return consistent error JSON for validation errors."""
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Return consistent error JSON for unhandled exceptions."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_persona_from_id(persona_id: str) -> Persona:
    """Load a persona from test_set by persona_id."""
    path = TEST_SET_DIR / f"{persona_id}.json"
    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Persona not found: {persona_id}"
        )
    return load_persona_from_file(str(path))


def _resolve_persona(
    persona: str | None, persona_id: str | None
) -> Persona:
    """Resolve persona from query params."""
    if persona_id:
        return _load_persona_from_id(persona_id)
    if persona:
        try:
            decoded = unquote(persona)
            data = json.loads(decoded)
            return Persona.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid persona JSON: {e}"
            ) from e
    raise HTTPException(
        status_code=400,
        detail="Provide persona (JSON) or persona_id query parameter",
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Lightweight health check for frontend connectivity."""
    return {"status": "ok"}


@app.post("/api/curriculum", response_model=Curriculum)
async def create_curriculum(persona: Persona) -> Curriculum:
    """Run the full agent synchronously and return the curriculum."""
    _ensure_keys()
    loop = asyncio.get_event_loop()
    agent = CurriculumAgent(persona)

    def _run() -> Curriculum:
        return agent.run()

    return await loop.run_in_executor(executor, _run)


@app.get("/api/curriculum/stream")
async def stream_curriculum(
    request: Request,
    persona: str | None = Query(None),
    persona_id: str | None = Query(None),
) -> StreamingResponse:
    """Stream agent progress via SSE, then return the final curriculum."""
    _ensure_keys()
    resolved = _resolve_persona(persona, persona_id)

    async def event_generator() -> Any:
        """Generate SSE progress, result, or error events."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_event_loop()
        agent = CurriculumAgent(resolved)
        result_holder: list[Curriculum] = []
        error_holder: list[str] = []

        def progress_callback(event: AgentProgressEvent) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "progress", "payload": event.model_dump()},
            )

        def _run_agent() -> None:
            try:
                curriculum = agent.run(progress_callback=progress_callback)
                result_holder.append(curriculum)
                loop.call_soon_threadsafe(
                    queue.put_nowait, {"type": "done"}
                )
            except Exception as e:
                logger.exception("Agent run failed: %s", e)
                error_holder.append(str(e))
                loop.call_soon_threadsafe(
                    queue.put_nowait, {"type": "error", "message": str(e)}
                )

        task = loop.run_in_executor(executor, _run_agent)

        while True:
            if await request.is_disconnected():
                logger.info("Client disconnected, stopping SSE stream")
                return

            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            if item["type"] == "progress":
                payload = json.dumps(item["payload"])
                yield f"event: progress\ndata: {payload}\n\n"
            elif item["type"] == "done":
                await task
                if result_holder:
                    result_json = json.dumps(
                        result_holder[0].model_dump()
                    )
                    yield f"event: result\ndata: {result_json}\n\n"
                break
            elif item["type"] == "error":
                await task
                err_json = json.dumps({"message": item["message"]})
                yield f"event: error\ndata: {err_json}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/followup", response_model=FollowUpResponse)
async def followup(request: FollowUpRequest) -> FollowUpResponse:
    """Answer a follow-up question about a curriculum."""
    _ensure_keys()
    loop = asyncio.get_event_loop()

    def _run() -> str:
        curator = CurriculumCurator(request.persona)
        return curator.answer_followup(request.curriculum, request.question)

    answer = await loop.run_in_executor(executor, _run)
    return FollowUpResponse(answer=answer)


@app.post("/api/evaluate", response_model=EvalResult)
async def evaluate(request: EvaluateRequest) -> EvalResult:
    """Evaluate a curriculum against a persona."""
    _ensure_keys()
    loop = asyncio.get_event_loop()

    def _run() -> EvalResult:
        youtube = YouTubeClient(config.YOUTUBE_API_KEY)
        evaluator = CurriculumEvaluator(youtube_client=youtube)
        return evaluator.evaluate(request.persona, request.curriculum)

    return await loop.run_in_executor(executor, _run)


@app.get("/api/test-personas", response_model=list[TestPersonaItem])
async def get_test_personas() -> list[TestPersonaItem]:
    """Return all test personas from test_set/."""
    items: list[TestPersonaItem] = []
    if not TEST_SET_DIR.exists():
        return items

    for path in sorted(TEST_SET_DIR.glob("*.json")):
        persona = load_persona_from_file(str(path))
        items.append(
            TestPersonaItem(
                filename=path.name,
                persona_id=persona.persona_id,
                persona=persona,
            )
        )
    return items
