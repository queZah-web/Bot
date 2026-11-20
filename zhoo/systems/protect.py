"""نظام الحماية: فحص الرسائل، العقوبة المتدرجة، التحقق من الأعضاء الجدد، والبوتات الدخيلة.

القواعد:
- المميز فما فوق مستثنى دائماً.
- ما نعاقب عقوبة قاسية على إشارة وحدة: حذف + تنبيه، وبعد تكرار المخالفة كتم مؤقت.
- الإغراق إشارة قوية → كتم قصير مباشرة.
- كل إجراء ينسجل بسجل التدقيق بإسم guard_*.
"""
from __future__ import annotations

import json
import logging
import time

from telegram import (Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User)
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes

from zhoo.core import guards
from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.durations import format_duration
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank

log = logging.getLogger(__name__)
S = "protect"

GUARD_KEYS = ("flood", "repeat", "links", "forward", "mentions", "bots", "captcha")
LEVELS: dict[str, dict[str, bool]] = {
    "light":  {"flood": True, "repeat": False, "links": False, "forward": False,
               "mentions": True, "bots": True, "captcha": False},
    "medium": {"flood": True, "repeat": True, "links": True, "forward": False,
               "mentions": True, "bots": True, "captcha": False},
    "strict": {"flood": True, "repeat": True, "links": True, "forward": True,
               "mentions": True, "bots": True, "captcha": True},
}
LEVEL_WORDS = {normalize("خفيف"): "light", normalize("متوسط"): "medium", normalize("صارم"): "strict"}

EXEMPT_RANK = Rank.VIP          # المميز فما فوق مستثنى
EDIT_RANK = Rank.MANAGER        # تعديل الإعدادات
VIEW_RANK = Rank.ADMIN          # عرض الإعدادات والسجل

FLOOD_LIMIT = 7                 # رسائل خلال نافذة FloodTracker (5 ثواني)
FLOOD_MUTE = 10 * 60
REPEAT_LIMIT = 3                # نفس الرسالة 3 مرات ورا بعض
MENTION_LIMIT = 5
MAX_STRIKES = 3                 # بعدها كتم
STRIKE_MUTE = 60 * 60
NOTICE_TTL = 20                 # التنبيه ينحذف بعد 20 ثانية
CAPTCHA_TTL = 3 * 60


# ── أدوات ───────────────────────────────────────────
async def guards_state(svc: Services, chat_id: int) -> dict[str, bool]:
    return {k: (await svc.group_settings.get(chat_id, f"guard_{k}")) == "1" for k in GUARD_KEYS}


def current_level(state: dict[str, bool]) -> str | None:
    return next((name for name, preset in LEVELS.items() if preset == state), None)


async def whitelist(svc: Services, chat_id: int) -> set[str]:
    raw = await svc.group_settings.get(chat_id, "link_whitelist")
    return {d for d in raw.split(",") if d}


