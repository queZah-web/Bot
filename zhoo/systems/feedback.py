"""الاقتراحات (بتصويت وقرار الإدارة) والشكاوى (سرية، توصل للإدارة بالخاص)."""
from __future__ import annotations

import logging
import time

from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup, Message
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration, esc, mention
from zhoo.core.ranks import Rank

log = logging.getLogger(__name__)
S = "social"

SUGG_COOLDOWN = 5 * 60
COMPLAINT_COOLDOWN = 10 * 60
STAFF_RANK = Rank.ADMIN          # قرار الاقتراحات
COMPLAINT_RANK = Rank.MANAGER    # استلام وحل الشكاوى
MIN_LEN, MAX_LEN = 5, 1000


def _name(row) -> str:
    return " ".join(p for p in (row["first_name"], row["last_name"]) if p) or str(row["user_id"])


# ── الاقتراحات ──────────────────────────────────────
async def suggestion_view(svc: Services, sid: int, actor: str | None = None):
    row = await svc.social.get_suggestion(sid)
    if row is None:
        return None, None
    up, down = await svc.social.votes(sid)
    text = T.SUGGESTION.format(
        id=sid, mention=mention(row["user_id"], _name(row)), text=esc(row["text"]),
        status=T.SUGG_STATUS[row["status"]], up=up, down=down,
        decided=T.SUGG_DECIDED.format(actor=actor) if actor else "")
    rows = [[B(f"👍 {up}", callback_data=f"sg:{sid}:u"), B(f"👎 {down}", callback_data=f"sg:{sid}:d")]]
    if row["status"] in ("new", "review"):
        rows.append([B(T.BTN_SUGG_REVIEW, callback_data=f"sg:{sid}:r"),
                     B(T.BTN_SUGG_ACCEPT, callback_data=f"sg:{sid}:a"),
                     B(T.BTN_SUGG_REJECT, callback_data=f"sg:{sid}:x")])
    return text, InlineKeyboardMarkup(rows)


@registry.command("suggest", ("اقتراح", "اقترح"), section=S, args="text", usage="نص الاقتراح",
                  description="اقتراح للمجموعة، الأعضاء يصوتون والإدارة تقرر", order=30)
async def cmd_suggest(cx: CommandContext) -> None:
    text = cx.raw_args.strip()
    if not MIN_LEN <= len(text) <= MAX_LEN:
        await cx.reply(T.SUGG_BAD)
        return
    svc = cx.services
    last = await svc.social.last_suggestion_at(cx.chat.id, cx.user.id)
    if last and time.time() - last < SUGG_COOLDOWN and cx.rank < STAFF_RANK:
        await cx.reply(T.SUGG_WAIT.format(left=duration(SUGG_COOLDOWN - (time.time() - last))))
        return
    sid = await svc.social.add_suggestion(cx.chat.id, cx.user.id, text)
    await svc.audit.log("suggestion", chat_id=cx.chat.id, actor_id=cx.user.id, details={"id": sid})
    view, kb = await suggestion_view(svc, sid)
    await cx.reply(view, reply_markup=kb)


