"""Offline unit + graph tests (no API key, no network).

    python -m pytest tests/test_offline.py -q

The LLM calls are replaced by a fake model, so these run in a second and are
safe for CI. The real-LLM evaluation suite is still tests/test_cases.py.
"""
from __future__ import annotations

from datetime import date

import pytest
from langchain_core.messages import AIMessage

from src.exporters import serialize_state, to_ics, to_markdown
from src.guardrails import validate_requirements
from src.schemas import (
    EventPlan,
    EventRequirements,
    ScheduleItem,
    VendorChoice,
    VendorShortlist,
)
from src.scoring import health_score
from src.tools.checklist import build_checklist
from src.tools.dates import describe_date, parse_event_date
from src.tools.packages import build_packages, viable_vendors
from src.tools.retrieval import get_vendor_by_id
from src.tools.weather import assess_weather

TODAY = date(2030, 1, 10)  # a Thursday


# ------------------------------------------------------------------ dates

@pytest.mark.parametrize("text, expected", [
    ("2030-12-18", date(2030, 12, 18)),
    ("18/12/2030", date(2030, 12, 18)),
    ("18th December 2030", date(2030, 12, 18)),
    ("Dec 18, 2030", date(2030, 12, 18)),
    ("dec 18", date(2030, 12, 18)),          # no year -> next occurrence
    ("5 jan", date(2031, 1, 5)),             # already passed this year -> next year
    ("in 3 weeks", date(2030, 1, 31)),
    ("next saturday", date(2030, 1, 12)),
    ("tomorrow", date(2030, 1, 11)),
])
def test_parse_event_date(text, expected):
    assert parse_event_date(text, TODAY) == expected


def test_describe_date_flags():
    info = describe_date("2030-01-12", TODAY)
    assert info["weekday"] == "Saturday" and info["is_weekend"] and info["days_until"] == 2
    assert describe_date("2029-05-01", TODAY)["is_past"]
    assert describe_date("sometime soon", TODAY)["iso"] is None


def test_past_date_is_refused():
    req = EventRequirements(in_scope=True, city="Mumbai", guest_count=50,
                            budget_inr=100000, event_date="2001-01-01")
    assert any("in the past" in p for p in validate_requirements(req))


# ---------------------------------------------------------------- weather

def test_weather_monsoon_outdoor_is_high_risk():
    w = assess_weather("Mumbai", "2030-07-15", "outdoor")
    assert w["risk"] == "high" and w["month"] == "July"


def test_weather_indoor_is_always_low():
    assert assess_weather("Mumbai", "2030-07-15", "indoor")["risk"] == "low"


def test_weather_unknown_without_date():
    assert assess_weather("Bangalore", None, "outdoor")["risk"] == "unknown"


# -------------------------------------------------------------- checklist

def test_checklist_only_includes_booked_categories():
    items = build_checklist("2030-12-18", ["venue", "caterer"], "wedding", TODAY)
    tasks = " ".join(i["task"] for i in items)
    assert "caterer" in tasks and "photographer" not in tasks
    assert "makeup" in tasks.lower()  # wedding extra
    assert [i["due"] for i in items] == sorted(i["due"] for i in items)


def test_checklist_marks_overdue_tasks_urgent():
    items = build_checklist("2030-01-25", ["venue", "caterer"], "party", TODAY)
    assert any(i["urgent"] for i in items)
    assert all(i["due"] >= TODAY.isoformat() for i in items)


# --------------------------------------------------------------- packages

def test_viable_venues_respect_capacity_and_blackouts():
    big = viable_vendors("venue", "Bangalore", 350, "2030-12-18")
    assert [v["id"] for v in big] == ["venue-001"]
    assert viable_vendors("venue", "Bangalore", 350, "2026-12-20") == []  # venue-001 booked


def test_packages_are_ordered_lean_to_luxe():
    pkgs = build_packages("Bangalore", 150, 800000, "2030-12-18")
    assert [p["tier"] for p in pkgs] == ["lean", "balanced", "luxe"]
    assert pkgs[0]["total_cost_inr"] <= pkgs[1]["total_cost_inr"] <= pkgs[2]["total_cost_inr"]
    assert set(pkgs[0]["vendors"]) == {"venue", "caterer"}


def test_no_packages_when_no_venue_fits():
    assert build_packages("Bangalore", 900, 5000000, "2030-12-18") == []


# ------------------------------------------------------------ health score

def test_health_score_rewards_a_solid_plan():
    h = health_score(total=700000, budget=800000, capacity=200, guests=150,
                     weather_risk="low", days_until=200, setting_pref="outdoor",
                     venue_setting="outdoor", missing_requested=[])
    assert h["score"] == 100 and h["grade"] == "A"


def test_health_score_punishes_risk():
    h = health_score(total=900000, budget=800000, capacity=400, guests=100,
                     weather_risk="high", days_until=10, setting_pref="indoor",
                     venue_setting="outdoor", missing_requested=["photographer"])
    assert h["score"] < 40 and h["grade"] == "D"


# ----------------------------------------------------- full graph, fake LLM

def _choice(vid: str) -> VendorChoice:
    v = get_vendor_by_id(vid)
    return VendorChoice(id=v["id"], name=v["name"], type=v["type"], price_inr=v["price_inr"],
                        price_unit=v["price_unit"], reason="test pick")


