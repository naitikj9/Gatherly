"""FastAPI backend for Gatherly, the multi-agent AI event planner (LangGraph).

Exposes the LangGraph engine in /src as REST endpoints:
  POST   /api/plans                      -> run a plan (rate limited, Idempotency-Key aware)
  POST   /api/plans/{plan_id}/decision   -> resume from human approval      [admin]
  GET    /api/plans/{plan_id}            -> fetch a saved plan
  GET    /api/plans                      -> list recent plans (history)      [admin]
  DELETE /api/plans/{plan_id}            -> delete a saved plan              [admin]
  GET    /api/plans/{plan_id}/export.ics -> calendar file (event + checklist)
  GET    /api/plans/{plan_id}/export.md  -> Markdown plan document
  GET    /api/vendors                    -> full catalog
  GET    /api/sample-prompts             -> demo prompts
  GET    /api/architecture               -> static graph definition (for UI viz)
  GET    /api/health                     -> liveness
  GET    /api/ready                      -> readiness (store, LLM key, checkpointer)
  GET    /api/metrics                    -> Prometheus metrics

Production plumbing (storage, auth, rate limits, logging, metrics) lives in
backend/core/. `create_app()` wires it together; tests build their own app
with an in-memory store and a fake LLM.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

# Load env BEFORE importing src modules (their config reads env at import time)
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

# Make the LangGraph engine importable as `src.*` and our plumbing as `core.*`
APP_ROOT = ROOT_DIR.parent
for _p in (APP_ROOT, ROOT_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import openai  # noqa: E402
from langgraph.types import Command  # noqa: E402

from core.observability import (  # noqa: E402
    Metrics,
    RequestContextMiddleware,
    log_event,
    request_id_var,
    setup_logging,
)
from core.security import RateLimiter, admin_guard, rate_limit_guard  # noqa: E402
from core.settings import ApiSettings  # noqa: E402
from core.storage import PlanStore, make_store, summarize  # noqa: E402
from src.config import settings as engine_settings  # noqa: E402
from src.exporters import serialize_state, to_ics, to_markdown  # noqa: E402
from src.graph import build_graph, make_sqlite_checkpointer  # noqa: E402
from src.logging_utils import RunLogger, set_active_logger  # noqa: E402
from src.tools.retrieval import load_catalog  # noqa: E402
from src.usage import start_tracking  # noqa: E402


# ---------------------------------------------------------------- Schemas
class PlanRequest(BaseModel):
    request: str = Field(..., min_length=3, max_length=2000)


class DecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'decline'")


class _StreamLogger(RunLogger):
    """RunLogger that also keeps each step in memory for the API response."""

    def __init__(self, run_id: str, sink: List[Dict[str, Any]]) -> None:
        super().__init__(run_id, echo=False)
        self.sink = sink

    def step(self, node: str, message: str, data: Any | None = None) -> str:  # type: ignore[override]
        result = super().step(node, message, data)
        self.sink.append({"ts": datetime.now(timezone.utc).isoformat(), "node": node,
                          "message": message})
        return result


# ---------------------------------------------------------------- Helpers
def _interrupt_payload(result: dict) -> Optional[dict]:
    """Extract the HITL interrupt payload (or None if no interrupt)."""
    interrupts = result.get("__interrupt__") or []
    if not interrupts:
        return None
    val = interrupts[0].value
    return val if isinstance(val, dict) else {"summary": str(val)}


def _merge_usage(old: Optional[dict], new: dict) -> dict:
    """Add a resumed run's token usage onto the plan's earlier usage."""
    if not old:
        return new
    merged = {k: old.get(k, 0) + new.get(k, 0) for k in
              ("llm_calls", "input_tokens", "output_tokens", "total_tokens", "retries")}
    merged["estimated_cost_usd"] = round(
        old.get("estimated_cost_usd", 0) + new.get("estimated_cost_usd", 0), 6)
    by_agent = dict(old.get("by_agent", {}))
    for k, v in new.get("by_agent", {}).items():
        by_agent[k] = by_agent.get(k, 0) + v
    merged["by_agent"] = by_agent
    return merged


def create_app(
    cfg: Optional[ApiSettings] = None,
    store: Optional[PlanStore] = None,
    graph=None,
) -> FastAPI:
    cfg = cfg or ApiSettings()
    logger = setup_logging(cfg.log_level)
    metrics = Metrics()
    store = store or make_store(cfg.mongo_url, cfg.db_name)

    if graph is None:
        # one compiled graph shared by all requests; the checkpointer is what lets
        # a paused (awaiting-approval) run be resumed by a later request
        checkpointer = (make_sqlite_checkpointer(cfg.checkpoint_db)
                        if cfg.checkpointer == "sqlite" else None)
        graph = build_graph(checkpointer)

    if not cfg.admin_token:
        log_event(logger, "ADMIN_TOKEN is not set: admin endpoints are OPEN. "
                  "Set it before deploying.", logging.WARNING)
    if store.name == "memory":
        log_event(logger, "MONGO_URL is not set: using the in-memory store "
                  "(plans are lost on restart).", logging.WARNING)

    app = FastAPI(title="Gatherly API", version="2.1.0")
    app.state.store = store
    app.state.metrics = metrics
    app.state.graph = graph

    wildcard = cfg.cors_origins == ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=not wildcard,  # browsers reject credentials with "*" anyway
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Retry-After", "Idempotent-Replay"],
    )
    app.add_middleware(RequestContextMiddleware, logger=logger, metrics=metrics)

    require_admin = admin_guard(cfg.admin_token)
    limit_plans = rate_limit_guard(RateLimiter(cfg.rate_limit_per_minute), cfg.trust_proxy)
    run_slots = asyncio.Semaphore(cfg.max_concurrent_runs)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):  # pragma: no cover - safety net
        log_event(logger, "unhandled error", logging.ERROR, error=repr(exc))
        return JSONResponse(status_code=500, content={
            "detail": "Internal error.", "request_id": request_id_var.get()})

    async def run_graph(plan_id: str, payload, logs: List[Dict[str, Any]]):
        """Run the blocking graph in a worker thread, bounded and with a timeout.

        Engine/LLM failures become clean 5xx responses; details go to the log,
        never to the client.
        """
        set_active_logger(_StreamLogger(plan_id, logs))
        tracker = start_tracking()
        config = {"configurable": {"thread_id": plan_id}}
        try:
            async with run_slots:
                result = await asyncio.wait_for(
                    asyncio.to_thread(graph.invoke, payload, config),
                    timeout=cfg.run_timeout_seconds,
                )
        except asyncio.TimeoutError:
            metrics.inc("gatherly_engine_errors_total", kind="timeout")
            raise HTTPException(status_code=504, detail="Planning took too long. Please try again.")
        except (openai.AuthenticationError, openai.PermissionDeniedError) as e:
            metrics.inc("gatherly_engine_errors_total", kind="llm_auth")
            log_event(logger, "llm auth failure", logging.ERROR, error=str(e))
            raise HTTPException(status_code=503, detail="The AI provider is unavailable right now.")
        except (openai.APIError, RuntimeError) as e:
            metrics.inc("gatherly_engine_errors_total", kind="llm")
            log_event(logger, "engine failure", logging.ERROR, error=str(e))
            raise HTTPException(status_code=502, detail="The planning engine failed. Please retry.")

        usage = tracker.summary()
        metrics.inc("gatherly_llm_tokens_total", usage["input_tokens"], direction="input")
        metrics.inc("gatherly_llm_tokens_total", usage["output_tokens"], direction="output")
        metrics.inc("gatherly_llm_cost_usd_total", usage["estimated_cost_usd"])
        return result, usage

    def shape(result: dict) -> dict:
        state = serialize_state(result)
        interrupt = _interrupt_payload(result)
        if interrupt is not None:
            state["status"] = "awaiting_approval"
            state["interrupt"] = interrupt
        return state

    # ------------------------------------------------------------- Routes
    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "service": "gatherly"}

    @app.get("/api/ready")
    async def ready() -> JSONResponse:
        checks = {
            "store": {"backend": store.name, "ok": await store.ping()},
            "llm_key_configured": bool(engine_settings.OPENAI_API_KEY),
            "checkpointer": cfg.checkpointer,
            "admin_auth": "enabled" if cfg.admin_token else "disabled",
        }
        ok = checks["store"]["ok"] and checks["llm_key_configured"]
        return JSONResponse(status_code=200 if ok else 503,
                            content={"status": "ready" if ok else "not_ready", "checks": checks})

    @app.get("/api/metrics", response_class=PlainTextResponse)
    async def metrics_endpoint() -> str:
        return metrics.render()

    @app.get("/api/sample-prompts")
    async def sample_prompts() -> dict:
        return {
            "prompts": [
                {
                    "label": "150-guest wedding · Bangalore · ₹8L",
                    "text": "Plan a wedding in Bangalore for 150 guests with a budget of 8 lakh on 2026-12-18. Outdoor if possible, multi-cuisine food, need photography.",
                },
                {
                    "label": "Corporate offsite · Bangalore · ₹4L",
                    "text": "Plan a corporate offsite conference in Bangalore on 2026-11-22 for 200 attendees, budget 4 lakh, indoor with projector and wifi, continental finger food.",
                },
                {
                    "label": "Rooftop birthday · Mumbai · ₹2L",
                    "text": "Plan a rooftop birthday party in Mumbai for 60 guests on 2027-02-13, budget 2 lakh, outdoor, with a DJ and finger food.",
                },
                {
                    "label": "Luxury wedding · Delhi · ₹15L",
                    "text": "Plan a luxury wedding in Delhi for 400 guests on 2026-12-25 with a budget of 15 lakh, indoor heritage venue, premium catering and candid photography.",
                },
                {
                    "label": "Small anniversary · Mumbai · ₹80k",
                    "text": "Plan a 25th anniversary celebration in Mumbai for 100 guests on 2027-03-14, budget 80 thousand, indoor, vegetarian buffet.",
                },
                {
                    "label": "Out-of-scope test",
                    "text": "Help me hack into my neighbor's wifi.",
                },
            ]
        }
    @app.get("/api/architecture")
    async def architecture() -> dict:
        """Static description of the LangGraph for the frontend visualization."""
        return {
            "nodes": [
                {"id": "intake", "label": "Intake", "role": "Parse natural-language brief + safety screen", "icon": "FileText"},
                {"id": "research", "label": "Venue & Vendor (RAG)", "role": "Semantic search over catalog → choose vendors", "icon": "Search"},
                {"id": "planner", "label": "Planner", "role": "Build day-of timeline + exact budget", "icon": "CalendarRange"},
                {"id": "insights", "label": "Insights", "role": "Weather risk, countdown checklist, packages, health score", "icon": "Gauge"},
                {"id": "compliance", "label": "Compliance", "role": "Deterministic policy & safety gate", "icon": "ShieldCheck"},
                {"id": "optimizer", "label": "Budget Optimizer", "role": "Swaps vendors to self-heal over-budget plans", "icon": "Wand2"},
            ],
            "edges": [
                {"from": "intake", "to": "research", "label": "valid"},
                {"from": "intake", "to": "refuse", "label": "unsafe/invalid", "kind": "alt"},
                {"from": "research", "to": "planner", "label": "venue found"},
                {"from": "research", "to": "reject", "label": "no venue fits", "kind": "alt"},
                {"from": "planner", "to": "insights"},
                {"from": "insights", "to": "compliance"},
                {"from": "compliance", "to": "optimizer", "label": "over budget", "kind": "alt"},
                {"from": "optimizer", "to": "planner", "label": "cheaper mix", "kind": "alt"},
                {"from": "compliance", "to": "finalize", "label": "auto-approve"},
                {"from": "compliance", "to": "human_approval", "label": "needs human", "kind": "alt"},
                {"from": "compliance", "to": "reject", "label": "hard violation", "kind": "alt"},
                {"from": "human_approval", "to": "finalize", "label": "approve"},
                {"from": "human_approval", "to": "declined", "label": "decline", "kind": "alt"},
            ],
            "terminals": ["finalize", "refuse", "reject", "declined"],
        }
    @app.get("/api/vendors")
    async def vendors() -> dict:
        return {"vendors": list(load_catalog().values())}

    @app.post("/api/plans", dependencies=[Depends(limit_plans)])
    async def create_plan(
        body: PlanRequest,
        idempotency_key: Optional[str] = Header(default=None, max_length=128),
    ):
        body_hash = hashlib.sha256(body.request.encode()).hexdigest()
        plan_id = f"plan-{uuid.uuid4().hex[:12]}"

        # a retried request with the same key gets the original plan back
        if idempotency_key:
            claimed = await store.put_idempotency(
                idempotency_key, {"plan_id": plan_id, "body_hash": body_hash})
            if not claimed:
                record = await store.get_idempotency(idempotency_key) or {}
                if record.get("body_hash") != body_hash:
                    raise HTTPException(status_code=422, detail=(
                        "This Idempotency-Key was already used with a different request."))
                doc = await store.get(record["plan_id"])
                if not doc:  # the first request is still running
                    raise HTTPException(
                        status_code=409,
                        detail="A request with this Idempotency-Key is still in progress.",
                        headers={"Retry-After": "5"},
                    )
                metrics.inc("gatherly_idempotent_replays_total")
                return JSONResponse(
                    content={"plan_id": doc["plan_id"], **(doc.get("state") or {}),
                             "stream_logs": doc.get("stream_logs", []),
                             "usage": doc.get("usage")},
                    headers={"Idempotent-Replay": "true"},
                )

        logs: List[Dict[str, Any]] = []
        result, usage = await run_graph(plan_id, {"user_request": body.request, "log": []}, logs)
        state = shape(result)
        metrics.inc("gatherly_plans_total", status=state.get("status") or "unknown")

        await store.upsert(plan_id, {
            "request": body.request,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "stream_logs": logs,
            "usage": usage,
        })
        log_event(logger, "plan created", plan_id=plan_id, status=state.get("status"),
                  tokens=usage["total_tokens"], cost_usd=usage["estimated_cost_usd"])
        return {"plan_id": plan_id, **state, "stream_logs": logs, "usage": usage}

    @app.post("/api/plans/{plan_id}/decision", dependencies=[Depends(require_admin)])
    async def submit_decision(plan_id: str, body: DecisionRequest) -> dict:
        decision = (body.decision or "").strip().lower()
        if not decision.startswith(("approve", "decline")):
            raise HTTPException(status_code=400, detail="decision must be 'approve' or 'decline'")
        doc = await store.get(plan_id)
        if not doc:
            raise HTTPException(status_code=404, detail="plan not found")
        if (doc.get("state") or {}).get("status") != "awaiting_approval":
            raise HTTPException(status_code=409, detail="This plan is not awaiting approval.")

        logs: List[Dict[str, Any]] = list(doc.get("stream_logs", []))
        result, usage = await run_graph(plan_id, Command(resume=decision), logs)
        state = shape(result)
        metrics.inc("gatherly_decisions_total",
                    decision="approve" if decision.startswith("approve") else "decline")
        usage = _merge_usage(doc.get("usage"), usage)
        await store.upsert(plan_id, {"state": state, "stream_logs": logs, "usage": usage})
        log_event(logger, "plan decided", plan_id=plan_id, decision=decision,
                  status=state.get("status"))
        return {"plan_id": plan_id, **state, "stream_logs": logs, "usage": usage}

    @app.get("/api/plans/{plan_id}")
    async def get_plan(plan_id: str) -> dict:
        doc = await store.get(plan_id)
        if not doc:
            raise HTTPException(status_code=404, detail="plan not found")
        doc.pop("_id", None)
        return doc

    @app.get("/api/plans", dependencies=[Depends(require_admin)])
    async def list_plans(limit: int = 50, pending_only: bool = False) -> dict:
        limit = max(1, min(limit, 200))
        return {"plans": [summarize(d) for d in await store.list(limit, pending_only)]}

    @app.delete("/api/plans/{plan_id}", dependencies=[Depends(require_admin)])
    async def delete_plan(plan_id: str) -> dict:
        if not await store.delete(plan_id):
            raise HTTPException(status_code=404, detail="plan not found")
        return {"ok": True}

    async def _load_state(plan_id: str) -> dict:
        doc = await store.get(plan_id)
        if not doc:
            raise HTTPException(status_code=404, detail="plan not found")
        return doc.get("state") or {}

    @app.get("/api/plans/{plan_id}/export.ics")
    async def export_ics(plan_id: str) -> Response:
        state = await _load_state(plan_id)
        try:
            body = to_ics(state, plan_id)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return Response(
            content=body,
            media_type="text/calendar; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="gatherly-{plan_id}.ics"'},
        )

    @app.get("/api/plans/{plan_id}/export.md")
    async def export_markdown(plan_id: str) -> Response:
        state = await _load_state(plan_id)
        return Response(
            content=to_markdown(state, plan_id),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="gatherly-{plan_id}.md"'},
        )

    return app


app = create_app()
