"""اختصارات الأوامر لكل مجموعة (مع ذاكرة مؤقتة)."""
from __future__ import annotations

from zhoo.database.db import Database, now


class AliasesRepo:
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[int, dict[str, tuple[str, str]]] = {}

    async def all(self, chat_id: int) -> dict[str, tuple[str, str]]:
        """{الاختصار الموحد: (كما انكتب، مفتاح الأمر)}"""
        if chat_id not in self._cache:
            rows = await self.db.fetchall(
                "SELECT alias, display, command_key FROM command_aliases WHERE chat_id = ?", (chat_id,))
            if len(self._cache) > 5000:
                self._cache.clear()
            self._cache[chat_id] = {r["alias"]: (r["display"], r["command_key"]) for r in rows}
        return self._cache[chat_id]

    async def add(self, chat_id: int, alias: str, display: str, command_key: str, by: int) -> None:
        await self.db.execute(
            "INSERT INTO command_aliases (chat_id, alias, display, command_key, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)", (chat_id, alias, display, command_key, by, now()))
        self._cache.pop(chat_id, None)

    async def remove(self, chat_id: int, alias: str) -> bool:
        n = await self.db.execute("DELETE FROM command_aliases WHERE chat_id = ? AND alias = ?", (chat_id, alias))
        self._cache.pop(chat_id, None)
        return n > 0

    async def clear(self, chat_id: int) -> int:
        n = await self.db.execute("DELETE FROM command_aliases WHERE chat_id = ?", (chat_id,))
        self._cache.pop(chat_id, None)
        return n
