"""تغيير صورة المجموعة واسمها وبايوها.

- «تغيير صورة المجموعه» ← زهو تطلب الصورة ← تتغير فوراً (أو بالرد على صورة مباشرة).
- «تغيير اسم المجموعه» ← تطلب الاسم (أو اكتبه ويا الأمر).
- «تغيير بايو المجموعه» ← تطلب البايو (أو اكتبه ويا الأمر).
- «الغاء» توقف الطلب بأي وقت. تحتاج صلاحية «تغيير معلومات المجموعة».
"""
from __future__ import annotations

import logging

from telegram import Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import conversation
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import Rank

log = logging.getLogger(__name__)
S = "group"
EDIT_RANK = Rank.MANAGER
MAX_TITLE = 128
MAX_BIO = 255
MAX_PHOTO_BYTES = 10 * 1024 * 1024


async def _can_change(svc: Services, bot, chat_id: int) -> bool:
    rights = await svc.perms.bot_rights(bot, chat_id)
    return rights is not None and bool(rights.can_change_info)


async def _apply_photo(svc: Services, bot, chat, msg: Message, user) -> str:
    photo = msg.photo[-1] if msg.photo else None
    if photo is None and msg.document and (msg.document.mime_type or "").startswith("image/"):
        photo = msg.document
    if photo is None:
        return T.CHAT_PHOTO_NEED
    if (photo.file_size or 0) > MAX_PHOTO_BYTES:
        return T.CHAT_PHOTO_TOO_BIG
    try:
        file = await bot.get_file(photo.file_id)
        data = bytes(await file.download_as_bytearray())
        await bot.set_chat_photo(chat.id, data)
    except TelegramError as e:
        log.info("فشل تغيير صورة المجموعة: %s", e)
        return T.CHAT_INFO_FAILED
    await svc.audit.log("chat_photo", chat_id=chat.id, actor_id=user.id)
    return T.CHAT_PHOTO_DONE.format(actor=mention(user.id, user.full_name))


async def _apply_title(svc: Services, bot, chat, text: str, user) -> str:
    text = " ".join(text.split())
    if not 1 <= len(text) <= MAX_TITLE:
        return T.CHAT_TITLE_BAD.format(n=MAX_TITLE)
    try:
        await bot.set_chat_title(chat.id, text)
    except TelegramError as e:
        log.info("فشل تغيير اسم المجموعة: %s", e)
        return T.CHAT_INFO_FAILED
    await svc.audit.log("chat_title", chat_id=chat.id, actor_id=user.id)
    return T.CHAT_TITLE_DONE.format(title=esc(text), actor=mention(user.id, user.full_name))


async def _apply_bio(svc: Services, bot, chat, text: str, user) -> str:
    text = text.strip()
    if len(text) > MAX_BIO:
        return T.CHAT_BIO_BAD.format(n=MAX_BIO)
    try:
        await bot.set_chat_description(chat.id, text)
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return T.CHAT_BIO_SAME
        log.info("فشل تغيير البايو: %s", e)
        return T.CHAT_INFO_FAILED
    except TelegramError as e:
        log.info("فشل تغيير البايو: %s", e)
        return T.CHAT_INFO_FAILED
    await svc.audit.log("chat_bio", chat_id=chat.id, actor_id=user.id)
    return T.CHAT_BIO_DONE.format(bio=esc(text) or "—", actor=mention(user.id, user.full_name))


# ── الأوامر ─────────────────────────────────────────
@registry.command("chat_photo", ("تغيير صورة المجموعه", "تغيير صوره المجموعه", "ضع صورة المجموعه", "ضع صوره",
                                 "تغيير الصوره"), section=S, min_rank=EDIT_RANK,
                  usage="بعدها ارسل الصورة، أو بالرد على صورة", description="يغير صورة المجموعة", order=30)
async def cmd_photo(cx: CommandContext) -> None:
    if not await _can_change(cx.services, cx.bot, cx.chat.id):
        await cx.reply(T.CHAT_INFO_NEED_RIGHT)
        return
    reply = cx.message.reply_to_message
    if reply is not None and (reply.photo or reply.document):
        await cx.reply(await _apply_photo(cx.services, cx.bot, cx.chat, reply, cx.user))
        return
    cx.services.conversations.start(cx.chat.id, cx.user.id, "chat_info", "photo")
    await cx.reply(T.CHAT_PHOTO_ASK)


@registry.command("chat_title", ("تغيير اسم المجموعه", "ضع اسم المجموعه", "تغيير الاسم"), section=S,
                  min_rank=EDIT_RANK, args="text", usage="الاسم (اختياري)", description="يغير اسم المجموعة",
                  order=31)
async def cmd_title(cx: CommandContext) -> None:
    if not await _can_change(cx.services, cx.bot, cx.chat.id):
        await cx.reply(T.CHAT_INFO_NEED_RIGHT)
        return
    if cx.raw_args.strip():
        await cx.reply(await _apply_title(cx.services, cx.bot, cx.chat, cx.raw_args, cx.user))
        return
    cx.services.conversations.start(cx.chat.id, cx.user.id, "chat_info", "title")
    await cx.reply(T.CHAT_TITLE_ASK)


@registry.command("chat_bio", ("تغيير بايو المجموعه", "تغيير وصف المجموعه", "ضع بايو", "تغيير البايو",
                               "ضع وصف المجموعه"), section=S, min_rank=EDIT_RANK, args="text",
                  usage="البايو (اختياري)", description="يغير بايو (وصف) المجموعة", order=32)
async def cmd_bio(cx: CommandContext) -> None:
    if not await _can_change(cx.services, cx.bot, cx.chat.id):
        await cx.reply(T.CHAT_INFO_NEED_RIGHT)
        return
    if cx.raw_args.strip():
        await cx.reply(await _apply_bio(cx.services, cx.bot, cx.chat, cx.raw_args, cx.user))
        return
    cx.services.conversations.start(cx.chat.id, cx.user.id, "chat_info", "bio")
    await cx.reply(T.CHAT_BIO_ASK)


@conversation.handler("chat_info")
async def _flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    bot = context.bot
    if p.step == "photo":
        if not (msg.photo or msg.document):
            await msg.reply_text(T.CHAT_PHOTO_NEED)
            return   # ننتظر صورة (أو «الغاء»)
        svc.conversations.end(chat.id, user.id)
        await msg.reply_text(await _apply_photo(svc, bot, chat, msg, user))
        return
    text = msg.text or ""
    if not text.strip():
        await msg.reply_text(T.CHAT_TEXT_NEED)
        return
    svc.conversations.end(chat.id, user.id)
    if p.step == "title":
        await msg.reply_text(await _apply_title(svc, bot, chat, text, user))
    else:
        await msg.reply_text(await _apply_bio(svc, bot, chat, text, user))
