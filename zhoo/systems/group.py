"""إعدادات المجموعة: الترحيب والتوديع، القوانين، الرابط، الإحصائيات، ولوحة الإعدادات الشاملة."""
from __future__ import annotations

import logging
import time

from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.fmt import esc, mention
from zhoo.core.moderation import WARN_ACTIONS
from zhoo.core.ranks import Rank
from zhoo.database.db import now

log = logging.getLogger(__name__)

VIEW_RANK = Rank.ADMIN
EDIT_RANK = Rank.MANAGER
MAX_TEMPLATE = 1000
MAX_RULES = 3500

KINDS = {  # نوع القالب ← (المفتاح، مفتاح التفعيل، الافتراضي، الاسم)
    "welcome": ("welcome_text", "welcome_on", T.DEFAULT_WELCOME, "الترحيب"),
    "goodbye": ("goodbye_text", "goodbye_on", T.DEFAULT_GOODBYE, "التوديع"),
}

# آخر رسالة ترحيب بكل مجموعة (نحذف القديمة حتى ما تتكدس)
_last_welcome: dict[int, int] = {}


# ── القوالب ─────────────────────────────────────────
def render(template: str, user: User, chat: Chat, count: int | None) -> str:
    text = esc(template)
    values = {
        "{الاسم}": mention(user.id, user.full_name),
        "{اليوزر}": f"@{esc(user.username)}" if user.username else esc(user.full_name),
        "{الايدي}": f"<code>{user.id}</code>",
        "{المجموعة}": f"<b>{esc(chat.title or '')}</b>",
        "{المجموعه}": f"<b>{esc(chat.title or '')}</b>",
        "{العدد}": f"<b>{count}</b>" if count else "—",
    }
    for k, v in values.items():
        text = text.replace(k, v)
    return text


async def template_of(svc: Services, chat_id: int, kind: str) -> str:
    key, _, default, _ = KINDS[kind]
    return (await svc.group_settings.get(chat_id, key)) or default


async def _member_count(bot, chat_id: int) -> int | None:
    try:
        return await bot.get_chat_member_count(chat_id)
    except TelegramError:
        return None


async def _rules_keyboard(svc: Services, chat_id: int) -> InlineKeyboardMarkup | None:
    if await svc.group_settings.get(chat_id, "rules"):
        return InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_RULES, callback_data="r:show")]])
    return None


async def send_welcome(bot, svc: Services, chat: Chat, user: User) -> None:
    from zhoo.systems import botstate
    if (await svc.group_settings.get(chat.id, "welcome_on")) != "1" or await botstate.is_quiet(svc, chat.id):
        return
    text = render(await template_of(svc, chat.id, "welcome"), user, chat, await _member_count(bot, chat.id))
    try:
        sent = await bot.send_message(chat.id, text, reply_markup=await _rules_keyboard(svc, chat.id))
    except TelegramError as e:
        log.info("فشل إرسال الترحيب: %s", e)
        return
    old = _last_welcome.get(chat.id)
    _last_welcome[chat.id] = sent.message_id
    if old:
        try:
            await bot.delete_message(chat.id, old)
        except TelegramError:
            pass


async def on_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat = update.effective_message, update.effective_chat
    if msg is None or chat is None or msg.left_chat_member is None:
        return
    svc = get_services(context)
    left = msg.left_chat_member
    from zhoo.systems import botstate
    if not await botstate.is_active(svc, chat.id):
        return
    if (await svc.group_settings.get(chat.id, "lock_service")) == "1":
        try:
            await msg.delete()
        except TelegramError:
            pass
    if left.is_bot or left.id == context.bot.id:
        return
    # إذا انطرد (مو طلع بنفسه) ما نودعه
    if msg.from_user is not None and msg.from_user.id != left.id:
        return
    if (await svc.group_settings.get(chat.id, "goodbye_on")) != "1":
        return
    text = render(await template_of(svc, chat.id, "goodbye"), left, chat, None)
    from zhoo.systems.protect import send_notice
    await send_notice(context, chat.id, text, ttl=60)


# ── أوامر الترحيب والتوديع ────────────────────────────
async def _status(cx: CommandContext, kind: str) -> None:
    key, on_key, default, name = KINDS[kind]
    svc = cx.services
    on = (await svc.group_settings.get(cx.chat.id, on_key)) == "1"
    custom = bool(await svc.group_settings.get(cx.chat.id, key))
    preview = render(await template_of(svc, cx.chat.id, kind), cx.user, cx.chat, await _member_count(cx.bot, cx.chat.id))
    await cx.reply(T.WELCOME_STATUS.format(
        kind=name, state=T.STATE_ON if on else T.STATE_OFF, custom=T.TEMPLATE_CUSTOM if custom else T.TEMPLATE_DEFAULT,
        preview=preview) + "\n\n" + T.TEMPLATE_VARS)


