"""قناة السجل: كل عقوبة وتغيير رتبة وقفل ينرسل لقناة (أو مجموعة) خاصة بالإدارة.

«تعيين قناة السجل @القناة» (أو الايدي، أو بالرد على رسالة محوّلة من القناة) ⋅ «قناة السجل» ⋅ «حذف قناة السجل».
زهو لازم تكون مشرفة بالقناة. يشتغل كمستمع على سجل التدقيق، فأي عملية جديدة تنضاف تلقائياً.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram.error import TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import Rank, rank_label

log = logging.getLogger(__name__)
S = "group"
SET_RANK = Rank.OWNER
KEY = "log_channel"
BAGHDAD = timezone(timedelta(hours=3))


def label(action: str, details: dict) -> str | None:
    """اسم العملية بالسجل، أو None إذا ما تنرسل (مثل المسح العادي اللي يصير كثير)."""
    if action in T.LOG_ACTIONS:
        return T.LOG_ACTIONS[action]
    if action.startswith("swear_") and action[6:] in ("mute", "ban", "warn", "kick", "restrict"):
        return T.LOG_SWEAR.format(kind=T.LOG_ACTIONS.get(action[6:], action[6:]))
    if action.startswith("guard_mute_"):
        return T.LOG_ACTIONS["guard_mute"]
    if action.startswith("auto_"):
        return T.LOG_AUTO.format(kind=T.LOG_ACTIONS.get(action[5:], action[5:]))
    if action.startswith("un") and action.endswith("_all"):
        return T.LOG_ACTIONS.get(action)
    return None


async def _who(svc: Services, bot, user_id: int | None) -> str:
    if user_id is None:
        return T.NONE_VALUE
    if user_id == bot.id:
        return T.LOG_BY_ZHOO
    u = await svc.users.get(user_id)
    return mention(user_id, u.full_name if u else str(user_id))


def _extra(action: str, d: dict) -> list[str]:
    lines = []
    if d.get("reason"):
        lines.append(T.LOG_LINE_REASON.format(v=esc(str(d["reason"])[:200])))
    if isinstance(d.get("seconds"), int) and d["seconds"] > 0:
        from zhoo.core.durations import format_duration
        lines.append(T.LOG_LINE_DURATION.format(v=format_duration(d["seconds"])))
    if action == "rank_change" and "to" in d:
        lines.append(T.LOG_LINE_RANK.format(old=rank_label(d.get("from", 0)), new=rank_label(d["to"])))
    if action in ("lock", "unlock") and d.get("key"):
        lines.append(T.LOG_LINE_LOCK.format(v=esc(str(d["key"]))))
    if d.get("n") is not None:
        lines.append(T.LOG_LINE_COUNT.format(v=d["n"]))
    if action == "bot_state" and d.get("to"):
        lines.append(T.LOG_LINE_STATE.format(v=T.GROUP_STATES.get(d["to"], d["to"])))
    return lines


async def on_audit(bot, svc: Services, action: str, chat_id: int | None, actor_id: int | None,
                   target_id: int | None, details: dict, result: str = "ok") -> None:
    if not chat_id or chat_id > 0 or result != "ok":
        return
    name = label(action, details)
    if name is None:
        return
    channel = await svc.group_settings.get(chat_id, KEY)
    if not channel:
        return
    title = await svc.db.fetchval("SELECT title FROM groups WHERE chat_id = ?", (chat_id,), default="") or str(chat_id)
    lines = [T.LOG_HEAD.format(title=esc(title)), T.LINE, T.LOG_LINE_ACTION.format(v=name)]
    if target_id:
        lines.append(T.LOG_LINE_TARGET.format(v=await _who(svc, bot, target_id)) + f" <code>{target_id}</code>")
    lines.append(T.LOG_LINE_ACTOR.format(v=await _who(svc, bot, actor_id)))
    lines += _extra(action, details)
    lines.append(T.LOG_LINE_TIME.format(v=datetime.now(BAGHDAD).strftime("%Y-%m-%d ⋅ %H:%M")))
    try:
        await bot.send_message(int(channel), "\n".join(lines), disable_notification=True)
    except TelegramError as e:
        log.info("ما گدرت أرسل لقناة السجل %s: %s", channel, e)


def _channel_from(cx: CommandContext) -> int | str | None:
    reply = cx.message.reply_to_message
    origin = getattr(reply, "forward_origin", None) if reply else None
    if origin is not None and getattr(origin, "chat", None) is not None:
        return origin.chat.id
    raw = cx.raw_args.strip()
    if raw.lstrip("-").isdigit():
        return int(raw)
    if raw.startswith("@") and len(raw) > 2:
        return raw
    return None


@registry.command("log_set", ("تعيين قناة السجل", "تعيين قناه السجل", "ضع قناة السجل"), section=S,
                  min_rank=SET_RANK, args="text", usage="@القناة أو الايدي",
                  description="كل عقوبة وتغيير رتبة ينرسل لقناة الإدارة 📒", order=80)
async def cmd_set(cx: CommandContext) -> None:
    target = _channel_from(cx)
    if target is None:
        await cx.reply(T.LOG_SET_HOW)
        return
    try:
        sent = await cx.bot.send_message(target, T.LOG_TEST.format(title=esc(cx.chat.title or "")))
    except TelegramError as e:
        log.info("قناة السجل مرفوضة: %s", e)
        await cx.reply(T.LOG_SET_FAILED)
        return
    channel_id = sent.chat.id if getattr(sent, "chat", None) is not None else target
    await cx.services.group_settings.set(cx.chat.id, KEY, str(channel_id), cx.user.id)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"key": KEY, "to": str(channel_id)})
    await cx.reply(T.LOG_SET_DONE)


@registry.command("log_show", ("قناة السجل", "قناه السجل"), section=S, min_rank=SET_RANK,
                  description="شنو قناة السجل الحالية", order=81)
async def cmd_show(cx: CommandContext) -> None:
    channel = await cx.services.group_settings.get(cx.chat.id, KEY)
    await cx.reply(T.LOG_SHOW.format(v=f"<code>{esc(channel)}</code>") if channel else T.LOG_NONE)


@registry.command("log_clear", ("حذف قناة السجل", "حذف قناه السجل", "الغاء قناة السجل"), section=S,
                  min_rank=SET_RANK, description="يوقف إرسال السجل", order=82)
async def cmd_clear(cx: CommandContext) -> None:
    if not await cx.services.group_settings.get(cx.chat.id, KEY):
        await cx.reply(T.LOG_NONE)
        return
    await cx.services.group_settings.set(cx.chat.id, KEY, "", cx.user.id)
    await cx.reply(T.LOG_CLEARED)
