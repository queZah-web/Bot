"""ميزات إضافية: ضافني، افتاري، اطردني، المنشن للكل، التسلية، الكت، الخدمية، الأذكار، وردود زهو."""
from __future__ import annotations

import ast
import asyncio
import hashlib
import logging
import operator
import random
import time
from datetime import date, datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import levels as L
from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank
from zhoo.core.ratelimit import RateLimiter
from zhoo.core.targets import Target, TargetError, resolve_target
from zhoo.data import extras_bank as bank
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S_SOCIAL, S_GROUP, S_GAMES = "social", "group", "games"
BAGHDAD = timezone(timedelta(hours=3))
MENTION_BATCH, MENTION_DELAY = 6, 1.5


async def _target_or_self(cx: CommandContext) -> Target:
    if cx.message.reply_to_message is None and not cx.args:
        return Target(cx.user.id, cx.user.full_name, cx.user.username, False)
    return await resolve_target(cx)


# ── ضافني ───────────────────────────────────────────
async def _who_added(cx: CommandContext, target: Target) -> None:
    who = mention(target.user_id, target.name)
    adder = await cx.services.members.added_by(cx.chat.id, target.user_id)
    if adder is None:
        await cx.reply(T.WHO_ADDED_UNKNOWN.format(mention=who))
    elif adder == 0:
        await cx.reply(T.WHO_ADDED_SELF.format(mention=who))
    else:
        u = await cx.services.users.get(adder)
        await cx.reply(T.WHO_ADDED.format(mention=who, adder=mention(adder, u.full_name if u else str(adder))))


@registry.command("whoadded", ("ضافني", "منو ضافني"), section=S_SOCIAL, description="منو ضافك للمجموعة", order=40)
async def cmd_whoadded(cx: CommandContext) -> None:
    await _who_added(cx, Target(cx.user.id, cx.user.full_name, cx.user.username, False))


@registry.command("their_adder", ("ضافه", "منو ضافه"), section=S_SOCIAL, args="target", usage="بالرد/اليوزر",
                  description="منو ضاف عضو معيّن", order=41)
async def cmd_their_adder(cx: CommandContext) -> None:
    try:
        await _who_added(cx, await resolve_target(cx))
    except TargetError as e:
        await reply_target_error(cx, e, "ضافه @username")


# ── افتاري ──────────────────────────────────────────
async def _avatar(cx: CommandContext, target: Target) -> None:
    who = mention(target.user_id, target.name)
    try:
        photos = await cx.bot.get_user_profile_photos(target.user_id, limit=1)
    except TelegramError:
        photos = None
    if not photos or not photos.total_count:
        await cx.reply(T.AVATAR_NONE.format(mention=who))
        return
    await cx.message.reply_photo(photos.photos[0][-1].file_id,
                                 caption=T.AVATAR_CAPTION.format(mention=who, count=photos.total_count))


@registry.command("avatar", ("افتاري", "صورتي"), section=S_SOCIAL, description="صورة حسابك", order=42)
async def cmd_avatar(cx: CommandContext) -> None:
    await _avatar(cx, Target(cx.user.id, cx.user.full_name, cx.user.username, False))


@registry.command("their_avatar", ("افتاره", "صورته", "افتارها", "صورتها"), section=S_SOCIAL, args="target",
                  usage="بالرد/اليوزر", description="صورة حساب عضو", order=43)
async def cmd_their_avatar(cx: CommandContext) -> None:
    try:
        await _avatar(cx, await resolve_target(cx))
    except TargetError as e:
        await reply_target_error(cx, e, "افتاره @username")


# ── اطردني ──────────────────────────────────────────
@registry.command("kickme", ("اطردني", "طلعني"), section=S_GROUP, description="تطلع من المجموعة (بتأكيد)", order=50)
async def cmd_kickme(cx: CommandContext) -> None:
    if cx.rank >= Rank.ADMIN:
        await cx.reply(T.KICKME_ADMIN)
        return
    uid = cx.user.id
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_KICKME_YES, callback_data=f"km:{uid}:y"),
                                InlineKeyboardButton(T.BTN_KICKME_NO, callback_data=f"km:{uid}:n")]])
    await cx.reply(T.KICKME_ASK.format(mention=mention(uid, cx.user.full_name)), reply_markup=kb)