async def _set_template(cx: CommandContext, kind: str) -> None:
    key, on_key, _, name = KINDS[kind]
    text = cx.raw_args.strip()
    if not text:
        await cx.reply(T.WELCOME_EMPTY.format(vars=T.TEMPLATE_VARS))
        return
    if len(text) > MAX_TEMPLATE:
        await cx.reply(T.WELCOME_TOO_LONG)
        return
    svc = cx.services
    await svc.group_settings.set(cx.chat.id, key, text, cx.user.id)
    await svc.group_settings.set(cx.chat.id, on_key, "1", cx.user.id)
    await svc.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id, details={"key": key})
    preview = render(text, cx.user, cx.chat, await _member_count(cx.bot, cx.chat.id))
    await cx.reply(T.WELCOME_SET.format(kind=name, preview=preview))


async def _toggle(cx: CommandContext, kind: str, on: bool) -> None:
    _, on_key, _, name = KINDS[kind]
    await cx.services.group_settings.set(cx.chat.id, on_key, "1" if on else "0", cx.user.id)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"key": on_key, "to": int(on)})
    await cx.reply((T.WELCOME_ON if on else T.WELCOME_OFF).format(kind=name))


async def _reset(cx: CommandContext, kind: str) -> None:
    key, _, _, name = KINDS[kind]
    await cx.services.group_settings.set(cx.chat.id, key, "", cx.user.id)
    await cx.reply(T.WELCOME_RESET.format(kind=name))


def _register_welcome() -> None:
    specs = [
        ("welcome", "الترحيب", "welcome", 1),
        ("goodbye", "التوديع", "welcome", 10),
    ]
    for kind, word, section, base in specs:
        async def status(cx, _k=kind): await _status(cx, _k)               # noqa: E704
        async def set_t(cx, _k=kind): await _set_template(cx, _k)          # noqa: E704
        async def on(cx, _k=kind): await _toggle(cx, _k, True)             # noqa: E704
        async def off(cx, _k=kind): await _toggle(cx, _k, False)           # noqa: E704
        async def reset(cx, _k=kind): await _reset(cx, _k)                 # noqa: E704

        registry.command(f"{kind}_status", (word,), section=section, min_rank=VIEW_RANK,
                         description=f"حالة {word} ومعاينته", order=base)(status)
        registry.command(f"{kind}_set", (f"تعيين {word}", f"وضع {word}"), section=section, min_rank=EDIT_RANK,
                         args="text", usage="النص", description=f"قالب {word} الخاص بك", order=base + 1)(set_t)
        registry.command(f"{kind}_on", (f"تفعيل {word}",), section=section, min_rank=EDIT_RANK,
                         description=f"يشغّل {word}", order=base + 2)(on)
        registry.command(f"{kind}_off", (f"تعطيل {word}",), section=section, min_rank=EDIT_RANK,
                         description=f"يوقف {word}", order=base + 3)(off)
        registry.command(f"{kind}_reset", (f"حذف {word}",), section=section, min_rank=EDIT_RANK,
                         description=f"يرجع {word} للقالب الافتراضي", order=base + 4)(reset)


_register_welcome()


# ── القوانين ─────────────────────────────────────────
@registry.command("rules", ("القوانين", "قوانين"), section="group", description="يعرض قوانين المجموعة", order=1)
async def cmd_rules(cx: CommandContext) -> None:
    rules = await cx.services.group_settings.get(cx.chat.id, "rules")
    if not rules:
        await cx.reply(T.RULES_EMPTY)
        return
    await cx.reply(T.RULES_TEXT.format(title=esc(cx.chat.title or ""), rules=esc(rules)))


@registry.command("rules_set", ("تعيين القوانين", "وضع القوانين"), section="group", min_rank=EDIT_RANK,
                  args="text", usage="النص", description="يحفظ قوانين المجموعة", order=2)
async def cmd_rules_set(cx: CommandContext) -> None:
    text = cx.raw_args.strip()
    if not text:
        await cx.reply(T.RULES_NEED_TEXT)
        return
    await cx.services.group_settings.set(cx.chat.id, "rules", text[:MAX_RULES], cx.user.id)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id, details={"key": "rules"})
    await cx.reply(T.RULES_SET)


@registry.command("rules_del", ("حذف القوانين",), section="group", min_rank=EDIT_RANK,
                  description="يحذف القوانين", order=3)
async def cmd_rules_del(cx: CommandContext) -> None:
    await cx.services.group_settings.set(cx.chat.id, "rules", "", cx.user.id)
    await cx.reply(T.RULES_DELETED)


