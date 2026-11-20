"""أوامر المسح والمنع والتنظيف:

- مسح الرتب: «مسح المدراء» ، «مسح المميزين»... و«مسح الكل» (بتأكيد) — كل منهم ينسحب منه كلشي.
- «مسح المحظورين» ، «مسح المكتومين».
- «مسح 50» يمسح آخر 50 رسالة ، «مسح» بالرد يمسح الرسالة.
- المنع: «منع» بالرد على ملصق/متحركة/صورة/فيديو/كلمة ← تنمسح كل ما تنرسل. «الغاء منع» ، «قائمة المنع» ، «مسح قائمة المنع».
- «طرد البوتات» ، «كشف البوتات» ، «طرد المحذوفين» ، «رفع القيود».
"""
from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden, TelegramError

from zhoo.core import moderation as mod
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import ASSIGNABLE, RANK_PLURALS, Rank, rank_label
from zhoo.core.targets import TargetError, resolve_target
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "punish"

MAX_PURGE = 300
DELETED_SCAN_LIMIT = 500
FILTER_RANK = Rank.ADMIN          # المشرفين ما يشملهم المنع
_DELETED_NAMES = {"", "Deleted Account"}


def _needed(rank: Rank) -> Rank:
    return next((r for r in sorted(Rank) if r > rank), Rank.DEVELOPER)


# ── مسح الرتب ───────────────────────────────────────
async def demote_everyone(svc: Services, bot, chat_id: int, ranks: set[Rank], by: int) -> int:
    from zhoo.systems.ranks import tg_demote
    count = 0
    for r in await svc.members.list_ranked(chat_id):
        rank = Rank(r["rank"])
        if rank not in ranks:
            continue
        await svc.members.set_rank(chat_id, r["user_id"], Rank.MEMBER, by)
        await svc.member_perms.clear(chat_id, r["user_id"])
        if rank == Rank.SUPERVISOR:
            await tg_demote(bot, svc, chat_id, r["user_id"])
        count += 1
    await svc.audit.log("ranks_clear", chat_id=chat_id, actor_id=by,
                        details={"ranks": sorted(int(x) for x in ranks), "count": count})
    return count


def _register_rank_clears() -> None:
    for i, rank in enumerate(ASSIGNABLE):
        plural = RANK_PLURALS[rank]
        names = {f"مسح {plural}", f"مسح {normalize(plural)}"}
        if rank == Rank.ADMIN:
            names |= {"مسح الادمنيه", "مسح الادمن"}

        async def handler(cx: CommandContext, _r: Rank = rank) -> None:
            n = await demote_everyone(cx.services, cx.bot, cx.chat.id, {_r}, cx.user.id)
            plural_ = RANK_PLURALS[_r]
            await cx.reply(T.CLEAR_RANK_DONE.format(n=n, what=plural_) if n else T.CLEAR_RANK_EMPTY.format(what=plural_))

        registry.command(f"clear_{rank.name.lower()}", tuple(sorted(names)), section="ranks",
                         min_rank=_needed(rank), order=70 + i,
                         description=f"ينزل كل {plural} لأعضاء ويسحب صلاحياتهم")(handler)


_register_rank_clears()


@registry.command("clear_ranks", ("مسح الكل", "مسح الرتب", "تنزيل الجميع"), section="ranks", min_rank=Rank.OWNER,
                  description="ينزل كل الرتب اللي تحت رتبتك (يطلب تأكيد)", order=69)
async def cmd_clear_ranks(cx: CommandContext) -> None:
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_CONFIRM_CLEAR, callback_data=f"cr:{cx.user.id}:y"),
                                InlineKeyboardButton(T.BTN_CANCEL_CLEAR, callback_data=f"cr:{cx.user.id}:n")]])
    await cx.reply(T.CLEAR_ALL_CONFIRM.format(rank=rank_label(cx.rank)), reply_markup=kb)


