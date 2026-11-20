"""مركز المالك: لوحة التحكم، الصيانة، الإذاعة، النسخ الاحتياطي والاستعادة، التقارير، فحص النظام، والمساعدين.

الصلاحيات:
  • المطور (OWNER_ID): كلشي.
  • المساعد: يشوف اللوحة والتقارير وفحص النظام والسجل والمجموعات بس —
    ما يگدر يذيع، ولا ينسخ أو يستعيد، ولا يغيّر الصيانة أو المساعدين.
"""
from __future__ import annotations

import asyncio
import logging
import platform
import time

import telegram
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

from zhoo import __version__
from zhoo.core import conversation
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration
from zhoo.core.ranks import Rank
from zhoo.handlers.views import audit_text, groups_text, owner_panel_text
from zhoo.systems import backup, reports

log = logging.getLogger(__name__)
S = "dev"
DEV = Rank.DEVELOPER
BROADCAST_DELAY = 0.05   # ~20 رسالة بالثانية (أقل من حد تيليجرام)


def _eta(seconds: float) -> str:
    return T.LESS_THAN_MINUTE if seconds < 60 else duration(seconds)


# ── اللوحة ──────────────────────────────────────────
def panel_keyboard(maintenance: bool, full: bool) -> InlineKeyboardMarkup:
    B = InlineKeyboardButton
    rows = [[B(T.BTN_REFRESH, callback_data="o:main")]]
    if full:
        rows[0].append(B(T.BTN_MAINT_OFF if maintenance else T.BTN_MAINT_ON, callback_data="o:maint"))
        rows.append([B(T.BTN_BROADCAST, callback_data="o:bc"), B(T.BTN_BACKUP, callback_data="o:backup")])
    rows.append([B(T.BTN_REPORT, callback_data="o:report"), B(T.BTN_HEALTH, callback_data="o:health")])
    rows.append([B(T.BTN_AUDIT, callback_data="o:audit"), B(T.BTN_GROUPS, callback_data="o:groups")])
    rows.append([B(T.BTN_HOME, callback_data="s:home")])
    return InlineKeyboardMarkup(rows)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_BACK, callback_data="o:main")]])


@registry.command("owner_panel", ("مركز المالك", "لوحه التحكم", "لوحة التحكم"), section=S, min_rank=DEV,
                  where="private", helpers=True, description="لوحة التحكم الكاملة بالأزرار")
async def cmd_owner_panel(cx: CommandContext) -> None:
    svc = cx.services
    full = svc.perms.is_developer(cx.user.id)
    await cx.reply(await owner_panel_text(svc), reply_markup=panel_keyboard(svc.maintenance, full))


@registry.command("maint_on", ("تفعيل الصيانه", "تفعيل الصيانة"), section=S, min_rank=DEV,
                  where="any", description="يوقف زهو للجميع عدا المطور", order=1)
async def cmd_maint_on(cx: CommandContext) -> None:
    await cx.services.bot_settings.set("maintenance", "1")
    await cx.services.audit.log("maintenance_on", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.MAINTENANCE_ON)


@registry.command("maint_off", ("تعطيل الصيانه", "تعطيل الصيانة", "ايقاف الصيانه"), section=S,
                  min_rank=DEV, where="any", description="يعيد زهو للعمل", order=2)
async def cmd_maint_off(cx: CommandContext) -> None:
    await cx.services.bot_settings.set("maintenance", "0")
    await cx.services.audit.log("maintenance_off", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.MAINTENANCE_OFF)


@registry.command("audit", ("سجل العمليات",), section=S, min_rank=DEV, where="any", helpers=True,
                  description="آخر العمليات الإدارية المسجلة", order=3)
async def cmd_audit(cx: CommandContext) -> None:
    await cx.reply(await audit_text(cx.services))


@registry.command("my_groups", ("مجموعاتي", "المجموعات"), section=S, min_rank=DEV, where="any", helpers=True,
                  description="آخر المجموعات التي أضافتني", order=4)
async def cmd_groups(cx: CommandContext) -> None:
    await cx.reply(await groups_text(cx.services))


# ── التقارير وفحص النظام ────────────────────────────
@registry.command("global_report", ("تقرير", "التقرير"), section=S, min_rank=DEV, where="private", helpers=True,
                  description="تقرير عام لآخر 7 أيام (وينرسل تلقائياً كل أحد)", order=5)
async def cmd_report(cx: CommandContext) -> None:
    await cx.reply(await reports.global_report(cx.services))


