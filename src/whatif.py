"""What-if simulator: re-price a finished plan for a different guest count,
budget or setting, without calling the LLM.

It answers "what if we invite 50 more people?" or "what if we cut the budget
to 6 lakh?" in milliseconds, using the same deterministic tools the agents
use: the current vendor mix is re-costed, the venue is checked against the new
headcount, and fresh Lean / Balanced / Luxe packages are built for the new
numbers.
"""
from __future__ import annotations

from typing import Dict, Optional

from .tools.packages import CATEGORIES, build_packages, total_for
from .tools.retrieval import load_catalog


def _inr(n: int) -> str:
    """Indian digit grouping, like the web app shows it: 1300000 -> ₹13,00,000."""
    s = str(abs(int(n)))
    head, tail = s[:-3], s[-3:]
    while len(head) > 2:
        tail = f"{head[-2:]},{tail}"
        head = head[:-2]
    return f"₹{head + ',' if head else ''}{tail}"


def _current_vendor_ids(shortlist: dict) -> Dict[str, str]:
    ids = {}
    for cat in CATEGORIES:
        choice = (shortlist or {}).get(cat)
        if choice and choice.get("id"):
            ids[cat] = choice["id"]
    return ids


def simulate(
    state: dict,
    guest_count: Optional[int] = None,
    budget_inr: Optional[int] = None,
    setting: Optional[str] = None,
) -> dict:
    """Re-price `state` (a serialized plan) under new numbers.

    Any argument left as None keeps the plan's original value.
    """
    req = state.get("requirements") or {}
    if not req.get("city"):
        raise ValueError("This plan has no requirements to simulate from.")

    base_guests = int(req.get("guest_count") or 0)
    base_budget = int(req.get("budget_inr") or 0)
    guests = int(guest_count if guest_count is not None else base_guests)
    budget = int(budget_inr if budget_inr is not None else base_budget)
    setting = setting or req.get("setting_preference") or "any"
    event_iso = (state.get("insights") or {}).get("event_date_iso")

    # 1) the current vendor mix at the new headcount
    ids = _current_vendor_ids(state.get("shortlist") or {})
    current_total = total_for(ids, guests) if ids else 0
    venue = load_catalog().get(ids.get("venue", ""), {})
    capacity = int(venue.get("capacity", 0) or 0)
    venue_fits = bool(venue) and capacity >= guests

    warnings = []
    if venue and not venue_fits:
        warnings.append(
            f"{venue.get('name', 'The venue')} holds {capacity} guests; "
            f"{guests} will not fit. Pick a package below instead."
        )
    if budget and current_total > budget:
        warnings.append(
            f"The current vendors would cost {_inr(current_total - budget)} more than the budget."
        )

    # 2) fresh alternatives for the new numbers
    packages = build_packages(
        req["city"], guests, budget, event_iso, req.get("diet") or "any", setting
    )
    fitting = [p for p in packages if p["fits_budget"]]
    best = max(fitting, key=lambda p: p["total_cost_inr"]) if fitting else None

    return {
        "inputs": {"guest_count": guests, "budget_inr": budget, "setting": setting},
        "baseline": {
            "guest_count": base_guests,
            "budget_inr": base_budget,
            "total_cost_inr": (state.get("plan") or {}).get("total_cost_inr", 0),
        },
        "current_mix": {
            "total_cost_inr": current_total,
            "per_guest_inr": round(current_total / guests) if guests else 0,
            "fits_budget": bool(budget) and current_total <= budget and venue_fits,
            "venue_capacity": capacity,
            "venue_fits": venue_fits,
            "delta_inr": current_total - int((state.get("plan") or {}).get("total_cost_inr") or 0),
        },
        "packages": packages,
        "recommended_tier": best["tier"] if best else None,
        "warnings": warnings,
    }
