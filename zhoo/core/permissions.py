"""خدمة الصلاحيات المركزية: تحسب الرتبة الفعلية لأي شخص بأي مجموعة.

الرتبة الفعلية = الأعلى من:
  • مطور البوت (OWNER_ID)      → مطور زهو
  • منشئ المجموعة في تيليجرام  → المنشئ
  • مشرف تيليجرام               → أدمن على الأقل
  • الرتبة المخزنة بقاعدة البيانات
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from telegram import Bot, ChatMember, ChatMemberAdministrator
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

from zhoo.core.ranks import Rank
from zhoo.repositories.members import MembersRepo

log = logging.getLogger(__name__)

ADMIN_CACHE_SECONDS = 120


@dataclass(frozen=True)
class RankInfo:
    effective: Rank
    floor: Rank        # أقل رتبة ممكنة بسبب تيليجرام/المطور
    stored: Rank       # الرتبة المخزنة بالقاعدة

    @property
    def is_telegram_admin(self) -> bool:
        return self.floor >= Rank.ADMIN


class PermissionService:
    def __init__(self, members: MembersRepo, developer_id: int):
        self.members = members
        self.developer_id = developer_id
        self._admins: dict[int, tuple[float, dict[int, ChatMember]]] = {}

    def is_developer(self, user_id: int) -> bool:
        return user_id == self.developer_id

    def invalidate(self, chat_id: int) -> None:
        self._admins.pop(chat_id, None)

    async def admins(self, bot: Bot, chat_id: int) -> dict[int, ChatMember]:
        cached = self._admins.get(chat_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        try:
            members = await bot.get_chat_administrators(chat_id)
        except TelegramError as e:
            log.warning("تعذر جلب مشرفي %s: %s", chat_id, e)
            return cached[1] if cached else {}
        data = {m.user.id: m for m in members}
        self._admins[chat_id] = (time.monotonic() + ADMIN_CACHE_SECONDS, data)
        return data

    async def telegram_floor(self, bot: Bot, chat_id: int, user_id: int) -> Rank:
        if self.is_developer(user_id):
            return Rank.DEVELOPER
        member = (await self.admins(bot, chat_id)).get(user_id)
        if member is None:
            return Rank.MEMBER
        if member.status == ChatMemberStatus.OWNER:
            return Rank.CREATOR
        return Rank.ADMIN

    async def rank_info(self, bot: Bot, chat_id: int, user_id: int, *, private: bool = False) -> RankInfo:
        if private:
            r = Rank.DEVELOPER if self.is_developer(user_id) else Rank.MEMBER
            return RankInfo(r, r, Rank.MEMBER)
        floor = await self.telegram_floor(bot, chat_id, user_id)
        stored = await self.members.get_rank(chat_id, user_id)
        return RankInfo(max(floor, stored), floor, stored)

    async def rank_of(self, bot: Bot, chat_id: int, user_id: int, *, private: bool = False) -> Rank:
        return (await self.rank_info(bot, chat_id, user_id, private=private)).effective

    async def bot_rights(self, bot: Bot, chat_id: int) -> ChatMemberAdministrator | None:
        """صلاحيات البوت الفعلية في المجموعة (None إذا مو مشرف)."""
        member = (await self.admins(bot, chat_id)).get(bot.id)
        return member if isinstance(member, ChatMemberAdministrator) else None
