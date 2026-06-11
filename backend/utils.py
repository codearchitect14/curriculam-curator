"""Utility functions for duration parsing, filtering, dedup, and CLI output."""

import json
import logging
import re
from pathlib import Path

import isodate
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from models import (
    Curriculum,
    CurriculumEntry,
    DroppedVideo,
    Persona,
    PipelineDrop,
    VideoCandidate,
)

logger = logging.getLogger(__name__)
console = Console()

_STOPWORDS: frozenset[str] = frozenset(
    {
        "for",
        "the",
        "and",
        "with",
        "from",
        "this",
        "that",
        "are",
        "was",
        "have",
        "has",
        "not",
        "but",
        "you",
        "your",
    }
)


def parse_iso8601_duration(iso: str) -> float:
    """Parse ISO 8601 duration string to minutes."""
    duration = isodate.parse_duration(iso)
    return duration.total_seconds() / 60.0


def deduplicate_candidates(
    candidates: list[VideoCandidate],
) -> list[VideoCandidate]:
    """Deduplicate candidates by video_id, keeping highest view_count."""
    best: dict[str, VideoCandidate] = {}
    for candidate in candidates:
        existing = best.get(candidate.video_id)
        if existing is None or candidate.view_count > existing.view_count:
            best[candidate.video_id] = candidate
    return list(best.values())


_TOPIC_SYNONYMS: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript"],
    "react": ["reactjs", "react.js"],
    "python": ["py"],
    "rest": ["restful", "rest api", "rest apis"],
    "http": ["https", "http endpoints", "web requests"],
    "git": ["github", "version control"],
    "npm": ["node package manager", "node.js packages"],
    "json": ["json data", "json format"],
    "machine learning": ["ml", "machine-learning"],
    "neural networks": ["neural nets", "deep learning basics"],
    "numpy": ["np", "numerical python"],
    "pandas": ["pd", "dataframes"],
    "sklearn": ["scikit-learn", "scikit learn"],
}


def _expand_topic_tokens(topic: str) -> set[str]:
    """Expand a known topic into tokens and synonym phrases for matching."""
    phrase = topic.lower().strip()
    tokens = set(re.findall(r"\w+", phrase))
    expanded = set(tokens)
    expanded.add(phrase)
    for token in list(tokens):
        for synonym in _TOPIC_SYNONYMS.get(token, []):
            expanded.add(synonym.lower())
            expanded.update(re.findall(r"\w+", synonym.lower()))
    for key, synonyms in _TOPIC_SYNONYMS.items():
        if key in phrase or phrase in key:
            expanded.add(key)
            expanded.update(synonyms)
    return expanded


def semantic_known_overlap_score(text: str, known_topics: list[str]) -> float:
    """Return 0.0-1.0 semantic overlap between text and known topics."""
    if not known_topics:
        return 0.0
    text_lower = text.lower()
    text_tokens = set(re.findall(r"\w+", text_lower))
    scores: list[float] = []
    for topic in known_topics:
        topic_lower = topic.lower().strip()
        if not topic_lower:
            continue
        if topic_lower in text_lower:
            scores.append(1.0)
            continue
        expanded = _expand_topic_tokens(topic)
        if any(
            len(term) >= 4
            and term not in _STOPWORDS
            and term in text_lower
            for term in expanded
        ):
            scores.append(0.85)
            continue
        union = text_tokens | expanded
        if union:
            scores.append(len(text_tokens & expanded) / len(union))
    return max(scores) if scores else 0.0


def _count_known_matches(text: str, known_topics: list[str]) -> int:
    """Count how many known topics appear in text (case-insensitive)."""
    text_lower = text.lower()
    matches = 0
    for topic in known_topics:
        topic_lower = topic.lower().strip()
        if not topic_lower:
            continue
        if topic_lower in text_lower:
            matches += 1
    return matches


def _known_topic_shares_domain_with_unknown(
    known_topic: str, unknown_topics: list[str]
) -> bool:
    """Return True if a known topic shares tokens with any unknown topic."""
    known_tokens = set(re.findall(r"\w+", known_topic.lower()))
    for unknown in unknown_topics:
        unknown_tokens = set(re.findall(r"\w+", unknown.lower()))
        if known_tokens & unknown_tokens:
            return True
    return False


