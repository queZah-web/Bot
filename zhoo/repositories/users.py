"""الوصول لبيانات المستخدمين."""
from __future__ import annotations

from dataclasses import dataclass

from zhoo.database.db import Database, now


@dataclass(frozen=True)
class UserRecord:
    user_id: int
    first_name: str
    last_name: str | None
    username: str | None
    is_bot: bool

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p) or str(self.user_id)


class UsersRepo:
    def __init__(self, db: Database):
        self.db = db

    async def upsert(self, user_id: int, first_name: str, last_name: str | None,
                     username: str | None, is_bot: bool) -> None:
        ts = now()
        await self.db.execute(
            """
            INSERT INTO users (user_id, first_name, last_name, username, is_bot, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                username   = excluded.username,
                is_bot     = excluded.is_bot,
                last_seen  = excluded.last_seen
            """,
            (user_id, first_name or "", last_name, username, int(is_bot), ts, ts),
        )
        if username:
            # اليوزر لا يكون إلا لشخص واحد؛ نمسحه عن أي سجل قديم
            await self.db.execute(
                "UPDATE users SET username = NULL WHERE lower(username) = lower(?) AND user_id != ?",
                (username, user_id),
            )

    async def get(self, user_id: int) -> UserRecord | None:
        row = await self.db.fetchone(
            "SELECT user_id, first_name, last_name, username, is_bot FROM users WHERE user_id = ?",
            (user_id,),
        )
        return _to_record(row)

    async def find_by_username(self, username: str) -> UserRecord | None:
        username = username.lstrip("@").strip()
        if not username:
            return None
        row = await self.db.fetchone(
            "SELECT user_id, first_name, last_name, username, is_bot FROM users "
            "WHERE lower(username) = lower(?)",
            (username,),
        )
        return _to_record(row)

    async def count(self) -> int:
        return await self.db.fetchval("SELECT COUNT(*) FROM users WHERE is_bot = 0", default=0)


def _to_record(row) -> UserRecord | None:
    if row is None:
        return None
    return UserRecord(row["user_id"], row["first_name"], row["last_name"], row["username"], bool(row["is_bot"]))