async def on_clear_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    if action == "n":
        await q.answer()
        try:
            await msg.edit_text(T.CLEAR_ALL_CANCELLED)
        except BadRequest:
            pass
        return
    rank = await svc.perms.rank_of(bot, msg.chat.id, q.from_user.id)
    if rank < Rank.OWNER:
        await q.answer(T.CLEAR_ALL_NEED_RANK, show_alert=True)
        return
    n = await demote_everyone(svc, bot, msg.chat.id, {r for r in ASSIGNABLE if r < rank}, q.from_user.id)
    await q.answer("✅")
    try:
        await msg.edit_text(T.CLEAR_ALL_DONE.format(n=n))
    except BadRequest:
        pass


# ── مسح المحظورين والمكتومين ─────────────────────────
async def _lift_list(cx: CommandContext, kinds: tuple[str, ...], what: str) -> None:
    from zhoo.systems.punish import do_lift
    svc = cx.services
    rights = await svc.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_restrict_members:
        await cx.reply(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT))
        return
    done = 0
    for kind in kinds:
        for r in await svc.punishments.list_active(cx.chat.id, kind, limit=1000):
            try:
                await do_lift(svc, cx.bot, cx.chat.id, r["user_id"], kind, cx.user.id)
                done += 1
            except (BadRequest, Forbidden) as e:
                log.info("ما كدرت أفك %s عن %s: %s", kind, r["user_id"], e)
            await asyncio.sleep(0.03)
    await cx.reply(T.CLEAR_LIST_DONE.format(n=done, what=what) if done else T.CLEAR_LIST_EMPTY.format(what=what))


@registry.command("clear_banned", ("مسح المحظورين", "الغاء حظر الكل"), section=S, min_rank=Rank.MANAGER,
                  description="يفك الحظر عن كل المحظورين", order=40)
async def cmd_clear_banned(cx: CommandContext) -> None:
    await _lift_list(cx, ("ban",), "المحظورين")


@registry.command("clear_muted", ("مسح المكتومين", "الغاء كتم الكل"), section=S, min_rank=Rank.ADMIN,
                  description="يفك الكتم والتقييد عن الكل", order=41)
async def cmd_clear_muted(cx: CommandContext) -> None:
    await _lift_list(cx, ("mute", "restrict"), "المكتومين والمقيدين")


# ── مسح الرسائل ─────────────────────────────────────
def _accept_purge(rest: str) -> bool:
    rest = rest.strip()
    return rest.isdigit() and 1 <= int(rest) <= MAX_PURGE


@registry.command("purge", ("مسح", "تنظيف"), section=S, min_rank=Rank.ADMIN, accept=_accept_purge,
                  usage=f"عدد (لحد {MAX_PURGE}) أو بالرد", description="«مسح 50» آخر 50 رسالة، أو «مسح» بالرد على رسالة",
                  order=42)
async def cmd_purge(cx: CommandContext) -> None:
    from zhoo.systems.protect import send_notice
    rights = await cx.services.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_delete_messages:
        await cx.reply(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_DELETE))
        return
    me = cx.message.message_id
    if cx.args:
        n = int(cx.args[0])
        ids = [me] + [m for m in range(me - 1, me - 1 - n, -1) if m > 0]
    elif cx.message.reply_to_message is not None:
        ids, n = [me, cx.message.reply_to_message.message_id], 1
    else:
        await cx.reply(T.PURGE_HINT)
        return
    deleted = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            if await cx.bot.delete_messages(cx.chat.id, chunk):
                deleted += len(chunk)
        except TelegramError as e:
            log.info("فشل مسح رسائل: %s", e)
    await cx.services.audit.log("purge", chat_id=cx.chat.id, actor_id=cx.user.id, details={"count": n})
    await send_notice(cx.context, cx.chat.id, T.PURGE_DONE.format(n=max(deleted - 1, 0)), ttl=5)


