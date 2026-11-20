"""الخبرة والفوز بالمسابقات."""
from __future__ import annotations

import time

from zhoo.database.db import Database, now


def today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def day_ago(days: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))


class LevelsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def add_xp(self, chat_id: int, user_id: int, amount: int) -> tuple[int, int]:
        """يضيف خبرة ذرياً ويرجع (القديمة، الجديدة). ما يسوي شي إذا المجموعة مو مسجلة."""
        ts = now()
        async with self.db.transaction() as conn:
            cur = await conn.execute("SELECT 1 FROM groups WHERE chat_id = ?", (chat_id,))
            if await cur.fetchone() is None:
                return 0, 0
            cur = await conn.execute("SELECT xp FROM group_members WHERE chat_id = ? AND user_id = ?",
                                     (chat_id, user_id))
            row = await cur.fetchone()
            old = row[0] if row else 0
            await conn.execute(
                "INSERT INTO group_members (chat_id, user_id, xp, first_seen, last_seen) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (chat_id, user_id) DO UPDATE SET xp = group_members.xp + excluded.xp",
                (chat_id, user_id, amount, ts, ts))
            await conn.execute(
                "INSERT INTO xp_daily (chat_id, user_id, day, xp) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (chat_id, user_id, day) DO UPDATE SET xp = xp_daily.xp + excluded.xp",
                (chat_id, user_id, today(), amount))
            return old, old + amount

    async def add_win(self, chat_id: int, user_id: int) -> int:
        await self.db.execute("UPDATE group_members SET wins = wins + 1 WHERE chat_id = ? AND user_id = ?",
                              (chat_id, user_id))
        return await self.db.fetchval("SELECT wins FROM group_members WHERE chat_id = ? AND user_id = ?",
                                      (chat_id, user_id), default=0)

    async def get(self, chat_id: int, user_id: int) -> tuple[int, int]:
        row = await self.db.fetchone("SELECT xp, wins FROM group_members WHERE chat_id = ? AND user_id = ?",
                                     (chat_id, user_id))
        return (row["xp"], row["wins"]) if row else (0, 0)

    async def position(self, chat_id: int, xp: int) -> int:
        return 1 + await self.db.fetchval("SELECT COUNT(*) FROM group_members WHERE chat_id = ? AND xp > ?",
                                          (chat_id, xp), default=0)

    async def top(self, chat_id: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT m.user_id, m.xp AS value, u.first_name, u.last_name FROM group_members m "
            "LEFT JOIN users u ON u.user_id = m.user_id WHERE m.chat_id = ? AND m.xp > 0 "
            "ORDER BY m.xp DESC LIMIT ?", (chat_id, limit))

    async def top_since(self, chat_id: int, days: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT d.user_id, SUM(d.xp) AS value, u.first_name, u.last_name FROM xp_daily d "
            "LEFT JOIN users u ON u.user_id = d.user_id WHERE d.chat_id = ? AND d.day > ? "
            "GROUP BY d.user_id ORDER BY value DESC LIMIT ?", (chat_id, day_ago(days), limit))

    async def top_wins(self, chat_id: int, limit: int = 10):
        return await self.db.fetchall(
            "SELECT m.user_id, m.wins AS value, u.first_name, u.last_name FROM group_members m "
            "LEFT JOIN users u ON u.user_id = m.user_id WHERE m.chat_id = ? AND m.wins > 0 "
            "ORDER BY m.wins DESC LIMIT ?", (chat_id, limit))

    async def prune_daily(self, keep_days: int = 40) -> int:
        return await self.db.execute("DELETE FROM xp_daily WHERE day < ?", (day_ago(keep_days),))
