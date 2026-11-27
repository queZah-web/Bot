"""الردود والردود المميزة.

- الرد العادي: ينرسل إذا الرسالة كلها هي الكلمة.
- الرد المميز: ينرسل إذا الكلمة موجودة بأي مكان بالرسالة (حتى بنص كليشة).
- كل رد يگدر يحتوي لحد 10 ردود (نص، يوزر، رابط، صورة، ملصق، فيديو، بصمة، ملف، تحويل...)
  وينختار واحد منهم عشوائياً.
- بالنص تگدر تستخدم: {الاسم} {اليوزر} {الايدي}
"""
from __future__ import annotations

import logging
import random

from telegram import Message, User
from telegram.error import TelegramError

from zhoo.core import conversation
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank
from zhoo.core.swear import normalize_word
from zhoo.repositories.replies import ReplyItem

log = logging.getLogger(__name__)
S = "replies"

EDIT_RANK = Rank.ADMIN
CLEAR_RANK = Rank.MANAGER
MAX_ITEMS = 10
MAX_REPLIES = {False: 300, True: 100}
MAX_WORDS = 5
MAX_LEN = 50
DONE_WORD = normalize("تم")
DISCARD_WORD = normalize("حذف")
ADD_CMD = {False: "اضف رد", True: "اضف رد مميز"}
LIST_CMD = {False: "الردود", True: "الردود المميزة"}


def trigger_key(text: str) -> str:
    """توحيد الكلمة: نفس طريقة كاشف السب (تشكيل، تطويل، رموز، تكرار حروف)."""
    return " ".join(w for w in (normalize_word(x) for x in (text or "").split()) if w)


# ── إرسال الرد ──────────────────────────────────────
def _fill(text: str | None, user: User) -> str | None:
    if not text:
        return text
    return (text.replace("{الاسم}", mention(user.id, user.full_name))
                .replace("{اليوزر}", f"@{esc(user.username)}" if user.username else esc(user.full_name))
                .replace("{الايدي}", f"<code>{user.id}</code>"))


async def send_item(msg: Message, item: ReplyItem, user: User) -> None:
    text = _fill(item.text, user)
    k = item.kind
    if k == "text":
        await msg.reply_text(text)
    elif k == "photo":
        await msg.reply_photo(item.file_id, caption=text)
    elif k == "video":
        await msg.reply_video(item.file_id, caption=text)
    elif k == "animation":
        await msg.reply_animation(item.file_id, caption=text)
    elif k == "document":
        await msg.reply_document(item.file_id, caption=text)
    elif k == "audio":
        await msg.reply_audio(item.file_id, caption=text)
    elif k == "voice":
        await msg.reply_voice(item.file_id, caption=text)
    elif k == "sticker":
        await msg.reply_sticker(item.file_id)
    elif k == "video_note":
        await msg.reply_video_note(item.file_id)


async def find_reply(svc: Services, chat_id: int, text: str) -> int | None:
    key = trigger_key(text)
    if not key:
        return None
    hit = (await svc.replies.triggers(chat_id, False)).get(key)
    if hit:
        return hit[0]
    padded = f" {key} "
    for trig, (reply_id, _) in (await svc.replies.triggers(chat_id, True)).items():
        if f" {trig} " in padded:
            return reply_id
    return None


async def maybe_reply(svc: Services, msg: Message, chat, user: User) -> bool:
    text = msg.text or msg.caption
    if not text:
        return False
    from zhoo.systems import zhoo_replies
    reply_id = await find_reply(svc, chat.id, text)
    if reply_id is None:
        return False
    if not zhoo_replies.allow(chat.id, user.id) or not svc.reply_limiter.hit(chat.id):
        return True          # نفس الشخص استلم رد قبل شوية: نسكت (وما نرد بردود زهو بدالها)
    items = await svc.replies.items(reply_id)
    if not items:
        return False
    try:
        await send_item(msg, random.choice(items), user)
    except TelegramError as e:
        log.info("فشل إرسال الرد: %s", e)
        return False
    return True


