"""App configuration.

Loads the .env file once and keeps all the settings in one place so we don't
have os.getenv() calls scattered everywhere.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
KNOWLEDGE_BASE = DATA_DIR / "knowledge_base" / "vendors.json"
RUNS_DIR = ROOT_DIR / "runs"  # trace logs go here

# real env vars win over the .env file
load_dotenv(ROOT_DIR / ".env", override=False)


class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    EMBED_MODEL: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # optional LangSmith tracing
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "multiagent-event-planner")

    # budget / guardrail thresholds
    BUDGET_HARD_OVERAGE: float = 0.0
    HUMAN_APPROVAL_COST_INR: int = 200000  # anything above this needs a human to approve
    MIN_GUESTS: int = 1
    MAX_GUESTS: int = 2000
    MIN_BUDGET_INR: int = 10000
    OPTIMIZER_MAX_ATTEMPTS: int = 2  # how many times the budget optimizer may loop

    # LLM resilience + cost tracking
    LLM_MAX_ATTEMPTS: int = int(os.getenv("LLM_MAX_ATTEMPTS", "3"))
    # USD per 1M tokens; defaults are gpt-4o-mini list prices
    PRICE_INPUT_PER_M: float = float(os.getenv("LLM_PRICE_INPUT_PER_M", "0.15"))
    PRICE_OUTPUT_PER_M: float = float(os.getenv("LLM_PRICE_OUTPUT_PER_M", "0.60"))
    MAX_REQUEST_CHARS: int = 2000


settings = Settings()


def apply_langsmith_env() -> None:
    """Turn LangChain tracing env vars on/off based on our settings."""
    if settings.LANGCHAIN_TRACING_V2 and os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
