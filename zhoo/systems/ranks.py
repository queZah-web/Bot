"""نظام الرتب: رفع وتنزيل وقوائم الطاقم.

كل قرار يمر من check_rank_change المركزية، وكل تغيير ينسجل بسجل التدقيق.
"""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import capabilities as caps
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import (ASSIGNABLE, PROTECTED as PROTECTED_RANKS, RANK_NAMES, RANK_PLURALS, Rank,
                             RankDecision, check_rank_change, rank_label)
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "ranks"
# صلاحيات تيليجرام للمشرف اللي ترفعه زهو
TG_ADMIN_RIGHTS = dict(can_manage_chat=True, can_delete_messages=True, can_restrict_members=True,
                       can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True)
TG_NO_RIGHTS = dict(can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
                    can_invite_users=False, can_pin_messages=False, can_manage_video_chats=False,
                    can_promote_members=False, can_change_info=False, is_anonymous=False)

# اسم الرتبة كما يُكتب بالأمر
RANK_WORDS: dict[Rank, tuple[str, ...]] = {
    Rank.PRIMARY_OWNER: ("مالك اساسي", "مالك أساسي"),
    Rank.OWNER: ("مالك",),
    Rank.GENERAL_MANAGER: ("منشئ", "مدير عام"),
    Rank.MANAGER: ("مدير",),
    Rank.SUPERVISOR: ("مشرف",),
    Rank.ADMIN: ("ادمن", "أدمن"),
    Rank.VIP: ("مميز",),
}


async def change_rank(cx: CommandContext, new_rank: Rank, *, only_from: Rank | None = None) -> None:
    """التنفيذ المشترك لكل أوامر الرفع والتنزيل.

    only_from: لأوامر «تنزيل مدير» مثلاً — ينفذ فقط إذا كانت رتبته المخزنة مدير.
    """
    svc = cx.services
    example = f"{'رفع' if new_rank else 'تنزيل'} {RANK_WORDS.get(new_rank or only_from or Rank.VIP, ('مميز',))[0]} @username"
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, example)
        return

    who = mention(target.user_id, target.name)
    if target.is_bot:
        await cx.reply(T.RANK_BOT)
        return

    info = await svc.perms.rank_info(cx.bot, cx.chat.id, target.user_id)
    tg_note = ""
    # تنزيل لعضو: إذا مشرف بتيليجرام نشيل إشرافه (إذا زهو هي اللي رفعته) حتى ينسحب كلشي
    if new_rank == Rank.MEMBER and info.floor == Rank.ADMIN and info.effective < cx.rank \
            and target.user_id != cx.user.id:
        if await tg_demote(cx.bot, svc, cx.chat.id, target.user_id):
            info = await svc.perms.rank_info(cx.bot, cx.chat.id, target.user_id)
            tg_note = "\n" + T.RANK_TG_DEMOTED

    if only_from is not None and info.stored != only_from:
        await cx.reply(T.RANK_NOT_THAT.format(mention=who, rank=RANK_NAMES[only_from]))
        return

    decision = check_rank_change(cx.rank, info.effective, info.floor, new_rank,
                                 is_self=target.user_id == cx.user.id)
    replies = {
        RankDecision.SELF: T.RANK_SELF,
        RankDecision.PROTECTED: T.RANK_PROTECTED.format(mention=who, rank=rank_label(info.effective)),
        RankDecision.TARGET_HIGHER: T.RANK_TARGET_HIGHER.format(mention=who, rank=rank_label(info.effective)),
        RankDecision.CANT_GRANT: T.RANK_CANT_GRANT.format(rank=RANK_NAMES.get(new_rank, "")),
        RankDecision.SAME: T.RANK_SAME.format(mention=who, rank=RANK_NAMES[new_rank]),
        RankDecision.BELOW_FLOOR: T.RANK_BELOW_FLOOR.format(mention=who, rank=RANK_NAMES[info.floor]),
    }
    if decision != RankDecision.OK:
        await svc.audit.log("rank_denied", chat_id=cx.chat.id, actor_id=cx.user.id,
                            target_id=target.user_id, result="denied",
                            details={"reason": decision, "to": int(new_rank)})
        await cx.reply(replies[decision])
        return

    # إذا انطلبت رتبة أقل من حد تيليجرام، نخزن عضو (الحد يتكفل بالباقي)
    stored_value = new_rank if new_rank > info.floor else Rank.MEMBER
    previous = await svc.members.set_rank(cx.chat.id, target.user_id, stored_value, cx.user.id)
    new_effective = max(stored_value, info.floor)

    await svc.audit.log("rank_change", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id,
                        details={"from": int(previous), "to": int(new_effective)})

    actor = mention(cx.user.id, cx.user.full_name)
    if new_effective > info.effective:
        text = T.RANK_PROMOTED.format(mention=who, rank=rank_label(new_effective), actor=actor)
        if new_effective == Rank.SUPERVISOR:   # المشرف = مشرف حقيقي بتيليجرام
            text += "\n" + (T.RANK_TG_PROMOTED if await tg_promote(cx.bot, svc, cx.chat.id, target.user_id)
                            else T.RANK_TG_FAILED)
        text += "\n" + T.PERM_HINT
        _, kb = await perm_panel(svc, cx.chat.id, target.user_id, new_effective)
        await cx.reply(text, reply_markup=kb)
    else:
        if new_effective == Rank.MEMBER:   # تنزيل كامل: تنسحب كل الصلاحيات المخصصة
            await svc.member_perms.clear(cx.chat.id, target.user_id)
            tg_note += "\n" + T.RANK_ALL_REVOKED
        await cx.reply(T.RANK_DEMOTED.format(mention=who, old=rank_label(info.effective),
                                             rank=rank_label(new_effective), actor=actor) + tg_note)


