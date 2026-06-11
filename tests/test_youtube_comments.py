"""Unit tests for YouTube comment fetching helpers."""

from youtube_client import YouTubeClient


def test_pre_filter_comments_drops_short_and_spam() -> None:
    """Comment pre-filter should remove short and URL-only comments."""
    raw = [
        "hi",
        "https://spam.example.com",
        "This tutorial finally helped me understand React hooks clearly.",
        "aaaaaaa",
    ]
    filtered = YouTubeClient._pre_filter_comments(raw)
    assert len(filtered) == 1
    assert "React hooks" in filtered[0]
