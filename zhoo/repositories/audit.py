"""سجل التدقيق لكل عملية حساسة."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from zhoo.database.db import Database, now

log = logging.getLogger(__name__)


class AuditRepo:
    def __init__(self, db: Database):
        self.db = db
        # مستمعين (مثل قناة السجل): ينادون بعد كل عملية، وخطأهم ما يأثر على العملية
        self.listeners: list[Callable[..., Awaitable[None]]] = []
        self._tasks: set[asyncio.Task] = set()

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
        for listener in self.listeners:
            task = asyncio.get_running_loop().create_task(
                self._safe(listener, action, chat_id, actor_id, target_id, details or {}, result))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _safe(listener, *args) -> None:
        try:
            await listener(*args)
        except Exception:
            log.exception("مستمع السجل فشل")

    async def drain(self) -> None:
        """للاختبارات: ينتظر المستمعين يخلصون."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def recent_actions(self, chat_id: int, prefix: str, limit: int = 15):
        return await self.db.fetchall(
            "SELECT * FROM audit_logs WHERE chat_id = ? AND action LIKE ? ORDER BY id DESC LIMIT ?",
            (chat_id, prefix + "%", limit),
        )

    async def recent(self, limit: int = 10, chat_id: int | None = None):
        if chat_id is None:
            return await self.db.fetchall(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
            )
        return await self.db.fetchall(
            "SELECT * FROM audit_logs WHERE chat_id = ? ORDER BY id DESC LIMIT ?", (chat_id, limit)
        )
