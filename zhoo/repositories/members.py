"""عضوية المستخدمين ورتبهم وعداد رسائلهم داخل كل مجموعة."""
from __future__ import annotations

from typing import Iterable

from zhoo.core.ranks import Rank, coerce_rank
from zhoo.database.db import Database, now


class MembersRepo:
    def __init__(self, db: Database):
        self.db = db

    async def get_rank(self, chat_id: int, user_id: int) -> Rank:
        value = await self.db.fetchval(
            "SELECT rank FROM group_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id), default=0,
        )
        return coerce_rank(value)

    async def set_rank(self, chat_id: int, user_id: int, rank: Rank, set_by: int) -> Rank:
        """يغير الرتبة ويرجع الرتبة السابقة (عملية ذرية)."""
        ts = now()
        async with self.db.transaction() as conn:
            cur = await conn.execute(
                "SELECT rank FROM group_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)
            )
            row = await cur.fetchone()
            previous = coerce_rank(row[0]) if row else Rank.MEMBER
            await conn.execute(
                """
                INSERT INTO group_members (chat_id, user_id, rank, rank_set_by, rank_set_at, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (chat_id, user_id) DO UPDATE SET
                    rank = excluded.rank,
                    rank_set_by = excluded.rank_set_by,
                    rank_set_at = excluded.rank_set_at
                """,
                (chat_id, user_id, int(rank), set_by, ts, ts, ts),
            )
        return previous

    async def list_ranked(self, chat_id: int):
        return await self.db.fetchall(
            """
            SELECT m.user_id, m.rank, u.first_name, u.last_name, u.username
            FROM group_members m LEFT JOIN users u ON u.user_id = m.user_id
            WHERE m.chat_id = ? AND m.rank > 0
            ORDER BY m.rank DESC, m.rank_set_at ASC
            """,
            (chat_id,),
        )

    async def message_count(self, chat_id: int, user_id: int) -> int:
        return await self.db.fetchval(
            "SELECT msg_count FROM group_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id), default=0,
        )

    async def add_message_counts(self, rows: Iterable[tuple[int, int, int, int]]) -> None:
        """rows = (chat_id, user_id, count, last_seen)"""
        await self.db.executemany(
            """
            INSERT INTO group_members (chat_id, user_id, msg_count, first_seen, last_seen)
            SELECT ?1, ?2, ?3, ?4, ?4 WHERE EXISTS (SELECT 1 FROM groups WHERE chat_id = ?1)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET
                msg_count = group_members.msg_count + excluded.msg_count,
                last_seen = excluded.last_seen
            """,
            rows,
        )

    async def top_active(self, chat_id: int, limit: int = 10):
        return await self.db.fetchall(
            """
            SELECT m.user_id, m.msg_count, u.first_name, u.last_name
            FROM group_members m LEFT JOIN users u ON u.user_id = m.user_id
            WHERE m.chat_id = ? AND m.msg_count > 0
            ORDER BY m.msg_count DESC LIMIT ?
            """,
            (chat_id, limit),
        )
