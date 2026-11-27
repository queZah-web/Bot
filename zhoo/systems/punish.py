"""نظام العقوبات: حظر، طرد، كتم، تقييد، تحذير، والفك، مع مدد مؤقتة وأزرار تراجع."""
from __future__ import annotations

import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden, TelegramError

from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.durations import DurationError, format_duration, parse_duration
from zhoo.core.fmt import duration as fmt_remaining
from zhoo.core.fmt import esc, mention
from zhoo.core.moderation import KIND_EMOJI, KIND_NAMES, WARN_ACTIONS, PunishDecision
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank, rank_label
from zhoo.core.targets import Target, TargetError, resolve_target
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "punish"

MAX_REASON = 200

# أقل رتبة لكل عقوبة
MIN_RANK = {
    "warn": Rank.ADMIN,
    "mute": Rank.ADMIN,
    "restrict": Rank.ADMIN,
    "kick": Rank.SUPERVISOR,
    "ban": Rank.MANAGER,
}
# أزرار التراجع: رمز ← (نوع الفك، نص الزر)
UNDO = {
    "b": ("ban", T.BTN_UNDO_BAN),
    "m": ("mute", T.BTN_UNDO_MUTE),
    "r": ("restrict", T.BTN_UNDO_RESTRICT),
    "w": ("warn", T.BTN_UNDO_WARN),
}
UNDO_CODE = {kind: code for code, (kind, _) in UNDO.items()}


# ── أدوات مساعدة ────────────────────────────────────
async def _bot_can_restrict(cx: CommandContext) -> bool:
    rights = await cx.services.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None:
        await cx.reply(T.BOT_NOT_ADMIN)
        return False
    if not rights.can_restrict_members:
        await cx.reply(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT))
        return False
    return True


def _undo_keyboard(kind: str, user_id: int) -> InlineKeyboardMarkup | None:
    code = UNDO_CODE.get(kind)
    if code is None:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(UNDO[code][1], callback_data=f"p:{code}:{user_id}")]])


def _clean_reason(text: str) -> str | None:
    text = " ".join((text or "").split())
    return text[:MAX_REASON] if text else None


async def _get_target(cx: CommandContext, example: str) -> Target | None:
    try:
        return await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, example)
        return None


async def _decision_reply(cx: CommandContext, target: Target, kind: str) -> bool:
    """يرجع True إذا مسموح. وإلا يرد بالسبب."""
    info = await cx.services.perms.rank_info(cx.bot, cx.chat.id, target.user_id)
    who = mention(target.user_id, target.name)
    decision = mod.check_punish(
        cx.rank, info.effective, info.floor, kind,
        is_self=target.user_id == cx.user.id, is_this_bot=target.user_id == cx.bot.id,
        target_is_bot=target.is_bot,
    )
    if decision == PunishDecision.OK:
        return True
    replies = {
        PunishDecision.SELF: T.PUNISH_SELF,
        PunishDecision.BOT_SELF: T.PUNISH_BOT_SELF,
        PunishDecision.PROTECTED: T.PUNISH_PROTECTED.format(mention=who, rank=rank_label(info.effective)),
        PunishDecision.HIGHER: T.PUNISH_HIGHER.format(mention=who, rank=rank_label(info.effective)),
        PunishDecision.TG_ADMIN: T.PUNISH_TG_ADMIN.format(mention=who),
        PunishDecision.OTHER_BOT: T.PUNISH_OTHER_BOT.format(mention=who),
    }
    await cx.services.audit.log(f"{kind}_denied", chat_id=cx.chat.id, actor_id=cx.user.id,
                                target_id=target.user_id, result="denied", details={"reason": decision})
    await cx.reply(replies[decision])
    return False


