"""All LLM prompt templates for the curriculum builder."""

from models import CommentSample, Curriculum, CurriculumEntry, DroppedVideo, Persona, VideoCandidate


def _serialize_candidates(candidates: list[VideoCandidate]) -> str:
    """Serialize video candidates for inclusion in a prompt."""
    lines: list[str] = []
    for i, c in enumerate(candidates, 1):
        lines.append(
            f"[{i}] Title: {c.title}\n"
            f"    Channel: {c.channel}\n"
            f"    Duration: {c.duration_minutes:.1f} min\n"
            f"    Views: {c.view_count:,}\n"
            f"    Description: {c.description[:300]}\n"
            f"    URL: {c.url}\n"
            f"    video_id: {c.video_id}"
        )
    return "\n\n".join(lines)


def build_curation_prompt(
    persona: Persona, candidates: list[VideoCandidate]
) -> str:
    """Build the prompt for LLM-based curriculum curation."""
    ctx = persona.user_context
    candidates_text = _serialize_candidates(candidates)

    return f"""You are an expert curriculum curator. Given a learner persona and a list of YouTube video candidates, select the best 4-6 videos that fit within the time budget.

PERSONA:
- persona_id: {persona.persona_id}
- goal: {persona.goal}
- time_budget_minutes: {persona.time_budget_minutes}
- background: {ctx.background}
- known topics: {', '.join(ctx.known)}
- unknown topics (need coverage): {', '.join(ctx.unknown)}
- constraints: {ctx.constraints}

VIDEO CANDIDATES:
{candidates_text}

INSTRUCTIONS:
1. Read the full persona: background, known topics, unknown topics, constraints.
2. Select 4-6 videos that fit within {persona.time_budget_minutes} minutes total.
3. For EACH selected video:
   - Write inclusion_reason referencing specific content (not just title)
   - Assign confidence (0.0-1.0) with brief justification
   - List which unknown topics this video covers in covers_topics
4. For EACH dropped video (candidates not selected), write a specific drop_reason tied to the persona.
5. Detect content-level duplicates: if two videos cover the same ground, pick the better one and explain why in drop_reason for the other.
6. Write agent_notes explaining your overall curation strategy.
7. Strictly respect constraints (e.g. "no pure theory" = drop theory-only videos).
8. Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation outside JSON.

Use this exact JSON schema:
{{
  "entries": [
    {{
      "rank": 1,
      "video_id": "...",
      "inclusion_reason": "...",
      "confidence": 0.95,
      "covers_topics": ["React hooks", "useState"]
    }}
  ],
  "dropped": [
    {{
      "video_id": "...",
      "drop_reason": "..."
    }}
  ],
  "agent_notes": "..."
}}"""


def build_followup_prompt(
    curriculum: Curriculum, question: str, persona: Persona
) -> str:
    """Build the prompt for follow-up Q&A about a curriculum."""
    ctx = persona.user_context
    entries_text = "\n".join(
        f"#{e.rank} {e.video.title} ({e.video.duration_minutes:.1f} min) - "
        f"Reason: {e.inclusion_reason}. Topics: {', '.join(e.covers_topics)}"
        for e in curriculum.entries
    )
    dropped_text = "\n".join(
        f"- {d.video.title}: {d.drop_reason}" for d in curriculum.dropped
    )

    return f"""You curated this learning curriculum. Answer the user's question using content-grounded reasoning.

LEARNER PERSONA:
- background: {ctx.background}
- known topics: {', '.join(ctx.known)}
- unknown topics: {', '.join(ctx.unknown)}
- constraints: {ctx.constraints}

GOAL: {curriculum.goal}
BUDGET: {curriculum.total_minutes:.1f} / {curriculum.budget_minutes} min

SELECTED VIDEOS:
{entries_text}

DROPPED VIDEOS:
{dropped_text}

AGENT NOTES: {curriculum.agent_notes}

USER QUESTION: {question}

Provide a clear, helpful answer that defends or explains your curation choices. Reference specific video content, persona constraints, and reasons. Return plain text only, not JSON."""