# ── إضافة رد (بخطوات) ───────────────────────────────
def capture(msg: Message) -> ReplyItem | None:
    """يحوّل أي رسالة (حتى المحوّلة) لعنصر رد قابل للحفظ."""
    caption = msg.caption_html if msg.caption else None
    if msg.text:
        return ReplyItem("text", None, msg.text_html)
    if msg.sticker:
        return ReplyItem("sticker", msg.sticker.file_id, None)
    if msg.animation:
        return ReplyItem("animation", msg.animation.file_id, caption)
    if msg.photo:
        return ReplyItem("photo", msg.photo[-1].file_id, caption)
    if msg.video:
        return ReplyItem("video", msg.video.file_id, caption)
    if msg.video_note:
        return ReplyItem("video_note", msg.video_note.file_id, None)
    if msg.voice:
        return ReplyItem("voice", msg.voice.file_id, caption)
    if msg.audio:
        return ReplyItem("audio", msg.audio.file_id, caption)
    if msg.document:
        return ReplyItem("document", msg.document.file_id, caption)
    return None


async def _start_add(cx: CommandContext, special: bool) -> None:
    cx.services.conversations.start(cx.chat.id, cx.user.id, "reply_add", "word", special=special, items=[])
    await cx.reply(T.REPLY_ASK_WORD_SPECIAL if special else T.REPLY_ASK_WORD)


async def _save(svc: Services, msg: Message, chat, user, p) -> None:
    special = p.data["special"]
    await svc.replies.add(chat.id, p.data["key"], p.data["word"], special, p.data["items"], user.id)
    await svc.audit.log("reply_add", chat_id=chat.id, actor_id=user.id,
                        details={"word": p.data["word"], "special": special, "items": len(p.data["items"])})
    svc.conversations.end(chat.id, user.id)
    await msg.reply_text(T.REPLY_SAVED.format(kind=T.REPLY_KINDS[special], word=esc(p.data["word"]),
                                              count=len(p.data["items"])))


@conversation.handler("reply_add")
async def _reply_flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    from zhoo.systems import aliases
    special = p.data["special"]

    if p.step == "word":
        text = (msg.text or "").strip()
        key = trigger_key(text)
        if not text or not key or len(text.split()) > MAX_WORDS or len(text) > MAX_LEN:
            await msg.reply_text(T.REPLY_WORD_BAD)
            return
        if registry.parse(text) is not None or await aliases.expand(svc, chat.id, text):
            await msg.reply_text(T.REPLY_WORD_IS_COMMAND.format(word=esc(text)))
            return
        existing = await svc.replies.triggers(chat.id, special)
        if key in existing:
            await msg.reply_text(T.REPLY_EXISTS.format(word=esc(text)))
            return
        if len(existing) >= MAX_REPLIES[special]:
            svc.conversations.end(chat.id, user.id)
            await msg.reply_text(T.REPLIES_LIMIT.format(n=MAX_REPLIES[special]))
            return
        p.data.update(word=text, key=key)
        p.step = "content"
        await msg.reply_text(T.REPLY_ASK_CONTENT.format(word=esc(text)))
        return

    # خطوة المحتوى
    if msg.text:
        word = normalize(msg.text.strip())
        if word == DONE_WORD:
            if not p.data["items"]:
                await msg.reply_text(T.REPLY_NO_ITEMS)
                return
            await _save(svc, msg, chat, user, p)
            return
        if word == DISCARD_WORD:
            svc.conversations.end(chat.id, user.id)
            await msg.reply_text(T.REPLY_DISCARDED)
            return
    item = capture(msg)
    if item is None:
        await msg.reply_text(T.REPLY_UNSUPPORTED)
        return
    p.data["items"].append(item)
    left = MAX_ITEMS - len(p.data["items"])
    if left <= 0:
        await _save(svc, msg, chat, user, p)
        return
    await msg.reply_text(T.REPLY_ITEM_ADDED.format(left=left))


async def _add_normal(cx): await _start_add(cx, False)     # noqa: E704
async def _add_special(cx): await _start_add(cx, True)     # noqa: E704


registry.command("reply_add", ("اضف رد", "اضافة رد", "إضافة رد", "اضافه رد"), section=S, min_rank=EDIT_RANK,
                 description="يضيف رد ينرسل إذا انكتبت الكلمة (حتى 10 ردود)", order=1)(_add_normal)