async def on_kickme_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.KICKME_NOT_YOURS, show_alert=True)
        return
    who = mention(q.from_user.id, q.from_user.full_name)
    if action == "y":
        try:
            await mod.apply(bot, msg.chat.id, q.from_user.id, "kick", None)
        except TelegramError:
            await q.answer(T.PUNISH_FAILED.replace(f"{T.BULLET} ", ""), show_alert=True)
            return
        await svc.audit.log("kickme", chat_id=msg.chat.id, actor_id=q.from_user.id, target_id=q.from_user.id)
        text = T.KICKME_DONE.format(mention=who)
    else:
        text = T.KICKME_STAY
    await q.answer()
    try:
        await msg.edit_text(text, reply_markup=None)
    except BadRequest:
        pass


# ── المنشن للكل ─────────────────────────────────────
async def _run_mentions(bot, svc: Services, chat_id: int, ids: list[int], header: str) -> None:
    sent = 0
    try:
        for i in range(0, len(ids), MENTION_BATCH):
            chunk = ids[i:i + MENTION_BATCH]
            names = []
            for uid in chunk:
                u = await svc.users.get(uid)
                names.append(mention(uid, u.full_name if u else "🌸"))
            await bot.send_message(chat_id, header + " ⋅ ".join(names))
            sent += len(chunk)
            await asyncio.sleep(MENTION_DELAY)
        await bot.send_message(chat_id, T.MENTION_DONE.format(n=sent))
    except asyncio.CancelledError:
        pass
    except TelegramError as e:
        log.info("توقف المنشن: %s", e)
    finally:
        svc.mention_tasks.pop(chat_id, None)


@registry.command("mention_all", ("منشن", "نداء", "تاك للكل", "منشن للكل"), section=S_GROUP, min_rank=Rank.ADMIN,
                  args="text", usage="اختياري: الرسالة", description="ينادي الأعضاء النشطين (آخر 30 يوم)", order=51)
async def cmd_mention_all(cx: CommandContext) -> None:
    svc = cx.services
    if cx.chat.id in svc.mention_tasks:
        await cx.reply(T.MENTION_RUNNING)
        return
    ids = [i for i in await svc.members.recent_active(cx.chat.id) if i != cx.bot.id]
    if not ids:
        await cx.reply(T.MENTION_EMPTY)
        return
    header = T.MENTION_HEADER.format(text=esc(cx.raw_args.strip()[:300]) or "🌸")
    await svc.audit.log("mention_all", chat_id=cx.chat.id, actor_id=cx.user.id, details={"n": len(ids)})
    svc.mention_tasks[cx.chat.id] = asyncio.get_running_loop().create_task(
        _run_mentions(cx.bot, svc, cx.chat.id, ids, header))


@registry.command("mention_stop", ("ايقاف المنشن", "وقف المنشن"), section=S_GROUP, min_rank=Rank.ADMIN,
                  description="يوقف النداء الشغّال", order=52)
async def cmd_mention_stop(cx: CommandContext) -> None:
    task = cx.services.mention_tasks.pop(cx.chat.id, None)
    if task is None:
        await cx.reply(T.MENTION_NONE)
        return
    task.cancel()
    await cx.reply(T.MENTION_STOPPED)


# ── التسلية ─────────────────────────────────────────
def daily_pct(*parts: object) -> int:
    """نسبة ثابتة لنفس الأشخاص بنفس اليوم (حتى ما تتغير كل ما تنسأل)."""
    seed = f"{date.today().isoformat()}:" + ":".join(str(p) for p in parts)
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 101


@registry.command("fun_love", ("نسبه الحب", "نسبة الحب"), section=S_GAMES, args="target", usage="بالرد/اليوزر",
                  description="نسبة الحب بينك وبين عضو 💞", order=30)
async def cmd_love(cx: CommandContext) -> None:
    try:
        target = await resolve_target(cx)
    except TargetError:
        await cx.reply(T.FUN_LOVE_NEED)
        return
    a, b = sorted((cx.user.id, target.user_id))
    pct = daily_pct("love", a, b)
    await cx.reply(T.FUN_LOVE.format(a=mention(cx.user.id, cx.user.full_name), b=mention(target.user_id, target.name),
                                     pct=pct, bar=L.bar(pct / 100)))


def _ratio_cmd(key: str, what: str, emoji: str):
    async def handler(cx: CommandContext) -> None:
        try:
            target = await _target_or_self(cx)
        except TargetError as e:
            await reply_target_error(cx, e, f"نسبة {what} @username")
            return
        pct = daily_pct(key, target.user_id)
        await cx.reply(T.FUN_RATIO.format(what=f"نسبة {what}", who=mention(target.user_id, target.name), pct=pct,
                                          emoji=emoji, bar=L.bar(pct / 100)))
    return handler