def _punish_text(kind: str, who: str, actor: str, *, seconds: int | None = None,
                 reason: str | None = None, warn: tuple[int, int] | None = None,
                 show_duration: bool = True) -> str:
    head, emoji = T.PUNISH_TITLES[kind]
    extra = ""
    if show_duration:
        extra += T.PUNISH_DURATION.format(duration=format_duration(seconds)) if seconds else T.PUNISH_FOREVER
    if warn:
        extra += T.WARN_COUNT.format(count=warn[0], limit=warn[1])
    if reason:
        extra += T.PUNISH_REASON.format(reason=esc(reason))
    return T.title(head, emoji) + "\n" + T.PUNISH_BODY.format(mention=who, actor=actor, extra=extra)


# ── العقوبات ───────────────────────────────────────
async def punish(cx: CommandContext, kind: str) -> None:
    svc = cx.services
    target = await _get_target(cx, f"{KIND_NAMES[kind]} @username")
    if target is None:
        return

    seconds, rest = None, target.rest
    if kind in ("ban", "mute", "restrict"):
        try:
            seconds, rest = parse_duration(target.rest)
        except DurationError:
            await cx.reply(T.BAD_DURATION)
            return
    reason = _clean_reason(rest)

    if not await _decision_reply(cx, target, kind):
        return
    if not await _bot_can_restrict(cx):
        return

    until = int(time.time()) + seconds if seconds else None
    try:
        await mod.apply(cx.bot, cx.chat.id, target.user_id, kind, until)
    except (BadRequest, Forbidden) as e:
        log.info("فشل %s على %s في %s: %s", kind, target.user_id, cx.chat.id, e)
        await svc.audit.log(kind, chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id,
                            result="failed", details={"error": str(e)[:200]})
        await cx.reply(T.PUNISH_FAILED)
        return

    await svc.punishments.add(cx.chat.id, target.user_id, kind, cx.user.id, reason, until)
    await svc.audit.log(kind, chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id,
                        details={"seconds": seconds, "reason": reason})
    text = _punish_text(kind, mention(target.user_id, target.name), mention(cx.user.id, cx.user.full_name),
                        seconds=seconds, reason=reason, show_duration=kind != "kick")
    await cx.reply(text, reply_markup=_undo_keyboard(kind, target.user_id))
    if kind in ("ban", "kick"):
        from zhoo.systems import watchdog
        await watchdog.record(cx.bot, svc, cx.chat.id, cx.user.id)   # مراقبة «ش»


async def warn(cx: CommandContext) -> None:
    svc = cx.services
    target = await _get_target(cx, "تحذير @username")
    if target is None:
        return
    reason = _clean_reason(target.rest)
    if not await _decision_reply(cx, target, "warn"):
        return

    limit = await svc.group_settings.get_int(cx.chat.id, "warn_limit")
    count = await svc.punishments.add_warning(cx.chat.id, target.user_id, cx.user.id, reason)
    await svc.audit.log("warn", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id,
                        details={"count": count, "reason": reason})
    who, actor = mention(target.user_id, target.name), mention(cx.user.id, cx.user.full_name)
    text = _punish_text("warn", who, actor, reason=reason, warn=(count, limit), show_duration=False)
    markup = _undo_keyboard("warn", target.user_id)

    if count >= limit:
        action = await svc.group_settings.get(cx.chat.id, "warn_action")
        action = action if action in WARN_ACTIONS else "mute"
        rights = await svc.perms.bot_rights(cx.bot, cx.chat.id)
        if rights is None or not rights.can_restrict_members:
            text += "\n" + (T.BOT_NOT_ADMIN if rights is None else
                            T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT))
        else:
            try:
                await mod.apply(cx.bot, cx.chat.id, target.user_id, action, None)
                await svc.punishments.add(cx.chat.id, target.user_id, action, cx.bot.id,
                                          T.WARN_AUTO_REASON, None)
                await svc.punishments.clear_warnings(cx.chat.id, target.user_id)
                await svc.audit.log(f"auto_{action}", chat_id=cx.chat.id, actor_id=cx.bot.id,
                                    target_id=target.user_id, details={"warnings": count})
                text += T.WARN_LIMIT_REACHED.format(action=WARN_ACTIONS[action])
                markup = _undo_keyboard(action, target.user_id)
            except (BadRequest, Forbidden) as e:
                log.info("فشلت العقوبة التلقائية: %s", e)
                text += "\n" + T.PUNISH_FAILED
    await cx.reply(text, reply_markup=markup)


