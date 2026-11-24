"""المميز المشكوك فيه: «رفع مميز م» (بالرد) ← يصير مميز، بس صوره وملصقاته ومتحركاته وفيديوهاته
تنمسح تلقائياً بعد DELAY ثانية من ما يرسلها.

- «تنزيل مشكوك» ← يشيل الشك ويبقى مميز ⋅ «تنزيل» ← يرجع عضو ويشيل كلشي.
- «المشكوك فيهم» ← القائمة.
"""
from __future__ import annotations

import asyncio
import logging

from telegram import Message
from telegram.error import TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import mention
from zhoo.core.ranks import Rank
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "ranks"
DELAY = 20          # ثواني قبل ما تنمسح الصورة/الملصق
MIN_RANK = Rank.ADMIN


def _key(user_id: int) -> str:
    return f"suspect_{user_id}"


async def is_suspect(svc: Services, chat_id: int, user_id: int) -> bool:
    return await svc.group_settings.get(chat_id, _key(user_id)) == "1"


async def clear(svc: Services, chat_id: int, user_id: int, by: int) -> bool:
    if not await is_suspect(svc, chat_id, user_id):
        return False
    await svc.group_settings.set(chat_id, _key(user_id), "", by)
    return True


def _is_visual(msg: Message) -> bool:
    return bool(msg.photo or msg.sticker or msg.animation or msg.video or msg.video_note)


async def _delete_after(bot, chat_id: int, message_id: int, delay: float) -> None:
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramError:
        pass


async def check(context, svc: Services, msg: Message, chat, user) -> None:
    """صورة/ملصق من مشكوك فيه ← تنمسح بعد DELAY ثانية (الرسالة تبقى ظاهرة شوية)."""
    if not _is_visual(msg) or not await is_suspect(svc, chat.id, user.id):
        return
    jq = getattr(context, "job_queue", None)
    if jq is not None:
        from zhoo.systems.protect import _delete_later
        jq.run_once(_delete_later, DELAY, data=(chat.id, msg.message_id))
    else:
        asyncio.get_running_loop().create_task(_delete_after(context.bot, chat.id, msg.message_id, DELAY))


async def _target(cx: CommandContext, example: str):
    try:
        return await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, example)
        return None


@registry.command("promote_suspect", ("رفع مميز م", "رفع مشكوك", "رفع مشكوك فيه"), section=S,
                  min_rank=MIN_RANK, args="target", usage="بالرد/اليوزر/الايدي", order=17,
                  description=f"مميز مشكوك فيه: صوره وملصقاته تنمسح بعد {DELAY} ثانية")
async def cmd_promote_suspect(cx: CommandContext) -> None:
    from zhoo.systems.ranks import change_rank
    target = await _target(cx, "رفع مميز م @username")
    if target is None:
        return
    svc = cx.services
    if await svc.perms.rank_of(cx.bot, cx.chat.id, target.user_id) != Rank.VIP:
        await change_rank(cx, Rank.VIP)
        if await svc.perms.rank_of(cx.bot, cx.chat.id, target.user_id) != Rank.VIP:
            return   # ما انرفع (رتبته أعلى، أو محمي...) والسبب انكتب
    await svc.group_settings.set(cx.chat.id, _key(target.user_id), "1", cx.user.id)
    await svc.audit.log("suspect_on", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id)
    await cx.reply(T.SUSPECT_ON.format(mention=mention(target.user_id, target.name), n=DELAY))


@registry.command("demote_suspect", ("تنزيل مشكوك", "تنزيل مميز م", "الغاء مشكوك", "الغاء الشك"), section=S,
                  min_rank=MIN_RANK, args="target", usage="بالرد/اليوزر/الايدي", order=18,
                  description="يشيل الشك ويبقى مميز عادي")
async def cmd_demote_suspect(cx: CommandContext) -> None:
    target = await _target(cx, "تنزيل مشكوك @username")
    if target is None:
        return
    who = mention(target.user_id, target.name)
    if not await clear(cx.services, cx.chat.id, target.user_id, cx.user.id):
        await cx.reply(T.SUSPECT_NOT.format(mention=who))
        return
    await cx.services.audit.log("suspect_off", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id)
    await cx.reply(T.SUSPECT_OFF.format(mention=who))


@registry.command("list_suspects", ("المشكوك فيهم", "المشكوكين"), section=S, min_rank=MIN_RANK,
                  description="قائمة المميزين المشكوك فيهم", order=19)
async def cmd_list(cx: CommandContext) -> None:
    rows = await cx.services.db.fetchall(
        "SELECT g.key, u.first_name, u.last_name FROM group_settings g LEFT JOIN users u "
        "ON u.user_id = CAST(substr(g.key, 9) AS INTEGER) WHERE g.chat_id = ? AND g.key LIKE 'suspect_%' "
        "AND g.value = '1'", (cx.chat.id,))
    if not rows:
        await cx.reply(f"{T.SUSPECT_LIST_HEADER}\n{T.SUSPECT_LIST_EMPTY}")
        return
    lines = []
    for i, r in enumerate(rows, 1):
        uid = int(r["key"][len("suspect_"):])
        name = " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(uid)
        lines.append(f"{i}. {mention(uid, name)}")
    await cx.reply(f"{T.SUSPECT_LIST_HEADER}\n" + "\n".join(lines))
