"""Export a finished plan as a calendar file (.ics) or a Markdown document.

Both work on the plain-dict form of the state (what the API stores and
returns), so the CLI and the backend share one implementation.

The .ics holds the event itself plus every countdown-checklist task as an
all-day reminder, so importing it into Google/Apple/Outlook calendar drops the
whole plan onto the person's calendar.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

CATEGORIES = ["venue", "caterer", "decorator", "entertainment", "photographer"]


def serialize_state(state: dict) -> Dict[str, Any]:
    """Pydantic-aware -> plain dict."""
    def _v(x):
        if x is None:
            return None
        if hasattr(x, "model_dump"):
            return x.model_dump()
        return x

    return {
        "user_request": state.get("user_request", ""),
        "requirements": _v(state.get("requirements")),
        "shortlist": _v(state.get("shortlist")),
        "plan": _v(state.get("plan")),
        "insights": _v(state.get("insights")),
        "compliance": _v(state.get("compliance")),
        "optimization_log": state.get("optimization_log", []),
        "status": state.get("status"),
        "final_message": state.get("final_message"),
        "log": state.get("log", []),
        "human_decision": state.get("human_decision"),
    }


def _inr(n: Any) -> str:
    try:
        return f"₹{int(n):,}"
    except (TypeError, ValueError):
        return "—"


# --------------------------------------------------------------------- .ics

def _ics_escape(text: str) -> str:
    return (str(text).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _fold(line: str) -> List[str]:
    """RFC 5545: lines longer than 75 octets are folded with a leading space."""
    out, raw = [], line.encode("utf-8")
    while len(raw) > 75:
        cut = 75
        while (raw[cut] & 0xC0) == 0x80:  # don't split a UTF-8 character
            cut -= 1
        out.append(raw[:cut].decode("utf-8"))
        raw = b" " + raw[cut:]
    out.append(raw.decode("utf-8"))
    return out


def _all_day_event(uid: str, day: str, summary: str, description: str, stamp: str) -> List[str]:
    start = datetime.strptime(day, "%Y-%m-%d")
    end = start + timedelta(days=1)
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
        f"DTEND;VALUE=DATE:{end:%Y%m%d}",
        f"SUMMARY:{_ics_escape(summary)}",
        f"DESCRIPTION:{_ics_escape(description)}",
        "END:VEVENT",
    ]


def to_ics(state: Dict[str, Any], plan_id: str = "plan") -> str:
    req = state.get("requirements") or {}
    insights = state.get("insights") or {}
    shortlist = state.get("shortlist") or {}
    plan = state.get("plan") or {}
    day = insights.get("event_date_iso")
    if not day:
        raise ValueError("This plan has no exact date, so it can't be exported to a calendar.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    title = f"{(req.get('event_type') or 'Event').title()} in {req.get('city') or '?'}"
    venue = (shortlist.get("venue") or {}).get("name", "")
    details = [f"{req.get('guest_count', 0)} guests · total {_inr(plan.get('total_cost_inr'))}"]
    details += [f"{item.get('time')}: {item.get('activity')}" for item in plan.get("timeline", [])]

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Gatherly//Event Plan//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    event = _all_day_event(f"{plan_id}-event@gatherly", day, title, "\n".join(details), stamp)
    if venue:
        event.insert(-1, f"LOCATION:{_ics_escape(venue + ', ' + (req.get('city') or ''))}")
    lines += event
    for i, task in enumerate(insights.get("checklist", [])):
        prefix = "[URGENT] " if task.get("urgent") else ""
        lines += _all_day_event(
            f"{plan_id}-task-{i}@gatherly", task["due"], f"{prefix}{task['task']}",
            f"{title}: {task['days_before']} days before the event.", stamp,
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold(line)) + "\r\n"


# ---------------------------------------------------------------- Markdown

def to_markdown(state: Dict[str, Any], plan_id: str = "plan") -> str:
    req = state.get("requirements") or {}
    shortlist = state.get("shortlist") or {}
    plan = state.get("plan") or {}
    insights = state.get("insights") or {}
    compliance = state.get("compliance") or {}

    title = f"{(req.get('event_type') or 'Event').title()} in {req.get('city') or '?'}"
    md = [f"# {title}", "",
          f"**Date:** {insights.get('event_date_iso') or req.get('event_date') or 'TBD'}"
          f"{' (' + insights['weekday'] + ')' if insights.get('weekday') else ''} · "
          f"**Guests:** {req.get('guest_count', 0)} · **Budget:** {_inr(req.get('budget_inr'))} · "
          f"**Status:** {state.get('status') or '—'}", ""]

    health = insights.get("health") or {}
    if health:
        md += [f"## Plan health: {health.get('score')}/100 (grade {health.get('grade')})", "",
               "| Factor | Score | Note |", "|---|---|---|"]
        md += [f"| {f['name']} | {f['score']}/{f['max']} | {f['note']} |"
               for f in health.get("factors", [])]
        md.append("")

    md += ["## Vendors", "", "| Category | Vendor | Price |", "|---|---|---|"]
    units = {"per_plate": "/plate", "per_day": "/day", "flat": " flat"}
    for cat in CATEGORIES:
        v = shortlist.get(cat)
        if v:
            md.append(f"| {cat.title()} | {v['name']} | {_inr(v['price_inr'])}"
                      f"{units.get(v.get('price_unit'), '')} |")
    md.append("")

    md += ["## Budget", "", "| Category | Amount |", "|---|---|"]
    md += [f"| {b['category'].title()} | {_inr(b['amount_inr'])} |"
           for b in plan.get("budget_breakdown", [])]
    md += [f"| **Total** | **{_inr(plan.get('total_cost_inr'))}** |", ""]

    if plan.get("timeline"):
        md += ["## Day-of timeline", ""]
        md += [f"- **{t['time']}** {t['activity']}" for t in plan["timeline"]]
        md.append("")

    weather = insights.get("weather") or {}
    if weather.get("risk") not in (None, "unknown"):
        md += ["## Weather", "", f"**{weather['risk'].title()} risk** in {weather.get('month')}. "
               f"{weather.get('advice', '')}", ""]

    if insights.get("checklist"):
        md += ["## Countdown checklist", ""]
        md += [f"- [ ] **{t['due']}** {'⚠️ ' if t.get('urgent') else ''}{t['task']}"
               for t in insights["checklist"]]
        md.append("")

    if insights.get("packages"):
        md += ["## Alternative packages", "", "| Package | Total | Per guest | Fits budget |",
               "|---|---|---|---|"]
        md += [f"| {p['label']} | {_inr(p['total_cost_inr'])} | {_inr(p['per_guest_inr'])} | "
               f"{'✅' if p['fits_budget'] else '❌'} |" for p in insights["packages"]]
        md.append("")

    if state.get("optimization_log"):
        md += ["## Budget optimizer changes", ""]
        md += [f"- {c}" for c in state["optimization_log"]]
        md.append("")

    if compliance:
        md += ["## Compliance", "", f"**{compliance.get('decision')}** "
               f"({compliance.get('risk_level')} risk). {compliance.get('rationale', '')}"]
        md += [f"- {v}" for v in compliance.get("violations", [])]
        md.append("")

    if plan.get("summary"):
        md += ["## Summary", "", plan["summary"], ""]
    md.append(f"_Generated by Gatherly · plan `{plan_id}`_")
    return "\n".join(md) + "\n"
