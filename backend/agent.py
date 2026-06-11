"""Core agent orchestration for curriculum building."""

import logging
from collections.abc import Callable

import config
from config import MAX_CANDIDATES, MAX_VIDEO_MINUTES, MIN_VIDEO_MINUTES
from curator import CurriculumCurator
from models import AgentProgressEvent, Curriculum, Persona, PipelineDrop
from utils import (
    cap_by_view_count_with_drops,
    deduplicate_candidates,
    enforce_budget,
    filter_duration_with_drops,
    filter_known_topic_overlap_with_drops,
)
from youtube_client import YouTubeClient

logger = logging.getLogger(__name__)


class CurriculumAgent:
    """Orchestrates YouTube search, filtering, and LLM curation."""

    def __init__(self, persona: Persona) -> None:
        """Initialize the agent with a learner persona."""
        self._persona = persona
        self._youtube = YouTubeClient(config.YOUTUBE_API_KEY)

    def _emit(
        self,
        callback: Callable[[AgentProgressEvent], None] | None,
        step: str,
        message: str,
        data: dict | None = None,
    ) -> None:
        """Emit a progress event via the optional callback."""
        if callback is not None:
            event = AgentProgressEvent(
                step=step,
                message=message,
                data=data or {},
            )
            callback(event)

    def run(
        self,
        progress_callback: Callable[[AgentProgressEvent], None] | None = None,
    ) -> Curriculum:
        """Run the full curriculum building pipeline."""
        pipeline_drops: list[PipelineDrop] = []

        self._emit(
            progress_callback,
            "searching_youtube",
            "Building search queries...",
        )

        queries = self._youtube.build_search_queries(self._persona)
        all_candidates = []

        for query in queries:
            logger.info("Searching YouTube: %s", query)
            results = self._youtube.search_videos(query)
            all_candidates.extend(results)

        raw_count = len(all_candidates)
        self._emit(
            progress_callback,
            "searching_youtube",
            f"Found {raw_count} raw candidates across {len(queries)} queries",
            {"candidates": raw_count, "queries": len(queries)},
        )

        candidates = deduplicate_candidates(all_candidates)

        candidates, duration_drops = filter_duration_with_drops(
            candidates, MIN_VIDEO_MINUTES, MAX_VIDEO_MINUTES
        )
        pipeline_drops.extend(duration_drops)

        candidates, known_drops = filter_known_topic_overlap_with_drops(
            candidates,
            self._persona.user_context.known,
            self._persona.user_context.unknown,
        )
        pipeline_drops.extend(known_drops)

        candidates, view_cap_drops = cap_by_view_count_with_drops(
            candidates, MAX_CANDIDATES
        )
        pipeline_drops.extend(view_cap_drops)

        filtered_count = len(candidates)
        self._emit(
            progress_callback,
            "filtering",
            f"Filtered to {filtered_count} candidates",
            {"candidates": filtered_count},
        )

        if not candidates:
            raise RuntimeError("No suitable videos found after filtering")

        self._emit(
            progress_callback,
            "curating",
            "Sending candidates to Claude for curation...",
            {"candidates": filtered_count},
        )

        curator = CurriculumCurator(self._persona)
        curriculum = enforce_budget(curator.curate(candidates))
        curriculum = curriculum.model_copy(
            update={
                "pipeline_drops": pipeline_drops + curriculum.pipeline_drops,
            }
        )

        self._emit(
            progress_callback,
            "done",
            f"Curriculum ready with {len(curriculum.entries)} videos",
            {"entries": len(curriculum.entries)},
        )

        return curriculum
