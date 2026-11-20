"""التقارير: تقرير عام للمطور، تقرير المجموعة، وتصدير الأعضاء CSV."""
from __future__ import annotations

import csv
import io
import logging

from telegram.error import TelegramError

from zhoo.core import levels as L
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.ranks import RANK_NAMES, Rank, coerce_rank
from zhoo.database.db import now
from zhoo.repositories.levels import day_ago

log = logging.getLogger(__name__)
GROUP_RANK = Rank.OWNER
DAYS = 7


async def global_report(svc: Services, days: int = DAYS) -> str:
    since = now() - days * 86400
    db = svc.db
    top_rows = await db.fetchall(
        "SELECT d.chat_id, SUM(d.xp) AS xp, g.title FROM xp_daily d LEFT JOIN groups g ON g.chat_id = d.chat_id "
        "WHERE d.day > ? GROUP BY d.chat_id ORDER BY xp DESC LIMIT 5", (day_ago(days),))
    top = "\n".join(f"    {i}. <b>{esc(r['title'] or r['chat_id'])}</b> ⋅ {r['xp']:,}"
                    for i, r in enumerate(top_rows, 1)) or T.REPORT_NONE
    return T.REPORT_GLOBAL.format(
        days=days,
        groups=await svc.groups.count_active(),
        new_groups=await db.fetchval("SELECT COUNT(*) FROM groups WHERE joined_at > ?", (since,), default=0),
        users=await svc.users.count(),
        new_users=await db.fetchval("SELECT COUNT(*) FROM users WHERE first_seen > ? AND is_bot = 0", (since,),
                                    default=0),
        started=await svc.users.count_started(),
        punish=await db.fetchval("SELECT COUNT(*) FROM punishments WHERE created_at > ?", (since,), default=0),
        swear=await db.fetchval("SELECT COUNT(*) FROM swear_logs WHERE created_at > ?", (since,), default=0),
        guard=await db.fetchval("SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'guard_%' AND created_at > ?",
                                (since,), default=0),
        errors=svc.error_count, top=top)


async def group_report(svc: Services, bot, chat, days: int = DAYS) -> str:
    since = now() - days * 86400
    db, cid = svc.db, chat.id
    try:
        members = await bot.get_chat_member_count(cid)
    except TelegramError:
        members = "—"
    top_rows = await svc.levels.top_since(cid, days, 3)
    medals = ("🥇", "🥈", "🥉")
    top = "\n".join(
        f"    {medals[i]} {mention(r['user_id'], ' '.join(p for p in (r['first_name'], r['last_name']) if p))}"
        f" ⋅ {r['value']:,}" for i, r in enumerate(top_rows)) or T.REPORT_NONE
    xp = await db.fetchval("SELECT COALESCE(SUM(xp), 0) FROM xp_daily WHERE chat_id = ? AND day > ?",
                           (cid, day_ago(days)), default=0)
    return T.REPORT_GROUP.format(
        title=esc(chat.title or ""), days=days, members=members, xp=f"{xp:,}",
        new=await db.fetchval("SELECT COUNT(*) FROM group_members WHERE chat_id = ? AND first_seen > ?",
                              (cid, since), default=0),
        active=await db.fetchval("SELECT COUNT(DISTINCT user_id) FROM xp_daily WHERE chat_id = ? AND day > ?",
                                 (cid, day_ago(days)), default=0),
        punish=await db.fetchval("SELECT COUNT(*) FROM punishments WHERE chat_id = ? AND created_at > ?",
                                 (cid, since), default=0),
        swear=await svc.swear_logs.count_since(cid, days * 86400),
        guard=await db.fetchval("SELECT COUNT(*) FROM audit_logs WHERE chat_id = ? AND action LIKE 'guard_%' "
                                "AND created_at > ?", (cid, since), default=0),
        top=top)


async def members_csv(svc: Services, chat_id: int) -> tuple[bytes, int]:
    rows = await svc.db.fetchall(
        "SELECT m.user_id, u.first_name, u.last_name, u.username, m.rank, m.msg_count, m.xp, m.wins, "
        "COALESCE(w.balance, 0) AS balance, m.first_seen FROM group_members m "
        "LEFT JOIN users u ON u.user_id = m.user_id "
        "LEFT JOIN wallets w ON w.chat_id = m.chat_id AND w.user_id = m.user_id "
        "WHERE m.chat_id = ? ORDER BY m.msg_count DESC", (chat_id,))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["user_id", "name", "username", "rank", "messages", "xp", "level", "wins", "balance", "first_seen"])
    for r in rows:
        name = " ".join(p for p in (r["first_name"], r["last_name"]) if p)
        writer.writerow([r["user_id"], name, r["username"] or "", RANK_NAMES[coerce_rank(r["rank"])],
                         r["msg_count"], r["xp"], L.level_for(r["xp"]), r["wins"], r["balance"], r["first_seen"]])
    return ("﻿" + buf.getvalue()).encode("utf-8"), len(rows)  # BOM حتى إكسل يقرا العربي صح


async def weekly_job(context) -> None:
    from zhoo.core.context import get_services
    svc = get_services(context)
    try:
        await context.bot.send_message(svc.settings.owner_id, await global_report(svc))
    except TelegramError as e:
        log.info("ما گدرت أدز التقرير الأسبوعي: %s", e)


# ── أوامر المجموعة ──────────────────────────────────
@registry.command("group_report", ("تقرير المجموعه", "تقرير المجموعة"), section="group", min_rank=GROUP_RANK,
                  description="تقرير آخر 7 أيام للمجموعة", order=30)
async def cmd_group_report(cx: CommandContext) -> None:
    await cx.reply(await group_report(cx.services, cx.bot, cx.chat))


@registry.command("export_members", ("تصدير الاعضاء", "تصدير الأعضاء"), section="group", min_rank=GROUP_RANK,
                  description="ملف CSV بكل الأعضاء وإحصائياتهم (ينرسل بالخاص)", order=31)
async def cmd_export(cx: CommandContext) -> None:
    data, n = await members_csv(cx.services, cx.chat.id)
    try:
        await cx.bot.send_document(cx.user.id, io.BytesIO(data), filename=f"members-{abs(cx.chat.id)}.csv",
                                   caption=T.EXPORT_CAPTION.format(title=esc(cx.chat.title or ""), n=n))
    except TelegramError:
        await cx.reply(T.EXPORT_NEED_START)
        return
    await cx.services.audit.log("export_members", chat_id=cx.chat.id, actor_id=cx.user.id, details={"rows": n})
    await cx.reply(T.EXPORT_SENT)
