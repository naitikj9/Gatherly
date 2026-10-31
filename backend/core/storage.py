"""Plan storage behind one small interface.

MongoPlanStore is the production store. MemoryPlanStore is used when no
MONGO_URL is configured (local dev, tests), so the API runs without a database.
Both also hold idempotency keys, so a retried POST never plans the same event
twice, and guest RSVPs (one response per guest name per plan).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def summarize(doc: dict) -> dict:
    """Compact row for the history list."""
    state = doc.get("state") or {}
    req = state.get("requirements") or {}
    return {
        "plan_id": doc["plan_id"],
        "request": doc.get("request", ""),
        "status": state.get("status"),
        "city": req.get("city"),
        "event_type": req.get("event_type"),
        "total_cost_inr": (state.get("plan") or {}).get("total_cost_inr"),
        "budget_inr": req.get("budget_inr"),
        "guest_count": req.get("guest_count"),
        "health_score": ((state.get("insights") or {}).get("health") or {}).get("score"),
        "updated_at": doc.get("updated_at"),
    }


class PlanStore(Protocol):
    name: str

    async def upsert(self, plan_id: str, doc: dict) -> None: ...
    async def get(self, plan_id: str) -> Optional[dict]: ...
    async def list(self, limit: int, pending_only: bool) -> List[dict]: ...
    async def delete(self, plan_id: str) -> bool: ...
    async def ping(self) -> bool: ...
    async def get_idempotency(self, key: str) -> Optional[dict]: ...
    async def put_idempotency(self, key: str, record: dict) -> bool: ...
    async def upsert_rsvp(self, plan_id: str, rsvp: dict) -> bool: ...
    async def list_rsvps(self, plan_id: str) -> List[dict]: ...
    async def count_rsvps(self, plan_id: str) -> int: ...


def rsvp_key(name: str) -> str:
    """Same guest, same row: 'Asha  Rao' and 'asha rao' are one response."""
    return " ".join(name.lower().split())


class MemoryPlanStore:
    """Process-local store. Fine for dev and tests, not for multiple workers."""

    name = "memory"

    def __init__(self) -> None:
        self._plans: Dict[str, dict] = {}
        self._idem: Dict[str, dict] = {}
        self._rsvps: Dict[str, Dict[str, dict]] = {}
        self._lock = asyncio.Lock()

    async def upsert(self, plan_id: str, doc: dict) -> None:
        async with self._lock:
            current = self._plans.get(plan_id, {})
            self._plans[plan_id] = {**current, **doc, "plan_id": plan_id, "updated_at": _now()}

    async def get(self, plan_id: str) -> Optional[dict]:
        doc = self._plans.get(plan_id)
        return dict(doc) if doc else None

    async def list(self, limit: int, pending_only: bool) -> List[dict]:
        docs = sorted(self._plans.values(), key=lambda d: d.get("updated_at", ""), reverse=True)
        if pending_only:
            docs = [d for d in docs if (d.get("state") or {}).get("status") == "awaiting_approval"]
        return [dict(d) for d in docs[:limit]]

    async def delete(self, plan_id: str) -> bool:
        async with self._lock:
            self._rsvps.pop(plan_id, None)
            return self._plans.pop(plan_id, None) is not None

    async def ping(self) -> bool:
        return True

    async def get_idempotency(self, key: str) -> Optional[dict]:
        return self._idem.get(key)

    async def put_idempotency(self, key: str, record: dict) -> bool:
        """Insert-if-absent. False if another request already claimed the key."""
        async with self._lock:
            if key in self._idem:
                return False
            self._idem[key] = record
            return True

    async def upsert_rsvp(self, plan_id: str, rsvp: dict) -> bool:
        """Save a response; True if it was new, False if it replaced an earlier one."""
        key = rsvp_key(rsvp["name"])
        async with self._lock:
            rows = self._rsvps.setdefault(plan_id, {})
            is_new = key not in rows
            rows[key] = {**rsvp, "updated_at": _now()}
            return is_new

    async def list_rsvps(self, plan_id: str) -> List[dict]:
        rows = self._rsvps.get(plan_id, {}).values()
        return sorted((dict(r) for r in rows), key=lambda r: r["updated_at"])

    async def count_rsvps(self, plan_id: str) -> int:
        return len(self._rsvps.get(plan_id, {}))


class MongoPlanStore:
    name = "mongo"

    def __init__(self, url: str, db_name: str) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient

        self._client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=3000)
        db = self._client[db_name]
        self._plans = db["plans"]
        self._idem = db["idempotency_keys"]
        self._rsvps = db["rsvps"]
        self._indexes_ready = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        await self._plans.create_index("plan_id", unique=True)
        await self._plans.create_index([("updated_at", -1)])
        await self._plans.create_index("state.status")
        await self._idem.create_index("key", unique=True)
        # idempotency keys only need to live a day
        await self._idem.create_index("created_at_dt", expireAfterSeconds=86400)
        await self._rsvps.create_index([("plan_id", 1), ("key", 1)], unique=True)
        self._indexes_ready = True

    async def upsert(self, plan_id: str, doc: dict) -> None:
        await self._ensure_indexes()
        await self._plans.update_one(
            {"plan_id": plan_id},
            {"$set": {**doc, "plan_id": plan_id, "updated_at": _now()}},
            upsert=True,
        )

    async def get(self, plan_id: str) -> Optional[dict]:
        return await self._plans.find_one({"plan_id": plan_id}, {"_id": 0})

    async def list(self, limit: int, pending_only: bool) -> List[dict]:
        query = {"state.status": "awaiting_approval"} if pending_only else {}
        cursor = self._plans.find(query, {"_id": 0}).sort("updated_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def delete(self, plan_id: str) -> bool:
        res = await self._plans.delete_one({"plan_id": plan_id})
        await self._rsvps.delete_many({"plan_id": plan_id})
        return res.deleted_count > 0

    async def ping(self) -> bool:
        try:
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    async def get_idempotency(self, key: str) -> Optional[dict]:
        return await self._idem.find_one({"key": key}, {"_id": 0, "created_at_dt": 0})

    async def put_idempotency(self, key: str, record: dict) -> bool:
        from pymongo.errors import DuplicateKeyError

        await self._ensure_indexes()
        try:
            await self._idem.insert_one(
                {**record, "key": key, "created_at_dt": datetime.now(timezone.utc)}
            )
            return True
        except DuplicateKeyError:
            return False

    async def upsert_rsvp(self, plan_id: str, rsvp: dict) -> bool:
        await self._ensure_indexes()
        res = await self._rsvps.update_one(
            {"plan_id": plan_id, "key": rsvp_key(rsvp["name"])},
            {"$set": {**rsvp, "updated_at": _now()}},
            upsert=True,
        )
        return res.upserted_id is not None

    async def list_rsvps(self, plan_id: str) -> List[dict]:
        cursor = self._rsvps.find({"plan_id": plan_id}, {"_id": 0, "plan_id": 0, "key": 0})
        return await cursor.sort("updated_at", 1).to_list(length=None)

    async def count_rsvps(self, plan_id: str) -> int:
        return await self._rsvps.count_documents({"plan_id": plan_id})


def make_store(mongo_url: str, db_name: str) -> PlanStore:
    return MongoPlanStore(mongo_url, db_name) if mongo_url else MemoryPlanStore()
