"""Weather-risk tool (seasonal climatology).

An outdoor wedding in Mumbai in July is a very different bet from one in
December. We don't call a live forecast API (events are booked months ahead,
long past any forecast horizon); instead we use approximate monthly
climatology per city: average rainy days and typical daytime high. That's
deterministic, free, and the right signal at planning time.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool

from .dates import to_date

# city -> 12 months of (avg rainy days, typical high °C). Approximate climate normals.
_CLIMATE = {
    "bangalore": [(0, 28), (1, 31), (1, 33), (4, 34), (8, 33), (8, 29),
                  (11, 28), (12, 28), (11, 28), (10, 28), (5, 27), (2, 26)],
    "mumbai":    [(0, 31), (0, 32), (0, 33), (0, 33), (1, 34), (14, 32),
                  (23, 30), (21, 29), (14, 30), (3, 33), (1, 34), (0, 33)],
    "delhi":     [(2, 20), (2, 24), (2, 30), (1, 36), (2, 40), (5, 39),
                  (12, 35), (12, 34), (6, 34), (1, 33), (0, 28), (1, 22)],
}
_ALIASES = {"bengaluru": "bangalore", "bombay": "mumbai", "new delhi": "delhi"}
_FALLBACK = [(2, 28)] * 12


def _climate_for(city: str) -> tuple[list, bool]:
    key = (city or "").strip().lower()
    key = _ALIASES.get(key, key)
    if key in _CLIMATE:
        return _CLIMATE[key], True
    return _FALLBACK, False


def assess_weather(city: str, iso_date: Optional[str], setting: str) -> dict:
    """Plain-Python weather risk, shared by the tool and the insights agent."""
    climate, known = _climate_for(city)
    d = to_date(iso_date or "")
    if d is None:
        return {
            "city": city, "month": None, "rain_probability": None, "high_c": None,
            "risk": "unknown", "advice": "No exact date yet, so seasonal risk can't be assessed.",
        }

    rainy_days, high_c = climate[d.month - 1]
    days_in_month = 30
    rain_p = round(min(rainy_days / days_in_month, 1.0), 2)
    outdoor = setting == "outdoor"

    if not outdoor:
        risk = "low"
        advice = "Indoor venue, weather won't affect the event."
    elif rain_p >= 0.4:
        risk = "high"
        advice = (f"Peak rain season (~{rain_p:.0%} chance of rain on a given day). "
                  "Book a covered backup space or switch to an indoor venue.")
    elif rain_p >= 0.2 or high_c >= 37:
        risk = "medium"
        advice = ("Some rain or heat risk. Plan tents, fans/coolers and an evening "
                  "start time." if high_c >= 37 else
                  "Some chance of showers. Keep a tent or canopy on standby.")
    else:
        risk = "low"
        advice = "Dry season, good conditions for an outdoor event."

    if not known:
        advice += " (No local climate data for this city; using a generic estimate.)"
    return {
        "city": city, "month": d.strftime("%B"), "rain_probability": rain_p,
        "high_c": high_c, "risk": risk, "advice": advice,
    }


@tool
def check_weather_risk(city: str, event_date: str, setting: str = "outdoor") -> dict:
    """Seasonal weather risk for an event (YYYY-MM-DD) in a city.

    Returns {"month", "rain_probability", "high_c", "risk": low|medium|high|unknown, "advice"}.
    """
    return assess_weather(city, event_date, setting)