async def health_text(svc: Services, bot, application=None) -> str:
    db_ok = (await svc.db.fetchval("PRAGMA quick_check")) == "ok"
    size = await svc.db.fetchval(
        "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()", default=0)
    t0 = time.monotonic()
    try:
        await bot.get_me()
        tg, ping = T.HEALTH_OK, f"{(time.monotonic() - t0) * 1000:.0f} ms"
    except TelegramError:
        tg, ping = T.HEALTH_BAD, "—"
    jq = getattr(application, "job_queue", None) if application else None
    age = backup.last_backup_age(svc)
    return T.HEALTH.format(
        db=T.HEALTH_OK if db_ok else T.HEALTH_BAD, size=backup.human_size(size or 0), tg=tg, ping=ping,
        jobs=len(jq.jobs()) if jq else 0, backup=duration(age) if age is not None else "—",
        uptime=duration(time.time() - svc.started_at), errors=svc.error_count, version=__version__,
        py=platform.python_version(), ptb=telegram.__version__)


@registry.command("health", ("فحص النظام",), section=S, min_rank=DEV, where="private", helpers=True,
                  description="يفحص القاعدة واتصال تيليجرام والمهام والنسخ", order=6)
async def cmd_health(cx: CommandContext) -> None:
    await cx.reply(await health_text(cx.services, cx.bot, cx.context.application))


# ── النسخ الاحتياطي والاستعادة ─────────────────────
async def _do_backup(bot, svc: Services, chat_id: int) -> None:
    try:
        path, stats = await backup.make_backup(svc, "manual")
        await backup.send_backup(bot, svc, chat_id, path, stats)
    except Exception:
        log.exception("فشل النسخ اليدوي")
        await bot.send_message(chat_id, T.BACKUP_FAILED)


@registry.command("backup", ("نسخه احتياطيه", "نسخة احتياطية", "نسخ احتياطي"), section=S, min_rank=DEV,
                  where="private", description="ينسخ قاعدة البيانات ويدزها إلك (وكل يوم تلقائياً)", order=7)
async def cmd_backup(cx: CommandContext) -> None:
    await cx.reply(T.BACKUP_WORKING)
    await _do_backup(cx.bot, cx.services, cx.chat.id)


@registry.command("restore", ("استعاده نسخه", "استعادة نسخة"), section=S, min_rank=DEV, where="private",
                  description="يرجّع البيانات من ملف نسخة (بفحص وتأكيد)", order=8)
async def cmd_restore(cx: CommandContext) -> None:
    cx.services.conversations.start(cx.chat.id, cx.user.id, "restore", "file")
    await cx.reply(T.RESTORE_ASK.format(cancel=T.CONV_CANCEL_HINT))


@conversation.handler("restore")
async def _restore_flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    if p.step == "confirm":
        await msg.reply_text(T.BC_PRESS_BUTTON)
        return
    doc = msg.document
    if doc is None or not (doc.file_name or "").endswith(".db") or (doc.file_size or 0) > backup.MAX_UPLOAD:
        await msg.reply_text(T.RESTORE_NEED_FILE)
        return
    path = await backup.download_upload(context.bot, svc, doc.file_id)
    stats = await asyncio.to_thread(backup.verify_file, path)
    if stats is None:
        path.unlink(missing_ok=True)
        svc.conversations.end(chat.id, user.id)
        await msg.reply_text(T.RESTORE_BAD_FILE)
        return
    p.data["path"] = str(path)
    p.step = "confirm"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_RESTORE_GO, callback_data="rs:go"),
                                InlineKeyboardButton(T.BTN_BC_CANCEL, callback_data="rs:x")]])
    await msg.reply_text(T.RESTORE_CONFIRM.format(**stats), reply_markup=kb)


async def on_restore_button(q, msg: Message, svc: Services, action: str) -> None:
    from pathlib import Path
    uid = q.from_user.id
    if not svc.perms.is_developer(uid):
        await q.answer(T.DEV_ONLY, show_alert=True)
        return
    p = svc.conversations.get(msg.chat.id, uid)
    if p is None or p.kind != "restore" or p.step != "confirm":
        await q.answer(T.BC_EXPIRED, show_alert=True)
        return
    svc.conversations.end(msg.chat.id, uid)
    if action != "go":
        Path(p.data["path"]).unlink(missing_ok=True)
        await msg.edit_text(T.BC_CANCELLED)
        return
    await q.answer("♻️")
    try:
        pre = await backup.restore(svc, Path(p.data["path"]))
    except RuntimeError as e:
        await msg.edit_text(T.RESTORE_MEMORY if str(e) == "memory" else T.RESTORE_FAILED)
        return
    except Exception:
        log.exception("فشلت الاستعادة")
        await msg.edit_text(T.RESTORE_FAILED)
        return
    await msg.edit_text(T.RESTORE_DONE.format(pre=pre.name))


