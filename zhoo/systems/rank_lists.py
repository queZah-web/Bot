"""قوائم الرتب بالأزرار: «المميزين» ⋅ «الأدمنية» ⋅ «المشرفين» ⋅ «المدراء» ⋅ «المنشئين» ⋅ «المالكين»...

تحت كل قائمة (إذا اللي طلبها يگدر ينزّل هاي الرتبة):
- زر لكل شخص «⬇️ تنزيل 1. الاسم» ← ينزله عضو بضغطة (نفس قواعد check_rank_change).
- زر «🧹 تنزيل الكل» ← يطلب تأكيد، وبعدها ينزلهم كلهم.
- صفحات (10 بكل صفحة) + تحديث.

callback: rl:<رقم الرتبة>:<فعل>:<قيمة>   u=تنزيل شخص ⋅ a=الكل (تأكيد) ⋅ y=تأكيد ⋅ p=صفحة
"""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest

from zhoo.core import texts as T
from zhoo.core.context import Services
from zhoo.core.fmt import mention
from zhoo.core.ranks import ASSIGNABLE, RANK_NAMES, RANK_PLURALS, Rank, RankDecision, check_rank_change, rank_label

log = logging.getLogger(__name__)
PAGE = 10
NAME_MAX = 22


def needed(rank: Rank) -> Rank:
    """أقل رتبة تگدر تنزّل هاي الرتبة (أعلى منها بدرجة)."""
    return next((r for r in sorted(Rank) if r > rank), Rank.DEVELOPER)


def _name(r) -> str:
    return " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])


def _short(text: str) -> str:
    return text if len(text) <= NAME_MAX else text[:NAME_MAX - 1] + "…"


async def _rows(svc: Services, chat_id: int, rank: Rank):
    return [r for r in await svc.members.list_ranked(chat_id) if r["rank"] == rank]


