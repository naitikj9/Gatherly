"""Plan storage behind one small interface.

MongoPlanStore is the production store. MemoryPlanStore is used when no
MONGO_URL is configured (local dev, tests), so the API runs without a database.
Both also hold idempotency keys, so a retried POST never plans the same event
twice, guest RSVPs (one response per guest name per plan) and the party
playlist (song requests with one vote per guest device).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, Tuple


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
    async def add_song(self, plan_id: str, song: dict, voter: str) -> Tuple[dict, bool]: ...
    async def toggle_vote(self, plan_id: str, song_id: str, voter: str) -> Optional[dict]: ...
    async def list_songs(self, plan_id: str) -> List[dict]: ...
    async def count_songs(self, plan_id: str) -> int: ...
    async def delete_song(self, plan_id: str, song_id: str) -> bool: ...


def song_key(title: str) -> str:
    """'Kesariya ' and 'kesariya' are one request, whoever typed the artist."""
    return " ".join(title.lower().split())


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
        self._songs: Dict[str, Dict[str, dict]] = {}  # plan_id -> song id -> song
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
            self._songs.pop(plan_id, None)
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

    async def add_song(self, plan_id: str, song: dict, voter: str) -> Tuple[dict, bool]:
        """Add a request, or count it as a vote if the song is already on the list."""
        key = song_key(song["title"])
        async with self._lock:
            songs = self._songs.setdefault(plan_id, {})
            for row in songs.values():
                if row["key"] == key:
                    if voter not in row["voters"]:
                        row["voters"].append(voter)
                    if not row.get("artist") and song.get("artist"):
                        row["artist"] = song["artist"]
                    return _copy_song(row), False
            row = {**song, "id": uuid.uuid4().hex[:12], "key": key,
                   "voters": [voter], "created_at": _now()}
            songs[row["id"]] = row
            return _copy_song(row), True

    async def toggle_vote(self, plan_id: str, song_id: str, voter: str) -> Optional[dict]:
        async with self._lock:
            row = self._songs.get(plan_id, {}).get(song_id)
            if row is None:
                return None
            if voter in row["voters"]:
                row["voters"].remove(voter)
            else:
                row["voters"].append(voter)
            return _copy_song(row)

    async def list_songs(self, plan_id: str) -> List[dict]:
        return [_copy_song(r) for r in self._songs.get(plan_id, {}).values()]

    async def count_songs(self, plan_id: str) -> int:
        return len(self._songs.get(plan_id, {}))

    async def delete_song(self, plan_id: str, song_id: str) -> bool:
        async with self._lock:
            return self._songs.get(plan_id, {}).pop(song_id, None) is not None


def _copy_song(row: dict) -> dict:
    return {**row, "voters": list(row["voters"])}


class MongoPlanStore:
    name = "mongo"

    def __init__(self, url: str, db_name: str) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient

        self._client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=3000)
        db = self._client[db_name]
        self._plans = db["plans"]
        self._idem = db["idempotency_keys"]
        self._rsvps = db["rsvps"]
        self._songs = db["songs"]
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
        await self._songs.create_index([("plan_id", 1), ("key", 1)], unique=True)
        await self._songs.create_index([("plan_id", 1), ("id", 1)], unique=True)
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
        await self._songs.delete_many({"plan_id": plan_id})
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

    async def add_song(self, plan_id: str, song: dict, voter: str) -> Tuple[dict, bool]:
        from pymongo import ReturnDocument
        from pymongo.errors import DuplicateKeyError

        await self._ensure_indexes()
        key = song_key(song["title"])
        before = await self._songs.find_one({"plan_id": plan_id, "key": key}, {"_id": 1})
        update = {"$setOnInsert": {**song, "id": uuid.uuid4().hex[:12], "created_at": _now()},
                  "$addToSet": {"voters": voter}}
        opts = {"projection": {"_id": 0, "plan_id": 0}, "return_document": ReturnDocument.AFTER}
        try:
            row = await self._songs.find_one_and_update(
                {"plan_id": plan_id, "key": key}, update, upsert=True, **opts)
        except DuplicateKeyError:
            # another guest added the same song a moment ago: count this as a vote
            row = await self._songs.find_one_and_update(
                {"plan_id": plan_id, "key": key}, {"$addToSet": {"voters": voter}}, **opts)
            before = row
        if before is not None and song.get("artist") and not row.get("artist"):
            await self._songs.update_one({"plan_id": plan_id, "key": key, "artist": ""},
                                         {"$set": {"artist": song["artist"]}})
            row = {**row, "artist": song["artist"]}
        return row, before is None

    async def toggle_vote(self, plan_id: str, song_id: str, voter: str) -> Optional[dict]:
        query = {"plan_id": plan_id, "id": song_id}
        # take the vote back if this voter has one; otherwise add it
        res = await self._songs.update_one({**query, "voters": voter}, {"$pull": {"voters": voter}})
        if res.modified_count == 0:
            await self._songs.update_one(query, {"$addToSet": {"voters": voter}})
        return await self._songs.find_one(query, {"_id": 0, "plan_id": 0})

    async def list_songs(self, plan_id: str) -> List[dict]:
        cursor = self._songs.find({"plan_id": plan_id}, {"_id": 0, "plan_id": 0})
        return await cursor.to_list(length=None)

    async def count_songs(self, plan_id: str) -> int:
        return await self._songs.count_documents({"plan_id": plan_id})

    async def delete_song(self, plan_id: str, song_id: str) -> bool:
        res = await self._songs.delete_one({"plan_id": plan_id, "id": song_id})
        return res.deleted_count > 0


def make_store(mongo_url: str, db_name: str) -> PlanStore:
    return MongoPlanStore(mongo_url, db_name) if mongo_url else MemoryPlanStore()