# ── الفك ───────────────────────────────────────────
async def _is_punished_on_telegram(cx: CommandContext, user_id: int, kind: str) -> bool:
    try:
        member = await cx.bot.get_chat_member(cx.chat.id, user_id)
    except TelegramError:
        return await cx.services.punishments.is_active(cx.chat.id, user_id, kind)
    if kind == "ban":
        return member.status == ChatMemberStatus.BANNED
    return member.status == ChatMemberStatus.RESTRICTED


async def do_lift(svc: Services, bot, chat_id: int, user_id: int, kind: str, actor_id: int) -> None:
    """التنفيذ المشترك للفك (من الأمر أو من زر التراجع)."""
    if kind == "warn":
        await svc.punishments.clear_warnings(chat_id, user_id)
    else:
        await mod.lift(bot, chat_id, user_id, kind)
        kinds = ("mute", "restrict") if kind in ("mute", "restrict") else (kind,)
        for k in kinds:
            await svc.punishments.lift(chat_id, user_id, k, actor_id)
    await svc.audit.log(f"un{kind}", chat_id=chat_id, actor_id=actor_id, target_id=user_id)


async def unpunish(cx: CommandContext, kind: str) -> None:
    states = {"ban": "محظور", "mute": "مكتوم", "restrict": "مقيّد"}
    target = await _get_target(cx, f"فك {KIND_NAMES[kind]} @username")
    if target is None:
        return
    who = mention(target.user_id, target.name)
    if not await _bot_can_restrict(cx):
        return
    if not await _is_punished_on_telegram(cx, target.user_id, kind):
        await cx.services.punishments.lift(cx.chat.id, target.user_id, kind, cx.user.id)
        await cx.reply(T.NOT_PUNISHED.format(mention=who, state=states[kind]))
        return
    try:
        await do_lift(cx.services, cx.bot, cx.chat.id, target.user_id, kind, cx.user.id)
    except (BadRequest, Forbidden) as e:
        log.info("فشل فك %s: %s", kind, e)
        await cx.reply(T.PUNISH_FAILED)
        return
    head, emoji = T.PUNISH_TITLES[f"un{kind}"]
    await cx.reply(T.title(head, emoji) + "\n" + T.PUNISH_BODY.format(
        mention=who, actor=mention(cx.user.id, cx.user.full_name), extra=""))


async def clear_warns(cx: CommandContext) -> None:
    target = await _get_target(cx, "مسح التحذيرات @username")
    if target is None:
        return
    who = mention(target.user_id, target.name)
    if await cx.services.punishments.warning_count(cx.chat.id, target.user_id) == 0:
        await cx.reply(T.NO_WARNINGS.format(mention=who))
        return
    await do_lift(cx.services, cx.bot, cx.chat.id, target.user_id, "warn", cx.user.id)
    head, emoji = T.PUNISH_TITLES["unwarn"]
    await cx.reply(T.title(head, emoji) + "\n" + T.PUNISH_BODY.format(
        mention=who, actor=mention(cx.user.id, cx.user.full_name), extra=""))


# ── تسجيل الأوامر ───────────────────────────────────
def _reg(key, names, kind_rank, description, order, fn, args="punish", usage="بالرد/اليوزر/الايدي"):
    registry.command(key, names, section=S, min_rank=kind_rank, description=description,
                     order=order, args=args, usage=usage)(fn)


async def _ban(cx): await punish(cx, "ban")          # noqa: E704
async def _kick(cx): await punish(cx, "kick")        # noqa: E704
async def _mute(cx): await punish(cx, "mute")        # noqa: E704
async def _restrict(cx): await punish(cx, "restrict")  # noqa: E704
async def _unban(cx): await unpunish(cx, "ban")      # noqa: E704
async def _unmute(cx): await unpunish(cx, "mute")    # noqa: E704
async def _unrestrict(cx): await unpunish(cx, "restrict")  # noqa: E704