async def on_suggestion_button(q, msg: Message, svc: Services, bot, sid_raw: str, action: str) -> None:
    if not sid_raw.isdigit():
        await q.answer(T.SUGG_GONE)
        return
    sid = int(sid_raw)
    row = await svc.social.get_suggestion(sid)
    if row is None or row["chat_id"] != msg.chat.id:
        await q.answer(T.SUGG_GONE, show_alert=True)
        return
    actor = None
    if action in ("u", "d"):
        result = await svc.social.vote(sid, q.from_user.id, 1 if action == "u" else -1)
        await q.answer(T.SUGG_VOTED[result])
    elif action in ("r", "a", "x"):
        if await svc.perms.rank_of(bot, msg.chat.id, q.from_user.id) < STAFF_RANK:
            await q.answer(T.SUGG_NEED_STAFF, show_alert=True)
            return
        status = {"r": "review", "a": "accepted", "x": "rejected"}[action]
        await svc.social.set_suggestion_status(sid, status, q.from_user.id)
        await svc.audit.log("suggestion_status", chat_id=msg.chat.id, actor_id=q.from_user.id,
                            details={"id": sid, "status": status})
        actor = mention(q.from_user.id, q.from_user.full_name)
        await q.answer(T.SUGG_STATUS[status])
    else:
        await q.answer()
        return
    if actor is None and row["decided_by"]:
        u = await svc.users.get(row["decided_by"])
        actor = mention(row["decided_by"], u.full_name if u else str(row["decided_by"]))
    view, kb = await suggestion_view(svc, sid, actor)
    try:
        await msg.edit_text(view, reply_markup=kb)
    except BadRequest:
        pass


@registry.command("suggestions", ("الاقتراحات",), section=S, description="آخر الاقتراحات وحالتها", order=31)
async def cmd_suggestions(cx: CommandContext) -> None:
    rows = await cx.services.social.recent_suggestions(cx.chat.id)
    if not rows:
        await cx.reply(f"{T.SUGG_LIST_HEADER}\n{T.SUGG_LIST_EMPTY}")
        return
    lines = []
    for r in rows:
        txt = r["text"] if len(r["text"]) <= 80 else r["text"][:80] + "…"
        lines.append(f"▫️ <b>#{r['id']}</b> {T.SUGG_STATUS[r['status']]} ⋅ 👍 {r['up']} ⋅ 👎 {r['down']}\n"
                     f"    {mention(r['user_id'], _name(r))}: <i>{esc(txt)}</i>")
    await cx.reply(f"{T.SUGG_LIST_HEADER}\n" + "\n".join(lines))


# ── الشكاوى ─────────────────────────────────────────
async def _complaint_recipients(svc: Services, bot, chat_id: int, exclude: int) -> set[int]:
    ids: set[int] = set()
    for m in (await svc.perms.admins(bot, chat_id)).values():
        if m.status == ChatMemberStatus.OWNER and not m.user.is_bot:
            ids.add(m.user.id)
    for r in await svc.members.list_ranked(chat_id):
        if r["rank"] >= COMPLAINT_RANK:
            ids.add(r["user_id"])
    ids.discard(exclude)
    return ids


@registry.command("complain", ("شكوى", "شكوه"), section=S, args="text", usage="نص الشكوى",
                  description="شكوى سرية توصل للإدارة بالخاص (رسالتك تنمسح من المجموعة)", order=32)
async def cmd_complain(cx: CommandContext) -> None:
    from zhoo.systems.protect import send_notice
    svc = cx.services
    text = cx.raw_args.strip()
    try:
        await cx.message.delete()  # السرية: نشيل الشكوى من المجموعة
    except TelegramError:
        pass
    who = mention(cx.user.id, cx.user.full_name)
    if not MIN_LEN <= len(text) <= MAX_LEN:
        await send_notice(cx.context, cx.chat.id, T.COMPLAINT_BAD, ttl=15)
        return
    last = await svc.social.last_complaint_at(cx.chat.id, cx.user.id)
    if last and time.time() - last < COMPLAINT_COOLDOWN:
        await send_notice(cx.context, cx.chat.id, T.COMPLAINT_WAIT.format(
            left=duration(COMPLAINT_COOLDOWN - (time.time() - last))), ttl=15)
        return
    cid = await svc.social.add_complaint(cx.chat.id, cx.user.id, text)
    await svc.audit.log("complaint", chat_id=cx.chat.id, actor_id=cx.user.id, details={"id": cid})
    dm = T.COMPLAINT_DM.format(id=cid, group=esc(cx.chat.title or ""), mention=who, text=esc(text))
    kb = InlineKeyboardMarkup([[B(T.BTN_COMPLAINT_CLOSE, callback_data=f"cp:{cid}:c")]])
    for uid in await _complaint_recipients(svc, cx.bot, cx.chat.id, cx.user.id):
        try:
            await cx.bot.send_message(uid, dm, reply_markup=kb)
        except TelegramError:
            pass  # ما بدأ محادثة ويا البوت؛ يگدر يشوفها بأمر «الشكاوى»
    await send_notice(cx.context, cx.chat.id, T.COMPLAINT_SENT.format(mention=who, id=cid), ttl=15)


