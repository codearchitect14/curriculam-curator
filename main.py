"""CLI entry point for the curriculum builder."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from agent import CurriculumAgent
from config import validate_api_keys
from curator import CurriculumCurator
from utils import load_persona_from_file, print_curriculum


def main() -> None:
    """Run the curriculum builder from the command line."""
    parser = argparse.ArgumentParser(description="Curriculum Builder CLI")
    parser.add_argument(
        "--persona",
        required=True,
        help="Path to persona JSON file",
    )
    parser.add_argument(
        "--ask",
        default=None,
        help="Optional follow-up question after curation",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write curriculum JSON",
    )
    args = parser.parse_args()

    validate_api_keys()
    persona = load_persona_from_file(args.persona)
    agent = CurriculumAgent(persona)
    curriculum = agent.run()
    print_curriculum(curriculum)

    if args.ask:
        curator = CurriculumCurator(persona)
        answer = curator.answer_followup(curriculum, args.ask)
        from rich.console import Console

        Console().print(f"\n[bold]Follow-up answer:[/bold]\n{answer}")

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(curriculum.model_dump(), f, indent=2)


if __name__ == "__main__":
    main()