for _key, _names, _what, _emoji, _order in (
    ("fun_beauty", ("نسبه الجمال", "نسبة الجمال"), "الجمال", "✨", 31),
    ("fun_smart", ("نسبه الذكاء", "نسبة الذكاء"), "الذكاء", "🧠", 32),
    ("fun_kind", ("نسبه الطيبه", "نسبة الطيبة"), "الطيبة", "🤍", 33),
    ("fun_luck_pct", ("نسبه الحظ", "نسبة الحظ"), "الحظ", "🍀", 34),
):
    registry.command(_key, _names, section=S_GAMES, args="target", usage="اختياري: بالرد",
                     description=f"نسبة {_what} {_emoji}", order=_order)(_ratio_cmd(_key, _what, _emoji))

LUCK = ("نار 🔥 يومك حلو", "ممتاز ✨ كلشي يمشي وياك", "زين 🙂 بس دير بالك", "متوسط 🌥 اصبر شوية",
        "مو أحسن شي 🌧 بس باچر أحلى", "خرافي 🍀 لا تفوّت الفرص")


@registry.command("fun_luck", ("حظي اليوم", "حظي"), section=S_GAMES, description="حظك اليوم 🍀", order=35)
async def cmd_luck(cx: CommandContext) -> None:
    await cx.reply(T.FUN_LUCK.format(mention=mention(cx.user.id, cx.user.full_name),
                                     luck=LUCK[daily_pct("luck", cx.user.id) % len(LUCK)]))


@registry.command("fun_choose", ("زهو اختاري", "اختاري"), section=S_GAMES, args="text", usage="شي او شي",
                  description="زهو تختار بدالك", order=36)
async def cmd_choose(cx: CommandContext) -> None:
    import re
    options = [o.strip() for o in re.split(r"\s+(?:او|أو|ولا)\s+|،|,", cx.raw_args) if o.strip()]
    if len(options) < 2:
        await cx.reply(T.FUN_CHOICE_BAD)
        return
    await cx.reply(T.FUN_CHOICE.format(choice=esc(random.choice(options)[:100])))


@registry.command("kt", ("كت", "كت تويت"), section=S_GAMES, description="سؤال عشوائي للسوالف 💭", order=37)
async def cmd_kt(cx: CommandContext) -> None:
    await cx.reply(f"{T.KT_TITLE}\n{T.LINE}\n{random.choice(bank.KT)}")


# ── الخدمية ─────────────────────────────────────────
WEEKDAYS = ("الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد")
MONTHS = ("كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول",
          "تشرين الأول", "تشرين الثاني", "كانون الأول")


@registry.command("time", ("الوقت", "الساعه", "الساعة", "شكد الساعه"), section=S_GROUP,
                  description="الساعة هسه بتوقيت بغداد", where="any", order=60)
async def cmd_time(cx: CommandContext) -> None:
    now = datetime.now(BAGHDAD)
    hour = now.hour % 12 or 12
    await cx.reply(T.TIME_TEXT.format(time=f"{hour}:{now.minute:02d} {'ص' if now.hour < 12 else 'م'}"))


@registry.command("date", ("التاريخ", "تاريخ اليوم"), section=S_GROUP, description="تاريخ اليوم", where="any",
                  order=61)
async def cmd_date(cx: CommandContext) -> None:
    now = datetime.now(BAGHDAD)
    await cx.reply(T.DATE_TEXT.format(weekday=WEEKDAYS[now.weekday()], day=now.day, month=MONTHS[now.month - 1],
                                      year=now.year))


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def safe_calc(expr: str) -> float | None:
    """حاسبة آمنة: أرقام وعمليات بس (بدون eval)."""
    expr = (expr.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")).replace("×", "*").replace("÷", "/")
            .replace("^", "**").replace("x", "*").replace("X", "*"))
    if not expr.strip() or len(expr) > 100:
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = ev(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > 50 or abs(left) > 1e6):
                raise ValueError("كبير")
            result = _OPS[type(node.op)](left, right)
            if abs(result) > 1e15:
                raise ValueError("كبير")
            return result
        raise ValueError("ممنوع")

    try:
        return ev(tree)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None


@registry.command("calc", ("احسب", "حاسبه", "حاسبة"), section=S_GROUP, args="text", usage="العملية",
                  description="حاسبة: احسب (5 + 3) × 2", where="any", order=62)
async def cmd_calc(cx: CommandContext) -> None:
    result = safe_calc(cx.raw_args)
    if result is None:
        await cx.reply(T.CALC_BAD)
        return
    shown = int(result) if float(result).is_integer() else round(result, 6)
    await cx.reply(T.CALC_RESULT.format(expr=esc(cx.raw_args.strip()), result=f"{shown:,}" if isinstance(shown, int)
                                        else shown))