async def _delete_later(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id, message_id = context.job.data
    try:
        await context.bot.delete_message(chat_id, message_id)
    except TelegramError:
        pass


async def send_notice(context, chat_id: int, text: str, ttl: int = NOTICE_TTL, **kw) -> Message | None:
    try:
        sent = await context.bot.send_message(chat_id, text, **kw)
    except TelegramError:
        return None
    jq = getattr(context, "job_queue", None)
    if jq is not None and ttl:
        jq.run_once(_delete_later, ttl, data=(chat_id, sent.message_id))
    return sent


async def _safe_delete(msg: Message) -> bool:
    try:
        await msg.delete()
        return True
    except TelegramError:
        return False


# ── الفحص الرئيسي ───────────────────────────────────
async def inspect(update: Update, context: ContextTypes.DEFAULT_TYPE, svc: Services,
                  msg: Message, chat: Chat, user: User) -> bool:
    """يفحص رسالة بالمجموعة. يرجع True إذا انحذفت (فما نكمل معالجتها)."""
    state = await guards_state(svc, chat.id)
    key = (chat.id, user.id)
    violation: str | None = None

    # ١) الإغراق — يُحسب للكل، والاستثناء يتحدد بعد الكشف فقط (أسرع)
    if state["flood"] and svc.flood.hit(key) >= FLOOD_LIMIT:
        violation = "flood"
    # ٢) التكرار
    elif state["repeat"] and (msg.text or msg.caption) and \
            svc.repeats.hit(key, msg.text or msg.caption) >= REPEAT_LIMIT:
        violation = "repeat"
    # ٣) المنشن الجماعي
    elif state["mentions"] and guards.count_mentions(msg) > MENTION_LIMIT:
        violation = "mentions"
    # ٤) التوجيه
    elif state["forward"] and guards.is_forward(msg):
        violation = "forward"
    # ٥) الروابط
    elif state["links"] and guards.forbidden_links(msg, await whitelist(svc, chat.id), chat.username):
        violation = "links"

    if violation is None:
        return False

    rank = await svc.perms.rank_of(context.bot, chat.id, user.id)
    if rank >= EXEMPT_RANK:
        return False

    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False  # ما نكدر نسوي شي بدون صلاحية الحذف

    await _safe_delete(msg)
    who = mention(user.id, user.full_name)

    if violation == "flood":
        svc.flood.reset(key)
        await _auto_mute(context, svc, chat.id, user, "flood", FLOOD_MUTE, rights)
        return True

    strike = svc.strikes.add(key)
    await svc.audit.log(f"guard_{violation}", chat_id=chat.id, actor_id=context.bot.id, target_id=user.id,
                        details={"strike": strike})
    if strike >= MAX_STRIKES:
        svc.strikes.reset(key)
        await _auto_mute(context, svc, chat.id, user, violation, STRIKE_MUTE, rights)
    elif svc.notice_limiter.hit(key):
        await send_notice(context, chat.id, T.GUARD_NOTICE.format(
            mention=who, what=T.GUARD_WHAT[violation], strike=strike, max=MAX_STRIKES))
    return True


async def _auto_mute(context, svc: Services, chat_id: int, user: User, why: str, seconds: int, rights) -> None:
    if not rights.can_restrict_members:
        return
    until = int(time.time()) + seconds
    try:
        await mod.apply(context.bot, chat_id, user.id, "mute", until)
    except (BadRequest, Forbidden) as e:
        log.info("فشل الكتم التلقائي: %s", e)
        return
    await svc.punishments.add(chat_id, user.id, "mute", context.bot.id, T.GUARD_WHY[why], until)
    await svc.audit.log(f"guard_mute_{why}", chat_id=chat_id, actor_id=context.bot.id, target_id=user.id,
                        details={"seconds": seconds})
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_UNDO_MUTE, callback_data=f"p:m:{user.id}")]])
    await send_notice(context, chat_id, T.GUARD_MUTED.format(
        mention=mention(user.id, user.full_name), why=T.GUARD_WHY[why], duration=format_duration(seconds)),
        ttl=0, reply_markup=kb)


# ── الأعضاء الجدد: البوتات والتحقق ────────────────────
async def on_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat = update.effective_message, update.effective_chat
    if msg is None or chat is None or not msg.new_chat_members:
        return
    svc = get_services(context)
    await svc.tracker.track_group(chat)
    state = await guards_state(svc, chat.id)
    adder = msg.from_user
    adder_rank = await svc.perms.rank_of(context.bot, chat.id, adder.id) if adder else Rank.MEMBER

    for member in msg.new_chat_members:
        if member.id == context.bot.id:
            continue
        await svc.tracker.track_user(member)
        self_joined = adder is None or adder.id == member.id

        if member.is_bot:
            if state["bots"] and adder_rank < Rank.ADMIN:
                await _kick_bot(context, svc, chat.id, member, adder)
            continue

        if state["captcha"] and (self_joined or adder_rank < Rank.ADMIN) and \
                await start_captcha(context, svc, chat.id, member):
            continue  # الترحيب بعد التحقق
        from zhoo.systems.group import send_welcome
        await send_welcome(context.bot, svc, chat, member)

    if (await svc.group_settings.get(chat.id, "lock_service")) == "1":
        try:
            await msg.delete()
        except TelegramError:
            pass


