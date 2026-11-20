"""قفل السب: مسح / مسح + كتم / مسح + حظر — من أول رسالة، حتى لو السب بنص كليشة.

- يفحص النص والتعليق على الوسائط، وحتى الرسائل المعدّلة.
- مشرفين تيليجرام والأدمن فما فوق: تنمسح رسالتهم بس (بدون عقوبة).
- كل رسالة تنمسح تنحفظ بسجل «السب المحذوف» (30 يوم).
"""
from __future__ import annotations

import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes

from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import Rank
from zhoo.core.swear import detector, normalize_word
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "locks"

MODES = ("off", "delete", "mute", "ban")
NO_PUNISH_RANK = Rank.ADMIN          # الأدمن فما فوق: مسح بدون عقوبة
SET_RANK = {"off": Rank.ADMIN, "delete": Rank.ADMIN, "mute": Rank.MANAGER, "ban": Rank.MANAGER}
VIEW_RANK = Rank.ADMIN
DICT_RANK = Rank.MANAGER
MAX_CUSTOM = 100
DICT_COMMANDS = {"swear_add", "swear_remove", "swear_allow"}


# ── الإعدادات ───────────────────────────────────────
async def get_mode(svc: Services, chat_id: int) -> str:
    mode = await svc.group_settings.get(chat_id, "swear_mode")
    return mode if mode in MODES else "off"


async def _word_set(svc: Services, chat_id: int, key: str) -> set[str]:
    raw = await svc.group_settings.get(chat_id, key)
    return {w for w in raw.split(",") if w}


async def set_mode(svc: Services, chat_id: int, mode: str, by: int) -> str:
    old = await svc.group_settings.set(chat_id, "swear_mode", mode, by)
    await svc.audit.log("setting", chat_id=chat_id, actor_id=by,
                        details={"key": "swear_mode", "from": old, "to": mode})
    return old


# ── الفحص ───────────────────────────────────────────
async def check(context, svc: Services, msg: Message, chat, user) -> bool:
    """يرجع True إذا انمسحت الرسالة بسبب السب."""
    from zhoo.systems import botstate
    if not await botstate.is_active(svc, chat.id):
        return False
    mode = await get_mode(svc, chat.id)
    if mode == "off":
        return False
    text = msg.text or msg.caption
    if not text:
        return False
    word = detector.find(text, extra=await _word_set(svc, chat.id, "swear_custom"),
                         allowed=await _word_set(svc, chat.id, "swear_allow"))
    if word is None:
        return False

    rank = await svc.perms.rank_of(context.bot, chat.id, user.id)
    # أوامر القاموس نفسها لازم تحتوي الكلمة، فما نمسحها إذا الرتبة تسمح
    parsed = registry.parse(msg.text or "") if msg.text else None
    if parsed and parsed.command.key in DICT_COMMANDS and rank >= DICT_RANK:
        return False

    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False
    try:
        await msg.delete()
    except TelegramError:
        return False

    action = mode if rank < NO_PUNISH_RANK else "delete"
    if await botstate.is_quiet(svc, chat.id):
        action = "delete"  # بالإيقاف: مسح سريع بس، بدون كتم أو حظر
    if action in ("mute", "ban") and not rights.can_restrict_members:
        action = "delete"

    who = mention(user.id, user.full_name)
    if action in ("mute", "ban"):
        try:
            await mod.apply(context.bot, chat.id, user.id, action, None)
        except (BadRequest, Forbidden) as e:
            log.info("فشلت عقوبة السب: %s", e)
            action = "delete"

    await svc.swear_logs.add(chat.id, user.id, word, text, action)
    await svc.audit.log(f"swear_{action}", chat_id=chat.id, actor_id=context.bot.id, target_id=user.id)

    from zhoo.systems.protect import send_notice  # تجنب الاستيراد الدائري
    if action == "delete":
        if svc.notice_limiter.hit((chat.id, user.id)):
            await send_notice(context, chat.id, T.SWEAR_NOTICE.format(mention=who), ttl=15)
        return True

    await svc.punishments.add(chat.id, user.id, action, context.bot.id, T.SWEAR_REASON, None)
    head, emoji = T.PUNISH_TITLES[action]
    code = "m" if action == "mute" else "b"
    undo = T.BTN_UNDO_MUTE if action == "mute" else T.BTN_UNDO_BAN
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(undo, callback_data=f"p:{code}:{user.id}")]])
    await send_notice(context, chat.id, T.SWEAR_PUNISHED.format(head=head, emoji=emoji, mention=who),
                      ttl=0, reply_markup=kb)
    return True


