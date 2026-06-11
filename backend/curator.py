"""LLM-based curriculum curation via OpenRouter (Claude)."""

import json
import logging
from typing import Any

import httpx

import config
from config import MAX_TOKENS
from models import (
    Curriculum,
    CurriculumEntry,
    DroppedVideo,
    Persona,
    VideoCandidate,
)
from prompts import build_curation_prompt, build_followup_prompt
from utils import cap_by_view_count, strip_markdown_fences

logger = logging.getLogger(__name__)


def call_anthropic(prompt: str) -> tuple[str, int, int]:
    """Make a single LLM call via OpenRouter. Returns (text, input_tokens, output_tokens)."""
    config._reload_env()
    api_key = config.ANTHROPIC_API_KEY

    url = f"{config.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": config.OPENROUTER_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "Curriculum Builder",
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=180.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500]
        logger.error("OpenRouter API error %s: %s", e.response.status_code, detail)
        raise RuntimeError(
            f"OpenRouter API error {e.response.status_code}: {detail}"
        ) from e
    except httpx.RequestError as e:
        logger.error("OpenRouter request failed: %s", e)
        raise RuntimeError(f"OpenRouter request failed: {e}") from e

    data = response.json()

    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("OpenRouter returned no choices")

    message = choices[0].get("message", {})
    text = message.get("content", "")
    if not text:
        raise RuntimeError("OpenRouter returned empty content")

    usage = data.get("usage", {})
    input_tokens = int(usage.get("prompt_tokens", 0))
    output_tokens = int(usage.get("completion_tokens", 0))
    print(f"Anthropic tokens — input: {input_tokens}, output: {output_tokens}")

    return text, input_tokens, output_tokens


class CurriculumCurator:
    """Curates a personalized curriculum using Claude via OpenRouter."""

    def __init__(self, persona: Persona) -> None:
        """Initialize the curator with a learner persona."""
        self._persona = persona
        self.input_tokens: int = 0
        self.output_tokens: int = 0

    def curate(self, candidates: list[VideoCandidate]) -> Curriculum:
        """Curate a curriculum from video candidates using the LLM."""
        return self._curate_with_retry(candidates, retried=False)

    def _curate_with_retry(
        self,
        candidates: list[VideoCandidate],
        retried: bool,
    ) -> Curriculum:
        """Run curation with optional retry on JSON parse failure."""
        prompt = build_curation_prompt(self._persona, candidates)
        raw_text, in_tok, out_tok = call_anthropic(prompt)
        self.input_tokens += in_tok
        self.output_tokens += out_tok

        try:
            parsed = self._parse_curation_response(raw_text, candidates)
            return parsed
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM curation response: %s", raw_text)
            if retried:
                raise RuntimeError(
                    "Failed to parse curriculum from LLM after retry"
                ) from None
            top_20 = cap_by_view_count(candidates, 20)
            return self._curate_with_retry(top_20, retried=True)

    def _parse_curation_response(
        self,
        raw_text: str,
        candidates: list[VideoCandidate],
    ) -> Curriculum:
        """Parse LLM JSON response into a Curriculum model."""
        cleaned = strip_markdown_fences(raw_text)
        data: dict[str, Any] = json.loads(cleaned)

        lookup: dict[str, VideoCandidate] = {
            c.video_id: c for c in candidates
        }

        entries: list[CurriculumEntry] = []
        for item in data.get("entries", []):
            vid = item.get("video_id", "")
            if vid not in lookup:
                logger.warning("Skipping unknown video_id from LLM: %s", vid)
                continue
            entries.append(
                CurriculumEntry(
                    rank=item.get("rank", len(entries) + 1),
                    video=lookup[vid],
                    inclusion_reason=item.get("inclusion_reason", ""),
                    confidence=float(item.get("confidence", 0.5)),
                    covers_topics=item.get("covers_topics", []),
                )
            )

        if not entries:
            raise RuntimeError("LLM returned no valid curriculum entries")

        entries.sort(key=lambda e: e.rank)

        dropped: list[DroppedVideo] = []
        for item in data.get("dropped", []):
            vid = item.get("video_id", "")
            if vid not in lookup:
                continue
            dropped.append(
                DroppedVideo(
                    video=lookup[vid],
                    drop_reason=item.get("drop_reason", ""),
                )
            )

        total_minutes = sum(e.video.duration_minutes for e in entries)

        return Curriculum(
            persona_id=self._persona.persona_id,
            goal=self._persona.goal,
            total_minutes=total_minutes,
            budget_minutes=self._persona.time_budget_minutes,
            entries=entries,
            dropped=dropped,
            agent_notes=data.get("agent_notes", ""),
        )

    def answer_followup(self, curriculum: Curriculum, question: str) -> str:
        """Answer a follow-up question about the curriculum."""
        prompt = build_followup_prompt(curriculum, question, self._persona)
        text, in_tok, out_tok = call_anthropic(prompt)
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        return text.strip()