def _register_rank_commands() -> None:
    for i, rank in enumerate(ASSIGNABLE):
        words = RANK_WORDS[rank]
        # لرفع رتبة لازم تكون أعلى منها بدرجة على الأقل
        needed = next((r for r in sorted(Rank) if r > rank), Rank.DEVELOPER)

        async def promote(cx: CommandContext, _r: Rank = rank) -> None:
            await change_rank(cx, _r)

        async def demote(cx: CommandContext, _r: Rank = rank) -> None:
            await change_rank(cx, Rank.MEMBER, only_from=_r)

        async def list_rank(cx: CommandContext, _r: Rank = rank) -> None:
            await send_rank_list(cx, _r)

        registry.command(f"promote_{rank.name.lower()}", tuple(f"رفع {w}" for w in words), section=S,
                         min_rank=needed, usage="بالرد/اليوزر/الايدي", args="target",
                         description=f"يرفع العضو {RANK_NAMES[rank]}", order=10 + i)(promote)
        registry.command(f"demote_{rank.name.lower()}", tuple(f"تنزيل {w}" for w in words), section=S,
                         min_rank=needed, usage="بالرد/اليوزر/الايدي", args="target",
                         description=f"ينزل {RANK_NAMES[rank]} لعضو", order=30 + i, show_in_help=False)(demote)
        registry.command(f"list_{rank.name.lower()}", (RANK_PLURALS[rank],), section=S,
                         description=f"قائمة {RANK_PLURALS[rank]}", order=50 + i,
                         show_in_help=False)(list_rank)


_register_rank_commands()


@registry.command("demote", ("تنزيل", "تنزيل الكل", "تنزيل لعضو"), section=S, min_rank=Rank.ADMIN,
                  usage="بالرد/اليوزر/الايدي", args="target",
                  description="ينزله عضو عادي ويسحب كل صلاحياته (حتى إشراف تيليجرام إذا زهو رفعته)", order=29)
async def cmd_demote(cx: CommandContext) -> None:
    await change_rank(cx, Rank.MEMBER)


