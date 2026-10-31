"""Plain-Python validation and safety checks (no LLM).

These give us a reliable safety net that doesn't depend on the model behaving.
Used at intake (screen unsafe requests + validate the parsed fields) and at
compliance (capacity check).
"""
from __future__ import annotations

import re
from typing import List

from .config import settings
from .schemas import EventRequirements
from .tools.dates import describe_date

# obvious red-flag terms -> refuse outright, alongside the LLM's own judgment
_UNSAFE_TERMS = [
    "weapon", "explosive", "bomb", "drugs", "smuggle", "fake id",
    "hack", "launder", "counterfeit", "poison",
]


# attempts to hijack the agents' instructions (prompt injection)
_INJECTION_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instructions?|rules?|prompts?|guidelines?)",
        r"\b(reveal|print|show|repeat|leak)\b.{0,30}\b(system|hidden|developer)\s+(prompt|message|instructions?)",
        r"\byou\s+are\s+now\b",
        r"\b(developer|god|jailbreak|dan)\s+mode\b",
        r"\bact\s+as\b.{0,30}\b(unrestricted|unfiltered|admin|root)\b",
        r"\b(set|mark|make)\b.{0,30}\b(status|decision)\b.{0,20}\b(booked|approved?|approve_auto)\b",
        r"</?\s*(system|assistant|instructions?)\s*>",
    )
]

_PII_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[email]"),
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[phone]"),
    (re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"), "[id-number]"),  # Aadhaar-like
]


def detect_injection(text: str) -> bool:
    """True if the text tries to override the agents' instructions."""
    return any(p.search(text or "") for p in _INJECTION_PATTERNS)


def redact_pii(text: str) -> str:
    """Mask emails, Indian phone numbers and 12-digit ID numbers (for logs/traces)."""
    for pattern, mask in _PII_PATTERNS:
        text = pattern.sub(mask, text)
    return text


def screen_request(text: str) -> str | None:
    """Return a refusal reason if the request is unsafe/out of scope, else None."""
    if len(text or "") > settings.MAX_REQUEST_CHARS:
        return (f"That request is too long. Please describe your event in under "
                f"{settings.MAX_REQUEST_CHARS} characters.")
    if detect_injection(text):
        return ("This request looks like an attempt to change how the planner works, "
                "so I can't process it. Please just describe your event.")
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
