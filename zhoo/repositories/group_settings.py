"""إعدادات مستقلة لكل مجموعة مع ذاكرة مؤقتة وسجل تغييرات."""
from __future__ import annotations

from zhoo.database.db import Database, now

DEFAULTS: dict[str, str] = {
    "warn_limit": "3",
    "warn_action": "mute",   # mute | kick | ban
}


class GroupSettingsRepo:
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[tuple[int, str], str] = {}

    async def get(self, chat_id: int, key: str) -> str:
        ck = (chat_id, key)
        if ck in self._cache:
            return self._cache[ck]
        value = await self.db.fetchval(
            "SELECT value FROM group_settings WHERE chat_id = ? AND key = ?", (chat_id, key)
        )
        if value is None:
            value = DEFAULTS.get(key, "")
        if len(self._cache) > 20_000:
            self._cache.clear()
        self._cache[ck] = value
        return value

    async def get_int(self, chat_id: int, key: str) -> int:
        try:
            return int(await self.get(chat_id, key))
        except ValueError:
            return int(DEFAULTS[key])

    async def set(self, chat_id: int, key: str, value: str, by: int) -> str:
        """يحفظ القيمة ويرجع القيمة السابقة."""
        previous = await self.get(chat_id, key)
        await self.db.execute(
            "INSERT INTO group_settings (chat_id, key, value, updated_by, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (chat_id, key) DO UPDATE SET value = excluded.value, "
            "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
            (chat_id, key, value, by, now()),
        )
        self._cache[(chat_id, key)] = value
        return previous
