"""سجل التدقيق لكل عملية حساسة."""
from __future__ import annotations

import json
import logging
from typing import Any

from zhoo.database.db import Database, now

log = logging.getLogger(__name__)


class AuditRepo:
    def __init__(self, db: Database):
        self.db = db

    async def log(self, action: str, *, chat_id: int | None = None, actor_id: int | None = None,
                  target_id: int | None = None, details: dict[str, Any] | None = None,
                  result: str = "ok") -> None:
        try:
            await self.db.execute(
                "INSERT INTO audit_logs (chat_id, actor_id, target_id, action, details, result, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chat_id, actor_id, target_id, action,
                 json.dumps(details, ensure_ascii=False) if details else None, result, now()),
            )
        except Exception:  # السجل لا يجب أن يكسر العملية الأصلية
            log.exception("تعذر كتابة سجل التدقيق")

    async def recent(self, limit: int = 10, chat_id: int | None = None):
        if chat_id is None:
            return await self.db.fetchall(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
            )
        return await self.db.fetchall(
            "SELECT * FROM audit_logs WHERE chat_id = ? ORDER BY id DESC LIMIT ?", (chat_id, limit)
        )
