"""إعدادات البوت العامة (مثل وضع الصيانة) مع تخزين مؤقت بالذاكرة."""
from __future__ import annotations

from zhoo.database.db import Database, now


class BotSettingsRepo:
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[str, str | None] = {}

    async def load(self) -> None:
        rows = await self.db.fetchall("SELECT key, value FROM bot_settings")
        self._cache = {r["key"]: r["value"] for r in rows}

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._cache.get(key, default)

    def get_bool(self, key: str) -> bool:
        return self._cache.get(key) == "1"

    async def set(self, key: str, value: str | None) -> None:
        await self.db.execute(
            "INSERT INTO bot_settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now()),
        )
        self._cache[key] = value
