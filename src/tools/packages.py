"""Catalog search helpers + the plan-packages tool.

`viable_vendors` answers "which catalog entries could actually work for this
event?" (right city, venue big enough and free on the date, caterer matches the
diet). Both the budget optimizer and the packages tool build on it.

`build_packages` turns that into three ready-made alternatives (Lean, Balanced,
Luxe) so the person can see what the same event costs at different levels.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .availability import check_availability
from .budget import calculate_budget
from .retrieval import load_catalog

CATEGORIES = ["venue", "caterer", "decorator", "entertainment", "photographer"]
# categories the optimizer may drop entirely to save money
OPTIONAL = ["entertainment", "decorator", "photographer"]

_KEYWORDS = {
    "photographer": ("photo", "camera", "candid", "video", "shoot"),
    "entertainment": ("dj", "music", "band", "singer", "dance", "sangeet", "live"),
    "decorator": ("decor", "floral", "flower", "stage", "mandap", "lighting"),
}


def _same_city(item: dict, city: str) -> bool:
    return (item.get("city") or "").strip().lower() == (city or "").strip().lower()


def _diet_ok(item: dict, diet: str) -> bool:
    offered = item.get("diet", "")
    if diet == "non-veg":
        return offered != "pure-veg"
    return True  # veg requests can be served by pure-veg or mixed kitchens


def viable_vendors(
    category: str,
    city: str,
    guest_count: int,
    event_iso: Optional[str] = None,
    diet: str = "any",
) -> List[dict]:
    """Catalog entries for `category` that could serve this event, cheapest first."""
    out = []
    for item in load_catalog().values():
        if item["type"] != category or not _same_city(item, city):
            continue
        if category == "venue":
            if item.get("capacity", 0) < guest_count:
                continue
            if event_iso and not check_availability.invoke(
                {"vendor_id": item["id"], "event_date": event_iso}
            )["available"]:
                continue
        if category == "caterer" and not _diet_ok(item, diet):
            continue
        out.append(item)
    return sorted(out, key=lambda v: _unit_cost(v, guest_count))


def _unit_cost(item: dict, guest_count: int) -> int:
    price = int(item.get("price_inr", 0))
    return price * guest_count if item.get("price_unit") == "per_plate" else price


def requested_categories(special_requests: Optional[str], user_request: str = "") -> set:
    """Optional categories the person explicitly asked for (never dropped)."""
    text = f"{special_requests or ''} {user_request or ''}".lower()
    return {cat for cat, words in _KEYWORDS.items() if any(w in text for w in words)}


def total_for(vendor_ids: Dict[str, str], guest_count: int) -> int:
    return calculate_budget.invoke(
        {"vendor_ids": vendor_ids, "guest_count": guest_count}
    )["total_cost_inr"]


def build_packages(
    city: str,
    guest_count: int,
    budget_inr: int,
    event_iso: Optional[str] = None,
    diet: str = "any",
    setting: str = "any",
) -> List[dict]:
    """Three alternative vendor combos: Lean (cheapest), Balanced (middle), Luxe (priciest)."""
    pools = {c: viable_vendors(c, city, guest_count, event_iso, diet) for c in CATEGORIES}
    if setting in ("indoor", "outdoor"):
        matching = [v for v in pools["venue"] if v.get("setting") == setting]
        pools["venue"] = matching or pools["venue"]
    if not pools["venue"]:
        return []

    def pick(pool: List[dict], tier: str) -> Optional[dict]:
        if not pool:
            return None
        return {"lean": pool[0], "balanced": pool[len(pool) // 2], "luxe": pool[-1]}[tier]

    packages = []
    for tier, label, blurb in (
        ("lean", "Lean", "Essentials only, lowest cost."),
        ("balanced", "Balanced", "Best value across every category."),
        ("luxe", "Luxe", "Top-tier vendors for a premium experience."),
    ):
        chosen = {c: pick(pools[c], tier) for c in CATEGORIES}
        if tier == "lean":
            # lean keeps just venue + food
            chosen = {c: v for c, v in chosen.items() if c in ("venue", "caterer")}
        ids = {c: v["id"] for c, v in chosen.items() if v}
        total = total_for(ids, guest_count)
        packages.append({
            "tier": tier,
            "label": label,
            "blurb": blurb,
            "vendors": {c: v["name"] for c, v in chosen.items() if v},
            "vendor_ids": ids,
            "total_cost_inr": total,
            "per_guest_inr": round(total / guest_count) if guest_count else 0,
            "fits_budget": total <= budget_inr,
        })
    return packages
