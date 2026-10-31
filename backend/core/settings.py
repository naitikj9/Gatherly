"""API settings, read once from the environment.

Everything has a safe local-dev default, so `uvicorn server:app` works with no
config at all (in-memory store, SQLite checkpoints, auth off). Production sets
MONGO_URL, ADMIN_TOKEN and CORS_ORIGINS.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

APP_ROOT = Path(__file__).resolve().parents[2]


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _list(name: str, default: str) -> List[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass
class ApiSettings:
    mongo_url: str = field(default_factory=lambda: os.getenv("MONGO_URL", ""))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "gatherly"))

    # "sqlite" keeps paused plans across restarts; "memory" is for tests
    checkpointer: str = field(default_factory=lambda: os.getenv("CHECKPOINTER", "sqlite"))
    checkpoint_db: str = field(default_factory=lambda: os.getenv(
        "CHECKPOINT_DB", str(APP_ROOT / "data" / "checkpoints.sqlite")))

    # empty = admin endpoints are open (local dev only; logged loudly)
    admin_token: str = field(default_factory=lambda: os.getenv("ADMIN_TOKEN", ""))
    cors_origins: List[str] = field(default_factory=lambda: _list("CORS_ORIGINS", "*"))
    trust_proxy: bool = field(default_factory=lambda: os.getenv("TRUST_PROXY", "false").lower() == "true")

    rate_limit_per_minute: int = field(default_factory=lambda: _int("RATE_LIMIT_PER_MINUTE", 10))
    max_concurrent_runs: int = field(default_factory=lambda: _int("MAX_CONCURRENT_RUNS", 4))
    run_timeout_seconds: int = field(default_factory=lambda: _int("RUN_TIMEOUT_SECONDS", 120))

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
