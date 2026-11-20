"""الردود والردود المميزة (مع ذاكرة مؤقتة للكلمات)."""
from __future__ import annotations

from dataclasses import dataclass

from zhoo.database.db import Database, now


@dataclass(frozen=True)
class ReplyItem:
    kind: str
    file_id: str | None
    text: str | None


class RepliesRepo:
    def __init__(self, db: Database):
        self.db = db
        # chat_id -> {special: {trigger: (reply_id, display)}}
        self._cache: dict[int, dict[bool, dict[str, tuple[int, str]]]] = {}

    async def triggers(self, chat_id: int, special: bool) -> dict[str, tuple[int, str]]:
        if chat_id not in self._cache:
            rows = await self.db.fetchall(
                "SELECT id, trigger, display, special FROM replies WHERE chat_id = ?", (chat_id,))
            data: dict[bool, dict[str, tuple[int, str]]] = {False: {}, True: {}}
            for r in rows:
                data[bool(r["special"])][r["trigger"]] = (r["id"], r["display"])
            if len(self._cache) > 5000:
                self._cache.clear()
            self._cache[chat_id] = data
        return self._cache[chat_id][special]

    async def add(self, chat_id: int, trigger: str, display: str, special: bool,
                  items: list[ReplyItem], by: int) -> int:
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "INSERT INTO replies (chat_id, trigger, display, special, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)", (chat_id, trigger, display, int(special), by, now()))
            reply_id = cur.lastrowid
            await conn.executemany(
                "INSERT INTO reply_items (reply_id, position, kind, file_id, text) VALUES (?, ?, ?, ?, ?)",
                [(reply_id, i, it.kind, it.file_id, it.text) for i, it in enumerate(items)])
        self._cache.pop(chat_id, None)
        return reply_id

    async def items(self, reply_id: int) -> list[ReplyItem]:
        rows = await self.db.fetchall(
            "SELECT kind, file_id, text FROM reply_items WHERE reply_id = ? ORDER BY position", (reply_id,))
        return [ReplyItem(r["kind"], r["file_id"], r["text"]) for r in rows]

    async def counts(self, chat_id: int, special: bool):
        return await self.db.fetchall(
            "SELECT r.display, COUNT(i.id) AS n FROM replies r LEFT JOIN reply_items i ON i.reply_id = r.id "
            "WHERE r.chat_id = ? AND r.special = ? GROUP BY r.id ORDER BY r.display", (chat_id, int(special)))

    async def remove(self, chat_id: int, trigger: str, special: bool) -> bool:
        n = await self.db.execute(
            "DELETE FROM replies WHERE chat_id = ? AND trigger = ? AND special = ?", (chat_id, trigger, int(special)))
        self._cache.pop(chat_id, None)
        return n > 0

    async def clear(self, chat_id: int, special: bool) -> int:
        n = await self.db.execute("DELETE FROM replies WHERE chat_id = ? AND special = ?", (chat_id, int(special)))
        self._cache.pop(chat_id, None)
        return n
