"""تحديد العضو المستهدف: بالرد، أو المنشن، أو اليوزر، أو الايدي."""
from __future__ import annotations

import re
from dataclasses import dataclass

from telegram import MessageEntity
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

from zhoo.core.context import CommandContext


@dataclass(frozen=True)
class Target:
    user_id: int
    name: str
    username: str | None
    is_bot: bool


class TargetError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason  # none | not_found | channel


_USERNAME = re.compile(r"^@?([A-Za-z][A-Za-z0-9_]{3,31})$")


async def resolve_target(cx: CommandContext) -> Target:
    msg = cx.message

    # 1) بالرد (مع تجاهل رسالة إنشاء الموضوع في المجموعات ذات المواضيع)
    reply = msg.reply_to_message
    if reply is not None and not reply.forum_topic_created:
        if reply.sender_chat is not None:  # قناة أو مشرف مخفي
            raise TargetError("channel")
        user = reply.from_user
        if user is not None:
            return Target(user.id, user.full_name, user.username, user.is_bot)

    # 2) منشن لشخص بدون يوزر (text_mention)
    for ent in msg.entities or ():
        if ent.type == MessageEntity.TEXT_MENTION and ent.user is not None:
            u = ent.user
            return Target(u.id, u.full_name, u.username, u.is_bot)

    if not cx.args:
        raise TargetError("none")
    arg = cx.args[0]

    # 3) ايدي رقمي
    if arg.isdigit() and 5 <= len(arg) <= 15:
        user_id = int(arg)
        known = await cx.services.users.get(user_id)
        if known is not None:
            return Target(known.user_id, known.full_name, known.username, known.is_bot)
        if not cx.is_private:
            try:
                member = await cx.bot.get_chat_member(cx.chat.id, user_id)
                if member.status != ChatMemberStatus.LEFT or member.user.first_name:
                    u = member.user
                    return Target(u.id, u.full_name, u.username, u.is_bot)
            except TelegramError:
                pass
        raise TargetError("not_found")

    # 4) يوزر — من الأشخاص اللي شافهم البوت
    m = _USERNAME.match(arg)
    if m:
        known = await cx.services.users.find_by_username(m.group(1))
        if known is not None:
            return Target(known.user_id, known.full_name, known.username, known.is_bot)
        raise TargetError("not_found")

    raise TargetError("none")
