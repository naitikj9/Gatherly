"""Request IDs, structured JSON logs, security headers and Prometheus metrics.

Every response carries an `X-Request-ID` (echoed from the client or generated),
every request is logged as one JSON line, and `/api/metrics` exposes counters
and a latency histogram in Prometheus text format, with no extra dependency.
"""
from __future__ import annotations

import json
import logging
import sys
import threading
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        payload.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("gatherly")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level)
    return logger


def log_event(logger: logging.Logger, msg: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, msg, extra={"extra_fields": fields})


# ------------------------------------------------------------------ metrics

_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120)


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: Dict[Tuple[str, Tuple], float] = defaultdict(float)
        self.hist: Dict[Tuple, list] = {}  # labels -> [bucket counts..., sum, count]

    def inc(self, name: str, value: float = 1.0, **labels) -> None:
        with self._lock:
            self.counters[(name, tuple(sorted(labels.items())))] += value

    def observe(self, seconds: float, **labels) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            row = self.hist.setdefault(key, [0] * len(_BUCKETS) + [0.0, 0])
            for i, b in enumerate(_BUCKETS):
                if seconds <= b:
                    row[i] += 1
            row[-2] += seconds
            row[-1] += 1

    @staticmethod
    def _labels(pairs) -> str:
        if not pairs:
            return ""
        inner = ",".join(f'{k}="{str(v).replace(chr(34), "")}"' for k, v in pairs)
        return "{" + inner + "}"

    def render(self) -> str:
        lines = []
        with self._lock:
            names = sorted({name for name, _ in self.counters})
            for name in names:
                lines.append(f"# TYPE {name} counter")
                for (n, labels), value in sorted(self.counters.items()):
                    if n == name:
                        lines.append(f"{name}{self._labels(labels)} {value:g}")
            if self.hist:
                name = "gatherly_http_request_duration_seconds"
                lines.append(f"# TYPE {name} histogram")
                for labels, row in sorted(self.hist.items()):
                    for i, b in enumerate(_BUCKETS):
                        lines.append(f"{name}_bucket{self._labels(labels + (('le', b),))} {row[i]}")
                    lines.append(f"{name}_bucket{self._labels(labels + (('le', '+Inf'),))} {row[-1]}")
                    lines.append(f"{name}_sum{self._labels(labels)} {row[-2]:.6f}")
                    lines.append(f"{name}_count{self._labels(labels)} {row[-1]}")
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------- middleware

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger, metrics: Metrics) -> None:
        super().__init__(app)
        self.logger = logger
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if 0 < len(incoming) <= 64 and incoming.isprintable() else uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            path = getattr(route, "path", "unmatched")  # template, keeps label cardinality low
            self.metrics.inc("gatherly_http_requests_total", method=request.method,
                             route=path, status=status)
            self.metrics.observe(elapsed, route=path)
            log_event(self.logger, "request", method=request.method, path=request.url.path,
                      route=path, status=status, duration_ms=round(elapsed * 1000, 1))
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        for k, v in _SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response