async def send_rank_list(cx: CommandContext, rank: Rank) -> None:
    rows = [r for r in await cx.services.members.list_ranked(cx.chat.id) if r["rank"] == rank]
    text = T.RANK_LIST_HEADER.format(plural=RANK_PLURALS[rank]) + "\n"
    if not rows:
        text += T.STAFF_EMPTY
    else:
        text += "\n".join(f"{i}. {_row_mention(r)}" for i, r in enumerate(rows, 1))
    await cx.reply(text)


def _row_mention(row) -> str:
    name = " ".join(p for p in (row["first_name"], row["last_name"]) if p) or str(row["user_id"])
    return mention(row["user_id"], name)


@registry.command("staff", ("قائمة الإدارة", "الإدارة", "الطاقم"), section=S,
                  description="يعرض طاقم الإدارة مرتباً حسب الرتبة", order=1)
async def cmd_staff(cx: CommandContext) -> None:
    svc = cx.services
    text = T.STAFF_HEADER.format(title=esc(cx.chat.title or "المجموعة")) + "\n"

    admins = await svc.perms.admins(cx.bot, cx.chat.id)
    creator = next((m for m in admins.values() if m.status == "creator"), None)
    if creator is not None and not creator.is_anonymous:
        text += f"\n{rank_label(Rank.CREATOR)}\n   ▫️ {mention(creator.user.id, creator.user.full_name)}\n"

    rows = await svc.members.list_ranked(cx.chat.id)
    any_rank = False
    for rank in ASSIGNABLE:
        group = [r for r in rows if r["rank"] == rank]
        if not group:
            continue
        any_rank = True
        text += f"\n{rank_label(rank)}\n" + "\n".join(f"   ▫️ {_row_mention(r)}" for r in group[:30])
        if len(group) > 30:
            text += "\n   " + T.STAFF_MORE.format(n=len(group) - 30)
        text += "\n"

    tg_admins = [m for m in admins.values()
                 if m.status == "administrator" and not m.user.is_bot and not m.is_anonymous]
    if tg_admins:
        text += f"\n{T.TG_ADMINS_LABEL}\n" + "\n".join(
            f"   ▫️ {mention(m.user.id, m.user.full_name)}" for m in tg_admins[:30]) + "\n"

    if not any_rank and not tg_admins and creator is None:
        text += T.STAFF_EMPTY
    await cx.reply(text)


# ── إشراف تيليجرام (رتبة المشرف) ───────────────────
async def tg_promote(bot, svc: Services, chat_id: int, user_id: int) -> bool:
    rights = await svc.perms.bot_rights(bot, chat_id)
    if rights is None or not rights.can_promote_members:
        return False
    try:
        await bot.promote_chat_member(chat_id, user_id, **TG_ADMIN_RIGHTS)
    except TelegramError as e:
        log.info("ما كدرت أرفع %s مشرف بتيليجرام: %s", user_id, e)
        return False
    svc.perms.invalidate(chat_id)
    return True


async def tg_demote(bot, svc: Services, chat_id: int, user_id: int) -> bool:
    """يشيل إشراف تيليجرام (يشتغل بس للمشرفين اللي رفعتهم زهو)."""
    rights = await svc.perms.bot_rights(bot, chat_id)
    if rights is None or not rights.can_promote_members:
        return False
    try:
        await bot.promote_chat_member(chat_id, user_id, **TG_NO_RIGHTS)
    except TelegramError as e:
        log.info("ما كدرت أنزل %s من إشراف تيليجرام: %s", user_id, e)
        return False
    svc.perms.invalidate(chat_id)
    return True


# ── لوحة الصلاحيات ─────────────────────────────────
async def perm_panel(svc: Services, chat_id: int, user_id: int, rank: Rank) -> tuple[str, InlineKeyboardMarkup]:
    allow, deny = await svc.member_perms.get(chat_id, user_id)
    buttons = []
    for cap, (name, emoji, _) in caps.CAPS.items():
        on = caps.decide(caps.default_on(cap, rank), cap, allow, deny)
        custom = cap in allow or cap in deny
        buttons.append(InlineKeyboardButton(f"{'✅' if on else '▫️'} {emoji} {name}{' ✏️' if custom else ''}",
                                            callback_data=f"pm:{user_id}:{cap}"))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(T.PERM_BTN_RESET, callback_data=f"pm:{user_id}:r"),
                 InlineKeyboardButton(T.BTN_CLOSE, callback_data=f"pm:{user_id}:x")])
    text = T.PERM_PANEL.format(rank=rank_label(rank))
    return text, InlineKeyboardMarkup(rows)