def build_eval_metric_prompt(
    metric: str,
    persona: Persona,
    entry: CurriculumEntry | None = None,
    curriculum: Curriculum | None = None,
) -> str:
    """Build a focused prompt for LLM-based evaluation metrics."""
    ctx = persona.user_context

    if metric == "known_topic_overlap":
        if entry is None:
            raise ValueError("entry required for known_topic_overlap metric")
        return f"""Evaluate whether this curriculum entry overlaps with topics the learner already knows.

KNOWN TOPICS: {', '.join(ctx.known)}

VIDEO: {entry.video.title}
INCLUSION REASON: {entry.inclusion_reason}
COVERS TOPICS: {', '.join(entry.covers_topics)}

Does this entry teach content the learner already knows (overlap with known topics)?
Answer with exactly YES or NO on the first line, then a one-sentence explanation."""

    if metric == "constraint_violation":
        if curriculum is None:
            raise ValueError("curriculum required for constraint_violation metric")
        entries_summary = "\n".join(
            f"- {e.video.title} ({e.video.duration_minutes:.1f} min): "
            f"{e.inclusion_reason}"
            for e in curriculum.entries
        )
        return f"""Evaluate whether this curriculum violates the learner's constraints.

CONSTRAINTS: {ctx.constraints}
GOAL: {persona.goal}
BUDGET: {curriculum.total_minutes:.1f} / {curriculum.budget_minutes} min

CURRICULUM ENTRIES:
{entries_summary}

List any constraint violations. If none, respond with exactly "NONE" on the first line.
If violations exist, respond with "VIOLATIONS: N" on the first line (N = count), then list each violation on its own line."""

    if metric == "reason_quality":
        if entry is None:
            raise ValueError("entry required for reason_quality metric")
        return f"""Rate the quality of this inclusion reason for a curriculum entry.

VIDEO TITLE: {entry.video.title}
VIDEO DESCRIPTION (excerpt): {entry.video.description[:300]}
INCLUSION REASON: {entry.inclusion_reason}

Rate 0.0-1.0 whether the reason references specific video content (not just the title).
Respond with exactly a decimal number between 0.0 and 1.0 on the first line, then a one-sentence justification."""

    raise ValueError(f"Unknown metric: {metric}")


def build_batch_known_topic_overlap_prompt(
    persona: Persona, entries: list[CurriculumEntry]
) -> str:
    """Build a batched prompt to score known-topic overlap for all entries."""
    ctx = persona.user_context
    entries_text = "\n".join(
        f"{i + 1}. VIDEO: {e.video.title}\n"
        f"   INCLUSION REASON: {e.inclusion_reason}\n"
        f"   COVERS TOPICS: {', '.join(e.covers_topics)}"
        for i, e in enumerate(entries)
    )
    return f"""Evaluate whether each curriculum entry overlaps with topics the learner already knows.

KNOWN TOPICS: {', '.join(ctx.known)}

ENTRIES:
{entries_text}

For each entry (1 through {len(entries)}), does it teach content the learner already knows?
Respond with exactly one line per entry in this format:
N: YES or N: NO
where N is the entry number. No other text."""


def build_batch_reason_quality_prompt(
    persona: Persona, entries: list[CurriculumEntry]
) -> str:
    """Build a batched prompt to score inclusion-reason quality for all entries."""
    entries_text = "\n".join(
        f"{i + 1}. VIDEO: {e.video.title}\n"
        f"   DESCRIPTION: {e.video.description[:300]}\n"
        f"   INCLUSION REASON: {e.inclusion_reason}"
        for i, e in enumerate(entries)
    )
    return f"""Rate the quality of each inclusion reason (0.0-1.0) for persona goal: {persona.goal}

ENTRIES:
{entries_text}

For each entry, rate whether the reason references specific video content (not just the title).
Respond with exactly one line per entry in this format:
N: 0.85
where N is the entry number and the value is between 0.0 and 1.0. No other text."""


def build_batch_inclusion_reason_quality_prompt(
    persona: Persona, entries: list[CurriculumEntry]
) -> str:
    """Build a batched prompt for persona-tied inclusion reason quality."""
    ctx = persona.user_context
    entries_text = "\n".join(
        f"{i + 1}. VIDEO: {e.video.title}\n"
        f"   DESCRIPTION: {e.video.description[:300]}\n"
        f"   INCLUSION REASON: {e.inclusion_reason}\n"
        f"   COVERS: {', '.join(e.covers_topics)}"
        for i, e in enumerate(entries)
    )
    return f"""Rate inclusion reason quality (0.0-1.0) for each entry.

PERSONA GOAL: {persona.goal}
UNKNOWN TOPICS TO COVER: {', '.join(ctx.unknown)}
CONSTRAINTS: {ctx.constraints}

For each entry, rate whether the reason:
1) References specific video content (not just title)
2) Ties clearly to this persona's goal or unknown-topic gap

ENTRIES:
{entries_text}

Respond with exactly one line per entry:
N: 0.85
where N is the entry number. No other text."""


