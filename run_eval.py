"""Batch evaluation runner for all test personas."""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from rich.console import Console
from rich.table import Table

from agent import CurriculumAgent
from config import EVAL_RESULTS_DIR, TEST_SET_DIR, YOUTUBE_API_KEY, validate_api_keys
from evaluator import CurriculumEvaluator
from utils import load_persona_from_file
from youtube_client import YouTubeClient

console = Console()


def main() -> None:
    """Run curriculum generation and evaluation for all test personas."""
    validate_api_keys()

    persona_files = sorted(TEST_SET_DIR.glob("*.json"))
    if not persona_files:
        console.print("[red]No persona files found in test_set/[/red]")
        sys.exit(1)

    results: list[dict] = []
    table = Table(title="Evaluation Results")
    table.add_column("Persona")
    table.add_column("Budget", justify="right")
    table.add_column("Known Avoid", justify="right")
    table.add_column("Constraints", justify="right")
    table.add_column("Reason", justify="right")
    table.add_column("Coverage", justify="right")
    table.add_column("Fit", justify="right")
    table.add_column("Audit", justify="right")
    table.add_column("Audience", justify="right")
    table.add_column("Overall", justify="right")

    for path in persona_files:
        persona = load_persona_from_file(str(path))
        console.print(f"\n[bold]Processing {persona.persona_id}...[/bold]")

        agent = CurriculumAgent(persona)
        curriculum = agent.run()

        youtube = YouTubeClient(YOUTUBE_API_KEY)
        evaluator = CurriculumEvaluator(youtube_client=youtube)
        eval_result = evaluator.evaluate(persona, curriculum)

        audience = (
            f"{eval_result.audience_signal_score:.2f}"
            if eval_result.audience_signal_score is not None
            else "n/a"
        )
        table.add_row(
            persona.persona_id,
            f"{eval_result.budget_adherence:.2f}",
            f"{eval_result.known_topic_avoidance:.2f}",
            f"{eval_result.constraint_adherence:.2f}",
            f"{eval_result.reason_quality:.2f}",
            f"{eval_result.coverage_score:.2f}",
            f"{eval_result.curriculum_fit_score:.2f}",
            f"{eval_result.decision_audit_score:.2f}",
            audience,
            f"{eval_result.overall_score:.2f}",
        )

        results.append(
            {
                "persona_id": persona.persona_id,
                "curriculum_summary": {
                    "entries": len(curriculum.entries),
                    "total_minutes": curriculum.total_minutes,
                    "dropped": len(curriculum.dropped),
                },
                "eval": eval_result.model_dump(),
            }
        )

    console.print(table)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "personas_evaluated": len(results),
        "results": results,
    }

    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = EVAL_RESULTS_DIR / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    console.print(f"\n[green]Report saved to {report_path}[/green]")


if __name__ == "__main__":
    main()
