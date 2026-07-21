# Curriculum Builder

A full-stack AI agent that builds personalized YouTube learning curricula from learner personas. It searches YouTube, curates videos with Claude, streams live progress to a React UI, and evaluates curriculum quality.

## Setup & Run

### Docker (recommended)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2).

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and YOUTUBE_API_KEY in .env

docker compose up --build
```

- **Frontend (production static build):** [http://localhost:5173](http://localhost:5173) — React is compiled during the image build and served by Nginx.
- **Backend API (direct access / debugging):** [http://localhost:8002](http://localhost:8002)

The frontend container reverse-proxies `/api` to the backend, so the browser uses same-origin relative URLs. Nginx is configured for SSE streaming on `/api/curriculum/stream`.

Useful commands:

```bash
docker compose up --build -d    # detached
docker compose down             # stop and remove containers
docker compose down -v          # also remove the youtube_cache volume
docker compose logs -f backend  # tail backend logs
```

YouTube search cache is persisted in the `youtube_cache` Docker volume at `/app/.youtube_cache` inside the backend container.

### Backend (local development)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and YOUTUBE_API_KEY in .env

cd backend
uvicorn api:app --reload --port 8002
```

### Frontend (local development)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

For local dev with the backend in Docker, point the Vite proxy at the container:

```bash
# Windows PowerShell
$env:VITE_API_PROXY_TARGET="http://localhost:8002"; npm run dev

# macOS/Linux
VITE_API_PROXY_TARGET=http://localhost:8002 npm run dev
```

Default proxy target when unset: `http://localhost:8002`.

### CLI

```bash
python main.py --persona test_set/weekend_react_dev.json
python main.py --persona test_set/weekend_react_dev.json --ask "Why not video X?"
python main.py --persona test_set/weekend_react_dev.json --output results/output.json
```

### Run All Evals

```bash
python run_eval.py
```

## Design Decisions

### Keyword Pre-filter Before LLM

Before sending candidates to Claude, the agent filters videos by duration bounds and removes those whose titles/descriptions strongly overlap with known topics using case-insensitive keyword matching. This keeps LLM input smaller and reduces latency and API cost without sacrificing curation quality, since the LLM still makes the final selection.

### SSE Over WebSockets

Server-Sent Events were chosen for one-way progress streaming because the client only needs to receive updates while the agent runs. SSE works over standard HTTP, requires no extra protocol handling, and integrates cleanly with FastAPI's `StreamingResponse`. The final curriculum is delivered as a `result` event in the same stream.

### All Prompts Centralized in prompts.py

Every LLM prompt string lives in a single module to make prompt engineering auditable and prevent scattered magic strings. Curation, follow-up Q&A, and evaluation metrics each have dedicated builder functions. This separation also enforces the architecture boundary that no other module constructs prompt text.

### Executor Pattern for Non-blocking FastAPI

YouTube and Anthropic SDK calls are synchronous and would block the asyncio event loop. All blocking work runs in a `ThreadPoolExecutor` via `run_in_executor`, keeping the API responsive for concurrent requests. The SSE stream uses an `asyncio.Queue` bridge so sync agent callbacks can push progress events to the async generator.

### Pure SVG Radar Chart

The evaluation dashboard renders radar charts in pure SVG with no chart library dependencies. Curriculum fit and decision audit tiers are shown as grouped metric bars plus optional decision flags.

## Evaluation Methodology

Quality is scored with a **two-tier model** (see `backend/evaluator.py`):

- **Curriculum Fit (60%)** — budget adherence, semantic marginal coverage, known-topic avoidance, constraint adherence, and **audience signal** from YouTube comments (LLM interprets top comments per included video for persona fit).
- **Decision Audit (40%)** — inclusion reason quality, drop decision quality, counterfactual regret (top-3 dropped videos sampled), and decision redundancy.

**Programmatic metrics** (no LLM): budget, marginal coverage (semantic topic overlap + LLM topic tags), redundancy/dedup.

**LLM-as-judge metrics**: known-topic avoidance, constraints, inclusion/drop reasoning, counterfactual swaps, audience comment interpretation.

**Pipeline audit trail**: pre-filter drops (duration, known-topic, view cap) and budget trims are tracked in `pipeline_drops` and surfaced as decision flags (`budget_forced_drop`, `suggested_swap`, `weak_audience_signal`, etc.).

**Blind spots** (documented in `eval_notes`):
- Inclusion reasons and audience comments are metadata-only — not verified against watched video content.
- Known-topic pre-filter uses keyword/token heuristics that miss some semantic overlap.
- Audience comments reflect a biased sample of engaged viewers, not all learners.
- Counterfactual regret only samples top-3 dropped videos by view count.

Re-run `python run_eval.py` to regenerate scores with the new framework. Full JSON: `eval_results/eval_report.json`.

## Evaluation Results

*Re-run `python run_eval.py` after pulling latest changes — scores below are from the prior single-tier eval (2026-06-11).*

| Persona | Budget | Known Avoid | Constraints | Reason | Coverage | Overall |
|---------|--------|-------------|-------------|--------|----------|---------|
| weekend_react_dev | 1.00 | 1.00 | 0.80 | 0.77 | 1.00 | 0.92 |
| ml_beginner | 1.00 | 1.00 | 1.00 | 0.77 | 0.60 | 0.89 |
| senior_dev_devops | 1.00 | 1.00 | 1.00 | 0.83 | 0.67 | 0.92 |
| non_technical_pm | 1.00 | 1.00 | 1.00 | 0.68 | 0.50 | 0.86 |
| advanced_llm_engineer | 1.00 | 1.00 | 0.60 | 0.73 | 0.75 | 0.83 |
| time_constrained_designer | 1.00 | 1.00 | 1.00 | 0.82 | 0.75 | 0.93 |

## What I'd Do With More Time

1. **Embedding-based semantic filter** — Upgrade the current synonym/token semantic filter to embedding similarity for finer-grained known-topic detection.

2. **Streaming Claude tokens** — Stream partial LLM responses during curation so the UI can show reasoning in real time rather than waiting for the full JSON response.

3. **Persistent eval history database** — Store eval results over time in SQLite or Postgres to track quality trends across prompt iterations and model versions.

4. **Auth and rate limiting** — Add API key authentication and per-user rate limits before deploying publicly, protecting YouTube and Anthropic quotas from abuse.
