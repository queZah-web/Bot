"""اختبارات نظام العقوبات من البداية للنهاية."""
import time

import pytest

from zhoo.core.durations import DurationError, format_duration, parse_duration
from zhoo.core.moderation import PunishDecision as D, check_punish
from zhoo.core.ranks import Rank
from tests.test_flow import ALI, BOT_ID, CREATOR, DEV, GROUP, SARA, env, say  # noqa: F401


# ── المدد ──
@pytest.mark.parametrize("text,secs,rest", [
    ("10د سبام", 600, "سبام"),
    ("2س", 7200, ""),
    ("3 ي ازعاج كثير", 3 * 86400, "ازعاج كثير"),
    ("١٠د", 600, ""),
    ("ساعتين", 7200, ""),
    ("1ا", 7 * 86400, ""),
    ("سبام فقط", None, "سبام فقط"),
    ("", None, ""),
])
def test_parse_duration(text, secs, rest):
    assert parse_duration(text) == (secs, rest)


def test_duration_limits():
    with pytest.raises(DurationError):
        parse_duration("999ي")


def test_format_duration():
    assert format_duration(600) == "10 دقيقة"
    assert format_duration(86400) == "يوم"
    assert format_duration(7200) == "ساعتين"


# ── القرار ──
def test_decisions():
    kw = dict(is_self=False, is_this_bot=False, target_is_bot=False)
    assert check_punish(Rank.ADMIN, Rank.MEMBER, Rank.MEMBER, "mute", **kw) == D.OK
    assert check_punish(Rank.ADMIN, Rank.ADMIN, Rank.MEMBER, "mute", **kw) == D.HIGHER
    assert check_punish(Rank.OWNER, Rank.ADMIN, Rank.ADMIN, "ban", **kw) == D.TG_ADMIN
    assert check_punish(Rank.DEVELOPER, Rank.CREATOR, Rank.CREATOR, "ban", **kw) == D.PROTECTED
    assert check_punish(Rank.OWNER, Rank.MEMBER, Rank.MEMBER, "mute",
                        is_self=False, is_this_bot=False, target_is_bot=True) == D.OTHER_BOT
    assert check_punish(Rank.OWNER, Rank.MEMBER, Rank.MEMBER, "ban",
                        is_self=False, is_this_bot=True, target_is_bot=True) == D.BOT_SELF


# ── التدفق الكامل ──
async def test_mute_with_duration_and_reason(env):
    svc, bot, _ = env
    out = await say(env, CREATOR, "كتم 30د سبام", reply_to=ALI)
    assert "تَـمَّ الـكَـتْـم" in out and "30 دقيقة" in out and "سبام" in out
    call = bot.calls[-1]
    assert call[0] == "restrict" and call[2] is False and call[3] > time.time()
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_unmute(env):
    svc, bot, _ = env
    await say(env, CREATOR, "كتم", reply_to=ALI)
    out = await say(env, CREATOR, "فك الكتم", reply_to=ALI)
    assert "فَـكُّ الـكَـتْـم" in out
    assert not await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_ban_needs_manager(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    assert "يحتاج رتبة" in await say(env, SARA, "حظر", reply_to=ALI)
    assert "تَـمَّ الـكَـتْـم" in await say(env, SARA, "كتم", reply_to=ALI)


async def test_cannot_punish_equal_or_creator(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    await svc.members.set_rank(GROUP, ALI, Rank.MANAGER, CREATOR)
    assert "أعلى منك" in await say(env, SARA, "كتم", reply_to=ALI)
    assert "محمي" in await say(env, DEV, "حظر", reply_to=CREATOR)
    assert "نفسي" in await say(env, CREATOR, "حظر", reply_to=BOT_ID)


async def test_kick_is_ban_then_unban(env):
    bot = env[1]
    out = await say(env, CREATOR, "طرد ازعاج", reply_to=ALI)
    assert "تَـمَّ الـطَّـرْد" in out
    assert [c[0] for c in bot.calls[-2:]] == ["ban", "unban"]


async def test_warn_reaches_limit_and_auto_mutes(env):
    svc, bot, _ = env
    await say(env, CREATOR, "عدد التحذيرات 2")
    out = await say(env, CREATOR, "تحذير سب", reply_to=ALI)
    assert "1/2" in out
    out = await say(env, CREATOR, "تحذير", reply_to=ALI)
    assert "2/2" in out and "العقوبة التلقائية" in out
    assert await svc.punishments.is_active(GROUP, ALI, "mute")
    assert await svc.punishments.warning_count(GROUP, ALI) == 0


async def test_warn_action_setting(env):
    out = await say(env, CREATOR, "عقوبة التحذيرات طرد")
    assert "طرد" in out
    assert "اختر" in await say(env, CREATOR, "عقوبة التحذيرات شي غريب")


async def test_bad_duration(env):
    assert "غير صحيحة" in await say(env, CREATOR, "كتم 999ي", reply_to=ALI)


async def test_bot_without_rights(env):
    bot = env[1]
    bot.admins.pop(BOT_ID)
    assert "مشرفة" in await say(env, CREATOR, "كتم", reply_to=ALI)


async def test_lists_and_log(env):
    await say(env, ALI, "هلا")  # حتى ينحفظ اسمه
    await say(env, CREATOR, "حظر 1ي", reply_to=ALI)
    out = await say(env, CREATOR, "المحظورين")
    assert "U3000003" in out and "⏳" in out
    out = await say(env, CREATOR, "سجل العقوبات")
    assert "حظر" in out


async def test_sentence_starting_with_ban_word_is_ignored(env):
    assert await say(env, CREATOR, "حظر الروابط شي زين") is None


async def test_undo_button(env):
    from types import SimpleNamespace

    from zhoo.systems.punish import on_undo_button
    svc, bot, _ = env
    await say(env, CREATOR, "كتم", reply_to=ALI)
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append(text)

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), text_html="عقوبة", edit_text=edit_text)
    # عضو عادي ما يكدر يتراجع
    q = SimpleNamespace(from_user=SimpleNamespace(id=SARA, full_name="Sara"), answer=answer)
    await on_undo_button(q, msg, svc, bot, "m", str(ALI))
    assert "لا تسمح" in answers[-1] and not edits
    # المنشئ يكدر
    q = SimpleNamespace(from_user=SimpleNamespace(id=CREATOR, full_name="Creator"), answer=answer)
    await on_undo_button(q, msg, svc, bot, "m", str(ALI))
    assert edits and "تراجع بواسطة" in edits[-1]
    assert not await svc.punishments.is_active(GROUP, ALI, "mute")
