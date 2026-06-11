"""Evaluation logic and scoring for curated curricula."""



import logging

import re



from config import AUDIENCE_SIGNAL_ENABLED, COMMENT_FETCH_ENABLED

from curator import call_anthropic

from models import (

    AudienceSignalDetail,

    CommentSample,

    Curriculum,

    CurriculumEntry,

    DecisionFlag,

    DroppedVideo,

    EvalResult,

    Persona,

)

from prompts import (

    build_batch_audience_signal_prompt,

    build_batch_drop_quality_prompt,

    build_batch_inclusion_reason_quality_prompt,

    build_batch_known_topic_overlap_prompt,

    build_batch_unknown_coverage_prompt,

    build_counterfactual_prompt,

    build_eval_metric_prompt,

)

from utils import (

    jaccard_similarity,

    summarize_pipeline_drops,

    topic_covered_semantically,

)

from youtube_client import YouTubeClient



logger = logging.getLogger(__name__)



# BLIND SPOT: reason_quality via LLM cannot verify if the reason is factually accurate about the video

# BLIND SPOT: known_topic_avoidance blind spot documents agent pre-filter limitation, not eval LLM logic

# BLIND SPOT: audience_signal_score reflects commenter opinions, not representative learner outcomes

# BLIND SPOT: counterfactual_regret only samples top dropped videos by view count



BLIND_SPOT_REASON = (

    "reason_quality via LLM cannot verify if the reason is factually accurate about the video"

)

BLIND_SPOT_KNOWN = (

    "known_topic_avoidance uses keyword matching which misses semantic overlap"

)

BLIND_SPOT_AUDIENCE = (

    "audience_signal_score reflects commenter opinions, not representative learner outcomes"

)

BLIND_SPOT_COUNTERFACTUAL = (

    "counterfactual_regret only samples top-3 dropped videos by view count"

)