async def _kick_bot(context, svc: Services, chat_id: int, bot_user: User, adder: User | None) -> None:
    rights = await svc.perms.bot_rights(context.bot, chat_id)
    if rights is None or not rights.can_restrict_members:
        return
    try:
        await context.bot.ban_chat_member(chat_id, bot_user.id)
    except TelegramError as e:
        log.info("ما كدرت أطرد البوت %s: %s", bot_user.id, e)
        return
    await svc.audit.log("guard_bot", chat_id=chat_id, actor_id=context.bot.id, target_id=bot_user.id,
                        details={"added_by": adder.id if adder else None})
    await send_notice(context, chat_id, T.GUARD_BOT_KICKED.format(bot=mention(bot_user.id, bot_user.full_name)))


async def start_captcha(context, svc: Services, chat_id: int, member: User) -> bool:
    """يرجع True إذا بدأ التحقق فعلاً."""
    rights = await svc.perms.bot_rights(context.bot, chat_id)
    if rights is None or not rights.can_restrict_members:
        return False
    try:
        await mod.apply(context.bot, chat_id, member.id, "restrict", None)  # مشاهدة فقط لحد التحقق
    except TelegramError as e:
        log.info("فشل تقييد العضو الجديد: %s", e)
        return False
    await svc.captcha.add(chat_id, member.id, None, CAPTCHA_TTL)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.CAPTCHA_BUTTON, callback_data=f"c:{member.id}")]])
    sent = await send_notice(context, chat_id, T.CAPTCHA_TEXT.format(
        mention=mention(member.id, member.full_name), minutes=CAPTCHA_TTL // 60), ttl=0, reply_markup=kb)
    if sent is not None:
        await svc.captcha.set_message(chat_id, member.id, sent.message_id)
    return True


async def on_captcha_button(q, msg: Message, svc: Services, bot, uid_raw: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.CAPTCHA_NOT_YOURS, show_alert=True)
        return
    row = await svc.captcha.pop(msg.chat.id, q.from_user.id)
    if row is None:
        await q.answer(T.CAPTCHA_EXPIRED)
        return
    try:
        await mod.lift(bot, msg.chat.id, q.from_user.id, "mute")
    except TelegramError as e:
        log.info("فشل فك تقييد العضو بعد التحقق: %s", e)
    await svc.audit.log("guard_captcha_ok", chat_id=msg.chat.id, actor_id=q.from_user.id, target_id=q.from_user.id)
    await q.answer(T.CAPTCHA_DONE)
    try:
        await msg.delete()
    except TelegramError:
        pass
    from zhoo.systems.group import send_welcome
    await send_welcome(bot, svc, msg.chat, q.from_user)


async def sweep_captcha(context: ContextTypes.DEFAULT_TYPE) -> None:
    """يطرد اللي ما تحققوا بالوقت (يشتغل كل دقيقة، ويتحمل إعادة التشغيل)."""
    svc = get_services(context)
    for row in await svc.captcha.expired():
        chat_id, user_id = row["chat_id"], row["user_id"]
        if await svc.captcha.pop(chat_id, user_id) is None:
            continue
        try:
            await mod.apply(context.bot, chat_id, user_id, "kick", None)
            await svc.audit.log("guard_captcha_kick", chat_id=chat_id, actor_id=context.bot.id, target_id=user_id)
        except TelegramError as e:
            log.info("فشل طرد غير المتحقق %s: %s", user_id, e)
        if row["message_id"]:
            try:
                await context.bot.delete_message(chat_id, row["message_id"])
            except TelegramError:
                pass


# ── لوحة الإعدادات ──────────────────────────────────
def panel_keyboard(uid: int, state: dict[str, bool], back: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for k in GUARD_KEYS:
        name, emoji, _ = T.GUARD_LABELS[k]
        mark = "✅" if state[k] else "▫️"
        buttons.append(InlineKeyboardButton(f"{mark} {name}", callback_data=f"g:{uid}:t:{k}"))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(label, callback_data=f"g:{uid}:p:{lvl}")
                 for lvl, label in T.GUARD_LEVELS.items()])
    last = [InlineKeyboardButton(T.BTN_CLOSE, callback_data=f"g:{uid}:x:-")]
    if back:
        last.insert(0, InlineKeyboardButton(T.BTN_BACK, callback_data=f"st:{uid}:home:-"))
    rows.append(last)
    return InlineKeyboardMarkup(rows)


def has_back(msg) -> bool:
    """هل اللوحة مفتوحة من «الإعدادات» (فيها زر رجوع)؟"""
    markup = getattr(msg, "reply_markup", None)
    if not markup:
        return False
    return any(b.callback_data and b.callback_data.startswith("st:") for row in markup.inline_keyboard for b in row)


def panel_text(state: dict[str, bool]) -> str:
    lvl = current_level(state)
    rows = "\n".join(
        f"{'✅' if state[k] else '▫️'} {T.GUARD_LABELS[k][1]} <b>{T.GUARD_LABELS[k][0]}</b>"
        for k in GUARD_KEYS
    )
    return T.GUARD_PANEL.format(level=T.GUARD_LEVELS[lvl] if lvl else T.GUARD_CUSTOM, rows=rows)


async def _apply_level(svc: Services, chat_id: int, level: str, by: int) -> None:
    for k, on in LEVELS[level].items():
        await svc.group_settings.set(chat_id, f"guard_{k}", "1" if on else "0", by)
    await svc.audit.log("setting", chat_id=chat_id, actor_id=by, details={"key": "guard_level", "to": level})


async def on_panel_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str, arg: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    chat_id = msg.chat.id
    if action == "x":
        try:
            await msg.delete()
        except TelegramError:
            pass
        return
    rank = await svc.perms.rank_of(bot, chat_id, q.from_user.id)
    if rank < EDIT_RANK:
        await q.answer(T.GUARD_NEED_MANAGER, show_alert=True)
        return
    if action == "t" and arg in GUARD_KEYS:
        key = f"guard_{arg}"
        new = "0" if (await svc.group_settings.get(chat_id, key)) == "1" else "1"
        old = await svc.group_settings.set(chat_id, key, new, q.from_user.id)
        await svc.audit.log("setting", chat_id=chat_id, actor_id=q.from_user.id,
                            details={"key": key, "from": old, "to": new})
        await q.answer(("✅ " if new == "1" else "▫️ ") + T.GUARD_LABELS[arg][0])
    elif action == "p" and arg in LEVELS:
        await _apply_level(svc, chat_id, arg, q.from_user.id)
        await q.answer(T.GUARD_LEVELS[arg])
    else:
        await q.answer()
        return
    state = await guards_state(svc, chat_id)
    try:
        await msg.edit_text(panel_text(state), reply_markup=panel_keyboard(q.from_user.id, state, has_back(msg)))
    except BadRequest:
        pass


# ── الأوامر ─────────────────────────────────────────
@registry.command("guard_panel", ("إعدادات الحماية", "الحماية", "اعدادات الحمايه"), section=S,
                  min_rank=VIEW_RANK, description="لوحة الحماية بالأزرار (تشغيل/إيقاف + المستويات)", order=1)
async def cmd_panel(cx: CommandContext) -> None:
    state = await guards_state(cx.services, cx.chat.id)
    text = panel_text(state)
    rights = await cx.services.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_delete_messages:
        text += "\n" + T.GUARD_NO_DELETE_RIGHT
    await cx.reply(text, reply_markup=panel_keyboard(cx.user.id, state))


@registry.command("guard_level", ("مستوى الحماية",), section=S, min_rank=EDIT_RANK, args="text",
                  usage="خفيف / متوسط / صارم", description="يضبط كل الحماية دفعة واحدة", order=2)
async def cmd_level(cx: CommandContext) -> None:
    level = LEVEL_WORDS.get(normalize(cx.raw_args))
    if level is None:
        await cx.reply(T.GUARD_LEVEL_BAD)
        return
    await _apply_level(cx.services, cx.chat.id, level, cx.user.id)
    await cx.reply(T.GUARD_LEVEL_SET.format(level=T.GUARD_LEVELS[level]))


async def _set_whitelist(cx: CommandContext, domains: set[str]) -> None:
    await cx.services.group_settings.set(cx.chat.id, "link_whitelist", ",".join(sorted(domains)), cx.user.id)


@registry.command("allow_link", ("سماح رابط", "السماح برابط"), section=S, min_rank=EDIT_RANK, args="text",
                  usage="النطاق مثل youtube.com", description="يسمح بروابط موقع معيّن", order=3)
async def cmd_allow_link(cx: CommandContext) -> None:
    domain = guards.clean_domain(cx.args[0]) if cx.args else None
    if domain is None:
        await cx.reply(T.WHITELIST_BAD)
        return
    wl = await whitelist(cx.services, cx.chat.id)
    if len(wl) >= 50:
        wl = set(sorted(wl)[:49])
    wl.add(domain)
    await _set_whitelist(cx, wl)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"key": "link_whitelist", "add": domain})
    await cx.reply(T.WHITELIST_ADDED.format(domain=esc(domain)))


