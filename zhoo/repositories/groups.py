"""الوصول لبيانات المجموعات."""
from __future__ import annotations

from zhoo.database.db import Database, now


class GroupsRepo:
    def __init__(self, db: Database):
        self.db = db

    async def upsert(self, chat_id: int, title: str, username: str | None,
                     *, active: bool = True, added_by: int | None = None) -> None:
        ts = now()
        await self.db.execute(
            """
            INSERT INTO groups (chat_id, title, username, is_active, added_by, joined_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (chat_id) DO UPDATE SET
                title      = excluded.title,
                username   = excluded.username,
                is_active  = excluded.is_active,
                added_by   = COALESCE(excluded.added_by, groups.added_by),
                updated_at = excluded.updated_at
            """,
            (chat_id, title or "", username, int(active), added_by, ts, ts),
        )

    async def set_active(self, chat_id: int, active: bool) -> None:
        await self.db.execute(
            "UPDATE groups SET is_active = ?, updated_at = ? WHERE chat_id = ?",
            (int(active), now(), chat_id),
        )

    async def migrate_chat_id(self, old_id: int, new_id: int) -> None:
        """عند تحويل المجموعة لمجموعة خارقة يتغير الايدي، ننقل كل بياناتها."""
        async with self.db.transaction() as conn:
            exists = await (await conn.execute("SELECT 1 FROM groups WHERE chat_id = ?", (new_id,))).fetchone()
            if exists:
                return
            # ننسخ صف المجموعة بالايدي الجديد، ننقل البيانات، وبعدين نحذف القديم
            await conn.execute(
                "INSERT INTO groups (chat_id, title, username, is_active, added_by, joined_at, updated_at) "
                "SELECT ?, title, username, is_active, added_by, joined_at, updated_at FROM groups WHERE chat_id = ?",
                (new_id, old_id),
            )
            await conn.execute("UPDATE group_members SET chat_id = ? WHERE chat_id = ?", (new_id, old_id))
            await conn.execute("UPDATE group_settings SET chat_id = ? WHERE chat_id = ?", (new_id, old_id))
            await conn.execute("UPDATE audit_logs SET chat_id = ? WHERE chat_id = ?", (new_id, old_id))
            await conn.execute("DELETE FROM groups WHERE chat_id = ?", (old_id,))

    async def count_active(self) -> int:
        return await self.db.fetchval("SELECT COUNT(*) FROM groups WHERE is_active = 1", default=0)

    async def count_all(self) -> int:
        return await self.db.fetchval("SELECT COUNT(*) FROM groups", default=0)

    async def recent(self, limit: int = 10):
        return await self.db.fetchall(
            "SELECT chat_id, title, username, is_active, joined_at FROM groups "
            "ORDER BY joined_at DESC LIMIT ?",
            (limit,),
        )
