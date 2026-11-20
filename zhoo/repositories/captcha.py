"""الأعضاء الجدد اللي ينتظرون التحقق."""
from __future__ import annotations

from zhoo.database.db import Database, now


class CaptchaRepo:
    def __init__(self, db: Database):
        self.db = db

    async def add(self, chat_id: int, user_id: int, message_id: int | None, ttl: int) -> None:
        ts = now()
        await self.db.execute(
            "INSERT INTO captcha_pending (chat_id, user_id, message_id, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT (chat_id, user_id) DO UPDATE SET "
            "message_id = excluded.message_id, expires_at = excluded.expires_at",
            (chat_id, user_id, message_id, ts + ttl, ts),
        )

    async def set_message(self, chat_id: int, user_id: int, message_id: int) -> None:
        await self.db.execute(
            "UPDATE captcha_pending SET message_id = ? WHERE chat_id = ? AND user_id = ?",
            (message_id, chat_id, user_id),
        )

    async def pop(self, chat_id: int, user_id: int):
        """يحذف الطلب ويرجعه (أو None إذا ما موجود)."""
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "SELECT * FROM captcha_pending WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
            )
            row = await cur.fetchone()
            if row is not None:
                await conn.execute(
                    "DELETE FROM captcha_pending WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
                )
            return row

    async def expired(self, limit: int = 50):
        return await self.db.fetchall(
            "SELECT * FROM captcha_pending WHERE expires_at <= ? ORDER BY expires_at LIMIT ?", (now(), limit)
        )
