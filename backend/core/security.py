"""Admin authentication and rate limiting.

Admin endpoints (approve/decline, delete, list everyone's plans) need the
ADMIN_TOKEN, sent as `X-Admin-Token: <token>` or `Authorization: Bearer <token>`.
Plan creation is rate limited per client IP with a sliding window, so one
client can't burn through the LLM budget.
"""
from __future__ import annotations

import hmac
import math
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Optional

from fastapi import HTTPException, Request


def client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _presented_token(request: Request) -> str:
    token = request.headers.get("x-admin-token", "")
    auth = request.headers.get("authorization", "")
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:]
    return token.strip()


def is_admin(request: Request, expected: str) -> bool:
    """True if the request carries the admin token (or none is configured: dev mode)."""
    if not expected:
        return True
    presented = _presented_token(request)
    # constant-time compare so the token can't be guessed byte by byte
    return bool(presented) and hmac.compare_digest(presented.encode(), expected.encode())


def admin_guard(expected: str) -> Callable[[Request], None]:
    """FastAPI dependency. With no token configured, admin access is open (dev mode)."""

    def check(request: Request) -> None:
        if not is_admin(request, expected):
            raise HTTPException(
                status_code=401,
                detail="Admin token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return check


class RateLimiter:
    """Sliding-window limiter: at most `limit` hits per `window` seconds per key."""

    def __init__(self, limit: int, window: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> Optional[int]:
        """Record a hit. Returns None if allowed, else seconds until the next slot."""
        if self.limit <= 0:
            return None
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, math.ceil(self.window - (now - hits[0])))
            hits.append(now)
            if len(self._hits) > 10_000:  # don't grow forever under a scan
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return None


def rate_limit_guard(limiter: RateLimiter, trust_proxy: bool,
                     what: str = "plan requests") -> Callable[[Request], None]:
    def check(request: Request) -> None:
        retry_after = limiter.hit(client_ip(request, trust_proxy))
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail=f"Too many {what}. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return check
