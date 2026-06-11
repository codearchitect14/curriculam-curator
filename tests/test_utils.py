"""Unit tests for backend utility functions."""



from models import Curriculum, CurriculumEntry, DroppedVideo, VideoCandidate

from utils import (

    deduplicate_candidates,

    enforce_budget,

    filter_known_topic_overlap,

    jaccard_similarity,

    semantic_known_overlap_score,

)





def _video(

    video_id: str,

    title: str = "Title",

    description: str = "Description",

    duration: float = 10.0,

    views: int = 100,

) -> VideoCandidate:

    """Build a minimal VideoCandidate for tests."""

    return VideoCandidate(

        video_id=video_id,

        title=title,

        channel="Channel",

        duration_minutes=duration,

        description=description,

        url=f"https://www.youtube.com/watch?v={video_id}",

        view_count=views,

        published_at="2024-01-01T00:00:00Z",

    )





def test_deduplicate_candidates_keeps_highest_views() -> None:

    """Deduplication should retain the candidate with more views."""

    candidates = [

        _video("a", views=100),

        _video("a", views=500),

        _video("b", views=50),

    ]

    result = deduplicate_candidates(candidates)

    assert len(result) == 2

    by_id = {c.video_id: c for c in result}

    assert by_id["a"].view_count == 500





def test_filter_known_topic_overlap_keyword_match() -> None:

    """Videos with multiple known-topic keyword hits should be removed."""

    candidates = [

        _video("keep", title="Advanced React patterns"),

        _video(

            "drop",

            title="JavaScript fundamentals and HTTP REST tutorial",

            description="Covers JSON and Git basics",

        ),

    ]

    known = ["JavaScript fundamentals", "HTTP", "REST", "JSON", "Git"]

    result = filter_known_topic_overlap(candidates, known)

    assert len(result) == 1

    assert result[0].video_id == "keep"





def test_semantic_known_overlap_detects_synonyms() -> None:

    """Semantic scoring should catch synonym overlap beyond exact phrases."""

    score = semantic_known_overlap_score(

        "Learn ECMAScript and JS basics for web dev",

        ["JavaScript fundamentals"],

    )

    assert score >= 0.55





def test_jaccard_similarity() -> None:

    """Jaccard similarity should reflect topic list overlap."""

    assert jaccard_similarity(["react", "hooks"], ["react", "state"]) == 0.3333333333333333

    assert jaccard_similarity([], []) == 0.0

    assert jaccard_similarity(["a"], ["b"]) == 0.0





def test_enforce_budget_trims_overflow_entries() -> None:

    """Budget enforcement should drop lowest-priority overflow videos."""

    entries = [

        CurriculumEntry(

            rank=1,

            video=_video("a", duration=60.0),

            inclusion_reason="r1",

            confidence=0.9,

            covers_topics=["t1"],

        ),

        CurriculumEntry(

            rank=2,

            video=_video("b", duration=50.0),

            inclusion_reason="r2",

            confidence=0.8,

            covers_topics=["t2"],

        ),

        CurriculumEntry(

            rank=3,

            video=_video("c", duration=40.0),

            inclusion_reason="r3",

            confidence=0.7,

            covers_topics=["t3"],

        ),

    ]

    curriculum = Curriculum(

        persona_id="test",

        goal="goal",

        total_minutes=150.0,

        budget_minutes=100,

        entries=entries,

        dropped=[],

        agent_notes="notes",

    )

    result = enforce_budget(curriculum)

    assert result.total_minutes <= 100

    assert len(result.entries) == 2

    assert len(result.dropped) == 1

    assert "Budget enforcement" in result.agent_notes
    assert result.dropped[0].drop_stage == "budget"
    assert len(result.pipeline_drops) == 1
    assert result.pipeline_drops[0].stage == "budget"


