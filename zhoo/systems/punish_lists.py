"""قوائم العقوبات بالأزرار: «المحظورين» ⋅ «المكتومين» ⋅ «المقيدين» ⋅ «المحذرين» ⋅ «العقوبات» (لوحة الكل).

تحت كل قائمة:
- زر لكل شخص «🔓 الغاء حظر 1. الاسم ∞» ← يفك عنه بضغطة.
- زر «🧹 الغاء حظر الكل» ← يطلب تأكيد، وبعدها يفك عن الكل.
- صفحات (10 بكل صفحة) + تحديث + رجوع للوحة.
القائمة تتحدث بمكانها بعد كل ضغطة. الصلاحيات نفس أوامر الفك (MIN_RANK).

callback: pl:<b|m|r|w|x>:<فعل>:<قيمة>
  u=فك شخص (ايدي) ⋅ a=الكل (طلب تأكيد) ⋅ y=تأكيد الكل ⋅ p=صفحة ⋅ o=لوحة العقوبات
"""
from __future__ import annotations

import asyncio
import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, Forbidden

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration, mention
from zhoo.core.ranks import RANK_NAMES, Rank
from zhoo.systems.punish import MIN_RANK, do_lift

log = logging.getLogger(__name__)
S = "punish"

PAGE = 10
FETCH_LIMIT = 1000
KINDS = {"b": "ban", "m": "mute", "r": "restrict", "w": "warn"}
CODES = {v: k for k, v in KINDS.items()}
# أقل رتبة لفك الكل (نفس «مسح المحظورين» و«مسح المكتومين»)
ALL_RANK = {"ban": Rank.MANAGER, "mute": Rank.ADMIN, "restrict": Rank.ADMIN, "warn": Rank.MANAGER}
NAME_MAX = 22


def _name(r) -> str:
    return " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])


def _short(text: str) -> str:
    return text if len(text) <= NAME_MAX else text[:NAME_MAX - 1] + "…"


def _left(r, now: float) -> str:
    if "n" in r.keys():                                   # التحذيرات: العدد
        return f"⚠️ {r['n']}"
    return f"⏳ {duration(r['until'] - now)}" if r["until"] else "∞"


async def _rows(svc: Services, chat_id: int, kind: str):
    if kind == "warn":
        return await svc.punishments.list_warned(chat_id, limit=FETCH_LIMIT)
    return await svc.punishments.list_active(chat_id, kind, limit=FETCH_LIMIT)


async def render(svc: Services, chat_id: int, kind: str, page: int = 0,
                 note: str = "") -> tuple[str, InlineKeyboardMarkup | None]:
    rows = await _rows(svc, chat_id, kind)
    pages = max(1, -(-len(rows) // PAGE))
    page = min(max(page, 0), pages - 1)
    chunk = rows[page * PAGE:(page + 1) * PAGE]
    now = time.time()
    code = CODES[kind]
    head = T.PL_HEADER.format(name=T.PL_NAMES[kind], n=len(rows))
    if not rows:
        text = f"{head}\n{T.PUNISHED_LIST_EMPTY}"
        if note:
            text += f"\n{T.LINE}\n{note}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.PL_BTN_REFRESH, callback_data=f"pl:{code}:p:0"),
                                    InlineKeyboardButton(T.PL_BTN_PANEL, callback_data="pl:x:o:0")]])
        return text, kb
    lines = [f"{page * PAGE + i}. {mention(r['user_id'], _name(r))}  <i>{_left(r, now)}</i>"
             for i, r in enumerate(chunk, 1)]
    text = f"{head}\n" + "\n".join(lines)
    if pages > 1:
        text += f"\n{T.LINE}\n" + T.PL_PAGE.format(page=page + 1, pages=pages)
    if note:
        text += f"\n{T.LINE}\n{note}"
    buttons = [[InlineKeyboardButton(T.PL_BTN_ALL[kind], callback_data=f"pl:{code}:a:{page}")]]
    for i, r in enumerate(chunk, 1):
        label = T.PL_BTN_ONE[kind].format(i=page * PAGE + i, name=_short(_name(r)), left=_left(r, now))
        buttons.append([InlineKeyboardButton(label, callback_data=f"pl:{code}:u:{r['user_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(T.PL_BTN_PREV, callback_data=f"pl:{code}:p:{page - 1}"))
    nav.append(InlineKeyboardButton(T.PL_BTN_REFRESH, callback_data=f"pl:{code}:p:{page}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(T.PL_BTN_NEXT, callback_data=f"pl:{code}:p:{page + 1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(T.PL_BTN_PANEL, callback_data="pl:x:o:0")])
    return text, InlineKeyboardMarkup(buttons)


async def render_panel(svc: Services, chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    counts = {k: len(await _rows(svc, chat_id, k)) for k in KINDS.values()}
    text = T.PL_PANEL.format(**counts)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T.PL_PANEL_BTN["ban"].format(n=counts["ban"]), callback_data="pl:b:p:0")],
        [InlineKeyboardButton(T.PL_PANEL_BTN["mute"].format(n=counts["mute"]), callback_data="pl:m:p:0"),
         InlineKeyboardButton(T.PL_PANEL_BTN["restrict"].format(n=counts["restrict"]), callback_data="pl:r:p:0")],
        [InlineKeyboardButton(T.PL_PANEL_BTN["warn"].format(n=counts["warn"]), callback_data="pl:w:p:0")],
    ])
    return text, kb


# ── الأوامر ─────────────────────────────────────────
def _list_cmd(kind: str):
    async def handler(cx: CommandContext) -> None:
        text, kb = await render(cx.services, cx.chat.id, kind)
        await cx.reply(text, reply_markup=kb)
    return handler


registry.command("list_banned", ("المحظورين", "قائمة المحظورين"), section=S, min_rank=Rank.ADMIN,
                 description="قائمة المحظورين + أزرار الفك", order=30)(_list_cmd("ban"))
registry.command("list_muted", ("المكتومين", "قائمة المكتومين"), section=S, min_rank=Rank.ADMIN,
                 description="قائمة المكتومين + أزرار الفك", order=31)(_list_cmd("mute"))
registry.command("list_restricted", ("المقيدين", "قائمة المقيدين"), section=S, min_rank=Rank.ADMIN,
                 description="قائمة المقيّدين + أزرار الفك", order=32)(_list_cmd("restrict"))
registry.command("list_warned", ("المحذرين", "قائمة المحذرين", "المنذرين"), section=S, min_rank=Rank.ADMIN,
                 description="اللي عندهم تحذيرات + أزرار المسح", order=33)(_list_cmd("warn"))


@registry.command("punish_panel", ("العقوبات", "قوائم العقوبات", "لوحة العقوبات"), section=S, min_rank=Rank.ADMIN,
                  description="لوحة: كم محظور ومكتوم ومقيّد، وتفتح كل قائمة بزر", order=29)
async def cmd_panel(cx: CommandContext) -> None:
    text, kb = await render_panel(cx.services, cx.chat.id)
    await cx.reply(text, reply_markup=kb)


# ── الأزرار ─────────────────────────────────────────
async def _edit(msg: Message, text: str, kb) -> None:
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass


def _plain(text: str) -> str:
    return text.replace(f"{T.BULLET} ", "").replace("<b>", "").replace("</b>", "")


async def _can_restrict(q, svc: Services, bot, chat_id: int) -> bool:
    rights = await svc.perms.bot_rights(bot, chat_id)
    if rights is None or not rights.can_restrict_members:
        await q.answer(_plain(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT)), show_alert=True)
        return False
    return True


