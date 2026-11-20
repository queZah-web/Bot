"""حالة زهو بكل مجموعة:

  on        ← كلشي شغّال
  paused    ← «إيقاف زهو»: الحماية شغّالة بصمت (مسح بس، بدون كتم أو حظر أو تنبيهات)،
               وزهو ما ترد إلا على «بوت/زهو» بتذكير، وعلى أوامر التشغيل.
  disabled  ← «تعطيل البوت»: كلشي متوقف (لا حماية ولا ردود)، إلا أمر «تفعيل البوت».
"""
from __future__ import annotations

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import mention
from zhoo.core.ranks import Rank

S = "group"
ON, PAUSED, DISABLED = "on", "paused", "disabled"
PAUSE_RANK = Rank.MANAGER
DISABLE_RANK = Rank.OWNER

# الأوامر المسموحة بكل حالة (غيرها يتجاهل بصمت)
ALLOWED_WHEN = {
    PAUSED: {"bot_resume", "bot_disable", "bot_enable", "bot_pause", "zhoo"},
    DISABLED: {"bot_enable"},
}


async def get_state(svc: Services, chat_id: int) -> str:
    if chat_id > 0:  # الخاص دائماً شغّال
        return ON
    state = await svc.group_settings.get(chat_id, "bot_state")
    return state if state in (ON, PAUSED, DISABLED) else ON


async def is_quiet(svc: Services, chat_id: int) -> bool:
    """موقوفة أو معطّلة: لا رسائل ولا عقوبات."""
    return await get_state(svc, chat_id) != ON


async def is_active(svc: Services, chat_id: int) -> bool:
    """الحماية تشتغل (شغّالة أو موقوفة)."""
    return await get_state(svc, chat_id) != DISABLED


async def _set(cx: CommandContext, state: str, same_text: str, done_text: str) -> None:
    if await get_state(cx.services, cx.chat.id) == state:
        await cx.reply(same_text)
        return
    old = await cx.services.group_settings.set(cx.chat.id, "bot_state", state, cx.user.id)
    await cx.services.audit.log("bot_state", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"from": old, "to": state})
    cx.services.conversations.end(cx.chat.id, cx.user.id)
    await cx.reply(done_text.format(actor=mention(cx.user.id, cx.user.full_name)))


async def _pause(cx): await _set(cx, PAUSED, T.BOT_ALREADY_PAUSED, T.BOT_PAUSED)          # noqa: E704
async def _resume(cx): await _set(cx, ON, T.BOT_ALREADY_ON, T.BOT_RESUMED)                # noqa: E704
async def _disable(cx): await _set(cx, DISABLED, T.BOT_ALREADY_DISABLED, T.BOT_DISABLED)  # noqa: E704
async def _enable(cx): await _set(cx, ON, T.BOT_ALREADY_ON, T.BOT_ENABLED)                # noqa: E704


registry.command("bot_pause", ("ايقاف زهو", "إيقاف زهو"), section=S, min_rank=PAUSE_RANK,
                 description="يوقف ردود زهو، والحماية تبقى بصمت (مسح بس)", order=20)(_pause)
registry.command("bot_resume", ("فتح زهو", "تشغيل زهو"), section=S, min_rank=PAUSE_RANK,
                 description="يرجع كل خدمات زهو بعد الإيقاف", order=21)(_resume)
registry.command("bot_disable", ("تعطيل البوت", "تعطيل زهو"), section=S, min_rank=DISABLE_RANK,
                 description="يعطل زهو كلياً (لا حماية ولا ردود)", order=22)(_disable)
registry.command("bot_enable", ("تفعيل البوت", "تفعيل زهو"), section=S, min_rank=DISABLE_RANK,
                 description="يرجع زهو بعد التعطيل", order=23)(_enable)
