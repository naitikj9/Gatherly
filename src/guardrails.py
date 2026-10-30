"""Plain-Python validation and safety checks (no LLM).

These give us a reliable safety net that doesn't depend on the model behaving.
Used at intake (screen unsafe requests + validate the parsed fields) and at
compliance (capacity check).
"""
from __future__ import annotations

from typing import List

from .config import settings
from .schemas import EventRequirements
from .tools.dates import describe_date

# obvious red-flag terms -> refuse outright, alongside the LLM's own judgment
_UNSAFE_TERMS = [
    "weapon", "explosive", "bomb", "drugs", "smuggle", "fake id",
    "hack", "launder", "counterfeit", "poison",
]


def screen_request(text: str) -> str | None:
    """Return a refusal reason if the request is unsafe/out of scope, else None."""
    lowered = text.lower()
    for term in _UNSAFE_TERMS:
        if term in lowered:
            return (
                "This request appears to involve unsafe or prohibited activity, "
                "so I can't help plan it."
            )
    return None


def validate_requirements(req: EventRequirements) -> List[str]:
    """Return a list of problems with the parsed requirements (empty = all good)."""
    problems: List[str] = []
    if not req.city.strip():
        problems.append("No city was provided for the event.")
    if req.guest_count < settings.MIN_GUESTS:
        problems.append("Guest count must be at least 1.")
    if req.guest_count > settings.MAX_GUESTS:
        problems.append(
            f"Guest count {req.guest_count} exceeds the supported maximum "
            f"of {settings.MAX_GUESTS}."
        )
    if req.budget_inr < settings.MIN_BUDGET_INR:
        problems.append(
            f"Budget ₹{req.budget_inr:,} is below the minimum workable "
            f"budget of ₹{settings.MIN_BUDGET_INR:,}."
        )
    when = describe_date(req.event_date)
    if when["is_past"]:
        problems.append(
            f"The event date {when['iso']} is in the past; please pick a future date."
        )
    return problems


def capacity_problem(venue_capacity: int, guest_count: int) -> str | None:
    """Return a violation string if the venue can't hold the guests, else None."""
    if venue_capacity and guest_count > venue_capacity:
        return (
            f"Venue capacity ({venue_capacity}) is smaller than the guest "
            f"count ({guest_count})."
        )
    return None
