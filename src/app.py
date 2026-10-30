"""Interactive CLI entry point.

Usage (from the project root, with the venv active):
    python -m src.app                       # prompts you for a request
    python -m src.app "plan a 150-guest wedding in Bangalore for 8 lakh on 2026-12-18"
"""
from __future__ import annotations

import sys
import uuid

from .config import RUNS_DIR
from .exporters import serialize_state, to_ics, to_markdown
from .logging_utils import console
from .runner import run_planner

SAMPLE = (
    "Plan a wedding in Bangalore for 150 guests with a budget of 8 lakh on "
    "2026-12-18. Outdoor if possible, multi-cuisine food, need photography."
)


def main() -> None:
    # take the request from the command line, else prompt, else use the sample
    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        console.print("[bold]Describe your event[/bold] (press Enter for a sample):")
        request = input("> ").strip() or SAMPLE

    run_id = f"cli-{uuid.uuid4().hex[:8]}"
    result = run_planner(request, thread_id=run_id)

    console.rule("[bold green]RESULT")
    console.print(f"[bold]Status:[/bold] {result.get('status', 'unknown')}\n")
    console.print(result.get("final_message", "(no message)"))

    if result.get("status") == "booked":
        _export(result, run_id)


def _export(result: dict, run_id: str) -> None:
    """Save the booked plan as Markdown + a calendar file next to the traces."""
    RUNS_DIR.mkdir(exist_ok=True)
    state = serialize_state(result)
    md_path = RUNS_DIR / f"plan-{run_id}.md"
    md_path.write_text(to_markdown(state, run_id), encoding="utf-8")
    console.print(f"\n[dim]Saved plan:[/dim] {md_path}")
    try:
        ics_path = RUNS_DIR / f"plan-{run_id}.ics"
        ics_path.write_text(to_ics(state, run_id), encoding="utf-8", newline="")
        console.print(f"[dim]Saved calendar:[/dim] {ics_path}")
    except ValueError as e:
        console.print(f"[dim]{e}[/dim]")


if __name__ == "__main__":
    main()