class _FakeLLM:
    """Stands in for ChatOpenAI: with_structured_output(Schema).invoke() -> canned object.

    Mirrors `include_raw=True`: returns {"raw", "parsed", "parsing_error"} with
    fake token usage, so the usage tracker has something to count.
    """

    def __init__(self, outputs: dict):
        self.outputs = outputs

    def with_structured_output(self, schema, include_raw=False):
        out = self.outputs[schema]

        def invoke(_self, _msgs):
            parsed = out.model_copy(deep=True)
            if not include_raw:
                return parsed
            raw = AIMessage(content="", usage_metadata={
                "input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
            return {"raw": raw, "parsed": parsed, "parsing_error": None}

        return type("Runnable", (), {"invoke": invoke})()


@pytest.fixture
def run_graph(monkeypatch, tmp_path):
    """Run the real graph with canned LLM answers. Returns (final_state, approvals_asked)."""
    from src import config, llm, logging_utils
    from src.agents import intake, planner, venue
    from src.graph import build_graph
    from src.runner import run_planner

    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(llm, "_sleep", lambda _s: None)
    monkeypatch.setattr(logging_utils, "RUNS_DIR", tmp_path)

    def _run(req: EventRequirements, shortlist: VendorShortlist, decision="approve"):
        fake = _FakeLLM({
            EventRequirements: req,
            VendorShortlist: shortlist,
            EventPlan: EventPlan(timeline=[ScheduleItem(time="18:00", activity="Guests arrive")],
                                 summary="A lovely evening."),
        })
        for mod in (intake, venue, planner):
            monkeypatch.setattr(mod, "get_chat_llm", lambda *a, **k: fake)
        asked = []

        def decide(payload):
            asked.append(payload)
            return decision

        state = run_planner("test request", decision_fn=decide, thread_id="t",
                            graph=build_graph(), verbose=False, quiet=True)
        return state, asked

    return _run


def _bangalore_wedding(budget: int) -> EventRequirements:
    return EventRequirements(
        in_scope=True, event_type="wedding", city="Bangalore", setting_preference="outdoor",
        guest_count=150, budget_inr=budget, event_date="Dec 18, 2030",
    )


def _premium_shortlist() -> VendorShortlist:
    return VendorShortlist(
        venue=_choice("venue-001"), caterer=_choice("cater-001"), decorator=_choice("decor-001"),
        entertainment=_choice("ent-001"), photographer=_choice("photo-001"),
    )


def test_graph_books_plan_and_adds_insights(run_graph):
    state, asked = run_graph(_bangalore_wedding(800000), _premium_shortlist())
    assert state["status"] == "booked"
    assert len(asked) == 1  # high-value booking still needs a human
    ins = state["insights"]
    assert ins.event_date_iso == "2030-12-18" and ins.weather.risk == "low"
    assert ins.checklist and len(ins.packages) == 3 and ins.health.score > 0
    assert "Plan health" in state["final_message"]


def test_optimizer_self_heals_an_over_budget_plan(run_graph):
    # premium mix costs ₹7.17L, budget is ₹4L -> optimizer must bring it under
    state, _ = run_graph(_bangalore_wedding(400000), _premium_shortlist())
    assert state["status"] == "booked"
    assert state["plan"].total_cost_inr <= 400000
    assert state["optimization_log"]
    assert get_vendor_by_id(state["shortlist"].venue.id)["capacity"] >= 150


def test_optimizer_gives_up_when_nothing_fits(run_graph):
    req = EventRequirements(in_scope=True, event_type="wedding", city="Delhi",
                            guest_count=450, budget_inr=400000, event_date="2030-12-10")
    shortlist = VendorShortlist(venue=_choice("venue-005"), caterer=_choice("cater-005"))
    state, asked = run_graph(req, shortlist)
    assert state["status"] == "rejected" and not asked
    assert "optimizer" in state["final_message"]


def test_monsoon_outdoor_event_needs_a_human(run_graph):
    req = EventRequirements(in_scope=True, event_type="birthday", city="Mumbai",
                            setting_preference="outdoor", guest_count=60,
                            budget_inr=190000, event_date="2030-07-20")
    shortlist = VendorShortlist(venue=_choice("venue-004"), caterer=_choice("cater-004"))
    state, asked = run_graph(req, shortlist, decision="decline")
    assert asked and state["status"] == "declined"
    assert any(v.startswith("Weather") for v in state["compliance"].violations)


# ---------------------------------------------------------------- exports

def test_exports_markdown_and_ics(run_graph):
    state, _ = run_graph(_bangalore_wedding(800000), _premium_shortlist())
    data = serialize_state(state)

    md = to_markdown(data, "plan-x")
    assert md.startswith("# Wedding in Bangalore") and "Countdown checklist" in md

    ics = to_ics(data, "plan-x")
    assert ics.startswith("BEGIN:VCALENDAR") and ics.rstrip().endswith("END:VCALENDAR")
    assert "DTSTART;VALUE=DATE:20301218" in ics
    assert ics.count("BEGIN:VEVENT") == 1 + len(data["insights"]["checklist"])
    assert all(len(line.encode()) <= 75 for line in ics.split("\r\n"))


def test_ics_needs_a_date():
    with pytest.raises(ValueError):
        to_ics({"requirements": {}, "insights": {}}, "x")
