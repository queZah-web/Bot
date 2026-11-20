"""الموجّه الرئيسي للرسائل النصية: تتبع ← تحليل ← فحوصات أمان ← تنفيذ."""
from __future__ import annotations

import logging

from telegram import Chat, MessageEntity, Update
from telegram.ext import ContextTypes

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, get_services
from zhoo.core.ranks import RANK_NAMES, Rank
from zhoo.systems import locks, protect

log = logging.getLogger(__name__)

GROUP_TYPES = (Chat.GROUP, Chat.SUPERGROUP)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None:
        return
    svc = get_services(context)
    in_group = chat.type in GROUP_TYPES

    # ١) التتبع (خفيف ومجمّع)
    if in_group:
        await svc.tracker.track_group(chat)
    if msg.sender_chat is None and not user.is_bot:
        await svc.tracker.track_user(user)
        if in_group:
            svc.tracker.count_message(chat.id, user.id)
            # الحماية تفحص قبل أي شي؛ إذا انحذفت الرسالة نوقف
            if await protect.inspect(update, context, svc, msg, chat, user):
                return
            if await locks.check(context, svc, msg, chat, user):
                return

    # ٢) التحليل
    text = msg.text
    if not text:
        return
    has_tm = any(e.type == MessageEntity.TEXT_MENTION for e in msg.entities or ())
    has_reply = msg.reply_to_message is not None and not msg.reply_to_message.forum_topic_created
    parsed = registry.parse(text, has_text_mention=has_tm, has_reply=has_reply)
    if parsed is None:
        return
    cmd = parsed.command

    # ٣) فحوصات الأمان
    if msg.sender_chat is not None:
        if msg.sender_chat.id == chat.id:  # مشرف مخفي
            await msg.reply_text(T.ANON_ADMIN)
        return  # رسائل القنوات ما تنفذ أوامر
    if user.is_bot:
        return

    is_dev = svc.perms.is_developer(user.id)
    private = chat.type == Chat.PRIVATE

    if svc.maintenance and not is_dev:
        if svc.command_limiter.should_warn(("maint", chat.id)):
            await msg.reply_text(T.MAINTENANCE)
        return

    if not is_dev and not svc.command_limiter.hit(user.id):
        if svc.command_limiter.should_warn(user.id):
            await msg.reply_text(T.SLOW_DOWN)
        return

    if cmd.where == "group" and not in_group:
        await msg.reply_text(T.GROUP_ONLY)
        return
    if cmd.where == "private" and not private:
        if cmd.min_rank < Rank.DEVELOPER or is_dev:
            await msg.reply_text(T.PRIVATE_ONLY)
        return

    rank = await svc.perms.rank_of(context.bot, chat.id, user.id, private=private)
    if rank < cmd.min_rank:
        if cmd.min_rank >= Rank.DEVELOPER:
            return  # أوامر المطور مخفية تماماً عن غيره
        await msg.reply_text(T.NO_PERMISSION.format(rank=RANK_NAMES[cmd.min_rank]))
        return

    # ٤) التنفيذ
    cx = CommandContext(update=update, context=context, services=svc, message=msg, chat=chat,
                        user=user, rank=rank, args=parsed.args, raw_args=parsed.raw_args)
    log.debug("أمر %s من %s في %s", cmd.key, user.id, chat.id)
    await cmd.handler(cx)


async def on_migrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تحويل مجموعة عادية لخارقة: الايدي يتغير، ننقل كل البيانات."""
    msg = update.effective_message
    if msg is None or not msg.migrate_to_chat_id:
        return
    svc = get_services(context)
    old_id, new_id = msg.chat.id, msg.migrate_to_chat_id
    await svc.tracker.flush()
    await svc.groups.migrate_chat_id(old_id, new_id)
    svc.tracker.forget_group(old_id)
    svc.perms.invalidate(old_id)
    await svc.audit.log("group_migrated", chat_id=new_id, details={"from": old_id})
    log.info("تم نقل المجموعة %s إلى %s", old_id, new_id)