async def on_edited(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """السب بالتعديل ما يفلت."""
    msg, chat, user = update.edited_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None or user.is_bot or msg.sender_chat is not None:
        return
    await check(context, get_services(context), msg, chat, user)


# ── أوامر القفل ─────────────────────────────────────
async def _cmd_set(cx: CommandContext, mode: str) -> None:
    svc = cx.services
    if cx.rank < SET_RANK[mode]:
        from zhoo.core.ranks import RANK_NAMES
        await cx.reply(T.NO_PERMISSION.format(rank=RANK_NAMES[SET_RANK[mode]]))
        return
    if await get_mode(svc, cx.chat.id) == mode:
        await cx.reply(T.SWEAR_MODE_SAME.format(mode=T.SWEAR_MODES[mode]))
        return
    await set_mode(svc, cx.chat.id, mode, cx.user.id)
    actor = mention(cx.user.id, cx.user.full_name)
    if mode == "off":
        await cx.reply(T.SWEAR_MODE_OFF.format(actor=actor))
        return
    text = T.SWEAR_MODE_SET.format(mode=T.SWEAR_MODES[mode], actor=actor)
    rights = await svc.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_delete_messages:
        text += "\n" + T.SWEAR_NEED_DELETE
    await cx.reply(text)


async def _lock_delete(cx): await _cmd_set(cx, "delete")   # noqa: E704
async def _lock_mute(cx): await _cmd_set(cx, "mute")       # noqa: E704
async def _lock_ban(cx): await _cmd_set(cx, "ban")         # noqa: E704
async def _unlock(cx): await _cmd_set(cx, "off")           # noqa: E704


registry.command("swear_delete", ("قفل السب", "قفل الشتائم"), section=S, min_rank=SET_RANK["delete"],
                 description="يمسح كل رسالة بيها سب", order=10)(_lock_delete)
registry.command("swear_mute", ("قفل السب بالكتم", "قفل الشتائم بالكتم"), section=S, min_rank=SET_RANK["mute"],
                 description="يمسح السب ويكتم صاحبه من أول مرة", order=11)(_lock_mute)
registry.command("swear_ban", ("قفل السب بالحظر", "قفل الشتائم بالحظر"), section=S, min_rank=SET_RANK["ban"],
                 description="يمسح السب ويحظر صاحبه من أول مرة", order=12)(_lock_ban)
registry.command("swear_off", ("فتح السب", "فتح الشتائم"), section=S, min_rank=SET_RANK["off"],
                 description="يوقف قفل السب", order=13)(_unlock)


# ── السب المحذوف ────────────────────────────────────
@registry.command("swear_log", ("السب المحذوف", "سجل السب"), section=S, min_rank=VIEW_RANK, args="target",
                  usage="اختياري: بالرد/اليوزر", description="يعرض السب المحذوف: منو سب، شنو كال، ورسالته", order=14)
async def cmd_swear_log(cx: CommandContext) -> None:
    user_id = None
    if cx.message.reply_to_message is not None or cx.args:
        try:
            target = await resolve_target(cx)
        except TargetError as e:
            await reply_target_error(cx, e, "السب المحذوف @username")
            return
        user_id = target.user_id
    rows = await cx.services.swear_logs.recent(cx.chat.id, user_id, 10)
    if not rows:
        await cx.reply(f"{T.SWEAR_LOG_HEADER}\n{T.SWEAR_LOG_EMPTY}")
        return
    items = []
    for r in rows:
        name = " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])
        text = r["text"] if len(r["text"]) <= 300 else r["text"][:300] + "…"
        items.append(T.SWEAR_LOG_ITEM.format(
            mention=mention(r["user_id"], name), action=T.SWEAR_ACTIONS.get(r["action"], r["action"]),
            word=esc(r["word"]), text=esc(text),
            when=time.strftime("%m-%d %H:%M", time.gmtime(r["created_at"]))))
    await cx.reply(f"{T.SWEAR_LOG_HEADER}\n" + "\n\n".join(items) + f"\n{T.LINE}\n{T.SWEAR_LOG_FOOTER}")


@registry.command("swear_log_clear", ("مسح سجل السب",), section=S, min_rank=DICT_RANK,
                  description="يمسح سجل السب المحذوف", order=15)
async def cmd_swear_log_clear(cx: CommandContext) -> None:
    await cx.services.swear_logs.clear(cx.chat.id)
    await cx.services.audit.log("swear_log_clear", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.SWEAR_LOG_CLEARED)


# ── قاموس المجموعة ──────────────────────────────────
def _clean_word(cx: CommandContext) -> tuple[str, str] | None:
    raw = cx.raw_args.strip()
    norm = " ".join(normalize_word(w) for w in raw.split())
    norm = norm.replace(" ", "")
    if not 2 <= len(norm) <= 40:
        return None
    return raw[:40], norm


async def _save_set(cx: CommandContext, key: str, words: set[str]) -> None:
    await cx.services.group_settings.set(cx.chat.id, key, ",".join(sorted(words)[:MAX_CUSTOM]), cx.user.id)


@registry.command("swear_add", ("اضافه سب", "إضافة سب", "اضف سب"), section=S, min_rank=DICT_RANK, args="text",
                  usage="الكلمة", description="يضيف كلمة لقاموس السب الخاص بالمجموعة", order=16)
async def cmd_swear_add(cx: CommandContext) -> None:
    w = _clean_word(cx)
    if w is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    custom = await _word_set(cx.services, cx.chat.id, "swear_custom")
    custom.add(w[1])
    await _save_set(cx, "swear_custom", custom)
    allow = await _word_set(cx.services, cx.chat.id, "swear_allow")
    if w[1] in allow:
        allow.discard(w[1])
        await _save_set(cx, "swear_allow", allow)
    await cx.services.audit.log("swear_word_add", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.SWEAR_WORD_ADDED.format(word=esc(w[0])))


@registry.command("swear_remove", ("حذف سب",), section=S, min_rank=DICT_RANK, args="text",
                  usage="الكلمة", description="يشيل كلمة من القاموس الخاص", order=17)
async def cmd_swear_remove(cx: CommandContext) -> None:
    w = _clean_word(cx)
    if w is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    custom = await _word_set(cx.services, cx.chat.id, "swear_custom")
    if w[1] not in custom:
        await cx.reply(T.SWEAR_WORD_NOT_FOUND)
        return
    custom.discard(w[1])
    await _save_set(cx, "swear_custom", custom)
    await cx.reply(T.SWEAR_WORD_REMOVED.format(word=esc(w[0])))


@registry.command("swear_allow", ("سماح كلمه", "سماح كلمة"), section=S, min_rank=DICT_RANK, args="text",
                  usage="الكلمة", description="يسمح بكلمة من القاموس الأساسي بهاي المجموعة", order=18)
async def cmd_swear_allow(cx: CommandContext) -> None:
    w = _clean_word(cx)
    if w is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    allow = await _word_set(cx.services, cx.chat.id, "swear_allow")
    allow.add(w[1])
    await _save_set(cx, "swear_allow", allow)
    custom = await _word_set(cx.services, cx.chat.id, "swear_custom")
    if w[1] in custom:
        custom.discard(w[1])
        await _save_set(cx, "swear_custom", custom)
    await cx.services.audit.log("swear_word_allow", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.SWEAR_WORD_ALLOWED.format(word=esc(w[0])))


@registry.command("swear_words", ("قاموس السب",), section=S, min_rank=DICT_RANK,
                  description="الكلمات المضافة والمسموحة بهاي المجموعة", order=19)
async def cmd_swear_words(cx: CommandContext) -> None:
    custom = sorted(await _word_set(cx.services, cx.chat.id, "swear_custom"))
    allow = sorted(await _word_set(cx.services, cx.chat.id, "swear_allow"))
    text = T.SWEAR_WORDS_HEADER + "\n"
    if not custom and not allow:
        await cx.reply(text + T.SWEAR_WORDS_EMPTY)
        return
    if custom:
        text += "\n".join(f"▫️ <tg-spoiler>{esc(w)}</tg-spoiler>" for w in custom)
    if allow:
        text += f"\n{T.SWEAR_ALLOWED_LABEL}\n" + "\n".join(f"▫️ <code>{esc(w)}</code>" for w in allow)
    await cx.reply(text)


def next_mode(mode: str) -> str:
    return MODES[(MODES.index(mode) + 1) % len(MODES)] if mode in MODES else "delete"