async def on_rules_button(q, msg: Message, svc: Services) -> None:
    rules = await svc.group_settings.get(msg.chat.id, "rules")
    if not rules:
        await q.answer(T.RULES_EMPTY.split("\n")[0].replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    limit = 190
    text = rules if len(rules) <= limit else rules[: limit - len(T.RULES_ALERT_MORE)] + T.RULES_ALERT_MORE
    await q.answer(text, show_alert=True)


# ── الرابط ───────────────────────────────────────────
@registry.command("link", ("الرابط", "رابط المجموعه", "رابط"), section="group",
                  description="رابط دعوة المجموعة", order=4)
async def cmd_link(cx: CommandContext) -> None:
    svc = cx.services
    link = await svc.group_settings.get(cx.chat.id, "invite_link")
    if not link and cx.chat.username:
        link = f"https://t.me/{cx.chat.username}"
    if not link:
        try:
            chat = await cx.bot.get_chat(cx.chat.id)
            link = getattr(chat, "invite_link", None)
            if not link:
                created = await cx.bot.create_chat_invite_link(cx.chat.id, name="Zhoo")
                link = created.invite_link
            await svc.group_settings.set(cx.chat.id, "invite_link", link, cx.bot.id)
        except TelegramError:
            link = None
    if not link:
        await cx.reply(T.LINK_NONE)
        return
    await cx.reply(T.LINK_TEXT.format(title=esc(cx.chat.title or ""), link=esc(link)))


@registry.command("link_set", ("تعيين الرابط", "وضع الرابط"), section="group", min_rank=EDIT_RANK,
                  args="text", usage="https://t.me/...", description="يحفظ رابطاً مخصصاً", order=5)
async def cmd_link_set(cx: CommandContext) -> None:
    link = cx.args[0] if cx.args else ""
    if not link.startswith(("https://t.me/", "http://t.me/", "t.me/")) or len(link) > 200:
        await cx.reply(T.LINK_BAD)
        return
    if link.startswith("t.me/"):
        link = "https://" + link
    await cx.services.group_settings.set(cx.chat.id, "invite_link", link, cx.user.id)
    await cx.reply(T.LINK_SET)


@registry.command("link_del", ("حذف الرابط",), section="group", min_rank=EDIT_RANK,
                  description="يحذف الرابط المحفوظ", order=6)
async def cmd_link_del(cx: CommandContext) -> None:
    await cx.services.group_settings.set(cx.chat.id, "invite_link", "", cx.user.id)
    await cx.reply(T.LINK_DELETED)


# ── الإحصائيات ───────────────────────────────────────
@registry.command("stats", ("الاحصائيات", "الإحصائيات", "احصائيات"), section="group", min_rank=VIEW_RANK,
                  description="إحصائيات المجموعة الكاملة", order=7)
async def cmd_stats(cx: CommandContext) -> None:
    from zhoo.systems import locks, protect
    svc = cx.services
    chat_id = cx.chat.id
    await svc.tracker.flush()
    members = await _member_count(cx.bot, chat_id)
    staff = len(await svc.members.list_ranked(chat_id))
    messages = await svc.db.fetchval(
        "SELECT COALESCE(SUM(msg_count), 0) FROM group_members WHERE chat_id = ?", (chat_id,), default=0)
    banned = len(await svc.punishments.list_active(chat_id, "ban", 1000))
    muted = len(await svc.punishments.list_active(chat_id, "mute", 1000))
    guard24 = await svc.db.fetchval(
        "SELECT COUNT(*) FROM audit_logs WHERE chat_id = ? AND action LIKE 'guard_%' "
        "AND action NOT LIKE 'guard_captcha_ok' AND created_at > ?", (chat_id, now() - 86400), default=0)
    state = await protect.guards_state(svc, chat_id)
    lvl = protect.current_level(state)
    lock_count = await locks.active_count(svc, chat_id)
    swear24 = await svc.swear_logs.count_since(chat_id, 86400)
    top_rows = await svc.members.top_active(chat_id, 3)
    medals = ("🥇", "🥈", "🥉")
    top = "\n".join(
        f"    {medals[i]} {mention(r['user_id'], ' '.join(p for p in (r['first_name'], r['last_name']) if p))}"
        f" ⋅ {r['msg_count']}" for i, r in enumerate(top_rows)) or "    —"
    await cx.reply(T.STATS_TEXT.format(
        title=esc(cx.chat.title or ""), members=members or "—", staff=staff, messages=messages,
        banned=banned, muted=muted, guard24=guard24, swear24=swear24,
        level=T.GUARD_LEVELS[lvl] if lvl else T.GUARD_CUSTOM, locks=lock_count, top=top))


# ── لوحة الإعدادات الشاملة ────────────────────────────
WARN_LIMIT_CYCLE = ("2", "3", "4", "5", "6")
WARN_ACTION_CYCLE = ("mute", "kick", "ban")


async def settings_view(svc: Services, chat: Chat, uid: int) -> tuple[str, InlineKeyboardMarkup]:
    from zhoo.systems import locks, protect
    g = svc.group_settings
    welcome_on = (await g.get(chat.id, "welcome_on")) == "1"
    goodbye_on = (await g.get(chat.id, "goodbye_on")) == "1"
    limit = await g.get(chat.id, "warn_limit")
    action = await g.get(chat.id, "warn_action")
    lvl = protect.current_level(await protect.guards_state(svc, chat.id))
    from zhoo.systems import swear
    lock_count = await locks.active_count(svc, chat.id)
    swear_mode = await swear.get_mode(svc, chat.id)
    text = T.SETTINGS_PANEL.format(
        title=esc(chat.title or ""), limit=limit, action=WARN_ACTIONS.get(action, "كتم"),
        level=T.GUARD_LEVELS[lvl] if lvl else T.GUARD_CUSTOM, locks=lock_count,
        swear=T.SWEAR_MODES[swear_mode])

    def b(label, action_, arg="-"):
        return InlineKeyboardButton(label, callback_data=f"st:{uid}:{action_}:{arg}")

    kb = InlineKeyboardMarkup([
        [b(f"{'✅' if welcome_on else '▫️'} {T.BTN_WELCOME}", "tw"),
         b(f"{'✅' if goodbye_on else '▫️'} {T.BTN_GOODBYE}", "tg")],
        [b(T.BTN_WARN_LIMIT.format(n=limit), "wl"),
         b(T.BTN_WARN_ACTION.format(a=WARN_ACTIONS.get(action, "كتم")), "wa")],
        [b(f"{T.SWEAR_LABEL}: {T.SWEAR_MODES[swear_mode]}", "sw")],
        [b(T.BTN_LOCKS, "locks"), b(T.BTN_PROTECT, "guard")],
        [b(T.BTN_CLOSE, "x")],
    ])
    return text, kb


@registry.command("settings", ("الاعدادات", "الإعدادات", "اعدادات المجموعه"), section="group",
                  min_rank=VIEW_RANK, description="لوحة إعدادات المجموعة الشاملة بالأزرار", order=0)
async def cmd_settings(cx: CommandContext) -> None:
    text, kb = await settings_view(cx.services, cx.chat, cx.user.id)
    await cx.reply(text, reply_markup=kb)


def _next(cycle: tuple[str, ...], current: str) -> str:
    return cycle[(cycle.index(current) + 1) % len(cycle)] if current in cycle else cycle[0]


async def on_settings_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str, arg: str) -> None:
    from zhoo.systems import locks, protect
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    uid, chat = q.from_user.id, msg.chat
    if action == "x":
        try:
            await msg.delete()
        except TelegramError:
            pass
        return
    rank = await svc.perms.rank_of(bot, chat.id, uid)
    if action == "home":
        text, kb = await settings_view(svc, chat, uid)
    elif action == "locks":
        from zhoo.systems import swear
        state = await locks.lock_state(svc, chat.id)
        mode = await swear.get_mode(svc, chat.id)
        text, kb = T.LOCK_PANEL, locks.panel_keyboard(uid, state, back=True, swear_mode=mode)
    elif action == "guard":
        state = await protect.guards_state(svc, chat.id)
        text, kb = protect.panel_text(state), protect.panel_keyboard(uid, state, back=True)
    else:
        if rank < EDIT_RANK:
            await q.answer(T.SETTINGS_NEED_MANAGER, show_alert=True)
            return
        g = svc.group_settings
        if action in ("tw", "tg"):
            key = "welcome_on" if action == "tw" else "goodbye_on"
            new = "0" if (await g.get(chat.id, key)) == "1" else "1"
            await g.set(chat.id, key, new, uid)
            await svc.audit.log("setting", chat_id=chat.id, actor_id=uid, details={"key": key, "to": new})
        elif action == "wl":
            new = _next(WARN_LIMIT_CYCLE, await g.get(chat.id, "warn_limit"))
            await g.set(chat.id, "warn_limit", new, uid)
            await svc.audit.log("setting", chat_id=chat.id, actor_id=uid, details={"key": "warn_limit", "to": new})
        elif action == "sw":
            from zhoo.systems import swear
            new = swear.next_mode(await swear.get_mode(svc, chat.id))
            await swear.set_mode(svc, chat.id, new, uid)
        elif action == "wa":
            new = _next(WARN_ACTION_CYCLE, await g.get(chat.id, "warn_action"))
            await g.set(chat.id, "warn_action", new, uid)
            await svc.audit.log("setting", chat_id=chat.id, actor_id=uid, details={"key": "warn_action", "to": new})
        else:
            await q.answer()
            return
        await q.answer("✨")
        text, kb = await settings_view(svc, chat, uid)
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass
