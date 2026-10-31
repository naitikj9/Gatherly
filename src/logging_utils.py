"""Lightweight logging / observability.

Prints each step nicely and also appends a JSON line per step to
runs/trace-*.jsonl, so you can go back and see exactly what every agent saw and
produced. (LangSmith tracing is also available via env vars in config.)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from contextvars import ContextVar
from typing import Any, Optional

from rich.console import Console

from .config import RUNS_DIR
from .guardrails import redact_pii

# Windows terminals often default to cp1252, which can't encode symbols like ₹.
# Force UTF-8 on the standard streams so output doesn't crash on those.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

console = Console()


class RunLogger:
    """Prints readable step logs and saves them as JSON lines."""

    def __init__(self, run_id: str, echo: bool = True) -> None:
        self.run_id = run_id
        self.echo = echo  # print to console? (off during batch evaluation)
        RUNS_DIR.mkdir(exist_ok=True)
        self.path = RUNS_DIR / f"trace-{run_id}.jsonl"

    def step(self, node: str, message: str, data: Any | None = None) -> str:
        """Log one node's activity. Returns the message (handy for state['log'])."""
        stamp = datetime.now().strftime("%H:%M:%S")
        if self.echo:
            console.print(f"[dim]{stamp}[/dim] [bold cyan]{node}[/bold cyan]: {message}")
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "node": node,
            "message": message,
            "data": _safe(data),
        }
        # traces outlive the run, so personal details never reach disk
        line = redact_pii(json.dumps(record, ensure_ascii=False))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return f"[{node}] {message}"


# We keep one "active" logger per run instead of putting it in the graph state,
# because the state gets serialized by the checkpointer and a logger object
# isn't serialisable. It lives in a ContextVar so concurrent API requests never
# write into each other's trace (asyncio.to_thread copies the context).
_active: ContextVar[Optional[RunLogger]] = ContextVar("gatherly_run_logger", default=None)


def set_active_logger(logger: RunLogger) -> None:
    _active.set(logger)


def log_step(node: str, message: str, data: Any | None = None) -> str:
    """Log via the active run logger (or just print if none is set)."""
    logger = _active.get()
    if logger is not None:
        return logger.step(node, message, data)
    console.print(f"[bold cyan]{node}[/bold cyan]: {message}")
    return f"[{node}] {message}"


def _safe(data: Any) -> Any:
    """Make pydantic / arbitrary objects JSON-serialisable for the trace file."""
    if data is None:
        return None
    if hasattr(data, "model_dump"):
        return data.model_dump()
    try:
        json.dumps(data)
        return data
    except (TypeError, ValueError):
        return str(data)