def build_batch_drop_quality_prompt(
    persona: Persona,
    entries: list[CurriculumEntry],
    dropped: list[DroppedVideo],
) -> str:
    """Build a batched prompt to judge whether drop decisions were justified."""
    if not dropped:
        return ""

    ctx = persona.user_context
    included_summary = "\n".join(
        f"- {e.video.title}: {e.inclusion_reason}" for e in entries
    )
    dropped_text = "\n".join(
        f"{i + 1}. VIDEO: {d.video.title}\n"
        f"   DESCRIPTION: {d.video.description[:250]}\n"
        f"   DROP REASON: {d.drop_reason}"
        for i, d in enumerate(dropped)
    )
    return f"""Judge whether each dropped video was correctly excluded for this learner.

PERSONA GOAL: {persona.goal}
KNOWN TOPICS: {', '.join(ctx.known)}
UNKNOWN TOPICS: {', '.join(ctx.unknown)}
CONSTRAINTS: {ctx.constraints}

INCLUDED VIDEOS:
{included_summary or '(none)'}

DROPPED VIDEOS:
{dropped_text}

For each dropped video (1 through {len(dropped)}), was the drop justified?
Respond with exactly one line per drop:
N: YES or N: NO
where YES means the drop was justified. No other text."""


def build_counterfactual_prompt(
    persona: Persona,
    entries: list[CurriculumEntry],
    sampled_dropped: list[DroppedVideo],
) -> str:
    """Build a prompt to detect regretful include/drop swaps."""
    if not sampled_dropped or not entries:
        return ""

    ctx = persona.user_context
    included_text = "\n".join(
        f"- {e.video.title} ({e.video.duration_minutes:.1f} min): "
        f"{e.inclusion_reason}"
        for e in entries
    )
    dropped_text = "\n".join(
        f"{i + 1}. {d.video.title} ({d.video.duration_minutes:.1f} min)\n"
        f"   Drop reason: {d.drop_reason}\n"
        f"   Description: {d.video.description[:250]}"
        for i, d in enumerate(sampled_dropped)
    )
    return f"""Counterfactual curriculum check for learner fit.

PERSONA GOAL: {persona.goal}
CONSTRAINTS: {ctx.constraints}
UNKNOWN TOPICS: {', '.join(ctx.unknown)}

CURRENTLY INCLUDED:
{included_text}

SAMPLED DROPPED (evaluate for swap regret):
{dropped_text}

For each sampled dropped video (1 through {len(sampled_dropped)}), should it replace a currently included video?
Respond with exactly one line per dropped video:
N: NO
or
N: YES - replace <included video title>
No other text."""


def build_batch_unknown_coverage_prompt(
    persona: Persona, entries: list[CurriculumEntry]
) -> str:
    """Build a prompt to map each entry to persona unknown topics."""
    ctx = persona.user_context
    entries_text = "\n".join(
        f"{i + 1}. VIDEO: {e.video.title}\n"
        f"   DESCRIPTION: {e.video.description[:300]}\n"
        f"   INCLUSION REASON: {e.inclusion_reason}"
        for i, e in enumerate(entries)
    )
    unknown_list = ", ".join(ctx.unknown)
    return f"""Map each video to unknown topics it teaches from this list ONLY:
{unknown_list}

ENTRIES:
{entries_text}

For each entry (1 through {len(entries)}), list matching unknown topics as comma-separated values.
If none match, write NONE.
Format:
N: topic1, topic2
No other text."""


def build_batch_audience_signal_prompt(
    persona: Persona,
    entries: list[CurriculumEntry],
    comment_samples: list[CommentSample],
) -> str:
    """Build a prompt to score audience feedback fit per included video."""
    ctx = persona.user_context
    blocks: list[str] = []
    for i, (entry, sample) in enumerate(zip(entries, comment_samples), 1):
        if sample.comments_disabled or not sample.comments:
            comment_block = "(comments disabled or unavailable)"
        else:
            comment_block = "\n".join(
                f'  - "{c[:200]}"' for c in sample.comments[:15]
            )
        blocks.append(
            f"{i}. VIDEO: {entry.video.title}\n"
            f"   GOAL RELEVANCE: {entry.inclusion_reason}\n"
            f"   AUDIENCE COMMENTS:\n{comment_block}"
        )
    entries_text = "\n\n".join(blocks)
    return f"""Score audience signal (0.0-1.0) for whether commenters suggest this video fits THIS learner.

PERSONA GOAL: {persona.goal}
BACKGROUND: {ctx.background}
CONSTRAINTS: {ctx.constraints}

Look for persona-relevant signals:
- Positive: clarity praise, hands-on praise (if practical learner), "finally understood X"
- Negative: too fast, assumes prior knowledge, outdated, confusing, clickbait

NOT raw positivity — rate fit for this specific learner.

ENTRIES:
{entries_text}

Respond with one line per entry:
N: 0.75
Optional evidence line:
N_EVIDENCE: short quote
If comments unavailable, respond N: 0.5"""
