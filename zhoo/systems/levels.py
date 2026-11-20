"""الخبرة والمستويات.

مصادر الخبرة:
  • الرسائل المفيدة: من 8 لـ 15 نقطة، مرة كل 45 ثانية بالكثير، وبشرط تكون الرسالة
    مو قصيرة (3 حروف وأكثر) ومو نفس رسالتك السابقة — فالسبام ما يفيد.
  • الفوز بالألعاب: مكافأة حسب الصعوبة.
"""
from __future__ import annotations

import hashlib
import random
import time

from zhoo.core import levels as L
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

S = "levels"
XP_COOLDOWN = 45
XP_MIN, XP_MAX = 8, 15
MIN_CHARS = 3
TOGGLE_RANK = Rank.MANAGER


async def enabled(svc: Services, chat_id: int) -> bool:
    return (await svc.group_settings.get(chat_id, "levels_on")) == "1"


async def give_xp(context, svc: Services, chat, user, amount: int) -> int:
    """يضيف خبرة، ويعلن الترقية إذا صارت. يرجع المستوى الجديد."""
    old, new = await svc.levels.add_xp(chat.id, user.id, amount)
    old_lvl, new_lvl = L.level_for(old), L.level_for(new)
    if new_lvl > old_lvl:
        from zhoo.systems import economy
        await economy.on_levelup(svc, chat.id, user.id, new_lvl)
    if new_lvl > old_lvl and (await svc.group_settings.get(chat.id, "levelup_notice")) == "1":
        from zhoo.systems.protect import send_notice
        await send_notice(context, chat.id, T.LEVEL_UP.format(
            mention=mention(user.id, user.full_name), level=new_lvl, title=L.title_for(new_lvl)), ttl=60)
    return new_lvl


async def on_message(context, svc: Services, msg, chat, user) -> None:
    """خبرة الرسائل العادية — مع مهلة ومنع التكرار."""
    text = msg.text or ""
    norm = normalize(text)
    if len(norm.replace(" ", "")) < MIN_CHARS or not await enabled(svc, chat.id):
        return
    key = (chat.id, user.id)
    fp = hashlib.blake2b(norm.encode(), digest_size=6).hexdigest()
    last = svc.xp_seen.get(key)
    now = time.monotonic()
    if last and (now - last[0] < XP_COOLDOWN or last[1] == fp):
        return
    if len(svc.xp_seen) > 50_000:
        svc.xp_seen.clear()
    svc.xp_seen[key] = (now, fp)
    await give_xp(context, svc, chat, user, random.randint(XP_MIN, XP_MAX))
    from zhoo.systems import economy
    await economy.mission(context, svc, chat, user, "messages")


# ── بطاقة المستوى ───────────────────────────────────
async def _card(cx: CommandContext, user_id: int, name: str) -> None:
    svc = cx.services
    xp, wins = await svc.levels.get(cx.chat.id, user_id)
    level, have, need, ratio = L.progress(xp)
    messages = await svc.members.message_count(cx.chat.id, user_id)
    thanks = await svc.social.thanks_count(cx.chat.id, user_id)
    _, _, avg, voters = await svc.ratings.summary(cx.chat.id, user_id)
    badges = L.badges(messages, thanks, wins, level, avg, voters)
    await cx.reply(T.LEVEL_CARD.format(
        name=mention(user_id, name), level=level, title=L.title_for(level), xp=f"{xp:,}",
        bar=L.bar(ratio), pct=int(ratio * 100), next=level + 1, left=f"{need - have:,}",
        pos=await svc.levels.position(cx.chat.id, xp), wins=wins,
        badges=" ⋅ ".join(badges) if badges else T.NO_BADGES))


@registry.command("my_level", ("مستواي", "لفلي"), section=S, description="بطاقة مستواك وتقدمك", order=1)
async def cmd_my_level(cx: CommandContext) -> None:
    if not await enabled(cx.services, cx.chat.id):
        await cx.reply(T.LEVELS_OFF)
        return
    await _card(cx, cx.user.id, cx.user.full_name)


