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
from zhoo.core.swear import LEVELS, LIGHT, MEDIUM, SEVERE, Hit, Lexicon, detector, glue, normalize_phrase, views
from zhoo.core.targets import TargetError, resolve_target
from zhoo.repositories.swear_words import GLOBAL
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "locks"

MODES = ("off", "smart", "delete", "mute", "ban")
NO_PUNISH_RANK = Rank.ADMIN          # الأدمن فما فوق: مسح بدون عقوبة
SET_RANK = {"off": Rank.ADMIN, "smart": Rank.ADMIN, "delete": Rank.ADMIN,
            "mute": Rank.MANAGER, "ban": Rank.MANAGER}
VIEW_RANK = Rank.ADMIN
DICT_RANK = Rank.MANAGER
MAX_GROUP_WORDS = 1000
MAX_WORD_LEN = 60
MAX_PHRASE_WORDS = 6
# أوامر نصها لازم يحتوي الكلمة نفسها: ما نمسحها إذا رتبة الكاتب تكفي للأمر
DICT_COMMANDS = {"swear_add", "swear_remove", "swear_allow", "swear_unallow", "swear_test"}

_versions = itertools.count(1)


# ── الإعدادات: نوعين قفل مستقلين ───────────────────
# vulgar = الفشار +18 والمسبات (الفئتين المتوسطة والشديدة) ⋅ insult = الإهانات (الفئة الخفيفة)
SCOPES = ("vulgar", "insult")
SCOPE_KEY = {"vulgar": "swear_mode", "insult": "insult_mode"}
SCOPE_LEVELS = {"vulgar": frozenset({MEDIUM, SEVERE}), "insult": frozenset({LIGHT})}


def scope_of(level: int) -> str:
    return "insult" if level == LIGHT else "vulgar"


async def get_mode(svc: Services, chat_id: int, scope: str = "vulgar") -> str:
    raw = await svc.group_settings.get(chat_id, SCOPE_KEY[scope])
    if scope == "insult" and raw == "":
        raw = await svc.group_settings.get(chat_id, "swear_mode")  # مجموعات قديمة: الإهانات تتبع قفل السب
    return raw if raw in MODES else "off"


async def get_modes(svc: Services, chat_id: int) -> dict[str, str]:
    return {sc: await get_mode(svc, chat_id, sc) for sc in SCOPES}


async def set_mode(svc: Services, chat_id: int, mode: str, by: int, scope: str = "all") -> None:
    """scope: vulgar | insult | all (الاثنين)."""
    if await svc.group_settings.get(chat_id, "insult_mode") == "":
        # نثبت قيمة الإهانات الموروثة قبل لا يتغير قفل الفشار لوحده
        await svc.group_settings.set(chat_id, "insult_mode", await get_mode(svc, chat_id, "insult"), by)
    for sc in (SCOPES if scope == "all" else (scope,)):
        old = await svc.group_settings.set(chat_id, SCOPE_KEY[sc], mode, by)
        await svc.audit.log("setting", chat_id=chat_id, actor_id=by,
                            details={"key": SCOPE_KEY[sc], "from": old, "to": mode})


async def active_scopes(svc: Services, chat_id: int) -> int:
    return sum(1 for m in (await get_modes(svc, chat_id)).values() if m != "off")


async def get_plan_key(svc: Services, chat_id: int, level: int) -> str:
    key = await svc.group_settings.get(chat_id, f"swear_l{level}")
    return key if key in mod.SWEAR_PLANS else "gradual"


async def plan_for(svc: Services, chat_id: int, level: int, mode: str):
    if mode in mod.SWEAR_FIXED_MODES:
        return mod.SWEAR_FIXED_MODES[mode]
    return mod.SWEAR_PLANS[await get_plan_key(svc, chat_id, level)]


def next_mode(mode: str) -> str:
    return MODES[(MODES.index(mode) + 1) % len(MODES)] if mode in MODES else "smart"


def step_label(step: tuple[str, int | None] | None) -> str:
    if step is None:
        return T.SWEAR_PLANS["off"]
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
    return lx


