"""قاموس السب الدائم (عام + لكل مجموعة) والاستثناءات."""
from __future__ import annotations

from zhoo.database.db import Database, now

GLOBAL = 0


class SwearWordsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def words(self, chat_id: int):
        return await self.db.fetchall(
            "SELECT norm, word, level FROM swear_words WHERE chat_id = ? ORDER BY level DESC, norm", (chat_id,))

    async def add(self, chat_id: int, word: str, norm: str, level: int, by: int) -> None:
        await self.db.execute(
            "INSERT INTO swear_words (chat_id, norm, word, level, added_by, created_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (chat_id, norm) DO UPDATE SET word = excluded.word, level = excluded.level, "
            "added_by = excluded.added_by",
            (chat_id, norm, word[:80], level, by, now()),
        )

    async def remove(self, chat_id: int, norm: str) -> bool:
        return await self.db.execute("DELETE FROM swear_words WHERE chat_id = ? AND norm = ?", (chat_id, norm)) > 0

    async def count(self, chat_id: int) -> int:
        return await self.db.fetchval("SELECT COUNT(*) FROM swear_words WHERE chat_id = ?", (chat_id,), default=0)

    async def allowed(self, chat_id: int):
        return await self.db.fetchall("SELECT norm, word FROM swear_allow WHERE chat_id = ? ORDER BY norm", (chat_id,))

    async def allow(self, chat_id: int, word: str, norm: str, by: int) -> None:
        await self.db.execute(
            "INSERT INTO swear_allow (chat_id, norm, word, added_by, created_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (chat_id, norm) DO UPDATE SET word = excluded.word",
            (chat_id, norm, word[:80], by, now()),
        )

    async def unallow(self, chat_id: int, norm: str) -> bool:
        return await self.db.execute("DELETE FROM swear_allow WHERE chat_id = ? AND norm = ?", (chat_id, norm)) > 0
