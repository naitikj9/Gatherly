"""Date intelligence tool.

People write dates like "Dec 18", "18th December 2026", "next Saturday" or
"in 3 weeks". The availability calendar and the checklist need a real ISO date,
so this turns free text into one, deterministically (no LLM). It also reports
the weekday and how many days are left, which the guardrails and the health
score use.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"),
            ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
            ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"),
            ("nov", "november"), ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_ISO = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_DMY_NUM = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")  # Indian style: 18/12/2026
_DAY_MONTH = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]{3,9})\.?,?(?:\s+(\d{4}))?\b")
_MONTH_DAY = re.compile(r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?(?:\s+(\d{4}))?\b")
_RELATIVE = re.compile(r"\bin\s+(\d{1,3})\s+(day|week|month)s?\b")
_NEXT_WEEKDAY = re.compile(r"\b(?:next|this|coming)\s+(" + "|".join(_WEEKDAYS) + r")\b")


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _roll_forward(m: int, d: int, today: date) -> Optional[date]:
    """No year given: pick the next occurrence of that day/month."""
    candidate = _safe_date(today.year, m, d)
    if candidate and candidate < today:
        candidate = _safe_date(today.year + 1, m, d)
    return candidate


def parse_event_date(text: str, today: Optional[date] = None) -> Optional[date]:
    """Best-effort parse of a free-text date. Returns None if nothing is found."""
    if not text:
        return None
    today = today or date.today()
    s = text.strip().lower()

    if s in ("today", "tonight"):
        return today
    if s == "tomorrow" or "tomorrow" in s:
        return today + timedelta(days=1)

    if m := _ISO.search(s):
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if m := _DMY_NUM.search(s):
        return _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    for pattern, day_idx, mon_idx in ((_DAY_MONTH, 1, 2), (_MONTH_DAY, 2, 1)):
        for m in pattern.finditer(s):
            month = _MONTHS.get(m.group(mon_idx))
            if not month:
                continue
            day = int(m.group(day_idx))
            if m.group(3):
                return _safe_date(int(m.group(3)), month, day)
            return _roll_forward(month, day, today)

    if m := _RELATIVE.search(s):
        n, unit = int(m.group(1)), m.group(2)
        days = {"day": 1, "week": 7, "month": 30}[unit] * n
        return today + timedelta(days=days)

    if m := _NEXT_WEEKDAY.search(s):
        target = _WEEKDAYS.index(m.group(1))
        ahead = (target - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)

    return None


def describe_date(text: str, today: Optional[date] = None) -> dict:
    """Normalize a date and describe it.

    Returns {"iso", "weekday", "days_until", "is_weekend", "is_past"}; every
    field is None/False when the text can't be parsed.
    """
    today = today or date.today()
    parsed = parse_event_date(text, today)
    if parsed is None:
        return {"iso": None, "weekday": None, "days_until": None,
                "is_weekend": False, "is_past": False}
    days = (parsed - today).days
    return {
        "iso": parsed.isoformat(),
        "weekday": _WEEKDAYS[parsed.weekday()].title(),
        "days_until": days,
        "is_weekend": parsed.weekday() >= 5,
        "is_past": days < 0,
    }


def to_date(iso: str) -> Optional[date]:
    """ISO string -> date, or None."""
    try:
        return datetime.strptime(iso, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
