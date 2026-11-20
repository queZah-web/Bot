"""سجل السب المحذوف."""
from __future__ import annotations

from zhoo.database.db import Database, now

MAX_TEXT = 1000
RETENTION_DAYS = 30


class SwearLogsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def add(self, chat_id: int, user_id: int, word: str, text: str, action: str,
                  level: int = 2, duration: int | None = None) -> None:
        await self.db.execute(
            "INSERT INTO swear_logs (chat_id, user_id, word, text, level, action, duration, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, word[:100], text[:MAX_TEXT], level, action, duration, now()),
        )

    async def strikes(self, chat_id: int, user_id: int, seconds: int) -> int:
        """عدد مخالفات العضو خلال فترة (للعقوبات التدريجية)."""
        return await self.db.fetchval(
            "SELECT COUNT(*) FROM swear_logs WHERE chat_id = ? AND user_id = ? AND created_at > ?",
            (chat_id, user_id, now() - seconds), default=0,
        )

    async def recent(self, chat_id: int, user_id: int | None = None, limit: int = 10):
        sql = ("SELECT s.*, u.first_name, u.last_name FROM swear_logs s "
               "LEFT JOIN users u ON u.user_id = s.user_id WHERE s.chat_id = ?")
        params: list = [chat_id]
        if user_id is not None:
            sql += " AND s.user_id = ?"
            params.append(user_id)
        sql += " ORDER BY s.id DESC LIMIT ?"
        params.append(limit)
        return await self.db.fetchall(sql, params)

    async def count_since(self, chat_id: int, seconds: int) -> int:
        return await self.db.fetchval(
            "SELECT COUNT(*) FROM swear_logs WHERE chat_id = ? AND created_at > ?",
            (chat_id, now() - seconds), default=0,
        )

    async def clear(self, chat_id: int, user_id: int | None = None) -> int:
        if user_id is not None:
            return await self.db.execute("DELETE FROM swear_logs WHERE chat_id = ? AND user_id = ?",
                                         (chat_id, user_id))
        return await self.db.execute("DELETE FROM swear_logs WHERE chat_id = ?", (chat_id,))

    async def prune(self) -> int:
        return await self.db.execute(
            "DELETE FROM swear_logs WHERE created_at < ?", (now() - RETENTION_DAYS * 86400,)
        )
