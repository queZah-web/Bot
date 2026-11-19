"""متابعة دخول وخروج البوت من المجموعات وتغير المشرفين."""
from __future__ import annotations

import logging

from telegram import Chat, ChatMemberUpdated, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus as S
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from zhoo.core import texts as T
from zhoo.core.context import get_services
from zhoo.core.fmt import esc, mention

log = logging.getLogger(__name__)

_IN = {S.MEMBER, S.ADMINISTRATOR, S.OWNER}


def _is_in(cm) -> bool:
    return cm.status in _IN or (cm.status == S.RESTRICTED and getattr(cm, "is_member", False))


async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cmu: ChatMemberUpdated | None = update.my_chat_member
    if cmu is None or cmu.chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        return
    svc = get_services(context)
    chat = cmu.chat
    actor = cmu.from_user
    svc.perms.invalidate(chat.id)

    was_in, now_in = _is_in(cmu.old_chat_member), _is_in(cmu.new_chat_member)

    if now_in and not was_in:
        await svc.groups.upsert(chat.id, chat.title or "", chat.username, active=True, added_by=actor.id)
        await svc.audit.log("bot_added", chat_id=chat.id, actor_id=actor.id)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_COMMANDS, callback_data=f"h:{actor.id}:main")]])
        try:
            await context.bot.send_message(chat.id, T.ADDED_TO_GROUP.format(title=esc(chat.title or "")),
                                           reply_markup=kb)
        except TelegramError as e:
            log.info("ما كدرت أرحب بالمجموعة %s: %s", chat.id, e)
        await _notify_owner(context, T.NEW_GROUP_NOTICE.format(
            title=esc(chat.title or ""), chat_id=chat.id, by=mention(actor.id, actor.full_name)))

    elif was_in and not now_in:
        await svc.groups.set_active(chat.id, False)
        svc.tracker.forget_group(chat.id)
        await svc.audit.log("bot_removed", chat_id=chat.id, actor_id=actor.id)
        await _notify_owner(context, T.LEFT_GROUP_NOTICE.format(title=esc(chat.title or ""), chat_id=chat.id))

    elif cmu.new_chat_member.status == S.ADMINISTRATOR and cmu.old_chat_member.status != S.ADMINISTRATOR:
        try:
            await context.bot.send_message(chat.id, f"{T.BULLET} شكراً على الإشراف 💜 هسه أشتغل بكامل قوتي 💪")
        except TelegramError:
            pass


async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أي تغيير بالمشرفين يمسح الذاكرة المؤقتة حتى الصلاحيات تكون دقيقة فوراً."""
    cmu = update.chat_member
    if cmu is None:
        return
    admin_states = {S.ADMINISTRATOR, S.OWNER}
    if cmu.old_chat_member.status in admin_states or cmu.new_chat_member.status in admin_states:
        get_services(context).perms.invalidate(cmu.chat.id)


async def _notify_owner(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    svc = get_services(context)
    try:
        await context.bot.send_message(svc.settings.owner_id, text)
    except TelegramError:
        pass  # المطور ما بدأ محادثة مع البوت بعد