async def render(svc: Services, chat_id: int, rank: Rank, page: int = 0, note: str = "",
                 buttons: bool = True) -> tuple[str, InlineKeyboardMarkup | None]:
    rows = await _rows(svc, chat_id, rank)
    pages = max(1, -(-len(rows) // PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = rows[page * PAGE:(page + 1) * PAGE]
    code = int(rank)
    text = T.RL_HEADER.format(label=rank_label(rank), plural=RANK_PLURALS[rank], n=len(rows))
    if rows:
        text += "\n" + "\n".join(f"{page * PAGE + i}. {mention(r['user_id'], _name(r))}"
                                 for i, r in enumerate(chunk, 1))
        if pages > 1:
            text += f"\n{T.LINE}\n" + T.PL_PAGE.format(page=page + 1, pages=pages)
    else:
        text += "\n" + T.STAFF_EMPTY
    if note:
        text += f"\n{T.LINE}\n{note}"
    if not buttons:
        return text, None
    kb = []
    if rows:
        kb.append([InlineKeyboardButton(T.RL_BTN_ALL.format(plural=RANK_PLURALS[rank]),
                                        callback_data=f"rl:{code}:a:{page}")])
        for i, r in enumerate(chunk, 1):
            kb.append([InlineKeyboardButton(T.RL_BTN_ONE.format(i=page * PAGE + i, name=_short(_name(r))),
                                            callback_data=f"rl:{code}:u:{r['user_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(T.PL_BTN_PREV, callback_data=f"rl:{code}:p:{page - 1}"))
    nav.append(InlineKeyboardButton(T.PL_BTN_REFRESH, callback_data=f"rl:{code}:p:{page}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(T.PL_BTN_NEXT, callback_data=f"rl:{code}:p:{page + 1}"))
    kb.append(nav)
    return text, InlineKeyboardMarkup(kb)


async def demote_one(svc: Services, bot, chat_id: int, actor_id: int, actor_rank: Rank,
                     user_id: int) -> str | None:
    """ينزّل شخص لعضو بنفس قواعد أمر «تنزيل». يرجع None إذا نجح، أو سبب الرفض كنص."""
    from zhoo.systems import suspect
    from zhoo.systems.ranks import tg_demote
    info = await svc.perms.rank_info(bot, chat_id, user_id)
    if info.floor == Rank.ADMIN and info.effective < actor_rank and user_id != actor_id:
        if await tg_demote(bot, svc, chat_id, user_id):   # مشرف رفعته زهو: نشيل إشرافه أول
            info = await svc.perms.rank_info(bot, chat_id, user_id)
    decision = check_rank_change(actor_rank, info.effective, info.floor, Rank.MEMBER, is_self=user_id == actor_id)
    if decision != RankDecision.OK:
        await svc.audit.log("rank_denied", chat_id=chat_id, actor_id=actor_id, target_id=user_id, result="denied",
                            details={"reason": decision, "to": 0})
        return T.RL_DENIED.get(decision, T.RL_DENIED[RankDecision.TARGET_HIGHER])
    previous = await svc.members.set_rank(chat_id, user_id, Rank.MEMBER, actor_id)
    await svc.member_perms.clear(chat_id, user_id)
    await suspect.clear(svc, chat_id, user_id, actor_id)
    if previous == Rank.SUPERVISOR:
        await tg_demote(bot, svc, chat_id, user_id)
    await svc.audit.log("rank_change", chat_id=chat_id, actor_id=actor_id, target_id=user_id,
                        details={"from": int(previous), "to": 0, "via": "list"})
    return None


async def _edit(msg: Message, text: str, kb) -> None:
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass


async def on_button(q, msg: Message, svc: Services, bot, code: str, action: str, value: str) -> None:
    if not code.isdigit() or int(code) not in [int(r) for r in ASSIGNABLE] or not value.isdigit():
        await q.answer()
        return
    rank, chat_id, uid = Rank(int(code)), msg.chat.id, q.from_user.id
    if action == "p":
        await q.answer()
        await _edit(msg, *await render(svc, chat_id, rank, int(value)))
        return
    actor_rank = await svc.perms.rank_of(bot, chat_id, uid)
    if actor_rank < needed(rank):
        await q.answer(T.PL_NOT_ALLOWED.format(rank=RANK_NAMES.get(needed(rank), "")), show_alert=True)
        return
    actor = mention(uid, q.from_user.full_name)

    if action == "u":
        target = int(value)
        reason = await demote_one(svc, bot, chat_id, uid, actor_rank, target)
        if reason:
            await q.answer(reason, show_alert=True)
            return
        u = await svc.users.get(target)
        who = mention(target, u.full_name if u else str(target))
        await q.answer(T.RL_DONE_ALERT)
        await _edit(msg, *await render(svc, chat_id, rank, 0, T.RL_DONE_ONE.format(
            who=who, rank=RANK_NAMES[rank], actor=actor)))
        return

    if action in ("a", "y"):
        rows = await _rows(svc, chat_id, rank)
        if not rows:
            await q.answer(T.PL_EMPTY_ALERT, show_alert=True)
            await _edit(msg, *await render(svc, chat_id, rank))
            return
        if action == "a":
            await q.answer()
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(T.RL_BTN_CONFIRM, callback_data=f"rl:{code}:y:0"),
                InlineKeyboardButton(T.PL_BTN_CANCEL, callback_data=f"rl:{code}:p:{value}"),
            ]])
            await _edit(msg, T.RL_CONFIRM.format(n=len(rows), plural=RANK_PLURALS[rank]), kb)
            return
        await q.answer(T.PL_WORKING)
        done = 0
        for r in rows:
            if await demote_one(svc, bot, chat_id, uid, actor_rank, r["user_id"]) is None:
                done += 1
        await _edit(msg, *await render(svc, chat_id, rank, 0, T.RL_DONE_ALL.format(
            n=done, plural=RANK_PLURALS[rank], actor=actor)))
        return
    await q.answer()
