"""Token usage + cost tracking per run.

Every structured LLM call reports its token counts here. The tracker lives in a
ContextVar, so concurrent API requests each get their own (asyncio.to_thread
copies the context into the worker thread that runs the graph).
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Dict, Optional

from .config import settings


@dataclass
class UsageTracker:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    retries: int = 0
    by_agent: Dict[str, int] = field(default_factory=dict)  # agent -> total tokens

    def record(self, agent: str, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.by_agent[agent] = self.by_agent.get(agent, 0) + input_tokens + output_tokens

    @property
    def cost_usd(self) -> float:
        return round(
            self.input_tokens / 1e6 * settings.PRICE_INPUT_PER_M
            + self.output_tokens / 1e6 * settings.PRICE_OUTPUT_PER_M,
            6,
        )

    def summary(self) -> dict:
        return {
            "llm_calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "retries": self.retries,
            "estimated_cost_usd": self.cost_usd,
            "by_agent": dict(self.by_agent),
        }


_current: ContextVar[Optional[UsageTracker]] = ContextVar("gatherly_usage", default=None)


def start_tracking() -> UsageTracker:
    """Begin a fresh tracker for the current run (and its worker threads)."""
    tracker = UsageTracker()
    _current.set(tracker)
    return tracker


def current_tracker() -> Optional[UsageTracker]:
    return _current.get()