# ── الأذكار ────────────────────────────────────────
@registry.command("azkar_now", ("ذكر", "اذكار", "أذكار"), section=S_GROUP, description="ذكر من الأذكار 📿", order=63)
async def cmd_azkar(cx: CommandContext) -> None:
    await cx.reply(f"{T.AZKAR_TITLE}\n{T.LINE}\n{random.choice(bank.AZKAR)}")


async def azkar_job(context) -> None:
    """كل 3 ساعات: ذكر للمجموعات اللي مفعّلة الأذكار وبيها نشاط آخر 6 ساعات."""
    from zhoo.systems import botstate, features
    svc = get_services(context)
    rows = await svc.db.fetchall(
        "SELECT g.chat_id FROM groups g JOIN group_settings s ON s.chat_id = g.chat_id "
        "WHERE g.is_active = 1 AND s.key = 'feat_azkar' AND s.value = '1' AND EXISTS ("
        "SELECT 1 FROM group_members m WHERE m.chat_id = g.chat_id AND m.last_seen > ?)",
        (int(time.time()) - 6 * 3600,))
    for r in rows:
        chat_id = r["chat_id"]
        if await botstate.is_quiet(svc, chat_id) or not await features.enabled(svc, chat_id, "azkar"):
            continue
        try:
            await context.bot.send_message(chat_id, f"{T.AZKAR_TITLE}\n{T.LINE}\n{random.choice(bank.AZKAR)}",
                                           disable_notification=True)
        except TelegramError:
            pass
        await asyncio.sleep(0.1)


# ── ردود زهو ────────────────────────────────────────
# الصيغة الموحدة ← اسم المجموعة
_TRIGGERS: dict[tuple[str, ...], str] = {}
for _gid, (_triggers, _) in bank.REPLY_GROUPS.items():
    for _t in _triggers:
        _TRIGGERS[tuple(normalize(_t).split())] = _gid
_MAX_TRIGGER_WORDS = max(len(k) for k in _TRIGGERS)
PREFIX_MAX_WORDS = 7                       # «السلام عليكم يا جماعة الخير» تنحسب، الجمل الطويلة لا
from zhoo.systems.zhoo_replies import gate as _source_limiter  # noqa: E402  رد وحد لكل شخص كل 10 ثواني
_chat_source_limiter = RateLimiter(12, 60)  # المجموعة كلها: 12 رد بالدقيقة (ضد الزحمة)
_last_reply: dict[tuple[int, str], int] = {}
_STRIP = " !.،,؟?~…🌸🤍❤️♥️✨🌹🌷💐😍🥰😊☺️🙏"


def match_reply_group(text: str) -> str | None:
    """يرجع اسم مجموعة الرد: الرسالة كلها صيغة معروفة، أو تبدأ بيها وهي قصيرة."""
    words = normalize(text.strip(_STRIP)).split()
    if not words:
        return None
    gid = _TRIGGERS.get(tuple(words))
    if gid is not None or len(words) > PREFIX_MAX_WORDS:
        return gid
    for n in range(min(len(words) - 1, _MAX_TRIGGER_WORDS), 0, -1):
        gid = _TRIGGERS.get(tuple(words[:n]))
        if gid is not None:
            return gid
    return None


def pick_reply(chat_id: int, gid: str, name: str) -> str:
    """رد عشوائي من المجموعة بدون تكرار آخر رد بنفس المجموعة."""
    replies = bank.REPLY_GROUPS[gid][1]
    choices = [i for i in range(len(replies)) if i != _last_reply.get((chat_id, gid))] or [0]
    idx = random.choice(choices)
    if len(_last_reply) > 20_000:
        _last_reply.clear()
    _last_reply[(chat_id, gid)] = idx
    return replies[idx].replace("{name}", esc(name or "")).replace("  ", " ")


async def maybe_source_reply(svc: Services, msg: Message, chat) -> bool:
    from zhoo.systems import features, zhoo_replies
    if not msg.text or len(msg.text) > 200 or not await features.enabled(svc, chat.id, "source_replies"):
        return False
    if await zhoo_replies.maybe_reply(svc, msg, chat):           # الردود المضافة تغلب الأساسية
        return True
    if len(msg.text) > 120:
        return False
    gid = match_reply_group(msg.text)
    if gid is None:
        return False
    user = msg.from_user
    uid = user.id if user else 0
    if not zhoo_replies.allow(chat.id, uid) or not _chat_source_limiter.hit(chat.id):
        return False
    name = (user.first_name if user else "")[:30]
    try:
        await msg.reply_text(pick_reply(chat.id, gid, name))
    except TelegramError:
        return False
    return True
