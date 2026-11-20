"""الاشتراك الإجباري: العضو لازم يشترك بقناة (أو أكثر) حتى يكتب بالمجموعة.

- «اضف قناه @channel» ← زهو تتأكد إنها قناة، وإنها مشرفة بيها (حتى تكدر تشوف المشتركين).
- رسالة غير المشترك تنمسح، وتطلع رسالة وحدة بأزرار: «📢 القناة» + «✅ اشتركت».
- المشرفين (أدمن فما فوق) مستثنين.
- نتيجة الفحص تنحفظ بالذاكرة (المشترك 10 دقايق، غير المشترك 20 ثانية) حتى ما نثقل على تيليجرام.
- إذا صار خلل بفحص قناة (زهو انشالت منها مثلاً) نعتبر العضو مشترك — ما نسكت المجموعة بسبب خلل.
"""
from __future__ import annotations

import json
import logging
import re
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ChatMemberStatus, ChatType
from telegram.error import TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import Rank

log = logging.getLogger(__name__)
S = "protect"

SETTING = "force_channels"
MAX_CHANNELS = 3
EDIT_RANK = Rank.MANAGER
VIEW_RANK = Rank.ADMIN
EXEMPT_RANK = Rank.ADMIN
OK_TTL = 600
BAD_TTL = 20
_MEMBER = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
_LINK_RE = re.compile(r"^(?:https?://)?t\.me/([A-Za-z0-9_]{4,})/?$")


# ── التخزين ─────────────────────────────────────────
async def load(svc: Services, chat_id: int) -> list[dict]:
    raw = await svc.group_settings.get(chat_id, SETTING)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [c for c in data if isinstance(c, dict) and isinstance(c.get("id"), int)]
    except (ValueError, TypeError):
        return []


async def _save(svc: Services, chat_id: int, channels: list[dict], by: int) -> None:
    await svc.group_settings.set(chat_id, SETTING, json.dumps(channels, ensure_ascii=False) if channels else "", by)


# ── الفحص ───────────────────────────────────────────
async def _is_member(bot, svc: Services, channel_id: int, user_id: int, *, fresh: bool = False) -> bool:
    key = (channel_id, user_id)
    hit = svc.fsub_cache.get(key)
    if hit is not None and not fresh and time.monotonic() - hit[1] < (OK_TTL if hit[0] else BAD_TTL):
        return hit[0]
    try:
        m = await bot.get_chat_member(channel_id, user_id)
        ok = m.status in _MEMBER or (m.status == ChatMemberStatus.RESTRICTED and getattr(m, "is_member", False))
    except TelegramError as e:
        log.info("فشل فحص الاشتراك بالقناة %s: %s", channel_id, e)
        ok = True  # خلل بالفحص: ما نعاقب العضو
    if len(svc.fsub_cache) > 50_000:
        svc.fsub_cache.clear()
    svc.fsub_cache[key] = (ok, time.monotonic())
    return ok


async def missing(bot, svc: Services, chat_id: int, user_id: int, *, fresh: bool = False) -> list[dict]:
    return [c for c in await load(svc, chat_id) if not await _is_member(bot, svc, c["id"], user_id, fresh=fresh)]


def _keyboard(channels: list[dict], user_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(T.FSUB_BTN_JOIN.format(title=c["title"][:40]), url=c["link"])]
            for c in channels if c.get("link")]
    rows.append([InlineKeyboardButton(T.FSUB_BTN_CHECK, callback_data=f"fs:{user_id}")])
    return InlineKeyboardMarkup(rows)


async def check(context, svc: Services, msg: Message, chat, user) -> bool:
    """يرجع True إذا انمسحت الرسالة لأن العضو مو مشترك."""
    if not await svc.group_settings.get(chat.id, SETTING):
        return False
    from zhoo.systems import botstate
    if not await botstate.is_active(svc, chat.id) or await botstate.is_quiet(svc, chat.id):
        return False
    if await svc.perms.rank_of(context.bot, chat.id, user.id) >= EXEMPT_RANK:
        return False
    lacking = await missing(context.bot, svc, chat.id, user.id)
    if not lacking:
        return False
    rights = await svc.perms.bot_rights(context.bot, chat.id)
    if rights is None or not rights.can_delete_messages:
        return False
    try:
        await msg.delete()
    except TelegramError:
        return False
    if svc.notice_limiter.hit(("fsub", chat.id, user.id)):
        from zhoo.systems.protect import send_notice
        await send_notice(context, chat.id, T.FSUB_NOTICE.format(mention=mention(user.id, user.full_name)),
                          ttl=60, reply_markup=_keyboard(lacking, user.id))
    return True


async def on_button(q, msg: Message, svc: Services, bot, uid_raw: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.FSUB_NOT_YOURS, show_alert=True)
        return
    if await missing(bot, svc, msg.chat.id, q.from_user.id, fresh=True):
        await q.answer(T.FSUB_NOT_YET, show_alert=True)
        return
    await q.answer(T.FSUB_OK, show_alert=True)
    try:
        await msg.delete()
    except TelegramError:
        pass


