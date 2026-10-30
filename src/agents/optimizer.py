"""Budget optimizer agent (the self-healing loop).

Without it, a plan that's over budget just gets rejected or kicked to a human.
With it, compliance hands cost-only problems here first: the optimizer swaps
vendors for cheaper catalog alternatives that still fit (same city, venue big
enough and free on the date, caterer matches the diet), or drops an optional
extra the person never asked for. The graph then loops back through
planner -> insights -> compliance with the cheaper shortlist.

It's deterministic and greedy:
  - if a single move gets the plan under budget, take the one that saves the
    *least* (smallest downgrade that still works)
  - otherwise take the move that saves the most and keep going
  - swaps are always tried before dropping a category
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..config import settings
from ..logging_utils import log_step
from ..schemas import EventPlan, EventRequirements, VendorChoice, VendorShortlist
from ..state import PlannerState
from ..tools.dates import describe_date
from ..tools.packages import (
    CATEGORIES,
    OPTIONAL,
    requested_categories,
    total_for,
    viable_vendors,
)

# (category, new vendor record or None to drop, saving)
Move = Tuple[str, Optional[dict], int]


def _cost(ids: Dict[str, str], guests: int) -> int:
    return total_for(ids, guests)


def _candidate_moves(
    ids: Dict[str, str], req: EventRequirements, event_iso: Optional[str], keep: set
) -> Tuple[List[Move], List[Move]]:
    current = _cost(ids, req.guest_count)
    swaps: List[Move] = []
    drops: List[Move] = []
    for cat, vid in ids.items():
        for alt in viable_vendors(cat, req.city, req.guest_count, event_iso, req.diet):
            if alt["id"] == vid:
                continue
            saving = current - _cost({**ids, cat: alt["id"]}, req.guest_count)
            if saving > 0:
                swaps.append((cat, alt, saving))
        if cat in OPTIONAL and cat not in keep:
            saving = current - _cost({k: v for k, v in ids.items() if k != cat}, req.guest_count)
            if saving > 0:
                drops.append((cat, None, saving))
    return swaps, drops


def _choose(moves: List[Move], gap: int) -> Optional[Move]:
    if not moves:
        return None
    enough = [m for m in moves if m[2] >= gap]
    if enough:
        return min(enough, key=lambda m: m[2])
    return max(moves, key=lambda m: m[2])


def optimize_shortlist(
    shortlist: VendorShortlist, req: EventRequirements, user_request: str = ""
) -> Tuple[VendorShortlist, List[str]]:
    """Return a cheaper shortlist and a log of what changed (empty log = no change)."""
    event_iso = describe_date(req.event_date)["iso"]
    keep = requested_categories(req.special_requests, user_request)
    ids = {c: getattr(shortlist, c).id for c in CATEGORIES if getattr(shortlist, c)}
    choices = {c: getattr(shortlist, c) for c in CATEGORIES}
    log: List[str] = []

    for _ in range(10):  # hard stop; the catalog is small so this converges fast
        total = _cost(ids, req.guest_count)
        gap = total - req.budget_inr
        if gap <= 0:
            break
        swaps, drops = _candidate_moves(ids, req, event_iso, keep)
        move = _choose(swaps, gap) or _choose(drops, gap)
        if move is None:
            break
        cat, alt, saving = move
        old = choices[cat]
        if alt is None:
            ids.pop(cat)
            choices[cat] = None
            log.append(f"Dropped {cat} ({old.name}), saves ₹{saving:,}.")
        else:
            ids[cat] = alt["id"]
            choices[cat] = VendorChoice(
                id=alt["id"], name=alt["name"], type=alt["type"],
                price_inr=int(alt["price_inr"]), price_unit=alt["price_unit"],
                reason=f"Swapped in by the budget optimizer for {old.name}; "
                       f"saves ₹{saving:,} and still fits the event.",
            )
            log.append(f"Swapped {cat}: {old.name} -> {alt['name']}, saves ₹{saving:,}.")

    if not log:
        return shortlist, log
    optimized = VendorShortlist(
        **choices,
        notes=(f"{shortlist.notes} Budget optimizer made {len(log)} change(s).").strip(),
    )
    return optimized, log


def optimizer_node(state: PlannerState) -> dict:
    req: EventRequirements = state["requirements"]
    plan: EventPlan = state["plan"]
    attempts = state.get("optimizer_attempts", 0) + 1

    shortlist, changes = optimize_shortlist(
        state["shortlist"], req, state.get("user_request", "")
    )
    if not changes:
        msg = log_step("optimizer", "No cheaper combination fits this event.")
        return {"optimizer_attempts": attempts, "optimizer_stuck": True, "log": [msg]}

    new_total = _cost(
        {c: getattr(shortlist, c).id for c in CATEGORIES if getattr(shortlist, c)},
        req.guest_count,
    )
    msg = log_step(
        "optimizer",
        f"Pass {attempts}/{settings.OPTIMIZER_MAX_ATTEMPTS}: ₹{plan.total_cost_inr:,} -> "
        f"₹{new_total:,} ({len(changes)} change(s)).",
        changes,
    )
    return {
        "shortlist": shortlist,
        "optimizer_attempts": attempts,
        "optimizer_stuck": False,
        "optimization_log": changes,
        "log": [msg],
    }
