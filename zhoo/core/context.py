"""حاوية الخدمات المشتركة وسياق تنفيذ الأمر."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from zhoo.config import Settings
from zhoo.core.permissions import PermissionService
from zhoo.core.ranks import Rank
from zhoo.core.ratelimit import RateLimiter
from zhoo.core.tracker import Tracker
from zhoo.database.db import Database
from zhoo.repositories.audit import AuditRepo
from zhoo.repositories.bot_settings import BotSettingsRepo
from zhoo.repositories.group_settings import GroupSettingsRepo
from zhoo.repositories.groups import GroupsRepo
from zhoo.repositories.members import MembersRepo
from zhoo.repositories.punishments import PunishmentsRepo
from zhoo.repositories.users import UsersRepo


@dataclass
class Services:
    settings: Settings
    db: Database
    users: UsersRepo
    groups: GroupsRepo
    members: MembersRepo
    audit: AuditRepo
    bot_settings: BotSettingsRepo
    perms: PermissionService
    tracker: Tracker
    punishments: PunishmentsRepo
    group_settings: GroupSettingsRepo
    command_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(5, 10))
    button_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(4, 3))
    started_at: float = field(default_factory=time.time)
    error_count: int = 0

    @classmethod
    def build(cls, settings: Settings, db: Database) -> "Services":
        users, groups, members = UsersRepo(db), GroupsRepo(db), MembersRepo(db)
        return cls(
            settings=settings, db=db, users=users, groups=groups, members=members,
            audit=AuditRepo(db), bot_settings=BotSettingsRepo(db),
            perms=PermissionService(members, settings.owner_id),
            tracker=Tracker(users, groups, members),
            punishments=PunishmentsRepo(db), group_settings=GroupSettingsRepo(db),
        )

    @property
    def maintenance(self) -> bool:
        return self.bot_settings.get_bool("maintenance")


def get_services(context: ContextTypes.DEFAULT_TYPE) -> Services:
    return context.application.bot_data["services"]


@dataclass
class CommandContext:
    update: Update
    context: ContextTypes.DEFAULT_TYPE
    services: Services
    message: Message
    chat: Chat
    user: User
    rank: Rank
    args: list[str]
    raw_args: str

    @property
    def bot(self):
        return self.context.bot

    @property
    def is_private(self) -> bool:
        return self.chat.type == Chat.PRIVATE

    async def reply(self, text: str, **kwargs) -> Message:
        return await self.message.reply_text(text, **kwargs)
