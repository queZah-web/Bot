"""مراقبة «ش» (شك) — ميزة مخفية لصاحب المجموعة.

صاحب المجموعة (أو مطور زهو) يرد على أي مشرف/مالك بحرف «ش» ← «تم التفعيل».
بعدها إذا هذا الشخص طرد أو حظر 3 أعضاء خلال أقل من 10 دقايق (بأوامر زهو أو من تيليجرام نفسه):
  • تنزل رتبته لعضو وتنسحب صلاحياته (وإشراف تيليجرام إذا زهو رفعته)
  • زهو تسوي تاگ لصاحب المجموعة للتحقيق
  • محد يكدر يرجّع رتبته غير صاحب المجموعة
«ش» مرة ثانية على نفس الشخص ← توقف المراقبة. الأمر ما يطلع بالقوائم، وما يرد على غير صاحب المجموعة.
"""
from __future__ import annotations

import time

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import mention
from zhoo.core.ranks import Rank

S = "ranks"
WINDOW = 10 * 60
THRESHOLD = 3


def _watch_key(user_id: int) -> str:
    return f"watch_{user_id}"


def _lock_key(user_id: int) -> str:
    return f"suspended_{user_id}"


async def is_locked(svc: Services, chat_id: int, user_id: int) -> bool:
    return await svc.group_settings.get(chat_id, _lock_key(user_id)) == "1"


async def unlock(svc: Services, chat_id: int, user_id: int, by: int) -> None:
    if await is_locked(svc, chat_id, user_id):
        await svc.group_settings.set(chat_id, _lock_key(user_id), "", by)


async def _can_use(cx: CommandContext) -> bool:
    return cx.services.perms.is_developer(cx.user.id) or cx.rank >= Rank.CREATOR


@registry.command("watch_toggle", ("ش",), section=S, show_in_help=False, order=99,
                  description="مخفي: مراقبة مشرف (صاحب المجموعة بس)")
async def cmd_watch(cx: CommandContext) -> None:
    reply = cx.message.reply_to_message
    if not await _can_use(cx) or reply is None or reply.from_user is None or reply.from_user.is_bot:
        return   # مخفي: ولا رد
    target = reply.from_user
    if target.id == cx.user.id:
        return
    svc = cx.services
    on = await svc.group_settings.get(cx.chat.id, _watch_key(target.id)) != "1"
    await svc.group_settings.set(cx.chat.id, _watch_key(target.id), "1" if on else "", cx.user.id)
    svc.watch_hits.pop((cx.chat.id, target.id), None)
    await svc.audit.log("watch_on" if on else "watch_off", chat_id=cx.chat.id, actor_id=cx.user.id,
                        target_id=target.id)
    await cx.reply(T.WATCH_ON if on else T.WATCH_OFF)


async def record(bot, svc: Services, chat_id: int, actor_id: int) -> bool:
    """ينادى بعد كل طرد/حظر. يرجع True إذا انطبق الإجراء."""
    if await svc.group_settings.get(chat_id, _watch_key(actor_id)) != "1":
        return False
    now = time.monotonic()
    hits = [t for t in svc.watch_hits.get((chat_id, actor_id), []) if now - t < WINDOW] + [now]
    svc.watch_hits[(chat_id, actor_id)] = hits
    if len(hits) < THRESHOLD:
        return False
    svc.watch_hits.pop((chat_id, actor_id), None)
    await _strip(bot, svc, chat_id, actor_id, len(hits))
    return True


async def _strip(bot, svc: Services, chat_id: int, actor_id: int, count: int) -> None:
    from zhoo.systems.ranks import tg_demote
    if await svc.perms.rank_of(bot, chat_id, actor_id) >= Rank.CREATOR:
        return   # صاحب المجموعة والمطور ما ينزلون
    await svc.members.set_rank(chat_id, actor_id, Rank.MEMBER, bot.id)
    await svc.member_perms.clear(chat_id, actor_id)
    await tg_demote(bot, svc, chat_id, actor_id)
    await svc.group_settings.set(chat_id, _lock_key(actor_id), "1", bot.id)
    await svc.audit.log("watch_triggered", chat_id=chat_id, actor_id=bot.id, target_id=actor_id,
                        details={"count": count})
    user = await svc.users.get(actor_id)
    who = mention(actor_id, user.full_name if user else str(actor_id))
    owners = [m.user for m in (await svc.perms.admins(bot, chat_id)).values()
              if getattr(m, "status", "") == "creator" and not getattr(m, "is_anonymous", False)]
    tag = " ".join(mention(u.id, u.full_name) for u in owners) or T.WATCH_NO_OWNER
    try:
        await bot.send_message(chat_id, T.WATCH_ALERT.format(actor=who, n=count, owner=tag))
    except Exception:  # noqa: BLE001 — التنبيه ما لازم يكسر شي
        pass
