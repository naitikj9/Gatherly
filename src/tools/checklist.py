"""Countdown checklist tool.

Turns the chosen vendors and the event date into a dated to-do list
("T-60: catering tasting", "T-7: final headcount"...). Tasks whose ideal
deadline has already passed are compressed to "as soon as possible" and marked
urgent, which is how a short lead time shows up in the plan.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from .dates import to_date

# (days before event, category it depends on or None for always, task)
_TASKS = [
    (120, "venue", "Sign the venue contract and pay the booking advance"),
    (90, None, "Lock the guest list and send save-the-dates"),
    (75, "caterer", "Menu tasting with the caterer, finalize dishes"),
    (60, "decorator", "Approve decor theme, mood board and stage design"),
    (45, None, "Send formal invitations and set up RSVP tracking"),
    (30, "photographer", "Share must-have shot list and family list with the photographer"),
    (21, "entertainment", "Finalize playlist / performance set with entertainment"),
    (14, None, "Arrange guest transport, parking and accommodation"),
    (7, "caterer", "Confirm final headcount with the caterer"),
    (3, None, "Reconfirm timings with every vendor; share day-of contact sheet"),
    (1, None, "Pack the day-of kit: payments, contracts, emergency supplies"),
]

_EXTRAS = {
    "wedding": [(100, "Book makeup artist, mehendi and pandit/officiant")],
    "corporate": [(30, "Test AV, wifi and presentation setup with the venue")],
    "conference": [(45, "Confirm speakers, agenda and badge printing")],
    "birthday": [(10, "Order the cake and return gifts")],
}


def build_checklist(
    event_iso: Optional[str],
    vendor_categories: List[str],
    event_type: str = "other",
    today: Optional[date] = None,
) -> List[dict]:
    """Dated checklist, earliest first. Empty if there's no parseable date."""
    event_day = to_date(event_iso or "")
    if event_day is None:
        return []
    today = today or date.today()

    tasks = [(d, t) for d, cat, t in _TASKS if cat is None or cat in vendor_categories]
    tasks += _EXTRAS.get(event_type, [])
    tasks.sort(key=lambda x: -x[0])

    items = []
    for days_before, task in tasks:
        due = event_day - timedelta(days=days_before)
        urgent = due < today
        if urgent:
            due = today  # deadline already passed: do it now
        if due > event_day:
            continue
        items.append({
            "due": due.isoformat(),
            "days_before": (event_day - due).days,
            "task": task,
            "urgent": urgent,
        })
    return items
