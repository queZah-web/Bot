"""تتبع المستخدمين والمجموعات وعداد الرسائل بدون إرهاق قاعدة البيانات.

- بيانات المستخدم تُحدّث فقط إذا تغيرت أو مرت ساعة.
- عداد الرسائل يتجمع بالذاكرة ويُكتب دفعة واحدة كل دقيقة.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from telegram import Chat, User

from zhoo.repositories.groups import GroupsRepo
from zhoo.repositories.members import MembersRepo
from zhoo.repositories.users import UsersRepo

log = logging.getLogger(__name__)

REFRESH_SECONDS = 3600
MAX_CACHE = 50_000


class Tracker:
    def __init__(self, users: UsersRepo, groups: GroupsRepo, members: MembersRepo):
        self.users = users
        self.groups = groups
        self.members = members
        self._user_seen: dict[int, tuple[tuple, float]] = {}
        self._group_seen: dict[int, tuple[tuple, float]] = {}
        self._counts: dict[tuple[int, int], int] = defaultdict(int)

    async def track_user(self, user: User | None) -> None:
        if user is None:
            return
        snap = (user.first_name, user.last_name, user.username, user.is_bot)
        prev = self._user_seen.get(user.id)
        t = time.monotonic()
        if prev and prev[0] == snap and t - prev[1] < REFRESH_SECONDS:
            return
        if len(self._user_seen) > MAX_CACHE:
            self._user_seen.clear()
        self._user_seen[user.id] = (snap, t)
        await self.users.upsert(user.id, user.first_name, user.last_name, user.username, user.is_bot)

    async def track_group(self, chat: Chat | None) -> None:
        if chat is None or chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
            return
        snap = (chat.title, chat.username)
        prev = self._group_seen.get(chat.id)
        t = time.monotonic()
        if prev and prev[0] == snap and t - prev[1] < REFRESH_SECONDS:
            return
        self._group_seen[chat.id] = (snap, t)
        await self.groups.upsert(chat.id, chat.title or "", chat.username, active=True)

    def forget_group(self, chat_id: int) -> None:
        self._group_seen.pop(chat_id, None)

    def count_message(self, chat_id: int, user_id: int) -> None:
        self._counts[(chat_id, user_id)] += 1

    def pending_count(self, chat_id: int, user_id: int) -> int:
        return self._counts.get((chat_id, user_id), 0)

    async def flush(self) -> int:
        if not self._counts:
            return 0
        batch, self._counts = self._counts, defaultdict(int)
        ts = int(time.time())
        try:
            await self.members.add_message_counts((c, u, n, ts) for (c, u), n in batch.items())
        except Exception:
            log.exception("تعذر حفظ عدادات الرسائل")
            for k, v in batch.items():  # نرجعها حتى ما تضيع
                self._counts[k] += v
            return 0
        return len(batch)
