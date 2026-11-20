"""الصلاحيات المخصصة لكل شخص وقائمة المنع (مع ذاكرة مؤقتة)."""
from __future__ import annotations

from zhoo.database.db import Database, now


class MemberPermsRepo:
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[tuple[int, int], tuple[frozenset[str], frozenset[str]]] = {}

    async def get(self, chat_id: int, user_id: int) -> tuple[frozenset[str], frozenset[str]]:
        key = (chat_id, user_id)
        if key in self._cache:
            return self._cache[key]
        row = await self.db.fetchone("SELECT allow, deny FROM member_perms WHERE chat_id = ? AND user_id = ?", key)
        value = (frozenset(filter(None, row["allow"].split(","))), frozenset(filter(None, row["deny"].split(","))))\
            if row else (frozenset(), frozenset())
        if len(self._cache) > 50_000:
            self._cache.clear()
        self._cache[key] = value
        return value

    async def set(self, chat_id: int, user_id: int, allow: set[str], deny: set[str], by: int) -> None:
        if not allow and not deny:
            await self.clear(chat_id, user_id)
            return
        await self.db.execute(
            "INSERT INTO member_perms (chat_id, user_id, allow, deny, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (chat_id, user_id) DO UPDATE SET allow = excluded.allow, deny = excluded.deny, "
            "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
            (chat_id, user_id, ",".join(sorted(allow)), ",".join(sorted(deny)), by, now()),
        )
        self._cache[(chat_id, user_id)] = (frozenset(allow), frozenset(deny))

    async def clear(self, chat_id: int, user_id: int) -> None:
        await self.db.execute("DELETE FROM member_perms WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self._cache.pop((chat_id, user_id), None)


class FiltersRepo:
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[int, dict[str, dict[str, str]]] = {}

    async def all(self, chat_id: int) -> dict[str, dict[str, str]]:
        """النوع ← {القيمة: الوصف}"""
        if chat_id in self._cache:
            return self._cache[chat_id]
        out: dict[str, dict[str, str]] = {}
        for r in await self.db.fetchall("SELECT kind, value, label FROM filters WHERE chat_id = ?", (chat_id,)):
            out.setdefault(r["kind"], {})[r["value"]] = r["label"]
        if len(self._cache) > 5000:
            self._cache.clear()
        self._cache[chat_id] = out
        return out

    async def add(self, chat_id: int, kind: str, value: str, label: str, by: int) -> bool:
        if value in (await self.all(chat_id)).get(kind, {}):
            return False
        await self.db.execute(
            "INSERT OR IGNORE INTO filters (chat_id, kind, value, label, added_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, kind, value, label[:80], by, now()))
        self._cache.pop(chat_id, None)
        return True

    async def remove(self, chat_id: int, kind: str, value: str) -> bool:
        n = await self.db.execute("DELETE FROM filters WHERE chat_id = ? AND kind = ? AND value = ?",
                                  (chat_id, kind, value))
        self._cache.pop(chat_id, None)
        return n > 0

    async def clear(self, chat_id: int) -> int:
        n = await self.db.execute("DELETE FROM filters WHERE chat_id = ?", (chat_id,))
        self._cache.pop(chat_id, None)
        return n

    async def count(self, chat_id: int) -> int:
        return sum(len(v) for v in (await self.all(chat_id)).values())
