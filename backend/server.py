"""FastAPI backend for Gatherly, the multi-agent AI event planner (LangGraph).

Exposes the existing /app/src LangGraph engine as REST endpoints:
  POST   /api/plans                     -> start a plan run (returns full state)
  POST   /api/plans/{plan_id}/decision  -> resume from human-approval interrupt
  GET    /api/plans/{plan_id}           -> fetch a saved plan
  GET    /api/plans                     -> list recent plans (history)
  DELETE /api/plans/{plan_id}           -> delete a saved plan
  GET    /api/plans/{plan_id}/export.ics -> calendar file (event + checklist)
  GET    /api/plans/{plan_id}/export.md  -> Markdown plan document
  GET    /api/vendors                   -> full catalog
  GET    /api/sample-prompts            -> demo prompts
  GET    /api/architecture              -> static graph definition (for UI viz)
  GET    /api/health                    -> health check
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

# Load env BEFORE importing src modules (their config reads env at import time)
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

# Make the original LangGraph engine importable as `src.*`
APP_ROOT = ROOT_DIR.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from langgraph.types import Command  # noqa: E402

from src.exporters import serialize_state, to_ics, to_markdown  # noqa: E402
from src.graph import build_graph  # noqa: E402
from src.tools.retrieval import load_catalog  # noqa: E402
from src.logging_utils import RunLogger, set_active_logger  # noqa: E402


# ---------------------------------------------------------------- Mongo setup
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client[DB_NAME]
plans_collection = db["plans"]


# ---------------------------------------------------------------- App + Graph
app = FastAPI(title="Gatherly API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single compiled graph + in-memory checkpointer shared across requests.
# Required so the HITL interrupt can be resumed in a follow-up POST.
GRAPH = build_graph()

# Per-run streaming logger buffer (for in-process polling/history during a run)
_run_logs: Dict[str, List[Dict[str, Any]]] = {}


class _StreamLogger(RunLogger):
    """RunLogger that also appends each step to an in-memory list."""

    def step(self, node: str, message: str, data: Any | None = None) -> str:  # type: ignore[override]
        result = super().step(node, message, data)
        ts = datetime.now(timezone.utc).isoformat()
        _run_logs.setdefault(self.run_id, []).append(
            {"ts": ts, "node": node, "message": message}
        )
        return result


# ---------------------------------------------------------------- Schemas
class PlanRequest(BaseModel):
    request: str = Field(..., min_length=3, max_length=2000)


class DecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'decline'")


# ---------------------------------------------------------------- Helpers
def _serialize_state(state: dict) -> dict:
    """Pydantic-aware → plain dict for JSON response / Mongo persistence."""
    return serialize_state(state)


def _interrupt_payload(result: dict) -> Optional[dict]:
    """Extract the HITL interrupt payload (or None if no interrupt)."""
    if "__interrupt__" not in result:
        return None
    interrupts = result["__interrupt__"]
    if not interrupts:
        return None
    val = interrupts[0].value
    return val if isinstance(val, dict) else {"summary": str(val)}


async def _persist(plan_id: str, doc: dict) -> None:
    doc = {**doc, "plan_id": plan_id, "updated_at": datetime.now(timezone.utc).isoformat()}
    await plans_collection.update_one(
        {"plan_id": plan_id}, {"$set": doc}, upsert=True
    )


async def _invoke_graph(payload, config) -> dict:
    """Run the (blocking) compiled graph in a worker thread."""
    return await asyncio.to_thread(GRAPH.invoke, payload, config)


# ---------------------------------------------------------------- Routes
@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "service": "gatherly"}


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
    catalog = load_catalog()
    return {"vendors": list(catalog.values())}


@app.post("/api/plans")
async def create_plan(body: PlanRequest) -> dict:
    plan_id = f"plan-{uuid.uuid4().hex[:10]}"
    _run_logs[plan_id] = []
    set_active_logger(_StreamLogger(plan_id, echo=False))

    config = {"configurable": {"thread_id": plan_id}}
    try:
        result = await _invoke_graph(
            {"user_request": body.request, "log": []}, config
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Engine error: {e}")

    state = _serialize_state(result)
    interrupt = _interrupt_payload(result)

    if interrupt is not None:
        state["status"] = "awaiting_approval"
        state["interrupt"] = interrupt

    doc = {
        "plan_id": plan_id,
        "request": body.request,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state": state,
        "stream_logs": _run_logs.get(plan_id, []),
    }
    await _persist(plan_id, doc)
    return {"plan_id": plan_id, **state, "stream_logs": _run_logs.get(plan_id, [])}


@app.post("/api/plans/{plan_id}/decision")
async def submit_decision(plan_id: str, body: DecisionRequest) -> dict:
    decision = (body.decision or "").strip().lower()
    if not decision.startswith(("approve", "decline")):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'decline'")

    set_active_logger(_StreamLogger(plan_id, echo=False))
    config = {"configurable": {"thread_id": plan_id}}
    try:
        result = await _invoke_graph(Command(resume=decision), config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume error: {e}")

    state = _serialize_state(result)
    interrupt = _interrupt_payload(result)
    if interrupt is not None:
        state["status"] = "awaiting_approval"
        state["interrupt"] = interrupt

    doc = {
        "plan_id": plan_id,
        "state": state,
        "stream_logs": _run_logs.get(plan_id, []),
    }
    await _persist(plan_id, doc)
    return {"plan_id": plan_id, **state, "stream_logs": _run_logs.get(plan_id, [])}


@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str) -> dict:
    doc = await plans_collection.find_one({"plan_id": plan_id})
    if not doc:
        raise HTTPException(status_code=404, detail="plan not found")
    doc.pop("_id", None)
    return doc


@app.get("/api/plans")
async def list_plans(limit: int = 50, pending_only: bool = False) -> dict:
    query = {"state.status": "awaiting_approval"} if pending_only else {}
    cursor = plans_collection.find(query, {"_id": 0}).sort("updated_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    summary = [
        {
            "plan_id": d["plan_id"],
            "request": d.get("request", ""),
            "status": (d.get("state") or {}).get("status"),
            "city": ((d.get("state") or {}).get("requirements") or {}).get("city"),
            "event_type": ((d.get("state") or {}).get("requirements") or {}).get("event_type"),
            "total_cost_inr": ((d.get("state") or {}).get("plan") or {}).get("total_cost_inr"),
            "budget_inr": ((d.get("state") or {}).get("requirements") or {}).get("budget_inr"),
            "guest_count": ((d.get("state") or {}).get("requirements") or {}).get("guest_count"),
            "health_score": (((d.get("state") or {}).get("insights") or {}).get("health") or {}).get("score"),
            "updated_at": d.get("updated_at"),
        }
        for d in items
    ]
    return {"plans": summary}


@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str) -> dict:
    res = await plans_collection.delete_one({"plan_id": plan_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"ok": True}


async def _load_state(plan_id: str) -> dict:
    doc = await plans_collection.find_one({"plan_id": plan_id}, {"_id": 0})
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
