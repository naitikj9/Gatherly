"""The run loop that drives the compiled graph, including the HITL pause/resume.

Shared by the CLI (app.py) and the test harness, so the same code path runs in
demos and tests. `decision_fn` lets the caller decide how the human approval is
answered (real keyboard input, or a scripted answer in tests).
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from langgraph.types import Command

from .config import apply_langsmith_env
from .graph import build_graph
from .logging_utils import RunLogger, console, set_active_logger
from .usage import start_tracking


def _interactive_decision(payload: dict) -> str:
    """Default approval handler: show the request and read a keyboard answer."""
    console.print("\n[bold yellow]HUMAN APPROVAL REQUIRED[/bold yellow]")
    console.print(payload["summary"])
    console.print(f"[dim]{payload['action_required']}[/dim]")
    raw = input("Your decision (approve/decline): ")
    # take the first run of ASCII letters so a stray BOM in piped input
    # (e.g. a UTF-8 BOM decoded as "ï») can't corrupt the answer
    match = re.search(r"[a-z]+", raw.lower())
    return match.group(0) if match else "decline"


def run_planner(
    request: str,
    decision_fn: Optional[Callable[[dict], str]] = None,
    thread_id: str = "demo",
    graph=None,
    verbose: bool = True,
    quiet: bool = False,
) -> dict:
    """Run one event-planning request end to end and return the final state.

    Handles the interrupt loop: if the graph pauses for human approval we ask
    `decision_fn` (interactive by default) and resume until it finishes.
    `quiet=True` silences per-step console logs (used by the batch evaluator).
    """
    apply_langsmith_env()
    set_active_logger(RunLogger(thread_id, echo=not quiet))
    tracker = start_tracking()
    graph = graph or build_graph()
    decision_fn = decision_fn or _interactive_decision
    config = {"configurable": {"thread_id": thread_id}}

    if verbose:
        console.rule(f"[bold]Run {thread_id}")
        console.print(f"[bold]Request:[/bold] {request}\n")

    result = graph.invoke({"user_request": request, "log": []}, config)

    # the graph comes back with "__interrupt__" set whenever it paused for a human
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        answer = decision_fn(payload)
        result = graph.invoke(Command(resume=answer), config)

    result["usage"] = tracker.summary()
    return result
