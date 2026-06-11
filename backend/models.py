"""Pydantic models for the curriculum builder application."""

from typing import Literal

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Learner background, knowledge, and constraints."""

    background: str
    known: list[str]
    unknown: list[str]
    constraints: str


class Persona(BaseModel):
    """Learner persona driving curriculum curation."""

    persona_id: str
    goal: str
    time_budget_minutes: int
    user_context: UserContext


class VideoCandidate(BaseModel):
    """A YouTube video candidate from search results."""

    video_id: str
    title: str
    channel: str
    duration_minutes: float
    description: str
    url: str
    view_count: int
    published_at: str


class CurriculumEntry(BaseModel):
    """A ranked video included in the curated curriculum."""

    rank: int
    video: VideoCandidate
    inclusion_reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    covers_topics: list[str]


class DroppedVideo(BaseModel):
    """A video excluded from the curriculum with reasoning."""

    video: VideoCandidate
    drop_reason: str
    drop_stage: Literal["curator", "budget"] = "curator"


PipelineStage = Literal["duration", "known_topic", "view_cap", "curator", "budget"]


class PipelineDrop(BaseModel):
    """A video removed during pipeline filtering before or after curation."""

    stage: PipelineStage
    video: VideoCandidate
    reason: str


class CommentSample(BaseModel):
    """Top YouTube comments fetched for audience signal evaluation."""

    comments: list[str] = Field(default_factory=list)
    comment_count: int = 0
    comments_disabled: bool = False


class Curriculum(BaseModel):
    """Final curated curriculum for a persona."""

    persona_id: str
    goal: str
    total_minutes: float
    budget_minutes: int
    entries: list[CurriculumEntry]
    dropped: list[DroppedVideo]
    agent_notes: str
    pipeline_drops: list[PipelineDrop] = Field(default_factory=list)


class DecisionFlag(BaseModel):
    """A flagged curation decision for human review."""

    flag_type: str
    video_id: str
    title: str
    summary: str
    severity: Literal["low", "medium", "high"] = "medium"


class AudienceSignalDetail(BaseModel):
    """Per-video audience signal breakdown."""

    video_id: str
    title: str
    score: float
    evidence: str = ""
    comment_sample_size: int = 0
    comments_disabled: bool = False


class EvalResult(BaseModel):
    """Evaluation scores for a curated curriculum."""

    persona_id: str
    budget_adherence: float
    known_topic_avoidance: float
    constraint_adherence: float
    reason_quality: float
    coverage_score: float
    overall_score: float
    eval_notes: str
    token_cost_estimate: dict
    curriculum_fit_score: float = 0.0
    decision_audit_score: float = 0.0
    marginal_coverage: float = 0.0
    drop_decision_quality: float = 0.0
    counterfactual_regret: float = 0.0
    decision_redundancy: float = 0.0
    audience_signal_score: float | None = None
    deduplication_quality: float = 0.0
    decision_flags: list[DecisionFlag] = Field(default_factory=list)
    audience_signal_details: list[AudienceSignalDetail] = Field(default_factory=list)
    pipeline_drops: dict[str, int] = Field(default_factory=dict)


class AgentProgressEvent(BaseModel):
    """Progress event streamed during agent execution."""

    step: str
    message: str
    data: dict = Field(default_factory=dict)


class FollowUpRequest(BaseModel):
    """Request body for follow-up Q&A."""

    persona: Persona
    curriculum: Curriculum
    question: str


class EvaluateRequest(BaseModel):
    """Request body for curriculum evaluation."""

    persona: Persona
    curriculum: Curriculum


class FollowUpResponse(BaseModel):
    """Response body for follow-up Q&A."""

    answer: str


class TestPersonaItem(BaseModel):
    """A test persona exposed via the API."""

    filename: str
    persona_id: str
    persona: Persona