async def _close(svc: Services, bot, cid: int, by: int) -> bool:
    row = await svc.social.get_complaint(cid)
    if row is None or not await svc.social.close_complaint(cid, by):
        return False
    await svc.audit.log("complaint_close", chat_id=row["chat_id"], actor_id=by, details={"id": cid})
    group = await svc.db.fetchval("SELECT title FROM groups WHERE chat_id = ?", (row["chat_id"],), default="")
    try:
        await bot.send_message(row["user_id"], T.COMPLAINT_CLOSED_DM.format(id=cid, group=esc(group or "")))
    except TelegramError:
        pass
    return True


@registry.command("complaints", ("الشكاوى", "الشكاوي"), section=S, min_rank=COMPLAINT_RANK,
                  description="الشكاوى المفتوحة", order=33)
async def cmd_complaints(cx: CommandContext) -> None:
    rows = await cx.services.social.open_complaints(cx.chat.id)
    if not rows:
        await cx.reply(f"{T.COMPLAINTS_HEADER}\n{T.COMPLAINTS_EMPTY}")
        return
    items = [T.COMPLAINT_ITEM.format(id=r["id"], mention=mention(r["user_id"], _name(r)),
                                     text=esc(r["text"] if len(r["text"]) <= 150 else r["text"][:150] + "…"))
             for r in rows]
    await cx.reply(f"{T.COMPLAINTS_HEADER}\n" + "\n".join(items) + "\n" + T.COMPLAINTS_FOOTER)


@registry.command("complaint_close", ("حل شكوى", "حل شكوه", "اغلاق شكوى"), section=S, min_rank=COMPLAINT_RANK,
                  args="text", usage="رقم الشكوى", description="يغلق شكوى ويبلغ صاحبها", order=34)
async def cmd_complaint_close(cx: CommandContext) -> None:
    raw = (cx.args[0] if cx.args else "").lstrip("#")
    row = await cx.services.social.get_complaint(int(raw)) if raw.isdigit() else None
    if row is None or row["chat_id"] != cx.chat.id or not await _close(cx.services, cx.bot, row["id"], cx.user.id):
        await cx.reply(T.COMPLAINT_NOT_FOUND)
        return
    await cx.reply(T.COMPLAINT_CLOSED.format(id=row["id"]))


async def on_complaint_button(q, msg: Message, svc: Services, bot, cid_raw: str) -> None:
    """زر «تم الحل» بخاص الإداري — نتحقق من رتبته بمجموعة الشكوى نفسها."""
    row = await svc.social.get_complaint(int(cid_raw)) if cid_raw.isdigit() else None
    if row is None:
        await q.answer(T.COMPLAINT_ALREADY)
        return
    if await svc.perms.rank_of(bot, row["chat_id"], q.from_user.id) < COMPLAINT_RANK:
        await q.answer(T.COMPLAINT_NEED_STAFF, show_alert=True)
        return
    if not await _close(svc, bot, row["id"], q.from_user.id):
        await q.answer(T.COMPLAINT_ALREADY, show_alert=True)
    else:
        await q.answer(T.COMPLAINT_CLOSED.replace(f"{T.BULLET} ", "").replace("<b>", "").replace("</b>", "")
                       .format(id=row["id"]))
    try:
        await msg.edit_text(msg.text_html + "\n\n✅", reply_markup=None)
    except (BadRequest, AttributeError):
        pass
