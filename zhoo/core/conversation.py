"""محادثات بخطوات: البوت يسأل، والشخص يجاوب برسالته الجاية (مثل «اضف رد» و«اضف امر»).

- لكل (مجموعة، شخص) محادثة وحدة بس.
- تنتهي تلقائياً بعد 5 دقايق بدون رد.
- «الغاء» تلغيها بأي خطوة.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

TTL = 300
CANCEL_WORDS = {"الغاء", "الغا", "cancel"}


@dataclass
class Pending:
    kind: str
    step: str
    data: dict[str, Any] = field(default_factory=dict)
    expires: float = 0.0


class Conversations:
    def __init__(self) -> None:
        self._items: dict[tuple[int, int], Pending] = {}

    def start(self, chat_id: int, user_id: int, kind: str, step: str, **data: Any) -> Pending:
        if len(self._items) > 5000:
            now = time.monotonic()
            self._items = {k: v for k, v in self._items.items() if v.expires > now}
        p = Pending(kind, step, dict(data), time.monotonic() + TTL)
        self._items[(chat_id, user_id)] = p
        return p

    def get(self, chat_id: int, user_id: int) -> Pending | None:
        p = self._items.get((chat_id, user_id))
        if p is None:
            return None
        if p.expires < time.monotonic():
            self._items.pop((chat_id, user_id), None)
            return None
        p.expires = time.monotonic() + TTL  # كل جواب يمدد المهلة
        return p

    def end(self, chat_id: int, user_id: int) -> None:
        self._items.pop((chat_id, user_id), None)


# نوع المحادثة ← الدالة اللي تعالج الرسالة الجاية
Handler = Callable[..., Awaitable[None]]
HANDLERS: dict[str, Handler] = {}


def handler(kind: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn
    return deco
