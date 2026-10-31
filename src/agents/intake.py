"""Intake agent.

Turns the user's free-text request into a validated EventRequirements object.
It also does the first guardrail: a keyword screen for unsafe requests, plus an
LLM judgment of whether the request is in scope at all.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..guardrails import screen_request
from ..llm import get_chat_llm, invoke_structured
from ..logging_utils import log_step
from ..schemas import EventRequirements
from ..state import PlannerState
from ..tools.dates import describe_date

_SYSTEM = """You are the Intake agent of an event-planning system.
Extract a structured event brief from the user's request.

Rules:
- Set in_scope=false ONLY if the request is not about planning an event, is
  nonsensical, or asks for something unsafe/illegal. Then give a short
  refusal_reason and leave other fields at defaults.
- Otherwise set in_scope=true and fill every field you can infer.
- budget_inr must be a plain integer in Indian Rupees. Convert shorthand:
  "8 lakh" -> 800000, "1.5 lakh" -> 150000, "50k" -> 50000.
- guest_count is an integer.
- Infer event_type from context (wedding, corporate, birthday, anniversary,
  conference, party, other).
- If the user mentions outdoor/garden/rooftop -> setting_preference="outdoor";
  hall/indoor/AC -> "indoor"; otherwise "any".
- Keep event_date exactly as the user expressed it (ISO if given)."""


def intake_node(state: PlannerState) -> dict:
    request = state["user_request"]

    # deterministic safety screen first, before spending an LLM call
    unsafe = screen_request(request)
    if unsafe:
        req = EventRequirements(in_scope=False, refusal_reason=unsafe)
        msg = log_step("intake", "Request blocked by safety screen.", req)
        return {"requirements": req, "log": [msg]}

    req: EventRequirements = invoke_structured(
        get_chat_llm(), EventRequirements,
        [SystemMessage(content=_SYSTEM), HumanMessage(content=request)], agent="intake",
    )

    # normalize "Dec 18" / "next Saturday" to ISO so availability + checklist work
    if req.in_scope and req.event_date:
        when = describe_date(req.event_date)
        if when["iso"]:
            req.event_date = when["iso"]

    summary = (
        f"{req.event_type} in {req.city or '?'}, {req.guest_count} guests, "
        f"budget ₹{req.budget_inr:,}"
        if req.in_scope
        else f"out of scope: {req.refusal_reason}"
    )
    msg = log_step("intake", f"Parsed request -> {summary}", req)
    return {"requirements": req, "log": [msg]}
