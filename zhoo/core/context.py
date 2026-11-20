"""حاوية الخدمات المشتركة وسياق تنفيذ الأمر."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from zhoo.config import Settings
from zhoo.core.permissions import PermissionService
from zhoo.core.ranks import Rank
from zhoo.core.conversation import Conversations
from zhoo.core.guards import FloodTracker, RepeatTracker, StrikeTracker
from zhoo.core.ratelimit import RateLimiter
from zhoo.core.tracker import Tracker
from zhoo.database.db import Database
from zhoo.repositories.aliases import AliasesRepo
from zhoo.repositories.audit import AuditRepo
from zhoo.repositories.bot_settings import BotSettingsRepo
from zhoo.repositories.captcha import CaptchaRepo
from zhoo.repositories.economy import EconomyRepo
from zhoo.repositories.group_settings import GroupSettingsRepo
from zhoo.repositories.groups import GroupsRepo
from zhoo.repositories.levels import LevelsRepo
from zhoo.repositories.members import MembersRepo
from zhoo.repositories.punishments import PunishmentsRepo
from zhoo.repositories.replies import RepliesRepo
from zhoo.repositories.social import RatingsRepo, SocialRepo
from zhoo.repositories.swear_logs import SwearLogsRepo
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
    captcha: CaptchaRepo
    swear_logs: SwearLogsRepo
    aliases: AliasesRepo
    replies: RepliesRepo
    social: SocialRepo
    ratings: RatingsRepo
    levels: LevelsRepo
    economy: EconomyRepo
    flood: FloodTracker = field(default_factory=FloodTracker)
    repeats: RepeatTracker = field(default_factory=RepeatTracker)
    strikes: StrikeTracker = field(default_factory=StrikeTracker)
    notice_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(1, 20))
    reply_limiter: RateLimiter = field(default_factory=lambda: RateLimiter(4, 10))
    conversations: Conversations = field(default_factory=Conversations)
    games: dict = field(default_factory=dict)          # chat_id ← اللعبة الشغّالة
    xp_seen: dict = field(default_factory=dict)        # (chat, user) ← (آخر وقت، بصمة آخر رسالة)
    broadcast_running: bool = False
    restoring: bool = False                            # أثناء الاستعادة نوقف استقبال التحديثات

    def reset_caches(self) -> None:
        """بعد استعادة نسخة احتياطية: نمسح كل الذاكرة المؤقتة حتى نقرا من القاعدة الجديدة."""
        self.group_settings._cache.clear()
        self.aliases._cache.clear()
        self.replies._cache.clear()
        self.tracker._user_seen.clear()
        self.tracker._group_seen.clear()
        self.perms._admins.clear()
        self.xp_seen.clear()
        self.games.clear()
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
            captcha=CaptchaRepo(db), swear_logs=SwearLogsRepo(db),
            aliases=AliasesRepo(db), replies=RepliesRepo(db), social=SocialRepo(db),
            ratings=RatingsRepo(db), levels=LevelsRepo(db), economy=EconomyRepo(db),
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