@registry.command("their_level", ("مستواه", "مستواها"), section=S, args="target", usage="بالرد/اليوزر",
                  description="مستوى عضو ثاني", order=2)
async def cmd_their_level(cx: CommandContext) -> None:
    if not await enabled(cx.services, cx.chat.id):
        await cx.reply(T.LEVELS_OFF)
        return
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "مستواه @username")
        return
    await _card(cx, target.user_id, target.name)


# ── الترتيب ─────────────────────────────────────────
async def send_board(cx: CommandContext, kind: str) -> None:
    svc = cx.services
    if kind == "all":
        rows = await svc.levels.top(cx.chat.id)
    elif kind == "wins":
        rows = await svc.levels.top_wins(cx.chat.id)
    else:
        rows = await svc.levels.top_since(cx.chat.id, 7 if kind == "week" else 30)
    header = T.LEADERBOARD_HEADERS[kind] + f"\n{T.LINE}"
    if not rows:
        await cx.reply(f"{header}\n{T.LEADERBOARD_EMPTY}")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    unit = T.LEADERBOARD_UNITS[kind]
    lines = []
    for i, r in enumerate(rows):
        name = " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])
        extra = f" ⋅ م{L.level_for(r['value'])}" if kind == "all" else ""
        lines.append(f"{medals[i]} {mention(r['user_id'], name)} ⋅ <b>{r['value']:,}</b> {unit}{extra}")
    await cx.reply(f"{header}\n" + "\n".join(lines))


async def _board_all(cx): await send_board(cx, "all")       # noqa: E704
async def _board_week(cx): await send_board(cx, "week")     # noqa: E704
async def _board_month(cx): await send_board(cx, "month")   # noqa: E704


registry.command("board_all", ("ترتيب المستويات", "توب المستويات"), section=S,
                 description="أعلى 10 بالخبرة (كل الوقت)", order=3)(_board_all)
registry.command("board_week", ("ترتيب الاسبوع", "ترتيب الأسبوع"), section=S,
                 description="أنشط 10 بآخر 7 أيام", order=4)(_board_week)
registry.command("board_month", ("ترتيب الشهر",), section=S,
                 description="أنشط 10 بآخر 30 يوم", order=5)(_board_month)


@registry.command("titles", ("الالقاب", "الألقاب"), section=S, description="الألقاب وكل لقب من أي مستوى", order=6)
async def cmd_titles(cx: CommandContext) -> None:
    lines = [T.TITLES_LINE.format(level=need, title=t) for need, t in L.TITLES]
    await cx.reply(f"{T.TITLES_HEADER}\n" + "\n".join(lines))


# ── الإعدادات ───────────────────────────────────────
def _toggle(key: str, on: bool, what: str):
    async def handler(cx: CommandContext) -> None:
        await cx.services.group_settings.set(cx.chat.id, key, "1" if on else "0", cx.user.id)
        await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                    details={"key": key, "to": int(on)})
        await cx.reply((T.TOGGLE_ON if on else T.TOGGLE_OFF).format(what=what))
    return handler


registry.command("levels_on", ("تفعيل المستويات",), section=S, min_rank=TOGGLE_RANK,
                 description="يشغّل نظام الخبرة", order=10)(_toggle("levels_on", True, "المستويات"))
registry.command("levels_off", ("تعطيل المستويات",), section=S, min_rank=TOGGLE_RANK,
                 description="يوقف نظام الخبرة", order=11)(_toggle("levels_on", False, "المستويات"))
registry.command("levelup_on", ("تفعيل اعلان المستوى", "تفعيل إعلان المستوى"), section=S,
                 min_rank=TOGGLE_RANK, description="يعلن لما أحد يترقى",
                 order=12)(_toggle("levelup_notice", True, "إعلان المستوى"))
registry.command("levelup_off", ("تعطيل اعلان المستوى", "تعطيل إعلان المستوى"), section=S,
                 min_rank=TOGGLE_RANK, description="يوقف إعلان الترقية",
                 order=13)(_toggle("levelup_notice", False, "إعلان المستوى"))