_reg("ban", ("حظر", "بان"), MIN_RANK["ban"], "يحظر العضو (مع مدة وسبب اختياريين)", 1, _ban,
     usage="بالرد/اليوزر + مدة + سبب")
_reg("kick", ("طرد",), MIN_RANK["kick"], "يطرد العضو، ويمكنه العودة بالرابط", 2, _kick, usage="بالرد/اليوزر + سبب")
_reg("mute", ("كتم", "اسكات"), MIN_RANK["mute"], "يمنع العضو من الكتابة والإرسال (يگدر يتفاعل بس)", 3, _mute,
     usage="بالرد/اليوزر + مدة + سبب")
_reg("restrict", ("تقييد",), MIN_RANK["restrict"], "يخلي العضو يشوف المجموعة بس، بلا كتابة ولا رياكت ولا أي تفاعل", 4, _restrict,
     usage="بالرد/اليوزر + مدة + سبب")
_reg("warn", ("تحذير", "انذار"), MIN_RANK["warn"], "تحذير، وعند الحد الأقصى تُطبَّق عقوبة تلقائية", 5, warn,
     usage="بالرد/اليوزر + سبب")
_reg("unban", ("إلغاء الحظر", "رفع الحظر", "فك الحظر", "فتح الحظر"), MIN_RANK["ban"], "يرفع الحظر عن العضو", 10, _unban,
     args="target")
_reg("unmute", ("فك الكتم", "إلغاء الكتم", "فتح الكتم"), MIN_RANK["mute"], "يعيد للعضو صلاحية الكتابة", 11, _unmute, args="target")
_reg("unrestrict", ("فك التقييد", "إلغاء التقييد", "فتح التقييد"), MIN_RANK["restrict"], "يرفع التقييد عن العضو", 12,
     _unrestrict, args="target")
_reg("clear_warns", ("مسح التحذيرات", "حذف التحذيرات"), MIN_RANK["warn"], "يمسح كل تحذيرات العضو", 13,
     clear_warns, args="target")


@registry.command("my_warns", ("تحذيراتي",), section=S, description="عدد تحذيراتك", order=20)
async def cmd_my_warns(cx: CommandContext) -> None:
    svc = cx.services
    count = await svc.punishments.warning_count(cx.chat.id, cx.user.id)
    limit = await svc.group_settings.get_int(cx.chat.id, "warn_limit")
    await cx.reply(T.WARNINGS_OF.format(mention=mention(cx.user.id, cx.user.full_name), count=count, limit=limit))


@registry.command("their_warns", ("تحذيراته", "تحذيراتها"), section=S, args="target",
                  usage="بالرد/اليوزر/الايدي", description="عدد تحذيرات عضو", order=21)
async def cmd_their_warns(cx: CommandContext) -> None:
    target = await _get_target(cx, "تحذيراته @username")
    if target is None:
        return
    svc = cx.services
    count = await svc.punishments.warning_count(cx.chat.id, target.user_id)
    limit = await svc.group_settings.get_int(cx.chat.id, "warn_limit")
    await cx.reply(T.WARNINGS_OF.format(mention=mention(target.user_id, target.name), count=count, limit=limit))


def _row_name(r) -> str:
    return " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])


@registry.command("punish_log", ("سجل العقوبات",), section=S, min_rank=Rank.ADMIN, args="target",
                  usage="اختياري: بالرد/اليوزر", description="آخر العقوبات بالمجموعة أو لعضو معيّن", order=33)
