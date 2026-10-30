"""Insights agent.

Runs after the planner and before compliance. It's fully deterministic (no
LLM) and enriches the plan with the things a real coordinator would check:

  - date intelligence  weekday, days left
  - weather risk       seasonal climatology for the venue's setting
  - countdown          dated checklist built from the chosen vendors
  - packages           Lean / Balanced / Luxe alternatives from the catalog
  - health score       0-100 with an explained breakdown

Compliance then reads the weather risk, so an outdoor monsoon wedding gets a
human look before booking.
"""
from __future__ import annotations

from ..logging_utils import log_step
from ..schemas import (
    ChecklistItem,
    EventPlan,
    EventRequirements,
    HealthScore,
    Insights,
    PlanPackage,
    VendorShortlist,
    WeatherRisk,
)
from ..scoring import health_score
from ..state import PlannerState
from ..tools import get_vendor_by_id
from ..tools.checklist import build_checklist
from ..tools.dates import describe_date
from ..tools.packages import CATEGORIES, build_packages, requested_categories
from ..tools.weather import check_weather_risk


def insights_node(state: PlannerState) -> dict:
    req: EventRequirements = state["requirements"]
    shortlist: VendorShortlist = state["shortlist"]
    plan: EventPlan = state["plan"]

    when = describe_date(req.event_date)
    venue = get_vendor_by_id(shortlist.venue.id) if shortlist.venue else {}
    venue_setting = (venue or {}).get("setting", req.setting_preference)

    weather = WeatherRisk(**{
        k: v for k, v in check_weather_risk.invoke(
            {"city": req.city, "event_date": when["iso"] or "", "setting": venue_setting}
        ).items() if k in WeatherRisk.model_fields
    })

    booked = [c for c in CATEGORIES if getattr(shortlist, c) is not None]
    checklist = [ChecklistItem(**i) for i in
                 build_checklist(when["iso"], booked, req.event_type)]

    packages = [PlanPackage(**p) for p in build_packages(
        req.city, req.guest_count, req.budget_inr, when["iso"],
        req.diet, req.setting_preference,
    )]

    wanted = requested_categories(req.special_requests, state.get("user_request", ""))
    missing = sorted(c for c in wanted if c not in booked)
    health = HealthScore(**health_score(
        total=plan.total_cost_inr,
        budget=req.budget_inr,
        capacity=(venue or {}).get("capacity", 0),
        guests=req.guest_count,
        weather_risk=weather.risk,
        days_until=when["days_until"],
        setting_pref=req.setting_preference,
        venue_setting=venue_setting,
        missing_requested=missing,
    ))

    insights = Insights(
        event_date_iso=when["iso"],
        weekday=when["weekday"],
        days_until=when["days_until"],
        weather=weather,
        checklist=checklist,
        packages=packages,
        health=health,
        per_guest_cost_inr=round(plan.total_cost_inr / req.guest_count) if req.guest_count else 0,
    )
    msg = log_step(
        "insights",
        f"Health {health.score}/100 ({health.grade}), weather risk {weather.risk}, "
        f"{len(checklist)} checklist tasks, {len(packages)} packages.",
        insights,
    )
    return {"insights": insights, "log": [msg]}