# ── قائمة المنع ─────────────────────────────────────
def _item_of(msg: Message) -> tuple[str, str, str] | None:
    """(النوع، القيمة، الوصف) للرسالة المردود عليها."""
    if msg.sticker:
        return "sticker", msg.sticker.file_unique_id, f"ملصق {msg.sticker.emoji or ''}".strip()
    if msg.animation:
        return "animation", msg.animation.file_unique_id, "متحركة"
    if msg.photo:
        return "photo", msg.photo[-1].file_unique_id, "صورة"
    if msg.video:
        return "video", msg.video.file_unique_id, "فيديو"
    text = (msg.text or "").strip()
    if text and len(text.split()) <= 4:
        return "word", normalize(text), text
    return None


def _word_item(text: str) -> tuple[str, str, str] | None:
    text = " ".join(text.split())
    norm = normalize(text)
    if not 2 <= len(norm) <= 60:
        return None
    return "word", norm, text


async def check(context, svc: Services, msg: Message, chat, user) -> bool:
    """يرجع True إذا انمسحت الرسالة لأنها ممنوعة."""
    items = await svc.filters.all(chat.id)
    if not items:
        return False
    hit = None
    if msg.sticker and msg.sticker.file_unique_id in items.get("sticker", {}):
        hit = "sticker"
    elif msg.animation and msg.animation.file_unique_id in items.get("animation", {}):
        hit = "animation"
    elif msg.photo and msg.photo[-1].file_unique_id in items.get("photo", {}):
        hit = "photo"
    elif msg.video and msg.video.file_unique_id in items.get("video", {}):
        hit = "video"
    elif "word" in items and (msg.text or msg.caption):
        padded = f" {normalize(msg.text or msg.caption)} "
        if any(f" {w} " in padded for w in items["word"]):
            hit = "word"
    if hit is None:
        return False
    from zhoo.systems import botstate
    if not await botstate.is_active(svc, chat.id):
        return False
    if await svc.perms.rank_of(context.bot, chat.id, user.id) >= FILTER_RANK:
        return False
    try:
        await msg.delete()
    except TelegramError:
        return False
    if svc.notice_limiter.hit(("filter", chat.id, user.id)):
        from zhoo.systems.protect import send_notice
        await send_notice(context, chat.id, T.FILTER_NOTICE.format(mention=mention(user.id, user.full_name)), ttl=10)
    return True


def _target_item(cx: CommandContext) -> tuple[str, str, str] | None:
    if cx.raw_args.strip():
        return _word_item(cx.raw_args)
    if cx.message.reply_to_message is not None:
        return _item_of(cx.message.reply_to_message)
    return None


@registry.command("filter_add", ("منع",), section=S, min_rank=Rank.ADMIN, args="text",
                  usage="بالرد على ملصق/متحركة/صورة، أو كلمة", description="يمنع ملصق أو متحركة أو صورة أو كلمة",
                  order=50)
async def cmd_filter_add(cx: CommandContext) -> None:
    item = _target_item(cx)
    if item is None:
        await cx.reply(T.FILTER_HINT)
        return
    kind, value, label = item
    if not await cx.services.filters.add(cx.chat.id, kind, value, label, cx.user.id):
        await cx.reply(T.FILTER_EXISTS)
        return
    await cx.services.audit.log("filter_add", chat_id=cx.chat.id, actor_id=cx.user.id, details={"kind": kind})
    await cx.reply(T.FILTER_ADDED.format(what=esc(label)))


@registry.command("filter_del", ("الغاء منع", "إلغاء منع", "الغاء المنع"), section=S, min_rank=Rank.ADMIN,
                  args="text", usage="بالرد أو الكلمة", description="يرجع الشي الممنوع مسموح", order=51)
