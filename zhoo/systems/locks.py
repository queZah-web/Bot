"""القفل والفتح: منع أنواع معيّنة من الرسائل (المميز فما فوق مستثنى).

- أقفال الوسائط تُخزن كـ lock_<type>.
- قفل الروابط والتوجيه = نفس خيارات الحماية (guard_links / guard_forward) حتى ما يتكرر المنطق.
- قفل الدردشة = صلاحيات تيليجرام نفسها (يمنع الكل عدا المشرفين).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import mention
from zhoo.core.ranks import Rank

log = logging.getLogger(__name__)
S = "locks"

EDIT_RANK = Rank.ADMIN
EXEMPT_RANK = Rank.VIP


@dataclass(frozen=True)
class Lock:
    key: str
    name: str
    emoji: str
    aliases: tuple[str, ...]
    setting: str


LOCKS: tuple[Lock, ...] = (
    Lock("photos", "الصور", "🖼", ("صور",), "lock_photos"),
    Lock("videos", "الفيديو", "🎬", ("الفيديوهات", "فيديو"), "lock_videos"),
    Lock("gifs", "المتحركات", "🎞", ("المتحركه", "الجيفات", "الصور المتحركه"), "lock_gifs"),
    Lock("stickers", "الملصقات", "🧸", ("الستيكرات", "ملصقات"), "lock_stickers"),
    Lock("voice", "البصمات", "🎙", ("الفويسات", "الصوت"), "lock_voice"),
    Lock("audio", "الصوتيات", "🎵", ("الاغاني", "الموسيقى"), "lock_audio"),
    Lock("files", "الملفات", "📁", ("ملفات",), "lock_files"),
    Lock("contacts", "الجهات", "📇", ("جهات الاتصال",), "lock_contacts"),
    Lock("locations", "المواقع", "📍", ("الموقع",), "lock_locations"),
    Lock("polls", "الاستفتاءات", "📊", ("الاستفتاء", "التصويت"), "lock_polls"),
    Lock("service", "الإشعارات", "🔔", ("اشعارات الدخول",), "lock_service"),
    Lock("reactions", "الرياكت", "❤️", ("الرياكشن", "التفاعلات", "الريأكت", "الرياكتات"), "lock_reactions"),
    Lock("links", "الروابط", "🔗", ("روابط",), "guard_links"),
    Lock("forward", "التوجيه", "↪️", ("الفوروارد",), "guard_forward"),
    Lock("chat", "الدردشة", "💬", ("الشات", "المجموعه"), "lock_chat"),
)
LOCK_MAP = {l.key: l for l in LOCKS}
# «قفل الكل» يشمل كل شي عدا الدردشة (لها أمر خاص لأنها توقف الكل)
ALL_KEYS = tuple(l.key for l in LOCKS if l.key != "chat")


def media_lock(msg: Message) -> str | None:
    """نوع القفل اللي تخصه الرسالة (الروابط والتوجيه تتكفل بيها الحماية)."""
    if msg.photo:
        return "photos"
    if msg.animation:
        return "gifs"
    if msg.video or msg.video_note:
        return "videos"
    if msg.sticker:
        return "stickers"
    if msg.voice:
        return "voice"
    if msg.audio:
        return "audio"
    if msg.document:
        return "files"
    if msg.contact:
        return "contacts"
    if msg.location or msg.venue:
        return "locations"
    if msg.poll:
        return "polls"
    return None


async def is_locked(svc: Services, chat_id: int, key: str) -> bool:
    return (await svc.group_settings.get(chat_id, LOCK_MAP[key].setting)) == "1"


async def lock_state(svc: Services, chat_id: int) -> dict[str, bool]:
    return {l.key: await is_locked(svc, chat_id, l.key) for l in LOCKS}


async def check(context, svc: Services, msg: Message, chat, user) -> bool:
    """يرجع True إذا انحذفت الرسالة لأنها مقفولة."""
    key = media_lock(msg)
    if key is None or not await is_locked(svc, chat.id, key):
        return False
    if await svc.perms.rank_of(context.bot, chat.id, user.id) >= EXEMPT_RANK:
        return False
    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False
    try:
        await msg.delete()
    except TelegramError:
        return False
    from zhoo.systems.protect import send_notice  # تجنب الاستيراد الدائري
    if svc.notice_limiter.hit((chat.id, user.id)):
        await send_notice(context, chat.id, T.LOCK_NOTICE.format(
            mention=mention(user.id, user.full_name), what=LOCK_MAP[key].name), ttl=15)
    return True


# ── تغيير الأقفال ───────────────────────────────────
_OPEN_CHAT = ChatPermissions(
    can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True,
    can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True,
    can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True,
    can_change_info=False, can_pin_messages=False, can_manage_topics=False,
    can_react_to_messages=True,
)


async def set_lock(svc: Services, bot, chat_id: int, key: str, on: bool, by: int) -> str:
    """يغير القفل. يرجع: ok | same | no_rights"""
    lock = LOCK_MAP[key]
    if await is_locked(svc, chat_id, key) == on:
        return "same"
    if key == "chat":
        rights = await svc.perms.bot_rights(bot, chat_id)
        if rights is None or not rights.can_restrict_members:
            return "no_rights"
        try:
            if on:
                await bot.set_chat_permissions(chat_id, ChatPermissions.no_permissions())
            else:
                await bot.set_chat_permissions(chat_id, _OPEN_CHAT)
        except (BadRequest, TelegramError) as e:
            log.info("فشل تغيير صلاحيات الدردشة: %s", e)
            return "no_rights"
    old = await svc.group_settings.set(chat_id, lock.setting, "1" if on else "0", by)
    await svc.audit.log("lock" if on else "unlock", chat_id=chat_id, actor_id=by,
                        details={"key": key, "from": old})
    return "ok"


async def _cmd_lock(cx: CommandContext, key: str, on: bool) -> None:
    lock = LOCK_MAP[key]
    result = await set_lock(cx.services, cx.bot, cx.chat.id, key, on, cx.user.id)
    what = f"{lock.emoji} {lock.name}"
    if result == "same":
        await cx.reply((T.ALREADY_LOCKED if on else T.ALREADY_UNLOCKED).format(what=lock.name))
        return
    if result == "no_rights":
        await cx.reply(T.LOCK_CHAT_NEED_RIGHTS)
        return
    text = (T.LOCKED if on else T.UNLOCKED).format(what=what, actor=mention(cx.user.id, cx.user.full_name))
    if on and key != "chat":
        rights = await cx.services.perms.bot_rights(cx.bot, cx.chat.id)
        if rights is None or not rights.can_delete_messages:
            text += "\n" + T.LOCK_NEED_RIGHTS
    await cx.reply(text)


def _register() -> None:
    for i, lock in enumerate(LOCKS):
        names = (lock.name,) + lock.aliases

        async def do_lock(cx, _k=lock.key):
            await _cmd_lock(cx, _k, True)

        async def do_unlock(cx, _k=lock.key):
            await _cmd_lock(cx, _k, False)

        registry.command(f"lock_{lock.key}", tuple(f"قفل {n}" for n in names), section=S, min_rank=EDIT_RANK,
                         description=f"يقفل {lock.name}", show_in_help=False, order=50 + i)(do_lock)
        registry.command(f"unlock_{lock.key}", tuple(f"فتح {n}" for n in names), section=S, min_rank=EDIT_RANK,
                         description=f"يفتح {lock.name}", show_in_help=False, order=70 + i)(do_unlock)


_register()


async def _set_all(svc: Services, bot, chat_id: int, on: bool, by: int) -> int:
    from zhoo.systems import swear
    changed = 0
    for key in ALL_KEYS:
        if await set_lock(svc, bot, chat_id, key, on, by) == "ok":
            changed += 1
    mode = await swear.get_mode(svc, chat_id)
    if on and mode == "off":
        await swear.set_mode(svc, chat_id, "delete", by)
    elif not on and mode != "off":
        await swear.set_mode(svc, chat_id, "off", by)
    return changed


async def active_count(svc: Services, chat_id: int) -> int:
    """عدد الأقفال الفعالة (مع السب)."""
    from zhoo.systems import swear
    return sum((await lock_state(svc, chat_id)).values()) + (await swear.get_mode(svc, chat_id) != "off")


@registry.command("lock_all", ("قفل الكل",), section=S, min_rank=EDIT_RANK,
                  description="يقفل كل الأنواع (عدا الدردشة)", order=2)
async def cmd_lock_all(cx: CommandContext) -> None:
    await _set_all(cx.services, cx.bot, cx.chat.id, True, cx.user.id)
    await cx.reply(T.LOCKED.format(what=T.ALL_TYPES, actor=mention(cx.user.id, cx.user.full_name)))


@registry.command("unlock_all", ("فتح الكل",), section=S, min_rank=EDIT_RANK,
                  description="يفتح كل الأنواع (عدا الدردشة)", order=3)
async def cmd_unlock_all(cx: CommandContext) -> None:
    await _set_all(cx.services, cx.bot, cx.chat.id, False, cx.user.id)
    await cx.reply(T.UNLOCKED.format(what=T.ALL_TYPES, actor=mention(cx.user.id, cx.user.full_name)))


@registry.command("lock_one", ("قفل",), section=S, min_rank=EDIT_RANK, usage="النوع",
                  description="يقفل نوعاً معيّناً، مثل: قفل الصور", order=4)
async def cmd_lock_hint(cx: CommandContext) -> None:
    await cx.reply(T.HELP_LOCK_TYPES.strip())


@registry.command("unlock_one", ("فتح",), section=S, min_rank=EDIT_RANK, usage="النوع",
                  description="يفتح نوعاً معيّناً، مثل: فتح الصور", order=5)
async def cmd_unlock_hint(cx: CommandContext) -> None:
    await cx.reply(T.HELP_LOCK_TYPES.strip())


# ── لوحة الأقفال ────────────────────────────────────
def panel_keyboard(uid: int, state: dict[str, bool], back: bool = False,
                   swear_mode: str = "off") -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"{'🔒' if state[l.key] else '🔓'} {l.name}", callback_data=f"l:{uid}:t:{l.key}")
        for l in LOCKS
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(f"{T.SWEAR_LABEL}: {T.SWEAR_MODES[swear_mode]}",
                                      callback_data=f"l:{uid}:s:-")])
    rows.append([InlineKeyboardButton(T.BTN_LOCK_ALL, callback_data=f"l:{uid}:a:1"),
                 InlineKeyboardButton(T.BTN_UNLOCK_ALL, callback_data=f"l:{uid}:a:0")])
    last = [InlineKeyboardButton(T.BTN_CLOSE, callback_data=f"l:{uid}:x:-")]
    if back:
        last.insert(0, InlineKeyboardButton(T.BTN_BACK, callback_data=f"st:{uid}:home:-"))
    rows.append(last)
    return InlineKeyboardMarkup(rows)


@registry.command("locks_panel", ("الاقفال", "الأقفال"), section=S, min_rank=EDIT_RANK,
                  description="لوحة الأقفال بالأزرار", order=1)
async def cmd_panel(cx: CommandContext) -> None:
    from zhoo.systems import swear
    state = await lock_state(cx.services, cx.chat.id)
    mode = await swear.get_mode(cx.services, cx.chat.id)
    await cx.reply(T.LOCK_PANEL, reply_markup=panel_keyboard(cx.user.id, state, swear_mode=mode))


async def on_panel_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str, arg: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    if action == "x":
        try:
            await msg.delete()
        except TelegramError:
            pass
        return
    chat_id = msg.chat.id
    if await svc.perms.rank_of(bot, chat_id, q.from_user.id) < EDIT_RANK:
        await q.answer(T.LOCK_NEED_RANK, show_alert=True)
        return
    if action == "t" and arg in LOCK_MAP:
        on = not await is_locked(svc, chat_id, arg)
        result = await set_lock(svc, bot, chat_id, arg, on, q.from_user.id)
        if result == "no_rights":
            await q.answer(T.LOCK_CHAT_NEED_RIGHTS.replace(f"{T.BULLET} ", "").replace("<b>", "")
                           .replace("</b>", ""), show_alert=True)
            return
        await q.answer(f"{'🔒' if on else '🔓'} {LOCK_MAP[arg].name}")
    elif action == "s":
        from zhoo.systems import swear
        new = swear.next_mode(await swear.get_mode(svc, chat_id))
        if await svc.perms.rank_of(bot, chat_id, q.from_user.id) < swear.SET_RANK[new]:
            new = "off"  # الكتم والحظر يحتاجون مدير، نرجع للمفتوح
        await swear.set_mode(svc, chat_id, new, q.from_user.id)
        await q.answer(f"{T.SWEAR_LABEL}: {T.SWEAR_MODES[new]}")
    elif action == "a" and arg in ("0", "1"):
        await _set_all(svc, bot, chat_id, arg == "1", q.from_user.id)
        await q.answer(T.BTN_LOCK_ALL if arg == "1" else T.BTN_UNLOCK_ALL)
    else:
        await q.answer()
        return
    from zhoo.systems import swear
    state = await lock_state(svc, chat_id)
    mode = await swear.get_mode(svc, chat_id)
    back = any(b.callback_data and b.callback_data.startswith("st:")
               for row in (msg.reply_markup.inline_keyboard if getattr(msg, "reply_markup", None) else [])
               for b in row)
    try:
        await msg.edit_reply_markup(reply_markup=panel_keyboard(q.from_user.id, state, back=back, swear_mode=mode))
    except BadRequest:
        pass


# ── قفل الرياكت ─────────────────────────────────────
async def on_reaction(update, context) -> None:
    """إذا الرياكت مقفول: نشيل تفاعل أي شخص أقل من مميز."""
    from zhoo.core.context import get_services
    from zhoo.systems.protect import send_notice
    r = update.message_reaction
    if r is None or not r.new_reaction:
        return  # شال تفاعله أو ماكو جديد
    svc = get_services(context)
    chat = r.chat
    if not await is_locked(svc, chat.id, "reactions"):
        return
    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return
    try:
        if r.user is not None:
            if r.user.is_bot or await svc.perms.rank_of(context.bot, chat.id, r.user.id) >= EXEMPT_RANK:
                return
            await context.bot.delete_message_reaction(chat.id, r.message_id, user_id=r.user.id)
        elif r.actor_chat is not None and r.actor_chat.id != chat.id:  # قناة تتفاعل (مو مشرف مخفي)
            await context.bot.delete_message_reaction(chat.id, r.message_id, actor_chat_id=r.actor_chat.id)
            return
        else:
            return
    except TelegramError as e:
        log.info("فشل حذف الرياكت: %s", e)
        return
    if svc.notice_limiter.hit((chat.id, r.user.id)):
        await send_notice(context, chat.id, T.REACTION_NOTICE.format(
            mention=mention(r.user.id, r.user.full_name)), ttl=10)