registry.command("reply_add_special", ("اضف رد مميز", "اضافة رد مميز", "إضافة رد مميز", "اضافه رد مميز"),
                 section=S, min_rank=EDIT_RANK,
                 description="رد ينرسل حتى لو الكلمة جت بنص كليشة", order=2)(_add_special)


# ── عرض الردود ──────────────────────────────────────
async def _list(cx: CommandContext, special: bool) -> None:
    rows = await cx.services.replies.counts(cx.chat.id, special)
    header = T.REPLIES_HEADER[special]
    if not rows:
        await cx.reply(f"{header}\n{T.REPLIES_EMPTY.format(cmd=ADD_CMD[special])}")
        return
    lines = [T.REPLY_LINE.format(word=esc(r["display"]), n=r["n"]) for r in rows[:150]]
    await cx.reply(f"{header}\n" + "\n".join(lines) + "\n" + T.REPLIES_FOOTER.format(n=len(rows)))


async def _list_normal(cx): await _list(cx, False)      # noqa: E704
async def _list_special(cx): await _list(cx, True)      # noqa: E704


registry.command("reply_list", ("الردود",), section=S, min_rank=EDIT_RANK,
                 description="يعرض الردود العادية", order=3)(_list_normal)
registry.command("reply_list_special", ("الردود المميزه", "الردود المميزة"), section=S, min_rank=EDIT_RANK,
                 description="يعرض الردود المميزة وأسماءها", order=4)(_list_special)


# ── حذف الردود ──────────────────────────────────────
async def _delete(svc: Services, chat_id: int, user_id: int, text: str, special: bool) -> str:
    key = trigger_key(text)
    if not key or not await svc.replies.remove(chat_id, key, special):
        return T.REPLY_NOT_FOUND.format(cmd=LIST_CMD[special])
    await svc.audit.log("reply_remove", chat_id=chat_id, actor_id=user_id,
                        details={"word": text.strip(), "special": special})
    return T.REPLY_DELETED.format(word=esc(text.strip()))


async def _start_delete(cx: CommandContext, special: bool) -> None:
    if cx.raw_args.strip():
        await cx.reply(await _delete(cx.services, cx.chat.id, cx.user.id, cx.raw_args, special))
        return
    cx.services.conversations.start(cx.chat.id, cx.user.id, "reply_del", "name", special=special)
    await cx.reply(T.REPLY_ASK_DELETE)


@conversation.handler("reply_del")
async def _reply_del_flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    svc.conversations.end(chat.id, user.id)
    await msg.reply_text(await _delete(svc, chat.id, user.id, msg.text or "", p.data["special"]))


async def _del_normal(cx): await _start_delete(cx, False)     # noqa: E704
async def _del_special(cx): await _start_delete(cx, True)     # noqa: E704


registry.command("reply_del", ("حذف رد", "حذف الرد", "مسح رد"), section=S, min_rank=EDIT_RANK, args="text",
                 usage="اختياري: اسم الرد", description="يحذف رد عادي", order=5)(_del_normal)
registry.command("reply_del_special", ("حذف رد مميز", "حذف الرد المميز", "مسح رد مميز"), section=S,
                 min_rank=EDIT_RANK, args="text", usage="اختياري: اسم الرد",
                 description="يحذف رد مميز", order=6)(_del_special)


async def _clear(cx: CommandContext, special: bool) -> None:
    await cx.services.replies.clear(cx.chat.id, special)
    await cx.services.audit.log("reply_clear", chat_id=cx.chat.id, actor_id=cx.user.id, details={"special": special})
    await cx.reply(T.REPLIES_CLEARED.format(kind=LIST_CMD[special]))


async def _clear_normal(cx): await _clear(cx, False)      # noqa: E704
async def _clear_special(cx): await _clear(cx, True)      # noqa: E704


registry.command("reply_clear", ("مسح الردود",), section=S, min_rank=CLEAR_RANK,
                 description="يمسح كل الردود العادية", order=7)(_clear_normal)
registry.command("reply_clear_special", ("مسح الردود المميزه", "مسح الردود المميزة"), section=S,
                 min_rank=CLEAR_RANK, description="يمسح كل الردود المميزة", order=8)(_clear_special)
