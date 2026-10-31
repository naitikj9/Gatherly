"""Planner agent.

Builds the actual plan. The budget is computed by the budget tool (never the
LLM); the timeline and summary are written by the LLM, grounded in the chosen
vendors.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_chat_llm, invoke_structured
from ..logging_utils import log_step
from ..schemas import BudgetLine, EventPlan, EventRequirements, VendorShortlist
from ..state import PlannerState
from ..tools import calculate_budget

_SYSTEM = """You are the Planner agent. Produce a realistic event-day timeline
(4-7 schedule items with times) and a one-paragraph summary, based on the event
type and chosen vendors. Do NOT compute budgets, that is given to you. Return
only the timeline and summary fields meaningfully; leave budget fields empty."""


def _vendor_ids(shortlist: VendorShortlist) -> dict:
    """Collect category -> id pairs, skipping empty categories."""
    pairs = {
        "venue": shortlist.venue,
        "caterer": shortlist.caterer,
        "decorator": shortlist.decorator,
        "entertainment": shortlist.entertainment,
        "photographer": shortlist.photographer,
    }
    return {cat: choice.id for cat, choice in pairs.items() if choice is not None}


def planner_node(state: PlannerState) -> dict:
    req: EventRequirements = state["requirements"]
    shortlist: VendorShortlist = state["shortlist"]

    # exact, auditable budget from the catalog prices
    ids = _vendor_ids(shortlist)
    budget = calculate_budget.invoke({"vendor_ids": ids, "guest_count": req.guest_count})
    log_step("planner", f"Budget tool total ₹{budget['total_cost_inr']:,}", budget)

    # LLM writes the timeline + summary, grounded in the chosen vendors
    chosen = {cat: (c.name if (c := getattr(shortlist, cat)) else None)
              for cat in ["venue", "caterer", "decorator", "entertainment", "photographer"]}
    human = (
        f"Event: {req.event_type} in {req.city} on {req.event_date} for "
        f"{req.guest_count} guests.\nChosen vendors: {chosen}\n"
        "Write the day-of timeline and a short summary."
    )
    drafted: EventPlan = invoke_structured(
        get_chat_llm(temperature=0.3), EventPlan,
        [SystemMessage(content=_SYSTEM), HumanMessage(content=human)], agent="planner",
    )

    # stitch the deterministic budget onto the LLM's timeline/summary
    plan = EventPlan(
        timeline=drafted.timeline,
        summary=drafted.summary,
        budget_breakdown=[BudgetLine(**line) for line in budget["breakdown"]],
        total_cost_inr=budget["total_cost_inr"],
    )
    msg = log_step("planner", f"Plan ready: {len(plan.timeline)} timeline items.", plan)
    return {"plan": plan, "log": [msg]}
