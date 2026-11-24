"""قفل السب المتقدم: كشف ذكي + عقوبات حسب الفئة وعدد المخالفات + قاموس دائم واستثناءات.

الأوضاع:
  smart  — 🧠 تدريجي ذكي: كل فئة (خفيف/متوسط/شديد) إلها خطة عقوبة، وتتصاعد مع تكرار المخالفة
  delete — مسح بس ⋅ mute/ban — مسح + كتم/حظر دائم من أول مرة ⋅ off — مطفي

- يفحص النص والتعليق على الوسائط، وحتى الرسائل المعدّلة.
- مشرفين المجموعة (أدمن فما فوق): تنمسح رسالتهم بس، بدون عقوبة.
- كل مخالفة تنحفظ بالسجل (30 يوم)، والعقوبة التدريجية تحسب مخالفات آخر 7 أيام.
- القواميس تنبني مرة وحدة وتنحفظ بالذاكرة، ونتائج الفحص كمان (ما نعيد فحص نفس النص).
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes

from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.durations import format_duration
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import RANK_NAMES, Rank
from zhoo.core.swear import (LEVELS, LIGHT, MEDIUM, SEVERE, Hit, Lexicon, category, detector, glue,
                              normalize_phrase, views)
from zhoo.core.targets import TargetError, resolve_target
from zhoo.repositories.swear_words import GLOBAL
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "locks"

MODES = ("off", "delete", "warn", "mute", "ban")
NO_PUNISH_RANK = Rank.ADMIN          # الأدمن فما فوق: مسح بدون عقوبة
SET_RANK = {"off": Rank.ADMIN, "delete": Rank.ADMIN, "warn": Rank.ADMIN,
            "mute": Rank.ADMIN, "ban": Rank.MANAGER}
VIEW_RANK = Rank.ADMIN
DICT_RANK = Rank.MANAGER
MAX_GROUP_WORDS = 1000
MAX_WORD_LEN = 60
MAX_PHRASE_WORDS = 6
# أوامر نصها لازم يحتوي الكلمة نفسها: ما نمسحها إذا رتبة الكاتب تكفي للأمر
DICT_COMMANDS = {"swear_add", "swear_remove", "swear_allow", "swear_unallow", "swear_test",
                 "dev_swear_add", "dev_swear_remove"}

_versions = itertools.count(1)


# ── الإعدادات: قفل واحد لكل شي ─────────────────────
# «قفل السب» يشمل الشتائم والإهانات والفشار والكفر. الوضع: مسح ⋅ إنذار ثم كتم ⋅ كتم ⋅ حظر
_LEGACY = {"smart": "warn"}   # مجموعات قديمة


async def get_mode(svc: Services, chat_id: int) -> str:
    raw = await svc.group_settings.get(chat_id, "swear_mode")
    raw = _LEGACY.get(raw, raw)
    if raw in ("", "off"):   # نسخة سابقة كان بيها قفل إهانات لوحده
        old = await svc.group_settings.get(chat_id, "insult_mode")
        raw = _LEGACY.get(old, old) if old not in ("", "off") else "off"
    return raw if raw in MODES else "off"


async def set_mode(svc: Services, chat_id: int, mode: str, by: int) -> None:
    old = await svc.group_settings.set(chat_id, "swear_mode", mode, by)
    if await svc.group_settings.get(chat_id, "insult_mode") not in ("", "off"):
        await svc.group_settings.set(chat_id, "insult_mode", "", by)
    await svc.audit.log("setting", chat_id=chat_id, actor_id=by,
                        details={"key": "swear_mode", "from": old, "to": mode})


def next_mode(mode: str) -> str:
    return MODES[(MODES.index(mode) + 1) % len(MODES)] if mode in MODES else "delete"


def step_label(step: tuple[str, int | None] | None) -> str:
    if step is None:
        return T.SWEAR_MODES["off"]
    kind, secs = step
    if kind == "delete":
        return T.SWEAR_STEP_DELETE
    if kind == "warn":
        return T.SWEAR_STEP_WARN
    return f"{mod.KIND_NAMES[kind]} {format_duration(secs) if secs else T.SWEAR_PERMANENT}"


# ── القواميس (بالذاكرة) ────────────────────────────
def _build(rows, source: str) -> Lexicon:
    lx = Lexicon(source)
    for r in rows:
        lx.add(r["word"], r["level"])
    lx.version = next(_versions)
    return lx


async def _migrate_legacy(svc: Services, chat_id: int) -> None:
    """الكلمات القديمة (مخزونة بالإعدادات) تنتقل مرة وحدة للجداول الجديدة."""
    custom = await svc.group_settings.get(chat_id, "swear_custom")
    allow = await svc.group_settings.get(chat_id, "swear_allow")
    if not custom and not allow:
        return
    for w in filter(None, custom.split(",")):
        await svc.swear_words.add(chat_id, w, w, MEDIUM, 0)
    for w in filter(None, allow.split(",")):
        await svc.swear_words.allow(chat_id, w, w, 0)
    await svc.group_settings.set(chat_id, "swear_custom", "", 0)
    await svc.group_settings.set(chat_id, "swear_allow", "", 0)


async def _global_layer(svc: Services) -> Lexicon:
    lx = svc.swear_cache.get(GLOBAL)
    if lx is None:
        lx = _build(await svc.swear_words.words(GLOBAL), "global")
        svc.swear_cache[GLOBAL] = lx
        detector.global_layer = lx   # فلتر الرسائل الطالعة يغطي كلمات المطور كمان
    return lx


async def _global_allowed(svc: Services) -> frozenset[str]:
    """كلمات أوقفها المطور من القاموس الأساسي (تنطبق على كل المجموعات)."""
    cached = svc.swear_cache.get("global_allow")
    if cached is None:
        rows = await svc.swear_words.allowed(GLOBAL)
        cached = frozenset({r["norm"] for r in rows} | {glue(r["norm"]) for r in rows})
        svc.swear_cache["global_allow"] = cached
    return cached


async def _group_layer(svc: Services, chat_id: int) -> tuple[Lexicon, frozenset[str]]:
    cached = svc.swear_cache.get(chat_id)
    if cached is None:
        await _migrate_legacy(svc, chat_id)
        lx = _build(await svc.swear_words.words(chat_id), "group")
        allowed: set[str] = set()
        for r in await svc.swear_words.allowed(chat_id):
            allowed.add(r["norm"])
            allowed.add(glue(r["norm"]))
        cached = (lx, frozenset(allowed) | await _global_allowed(svc))
        if len(svc.swear_cache) > 5000:
            svc.swear_cache.clear()
        svc.swear_cache[chat_id] = cached
    return cached


def invalidate(svc: Services, chat_id: int) -> None:
    if chat_id == GLOBAL:
        svc.swear_cache.clear()
    else:
        svc.swear_cache.pop(chat_id, None)


async def scan(svc: Services, chat_id: int, text: str, *, use_allowed: bool = True,
               levels: frozenset[int] | None = None) -> Hit | None:
    group, allowed = await _group_layer(svc, chat_id)
    glob = await _global_layer(svc)
    allowed = allowed if use_allowed else frozenset()
    return detector.scan(text, (group, glob), allowed, cache_key=(chat_id, group.version, glob.version),
                         levels=levels)


async def masked(svc: Services, chat_id: int, text: str) -> str:
    """النص بعد تغطية الكلمات المسيئة (قاموس المجموعة + العام + الأساسي) — حتى ما يطلع سب من زهو."""
    group, _ = await _group_layer(svc, chat_id)
    return detector.mask(text, (group, await _global_layer(svc)))


def _cover(word: str) -> str:
    """كلمة/عبارة نعرف إنها مسيئة (من القاموس): نغطيها كلها بدون فحص."""
    from zhoo.core.swear import _mask_word
    return " ".join(_mask_word(w) if len(w) > 1 else w for w in word.split())


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
    hit = await scan(svc, chat.id, text)
    reply = msg.reply_to_message
    at_zhoo = reply is not None and reply.from_user is not None and reply.from_user.id == context.bot.id
    if hit is None and reply is not None and chat.id not in svc.games:
        hit = detector.reply_insult(text)                  # رد على شخص بإهانة مفردة («قذر»)
        if hit is not None:
            _, allowed = await _group_layer(svc, chat.id)
            if hit.entry.key in allowed or glue(hit.entry.key) in allowed:
                hit = None
    if hit is None:
        return False

    level = hit.entry.level
    plan = mod.SWEAR_FIXED_MODES[mode]

    rank = await svc.perms.rank_of(context.bot, chat.id, user.id)
    parsed = registry.parse(msg.text or "") if msg.text else None
    if parsed and parsed.command.key in DICT_COMMANDS and rank >= parsed.command.min_rank:
        return False

    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False

    # نقرر العقوبة أولاً، وبعدين المسح والكتم/الحظر ينطلقون سوا بنفس اللحظة
    strike = await svc.swear_logs.strikes(chat.id, user.id, mod.SWEAR_WINDOW) + 1
    kind, secs = mod.swear_step(plan, strike)
    if rank >= NO_PUNISH_RANK or await botstate.is_quiet(svc, chat.id):
        kind, secs = "delete", None   # المشرفين، أو زهو موقوفة: مسح بس
    if kind in ("mute", "ban") and not rights.can_restrict_members:
        kind, secs = "delete", None
    until = int(time.time()) + secs if secs else None
    jobs = [msg.delete()]
    if kind in ("mute", "ban"):
        jobs.append(mod.apply(context.bot, chat.id, user.id, kind, until))
    results = await asyncio.gather(*jobs, return_exceptions=True)
    if isinstance(results[0], TelegramError) and len(results) == 1:
        return False   # ما انمسحت وماكو عقوبة
    if len(results) > 1 and isinstance(results[1], Exception):
        log.info("فشلت عقوبة السب: %s", results[1])
        kind, secs, until = "delete", None, None

    who = mention(user.id, user.full_name)

    await svc.swear_logs.add(chat.id, user.id, hit.found, text, kind, level, secs)
    await svc.audit.log(f"swear_{kind}", chat_id=chat.id, actor_id=context.bot.id, target_id=user.id,
                        details={"level": level, "strike": strike})

    from zhoo.systems.protect import send_notice  # تجنب الاستيراد الدائري
    reason = T.SWEAR_REASONS[category(hit.entry)]
    if at_zhoo:   # أحد غلط على زهو نفسها
        import random
        await send_notice(context, chat.id, random.choice(T.ZHOO_INSULTED).format(mention=who), ttl=60)
    if kind == "delete":
        if svc.notice_limiter.hit((chat.id, user.id)):
            await send_notice(context, chat.id, T.SWEAR_NOTICE.format(mention=who, reason=reason), ttl=15)
        return True
    if kind == "warn":
        nxt = step_label(mod.swear_step(plan, strike + 1))
        await send_notice(context, chat.id, T.SWEAR_WARNED.format(mention=who, n=strike, next=nxt, reason=reason),
                          ttl=60)
        return True

    await svc.punishments.add(chat.id, user.id, kind, context.bot.id, T.SWEAR_REASON_PLAIN[category(hit.entry)],
                              until)
    head, emoji = T.PUNISH_TITLES[kind]
    code = "m" if kind == "mute" else "b"
    undo = T.BTN_UNDO_MUTE if kind == "mute" else T.BTN_UNDO_BAN
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(undo, callback_data=f"p:{code}:{user.id}")]])
    await send_notice(context, chat.id, T.SWEAR_PUNISHED.format(
        head=head, emoji=emoji, mention=who, reason=reason, n=strike,
        duration=format_duration(secs) if secs else T.SWEAR_PERMANENT), ttl=0, reply_markup=kb)
    return True


async def on_edited(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """السب بالتعديل ما يفلت."""
    msg, chat, user = update.edited_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None or user.is_bot or msg.sender_chat is not None:
        return
    await check(context, get_services(context), msg, chat, user)


# ── أوامر القفل ─────────────────────────────────────
def _mode_words() -> dict[str, str]:
    return {normalize(k): v for k, v in T.SWEAR_MODE_WORDS.items()}


def _parse_lock_rest(rest: str) -> str | None:
    """«بالكتم» ← mute. بدون كلمة = كتم فوري. (كلمات مثل 18 تنتجاهل)"""
    mode = "mute"
    words = _mode_words()
    for word in rest.split():
        w = normalize(word)
        if w in words:
            mode = words[w]
        elif w not in T.SWEAR_IGNORE_WORDS:
            return None
    return mode


async def _cmd_set(cx: CommandContext, mode: str) -> None:
    svc = cx.services
    if cx.rank < SET_RANK[mode]:
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
    lines = [T.SWEAR_MODE_SET.format(mode=T.SWEAR_MODES[mode], hint=T.SWEAR_MODE_HINTS[mode], actor=actor),
             T.SWEAR_MODES_HELP]
    rights = await svc.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_delete_messages:
        lines.append(T.SWEAR_NEED_DELETE)
    await cx.reply("\n".join(lines))


async def _lock(cx: CommandContext) -> None:
    await _cmd_set(cx, _parse_lock_rest(cx.raw_args) or "mute")


async def _unlock(cx: CommandContext) -> None:
    await _cmd_set(cx, "off")


registry.command("swear_lock", ("قفل السب", "قفل الشتائم", "قفل الفشار", "قفل الاهانات", "قفل الإهانات",
                                "قفل الكفر", "قفل الكلام البذيء"), section=S, min_rank=SET_RANK["delete"], order=9,
                 usage="بالمسح / بالانذار / بالكتم / بالحظر",
                 accept=lambda rest: _parse_lock_rest(rest) is not None,
                 description="قفل واحد للشتائم والإهانات والفشار والكفر")(_lock)
registry.command("swear_unlock", ("فتح السب", "فتح الشتائم", "فتح الفشار", "فتح الاهانات", "فتح الإهانات",
                                  "فتح الكفر"), section=S, min_rank=SET_RANK["off"], order=10,
                 accept=lambda rest: all(normalize(w) in T.SWEAR_IGNORE_WORDS for w in rest.split()),
                 description="يفتح قفل السب")(_unlock)


# ── سجل المخالفات ──────────────────────────────────
async def _optional_target(cx: CommandContext, example: str):
    if cx.message.reply_to_message is None and not cx.args:
        return None, True
    try:
        return await resolve_target(cx), True
    except TargetError as e:
        await reply_target_error(cx, e, example)
        return None, False


@registry.command("swear_log", ("السب المحذوف", "سجل السب", "مخالفات السب"), section=S, min_rank=VIEW_RANK,
                  args="target", usage="اختياري: بالرد/اليوزر",
                  description="سجل المخالفات: منو سب، شنو كال، والإجراء", order=15)
async def cmd_swear_log(cx: CommandContext) -> None:
    target, ok = await _optional_target(cx, "مخالفات السب @username")
    if not ok:
        return
    user_id = target.user_id if target else None
    rows = await cx.services.swear_logs.recent(cx.chat.id, user_id, 10)
    head = T.SWEAR_LOG_HEADER
    if target is not None:
        n = await cx.services.swear_logs.strikes(cx.chat.id, target.user_id, mod.SWEAR_WINDOW)
        head += "\n" + T.SWEAR_LOG_STRIKES.format(mention=mention(target.user_id, target.name), n=n)
    if not rows:
        await cx.reply(f"{head}\n{T.SWEAR_LOG_EMPTY}")
        return
    items = []
    for r in rows:
        name = " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])
        text = r["text"] if len(r["text"]) <= 300 else r["text"][:300] + "…"
        action = T.SWEAR_ACTIONS.get(r["action"], r["action"])
        if r["action"] in ("mute", "ban"):
            action += f" ({format_duration(r['duration']) if r['duration'] else T.SWEAR_PERMANENT})"
        items.append(T.SWEAR_LOG_ITEM.format(
            mention=mention(r["user_id"], name), action=action, level=T.SWEAR_LEVELS.get(r["level"], ""),
            word=esc(_cover(r["word"])), text=esc(await masked(cx.services, cx.chat.id, text)),
            when=time.strftime("%m-%d %H:%M", time.gmtime(r["created_at"]))))
    await cx.reply(f"{head}\n" + "\n\n".join(items) + f"\n{T.LINE}\n{T.SWEAR_LOG_FOOTER}")


@registry.command("swear_log_clear", ("مسح سجل السب", "مسح مخالفات السب"), section=S, min_rank=DICT_RANK,
                  args="target", usage="اختياري: بالرد/اليوزر لعضو واحد",
                  description="يمسح سجل المخالفات (كله أو لعضو) ويصفر عداده", order=16)
async def cmd_swear_log_clear(cx: CommandContext) -> None:
    target, ok = await _optional_target(cx, "مسح مخالفات السب @username")
    if not ok:
        return
    await cx.services.swear_logs.clear(cx.chat.id, target.user_id if target else None)
    await cx.services.audit.log("swear_log_clear", chat_id=cx.chat.id, actor_id=cx.user.id,
                                target_id=target.user_id if target else None)
    if target is not None:
        await cx.reply(T.SWEAR_LOG_USER_CLEARED.format(mention=mention(target.user_id, target.name)))
    else:
        await cx.reply(T.SWEAR_LOG_CLEARED)


# ── القاموس ─────────────────────────────────────────
def _parse_options(cx: CommandContext, *, levels: bool) -> tuple[str, int, bool]:
    """يقرا الخيارات من بداية النص: [عام] [خفيف|متوسط|شديد] ثم الكلمة."""
    words = cx.raw_args.split()
    level, is_global = MEDIUM, False
    level_words = {normalize(k): v for k, v in T.SWEAR_LEVEL_WORDS.items()}
    for _ in range(2):
        if len(words) < 2:
            break
        first = normalize(words[0])
        if first == normalize(T.SWEAR_GLOBAL_WORD) and not is_global:
            is_global = True
        elif levels and first in level_words:
            level = level_words[first]
        else:
            break
        words = words[1:]
    return " ".join(words), level, is_global


def _valid(text: str) -> str | None:
    norm = normalize_phrase(text)
    glued = glue(norm)
    if not 2 <= len(glued) <= MAX_WORD_LEN or len(norm.split()) > MAX_PHRASE_WORDS:
        return None
    return norm


@registry.command("swear_add", ("اضافه سب", "إضافة سب", "اضف سب"), section=S, min_rank=DICT_RANK, args="text",
                  usage="[خفيف/متوسط/شديد] الكلمة أو العبارة",
                  description="يضيف كلمة أو عبارة لقاموس المجموعة (بعد فحصها ضد الكلمات السليمة)", order=17)
async def cmd_swear_add(cx: CommandContext) -> None:
    svc = cx.services
    word, level, is_global = _parse_options(cx, levels=True)
    if is_global and cx.rank < Rank.DEVELOPER:
        await cx.reply(T.SWEAR_GLOBAL_DEV_ONLY)
        return
    norm = _valid(word)
    if norm is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    base = detector.base.entries.get(norm)
    if base is not None and base.level == level:
        await cx.reply(T.SWEAR_WORD_IN_BASE.format(level=T.SWEAR_LEVELS[base.level]))
        return
    bad = detector.collisions(word, level)
    if bad:
        await cx.reply(T.SWEAR_WORD_COLLIDES.format(words="، ".join(f"<code>{esc(b)}</code>" for b in bad[:5])))
        return
    chat_id = GLOBAL if is_global else cx.chat.id
    if await svc.swear_words.count(chat_id) >= MAX_GROUP_WORDS and not is_global:
        await cx.reply(T.SWEAR_WORDS_LIMIT.format(n=MAX_GROUP_WORDS))
        return
    await svc.swear_words.add(chat_id, word, norm, level, cx.user.id)
    if not is_global:
        await svc.swear_words.unallow(chat_id, norm)
        await svc.swear_words.unallow(chat_id, glue(norm))
    invalidate(svc, chat_id)
    await svc.audit.log("swear_word_add", chat_id=cx.chat.id, actor_id=cx.user.id,
                        details={"level": level, "global": is_global})
    await cx.reply(T.SWEAR_WORD_ADDED.format(
        word=esc(_cover(word)), level=T.SWEAR_LEVELS[level], kind=T.SWEAR_KINDS[Lexicon.auto_kind(norm)],
        where=T.SWEAR_WHERE_GLOBAL if is_global else T.SWEAR_WHERE_GROUP))


@registry.command("swear_remove", ("حذف سب",), section=S, min_rank=DICT_RANK, args="text",
                  usage="الكلمة أو العبارة", description="يشيل كلمة من قاموس المجموعة", order=18)
async def cmd_swear_remove(cx: CommandContext) -> None:
    svc = cx.services
    word, _, is_global = _parse_options(cx, levels=False)
    if is_global and cx.rank < Rank.DEVELOPER:
        await cx.reply(T.SWEAR_GLOBAL_DEV_ONLY)
        return
    norm = _valid(word)
    if norm is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    chat_id = GLOBAL if is_global else cx.chat.id
    if await svc.swear_words.remove(chat_id, norm):
        invalidate(svc, chat_id)
        await svc.audit.log("swear_word_remove", chat_id=cx.chat.id, actor_id=cx.user.id,
                            details={"global": is_global})
        await cx.reply(T.SWEAR_WORD_REMOVED.format(word=esc(_cover(word))))
    elif norm in detector.base.entries or detector.find(word):
        await cx.reply(T.SWEAR_WORD_BASE_REMOVE)
    else:
        await cx.reply(T.SWEAR_WORD_NOT_FOUND)


@registry.command("swear_allow", ("سماح كلمه", "سماح كلمة"), section=S, min_rank=DICT_RANK, args="text",
                  usage="الكلمة", description="استثناء: يسمح بكلمة محظورة بهاي المجموعة", order=19)
async def cmd_swear_allow(cx: CommandContext) -> None:
    svc = cx.services
    word = cx.raw_args.strip()
    if _valid(word) is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    hit = await scan(svc, cx.chat.id, word, use_allowed=False)
    if hit is None:
        await cx.reply(T.SWEAR_WORD_NOT_SWEAR)
        return
    await svc.swear_words.allow(cx.chat.id, word, hit.entry.key, cx.user.id)
    if hit.entry.source == "group":
        await svc.swear_words.remove(cx.chat.id, hit.entry.key)
    invalidate(svc, cx.chat.id)
    await svc.audit.log("swear_word_allow", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.SWEAR_WORD_ALLOWED.format(word=esc(_cover(word))))


@registry.command("swear_unallow", ("الغاء سماح", "إلغاء سماح", "الغاء السماح"), section=S, min_rank=DICT_RANK,
                  args="text", usage="الكلمة", description="يرجع كلمة مستثناة محظورة", order=20)
async def cmd_swear_unallow(cx: CommandContext) -> None:
    svc = cx.services
    word = cx.raw_args.strip()
    norm = _valid(word)
    if norm is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    keys = {norm, glue(norm)}
    hit = await scan(svc, cx.chat.id, word, use_allowed=False)
    if hit is not None:
        keys.add(hit.entry.key)
    removed = False
    for k in keys:
        removed = await svc.swear_words.unallow(cx.chat.id, k) or removed
    if not removed:
        await cx.reply(T.SWEAR_ALLOW_NOT_FOUND)
        return
    invalidate(svc, cx.chat.id)
    await svc.audit.log("swear_word_unallow", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.SWEAR_UNALLOWED.format(word=esc(_cover(word))))


@registry.command("swear_test", ("فحص سب", "اختبار سب", "فحص كلمه", "فحص كلمة"), section=S, min_rank=VIEW_RANK,
                  args="text", usage="النص", description="يختبر نص: محظور لو لا، وليش، وشنو الإجراء", order=21)
async def cmd_swear_test(cx: CommandContext) -> None:
    svc = cx.services
    text = cx.raw_args.strip()
    if not text:
        await cx.reply(T.SWEAR_TEST_NEED)
        return
    v = views(text)
    norm = " ".join(t.norm for t in v[0]) if v else ""
    out = [T.SWEAR_TEST_HEADER, T.SWEAR_TEST_NORM.format(norm=esc(await masked(svc, cx.chat.id, norm) or "—"))]
    hit = await scan(svc, cx.chat.id, text)
    if hit is None:
        raw = await scan(svc, cx.chat.id, text, use_allowed=False)
        out.append(T.SWEAR_TEST_ALLOWED if raw is not None else T.SWEAR_TEST_CLEAN)
        await cx.reply("\n".join(out))
        return
    mode = await get_mode(svc, cx.chat.id)
    plan = mod.SWEAR_FIXED_MODES.get(mode, ())
    action = T.SWEAR_MODES["off"] if mode == "off" else step_label(mod.swear_step(plan, 1))
    out.append(T.SWEAR_TEST_BLOCKED.format(
        scope_mode=T.SWEAR_MODES[mode],
        found=esc(_cover(hit.found)), key=esc(_cover(hit.entry.key)), level=T.SWEAR_LEVELS[hit.entry.level],
        kind=T.SWEAR_KINDS[hit.entry.kind], source=T.SWEAR_SOURCES[hit.entry.source], action=action))
    await cx.reply("\n".join(out))


@registry.command("swear_words", ("قاموس السب",), section=S, min_rank=DICT_RANK,
                  description="كلمات المجموعة والاستثناءات وحجم القاموس", order=22)
async def cmd_swear_words(cx: CommandContext) -> None:
    svc = cx.services
    await _group_layer(svc, cx.chat.id)  # ينقل الكلمات القديمة إذا موجودة
    per_level = {lv: 0 for lv in LEVELS}
    for e in detector.base.entries.values():
        per_level[e.level] += 1
    detail = " ⋅ ".join(f"{T.SWEAR_LEVELS[lv]} {n}" for lv, n in sorted(per_level.items()))
    out = [T.SWEAR_WORDS_HEADER, T.SWEAR_WORDS_BASE.format(n=len(detector.base), detail=detail)]
    n_global = await svc.swear_words.count(GLOBAL)
    if n_global:
        out.append(T.SWEAR_WORDS_GLOBAL.format(n=n_global))
    rows = await svc.swear_words.words(cx.chat.id)
    allowed = await svc.swear_words.allowed(cx.chat.id)
    out.append(T.SWEAR_WORDS_GROUP.format(n=len(rows)))
    if not rows and not allowed:
        out.append(T.SWEAR_WORDS_EMPTY)
    for r in rows[:40]:
        out.append(f"▫️ <tg-spoiler>{esc(_cover(r['word']))}</tg-spoiler> ⋅ {T.SWEAR_LEVELS.get(r['level'], '')}")
    if len(rows) > 40:
        out.append(T.SWEAR_WORDS_MORE.format(n=len(rows) - 40))
    if allowed:
        out.append(T.SWEAR_ALLOWED_LABEL)
        out += [f"▫️ <tg-spoiler>{esc(_cover(r['word']))}</tg-spoiler>" for r in allowed[:40]]
    await cx.reply("\n".join(out))



# ── أوامر المطور: قاموس عام لكل المجموعات (من المجموعة أو من الخاص) ──
@registry.command("dev_swear_add", ("اضف كلمة سب جديدة", "اضف كلمه سب جديده", "اضف كلمة سب", "اضف كلمه سب"),
                  section="dev", min_rank=Rank.DEVELOPER, args="text", where="any", order=60,
                  usage="[خفيف/متوسط/شديد] الكلمة", description="كلمة سب جديدة تنحظر فوراً بكل المجموعات")
async def cmd_dev_swear_add(cx: CommandContext) -> None:
    svc = cx.services
    word, level, _ = _parse_options(cx, levels=True)
    norm = _valid(word)
    if norm is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    if await svc.swear_words.unallow(GLOBAL, norm) | await svc.swear_words.unallow(GLOBAL, glue(norm)):
        invalidate(svc, GLOBAL)   # كانت موقوفة: ترجع تشتغل
        await svc.audit.log("dev_swear_enable", actor_id=cx.user.id)
        await cx.reply(T.DEV_SWEAR_REENABLED)
        return
    if norm in detector.base.entries:   # موجودة بالقاموس الأساسي وشغّالة
        await cx.reply(T.SWEAR_WORD_IN_BASE.format(level=T.SWEAR_LEVELS[detector.base.entries[norm].level]))
        return
    bad = detector.collisions(word, level)
    if bad:
        await cx.reply(T.SWEAR_WORD_COLLIDES.format(words="، ".join(f"<code>{esc(b)}</code>" for b in bad[:5])))
        return
    await svc.swear_words.add(GLOBAL, word, norm, level, cx.user.id)
    invalidate(svc, GLOBAL)
    await svc.audit.log("dev_swear_add", actor_id=cx.user.id, details={"level": level})
    await cx.reply(T.DEV_SWEAR_ADDED.format(level=T.SWEAR_LEVELS[level],
                                            kind=T.SWEAR_KINDS[Lexicon.auto_kind(norm)]))


@registry.command("dev_swear_remove", ("ازل كلمة سب قديمة", "ازل كلمه سب قديمه", "ازل كلمة سب", "ازل كلمه سب",
                                      "ازالة كلمة سب"),
                  section="dev", min_rank=Rank.DEVELOPER, args="text", where="any", order=61,
                  usage="الكلمة", description="يوقف كلمة سب كانت تنحظر (بكل المجموعات)")
async def cmd_dev_swear_remove(cx: CommandContext) -> None:
    svc = cx.services
    word = cx.raw_args.strip()
    norm = _valid(word)
    if norm is None:
        await cx.reply(T.SWEAR_WORD_BAD)
        return
    if await svc.swear_words.remove(GLOBAL, norm):
        invalidate(svc, GLOBAL)
        await svc.audit.log("dev_swear_remove", actor_id=cx.user.id)
        await cx.reply(T.DEV_SWEAR_REMOVED)
        return
    hit = await scan(svc, cx.chat.id, word, use_allowed=False) if cx.chat.id < 0 else None
    hit = hit or detector.scan(word, (await _global_layer(svc),))
    if hit is None:
        await cx.reply(T.SWEAR_WORD_NOT_SWEAR)
        return
    await svc.swear_words.allow(GLOBAL, word, hit.entry.key, cx.user.id)
    invalidate(svc, GLOBAL)
    await svc.audit.log("dev_swear_disable", actor_id=cx.user.id)
    await cx.reply(T.DEV_SWEAR_DISABLED)