@registry.command("deny_link", ("منع رابط",), section=S, min_rank=EDIT_RANK, args="text",
                  usage="النطاق", description="يزيل موقعاً من الروابط المسموحة", order=4)
async def cmd_deny_link(cx: CommandContext) -> None:
    domain = guards.clean_domain(cx.args[0]) if cx.args else None
    if domain is None:
        await cx.reply(T.WHITELIST_BAD)
        return
    wl = await whitelist(cx.services, cx.chat.id)
    if domain not in wl:
        await cx.reply(T.WHITELIST_NOT_FOUND.format(domain=esc(domain)))
        return
    wl.discard(domain)
    await _set_whitelist(cx, wl)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"key": "link_whitelist", "remove": domain})
    await cx.reply(T.WHITELIST_REMOVED.format(domain=esc(domain)))


@registry.command("list_links", ("الروابط المسموحة", "الروابط المسموحه"), section=S, min_rank=VIEW_RANK,
                  description="قائمة المواقع المسموح بروابطها", order=5)
async def cmd_list_links(cx: CommandContext) -> None:
    wl = sorted(await whitelist(cx.services, cx.chat.id))
    body = "\n".join(f"▫️ <code>{esc(d)}</code>" for d in wl) if wl else T.WHITELIST_EMPTY
    await cx.reply(f"{T.WHITELIST_HEADER}\n{body}")


