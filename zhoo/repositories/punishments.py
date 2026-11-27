"""سجل العقوبات والتحذيرات."""
from __future__ import annotations

from zhoo.database.db import Database, now

# العقوبات التي تبقى «فعّالة» (الطرد لحظي فقط وينسجل للتاريخ)
LASTING = ("ban", "mute", "restrict")


class PunishmentsRepo:
    def __init__(self, db: Database):
        self.db = db

    # ── العقوبات ─────────────────────────────────
    async def add(self, chat_id: int, user_id: int, kind: str, actor_id: int,
                  reason: str | None, until: int | None) -> int:
        """يسجل عقوبة جديدة، ويُنهي أي عقوبة فعّالة سابقة من نفس النوع (ذرياً)."""
        ts = now()
        async with self.db.transaction() as conn:
            if kind in LASTING:
                await conn.execute(
                    "UPDATE punishments SET active = 0, lifted_at = ?, lifted_by = ? "
                    "WHERE chat_id = ? AND user_id = ? AND kind = ? AND active = 1",
                    (ts, actor_id, chat_id, user_id, kind),
                )
            cur = await conn.execute(
                "INSERT INTO punishments (chat_id, user_id, kind, actor_id, reason, until, active, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (chat_id, user_id, kind, actor_id, reason, until, int(kind in LASTING), ts),
            )
            return cur.lastrowid

    async def lift(self, chat_id: int, user_id: int, kind: str, by: int | None) -> int:
        """يُنهي العقوبة الفعالة ويرجع عدد السجلات المتأثرة."""
        return await self.db.execute(
            "UPDATE punishments SET active = 0, lifted_at = ?, lifted_by = ? "
            "WHERE chat_id = ? AND user_id = ? AND kind = ? AND active = 1",
            (now(), by, chat_id, user_id, kind),
        )

    async def is_active(self, chat_id: int, user_id: int, kind: str) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM punishments WHERE chat_id = ? AND user_id = ? AND kind = ? AND active = 1 "
            "AND (until IS NULL OR until > ?)",
            (chat_id, user_id, kind, now()),
        )
        return row is not None

    async def list_active(self, chat_id: int, kind: str, limit: int = 50):
        return await self.db.fetchall(
            """
            SELECT p.user_id, p.until, p.reason, u.first_name, u.last_name
            FROM punishments p LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.chat_id = ? AND p.kind = ? AND p.active = 1 AND (p.until IS NULL OR p.until > ?)
            ORDER BY p.created_at DESC LIMIT ?
            """,
            (chat_id, kind, now(), limit),
        )

    async def history(self, chat_id: int, user_id: int | None = None, limit: int = 15):
        if user_id is None:
            return await self.db.fetchall(
                """
                SELECT p.*, u.first_name, u.last_name FROM punishments p
                LEFT JOIN users u ON u.user_id = p.user_id
                WHERE p.chat_id = ? ORDER BY p.id DESC LIMIT ?
                """,
                (chat_id, limit),
            )
        return await self.db.fetchall(
            """
            SELECT p.*, u.first_name, u.last_name FROM punishments p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.chat_id = ? AND p.user_id = ? ORDER BY p.id DESC LIMIT ?
            """,
            (chat_id, user_id, limit),
        )

    async def expire(self) -> int:
        """العقوبات المؤقتة اللي انتهى وقتها تصير غير فعالة (تيليجرام يرفعها تلقائياً)."""
        ts = now()
        return await self.db.execute(
            "UPDATE punishments SET active = 0, lifted_at = until "
            "WHERE active = 1 AND until IS NOT NULL AND until <= ?",
            (ts,),
        )

    # ── التحذيرات ─────────────────────────────────
    async def add_warning(self, chat_id: int, user_id: int, actor_id: int, reason: str | None) -> int:
        async with self.db.transaction() as conn:
            await conn.execute(
                "INSERT INTO warnings (chat_id, user_id, actor_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, actor_id, reason, now()),
            )
            cur = await conn.execute(
                "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ? AND active = 1",
                (chat_id, user_id),
            )
            return (await cur.fetchone())[0]

    async def warning_count(self, chat_id: int, user_id: int) -> int:
        return await self.db.fetchval(
            "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ? AND active = 1",
            (chat_id, user_id), default=0,
        )

    async def list_warned(self, chat_id: int, limit: int = 50):
        """اللي عندهم تحذيرات فعّالة، الأكثر أول."""
        return await self.db.fetchall(
            "SELECT w.user_id, COUNT(*) AS n, NULL AS until, u.first_name, u.last_name FROM warnings w "
            "LEFT JOIN users u ON u.user_id = w.user_id WHERE w.chat_id = ? AND w.active = 1 "
            "GROUP BY w.user_id ORDER BY n DESC, MAX(w.created_at) DESC LIMIT ?", (chat_id, limit))

    async def clear_warnings(self, chat_id: int, user_id: int) -> int:
        return await self.db.execute(
            "UPDATE warnings SET active = 0 WHERE chat_id = ? AND user_id = ? AND active = 1",
            (chat_id, user_id),
        )