@registry.command("perms_panel", ("صلاحيات", "صلاحياته", "صلاحياتها", "تعديل الصلاحيات"), section=S,
                  min_rank=Rank.ADMIN, args="target", usage="بالرد/اليوزر",
                  description="لوحة أزرار: شنو يكدر يسوي (حظر، كتم، ملفات...)", order=5)
async def cmd_perms(cx: CommandContext) -> None:
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "صلاحياته @username")
        return
    rank = await cx.services.perms.rank_of(cx.bot, cx.chat.id, target.user_id)
    text, kb = await perm_panel(cx.services, cx.chat.id, target.user_id, rank)
    await cx.reply(f"{T.PERM_OF.format(mention=mention(target.user_id, target.name))}\n{text}", reply_markup=kb)


@registry.command("my_perms", ("صلاحياتي",), section=S, description="شنو تكدر تسوي بالمجموعة", order=6)
async def cmd_my_perms(cx: CommandContext) -> None:
    svc = cx.services
    on, off = [], []
    for cap, (name, emoji, _) in caps.CAPS.items():
        ok = await caps.has_cap(svc, cx.chat.id, cx.user.id, cap, caps.default_on(cap, cx.rank))
        (on if ok else off).append(f"{emoji} {name}")
    await cx.reply(T.PERM_MINE.format(rank=rank_label(cx.rank), on=" ⋅ ".join(on) or "—",
                                      off=" ⋅ ".join(off) or "—"))


async def on_perm_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str) -> None:
    if not uid_raw.isdigit():
        await q.answer()
        return
    target_id, editor = int(uid_raw), q.from_user.id
    chat_id = msg.chat.id
    editor_rank = await svc.perms.rank_of(bot, chat_id, editor)
    if action == "x":
        if editor_rank >= Rank.ADMIN:
            try:
                await msg.delete()
            except TelegramError:
                pass
        return
    target_rank = await svc.perms.rank_of(bot, chat_id, target_id)
    is_dev = svc.perms.is_developer(editor)
    if target_id == editor or (not is_dev and (editor_rank <= target_rank or editor_rank < Rank.ADMIN)):
        await q.answer(T.PERM_NOT_ALLOWED, show_alert=True)
        return
    if target_rank in PROTECTED_RANKS:
        await q.answer(T.PERM_PROTECTED, show_alert=True)
        return
    allow, deny = (set(x) for x in await svc.member_perms.get(chat_id, target_id))
    if action == "r":
        await svc.member_perms.clear(chat_id, target_id)
        await q.answer(T.PERM_RESET_DONE)
    elif action in caps.CAPS:
        if not await caps.has_cap(svc, chat_id, editor, action, caps.default_on(action, editor_rank)):
            await q.answer(T.PERM_YOU_LACK, show_alert=True)
            return
        default = caps.default_on(action, target_rank)
        new = not caps.decide(default, action, frozenset(allow), frozenset(deny))
        allow.discard(action)
        deny.discard(action)
        if new != default:
            (allow if new else deny).add(action)
        await svc.member_perms.set(chat_id, target_id, allow, deny, editor)
        name = caps.CAPS[action][0]
        await q.answer(("✅ " if new else "▫️ ") + name)
    else:
        await q.answer()
        return
    await svc.audit.log("perms_change", chat_id=chat_id, actor_id=editor, target_id=target_id,
                        details={"cap": action})
    _, kb = await perm_panel(svc, chat_id, target_id, target_rank)
    try:
        await msg.edit_reply_markup(reply_markup=kb)
    except BadRequest:
        pass