def filter_known_topic_overlap(
    candidates: list[VideoCandidate],
    known_topics: list[str],
    unknown_topics: list[str] | None = None,
) -> list[VideoCandidate]:
    """Remove videos whose title/description strongly match known topics."""
    unknown = unknown_topics or []
    filtered: list[VideoCandidate] = []
    for candidate in candidates:
        combined = f"{candidate.title} {candidate.description}"
        matches = _count_known_matches(combined, known_topics)
        long_phrase_match = any(
            len(t.strip()) >= 8 and t.lower() in combined.lower()
            for t in known_topics
        )
        strong_semantic = any(
            len(t.strip()) >= 8
            and not _known_topic_shares_domain_with_unknown(t, unknown)
            and semantic_known_overlap_score(combined, [t]) >= 0.55
            for t in known_topics
        )
        if (
            matches >= 2
            or (matches >= 1 and long_phrase_match)
            or strong_semantic
        ):
            logger.debug(
                "Filtered known-topic overlap for video %s "
                "(keyword=%d, semantic=%s)",
                candidate.video_id,
                matches,
                strong_semantic,
            )
            continue
        filtered.append(candidate)
    return filtered


def enforce_budget(curriculum: Curriculum) -> Curriculum:
    """Trim ranked entries to fit budget; move overflow videos to dropped."""
    budget = curriculum.budget_minutes
    if curriculum.total_minutes <= budget:
        return curriculum

    entries = sorted(curriculum.entries, key=lambda e: e.rank)
    kept: list[CurriculumEntry] = []
    dropped = list(curriculum.dropped)
    pipeline_drops = list(curriculum.pipeline_drops)
    total = 0.0

    for entry in entries:
        if total + entry.video.duration_minutes <= budget:
            kept.append(entry)
            total += entry.video.duration_minutes
        else:
            reason = (
                "Removed by budget enforcement: "
                f"adding this video would exceed {budget} min budget"
            )
            dropped.append(
                DroppedVideo(
                    video=entry.video,
                    drop_reason=reason,
                    drop_stage="budget",
                )
            )
            pipeline_drops.append(
                PipelineDrop(stage="budget", video=entry.video, reason=reason)
            )

    if not kept:
        raise RuntimeError(
            f"No videos fit within {budget} min budget after enforcement"
        )

    reranked = [
        entry.model_copy(update={"rank": i + 1}) for i, entry in enumerate(kept)
    ]
    trimmed = len(entries) - len(reranked)
    budget_note = (
        f" Budget enforcement removed {trimmed} video(s) "
        f"to fit {budget} min."
    )

    return curriculum.model_copy(
        update={
            "entries": reranked,
            "dropped": dropped,
            "pipeline_drops": pipeline_drops,
            "total_minutes": total,
            "agent_notes": curriculum.agent_notes + budget_note,
        }
    )


def cap_by_view_count(
    candidates: list[VideoCandidate],
    max_n: int,
) -> list[VideoCandidate]:
    """Keep top max_n candidates by view_count."""
    sorted_candidates = sorted(
        candidates, key=lambda c: c.view_count, reverse=True
    )
    return sorted_candidates[:max_n]


def cap_by_view_count_with_drops(
    candidates: list[VideoCandidate],
    max_n: int,
) -> tuple[list[VideoCandidate], list[PipelineDrop]]:
    """Keep top max_n candidates; return pipeline drops for the rest."""
    sorted_candidates = sorted(
        candidates, key=lambda c: c.view_count, reverse=True
    )
    kept = sorted_candidates[:max_n]
    dropped: list[PipelineDrop] = []
    for candidate in sorted_candidates[max_n:]:
        dropped.append(
            PipelineDrop(
                stage="view_cap",
                video=candidate,
                reason=(
                    f"Below top {max_n} by view count "
                    f"({candidate.view_count:,} views)"
                ),
            )
        )
    return kept, dropped


