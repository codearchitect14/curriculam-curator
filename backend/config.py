"""Configuration and constants loaded from environment variables."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
TEST_SET_DIR = ROOT_DIR / "test_set"
EVAL_RESULTS_DIR = ROOT_DIR / "eval_results"
YOUTUBE_CACHE_DIR = ROOT_DIR / ".youtube_cache"
FRONTEND_DIST_DIR = Path(
    os.environ.get("FRONTEND_DIST_DIR", ROOT_DIR / "frontend" / "dist")
)

def _reload_env() -> None:
    """Load or refresh API keys from the repo-root .env file."""
    load_dotenv(ROOT_DIR / ".env", override=True)


_reload_env()

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
YOUTUBE_API_KEY: str = os.environ.get("YOUTUBE_API_KEY", "")

MAX_SEARCH_RESULTS: int = 20
MAX_CANDIDATES: int = 40
# Claude via OpenRouter (OpenAI-compatible chat completions API)
OPENROUTER_BASE_URL: str = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL: str = os.environ.get(
    "OPENROUTER_MODEL", "anthropic/claude-sonnet-4"
)
MODEL_NAME: str = OPENROUTER_MODEL  # alias for eval cost docs / legacy refs
MAX_TOKENS: int = 4096
MIN_VIDEO_MINUTES: float = 3.0
MAX_VIDEO_MINUTES: float = 180.0
CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
YOUTUBE_CACHE_ENABLED: bool = (
    os.environ.get("YOUTUBE_CACHE_ENABLED", "true").lower() == "true"
)
COMMENT_FETCH_ENABLED: bool = (
    os.environ.get("COMMENT_FETCH_ENABLED", "true").lower() == "true"
)
AUDIENCE_SIGNAL_ENABLED: bool = (
    os.environ.get("AUDIENCE_SIGNAL_ENABLED", "true").lower() == "true"
)
MAX_COMMENTS_PER_VIDEO: int = int(os.environ.get("MAX_COMMENTS_PER_VIDEO", "50"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def validate_api_keys() -> None:
    """Raise RuntimeError if required API keys are missing."""
    global ANTHROPIC_API_KEY, YOUTUBE_API_KEY
    global OPENROUTER_BASE_URL, OPENROUTER_MODEL, MODEL_NAME
    _reload_env()
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
    OPENROUTER_BASE_URL = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    OPENROUTER_MODEL = os.environ.get(
        "OPENROUTER_MODEL", "anthropic/claude-sonnet-4"
    )
    MODEL_NAME = OPENROUTER_MODEL

    missing: list[str] = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not YOUTUBE_API_KEY:
        missing.append("YOUTUBE_API_KEY")
    if missing:
        raise RuntimeError(
            f"Missing API keys: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your keys."
        )

    if not (
        ANTHROPIC_API_KEY.startswith("sk-or-")
        or ANTHROPIC_API_KEY.startswith("sk-ant-")
    ):
        raise RuntimeError(
            "ANTHROPIC_API_KEY must be an OpenRouter key (sk-or-...) "
            "or a direct Anthropic key (sk-ant-...)."
        )
