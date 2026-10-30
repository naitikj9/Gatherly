"""Pydantic models the agents use to hand work off to one another.

Each agent returns one of these instead of loose text, so every handoff is
validated JSON. If an agent's output doesn't match the schema, LangChain makes
it retry.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# --- Intake agent output ---

EventType = Literal[
    "wedding", "corporate", "birthday", "anniversary", "conference", "party", "other"
]


class EventRequirements(BaseModel):
    """Structured version of the user's plain-language request."""

    in_scope: bool = Field(
        description="True only if this is a genuine event-planning request. "
        "False for off-topic, nonsensical, or unsafe/illegal requests."
    )
    refusal_reason: Optional[str] = Field(
        default=None,
        description="If in_scope is False, a short, polite reason to show the user.",
    )

    event_type: EventType = Field(default="other")
    city: str = Field(default="", description="City where the event is held.")
    setting_preference: Literal["indoor", "outdoor", "any"] = "any"
    guest_count: int = Field(default=0, description="Expected number of guests.")
    budget_inr: int = Field(default=0, description="Total budget in Indian Rupees.")
    event_date: str = Field(default="", description="Requested date, as given (free text/ISO).")
    cuisine_preference: Optional[str] = Field(default=None)
    diet: Literal["veg", "non-veg", "veg-and-nonveg", "any"] = "any"
    special_requests: Optional[str] = Field(default=None)


# --- Venue & vendor agent output ---


class VendorChoice(BaseModel):
    id: str
    name: str
    type: Literal["venue", "caterer", "decorator", "entertainment", "photographer"]
    price_inr: int = Field(description="Headline price from the catalog.")
    price_unit: Literal["per_day", "per_plate", "flat"]
    reason: str = Field(description="Why this vendor fits the request.")


class VendorShortlist(BaseModel):
    venue: Optional[VendorChoice] = None
    caterer: Optional[VendorChoice] = None
    decorator: Optional[VendorChoice] = None
    entertainment: Optional[VendorChoice] = None
    photographer: Optional[VendorChoice] = None
    notes: str = Field(default="", description="Any caveats, e.g. no exact match found.")


# --- Planner agent output ---


class ScheduleItem(BaseModel):
    time: str = Field(description="e.g. '18:00' or 'Evening'.")
    activity: str


class BudgetLine(BaseModel):
    category: str
    amount_inr: int


class EventPlan(BaseModel):
    timeline: List[ScheduleItem] = Field(default_factory=list)
    budget_breakdown: List[BudgetLine] = Field(default_factory=list)
    total_cost_inr: int = 0
    summary: str = Field(default="", description="One-paragraph plain-language summary.")


# --- Compliance agent output ---

Decision = Literal["approve_auto", "needs_human", "reject"]


class ComplianceResult(BaseModel):
    decision: Decision = Field(
        description="approve_auto = safe to finalize automatically; "
        "needs_human = a person must approve before booking; "
        "reject = cannot proceed."
    )
    risk_level: Literal["low", "medium", "high"] = "low"
    violations: List[str] = Field(
        default_factory=list, description="Concrete policy/safety problems found."
    )
    rationale: str = Field(default="", description="Short explanation of the verdict.")
    optimizable: bool = Field(
        default=False,
        description="True when the only problem is cost, so the budget optimizer "
        "can try swapping vendors before giving up.",
    )


# --- Insights agent output ---


class WeatherRisk(BaseModel):
    month: Optional[str] = None
    rain_probability: Optional[float] = None
    high_c: Optional[int] = None
    risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    advice: str = ""


class ChecklistItem(BaseModel):
    due: str
    days_before: int
    task: str
    urgent: bool = False


class PlanPackage(BaseModel):
    tier: Literal["lean", "balanced", "luxe"]
    label: str
    blurb: str = ""
    vendors: dict = Field(default_factory=dict, description="category -> vendor name")
    vendor_ids: dict = Field(default_factory=dict, description="category -> vendor id")
    total_cost_inr: int = 0
    per_guest_inr: int = 0
    fits_budget: bool = False


class HealthFactor(BaseModel):
    name: str
    score: int
    max: int
    note: str = ""


class HealthScore(BaseModel):
    score: int = 0
    grade: Literal["A", "B", "C", "D"] = "D"
    factors: List[HealthFactor] = Field(default_factory=list)


class Insights(BaseModel):
    """Everything the insights agent adds on top of the core plan."""

    event_date_iso: Optional[str] = None
    weekday: Optional[str] = None
    days_until: Optional[int] = None
    weather: WeatherRisk = Field(default_factory=WeatherRisk)
    checklist: List[ChecklistItem] = Field(default_factory=list)
    packages: List[PlanPackage] = Field(default_factory=list)
    health: HealthScore = Field(default_factory=HealthScore)
    per_guest_cost_inr: int = 0