async def _group_layer(svc: Services, chat_id: int) -> tuple[Lexicon, frozenset[str]]:
    cached = svc.swear_cache.get(chat_id)
    if cached is None:
        await _migrate_legacy(svc, chat_id)
        lx = _build(await svc.swear_words.words(chat_id), "group")
        allowed: set[str] = set()
        for r in await svc.swear_words.allowed(chat_id):
            allowed.add(r["norm"])
            allowed.add(glue(r["norm"]))
        cached = (lx, frozenset(allowed))
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
    modes = await get_modes(svc, chat.id)
    levels = frozenset().union(*(SCOPE_LEVELS[sc] for sc, m in modes.items() if m != "off"))
    if not levels:
        return False
    text = msg.text or msg.caption
    if not text:
        return False
    hit = await scan(svc, chat.id, text, levels=levels)   # نفحص بس الأنواع المقفولة
    reply = msg.reply_to_message
    at_zhoo = reply is not None and reply.from_user is not None and reply.from_user.id == context.bot.id
    if hit is None and LIGHT in levels and reply is not None and chat.id not in svc.games:
        hit = detector.reply_insult(text)                  # رد على شخص بإهانة مفردة («قذر»)
        if hit is not None:
            _, allowed = await _group_layer(svc, chat.id)
            if hit.entry.key in allowed or glue(hit.entry.key) in allowed:
                hit = None
    if hit is None:
        return False

    level = hit.entry.level
    plan = await plan_for(svc, chat.id, level, modes[scope_of(level)])
    if not plan:
        return False  # هاي الفئة على «تجاهل»

    rank = await svc.perms.rank_of(context.bot, chat.id, user.id)
    parsed = registry.parse(msg.text or "") if msg.text else None
    if parsed and parsed.command.key in DICT_COMMANDS and rank >= parsed.command.min_rank:
        return False

    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False
    try:
        await msg.delete()
    except TelegramError:
        return False

    strike = await svc.swear_logs.strikes(chat.id, user.id, mod.SWEAR_WINDOW) + 1
    kind, secs = mod.swear_step(plan, strike)
    if rank >= NO_PUNISH_RANK or await botstate.is_quiet(svc, chat.id):
        kind, secs = "delete", None   # المشرفين، أو زهو موقوفة: مسح بس
    if kind in ("mute", "ban") and not rights.can_restrict_members:
        kind, secs = "delete", None

    who = mention(user.id, user.full_name)
    until = int(time.time()) + secs if secs else None
    if kind in ("mute", "ban"):
        try:
            await mod.apply(context.bot, chat.id, user.id, kind, until)
        except (BadRequest, Forbidden) as e:
            log.info("فشلت عقوبة السب: %s", e)
            kind, secs, until = "delete", None, None

    await svc.swear_logs.add(chat.id, user.id, hit.found, text, kind, level, secs)
    await svc.audit.log(f"swear_{kind}", chat_id=chat.id, actor_id=context.bot.id, target_id=user.id,
                        details={"level": level, "strike": strike})

    from zhoo.systems.protect import send_notice  # تجنب الاستيراد الدائري
    if at_zhoo:   # أحد غلط على زهو نفسها
        import random
        await send_notice(context, chat.id, random.choice(T.ZHOO_INSULTED).format(mention=who), ttl=60)
    if kind == "delete":
        if svc.notice_limiter.hit((chat.id, user.id)):
            await send_notice(context, chat.id, T.SWEAR_NOTICE.format(mention=who), ttl=15)
        return True
    if kind == "warn":
        nxt = step_label(mod.swear_step(plan, strike + 1))
        await send_notice(context, chat.id, T.SWEAR_WARNED.format(mention=who, n=strike, next=nxt), ttl=60)
        return True

    await svc.punishments.add(chat.id, user.id, kind, context.bot.id, T.SWEAR_REASON, until)
    head, emoji = T.PUNISH_TITLES[kind]
    code = "m" if kind == "mute" else "b"
    undo = T.BTN_UNDO_MUTE if kind == "mute" else T.BTN_UNDO_BAN
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(undo, callback_data=f"p:{code}:{user.id}")]])
    await send_notice(context, chat.id, T.SWEAR_PUNISHED.format(
        head=head, emoji=emoji, mention=who, level=T.SWEAR_LEVELS[level], n=strike,
        duration=format_duration(secs) if secs else T.SWEAR_PERMANENT), ttl=0, reply_markup=kb)
    return True


