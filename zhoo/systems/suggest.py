"""«قصدك: حظر؟» — إذا مشرف كتب أمر عقوبة/رتبة بغلطة حرف وحدة (مثل «حضر» بالرد على شخص).

حتى ما تزعج السوالف العادية: بس للإدارة، وبس إذا الرسالة رد على شخص أو بيها يوزر/ايدي،
وبس لأوامر تحتاج هدف (عقوبات، رتب...).
"""
from __future__ import annotations

from telegram import Message

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import Services
from zhoo.core.normalize import normalize
from zhoo.core.ratelimit import RateLimiter
from zhoo.core.ranks import Rank

_limiter = RateLimiter(1, 30)
_index: dict[str, str] | None = None     # الكلمة الأولى الموحدة ← اسم الأمر مثل ما ينكتب


def _build() -> dict[str, str]:
    out: dict[str, str] = {}
    for cmd in registry.commands:
        if cmd.args not in ("target", "punish") or cmd.min_rank < Rank.ADMIN:
            continue
        for name in cmd.names:
            words = normalize(name).split()
            if len(words) == 1 and len(words[0]) >= 3:
                out.setdefault(words[0], name)
    return out


def _one_edit(a: str, b: str) -> bool:
    """فرق حرف واحد بالضبط (تبديل، زيادة، نقص، أو قلب حرفين متجاورين)."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def suggestion(text: str) -> str | None:
    global _index
    if _index is None:
        _index = _build()
    words = normalize(text or "").split()
    if not 1 <= len(words) <= 3 or len(words[0]) < 3 or words[0] in _index:
        return None
    hits = {name for key, name in _index.items() if _one_edit(words[0], key)}
    return hits.pop() if len(hits) == 1 else None


async def maybe_suggest(svc: Services, bot, msg: Message, chat, user) -> bool:
    has_target = msg.reply_to_message is not None or "@" in (msg.text or "") or any(
        w.isdigit() and len(w) >= 5 for w in (msg.text or "").split())
    if not has_target:
        return False
    name = suggestion(msg.text)
    if name is None:
        return False
    rank = await svc.perms.rank_of(bot, chat.id, user.id)
    cmd = registry.parse(name, has_reply=True)
    if rank < Rank.ADMIN or cmd is None or rank < cmd.command.min_rank or not _limiter.hit((chat.id, user.id)):
        return False
    await msg.reply_text(T.DID_YOU_MEAN.format(cmd=name))
    return True
