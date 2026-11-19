"""نظام الرتب: رفع وتنزيل وقوائم الطاقم.

كل قرار يمر من check_rank_change المركزية، وكل تغيير ينسجل بسجل التدقيق.
"""
from __future__ import annotations

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import (ASSIGNABLE, RANK_NAMES, RANK_PLURALS, Rank, RankDecision,
                             check_rank_change, rank_label)
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

S = "ranks"

# اسم الرتبة كما يُكتب بالأمر
RANK_WORDS: dict[Rank, tuple[str, ...]] = {
    Rank.OWNER: ("مالك",),
    Rank.GENERAL_MANAGER: ("مدير عام",),
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
        await cx.reply(T.RANK_PROMOTED.format(mention=who, rank=rank_label(new_effective), actor=actor))
    else:
        await cx.reply(T.RANK_DEMOTED.format(mention=who, old=rank_label(info.effective),
                                             rank=rank_label(new_effective), actor=actor))


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


@registry.command("demote", ("تنزيل", "تنزيل الكل"), section=S, min_rank=Rank.ADMIN,
                  usage="بالرد/اليوزر/الايدي", args="target",
                  description="ينزل العضو من أي رتبة لعضو عادي", order=29)
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
                  description="يعرض طاقم الإدارة كامل مرتب حسب الرتبة", order=1)
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
            text += f"\n   … و {len(group) - 30} غيرهم"
        text += "\n"

    tg_admins = [m for m in admins.values()
                 if m.status == "administrator" and not m.user.is_bot and not m.is_anonymous]
    if tg_admins:
        text += f"\n🔰 مشرفين تيليجرام\n" + "\n".join(
            f"   ▫️ {mention(m.user.id, m.user.full_name)}" for m in tg_admins[:30]) + "\n"

    if not any_rank and not tg_admins and creator is None:
        text += T.STAFF_EMPTY
    await cx.reply(text)
