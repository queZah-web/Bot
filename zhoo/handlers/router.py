"""الموجّه الرئيسي للرسائل النصية: تتبع ← تحليل ← فحوصات أمان ← تنفيذ."""
from __future__ import annotations

import logging

from telegram import Chat, MessageEntity, Update
from telegram.ext import ContextTypes

from zhoo.core import capabilities as caps
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, get_services
from zhoo.core.ranks import RANK_NAMES, Rank
from zhoo.core import conversation
from zhoo.core.normalize import normalize
from zhoo.systems import (ai, aliases, channels, cleanup, suspect, botstate, extras, features, games, levels, locks, protect, replies,
                          swear, zhoo_replies)

log = logging.getLogger(__name__)

GROUP_TYPES = (Chat.GROUP, Chat.SUPERGROUP)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None:
        return
    svc = get_services(context)
    if svc.restoring:
        return  # لحظات الاستعادة: نتجاهل التحديثات حتى ما نلمس قاعدة مسكّرة
    in_group = chat.type in GROUP_TYPES
    state = await botstate.get_state(svc, chat.id) if in_group else botstate.ON
    quiet = state != botstate.ON

    # ١) التتبع (خفيف ومجمّع)
    if in_group:
        await svc.tracker.track_group(chat)
    if msg.sender_chat is None and not user.is_bot:
        await svc.tracker.track_user(user)
        # محادثة بخطوات شغّالة (اضف رد، اضف امر...): الرسالة جواب إلها
        pending = svc.conversations.get(chat.id, user.id)
        if pending is not None and quiet:
            svc.conversations.end(chat.id, user.id)
            pending = None
        if pending is not None:
            if in_group:
                svc.tracker.count_message(chat.id, user.id)
            if msg.text and normalize(msg.text.strip()) in conversation.CANCEL_WORDS:
                svc.conversations.end(chat.id, user.id)
                await msg.reply_text(T.CONV_CANCELLED)
                return
            handler = conversation.HANDLERS.get(pending.kind)
            if handler is not None:
                await handler(svc, context, msg, chat, user, pending)
                return
            svc.conversations.end(chat.id, user.id)
        if in_group:
            svc.tracker.count_message(chat.id, user.id)
            # الحماية تفحص قبل أي شي؛ إذا انحذفت الرسالة نوقف
            if await protect.inspect(update, context, svc, msg, chat, user):
                return
            if await swear.check(context, svc, msg, chat, user):
                return
            if await locks.check(context, svc, msg, chat, user):
                return
            if await channels.check(context, svc, msg, chat, user):   # الاشتراك الإجباري
                return
            if await cleanup.check(context, svc, msg, chat, user):    # قائمة المنع
                return
            await suspect.check(context, svc, msg, chat, user)         # مميز مشكوك فيه: صوره تنمسح بعد شوية

    # ٢) التحليل
    text = msg.text
    if not text:
        if in_group and not quiet and msg.caption and msg.sender_chat is None and not user.is_bot \
                and not svc.maintenance and await features.enabled(svc, chat.id, "replies") \
                and not await zhoo_replies.muted(svc, chat.id, user.id):
            await replies.maybe_reply(svc, msg, chat, user)
        return
    # لعبة شغّالة: نفحص الجواب قبل الأوامر (حتى لو الجواب يشبه أمر مثل «الساعة»)
    if in_group and not quiet and chat.id in svc.games and msg.sender_chat is None and not user.is_bot:
        if await games.check_answer(context, svc, msg, chat, user):
            return
    has_tm = any(e.type == MessageEntity.TEXT_MENTION for e in msg.entities or ())
    has_reply = msg.reply_to_message is not None and not msg.reply_to_message.forum_topic_created
    parsed = registry.parse(text, has_text_mention=has_tm, has_reply=has_reply)
    if parsed is None and in_group:
        expanded = await aliases.expand(svc, chat.id, text)  # اختصار أمر (مثل: تق ← تقييد)
        if expanded:
            parsed = registry.parse(expanded, has_text_mention=has_tm, has_reply=has_reply)
    if parsed is None:
        if in_group and not quiet and msg.sender_chat is None and not user.is_bot and not svc.maintenance:
            await levels.on_message(context, svc, msg, chat, user)       # خبرة الرسائل
            await ai.on_message(svc, msg, chat, user)                    # ذاكرة التلخيص (إذا الذكاء شغّال)
            from zhoo.systems import suggest
            if await suggest.maybe_suggest(svc, context.bot, msg, chat, user):   # «قصدك: حظر؟»
                return
            if await zhoo_replies.muted(svc, chat.id, user.id):          # «لا تردي عليه»: بلا سوالف
                return
            if await features.enabled(svc, chat.id, "replies") and await replies.maybe_reply(svc, msg, chat, user):
                return
            await extras.maybe_source_reply(svc, msg, chat)              # ردود زهو (المضافة ثم الأساسية)
        return
    cmd = parsed.command

    # زهو موقوفة/معطّلة: بس أوامر التشغيل، وتذكير إذا نادوها.
    # حتى المطور: بس أوامر التشغيل وأوامر المطور الخاصة، وغيرها تسكت مثل الكل.
    if quiet and not (svc.perms.is_developer(user.id) and cmd.min_rank >= Rank.DEVELOPER):
        if cmd.key not in botstate.ALLOWED_WHEN[state] or msg.sender_chat is not None or user.is_bot:
            return
        if cmd.key == "zhoo":
            if svc.command_limiter.hit(("paused", chat.id)):
                await msg.reply_text(T.BOT_PAUSED_REPLY)
            return
        rank = await svc.perms.rank_of(context.bot, chat.id, user.id)
        if rank < cmd.min_rank:
            return  # بصمت

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
    cap = caps.COMMAND_CAP.get(cmd.key) if in_group else None
    if cap is not None:   # صلاحية قابلة للتخصيص لكل شخص
        allowed = await caps.has_cap(svc, chat.id, user.id, cap, rank >= cmd.min_rank)
    else:
        allowed = rank >= cmd.min_rank or (cmd.helpers and svc.perms.is_helper(user.id))
    if not allowed:
        if cmd.min_rank >= Rank.DEVELOPER:
            return  # أوامر المطور مخفية تماماً عن غيره
        if cap is not None and rank >= cmd.min_rank:
            await msg.reply_text(T.CAP_REVOKED.format(cap=caps.CAPS[cap][0]))
        else:
            await msg.reply_text(T.NO_PERMISSION.format(rank=RANK_NAMES[cmd.min_rank]))
        return

    # الميزات المعطّلة (المالك وفوگ يتجاوزونها)
    if in_group and await features.blocked(svc, chat.id, cmd.key, rank):
        await msg.reply_text(T.FEATURE_DISABLED)
        return

    # ٤) التنفيذ
    cx = CommandContext(update=update, context=context, services=svc, message=msg, chat=chat,
                        user=user, rank=rank, args=parsed.args, raw_args=parsed.raw_args,
                        quote=not in_group or await features.enabled(svc, chat.id, "quote"))
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