# ── الإذاعة ─────────────────────────────────────────
async def _audience(svc: Services, target: str) -> list[int]:
    ids: list[int] = []
    if target in ("groups", "all"):
        ids += await svc.groups.active_ids()
    if target in ("users", "all"):
        ids += await svc.users.started_ids()
    return list(dict.fromkeys(ids))


async def _ask_target(svc: Services) -> tuple[str, InlineKeyboardMarkup]:
    text = T.BC_ASK_TARGET.format(groups=await svc.groups.count_active(), users=await svc.users.count_started())
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"bc:t:{key}") for key, label in T.BC_TARGETS.items()],
        [InlineKeyboardButton(T.BTN_BC_CANCEL, callback_data="bc:x:-")],
    ])
    return text, kb


@registry.command("broadcast", ("اذاعه", "إذاعة", "اذاعة"), section=S, min_rank=DEV, where="private",
                  description="رسالة لكل المجموعات أو المستخدمين (بمعاينة وتأكيد)", order=9)
async def cmd_broadcast(cx: CommandContext) -> None:
    text, kb = await _ask_target(cx.services)
    await cx.reply(text, reply_markup=kb)


@conversation.handler("broadcast")
async def _broadcast_flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    if p.step == "confirm":
        await msg.reply_text(T.BC_PRESS_BUTTON)
        return
    count = len(await _audience(svc, p.data["target"]))
    if count == 0:
        svc.conversations.end(chat.id, user.id)
        await msg.reply_text(T.BC_EMPTY)
        return
    await context.bot.copy_message(chat.id, chat.id, msg.message_id)  # المعاينة: نفس الرسالة بالضبط
    p.data.update(src_chat=chat.id, src_msg=msg.message_id, count=count)
    p.step = "confirm"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_BC_SEND, callback_data="bc:go:-"),
                                InlineKeyboardButton(T.BTN_BC_CANCEL, callback_data="bc:x:-")]])
    await msg.reply_text(T.BC_CONFIRM.format(target=T.BC_TARGETS[p.data["target"]], count=count,
                                             eta=_eta(count * BROADCAST_DELAY + 1)), reply_markup=kb)


async def run_broadcast(bot, svc: Services, owner_chat: int, target: str, src_chat: int, src_msg: int) -> tuple[int, int]:
    """يرسل بمعدل آمن، ويتعامل مع حدود تيليجرام. يرجع (وصلت، ما وصلت)."""
    svc.broadcast_running = True
    sent = failed = 0
    t0 = time.monotonic()
    try:
        for chat_id in await _audience(svc, target):
            for attempt in range(2):
                try:
                    await bot.copy_message(chat_id, src_chat, src_msg)
                    sent += 1
                    break
                except RetryAfter as e:
                    await asyncio.sleep(float(getattr(e, "retry_after", 1)) + 0.5)
                    if attempt:
                        failed += 1
                except Forbidden:
                    failed += 1
                    if chat_id < 0:
                        await svc.groups.set_active(chat_id, False)
                    else:
                        await svc.users.set_started(chat_id, False)
                    break
                except TelegramError:
                    failed += 1
                    break
            await asyncio.sleep(BROADCAST_DELAY)
        await svc.audit.log("broadcast", actor_id=owner_chat,
                            details={"target": target, "sent": sent, "failed": failed})
        try:
            await bot.send_message(owner_chat, T.BC_DONE.format(sent=sent, failed=failed,
                                                                secs=_eta(time.monotonic() - t0)))
        except TelegramError:
            pass
    finally:
        svc.broadcast_running = False  # بعد التقرير، حتى ما تبدي إذاعة ثانية بالنص
    return sent, failed


async def on_broadcast_button(q, msg: Message, svc: Services, bot, action: str, arg: str) -> None:
    uid = q.from_user.id
    if not svc.perms.is_developer(uid) or msg.chat.type != Chat.PRIVATE:
        await q.answer(T.DEV_ONLY, show_alert=True)
        return
    if action == "t" and arg in T.BC_TARGETS:
        svc.conversations.start(msg.chat.id, uid, "broadcast", "content", target=arg)
        await msg.edit_text(T.BC_ASK_CONTENT.format(target=T.BC_TARGETS[arg], cancel=T.CONV_CANCEL_HINT))
        return
    if action == "x":
        svc.conversations.end(msg.chat.id, uid)
        await msg.edit_text(T.BC_CANCELLED)
        return
    if action == "go":
        p = svc.conversations.get(msg.chat.id, uid)
        if p is None or p.kind != "broadcast" or p.step != "confirm":
            await q.answer(T.BC_EXPIRED, show_alert=True)
            return
        if svc.broadcast_running:
            await q.answer(T.BC_BUSY, show_alert=True)
            return
        svc.conversations.end(msg.chat.id, uid)
        await msg.edit_text(T.BC_STARTED)
        svc.broadcast_running = True
        asyncio.get_running_loop().create_task(
            run_broadcast(bot, svc, msg.chat.id, p.data["target"], p.data["src_chat"], p.data["src_msg"]))
        return
    await q.answer()