_LOG_NAMES = {
    "guard_flood": "🌊 إغراق", "guard_repeat": "🔁 تكرار", "guard_links": "🔗 رابط",
    "guard_forward": "↪️ توجيه", "guard_mentions": "📣 منشن جماعي", "guard_bot": "🤖 بوت دخيل",
    "guard_captcha_kick": "🧩 لم يتحقق", "guard_captcha_ok": "🧩 تحقق ✓",
}


@registry.command("guard_log", ("سجل الحماية",), section=S, min_rank=VIEW_RANK,
                  description="آخر المخالفات وإجراءات الحماية", order=6)
async def cmd_guard_log(cx: CommandContext) -> None:
    rows = await cx.services.audit.recent_actions(cx.chat.id, "guard_", 15)
    if not rows:
        await cx.reply(f"{T.GUARD_LOG_HEADER}\n{T.GUARD_LOG_EMPTY}")
        return
    lines = []
    for r in rows:
        action = r["action"]
        if action.startswith("guard_mute_"):
            label = f"🔇 كتم ({T.GUARD_WHY.get(action[len('guard_mute_'):], '')})"
        else:
            label = _LOG_NAMES.get(action, action)
        who = await cx.services.users.get(r["target_id"]) if r["target_id"] else None
        name = mention(r["target_id"], who.full_name) if who else f"<code>{r['target_id']}</code>"
        when = time.strftime("%m-%d %H:%M", time.gmtime(r["created_at"]))
        extra = ""
        if r["details"]:
            d = json.loads(r["details"])
            if "strike" in d:
                extra = f" <i>({d['strike']}/{MAX_STRIKES})</i>"
        lines.append(f"▫️ {label} ⋅ {name}{extra}\n      <code>{when}</code>")
    await cx.reply(f"{T.GUARD_LOG_HEADER}\n" + "\n".join(lines) + "\n<i>الوقت UTC</i>")