# ── الأوامر ─────────────────────────────────────────
def _channel_ref(raw: str) -> str | int | None:
    raw = raw.strip()
    m = _LINK_RE.match(raw)
    if m:
        return "@" + m.group(1)
    if raw.startswith("@") and len(raw) > 4:
        return raw
    if raw.lstrip("-").isdigit():
        return int(raw)
    return None


@registry.command("fsub_add", ("اضف قناه", "اضف قناة", "اضافة قناة", "إضافة قناة", "اضافه قناه"), section=S,
                  min_rank=EDIT_RANK, args="text", usage="@يوزر_القناة أو ايديها",
                  description="اشتراك إجباري: الأعضاء لازم يشتركون بالقناة حتى يكتبون", order=20)
async def cmd_add(cx: CommandContext) -> None:
    svc = cx.services
    ref = _channel_ref(cx.args[0]) if cx.args else None
    if ref is None:
        await cx.reply(T.FSUB_NEED_ARG)
        return
    channels = await load(svc, cx.chat.id)
    if len(channels) >= MAX_CHANNELS:
        await cx.reply(T.FSUB_LIMIT.format(n=MAX_CHANNELS))
        return
    try:
        ch = await cx.bot.get_chat(ref)
    except TelegramError:
        await cx.reply(T.FSUB_BAD_CHANNEL)
        return
    if ch.type != ChatType.CHANNEL:
        await cx.reply(T.FSUB_NOT_CHANNEL)
        return
    if any(c["id"] == ch.id for c in channels):
        await cx.reply(T.FSUB_EXISTS)
        return
    try:
        me = await cx.bot.get_chat_member(ch.id, cx.bot.id)
        is_admin = me.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except TelegramError:
        is_admin = False
    if not is_admin:
        await cx.reply(T.FSUB_BOT_NOT_ADMIN)
        return
    link = f"https://t.me/{ch.username}" if ch.username else getattr(ch, "invite_link", None)
    if not link:
        try:
            link = await cx.bot.export_chat_invite_link(ch.id)
        except TelegramError:
            await cx.reply(T.FSUB_NO_LINK)
            return
    channels.append({"id": ch.id, "title": (ch.title or str(ch.id))[:60], "link": link})
    await _save(svc, cx.chat.id, channels, cx.user.id)
    await svc.audit.log("fsub_add", chat_id=cx.chat.id, actor_id=cx.user.id, details={"channel": ch.id})
    await cx.reply(T.FSUB_ADDED.format(title=esc(ch.title or str(ch.id))))


@registry.command("fsub_remove", ("حذف قناه", "حذف قناة", "مسح قناه", "مسح قناة"), section=S, min_rank=EDIT_RANK,
                  args="text", usage="@يوزر_القناة أو ايديها", description="يشيل قناة من الاشتراك الإجباري",
                  order=21)
async def cmd_remove(cx: CommandContext) -> None:
    svc = cx.services
    channels = await load(svc, cx.chat.id)
    raw = cx.raw_args.strip()
    ref = _channel_ref(raw) if raw else None
    target = None
    if ref is None and not raw and len(channels) == 1:
        target = channels[0]
    for c in channels:
        if target is not None:
            break
        if isinstance(ref, int) and c["id"] == ref:
            target = c
        elif isinstance(ref, str) and c.get("link", "").lower().endswith("/" + ref[1:].lower()):
            target = c
        elif raw and c["title"] == raw:
            target = c
    if target is None:
        await cx.reply(T.FSUB_NOT_FOUND if channels else T.FSUB_LIST_EMPTY)
        return
    channels.remove(target)
    await _save(svc, cx.chat.id, channels, cx.user.id)
    await svc.audit.log("fsub_remove", chat_id=cx.chat.id, actor_id=cx.user.id, details={"channel": target["id"]})
    await cx.reply(T.FSUB_REMOVED.format(title=esc(target["title"])))


@registry.command("fsub_clear", ("مسح القنوات", "حذف القنوات", "تعطيل الاشتراك الاجباري", "تعطيل الاشتراك الإجباري"),
                  section=S, min_rank=EDIT_RANK, description="يطفي الاشتراك الإجباري كله", order=22)
async def cmd_clear(cx: CommandContext) -> None:
    await _save(cx.services, cx.chat.id, [], cx.user.id)
    await cx.services.audit.log("fsub_clear", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.FSUB_CLEARED)


@registry.command("fsub_list", ("القنوات", "قنوات الاشتراك", "الاشتراك الاجباري", "الاشتراك الإجباري"), section=S,
                  min_rank=VIEW_RANK, description="قنوات الاشتراك الإجباري", order=23)
async def cmd_list(cx: CommandContext) -> None:
    channels = await load(cx.services, cx.chat.id)
    if not channels:
        await cx.reply(f"{T.FSUB_LIST_HEADER}\n{T.FSUB_LIST_EMPTY}")
        return
    items = [T.FSUB_LIST_ITEM.format(link=esc(c.get("link") or ""), title=esc(c["title"]), id=c["id"])
             for c in channels]
    await cx.reply(f"{T.FSUB_LIST_HEADER}\n" + "\n".join(items))