# ── أزرار اللوحة ────────────────────────────────────
async def on_owner_button(q, msg: Message, svc: Services, context, action: str) -> None:
    uid = q.from_user.id
    if not svc.perms.is_staff(uid) or msg.chat.type != Chat.PRIVATE:
        await q.answer(T.OWNER_ONLY, show_alert=True)
        return
    is_dev = svc.perms.is_developer(uid)
    if action in ("maint", "bc", "backup") and not is_dev:
        await q.answer(T.DEV_ONLY, show_alert=True)
        return

    async def edit(text: str, kb: InlineKeyboardMarkup | None) -> None:
        try:
            await msg.edit_text(text, reply_markup=kb)
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise

    if action == "main":
        await edit(await owner_panel_text(svc), panel_keyboard(svc.maintenance, is_dev))
    elif action == "maint":
        new_state = not svc.maintenance
        await svc.bot_settings.set("maintenance", "1" if new_state else "0")
        await svc.audit.log("maintenance_on" if new_state else "maintenance_off", actor_id=uid)
        await q.answer(T.MAINTENANCE_ON if new_state else T.MAINTENANCE_OFF)
        await edit(await owner_panel_text(svc), panel_keyboard(svc.maintenance, True))
    elif action == "audit":
        await edit(await audit_text(svc), back_keyboard())
    elif action == "groups":
        await edit(await groups_text(svc), back_keyboard())
    elif action == "report":
        await edit(await reports.global_report(svc), back_keyboard())
    elif action == "health":
        await edit(await health_text(svc, context.bot, context.application), back_keyboard())
    elif action == "bc":
        text, kb = await _ask_target(svc)
        await edit(text, kb)
    elif action == "backup":
        await q.answer(T.BACKUP_WORKING.replace(f"{T.BULLET} ", ""))
        await _do_backup(context.bot, svc, msg.chat.id)
    else:
        await q.answer(T.STALE)


# ── المساعدين ──────────────────────────────────────
async def _save_helpers(svc: Services) -> None:
    await svc.bot_settings.set("helpers", ",".join(str(i) for i in sorted(svc.perms.helpers)))


def _helper_id(cx: CommandContext) -> int | None:
    raw = (cx.args[0] if cx.args else "").strip()
    return int(raw) if raw.isdigit() and 5 <= len(raw) <= 15 else None


@registry.command("helper_add", ("رفع مساعد",), section=S, min_rank=DEV, where="private", args="text",
                  usage="الايدي", description="يضيف مساعد للمطور (صلاحيات عرض بس)", order=10)
async def cmd_helper_add(cx: CommandContext) -> None:
    hid = _helper_id(cx)
    if hid is None or hid == cx.services.settings.owner_id:
        await cx.reply(T.HELPER_BAD)
        return
    cx.services.perms.helpers.add(hid)
    await _save_helpers(cx.services)
    await cx.services.audit.log("helper_add", actor_id=cx.user.id, target_id=hid)
    await cx.reply(T.HELPER_ADDED.format(id=hid))


@registry.command("helper_remove", ("تنزيل مساعد",), section=S, min_rank=DEV, where="private", args="text",
                  usage="الايدي", description="يشيل مساعد", order=11)
async def cmd_helper_remove(cx: CommandContext) -> None:
    hid = _helper_id(cx)
    if hid is None or hid not in cx.services.perms.helpers:
        await cx.reply(T.HELPER_NOT_FOUND)
        return
    cx.services.perms.helpers.discard(hid)
    await _save_helpers(cx.services)
    await cx.services.audit.log("helper_remove", actor_id=cx.user.id, target_id=hid)
    await cx.reply(T.HELPER_REMOVED.format(id=hid))


@registry.command("helpers_list", ("المساعدين",), section=S, min_rank=DEV, where="private",
                  description="قائمة مساعدين المطور", order=12)
async def cmd_helpers(cx: CommandContext) -> None:
    helpers = sorted(cx.services.perms.helpers)
    if not helpers:
        await cx.reply(f"{T.HELPERS_HEADER}\n{T.HELPERS_EMPTY}")
        return
    lines = []
    for hid in helpers:
        u = await cx.services.users.get(hid)
        name = f" ⋅ {u.full_name}" if u else ""
        lines.append(f"▫️ <code>{hid}</code>{name}")
    await cx.reply(f"{T.HELPERS_HEADER}\n" + "\n".join(lines))
