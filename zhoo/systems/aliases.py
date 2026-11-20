"""اختصارات الأوامر: المدير يسمي أي أمر باسم جديد (مثل «تق» بدل «تقييد»).

- الاختصار يرث صلاحيات الأمر الأصلي، فما يفتح باب لأحد.
- ما يصير الاختصار يطابق أمر موجود، ولا يتكرر.
"""
from __future__ import annotations

from zhoo.core import conversation
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc
from zhoo.core.normalize import normalize, split_tokens
from zhoo.core.ranks import Rank

S = "replies"
EDIT_RANK = Rank.MANAGER
VIEW_RANK = Rank.ADMIN
MAX_ALIASES = 100
MAX_WORDS = 3
MAX_LEN = 25


def alias_key(text: str) -> str:
    return " ".join(normalize(w) for w in text.split())


async def expand(svc: Services, chat_id: int, text: str) -> str | None:
    """إذا الرسالة تبدأ باختصار، يرجع النص بعد تبديله باسم الأمر الأصلي."""
    aliases = await svc.aliases.all(chat_id)
    if not aliases or not text:
        return None
    tokens = split_tokens(text)
    for n in range(min(MAX_WORDS, len(tokens)), 0, -1):
        hit = aliases.get(" ".join(normalize(t[0]) for t in tokens[:n]))
        if hit is None:
            continue
        cmd = registry.get(hit[1])
        if cmd is None:
            return None
        return cmd.display_name + text[tokens[n - 1][2]:]
    return None


# ── إضافة اختصار (بخطوات) ───────────────────────────
@registry.command("alias_add", ("اضف امر", "اضافة امر", "إضافة أمر", "اضافه امر"), section=S,
                  min_rank=EDIT_RANK, description="يضيف اختصار لأي أمر (مثل: تق ← تقييد)", order=30)
async def cmd_alias_add(cx: CommandContext) -> None:
    cx.services.conversations.start(cx.chat.id, cx.user.id, "alias_add", "old")
    await cx.reply(T.ALIAS_ASK_OLD)


@conversation.handler("alias_add")
async def _alias_flow(svc: Services, context, msg, chat, user, p) -> None:
    text = (msg.text or "").strip()
    if p.step == "old":
        parsed = registry.parse(text) if text else None
        if parsed is None or parsed.args:
            await msg.reply_text(T.ALIAS_NOT_COMMAND)
            return
        p.data.update(key=parsed.command.key, old=parsed.command.display_name)
        p.step = "new"
        await msg.reply_text(T.ALIAS_ASK_NEW.format(old=esc(parsed.command.display_name)))
        return

    words = text.split()
    if not text or not 1 <= len(words) <= MAX_WORDS or len(text) > MAX_LEN:
        await msg.reply_text(T.ALIAS_BAD)
        return
    if registry.parse(text) is not None:
        await msg.reply_text(T.ALIAS_CONFLICT.format(alias=esc(text)))
        return
    aliases = await svc.aliases.all(chat.id)
    key = alias_key(text)
    if key in aliases:
        old_cmd = registry.get(aliases[key][1])
        await msg.reply_text(T.ALIAS_EXISTS.format(alias=esc(text), old=esc(old_cmd.display_name if old_cmd else "-")))
        return
    if len(aliases) >= MAX_ALIASES:
        svc.conversations.end(chat.id, user.id)
        await msg.reply_text(T.ALIASES_LIMIT.format(n=MAX_ALIASES))
        return
    await svc.aliases.add(chat.id, key, text, p.data["key"], user.id)
    await svc.audit.log("alias_add", chat_id=chat.id, actor_id=user.id,
                        details={"alias": text, "command": p.data["key"]})
    svc.conversations.end(chat.id, user.id)
    await msg.reply_text(T.ALIAS_ADDED.format(alias=esc(text), old=esc(p.data["old"])))


# ── حذف وعرض ────────────────────────────────────────
async def _delete(svc: Services, chat_id: int, user_id: int, text: str) -> str:
    key = alias_key(text.strip())
    if not key or not await svc.aliases.remove(chat_id, key):
        return T.ALIAS_NOT_FOUND
    await svc.audit.log("alias_remove", chat_id=chat_id, actor_id=user_id, details={"alias": text.strip()})
    return T.ALIAS_DELETED.format(alias=esc(text.strip()))


@registry.command("alias_del", ("حذف امر", "حذف أمر", "مسح امر"), section=S, min_rank=EDIT_RANK, args="text",
                  usage="اختياري: الاختصار", description="يحذف اختصار", order=31)
async def cmd_alias_del(cx: CommandContext) -> None:
    if cx.raw_args.strip():
        await cx.reply(await _delete(cx.services, cx.chat.id, cx.user.id, cx.raw_args))
        return
    cx.services.conversations.start(cx.chat.id, cx.user.id, "alias_del", "name")
    await cx.reply(T.ALIAS_ASK_DELETE)


@conversation.handler("alias_del")
async def _alias_del_flow(svc: Services, context, msg, chat, user, p) -> None:
    svc.conversations.end(chat.id, user.id)
    await msg.reply_text(await _delete(svc, chat.id, user.id, msg.text or ""))


@registry.command("alias_list", ("الاوامر المضافه", "الأوامر المضافة", "الاختصارات"), section=S,
                  min_rank=VIEW_RANK, description="يعرض كل الاختصارات", order=32)
async def cmd_alias_list(cx: CommandContext) -> None:
    aliases = await cx.services.aliases.all(cx.chat.id)
    if not aliases:
        await cx.reply(f"{T.ALIASES_HEADER}\n{T.ALIASES_EMPTY}")
        return
    lines = []
    for display, key in sorted(aliases.values()):
        cmd = registry.get(key)
        if cmd:
            lines.append(f"▫️ <code>{esc(display)}</code> ← <code>{esc(cmd.display_name)}</code>")
    await cx.reply(f"{T.ALIASES_HEADER}\n" + "\n".join(lines))


@registry.command("alias_clear", ("مسح الاوامر المضافه", "مسح الأوامر المضافة", "مسح الاختصارات"), section=S,
                  min_rank=EDIT_RANK, description="يمسح كل الاختصارات", order=33)
async def cmd_alias_clear(cx: CommandContext) -> None:
    await cx.services.aliases.clear(cx.chat.id)
    await cx.services.audit.log("alias_clear", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.ALIASES_CLEARED)