class CurriculumEvaluator:

    """Evaluates curriculum quality against persona requirements."""



    def __init__(self, youtube_client: YouTubeClient | None = None) -> None:

        """Initialize the evaluator with optional YouTube client for comments."""

        self.input_tokens: int = 0

        self.output_tokens: int = 0

        self._youtube = youtube_client



    def evaluate(self, persona: Persona, curriculum: Curriculum) -> EvalResult:

        """Evaluate a curriculum and return scored metrics."""

        entries = curriculum.entries

        curator_drops = [

            d for d in curriculum.dropped if d.drop_stage == "curator"

        ]

        decision_flags: list[DecisionFlag] = []



        budget_adherence = self._score_budget_adherence(curriculum)

        known_topic_avoidance = self._score_known_topic_avoidance(persona, entries)

        constraint_adherence = self._score_constraint_adherence(persona, curriculum)

        reason_quality = self._score_inclusion_reason_quality(persona, entries)

        marginal_coverage, llm_topic_map = self._score_marginal_coverage(

            persona, entries

        )

        decision_redundancy = self._score_decision_redundancy(

            persona, entries, llm_topic_map

        )

        deduplication_quality = self._score_deduplication(entries)

        drop_decision_quality = self._score_drop_decision_quality(

            persona, entries, curator_drops

        )

        counterfactual_regret, swap_flags = self._score_counterfactual_regret(

            persona, entries, curator_drops

        )

        decision_flags.extend(swap_flags)



        audience_signal_score, audience_details, audience_flags = (

            self._score_audience_signal(persona, entries)

        )

        decision_flags.extend(audience_flags)



        for entry in entries:

            if entry.confidence < 0.5 and reason_quality < 0.6:

                decision_flags.append(

                    DecisionFlag(

                        flag_type="questionable_inclusion",

                        video_id=entry.video.video_id,

                        title=entry.video.title,

                        summary=(

                            f"Low confidence ({entry.confidence:.2f}) "

                            "with weak inclusion reasoning"

                        ),

                        severity="medium",

                    )

                )



        redundant_entries = self._zero_contribution_entries(

            persona, entries, llm_topic_map

        )

        for entry in redundant_entries:

            decision_flags.append(

                DecisionFlag(

                    flag_type="redundant_inclusion",

                    video_id=entry.video.video_id,

                    title=entry.video.title,

                    summary="Entry contributes no unique unknown topics",

                    severity="medium",

                )

            )



        for dropped in curriculum.dropped:

            if dropped.drop_stage == "budget":

                decision_flags.append(

                    DecisionFlag(

                        flag_type="budget_forced_drop",

                        video_id=dropped.video.video_id,

                        title=dropped.video.title,

                        summary=dropped.drop_reason,

                        severity="low",

                    )

                )



        fit_weights = self._curriculum_fit_weights(audience_signal_score)

        curriculum_fit_score = (

            budget_adherence * fit_weights["budget"]

            + marginal_coverage * fit_weights["marginal_coverage"]

            + known_topic_avoidance * fit_weights["known_topic_avoidance"]

            + constraint_adherence * fit_weights["constraint_adherence"]

            + (audience_signal_score or 0.0) * fit_weights["audience_signal"]

        )



        decision_audit_score = (

            reason_quality * 0.30

            + drop_decision_quality * 0.30

            + counterfactual_regret * 0.25

            + decision_redundancy * 0.15

        )



        overall_score = (

            0.60 * curriculum_fit_score + 0.40 * decision_audit_score

        )



        pipeline_drop_counts = summarize_pipeline_drops(curriculum.pipeline_drops)

        for dropped in curator_drops:

            pipeline_drop_counts["curator"] = (

                pipeline_drop_counts.get("curator", 0) + 1

            )



        estimated_usd = (self.input_tokens * 0.000003) + (

            self.output_tokens * 0.000015

        )



        audience_note = (

            f"audience_signal: {audience_signal_score:.2f}"

            if audience_signal_score is not None

            else "audience_signal: unavailable"

        )

        eval_notes = (

            f"{BLIND_SPOT_REASON}. {BLIND_SPOT_KNOWN}. "

            f"{BLIND_SPOT_AUDIENCE}. {BLIND_SPOT_COUNTERFACTUAL}. "

            f"{audience_note}. "

            f"deduplication_quality (supplementary): {deduplication_quality:.2f}"

        )



        return EvalResult(

            persona_id=persona.persona_id,

            budget_adherence=budget_adherence,

            known_topic_avoidance=known_topic_avoidance,

            constraint_adherence=constraint_adherence,

            reason_quality=reason_quality,

            coverage_score=marginal_coverage,

            overall_score=overall_score,

            eval_notes=eval_notes,

            token_cost_estimate={

                "input_tokens": self.input_tokens,

                "output_tokens": self.output_tokens,

                "estimated_usd": round(estimated_usd, 4),

            },

            curriculum_fit_score=curriculum_fit_score,

            decision_audit_score=decision_audit_score,

            marginal_coverage=marginal_coverage,

            drop_decision_quality=drop_decision_quality,

            counterfactual_regret=counterfactual_regret,

            decision_redundancy=decision_redundancy,

            audience_signal_score=audience_signal_score,

            deduplication_quality=deduplication_quality,

            decision_flags=decision_flags,

            audience_signal_details=audience_details,

            pipeline_drops=pipeline_drop_counts,

        )



    def _curriculum_fit_weights(

        self, audience_signal_score: float | None

    ) -> dict[str, float]:

        """Return curriculum fit tier weights; redistribute audience if unavailable."""

        if audience_signal_score is not None:

            return {

                "budget": 0.10,

                "marginal_coverage": 0.30,

                "known_topic_avoidance": 0.20,

                "constraint_adherence": 0.20,

                "audience_signal": 0.20,

            }

        return {

            "budget": 0.125,

            "marginal_coverage": 0.375,

            "known_topic_avoidance": 0.25,

            "constraint_adherence": 0.25,

            "audience_signal": 0.0,

        }



    def _score_budget_adherence(self, curriculum: Curriculum) -> float:

        """Programmatic budget adherence score."""

        total = curriculum.total_minutes

        budget = curriculum.budget_minutes

        if total <= budget:

            return 1.0

        if total <= budget * 1.1:

            return 0.5

        return 0.0



    def _entry_topic_text(self, entry: CurriculumEntry) -> str:

        """Combine description, reason, and tags for topic matching."""

        return " ".join(

            [

                entry.video.description,

                entry.inclusion_reason,

                " ".join(entry.covers_topics),

            ]

        )



    def _parse_unknown_topic_map(

        self, text: str, count: int, unknown: list[str]

    ) -> list[list[str]]:

        """Parse LLM unknown-topic mapping lines into topic lists per entry."""

        unknown_lower = {u.lower(): u for u in unknown}

        results: dict[int, list[str]] = {}

        for line in text.strip().split("\n"):

            match = re.match(r"^\s*(\d+)\s*:\s*(.+)$", line.strip())

            if not match:

                continue

            idx = int(match.group(1))

            value = match.group(2).strip()

            if value.upper() == "NONE":

                results[idx] = []

                continue

            mapped: list[str] = []

            for part in value.split(","):

                key = part.strip().lower()

                if key in unknown_lower:

                    mapped.append(unknown_lower[key])

            results[idx] = mapped

        return [results.get(i + 1, []) for i in range(count)]



    def _score_marginal_coverage(

        self, persona: Persona, entries: list[CurriculumEntry]

    ) -> tuple[float, list[list[str]]]:

        """Score unknown topic coverage using LLM tags and semantic overlap."""

        unknown = persona.user_context.unknown

        if not unknown:

            return 1.0, [[] for _ in entries]

        if not entries:

            return 0.0, []



        llm_map: list[list[str]] = [[] for _ in entries]

        if entries:

            prompt = build_batch_unknown_coverage_prompt(persona, entries)

            text, in_tok, out_tok = call_anthropic(prompt)

            self.input_tokens += in_tok

            self.output_tokens += out_tok

            llm_map = self._parse_unknown_topic_map(text, len(entries), unknown)



        covered_topics: set[str] = set()

        unique_contributors = 0



        for entry, llm_topics in zip(entries, llm_map):

            entry_text = self._entry_topic_text(entry)

            entry_covers: set[str] = set()

            for topic in unknown:

                topic_union = " ".join([entry_text, " ".join(llm_topics)])

                if topic_covered_semantically(topic_union, topic):

                    entry_covers.add(topic)

            for topic in entry_covers:

                if topic not in covered_topics:

                    unique_contributors += 1

                covered_topics.add(topic)



        total_coverage = len(covered_topics) / len(unknown)

        if not entries:

            return total_coverage, llm_map



        per_entry_unique = 0

        for entry, llm_topics in zip(entries, llm_map):

            entry_text = self._entry_topic_text(entry)

            exclusively_covers = False

            for topic in unknown:

                topic_union = " ".join([entry_text, " ".join(llm_topics)])

                if not topic_covered_semantically(topic_union, topic):

                    continue

                if sum(

                    1

                    for other, other_llm in zip(entries, llm_map)

                    if other is not entry

                    and topic_covered_semantically(

                        " ".join(

                            [

                                self._entry_topic_text(other),

                                " ".join(other_llm),

                            ]

                        ),

                        topic,

                    )

                ) == 0:

                    exclusively_covers = True

                    break

            if exclusively_covers:

                per_entry_unique += 1



        uniqueness_bonus = per_entry_unique / len(entries)

        score = min(1.0, (0.75 * total_coverage) + (0.25 * uniqueness_bonus))

        return score, llm_map



    def _zero_contribution_entries(

        self,

        persona: Persona,

        entries: list[CurriculumEntry],

        llm_map: list[list[str]],

    ) -> list[CurriculumEntry]:

        """Return entries that uniquely cover zero unknown topics."""

        unknown = persona.user_context.unknown

        if not unknown:

            return []



        redundant: list[CurriculumEntry] = []

        for entry, llm_topics in zip(entries, llm_map):

            entry_text = self._entry_topic_text(entry)

            has_unique = False

            for topic in unknown:

                if not topic_covered_semantically(

                    " ".join([entry_text, " ".join(llm_topics)]), topic

                ):

                    continue

                other_covers = any(

                    topic_covered_semantically(

                        " ".join(

                            [

                                self._entry_topic_text(other),

                                " ".join(other_llm),

                            ]

                        ),

                        topic,

                    )

                    for other, other_llm in zip(entries, llm_map)

                    if other is not entry

                )

                if not other_covers:

                    has_unique = True

                    break

            if not has_unique:

                redundant.append(entry)

        return redundant



    def _score_decision_redundancy(

        self,

        persona: Persona,

        entries: list[CurriculumEntry],

        llm_map: list[list[str]],

    ) -> float:

        """Score how well included videos avoid redundant coverage."""

        if len(entries) <= 1:

            return 1.0



        redundant = self._zero_contribution_entries(persona, entries, llm_map)

        redundant_fraction = len(redundant) / len(entries)

        tag_overlap_penalty = 0.0

        for i in range(len(entries)):

            for j in range(i + 1, len(entries)):

                sim = jaccard_similarity(

                    entries[i].covers_topics, entries[j].covers_topics

                )

                if sim > 0.7:

                    tag_overlap_penalty += 0.15



        score = 1.0 - redundant_fraction - tag_overlap_penalty

        return max(0.0, min(1.0, score))



    def _score_deduplication(self, entries: list[CurriculumEntry]) -> float:

        """Programmatic deduplication quality via Jaccard similarity."""

        flagged_pairs = 0

        for i in range(len(entries)):

            for j in range(i + 1, len(entries)):

                sim = jaccard_similarity(

                    entries[i].covers_topics, entries[j].covers_topics

                )

                if sim > 0.7:

                    flagged_pairs += 1

        score = 1.0 - (0.25 * flagged_pairs)

        return max(0.0, score)



    def _parse_batch_yes_no(self, text: str, count: int) -> list[bool]:

        """Parse batched YES/NO lines like '1: NO' into booleans (True = no overlap)."""

        results: dict[int, bool] = {}

        for line in text.strip().split("\n"):

            match = re.match(r"^\s*(\d+)\s*:\s*(YES|NO)", line.strip(), re.I)

            if match:

                idx = int(match.group(1))

                results[idx] = match.group(2).upper() == "NO"

        return [results.get(i + 1, True) for i in range(count)]



    def _parse_batch_justified(self, text: str, count: int) -> list[bool]:

        """Parse batched YES/NO where YES means justified."""

        results: dict[int, bool] = {}

        for line in text.strip().split("\n"):

            match = re.match(r"^\s*(\d+)\s*:\s*(YES|NO)", line.strip(), re.I)

            if match:

                idx = int(match.group(1))

                results[idx] = match.group(2).upper() == "YES"

        return [results.get(i + 1, True) for i in range(count)]



    def _parse_batch_scores(

        self, text: str, count: int, default: float = 0.5

    ) -> list[float]:

        """Parse batched score lines like '1: 0.85' into floats."""

        results: dict[int, float] = {}

        for line in text.strip().split("\n"):

            match = re.match(r"^\s*(\d+)\s*:\s*(\d+\.?\d*)", line.strip())

            if match:

                idx = int(match.group(1))

                results[idx] = min(1.0, max(0.0, float(match.group(2))))

        return [results.get(i + 1, default) for i in range(count)]



    def _parse_audience_scores(

        self, text: str, count: int

    ) -> tuple[list[float], dict[int, str]]:

        """Parse audience signal scores and optional evidence lines."""

        scores = self._parse_batch_scores(text, count, default=0.5)

        evidence: dict[int, str] = {}

        for line in text.strip().split("\n"):

            match = re.match(r"^\s*(\d+)_EVIDENCE\s*:\s*(.+)$", line.strip(), re.I)

            if match:

                evidence[int(match.group(1))] = match.group(2).strip()

        return scores, evidence



    def _score_known_topic_avoidance(

        self, persona: Persona, entries: list[CurriculumEntry]

    ) -> float:

        """LLM-based known topic overlap score (batched)."""

        if not entries:

            return 0.0



        prompt = build_batch_known_topic_overlap_prompt(persona, entries)

        text, in_tok, out_tok = call_anthropic(prompt)

        self.input_tokens += in_tok

        self.output_tokens += out_tok

        no_overlap_flags = self._parse_batch_yes_no(text, len(entries))

        return sum(no_overlap_flags) / len(entries)



    def _score_constraint_adherence(

        self, persona: Persona, curriculum: Curriculum

    ) -> float:

        """LLM-based constraint violation score."""

        prompt = build_eval_metric_prompt(

            "constraint_violation", persona, curriculum=curriculum

        )

        text, in_tok, out_tok = call_anthropic(prompt)

        self.input_tokens += in_tok

        self.output_tokens += out_tok



        first_line = text.strip().split("\n")[0].upper()

        if first_line == "NONE":

            return 1.0



        match = re.search(r"VIOLATIONS:\s*(\d+)", first_line)

        if match:

            violations = int(match.group(1))

            return max(0.0, 1.0 - 0.2 * violations)



        violation_lines = [

            ln

            for ln in text.strip().split("\n")[1:]

            if ln.strip() and not ln.strip().upper().startswith("NONE")

        ]

        if not violation_lines:

            return 1.0

        return max(0.0, 1.0 - 0.2 * len(violation_lines))



    def _score_inclusion_reason_quality(

        self, persona: Persona, entries: list[CurriculumEntry]

    ) -> float:

        """LLM-based inclusion reason quality averaged across entries."""

        if not entries:

            return 0.0



        prompt = build_batch_inclusion_reason_quality_prompt(persona, entries)

        text, in_tok, out_tok = call_anthropic(prompt)

        self.input_tokens += in_tok

        self.output_tokens += out_tok

        scores = self._parse_batch_scores(text, len(entries))

        return sum(scores) / len(scores)



    def _score_drop_decision_quality(

        self,

        persona: Persona,

        entries: list[CurriculumEntry],

        dropped: list[DroppedVideo],

    ) -> float:

        """LLM-based drop justification score for curator drops."""

        if not dropped:

            return 1.0



        prompt = build_batch_drop_quality_prompt(persona, entries, dropped)

        if not prompt:

            return 1.0



        text, in_tok, out_tok = call_anthropic(prompt)

        self.input_tokens += in_tok

        self.output_tokens += out_tok

        justified = self._parse_batch_justified(text, len(dropped))

        return sum(justified) / len(justified)



    def _score_counterfactual_regret(

        self,

        persona: Persona,

        entries: list[CurriculumEntry],

        dropped: list[DroppedVideo],

    ) -> tuple[float, list[DecisionFlag]]:

        """Sample top dropped videos and detect swap regret."""

        flags: list[DecisionFlag] = []

        if not dropped or not entries:

            return 1.0, flags



        sampled = sorted(

            dropped, key=lambda d: d.video.view_count, reverse=True

        )[:3]

        prompt = build_counterfactual_prompt(persona, entries, sampled)

        if not prompt:

            return 1.0, flags



        text, in_tok, out_tok = call_anthropic(prompt)

        self.input_tokens += in_tok

        self.output_tokens += out_tok



        regret_count = 0

        for i, dropped_video in enumerate(sampled, 1):

            line = next(

                (

                    ln.strip()

                    for ln in text.split("\n")

                    if re.match(rf"^\s*{i}\s*:", ln.strip(), re.I)

                ),

                "",

            )

            if line and "YES" in line.upper():

                regret_count += 1

                flags.append(

                    DecisionFlag(

                        flag_type="suggested_swap",

                        video_id=dropped_video.video.video_id,

                        title=dropped_video.video.title,

                        summary=line.split(":", 1)[-1].strip(),

                        severity="high",

                    )

                )



        score = 1.0 - (regret_count / len(sampled))

        return score, flags



    def _score_audience_signal(

        self, persona: Persona, entries: list[CurriculumEntry]

    ) -> tuple[float | None, list[AudienceSignalDetail], list[DecisionFlag]]:

        """Fetch comments and score persona-relevant audience feedback."""

        flags: list[DecisionFlag] = []

        details: list[AudienceSignalDetail] = []



        if (

            not AUDIENCE_SIGNAL_ENABLED

            or not COMMENT_FETCH_ENABLED

            or not self._youtube

            or not entries

        ):

            return None, details, flags



        samples: list[CommentSample] = []

        for entry in entries:

            try:

                sample = self._youtube.fetch_video_comments(entry.video.video_id)

            except RuntimeError as e:

                logger.warning("Audience signal skipped: %s", e)

                return None, details, flags

            samples.append(sample)



        prompt = build_batch_audience_signal_prompt(persona, entries, samples)

        text, in_tok, out_tok = call_anthropic(prompt)

        self.input_tokens += in_tok

        self.output_tokens += out_tok

        scores, evidence_map = self._parse_audience_scores(text, len(entries))



        scorable_scores: list[float] = []

        for i, (entry, sample, score) in enumerate(

            zip(entries, samples, scores), 1

        ):

            if sample.comments_disabled or not sample.comments:

                details.append(

                    AudienceSignalDetail(

                        video_id=entry.video.video_id,

                        title=entry.video.title,

                        score=score,

                        evidence=evidence_map.get(i, ""),

                        comment_sample_size=0,

                        comments_disabled=True,

                    )

                )

                continue



            scorable_scores.append(score)

            detail = AudienceSignalDetail(

                video_id=entry.video.video_id,

                title=entry.video.title,

                score=score,

                evidence=evidence_map.get(i, ""),

                comment_sample_size=len(sample.comments),

                comments_disabled=False,

            )

            details.append(detail)

            if score < 0.4:

                flags.append(

                    DecisionFlag(

                        flag_type="weak_audience_signal",

                        video_id=entry.video.video_id,

                        title=entry.video.title,

                        summary=detail.evidence or "Low audience signal score",

                        severity="high",

                    )

                )



        if not scorable_scores:

            return None, details, flags



        return sum(scorable_scores) / len(scorable_scores), details, flags