async def cmd_filter_del(cx: CommandContext) -> None:
    item = _target_item(cx)
    if item is None:
        await cx.reply(T.FILTER_HINT)
        return
    kind, value, label = item
    if not await cx.services.filters.remove(cx.chat.id, kind, value):
        await cx.reply(T.FILTER_NOT_FOUND)
        return
    await cx.reply(T.FILTER_REMOVED.format(what=esc(label)))


@registry.command("filter_list", ("قائمة المنع", "قائمه المنع", "الممنوع"), section=S, min_rank=Rank.ADMIN,
                  description="كل الممنوعات بالمجموعة", order=52)
async def cmd_filter_list(cx: CommandContext) -> None:
    items = await cx.services.filters.all(cx.chat.id)
    if not items:
        await cx.reply(f"{T.FILTER_LIST_HEADER}\n{T.FILTER_LIST_EMPTY}")
        return
    lines = []
    for kind, values in items.items():
        name = T.FILTER_KINDS[kind]
        if kind == "word":
            lines.append(f"{name}: " + " ⋅ ".join(f"<code>{esc(v)}</code>" for v in list(values.values())[:50]))
        else:
            lines.append(f"{name}: <b>{len(values)}</b>")
    await cx.reply(f"{T.FILTER_LIST_HEADER}\n" + "\n".join(lines))


@registry.command("filter_clear", ("مسح قائمة المنع", "مسح قائمه المنع"), section=S, min_rank=Rank.MANAGER,
                  description="يمسح كل الممنوعات", order=53)
async def cmd_filter_clear(cx: CommandContext) -> None:
    n = await cx.services.filters.clear(cx.chat.id)
    await cx.services.audit.log("filter_clear", chat_id=cx.chat.id, actor_id=cx.user.id, details={"count": n})
    await cx.reply(T.FILTER_CLEARED.format(n=n))


# ── البوتات والمحذوفين ───────────────────────────────
async def _known_bots(svc: Services, bot, chat_id: int) -> dict[int, tuple[str, bool]]:
    """ايدي البوت ← (الاسم، مشرف؟). بوت API ما يعطي قائمة الأعضاء، فنجمع اللي نعرفهم."""
    out: dict[int, tuple[str, bool]] = {}
    for m in (await svc.perms.admins(bot, chat_id)).values():
        if m.user.is_bot and m.user.id != bot.id:
            out[m.user.id] = (m.user.full_name, True)
    rows = await svc.db.fetchall(
        "SELECT u.user_id, u.first_name, u.username FROM group_members m JOIN users u ON u.user_id = m.user_id "
        "WHERE m.chat_id = ? AND u.is_bot = 1", (chat_id,))
    for r in rows:
        if r["user_id"] != bot.id and r["user_id"] not in out:
            out[r["user_id"]] = (r["first_name"] or r["username"] or str(r["user_id"]), False)
    return out


@registry.command("bots_list", ("كشف البوتات", "البوتات"), section=S, min_rank=Rank.ADMIN,
                  description="البوتات اللي بالمجموعة", order=60)
async def cmd_bots_list(cx: CommandContext) -> None:
    bots = await _known_bots(cx.services, cx.bot, cx.chat.id)
    if not bots:
        await cx.reply(f"{T.BOTS_HEADER}\n{T.BOTS_EMPTY}")
        return
    lines = [f"▫️ {mention(uid, name)}{' ⋅ 🛡' if admin else ''}" for uid, (name, admin) in bots.items()]
    await cx.reply(f"{T.BOTS_HEADER}\n" + "\n".join(lines) + f"\n{T.LINE}\n{T.BOTS_FOOTER}")


@registry.command("kick_bots", ("طرد البوتات",), section=S, min_rank=Rank.MANAGER,
                  description="يطرد كل البوتات (عدا زهو)", order=61)
