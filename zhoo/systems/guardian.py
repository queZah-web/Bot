"""الحارس: صد الهجوم ⋅ الوضع الليلي ⋅ انتهاء التحذيرات.

صد الهجوم (شغّال افتراضياً): إذا دخل RAID_JOINS حساب خلال RAID_WINDOW ثانية (بدون ما يضيفهم أدمن)،
زهو تطرد اللي دخلوا بالموجة، وتقفل الدخول RAID_LOCK ثانية (كل داخل جديد ينطرد)، وتنادي المالكين.
«انهاء الهجوم» يفتح قبل الوقت ⋅ «تعطيل صد الهجوم» / «تفعيل صد الهجوم».

الوضع الليلي: «تفعيل الوضع الليلي 2 8» ← الدردشة تنقفل من 2 بالليل لـ 8 الصبح بتوقيت بغداد وتنفتح لحالها.
ما يفتح دردشة الإدارة قفلتها بإيدها.

انتهاء التحذيرات: «مدة التحذيرات 7» ← التحذير ينمسح بعد 7 أيام ⋅ «مدة التحذيرات 0» = ما تنتهي.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from telegram.error import TelegramError

from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.fmt import mention
from zhoo.core.ranks import Rank
from zhoo.database.db import now

log = logging.getLogger(__name__)
S = "protect"
BAGHDAD = timezone(timedelta(hours=3))

RAID_JOINS = 12
RAID_WINDOW = 60
RAID_LOCK = 10 * 60
RAID_TOGGLE_RANK = Rank.MANAGER
NIGHT_RANK = Rank.MANAGER
WARN_EXPIRY_RANK = Rank.MANAGER

_joins: dict[int, deque[tuple[float, int]]] = {}


# ── صد الهجوم ───────────────────────────────────────
async def raid_enabled(svc: Services, chat_id: int) -> bool:
    return await svc.group_settings.get(chat_id, "raid_guard") != "0"


async def raid_left(svc: Services, chat_id: int) -> int:
    until = await svc.group_settings.get_int(chat_id, "raid_until")
    return max(0, until - now())


async def _kick(context, chat_id: int, user_id: int) -> bool:
    try:
        await mod.apply(context.bot, chat_id, user_id, "kick", None)
        return True
    except TelegramError as e:
        log.info("صد الهجوم: ما گدرت أطرد %s: %s", user_id, e)
        return False


async def on_join(context, svc: Services, chat, member, added_by_admin: bool) -> bool:
    """يرجع True إذا العضو انطرد بسبب هجوم."""
    if added_by_admin or member.is_bot or not await raid_enabled(svc, chat.id):
        return False
    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_restrict_members:
        return False
    if await raid_left(svc, chat.id):
        await _kick(context, chat.id, member.id)
        return True
    t = time.monotonic()
    q = _joins.setdefault(chat.id, deque())
    q.append((t, member.id))
    while q and t - q[0][0] > RAID_WINDOW:
        q.popleft()
    if len(_joins) > 5000:
        _joins.clear()
    if len(q) < RAID_JOINS:
        return False
    # هجوم: نطرد الموجة كلها ونقفل الدخول
    wave = [uid for _, uid in q]
    q.clear()
    await svc.group_settings.set(chat.id, "raid_until", str(now() + RAID_LOCK), context.bot.id)
    kicked = 0
    for uid in wave:
        kicked += await _kick(context, chat.id, uid)
        await asyncio.sleep(0.05)
    await svc.audit.log("raid_on", chat_id=chat.id, actor_id=context.bot.id, details={"n": kicked})
    owners = await _owners_mentions(context, svc, chat.id)
    from zhoo.systems.protect import send_notice
    await send_notice(context, chat.id, T.RAID_ON.format(n=kicked, minutes=RAID_LOCK // 60, owners=owners), ttl=0)
    return True


async def _owners_mentions(context, svc: Services, chat_id: int) -> str:
    admins = await svc.perms.admins(context.bot, chat_id)
    creator = next((m for m in admins.values() if m.status == "creator" and not m.is_anonymous), None)
    people = [mention(creator.user.id, creator.user.full_name)] if creator else []
    for r in await svc.members.list_ranked(chat_id):
        if r["rank"] >= Rank.OWNER and len(people) < 5:
            name = " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])
            people.append(mention(r["user_id"], name))
    return " ⋅ ".join(people) or T.NONE_VALUE


@registry.command("raid_end", ("انهاء الهجوم", "إنهاء الهجوم", "فتح الهجوم"), section=S, min_rank=Rank.ADMIN,
                  description="يفتح الدخول قبل ما يخلص وقت صد الهجوم", order=60)
async def cmd_raid_end(cx: CommandContext) -> None:
    if not await raid_left(cx.services, cx.chat.id):
        await cx.reply(T.RAID_NONE)
        return
    await cx.services.group_settings.set(cx.chat.id, "raid_until", "0", cx.user.id)
    await cx.services.audit.log("raid_off", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.RAID_ENDED.format(actor=mention(cx.user.id, cx.user.full_name)))


def _raid_toggle(on: bool):
    async def handler(cx: CommandContext) -> None:
        await cx.services.group_settings.set(cx.chat.id, "raid_guard", "1" if on else "0", cx.user.id)
        await cx.reply(T.RAID_TOGGLED[on].format(n=RAID_JOINS, secs=RAID_WINDOW))
    return handler


registry.command("raid_on", ("تفعيل صد الهجوم", "تفعيل ضد الهجوم"), section=S, min_rank=RAID_TOGGLE_RANK,
                 description=f"يحمي من دخول {RAID_JOINS} حساب خلال دقيقة 🛡", order=61)(_raid_toggle(True))
registry.command("raid_off", ("تعطيل صد الهجوم", "تعطيل ضد الهجوم"), section=S, min_rank=RAID_TOGGLE_RANK,
                 description="يوقف صد الهجوم", order=62)(_raid_toggle(False))


# ── الوضع الليلي ────────────────────────────────────
def in_window(hour: int, start: int, end: int) -> bool:
    return start <= hour < end if start < end else (hour >= start or hour < end)


def _hours(raw: str) -> tuple[int, int] | None:
    nums = [int(x) for x in raw.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")).replace("-", " ").split()
            if x.isdigit()]
    if not nums:
        return 2, 8
    if len(nums) != 2 or not all(0 <= n <= 23 for n in nums) or nums[0] == nums[1]:
        return None
    return nums[0], nums[1]


def _h(hour: int) -> str:
    return f"{hour % 12 or 12} {'ص' if hour < 12 else 'م'}"


@registry.command("night_on", ("تفعيل الوضع الليلي", "الوضع الليلي تفعيل"), section=S, min_rank=NIGHT_RANK,
                  args="text", usage="من ساعة لساعة (مثال: 2 8)",
                  description="الدردشة تنقفل بالليل وتنفتح الصبح لحالها 🌙", order=63)
async def cmd_night_on(cx: CommandContext) -> None:
    hours = _hours(cx.raw_args)
    if hours is None:
        await cx.reply(T.NIGHT_BAD)
        return
    svc = cx.services
    for key, value in (("night_on", "1"), ("night_from", str(hours[0])), ("night_to", str(hours[1]))):
        await svc.group_settings.set(cx.chat.id, key, value, cx.user.id)
    await svc.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                        details={"key": "night", "from": hours[0], "to": hours[1]})
    await cx.reply(T.NIGHT_ON.format(start=_h(hours[0]), end=_h(hours[1])))


@registry.command("night_off", ("تعطيل الوضع الليلي", "الوضع الليلي تعطيل"), section=S, min_rank=NIGHT_RANK,
                  description="يوقف الوضع الليلي", order=64)
async def cmd_night_off(cx: CommandContext) -> None:
    svc = cx.services
    await svc.group_settings.set(cx.chat.id, "night_on", "0", cx.user.id)
    if await svc.group_settings.get(cx.chat.id, "night_active") == "1":
        from zhoo.systems import locks
        await locks.set_mode(svc, cx.bot, cx.chat.id, "chat", None, cx.user.id)
        await svc.group_settings.set(cx.chat.id, "night_active", "0", cx.user.id)
    await cx.reply(T.NIGHT_OFF)


@registry.command("night_status", ("الوضع الليلي",), section=S, description="وقت الوضع الليلي", order=65)
async def cmd_night_status(cx: CommandContext) -> None:
    svc = cx.services
    if await svc.group_settings.get(cx.chat.id, "night_on") != "1":
        await cx.reply(T.NIGHT_STATUS_OFF)
        return
    start = await svc.group_settings.get_int(cx.chat.id, "night_from")
    end = await svc.group_settings.get_int(cx.chat.id, "night_to")
    await cx.reply(T.NIGHT_STATUS.format(start=_h(start), end=_h(end)))


async def night_tick(bot, svc: Services, chat_id: int, hour: int) -> str | None:
    """يقرر لمجموعة وحدة. يرجع start/end إذا تغير شي."""
    from zhoo.systems import botstate, locks
    if not await botstate.is_active(svc, chat_id):
        return None
    start = await svc.group_settings.get_int(chat_id, "night_from")
    end = await svc.group_settings.get_int(chat_id, "night_to")
    active = await svc.group_settings.get(chat_id, "night_active") == "1"
    want = in_window(hour, start, end)
    if want and not active:
        if await locks.is_locked(svc, chat_id, "chat"):
            return None                       # الإدارة قافلتها بإيدها: ما نلمسها
        if await locks.set_mode(svc, bot, chat_id, "chat", "delete", bot.id) != "ok":
            return None
        await svc.group_settings.set(chat_id, "night_active", "1", bot.id)
        return "start"
    if not want and active:
        await locks.set_mode(svc, bot, chat_id, "chat", None, bot.id)
        await svc.group_settings.set(chat_id, "night_active", "0", bot.id)
        return "end"
    return None


async def night_job(context) -> None:
    svc = get_services(context)
    hour = datetime.now(BAGHDAD).hour
    rows = await svc.db.fetchall("SELECT chat_id FROM group_settings WHERE key = 'night_on' AND value = '1'")
    for r in rows:
        try:
            change = await night_tick(context.bot, svc, r["chat_id"], hour)
        except TelegramError as e:
            log.info("الوضع الليلي %s: %s", r["chat_id"], e)
            continue
        if change:
            end = await svc.group_settings.get_int(r["chat_id"], "night_to")
            text = T.NIGHT_START.format(end=_h(end)) if change == "start" else T.NIGHT_END
            from zhoo.systems.protect import send_notice
            await send_notice(context, r["chat_id"], text, ttl=0)
        await asyncio.sleep(0.05)


# ── انتهاء التحذيرات ────────────────────────────────
@registry.command("warn_expiry", ("مدة التحذيرات", "مده التحذيرات", "انتهاء التحذيرات"), section="punish",
                  min_rank=WARN_EXPIRY_RANK, args="text", usage="عدد الأيام (0 = ما تنتهي)",
                  description="التحذير ينمسح لحاله بعد كم يوم", order=42)
async def cmd_warn_expiry(cx: CommandContext) -> None:
    raw = cx.raw_args.strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    svc = cx.services
    if not raw:
        days = await svc.group_settings.get_int(cx.chat.id, "warn_expiry_days")
        await cx.reply(T.WARN_EXPIRY_SHOW.format(v=T.WARN_EXPIRY_DAYS.format(n=days) if days else T.WARN_EXPIRY_NEVER))
        return
    if not raw.isdigit() or int(raw) > 365:
        await cx.reply(T.WARN_EXPIRY_BAD)
        return
    days = int(raw)
    await svc.group_settings.set(cx.chat.id, "warn_expiry_days", str(days), cx.user.id)
    await svc.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                        details={"key": "warn_expiry_days", "to": days})
    await cx.reply(T.WARN_EXPIRY_SET.format(v=T.WARN_EXPIRY_DAYS.format(n=days) if days else T.WARN_EXPIRY_NEVER))


async def expire_warnings(svc: Services) -> int:
    return await svc.db.execute(
        "UPDATE warnings SET active = 0 WHERE active = 1 AND EXISTS ("
        "SELECT 1 FROM group_settings s WHERE s.chat_id = warnings.chat_id AND s.key = 'warn_expiry_days' "
        "AND CAST(s.value AS INTEGER) > 0 AND warnings.created_at < ? - CAST(s.value AS INTEGER) * 86400)",
        (now(),))
