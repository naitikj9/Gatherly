"""The LangGraph: nodes, edges, conditional routing and the human-in-the-loop.

intake screens/parses the request and either refuses or moves on. research
finds vendors (or rejects if no venue fits). planner builds the plan, insights
adds weather/checklist/packages/health score, compliance decides whether to
finalize, reject, or ask a human. If cost is the only problem, compliance first
loops through the budget optimizer (optimizer -> planner -> insights ->
compliance), up to OPTIMIZER_MAX_ATTEMPTS times. human_approval pauses the
graph until the person approves or declines.
"""
from __future__ import annotations

import re
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .agents import (
    compliance_node,
    insights_node,
    intake_node,
    optimizer_node,
    planner_node,
    research_node,
)
from .config import settings
from .formatting import approval_summary, format_plan
from .guardrails import validate_requirements
from .logging_utils import log_step
from .schemas import (
    BudgetLine,
    ChecklistItem,
    ComplianceResult,
    EventPlan,
    EventRequirements,
    HealthFactor,
    HealthScore,
    Insights,
    PlanPackage,
    ScheduleItem,
    VendorChoice,
    VendorShortlist,
    WeatherRisk,
)
from .state import PlannerState


def _make_serializer() -> JsonPlusSerializer:
    """Serializer that knows our Pydantic schemas.

    The checkpointer has to persist the graph state (which holds Pydantic models)
    while the graph is paused for human approval. Listing our types here makes
    that round-trip clean instead of relying on the deprecated allow-everything
    default.
    """
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            EventRequirements,
            VendorChoice,
            VendorShortlist,
            ScheduleItem,
            BudgetLine,
            EventPlan,
            ComplianceResult,
            WeatherRisk,
            ChecklistItem,
            PlanPackage,
            HealthFactor,
            HealthScore,
            Insights,
        ]
    )


def make_sqlite_checkpointer(path):
    """Durable checkpointer: paused (awaiting-approval) plans survive restarts.

    The in-memory default forgets every paused run when the process restarts,
    which would strand plans waiting for a human. SQLite keeps them on disk.
    """
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
    return SqliteSaver(conn, serde=_make_serializer())


# terminal / control nodes

def refusal_node(state: PlannerState) -> dict:
    """End state for out-of-scope or invalid requests."""
    req = state["requirements"]
    if not req.in_scope:
        message = f"Request declined: {req.refusal_reason}"
    else:
        problems = validate_requirements(req)
        message = "I can't plan this yet: " + "; ".join(problems)
    log_step("refusal", message)
    return {"status": "refused", "final_message": message, "log": [f"[refusal] {message}"]}


def reject_node(state: PlannerState) -> dict:
    """End state for a hard violation.

    Reached either when research found no suitable venue (before compliance) or
    when compliance flagged hard violations. Handle both.
    """
    compliance = state.get("compliance")
    if compliance and compliance.violations:
        message = "Plan rejected. " + " ".join(compliance.violations)
        if state.get("optimization_log"):
            message += (" The budget optimizer tried "
                        f"{len(state['optimization_log'])} cheaper swap(s) but "
                        "couldn't bring it within tolerance.")
    else:
        message = (
            "Plan rejected. No venue in the catalog matches the requested city "
            "and guest count, so the event cannot be planned."
        )
    log_step("reject", message)
    return {"status": "rejected", "final_message": message, "log": [f"[reject] {message}"]}


def human_approval_node(state: PlannerState) -> dict:
    """Human-in-the-loop: pause and wait for a person to approve/decline.

    interrupt() suspends the graph and hands `payload` back to the caller. When
    the caller resumes with Command(resume="approve"/"decline"), we re-enter this
    node and interrupt() returns that value.
    """
    payload = {
        "summary": approval_summary(state),
        "action_required": "Approve booking? Reply 'approve' or 'decline'.",
    }
    decision = interrupt(payload)  # graph pauses here on the first run
    # take the first run of ASCII letters, robust to BOM/encoding noise
    match = re.search(r"[a-z]+", str(decision).lower())
    decision = match.group(0) if match else ""
    log_step("human_approval", f"Human responded: {decision}")
    return {"human_decision": decision, "log": [f"[human_approval] {decision}"]}


def declined_node(state: PlannerState) -> dict:
    """End state when the human declines the plan."""
    message = "You declined the plan. Nothing was booked."
    log_step("declined", message)
    return {"status": "declined", "final_message": message, "log": [f"[declined] {message}"]}


def finalize_node(state: PlannerState) -> dict:
    """End state for an approved plan: 'book' it and show the full plan."""
    message = format_plan(
        state["requirements"], state["shortlist"], state["plan"], state["compliance"],
        state.get("insights"), state.get("optimization_log"),
    )
    confirmation = "BOOKED.\n\n" + message
    log_step("finalize", "Plan booked and finalized.")
    return {"status": "booked", "final_message": confirmation, "log": ["[finalize] booked"]}


# routers (conditional edges)

def route_after_intake(state: PlannerState) -> str:
    req = state["requirements"]
    if not req.in_scope or validate_requirements(req):
        return "refuse"
    return "research"


def route_after_research(state: PlannerState) -> str:
    # no venue means the event can't happen, skip straight to reject
    return "planner" if state["shortlist"].venue is not None else "reject"


def route_after_compliance(state: PlannerState) -> str:
    compliance = state["compliance"]
    if (compliance.optimizable
            and not state.get("optimizer_stuck")
            and state.get("optimizer_attempts", 0) < settings.OPTIMIZER_MAX_ATTEMPTS):
        return "optimizer"
    return {
        "approve_auto": "finalize",
        "needs_human": "human_approval",
        "reject": "reject",
    }[state["compliance"].decision]


def route_after_optimizer(state: PlannerState) -> str:
    # nothing cheaper found: re-run compliance, which now routes normally
    return "compliance" if state.get("optimizer_stuck") else "planner"


def route_after_human(state: PlannerState) -> str:
    return "finalize" if state["human_decision"].startswith("approve") else "declined"


def build_graph(checkpointer=None):
    """Build and compile the event-planning graph.

    A checkpointer is required for the human-in-the-loop interrupt to work, since
    the graph has to persist its state while paused. Defaults to in-memory.
    """
    g = StateGraph(PlannerState)

    # agent nodes
    g.add_node("intake", intake_node)
    g.add_node("research", research_node)
    g.add_node("planner", planner_node)
    g.add_node("insights", insights_node)
    g.add_node("compliance", compliance_node)
    g.add_node("optimizer", optimizer_node)
    # control nodes
    g.add_node("refuse", refusal_node)
    g.add_node("reject", reject_node)
    g.add_node("human_approval", human_approval_node)
    g.add_node("declined", declined_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "intake")
    g.add_conditional_edges("intake", route_after_intake,
                            {"research": "research", "refuse": "refuse"})
    g.add_conditional_edges("research", route_after_research,
                            {"planner": "planner", "reject": "reject"})
    g.add_edge("planner", "insights")
    g.add_edge("insights", "compliance")
    g.add_conditional_edges("compliance", route_after_compliance,
                            {"finalize": "finalize", "human_approval": "human_approval",
                             "reject": "reject", "optimizer": "optimizer"})
    g.add_conditional_edges("optimizer", route_after_optimizer,
                            {"planner": "planner", "compliance": "compliance"})
    g.add_conditional_edges("human_approval", route_after_human,
                            {"finalize": "finalize", "declined": "declined"})

    for terminal in ["refuse", "reject", "declined", "finalize"]:
        g.add_edge(terminal, END)

    return g.compile(checkpointer=checkpointer or MemorySaver(serde=_make_serializer()))
