"""Unit tests for programmatic evaluator metrics (no LLM)."""

from models import Curriculum, CurriculumEntry, Persona, UserContext, VideoCandidate
from evaluator import CurriculumEvaluator


def _entry(
    rank: int,
    duration: float,
    topics: list[str],
    description: str = "desc",
) -> CurriculumEntry:
    """Build a minimal curriculum entry for tests."""
    return CurriculumEntry(
        rank=rank,
        video=VideoCandidate(
            video_id=f"v{rank}",
            title=f"Video {rank}",
            channel="Ch",
            duration_minutes=duration,
            description=description,
            url=f"https://youtube.com/watch?v=v{rank}",
            view_count=100,
            published_at="2024-01-01T00:00:00Z",
        ),
        inclusion_reason="reason",
        confidence=0.8,
        covers_topics=topics,
    )


def _curriculum(
    total: float,
    budget: int,
    entries: list[CurriculumEntry],
) -> Curriculum:
    """Build a minimal curriculum for tests."""
    return Curriculum(
        persona_id="test",
        goal="goal",
        total_minutes=total,
        budget_minutes=budget,
        entries=entries,
        dropped=[],
        agent_notes="",
    )


class TestProgrammaticEvaluatorMetrics:
    """Tests for non-LLM scoring methods."""

    def setup_method(self) -> None:
        """Create a fresh evaluator per test."""
        self.evaluator = CurriculumEvaluator()

    def test_budget_adherence_within_budget(self) -> None:
        """Total within budget should score 1.0."""
        c = _curriculum(90.0, 100, [_entry(1, 90.0, [])])
        assert self.evaluator._score_budget_adherence(c) == 1.0

    def test_budget_adherence_slightly_over(self) -> None:
        """Total up to 110% of budget should score 0.5."""
        c = _curriculum(105.0, 100, [_entry(1, 105.0, [])])
        assert self.evaluator._score_budget_adherence(c) == 0.5

    def test_budget_adherence_well_over(self) -> None:
        """Total well over budget should score 0.0."""
        c = _curriculum(130.0, 100, [_entry(1, 130.0, [])])
        assert self.evaluator._score_budget_adherence(c) == 0.0

    def test_decision_redundancy_single_entry(self) -> None:
        """Single entry curricula should not be penalized for redundancy."""
        persona = Persona(
            persona_id="p",
            goal="g",
            time_budget_minutes=60,
            user_context=UserContext(
                background="bg",
                known=[],
                unknown=["React"],
                constraints="",
            ),
        )
        entries = [_entry(1, 10.0, ["React"], description="learn React hooks")]
        score = self.evaluator._score_decision_redundancy(
            persona, entries, [["React"]]
        )
        assert score == 1.0

    def test_zero_contribution_entries_detects_redundant_video(self) -> None:
        """Entry duplicating another's unique topic coverage should be redundant."""
        persona = Persona(
            persona_id="p",
            goal="g",
            time_budget_minutes=60,
            user_context=UserContext(
                background="bg",
                known=[],
                unknown=["React", "Vite"],
                constraints="",
            ),
        )
        entries = [
            _entry(1, 10.0, ["React"], description="React tutorial for beginners"),
            _entry(2, 10.0, ["React"], description="another React tutorial"),
            _entry(3, 10.0, ["Vite"], description="Vite tooling setup guide"),
        ]
        llm_map = [["React"], ["React"], ["Vite"]]
        redundant = self.evaluator._zero_contribution_entries(
            persona, entries, llm_map
        )
        redundant_ids = {entry.video.video_id for entry in redundant}
        assert redundant_ids == {"v1", "v2"}
        assert "v3" not in redundant_ids

    def test_deduplication_flags_similar_pairs(self) -> None:
        """High Jaccard overlap between entries should lower dedup score."""
        entries = [
            _entry(1, 10.0, ["react", "hooks", "state"]),
            _entry(2, 10.0, ["react", "hooks", "state", "effects"]),
        ]
        score = self.evaluator._score_deduplication(entries)
        assert score < 1.0

    def test_curriculum_fit_weights_redistribute_without_audience(self) -> None:
        """Audience weight should redistribute when signal is unavailable."""
        weights = self.evaluator._curriculum_fit_weights(None)
        assert weights["audience_signal"] == 0.0
        assert abs(sum(weights.values()) - 1.0) < 0.001

    def test_parse_unknown_topic_map(self) -> None:
        """Unknown topic map parser should preserve persona topic strings."""
        text = "1: React, hooks\n2: NONE"
        result = self.evaluator._parse_unknown_topic_map(
            text, 2, ["React", "hooks", "Vite"]
        )
        assert result[0] == ["React", "hooks"]
        assert result[1] == []
