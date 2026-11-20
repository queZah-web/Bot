"""القفل والفتح (الإصدار الثاني): كل قفل إله وضع عقوبة.

الأوضاع: 🗑 مسح (متدرج: بعد 3 مخالفات بنص ساعة كتم ساعة) ⋅ ⚠️ تحذير ⋅ 🔇 كتم ساعة ⋅ ⛓ تقييد ⋅ 👢 طرد
الأوامر: «قفل الصور» ، «قفل الصور بالتقييد» ، «فتح الصور».
الاستثناء حسب نوع القفل: المميز يكدر يرسل الصور والفيديو والملصقات وأشباهها حتى لو مقفولة،
بس الملفات والصوتيات والروابط والتوجيه وغيرها تحتاج أدمن فما فوق (VIP_EXEMPT).

يسد ثغرات مشهورة:
  • التعديل: رسالة عادية تتعدل بعدين وينحط بيها رابط/سب ← تنفحص من جديد.
  • تعديل الميديا: تبديل صورة بعد ما انرسلت.
  • جمثون/اليوزربوت، الفارسي (بدون ما يتأثر الكردي والعراقي)، الإباحي (نص وروابط)، الكلايش، الانلاين.

التخزين: lock_<key> = "0" (مفتوح) أو اسم الوضع. القيمة القديمة "1" تعني «مسح».
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Message, MessageEntity, Update
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes

from zhoo.core import guards
from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.fmt import mention
from zhoo.core.moderation import WARN_ACTIONS
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank

log = logging.getLogger(__name__)
S = "locks"

EDIT_RANK = Rank.ADMIN
EXEMPT_RANK = Rank.ADMIN   # الافتراضي: المشرفين بس يتجاوزون القفل
# أقفال «شكلية» يتجاوزها المميز فما فوق (الملفات والصوتيات والروابط... لا)
VIP_EXEMPT = frozenset({"photos", "videos", "gifs", "stickers", "animated_stickers", "premium_stickers",
                        "premium_emoji", "text", "long", "edit", "edit_media", "reactions"})
MODES_ALL = ("delete", "warn", "mute", "restrict", "kick")
MAX_STRIKES = 3
LOCK_MUTE = 3600


@dataclass(frozen=True)
class Lock:
    key: str
    name: str
    emoji: str
    aliases: tuple[str, ...]
    setting: str
    page: str
    modes: tuple[str, ...] = MODES_ALL
    in_all: bool = True   # يدخل بـ «قفل الكل»


LOCKS: tuple[Lock, ...] = (
    # ── الوسائط
    Lock("photos", "الصور", "🖼", ("صور",), "lock_photos", "media"),
    Lock("videos", "الفيديو", "🎬", ("الفيديوهات", "فيديو"), "lock_videos", "media"),
    Lock("gifs", "المتحركات", "🎞", ("المتحركه", "الجيفات", "الصور المتحركه"), "lock_gifs", "media"),
    Lock("stickers", "الملصقات", "🧸", ("الستيكرات", "ملصقات"), "lock_stickers", "media"),
    Lock("animated_stickers", "الملصقات المتحركة", "🌀", ("الملصقات المتحركه", "الستيكرات المتحركه",
                                                          "الملصقات المتحركة"), "lock_animated_stickers", "media"),
    Lock("premium_stickers", "الملصقات المميزة", "💎", ("الملصقات المميزه", "الستيكرات المميزه",
                                                        "ملصقات البريميوم", "الملصقات البريميوم"),
         "lock_premium_stickers", "media"),
    Lock("voice", "البصمات", "🎙", ("الفويسات", "الصوت", "البصمه"), "lock_voice", "media"),
    Lock("audio", "الصوتيات", "🎵", ("الاغاني", "الموسيقى"), "lock_audio", "media"),
    Lock("files", "الملفات", "📁", ("ملفات",), "lock_files", "media"),
    Lock("contacts", "الجهات", "📇", ("جهات الاتصال",), "lock_contacts", "media"),
    Lock("locations", "المواقع", "📍", ("الموقع",), "lock_locations", "media"),
    Lock("polls", "الاستفتاءات", "📊", ("الاستفتاء", "التصويت"), "lock_polls", "media"),
    # ── المحتوى
    Lock("text", "الكتابة", "✍️", ("الكتابه", "النص"), "lock_text", "content", in_all=False),
    Lock("links", "الروابط", "🔗", ("روابط",), "guard_links", "content"),
    Lock("usernames", "المعرفات", "🆔", ("اليوزرات", "المعرف", "اليوزر"), "lock_usernames", "content"),
    Lock("tag", "التاك", "🏷", ("التاگ", "التاق"), "lock_tag", "content"),
    Lock("forward", "التوجيه", "↪️", ("الفوروارد", "التحويلات"), "guard_forward", "content"),
    Lock("inline", "الانلاين", "🧷", ("الإنلاين", "الانلاين بوت"), "lock_inline", "content"),
    Lock("premium_emoji", "الإيموجي المميز", "✨", ("الايموجي المميز", "الايموجيات المميزه", "الايموجي البريميوم",
                                                   "الإيموجي المميزة"), "lock_premium_emoji", "content"),
    Lock("long", "الكلايش", "📜", ("الكليشه", "الكلايش الطويله", "الرسائل الطويله"), "lock_long", "content"),
    Lock("persian", "الإيرانية", "🇮🇷", ("الايرانيه", "الفارسيه", "الفارسي"), "lock_persian", "content"),
    Lock("porn", "الإباحي", "🔞", ("الاباحي", "الاباحيه"), "lock_porn", "content"),
    Lock("userbot", "جمثون", "🤖", ("اليوزربوت", "السورسات", "الجمثون"), "lock_userbot", "content"),
    # ── السلوك
    Lock("edit", "التعديل", "✏️", ("تعديل الرسائل",), "lock_edit", "behavior", in_all=False),
    Lock("edit_media", "تعديل الميديا", "🖌", ("تعديل الوسائط",), "lock_edit_media", "behavior"),
    Lock("flood", "التكرار", "🌊", ("الاغراق", "الإغراق"), "guard_flood", "behavior", ("delete",), False),
    Lock("reactions", "الرياكت", "❤️", ("الرياكشن", "التفاعلات", "الريأكت", "الرياكتات"), "lock_reactions",
         "behavior", ("delete",)),
    Lock("service", "الإشعارات", "🔔", ("اشعارات الدخول",), "lock_service", "behavior", ("delete",)),
    Lock("join", "الدخول", "🚪", ("دخول الاعضاء",), "lock_join", "behavior", ("kick",), False),
    Lock("bots", "البوتات", "🤖", ("البوت",), "guard_bots", "behavior", ("delete", "kick"), False),
    Lock("chat", "الدردشة", "💬", ("الشات", "المجموعه"), "lock_chat", "behavior", ("delete",), False),
)
LOCK_MAP = {l.key: l for l in LOCKS}
ALL_KEYS = tuple(l.key for l in LOCKS if l.in_all)
MEDIA_ORDER = ("photos", "gifs", "videos", "stickers", "animated_stickers", "premium_stickers", "voice", "audio", "files", "contacts", "locations", "polls")

_MODE_WORDS = {normalize(w): m for w, m in (
    ("بالمسح", "delete"), ("بالحذف", "delete"), ("بالتحذير", "warn"), ("بالانذار", "warn"),
    ("بالكتم", "mute"), ("بالتقييد", "restrict"), ("بالطرد", "kick"))}
_NAME_INDEX: dict[str, Lock] = {}
for _l in LOCKS:
    for _n in (_l.name,) + _l.aliases:
        _NAME_INDEX[normalize(_n)] = _l


def parse_lock(rest: str) -> tuple[Lock, str | None] | None:
    """«الصور بالتقييد» ← (قفل الصور، restrict)"""
    words = normalize(rest).split()
    mode = None
    if words and words[-1] in _MODE_WORDS:
        mode = _MODE_WORDS[words.pop()]
    lock = _NAME_INDEX.get(" ".join(words))
    return (lock, mode) if lock else None


def media_lock(msg: Message) -> str | None:
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


def _has_media(msg: Message) -> bool:
    return media_lock(msg) is not None


# ── الحالة ──────────────────────────────────────────
def _value_to_mode(lock: Lock, value: str) -> str | None:
    if value in ("", "0"):
        return None
    if value == "1" or value not in lock.modes:
        return lock.modes[0]
    return value


async def get_mode(svc: Services, chat_id: int, key: str) -> str | None:
    lock = LOCK_MAP[key]
    return _value_to_mode(lock, await svc.group_settings.get(chat_id, lock.setting))


async def is_locked(svc: Services, chat_id: int, key: str) -> bool:
    return await get_mode(svc, chat_id, key) is not None


async def lock_state(svc: Services, chat_id: int) -> dict[str, str | None]:
    return {l.key: await get_mode(svc, chat_id, l.key) for l in LOCKS}


async def active_count(svc: Services, chat_id: int) -> int:
    from zhoo.systems import swear
    state = await lock_state(svc, chat_id)
    return sum(1 for v in state.values() if v) + await swear.active_scopes(svc, chat_id)


# ── الكشف والتنفيذ ──────────────────────────────────
async def _violations(svc: Services, msg: Message, chat) -> list[str]:
    """الأقفال اللي تخالفها الرسالة، مرتبة من الأخطر."""
    text = msg.text or msg.caption
    found: list[str] = []
    if guards.has_porn(msg):
        found.append("porn")
    if guards.is_persian(text):
        found.append("persian")
    if guards.is_userbot_command(msg.text):
        found.append("userbot")
    if await is_locked(svc, chat.id, "links"):
        from zhoo.systems.protect import whitelist
        if guards.forbidden_links(msg, await whitelist(svc, chat.id), chat.username):
            found.append("links")
    if guards.has_usernames(msg):
        found.append("usernames")
    if guards.has_tag(msg):
        found.append("tag")
    if guards.is_forward(msg):
        found.append("forward")
    if msg.via_bot is not None:
        found.append("inline")
    if guards.is_long(text):
        found.append("long")
    if msg.text:
        found.append("text")
    entities = tuple(msg.entities or ()) + tuple(msg.caption_entities or ())
    if any(e.type == MessageEntity.CUSTOM_EMOJI for e in entities):
        found.append("premium_emoji")
    if msg.sticker:   # الأنواع الخاصة قبل العامة
        if msg.sticker.premium_animation is not None:
            found.append("premium_stickers")
        if msg.sticker.is_animated or msg.sticker.is_video:
            found.append("animated_stickers")
    media = media_lock(msg)
    if media:
        found.append(media)
    return found


async def check(context, svc: Services, msg: Message, chat, user, *, edited: bool = False) -> bool:
    """يرجع True إذا انمسحت الرسالة بسبب قفل."""
    from zhoo.systems import botstate
    if not await botstate.is_active(svc, chat.id):
        return False
    candidates = await _violations(svc, msg, chat)
    if edited:
        candidates = ["edit"] + (["edit_media"] if _has_media(msg) else []) + candidates
    rank = None
    for key in candidates:
        mode = await get_mode(svc, chat.id, key)
        if mode is None:
            continue
        if rank is None:
            rank = await svc.perms.rank_of(context.bot, chat.id, user.id)
        if await _exempt(svc, chat.id, user.id, key, rank):
            continue   # مستثنى من هذا القفل، نشوف باقي المخالفات
        return await enforce(context, svc, msg, chat, user, LOCK_MAP[key], mode)
    return False


def exempt_rank(key: str) -> Rank:
    """أقل رتبة تتجاوز القفل (افتراضياً)."""
    return Rank.VIP if key in VIP_EXEMPT else EXEMPT_RANK


async def _exempt(svc: Services, chat_id: int, user_id: int, key: str, rank: Rank) -> bool:
    """الرتبة + الصلاحيات المخصصة (مثلاً مميز انطوه صلاحية الملفات)."""
    from zhoo.core import capabilities as caps
    cap = caps.LOCK_CAP.get(key)
    default = rank >= exempt_rank(key)
    if cap is None:
        return default
    return await caps.has_cap(svc, chat_id, user_id, cap, default)


async def enforce(context, svc: Services, msg: Message, chat, user, lock: Lock, mode: str) -> bool:
    from zhoo.systems import botstate
    from zhoo.systems.protect import _auto_mute, send_notice
    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False
    try:
        await msg.delete()
    except TelegramError:
        return False
    if await botstate.is_quiet(svc, chat.id):
        return True  # موقوفة: مسح بصمت بس
    await svc.audit.log(f"guard_lock_{lock.key}", chat_id=chat.id, actor_id=context.bot.id, target_id=user.id,
                        details={"mode": mode})
    who = mention(user.id, user.full_name)
    if mode != "delete" and not rights.can_restrict_members:
        mode = "delete"

    if mode == "delete":
        strike = svc.strikes.add((chat.id, user.id))
        if strike >= MAX_STRIKES:
            svc.strikes.reset((chat.id, user.id))
            await _auto_mute(context, svc, chat.id, user, "lock", LOCK_MUTE, rights)
        elif svc.notice_limiter.hit((chat.id, user.id)):
            await send_notice(context, chat.id, T.LOCK_STRIKE_NOTICE.format(
                mention=who, what=lock.name, strike=strike, max=MAX_STRIKES), ttl=15)
        return True

    extra, undo = "", None
    try:
        if mode == "warn":
            limit = await svc.group_settings.get_int(chat.id, "warn_limit")
            count = await svc.punishments.add_warning(chat.id, user.id, context.bot.id, f"قفل {lock.name}")
            extra = T.LOCK_WARNED.format(count=count, limit=limit)
            undo = "w"
            if count >= limit:
                action = await svc.group_settings.get(chat.id, "warn_action")
                action = action if action in WARN_ACTIONS else "mute"
                await mod.apply(context.bot, chat.id, user.id, action, None)
                await svc.punishments.add(chat.id, user.id, action, context.bot.id, T.WARN_AUTO_REASON, None)
                await svc.punishments.clear_warnings(chat.id, user.id)
                extra += T.WARN_LIMIT_REACHED.format(action=WARN_ACTIONS[action])
                undo = {"mute": "m", "ban": "b"}.get(action)
        elif mode in ("mute", "restrict"):
            until = int(time.time()) + LOCK_MUTE if mode == "mute" else None
            await mod.apply(context.bot, chat.id, user.id, mode, until)
            await svc.punishments.add(chat.id, user.id, mode, context.bot.id, f"قفل {lock.name}", until)
            extra = T.PUNISH_DURATION.format(duration="ساعة") if until else T.PUNISH_FOREVER
            undo = "m" if mode == "mute" else "r"
        elif mode == "kick":
            await mod.apply(context.bot, chat.id, user.id, "kick", None)
            await svc.punishments.add(chat.id, user.id, "kick", context.bot.id, f"قفل {lock.name}", None)
    except (BadRequest, Forbidden) as e:
        log.info("فشلت عقوبة القفل: %s", e)
        return True
    head, emoji = T.PUNISH_TITLES[mode]
    kb = None
    if undo:
        label = {"w": T.BTN_UNDO_WARN, "m": T.BTN_UNDO_MUTE, "r": T.BTN_UNDO_RESTRICT, "b": T.BTN_UNDO_BAN}[undo]
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=f"p:{undo}:{user.id}")]])
    await send_notice(context, chat.id, T.LOCK_PUNISHED.format(head=head, emoji=emoji, mention=who,
                                                               what=lock.name, extra=extra),
                      ttl=0 if kb else 30, reply_markup=kb)
    return True


async def on_edited(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """الرسائل المعدّلة: السب + قفل التعديل + كل أقفال المحتوى (حتى ما ينحط رابط بالتعديل)."""
    from zhoo.systems import swear
    msg, chat, user = update.edited_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None or user.is_bot or msg.sender_chat is not None:
        return
    svc = get_services(context)
    if await swear.check(context, svc, msg, chat, user):
        return
    await check(context, svc, msg, chat, user, edited=True)


# ── تغيير الأقفال ───────────────────────────────────
_OPEN_CHAT = ChatPermissions(
    can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True,
    can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True,
    can_send_other_messages=True, can_add_web_page_previews=True, can_invite_users=True,
    can_change_info=False, can_pin_messages=False, can_manage_topics=False,
    can_react_to_messages=True,
)


async def set_mode(svc: Services, bot, chat_id: int, key: str, mode: str | None, by: int) -> str:
    """يغير القفل. يرجع: ok | same | no_rights | bad_mode"""
    lock = LOCK_MAP[key]
    if mode is not None and mode not in lock.modes:
        return "bad_mode"
    if await get_mode(svc, chat_id, key) == mode:
        return "same"
    if key == "chat":
        rights = await svc.perms.bot_rights(bot, chat_id)
        if rights is None or not rights.can_restrict_members:
            return "no_rights"
        try:
            await bot.set_chat_permissions(chat_id, ChatPermissions.no_permissions() if mode else _OPEN_CHAT)
        except TelegramError as e:
            log.info("فشل تغيير صلاحيات الدردشة: %s", e)
            return "no_rights"
    value = mode or "0"
    if lock.setting.startswith("guard_") and mode == lock.modes[0]:
        value = "1"  # خيارات الحماية تبقى متوافقة ويا لوحة الحماية
    old = await svc.group_settings.set(chat_id, lock.setting, value, by)
    await svc.audit.log("lock" if mode else "unlock", chat_id=chat_id, actor_id=by,
                        details={"key": key, "mode": mode, "from": old})
    return "ok"


async def set_lock(svc: Services, bot, chat_id: int, key: str, on: bool, by: int) -> str:
    """توافق مع الكود القديم: تشغيل = أول وضع."""
    return await set_mode(svc, bot, chat_id, key, LOCK_MAP[key].modes[0] if on else None, by)


def _mode_name(mode: str) -> str:
    icon, name = T.LOCK_MODES[mode]
    return f"{icon} {name}"


def _accept_lock(rest: str) -> bool:
    return parse_lock(rest) is not None


@registry.command("lock_one", ("قفل",), section=S, min_rank=EDIT_RANK, usage="النوع + الوضع (اختياري)",
                  accept=_accept_lock, description="يقفل نوع: «قفل الصور» أو «قفل الصور بالتقييد»", order=4)
async def cmd_lock(cx: CommandContext) -> None:
    parsed = parse_lock(cx.raw_args) if cx.raw_args.strip() else None
    if parsed is None:
        await cx.reply(T.HELP_LOCK_TYPES.strip())
        return
    lock, mode = parsed
    mode = mode or lock.modes[0]
    what = f"{lock.emoji} {lock.name}"
    result = await set_mode(cx.services, cx.bot, cx.chat.id, lock.key, mode, cx.user.id)
    if result == "bad_mode":
        await cx.reply(T.LOCK_MODE_NOT_ALLOWED.format(modes=" ، ".join(_mode_name(m) for m in lock.modes)))
    elif result == "same":
        await cx.reply(T.ALREADY_LOCKED_MODE.format(what=lock.name, mode=_mode_name(mode)))
    elif result == "no_rights":
        await cx.reply(T.LOCK_CHAT_NEED_RIGHTS)
    else:
        text = T.LOCKED_MODE.format(what=what, mode=_mode_name(mode), actor=mention(cx.user.id, cx.user.full_name))
        rights = await cx.services.perms.bot_rights(cx.bot, cx.chat.id)
        if lock.key != "chat" and (rights is None or not rights.can_delete_messages):
            text += "\n" + T.LOCK_NEED_RIGHTS
        await cx.reply(text)


@registry.command("unlock_one", ("فتح",), section=S, min_rank=EDIT_RANK, usage="النوع",
                  accept=_accept_lock, description="يفتح نوع، مثل: فتح الصور", order=5)
async def cmd_unlock(cx: CommandContext) -> None:
    parsed = parse_lock(cx.raw_args) if cx.raw_args.strip() else None
    if parsed is None:
        await cx.reply(T.HELP_LOCK_TYPES.strip())
        return
    lock = parsed[0]
    result = await set_mode(cx.services, cx.bot, cx.chat.id, lock.key, None, cx.user.id)
    if result == "same":
        await cx.reply(T.ALREADY_UNLOCKED.format(what=lock.name))
    elif result == "no_rights":
        await cx.reply(T.LOCK_CHAT_NEED_RIGHTS)
    else:
        await cx.reply(T.UNLOCKED.format(what=f"{lock.emoji} {lock.name}",
                                         actor=mention(cx.user.id, cx.user.full_name)))


async def _set_all(svc: Services, bot, chat_id: int, on: bool, by: int) -> int:
    from zhoo.systems import swear
    changed = 0
    for key in ALL_KEYS:
        if await set_lock(svc, bot, chat_id, key, on, by) == "ok":
            changed += 1
    for scope, mode in (await swear.get_modes(svc, chat_id)).items():
        if on and mode == "off":
            await swear.set_mode(svc, chat_id, "smart", by, scope)
        elif not on and mode != "off":
            await swear.set_mode(svc, chat_id, "off", by, scope)
    return changed


@registry.command("lock_all", ("قفل الكل",), section=S, min_rank=EDIT_RANK,
                  description="يقفل الوسائط والمحتوى المزعج (عدا الكتابة والدردشة والدخول)", order=2)
async def cmd_lock_all(cx: CommandContext) -> None:
    await _set_all(cx.services, cx.bot, cx.chat.id, True, cx.user.id)
    await cx.reply(T.LOCKED.format(what=T.ALL_TYPES, actor=mention(cx.user.id, cx.user.full_name)))


@registry.command("unlock_all", ("فتح الكل",), section=S, min_rank=EDIT_RANK,
                  description="يفتح كل اللي انقفل بـ «قفل الكل»", order=3)
async def cmd_unlock_all(cx: CommandContext) -> None:
    await _set_all(cx.services, cx.bot, cx.chat.id, False, cx.user.id)
    await cx.reply(T.UNLOCKED.format(what=T.ALL_TYPES, actor=mention(cx.user.id, cx.user.full_name)))


# ── لوحة الأقفال (3 صفحات) ──────────────────────────
def _next_mode(lock: Lock, current: str | None) -> str | None:
    cycle = (None,) + lock.modes
    return cycle[(cycle.index(current) + 1) % len(cycle)] if current in cycle else lock.modes[0]


async def panel_view(svc: Services, chat_id: int, uid: int, page: str = "media",
                     back: bool = False) -> tuple[str, InlineKeyboardMarkup]:
    from zhoo.systems import swear
    state = await lock_state(svc, chat_id)
    B = InlineKeyboardButton
    tabs = [B(("• " if p == page else "") + label, callback_data=f"l:{uid}:p:{p}") for p, label in T.LOCK_PAGES.items()]
    buttons = []
    for l in LOCKS:
        if l.page != page:
            continue
        mode = state[l.key]
        icon = T.LOCK_MODES[mode][0] if mode else "🔓"
        buttons.append(B(f"{icon} {l.name}", callback_data=f"l:{uid}:t:{l.key}"))
    rows = [tabs] + [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    if page == "content":
        modes = await swear.get_modes(svc, chat_id)
        rows.append([B(T.SWEAR_BTN_SCOPE[sc].format(mode=T.SWEAR_MODES[modes[sc]]),
                       callback_data=f"l:{uid}:s:{sc[0]}") for sc in swear.SCOPES])
    rows.append([B(T.BTN_LOCK_ALL, callback_data=f"l:{uid}:a:1"), B(T.BTN_UNLOCK_ALL, callback_data=f"l:{uid}:a:0")])
    last = [B(T.BTN_CLOSE, callback_data=f"l:{uid}:x:-")]
    if back:
        last.insert(0, B(T.BTN_BACK, callback_data=f"st:{uid}:home:-"))
    rows.append(last)
    text = T.LOCK_PANEL_V2.format(page=T.LOCK_PAGES[page], count=await active_count(svc, chat_id))
    return text, InlineKeyboardMarkup(rows)


@registry.command("locks_status", ("حالة الاقفال", "حالة الأقفال", "الممنوعات", "المقفول", "شنو المقفول",
                                  "حالة المجموعه"), section=S, min_rank=Rank.MEMBER, order=0,
                  description="يعرض شنو موقوف وشنو مسموح بالمجموعة")
async def cmd_status(cx: CommandContext) -> None:
    from zhoo.systems import features, swear
    svc, chat_id = cx.services, cx.chat.id
    state = await lock_state(svc, chat_id)
    locked, opened = [], []
    for page in T.LOCK_PAGES:
        for l in LOCKS:
            if l.page != page:
                continue
            mode = state[l.key]
            if mode:
                icon, name = T.LOCK_MODES[mode]
                locked.append(T.LOCK_STATUS_LOCKED_ITEM.format(
                    emoji=l.emoji, name=l.name, mode=f"{icon} {name}",
                    vip=T.LOCK_STATUS_VIP_MARK if l.key in VIP_EXEMPT else ""))
            else:
                opened.append(f"{l.emoji} {l.name}")
    modes = await swear.get_modes(svc, chat_id)
    off = [f.name for f in features.FEATURES if not await features.enabled(svc, chat_id, f.key)]
    out = [T.LOCK_STATUS_HEADER, T.LOCK_STATUS_LOCKED_HEAD, *(locked or [T.LOCK_STATUS_NONE_LOCKED])]
    if opened:
        out += ["", T.LOCK_STATUS_OPEN_HEAD, "  " + " ⋅ ".join(opened)]
    out += ["", T.LOCK_STATUS_SWEAR.format(summary=T.SWEAR_SUMMARY.format(
        vulgar=T.SWEAR_MODES[modes["vulgar"]], insult=T.SWEAR_MODES[modes["insult"]]))]
    if off:
        out.append(T.LOCK_STATUS_FEATURES_OFF.format(names=" ⋅ ".join(off)))
    out += [T.LINE, T.LOCK_STATUS_FOOTER]
    await cx.reply("\n".join(out))


@registry.command("locks_panel", ("الاقفال", "الأقفال"), section=S, min_rank=EDIT_RANK,
                  description="لوحة الأقفال بالأزرار (3 صفحات)", order=1)
async def cmd_panel(cx: CommandContext) -> None:
    text, kb = await panel_view(cx.services, cx.chat.id, cx.user.id)
    await cx.reply(text, reply_markup=kb)


def _current_page(msg) -> str:
    markup = getattr(msg, "reply_markup", None)
    if markup:
        for b in markup.inline_keyboard[0]:
            if b.text.startswith("• ") and b.callback_data:
                return b.callback_data.split(":")[-1]
    return "media"


def _has_back(msg) -> bool:
    markup = getattr(msg, "reply_markup", None)
    return bool(markup) and any(b.callback_data and b.callback_data.startswith("st:")
                                for row in markup.inline_keyboard for b in row)


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
    chat_id, uid = msg.chat.id, q.from_user.id
    page = _current_page(msg)
    if action == "p" and arg in T.LOCK_PAGES:
        page = arg
        await q.answer(T.LOCK_PAGES[arg])
    elif await svc.perms.rank_of(bot, chat_id, uid) < EDIT_RANK:
        await q.answer(T.LOCK_NEED_RANK, show_alert=True)
        return
    elif action == "t" and arg in LOCK_MAP:
        lock = LOCK_MAP[arg]
        new = _next_mode(lock, await get_mode(svc, chat_id, arg))
        if await set_mode(svc, bot, chat_id, arg, new, uid) == "no_rights":
            await q.answer(T.LOCK_CHAT_NEED_RIGHTS.replace(f"{T.BULLET} ", "").replace("<b>", "")
                           .replace("</b>", ""), show_alert=True)
            return
        await q.answer(f"{lock.name}: {_mode_name(new) if new else '🔓'}")
    elif action == "s":
        from zhoo.systems import swear
        scope = "insult" if arg == "i" else "vulgar"
        new = swear.next_mode(await swear.get_mode(svc, chat_id, scope))
        if await svc.perms.rank_of(bot, chat_id, uid) < swear.SET_RANK[new]:
            new = "off"
        await swear.set_mode(svc, chat_id, new, uid, scope)
        await q.answer(T.SWEAR_BTN_SCOPE[scope].format(mode=T.SWEAR_MODES[new]))
    elif action == "a" and arg in ("0", "1"):
        await _set_all(svc, bot, chat_id, arg == "1", uid)
        await q.answer(T.BTN_LOCK_ALL if arg == "1" else T.BTN_UNLOCK_ALL)
    else:
        await q.answer()
        return
    text, kb = await panel_view(svc, chat_id, uid, page, back=_has_back(msg))
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass


# ── قفل الرياكت ─────────────────────────────────────
async def on_reaction(update, context) -> None:
    from zhoo.systems import botstate
    from zhoo.systems.protect import send_notice
    r = update.message_reaction
    if r is None or not r.new_reaction:
        return
    svc = get_services(context)
    chat = r.chat
    if not await botstate.is_active(svc, chat.id) or not await is_locked(svc, chat.id, "reactions"):
        return
    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return
    try:
        if r.user is not None:
            if r.user.is_bot or await _exempt(svc, chat.id, r.user.id, "reactions",
                                              await svc.perms.rank_of(context.bot, chat.id, r.user.id)):
                return
            await context.bot.delete_message_reaction(chat.id, r.message_id, user_id=r.user.id)
        elif r.actor_chat is not None and r.actor_chat.id != chat.id:
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