async def on_edited(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """السب بالتعديل ما يفلت."""
    msg, chat, user = update.edited_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None or user.is_bot or msg.sender_chat is not None:
        return
    await check(context, get_services(context), msg, chat, user)


# ── أوامر القفل ─────────────────────────────────────
def _parse_lock_rest(rest: str, scope: str) -> tuple[str, str] | None:
    """باقي الأمر: [18] [بالمسح|بالكتم|بالحظر|التدريجي] ← (النوع، الوضع)."""
    mode = "smart"
    seen_mode = False
    for word in rest.split():
        w = normalize(word)
        if w in T.SWEAR_SCOPE_WORDS and scope == "all":
            scope = T.SWEAR_SCOPE_WORDS[w]
        elif w in {normalize(k): v for k, v in T.SWEAR_MODE_WORDS.items()} and not seen_mode:
            mode = {normalize(k): v for k, v in T.SWEAR_MODE_WORDS.items()}[w]
            seen_mode = True
        else:
            return None
    return scope, mode


def _parse_unlock_rest(rest: str, scope: str) -> str | None:
    words = [normalize(w) for w in rest.split()]
    if not words:
        return scope
    if scope == "all" and len(words) == 1 and words[0] in T.SWEAR_SCOPE_WORDS:
        return T.SWEAR_SCOPE_WORDS[words[0]]
    return None


async def _cmd_set(cx: CommandContext, scope: str, mode: str) -> None:
    svc = cx.services
    if cx.rank < SET_RANK[mode]:
        await cx.reply(T.NO_PERMISSION.format(rank=RANK_NAMES[SET_RANK[mode]]))
        return
    modes = await get_modes(svc, cx.chat.id)
    targets = SCOPES if scope == "all" else (scope,)
    if all(modes[sc] == mode for sc in targets):
        await cx.reply(T.SWEAR_MODE_SAME.format(scope=T.SWEAR_SCOPES[scope], mode=T.SWEAR_MODES[mode]))
        return
    await set_mode(svc, cx.chat.id, mode, cx.user.id, scope)
    actor = mention(cx.user.id, cx.user.full_name)
    lines = []
    if mode == "off":
        lines.append(T.SWEAR_MODE_OFF.format(head=T.SWEAR_UNLOCK_TITLES[scope], actor=actor))
    else:
        lines.append(T.SWEAR_MODE_SET.format(head=T.SWEAR_LOCK_TITLES[scope], covers=T.SWEAR_SCOPE_COVERS[scope],
                                             mode=T.SWEAR_MODES[mode], actor=actor))
        if mode == "smart":
            lines.append(T.SWEAR_MODE_SMART_HINT)
    if scope != "all":  # نوضح حالة النوع الثاني
        other = "insult" if scope == "vulgar" else "vulgar"
        lines.append(T.SWEAR_OTHER_STATE.format(scope=T.SWEAR_SCOPES[other], mode=T.SWEAR_MODES[modes[other]]))
    if mode != "off":
        rights = await svc.perms.bot_rights(cx.bot, cx.chat.id)
        if rights is None or not rights.can_delete_messages:
            lines.append(T.SWEAR_NEED_DELETE)
    await cx.reply("\n".join(lines))


def _lock_command(key: str, names: tuple[str, ...], scope: str, description: str, order: int) -> None:
    async def handler(cx: CommandContext) -> None:
        sc, mode = _parse_lock_rest(cx.raw_args, scope)
        await _cmd_set(cx, sc, mode)

    registry.command(key, names, section=S, min_rank=SET_RANK["smart"], order=order,
                     usage="اختياري: بالمسح / بالكتم / بالحظر", description=description,
                     accept=lambda rest: _parse_lock_rest(rest, scope) is not None)(handler)


def _unlock_command(key: str, names: tuple[str, ...], scope: str, description: str, order: int) -> None:
    async def handler(cx: CommandContext) -> None:
        await _cmd_set(cx, _parse_unlock_rest(cx.raw_args, scope), "off")

    registry.command(key, names, section=S, min_rank=SET_RANK["off"], order=order, description=description,
                     accept=lambda rest: _parse_unlock_rest(rest, scope) is not None)(handler)


_lock_command("swear_lock", ("قفل السب", "قفل الشتائم"), "all",
              "يقفل النوعين (الفشار + الإهانات) — تدريجي ذكي، أو: بالمسح/بالكتم/بالحظر", 9)
_lock_command("vulgar_lock", ("قفل الفشار", "قفل الفشائر", "قفل الكلام البذيء"), "vulgar",
              "يقفل الفشار +18 والمسبات بس", 10)
_lock_command("insult_lock", ("قفل الاهانات", "قفل الإهانات", "قفل الاهانه", "قفل الإهانة"), "insult",
              "يقفل الإهانات بس (يا حمار، يا حقير...)", 11)
_unlock_command("swear_unlock", ("فتح السب", "فتح الشتائم"), "all", "يفتح النوعين", 12)
_unlock_command("vulgar_unlock", ("فتح الفشار", "فتح الفشائر", "فتح الكلام البذيء"), "vulgar",
                "يفتح الفشار بس", 13)
_unlock_command("insult_unlock", ("فتح الاهانات", "فتح الإهانات", "فتح الاهانه", "فتح الإهانة"), "insult",
                "يفتح الإهانات بس", 13)


# ── لوحة العقوبات ──────────────────────────────────
async def policy_view(svc: Services, chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    modes = await get_modes(svc, chat_id)
    lines, rows = [], []
    for scope, levels in (("vulgar", (SEVERE, MEDIUM)), ("insult", (LIGHT,))):
        mode = modes[scope]
        lines.append(T.SWEAR_POLICY_SCOPE.format(scope=T.SWEAR_SCOPES[scope], mode=T.SWEAR_MODES[mode]))
        rows.append([InlineKeyboardButton(T.SWEAR_BTN_SCOPE[scope].format(mode=T.SWEAR_MODES[mode]),
                                          callback_data=f"sw:m:{scope[0]}")])
        for level in levels:
            key = await get_plan_key(svc, chat_id, level)
            if mode == "smart":
                lines.append(T.SWEAR_POLICY_LEVEL.format(level=T.SWEAR_LEVELS[level], plan=T.SWEAR_PLANS[key],
                                                         hint=T.SWEAR_PLAN_HINTS[key]))
            rows.append([InlineKeyboardButton(f"   {T.SWEAR_LEVELS[level]}: {T.SWEAR_PLANS[key]}",
                                              callback_data=f"sw:l:{level}")])
        lines.append("")
    rows.append([InlineKeyboardButton(T.BTN_CLOSE, callback_data="sw:x:0")])
    text = T.SWEAR_POLICY.format(levels="\n".join(lines).strip(), note=T.SWEAR_POLICY_FOOT)
    return text, InlineKeyboardMarkup(rows)


@registry.command("swear_policy", ("عقوبات السب", "عقوبات الشتائم"), section=S, min_rank=VIEW_RANK,
                  description="لوحة: تشغيل كل نوع وعقوبة كل فئة بالأزرار", order=14)
async def cmd_swear_policy(cx: CommandContext) -> None:
    text, kb = await policy_view(cx.services, cx.chat.id)
    await cx.reply(text, reply_markup=kb)


async def on_policy_button(q, msg: Message, svc: Services, bot, action: str, arg: str) -> None:
    chat_id, uid = msg.chat.id, q.from_user.id
    rank = await svc.perms.rank_of(bot, chat_id, uid)
    if action == "x":
        if rank >= VIEW_RANK:
            try:
                await msg.delete()
            except TelegramError:
                pass
        return
    if action == "m":
        scope = "insult" if arg == "i" else "vulgar"
        if rank < SET_RANK["smart"]:
            await q.answer(T.SWEAR_POLICY_NEED_RANK, show_alert=True)
            return
        new = next_mode(await get_mode(svc, chat_id, scope))
        if rank < SET_RANK[new]:
            new = "off"
        await set_mode(svc, chat_id, new, uid, scope)
        await q.answer(T.SWEAR_BTN_SCOPE[scope].format(mode=T.SWEAR_MODES[new]))
    elif rank < DICT_RANK:
        await q.answer(T.SWEAR_POLICY_NEED_RANK, show_alert=True)
        return
    elif action == "l" and arg.isdigit() and int(arg) in LEVELS:
        level = int(arg)
        cur = await get_plan_key(svc, chat_id, level)
        order = mod.SWEAR_PLAN_ORDER
        new = order[(order.index(cur) + 1) % len(order)]
        await svc.group_settings.set(chat_id, f"swear_l{level}", new, uid)
        await svc.audit.log("setting", chat_id=chat_id, actor_id=uid,
                            details={"key": f"swear_l{level}", "from": cur, "to": new})
        await q.answer(f"{T.SWEAR_LEVELS[level]}: {T.SWEAR_PLANS[new]}")
    else:
        await q.answer()
        return
    text, kb = await policy_view(svc, chat_id)
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass


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
    scope = scope_of(hit.entry.level)
    mode = await get_mode(svc, cx.chat.id, scope)
    plan = await plan_for(svc, cx.chat.id, hit.entry.level, mode)
    action = T.SWEAR_MODES["off"] if mode == "off" else step_label(mod.swear_step(plan, 1))
    out.append(T.SWEAR_TEST_BLOCKED.format(
        scope=T.SWEAR_SCOPES[scope], scope_mode=T.SWEAR_MODES[mode],
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
