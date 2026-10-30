"""Plan health score.

One 0-100 number (plus a letter grade) that says how solid a plan is, built
from five transparent factors so the person can see *why*:

  budget headroom   30   how much room is left under the budget
  capacity fit      20   is the venue the right size (not cramped, not empty)
  weather           20   seasonal risk for the venue's setting
  lead time         15   enough days to book everything calmly
  preference match  15   setting preference respected, asked-for vendors present
"""
from __future__ import annotations

from typing import List, Optional


def _budget(total: int, budget: int) -> tuple[int, str]:
    if not budget:
        return 0, "No budget given."
    used = total / budget
    if used > 1:
        over = used - 1
        return max(0, round(10 - over * 40)), f"Over budget by {over:.0%}."
    if used >= 0.95:
        return 22, "Uses almost the entire budget, little room for surprises."
    if used >= 0.6:
        return 30, f"Healthy: {1 - used:.0%} of the budget kept as buffer."
    return 26, f"Only {used:.0%} of the budget used; room to upgrade."


def _capacity(capacity: int, guests: int) -> tuple[int, str]:
    if not capacity:
        return 10, "Venue capacity unknown."
    fill = guests / capacity
    if fill > 1:
        return 0, "Venue is too small for the guest count."
    if fill >= 0.5:
        return 20, f"Venue {fill:.0%} full, a comfortable fit."
    if fill >= 0.3:
        return 14, f"Venue only {fill:.0%} full, may feel empty."
    return 8, f"Venue is far too big ({fill:.0%} full)."


def _weather(risk: str) -> tuple[int, str]:
    return {
        "low": (20, "Low weather risk."),
        "medium": (12, "Some weather risk; keep a backup."),
        "high": (4, "High weather risk for an outdoor setting."),
    }.get(risk, (12, "Weather risk unknown (no exact date)."))


def _lead_time(days: Optional[int]) -> tuple[int, str]:
    if days is None:
        return 7, "No exact date yet."
    if days < 0:
        return 0, "Date is in the past."
    if days >= 90:
        return 15, f"{days} days to go, plenty of time."
    if days >= 30:
        return 11, f"{days} days to go, tight but workable."
    return 4, f"Only {days} days to go, vendors will be rushed."


def _preferences(setting_pref: str, venue_setting: str, missing: List[str]) -> tuple[int, str]:
    score, notes = 15, []
    if setting_pref in ("indoor", "outdoor") and venue_setting and venue_setting != setting_pref:
        score -= 7
        notes.append(f"Asked for {setting_pref}, venue is {venue_setting}.")
    if missing:
        score -= 4 * len(missing)
        notes.append("Requested but not booked: " + ", ".join(missing) + ".")
    return max(score, 0), " ".join(notes) or "Matches every stated preference."


def health_score(
    *,
    total: int,
    budget: int,
    capacity: int,
    guests: int,
    weather_risk: str,
    days_until: Optional[int],
    setting_pref: str,
    venue_setting: str,
    missing_requested: List[str],
) -> dict:
    factors = []
    for name, maximum, (score, note) in (
        ("Budget headroom", 30, _budget(total, budget)),
        ("Capacity fit", 20, _capacity(capacity, guests)),
        ("Weather", 20, _weather(weather_risk)),
        ("Lead time", 15, _lead_time(days_until)),
        ("Preference match", 15, _preferences(setting_pref, venue_setting, missing_requested)),
    ):
        factors.append({"name": name, "score": score, "max": maximum, "note": note})
    total_score = sum(f["score"] for f in factors)
    grade = ("A" if total_score >= 85 else "B" if total_score >= 70
             else "C" if total_score >= 55 else "D")
    return {"score": total_score, "grade": grade, "factors": factors}