async def on_button(q, msg: Message, svc: Services, bot, code: str, action: str, value: str) -> None:
    chat_id = msg.chat.id
    rank = await svc.perms.rank_of(bot, chat_id, q.from_user.id)
    if rank < Rank.ADMIN:
        await q.answer(T.PL_NOT_ALLOWED.format(rank=RANK_NAMES[Rank.ADMIN]), show_alert=True)
        return
    if action == "o":
        await q.answer()
        await _edit(msg, *await render_panel(svc, chat_id))
        return
    kind = KINDS.get(code)
    if kind is None or not value.lstrip("-").isdigit():
        await q.answer()
        return
    actor = mention(q.from_user.id, q.from_user.full_name)

    if action == "p":
        await q.answer()
        await _edit(msg, *await render(svc, chat_id, kind, int(value)))
        return

    if action == "u":                                     # فك شخص واحد
        if rank < MIN_RANK[kind]:
            await q.answer(T.PL_NOT_ALLOWED.format(rank=RANK_NAMES[MIN_RANK[kind]]), show_alert=True)
            return
        if kind != "warn" and not await _can_restrict(q, svc, bot, chat_id):
            return
        uid = int(value)
        u = await svc.users.get(uid)
        who = mention(uid, u.full_name if u else str(uid))
        try:
            await do_lift(svc, bot, chat_id, uid, kind, q.from_user.id)
        except (BadRequest, Forbidden) as e:
            log.info("فشل فك %s عن %s: %s", kind, uid, e)
            await q.answer(_plain(T.PUNISH_FAILED), show_alert=True)
            return
        await q.answer(T.PL_DONE_ONE_ALERT[kind])
        await _edit(msg, *await render(svc, chat_id, kind, 0, T.PL_DONE_ONE[kind].format(who=who, actor=actor)))
        return

    if action in ("a", "y"):                              # الكل
        if rank < ALL_RANK[kind]:
            await q.answer(T.PL_NOT_ALLOWED.format(rank=RANK_NAMES[ALL_RANK[kind]]), show_alert=True)
            return
        rows = await _rows(svc, chat_id, kind)
        if not rows:
            await q.answer(T.PL_EMPTY_ALERT, show_alert=True)
            await _edit(msg, *await render(svc, chat_id, kind))
            return
        if action == "a":
            await q.answer()
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(T.PL_BTN_CONFIRM, callback_data=f"pl:{code}:y:0"),
                InlineKeyboardButton(T.PL_BTN_CANCEL, callback_data=f"pl:{code}:p:{value}"),
            ]])
            await _edit(msg, T.PL_CONFIRM[kind].format(n=len(rows)), kb)
            return
        if kind != "warn" and not await _can_restrict(q, svc, bot, chat_id):
            return
        await q.answer(T.PL_WORKING)
        done = 0
        for r in rows:
            try:
                await do_lift(svc, bot, chat_id, r["user_id"], kind, q.from_user.id)
                done += 1
            except (BadRequest, Forbidden) as e:
                log.info("ما كدرت أفك %s عن %s: %s", kind, r["user_id"], e)
            if kind != "warn":
                await asyncio.sleep(0.03)
        await svc.audit.log(f"un{kind}_all", chat_id=chat_id, actor_id=q.from_user.id, details={"n": done})
        await _edit(msg, *await render(svc, chat_id, kind, 0, T.PL_DONE_ALL[kind].format(n=done, actor=actor)))
        return
    await q.answer()

