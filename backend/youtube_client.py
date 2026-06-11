"""YouTube Data API v3 client for video search and metadata."""



import hashlib

import json

import logging

from pathlib import Path

from typing import Any



from googleapiclient.discovery import build

from googleapiclient.errors import HttpError



import re

from config import (
    COMMENT_FETCH_ENABLED,
    MAX_COMMENTS_PER_VIDEO,
    MAX_SEARCH_RESULTS,
    YOUTUBE_API_KEY,
    YOUTUBE_CACHE_DIR,
    YOUTUBE_CACHE_ENABLED,
)

from models import CommentSample, Persona, VideoCandidate

from utils import parse_iso8601_duration



logger = logging.getLogger(__name__)





class YouTubeClient:

    """Client for searching YouTube and fetching video metadata."""



    def __init__(self, api_key: str) -> None:

        """Initialize the YouTube API client."""

        self._api_key = api_key

        self._youtube = build("youtube", "v3", developerKey=api_key)



    def _cache_path(self, query: str, max_results: int) -> Path:

        """Return the filesystem path for a cached search result."""

        key = hashlib.sha256(f"{query}:{max_results}".encode()).hexdigest()

        return YOUTUBE_CACHE_DIR / f"{key}.json"



    def _load_cache(

        self, query: str, max_results: int

    ) -> list[VideoCandidate] | None:

        """Load cached search results if available."""

        if not YOUTUBE_CACHE_ENABLED:

            return None

        path = self._cache_path(query, max_results)

        if not path.exists():

            return None

        try:

            with open(path, encoding="utf-8") as f:

                data = json.load(f)

            candidates = [VideoCandidate.model_validate(item) for item in data]

            logger.info("YouTube cache hit for query: %s", query)

            return candidates

        except (json.JSONDecodeError, OSError, ValueError) as e:

            logger.warning("Invalid YouTube cache file %s: %s", path, e)

            return None



    def _save_cache(

        self, query: str, max_results: int, candidates: list[VideoCandidate]

    ) -> None:

        """Persist search results to the local cache."""

        if not YOUTUBE_CACHE_ENABLED:

            return

        try:

            YOUTUBE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

            path = self._cache_path(query, max_results)

            with open(path, "w", encoding="utf-8") as f:

                json.dump(

                    [c.model_dump() for c in candidates],

                    f,

                    indent=2,

                )

            logger.info("YouTube cache saved for query: %s", query)

        except OSError as e:

            logger.warning("Failed to write YouTube cache: %s", e)



    def search_videos(

        self, query: str, max_results: int = MAX_SEARCH_RESULTS

    ) -> list[VideoCandidate]:

        """Search YouTube for videos matching a query."""

        cached = self._load_cache(query, max_results)

        if cached is not None:

            return cached



        try:

            search_response = (

                self._youtube.search()

                .list(

                    q=query,

                    type="video",

                    part="snippet",

                    maxResults=max_results,

                    relevanceLanguage="en",

                )

                .execute()

            )

        except HttpError as e:

            if "quotaExceeded" in str(e):

                raise RuntimeError(

                    "YouTube API quota exceeded. "

                    "Check YOUTUBE_API_KEY and daily quota."

                ) from e

            raise



        video_ids: list[str] = []

        for item in search_response.get("items", []):

            vid = item.get("id", {}).get("videoId")

            if vid:

                video_ids.append(vid)



        if not video_ids:

            return []



        candidates = self._fetch_video_details(video_ids)

        self._save_cache(query, max_results, candidates)

        return candidates



    def _fetch_video_details(

        self, video_ids: list[str]

    ) -> list[VideoCandidate]:

        """Fetch full video details for a list of video IDs."""

        candidates: list[VideoCandidate] = []

        for i in range(0, len(video_ids), 50):

            batch = video_ids[i : i + 50]

            try:

                details_response = (

                    self._youtube.videos()

                    .list(

                        part="contentDetails,statistics,snippet",

                        id=",".join(batch),

                    )

                    .execute()

                )

            except HttpError as e:

                if "quotaExceeded" in str(e):

                    raise RuntimeError(

                        "YouTube API quota exceeded. "

                        "Check YOUTUBE_API_KEY and daily quota."

                    ) from e

                raise



            for item in details_response.get("items", []):

                candidate = self._parse_video_item(item)

                if candidate is not None:

                    candidates.append(candidate)



        return candidates

    def _comment_cache_path(self, video_id: str) -> Path:
        """Return filesystem path for cached comment sample."""
        return YOUTUBE_CACHE_DIR / "comments" / f"{video_id}.json"

    def _load_comment_cache(self, video_id: str) -> CommentSample | None:
        """Load cached comments for a video if available."""
        if not YOUTUBE_CACHE_ENABLED:
            return None
        path = self._comment_cache_path(video_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return CommentSample.model_validate(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Invalid comment cache %s: %s", path, e)
            return None

    def _save_comment_cache(self, video_id: str, sample: CommentSample) -> None:
        """Persist comment sample to local cache."""
        if not YOUTUBE_CACHE_ENABLED:
            return
        try:
            path = self._comment_cache_path(video_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sample.model_dump(), f, indent=2)
        except OSError as e:
            logger.warning("Failed to write comment cache: %s", e)

    @staticmethod
    def _pre_filter_comments(raw_comments: list[str]) -> list[str]:
        """Drop spam-like or too-short comments before LLM scoring."""
        filtered: list[str] = []
        for text in raw_comments:
            cleaned = text.strip()
            if len(cleaned) < 10:
                continue
            if re.fullmatch(r"https?://\S+", cleaned):
                continue
            if len(set(cleaned)) < 4:
                continue
            filtered.append(cleaned)
        return filtered

    def fetch_video_comments(
        self,
        video_id: str,
        max_comments: int = MAX_COMMENTS_PER_VIDEO,
    ) -> CommentSample:
        """Fetch top comment threads for a video via commentThreads.list."""
        if not COMMENT_FETCH_ENABLED:
            return CommentSample(comments_disabled=True)

        cached = self._load_comment_cache(video_id)
        if cached is not None:
            return cached

        try:
            response = (
                self._youtube.commentThreads()
                .list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(max_comments, 100),
                    order="relevance",
                    textFormat="plainText",
                )
                .execute()
            )
        except HttpError as e:
            error_text = str(e)
            if "quotaExceeded" in error_text:
                raise RuntimeError(
                    "YouTube API quota exceeded while fetching comments. "
                    "Check YOUTUBE_API_KEY and daily quota."
                ) from e
            if "commentsDisabled" in error_text or e.resp.status == 403:
                sample = CommentSample(comments_disabled=True)
                self._save_comment_cache(video_id, sample)
                return sample
            logger.warning("Comment fetch failed for %s: %s", video_id, e)
            return CommentSample(comments_disabled=True)

        raw_comments: list[str] = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get(
                "snippet", {}
            )
            text = snippet.get("textDisplay") or snippet.get("textOriginal", "")
            if text:
                raw_comments.append(text)

        comments = self._pre_filter_comments(raw_comments)
        sample = CommentSample(
            comments=comments,
            comment_count=len(comments),
            comments_disabled=len(raw_comments) == 0 and not response.get("items"),
        )
        self._save_comment_cache(video_id, sample)
        return sample

    def _parse_video_item(self, item: dict[str, Any]) -> VideoCandidate | None:

        """Parse a YouTube API video item into a VideoCandidate."""

        video_id = item.get("id", "")

        snippet = item.get("snippet", {})

        content_details = item.get("contentDetails", {})

        statistics = item.get("statistics", {})



        duration_iso = content_details.get("duration")

        if not duration_iso:

            logger.warning("Skipping video %s: missing duration", video_id)

            return None



        try:

            duration_minutes = parse_iso8601_duration(duration_iso)

        except (ValueError, TypeError):

            logger.warning(

                "Skipping video %s: unparseable duration %s",

                video_id,

                duration_iso,

            )

            return None



        view_count = int(statistics.get("viewCount", 0))



        return VideoCandidate(

            video_id=video_id,

            title=snippet.get("title", ""),

            channel=snippet.get("channelTitle", ""),

            duration_minutes=duration_minutes,

            description=snippet.get("description", ""),

            url=f"https://www.youtube.com/watch?v={video_id}",

            view_count=view_count,

            published_at=snippet.get("publishedAt", ""),

        )



    def build_search_queries(self, persona: Persona) -> list[str]:

        """Generate 2-3 targeted search queries from persona goal and unknown topics."""

        unknown = persona.user_context.unknown

        goal = persona.goal

        constraints = persona.user_context.constraints.lower()

        background = persona.user_context.background.lower()



        queries: list[str] = []



        if len(unknown) >= 2:

            q1 = f"{unknown[0]} {unknown[1]} tutorial hands-on"

        elif len(unknown) == 1:

            q1 = f"{unknown[0]} tutorial beginner"

        else:

            q1 = f"{goal.split(',')[0]} tutorial"



        if "beginner" in background or "student" in background:

            q1 += " beginner"

        elif "senior" in background or "engineer" in background:

            q1 += " intermediate"



        queries.append(q1.strip())



        goal_words = goal.replace(",", " ").split()

        key_words = [w for w in goal_words if len(w) > 3][:5]

        q2 = " ".join(key_words) + " tutorial project"

        queries.append(q2.strip())



        if (

            "project" in constraints

            or "hands-on" in constraints

            or "practical" in constraints

        ):

            if len(unknown) >= 1:

                q3 = f"build {unknown[0]} project tutorial"

            else:

                q3 = f"build {key_words[0] if key_words else 'app'} project tutorial"

            queries.append(q3.strip())



        return queries[:3]