async def cmd_kick_bots(cx: CommandContext) -> None:
    rights = await cx.services.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_restrict_members:
        await cx.reply(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT))
        return
    kicked = failed = 0
    for uid in await _known_bots(cx.services, cx.bot, cx.chat.id):
        try:
            await mod.apply(cx.bot, cx.chat.id, uid, "kick", None)
            kicked += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(0.05)
    await cx.services.audit.log("kick_bots", chat_id=cx.chat.id, actor_id=cx.user.id, details={"count": kicked})
    await cx.reply(T.BOTS_KICKED.format(n=kicked, failed=failed))


_scanning: set[int] = set()


@registry.command("kick_deleted", ("طرد المحذوفين", "طرد الحسابات المحذوفه"), section=S, min_rank=Rank.MANAGER,
                  description="يطرد الحسابات المحذوفة اللي تعرفها زهو", order=62)
async def cmd_kick_deleted(cx: CommandContext) -> None:
    svc, chat_id = cx.services, cx.chat.id
    rights = await svc.perms.bot_rights(cx.bot, chat_id)
    if rights is None or not rights.can_restrict_members:
        await cx.reply(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT))
        return
    if chat_id in _scanning:
        await cx.reply(T.DELETED_BUSY)
        return
    _scanning.add(chat_id)
    status = await cx.reply(T.DELETED_SCANNING)
    checked = kicked = 0
    try:
        rows = await svc.db.fetchall(
            "SELECT user_id FROM group_members WHERE chat_id = ? AND rank = 0 ORDER BY last_seen ASC LIMIT ?",
            (chat_id, DELETED_SCAN_LIMIT))
        for r in rows:
            try:
                m = await cx.bot.get_chat_member(chat_id, r["user_id"])
            except TelegramError:
                continue
            checked += 1
            if m.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                continue
            if (m.user.first_name or "") in _DELETED_NAMES and not m.user.username and not m.user.is_bot:
                try:
                    await mod.apply(cx.bot, chat_id, m.user.id, "kick", None)
                    kicked += 1
                except TelegramError:
                    pass
            await asyncio.sleep(0.05)
    finally:
        _scanning.discard(chat_id)
    await svc.audit.log("kick_deleted", chat_id=chat_id, actor_id=cx.user.id, details={"count": kicked})
    try:
        await status.edit_text(T.DELETED_DONE.format(checked=checked, n=kicked))
    except (BadRequest, AttributeError):
        await cx.reply(T.DELETED_DONE.format(checked=checked, n=kicked))


# ── رفع القيود ──────────────────────────────────────
@registry.command("lift_all", ("رفع القيود", "فك القيود", "الغاء القيود"), section=S, min_rank=Rank.MANAGER,
                  args="target", usage="بالرد/اليوزر/الايدي", description="يفك الحظر والكتم والتقييد مرة وحدة",
                  order=14)
async def cmd_lift_all(cx: CommandContext) -> None:
    svc = cx.services
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "رفع القيود @username")
        return
    rights = await svc.perms.bot_rights(cx.bot, cx.chat.id)
    if rights is None or not rights.can_restrict_members:
        await cx.reply(T.BOT_MISSING_RIGHT.format(right=T.RIGHT_RESTRICT))
        return
    try:
        await mod.lift(cx.bot, cx.chat.id, target.user_id, "ban")
        member = await cx.bot.get_chat_member(cx.chat.id, target.user_id)
        if member.status == ChatMemberStatus.RESTRICTED:
            await mod.lift(cx.bot, cx.chat.id, target.user_id, "mute")
    except BadRequest:
        pass
    except TelegramError as e:
        log.info("فشل رفع القيود: %s", e)
        await cx.reply(T.PUNISH_FAILED)
        return
    for kind in ("ban", "mute", "restrict"):
        await svc.punishments.lift(cx.chat.id, target.user_id, kind, cx.user.id)
    await svc.audit.log("lift_all", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=target.user_id)
    await cx.reply(T.LIFT_ALL_DONE.format(mention=mention(target.user_id, target.name),
                                          actor=mention(cx.user.id, cx.user.full_name)))