def filter_duration_with_drops(
    candidates: list[VideoCandidate],
    min_minutes: float,
    max_minutes: float,
) -> tuple[list[VideoCandidate], list[PipelineDrop]]:
    """Filter by duration bounds; return removed candidates as pipeline drops."""
    kept: list[VideoCandidate] = []
    dropped: list[PipelineDrop] = []
    for candidate in candidates:
        duration = candidate.duration_minutes
        if min_minutes <= duration <= max_minutes:
            kept.append(candidate)
            continue
        if duration < min_minutes:
            reason = f"Too short ({duration:.1f} min < {min_minutes} min)"
        else:
            reason = f"Too long ({duration:.1f} min > {max_minutes} min)"
        dropped.append(
            PipelineDrop(stage="duration", video=candidate, reason=reason)
        )
    return kept, dropped


def filter_known_topic_overlap_with_drops(
    candidates: list[VideoCandidate],
    known_topics: list[str],
    unknown_topics: list[str] | None = None,
) -> tuple[list[VideoCandidate], list[PipelineDrop]]:
    """Filter known-topic overlap; return removed candidates as pipeline drops."""
    unknown = unknown_topics or []
    kept: list[VideoCandidate] = []
    dropped: list[PipelineDrop] = []
    for candidate in candidates:
        combined = f"{candidate.title} {candidate.description}"
        matches = _count_known_matches(combined, known_topics)
        long_phrase_match = any(
            len(t.strip()) >= 8 and t.lower() in combined.lower()
            for t in known_topics
        )
        strong_semantic = any(
            len(t.strip()) >= 8
            and not _known_topic_shares_domain_with_unknown(t, unknown)
            and semantic_known_overlap_score(combined, [t]) >= 0.55
            for t in known_topics
        )
        if (
            matches >= 2
            or (matches >= 1 and long_phrase_match)
            or strong_semantic
        ):
            dropped.append(
                PipelineDrop(
                    stage="known_topic",
                    video=candidate,
                    reason=(
                        "Pre-filter: strong overlap with known topics "
                        f"({matches} keyword matches)"
                    ),
                )
            )
            continue
        kept.append(candidate)
    return kept, dropped


def topic_covered_semantically(text: str, topic: str) -> bool:
    """Return True if text semantically covers a topic at threshold 0.5."""
    return semantic_known_overlap_score(text, [topic]) >= 0.5


def summarize_pipeline_drops(
    pipeline_drops: list[PipelineDrop],
) -> dict[str, int]:
    """Count pipeline drops by stage."""
    counts: dict[str, int] = {
        "duration": 0,
        "known_topic": 0,
        "view_cap": 0,
        "curator": 0,
        "budget": 0,
    }
    for drop in pipeline_drops:
        counts[drop.stage] = counts.get(drop.stage, 0) + 1
    return counts


def jaccard_similarity(a: list[str], b: list[str]) -> float:
    """Compute Jaccard similarity between two topic lists."""
    set_a = {x.lower().strip() for x in a if x.strip()}
    set_b = {x.lower().strip() for x in b if x.strip()}
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def load_persona_from_file(path: str) -> Persona:
    """Load and validate a Persona from a JSON file."""
    file_path = Path(path)
    if not file_path.is_absolute():
        from config import ROOT_DIR

        file_path = ROOT_DIR / path
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    return Persona.model_validate(data)


def strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM response text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def print_curriculum(curriculum: Curriculum) -> None:
    """Print a human-readable curriculum summary using Rich."""
    console.print(
        Panel(
            f"[bold]{curriculum.goal}[/bold]\n"
            f"Persona: {curriculum.persona_id}\n"
            f"Time: {curriculum.total_minutes:.1f} / "
            f"{curriculum.budget_minutes} min",
            title="Curriculum",
        )
    )

    table = Table(title="Selected Videos")
    table.add_column("Rank", style="cyan")
    table.add_column("Title")
    table.add_column("Channel")
    table.add_column("Duration", justify="right")
    table.add_column("Confidence", justify="right")

    for entry in curriculum.entries:
        table.add_row(
            str(entry.rank),
            entry.video.title,
            entry.video.channel,
            f"{entry.video.duration_minutes:.1f} min",
            f"{entry.confidence:.2f}",
        )
    console.print(table)

    if curriculum.dropped:
        dropped_table = Table(title="Dropped Videos")
        dropped_table.add_column("Title")
        dropped_table.add_column("Reason")
        for dropped in curriculum.dropped:
            dropped_table.add_row(
                dropped.video.title,
                dropped.drop_reason,
            )
        console.print(dropped_table)

    console.print(Panel(curriculum.agent_notes, title="Agent Notes"))