async def cmd_punish_log(cx: CommandContext) -> None:
    user_id = None
    if cx.message.reply_to_message is not None or cx.args:
        target = await _get_target(cx, "سجل العقوبات @username")
        if target is None:
            return
        user_id = target.user_id
    rows = await cx.services.punishments.history(cx.chat.id, user_id)
    text = T.PUNISH_LOG_HEADER + "\n"
    if not rows:
        await cx.reply(text + T.PUNISH_LOG_EMPTY)
        return
    lines = []
    for r in rows:
        state = "🟢" if r["active"] and (not r["until"] or r["until"] > time.time()) else "⚪"
        when = time.strftime("%m-%d %H:%M", time.gmtime(r["created_at"]))
        line = f"{state} {KIND_EMOJI[r['kind']]} <b>{KIND_NAMES[r['kind']]}</b> ⋅ {mention(r['user_id'], _row_name(r))}"
        line += f"\n      <code>{when}</code>"
        if r["until"]:
            line += f" ⋅ {format_duration(r['until'] - r['created_at'])}"
        if r["reason"]:
            line += f" ⋅ <i>{esc(r['reason'][:60])}</i>"
        lines.append(line)
    await cx.reply(text + "\n".join(lines) + "\n" + T.PUNISH_LOG_FOOTER)


@registry.command("warn_limit", ("عدد التحذيرات",), section=S, min_rank=Rank.MANAGER, args="text",
                  usage="رقم من 2 إلى 10", description="الحد الأقصى للتحذيرات قبل العقوبة", order=40)
async def cmd_warn_limit(cx: CommandContext) -> None:
    raw = (cx.args[0] if cx.args else "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    if not raw.isdigit() or not 2 <= int(raw) <= 10:
        await cx.reply(T.WARN_SETTINGS_BAD_LIMIT)
        return
    svc = cx.services
    old = await svc.group_settings.set(cx.chat.id, "warn_limit", raw, cx.user.id)
    await svc.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                        details={"key": "warn_limit", "from": old, "to": raw})
    action = await svc.group_settings.get(cx.chat.id, "warn_action")
    await cx.reply(T.WARN_SETTINGS_SET.format(limit=raw, action=WARN_ACTIONS.get(action, "كتم")))


@registry.command("warn_action", ("عقوبة التحذيرات",), section=S, min_rank=Rank.MANAGER, args="text",
                  usage="كتم / طرد / حظر", description="العقوبة التلقائية عند الحد الأقصى", order=41)
async def cmd_warn_action(cx: CommandContext) -> None:
    wanted = normalize(cx.raw_args)
    action = next((k for k, v in WARN_ACTIONS.items() if normalize(v) == wanted), None)
    if action is None:
        await cx.reply(T.WARN_SETTINGS_BAD_ACTION)
        return
    svc = cx.services
    old = await svc.group_settings.set(cx.chat.id, "warn_action", action, cx.user.id)
    await svc.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                        details={"key": "warn_action", "from": old, "to": action})
    limit = await svc.group_settings.get(cx.chat.id, "warn_limit")
    await cx.reply(T.WARN_SETTINGS_SET.format(limit=limit, action=WARN_ACTIONS[action]))


# ── زر التراجع ─────────────────────────────────────
async def on_undo_button(q, msg: Message, svc: Services, bot, code: str, uid_raw: str) -> None:
    """p:<code>:<user_id> — يتحقق من رتبة الضاغط بنفس قواعد الأمر."""
    if code not in UNDO or not uid_raw.isdigit():
        await q.answer()
        return
    kind = UNDO[code][0]
    user_id = int(uid_raw)
    rank = await svc.perms.rank_of(bot, msg.chat.id, q.from_user.id)
    if rank < MIN_RANK[kind]:
        await q.answer(T.UNDO_NOT_ALLOWED, show_alert=True)
        return
    if kind != "warn":
        rights = await svc.perms.bot_rights(bot, msg.chat.id)
        if rights is None or not rights.can_restrict_members:
            await q.answer(T.BOT_NOT_ADMIN.replace(f"{T.BULLET} ", "").replace("<b>", "").replace("</b>", ""),
                           show_alert=True)
            return
    try:
        await do_lift(svc, bot, msg.chat.id, user_id, kind, q.from_user.id)
    except (BadRequest, Forbidden):
        await q.answer(T.PUNISH_FAILED.replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    await q.answer(T.UNDO_DONE)
    footer = T.UNDO_FOOTER.format(actor=mention(q.from_user.id, q.from_user.full_name))
    try:
        await msg.edit_text(msg.text_html + footer, reply_markup=None)
    except BadRequest:
        pass
