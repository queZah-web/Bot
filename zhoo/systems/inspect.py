"""«كشف» بالرد على شخص: تقرير كامل عنه للمشرفين.

هويته ← رتبته وحالته بتيليجرام وصلاحياته المخصصة ← تفاعله ومستواه ← تحذيراته وسبّه وعقوباته ← تواريخه ومنو ضافه.
"""
from __future__ import annotations

import time

from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

from zhoo.core import capabilities as caps
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import activity_level, mention, username_text
from zhoo.core.ranks import Rank, rank_label
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

S = "punish"
VIEW_RANK = Rank.ADMIN
_TG_STATUS = {
    ChatMemberStatus.OWNER: "tg_owner", ChatMemberStatus.ADMINISTRATOR: "tg_admin",
    ChatMemberStatus.MEMBER: "tg_member", ChatMemberStatus.RESTRICTED: "tg_restricted",
    ChatMemberStatus.LEFT: "tg_left", ChatMemberStatus.BANNED: "tg_banned",
}


def _date(ts: int | None) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts)) if ts else "—"


async def _tg_status(cx: CommandContext, user_id: int) -> str:
    try:
        m = await cx.bot.get_chat_member(cx.chat.id, user_id)
    except TelegramError:
        return T.INSPECT_TG["unknown"]
    key = _TG_STATUS.get(m.status, "unknown")
    if m.status == ChatMemberStatus.RESTRICTED and not getattr(m, "can_send_messages", True):
        key = "tg_muted"
    return T.INSPECT_TG[key]


async def build_report(cx: CommandContext, user_id: int, name: str, username: str | None, is_bot: bool) -> str:
    svc: Services = cx.services
    chat_id = cx.chat.id
    await svc.tracker.flush()

    # الرتبة والصلاحيات المخصصة
    rank = await svc.perms.rank_of(cx.bot, chat_id, user_id)
    allow, deny = await svc.member_perms.get(chat_id, user_id)
    custom = ""
    if allow or deny:
        parts = [f"✅ {caps.CAPS[c][0]}" for c in sorted(allow) if c in caps.CAPS]
        parts += [f"▫️ {caps.CAPS[c][0]}" for c in sorted(deny) if c in caps.CAPS]
        custom = T.INSPECT_CUSTOM_PERMS.format(perms=" ⋅ ".join(parts))

    # التفاعل والمستوى
    messages = await svc.members.message_count(chat_id, user_id)
    position = await svc.members.activity_position(chat_id, messages) if messages else None
    from zhoo.core import levels as L
    xp, wins = await svc.levels.get(chat_id, user_id)
    lvl = L.level_for(xp)
    thanks = await svc.social.thanks_count(chat_id, user_id)
    good, bad, avg, voters = await svc.ratings.summary(chat_id, user_id)
    economy = ""
    from zhoo.systems import economy as eco_sys
    if await eco_sys.enabled(svc, chat_id):
        wallet = await svc.economy.wallet(chat_id, user_id)
        economy = T.INSPECT_ECONOMY.format(balance=f"{wallet['balance']:,}")

    # السجل: تحذيرات، سب، عقوبات
    warns = await svc.punishments.warning_count(chat_id, user_id)
    limit = await svc.group_settings.get_int(chat_id, "warn_limit")
    swear_rows = await svc.db.fetchall(
        "SELECT level, COUNT(*) AS n FROM swear_logs WHERE chat_id = ? AND user_id = ? GROUP BY level",
        (chat_id, user_id))
    swear_by_level = {r["level"]: r["n"] for r in swear_rows}
    swear_total = sum(swear_by_level.values())
    from zhoo.core import moderation as mod
    swear_week = await svc.swear_logs.strikes(chat_id, user_id, mod.SWEAR_WINDOW)
    swear_detail = " ⋅ ".join(f"{T.INSPECT_SWEAR_LEVELS[lv]} {n}" for lv, n in sorted(swear_by_level.items())
                              if lv in T.INSPECT_SWEAR_LEVELS)
    pun_rows = await svc.db.fetchall(
        "SELECT kind, COUNT(*) AS n FROM punishments WHERE chat_id = ? AND user_id = ? GROUP BY kind",
        (chat_id, user_id))
    pun = {r["kind"]: r["n"] for r in pun_rows}
    pun_text = " ⋅ ".join(f"{T.INSPECT_PUNISH_KINDS[k]} {pun[k]}" for k in T.INSPECT_PUNISH_KINDS if pun.get(k)) \
        or T.INSPECT_CLEAN
    active = [T.INSPECT_PUNISH_KINDS[k] for k in ("ban", "mute", "restrict")
              if await svc.punishments.is_active(chat_id, user_id, k)]

    # التواريخ ومنو ضافه
    row = await svc.db.fetchone("SELECT first_seen, last_seen FROM group_members WHERE chat_id = ? AND user_id = ?",
                                (chat_id, user_id))
    added_by = await svc.members.added_by(chat_id, user_id)
    if added_by:
        adder = await svc.users.get(added_by)
        added = mention(added_by, adder.full_name if adder else str(added_by))
    elif added_by == 0:
        added = T.INSPECT_SELF_JOINED
    else:
        added = T.INSPECT_UNKNOWN

    return T.INSPECT.format(
        name=mention(user_id, name), id=user_id, username=username_text(username),
        kind=T.INSPECT_KIND_BOT if is_bot else T.INSPECT_KIND_USER,
        rank=rank_label(rank), tg=await _tg_status(cx, user_id), custom=custom,
        messages=f"{messages:,}", position=f"#{position}" if position else "—", activity=activity_level(messages),
        level=lvl, xp=f"{xp:,}", wins=wins, thanks=thanks,
        rating=f"{avg:.1f}/10 ({voters})" if avg is not None else T.INSPECT_NO_RATING, good=good, bad=bad,
        economy=economy, warns=warns, limit=limit,
        swear=swear_total, swear_week=swear_week,
        swear_detail=f" ({swear_detail})" if swear_detail else "",
        punish=pun_text, active=" ⋅ ".join(active) if active else T.INSPECT_NO_ACTIVE,
        first=_date(row["first_seen"] if row else None), last=_date(row["last_seen"] if row else None),
        added=added,
    )


@registry.command("inspect", ("كشف", "كشف عضو", "كشف حساب"), section=S, min_rank=VIEW_RANK, args="target",
                  usage="بالرد/اليوزر/الايدي",
                  description="تقرير كامل عن العضو: رتبته، تفاعله، سبّه، عقوباته، ومنو ضافه", order=30)
async def cmd_inspect(cx: CommandContext) -> None:
    if cx.message.reply_to_message is None and not cx.args:
        user = cx.user
        text = await build_report(cx, user.id, user.full_name, user.username, False)
    else:
        try:
            target = await resolve_target(cx)
        except TargetError as e:
            await reply_target_error(cx, e, "كشف @username")
            return
        text = await build_report(cx, target.user_id, target.name, target.username, target.is_bot)
    await cx.services.audit.log("inspect", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(text)

