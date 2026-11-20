"""اختبارات: تقييم الأعضاء، إيقاف زهو، وتعطيل البوت."""
from types import SimpleNamespace

from telegram import Chat, Message, PhotoSize, Update, User

from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.systems import botstate, social
from tests.test_flow import ALI, CREATOR, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)
    await say(env, ALI, "هلا")
    await say(env, SARA, "هلا")


def _q(user_id, answers):
    async def answer(text=None, show_alert=False):
        answers.append(text)
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id, full_name=f"U{user_id}"), answer=answer)


def _msg(edits):
    async def edit_text(text, reply_markup=None):
        edits.append((text, reply_markup))
    return SimpleNamespace(chat=CHAT, photo=None, edit_text=edit_text)


# ── التقييم ──
async def test_profile_shows_rating_section_and_buttons(env):
    await _setup(env)
    out = await say(env, SARA, "ملفه", reply_to=ALI)
    assert "إنسان جميل ✨: <b>0</b>" in out and "إنسان سيئ 👎🏻: <b>0</b>" in out and "/10" in out


async def test_rating_buttons(env):
    svc, bot, _ = env
    await _setup(env)
    answers, edits = [], []
    msg = _msg(edits)
    await social.on_rating_button(_q(SARA, answers), msg, svc, bot, str(ALI), "g", "-")
    await social.on_rating_button(_q(CREATOR, answers), msg, svc, bot, str(ALI), "g", "-")
    await social.on_rating_button(_q(9999901, answers), msg, svc, bot, str(ALI), "b", "-")
    assert "إنسان جميل ✨: <b>2</b>" in edits[-1][0] and "إنسان سيئ 👎🏻: <b>1</b>" in edits[-1][0]
    kb = edits[-1][1].inline_keyboard
    assert kb[0][0].text == "إنسان جميل ✨ 2" and len(kb[1]) == 5 and kb[2][-1].text == "10"
    # الضغط مرة ثانية يلغي، وتغيير الرأي يبدّل
    await social.on_rating_button(_q(SARA, answers), msg, svc, bot, str(ALI), "g", "-")
    assert "انشال" in answers[-1]
    await social.on_rating_button(_q(SARA, answers), msg, svc, bot, str(ALI), "b", "-")
    good, bad, _, _ = await svc.ratings.summary(GROUP, ALI)
    assert (good, bad) == (1, 2)
    # الدرجات من 10
    for uid, n in ((SARA, 10), (CREATOR, 8), (9999901, 6)):
        await social.on_rating_button(_q(uid, answers), msg, svc, bot, str(ALI), "s", str(n))
    _, _, avg, voters = await svc.ratings.summary(GROUP, ALI)
    assert voters == 3 and abs(avg - 8.0) < 0.01
    assert "<b>8.0</b>/10" in edits[-1][0] and "★★★★☆" in edits[-1][0]
    # ما يقيّم نفسه
    await social.on_rating_button(_q(ALI, answers), msg, svc, bot, str(ALI), "g", "-")
    assert "نفسك" in answers[-1]


async def test_rate_command_and_top(env):
    await _setup(env)
    assert "9/10" in await say(env, SARA, "قيمه 9", reply_to=ALI)
    assert "رقم من 1" in await say(env, SARA, "قيمه 11", reply_to=ALI)
    await say(env, CREATOR, "قيمه 7", reply_to=ALI)
    await env[0].ratings.set_score(GROUP, ALI, 9999902, 8)
    out = await say(env, CREATOR, "الأعلى تقييماً")
    assert "8.0" in out


# ── إيقاف زهو ──
async def test_pause_keeps_silent_protection(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب بالحظر")
    out = await say(env, CREATOR, "/إيقاف زهو")
    assert "إِيـقَـاف" in out and "/فتح زهو" in out
    # الأوامر والردود ما تشتغل
    assert await say(env, CREATOR, "ايدي") is None
    assert await say(env, ALI, "ملفي") is None
    # السب ينمسح بس، بدون حظر وبدون رسالة
    bot.calls.clear()
    assert await say(env, ALI, "كسمك") is None
    assert bot.calls[0][0] == "delete" and not any(c[0] == "ban" for c in bot.calls)
    assert not await svc.punishments.is_active(GROUP, ALI, "ban")
    # «بوت» يذكّر
    assert "نص خدماته" in await say(env, ALI, "بوت")
    # الأعضاء ما يگدرون يشغّلونها
    assert await say(env, ALI, "/فتح زهو") is None
    assert "تَـشْـغِـيـل" in await say(env, CREATOR, "/فتح زهو")
    assert str(CREATOR) in await say(env, CREATOR, "ايدي")


async def test_pause_locks_delete_silently(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, CREATOR, "قفل الصور")
    await say(env, CREATOR, "ايقاف زهو")
    msg = Message(next(_mid), None, CHAT, from_user=User(ALI, "A", False), photo=[PhotoSize("f", "u", 1, 1)])
    msg.set_bot(bot)
    bot.calls.clear()
    bot.sent.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    assert bot.calls[0][0] == "delete" and bot.sent == []


async def test_pause_needs_manager(env):
    await _setup(env)
    assert "يحتاج رتبة" in await say(env, ALI, "ايقاف زهو")


# ── تعطيل البوت ──
async def test_disable_stops_everything(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    assert "يحتاج رتبة" in await say(env, SARA, "/تعطيل البوت")  # يحتاج مالك
    out = await say(env, CREATOR, "/تعطيل البوت")
    assert "تَـعْـطِـيـل" in out
    bot.calls.clear()
    assert await say(env, ALI, "كسمك") is None
    assert bot.calls == []  # ولا حتى مسح
    assert await say(env, ALI, "بوت") is None
    assert await say(env, CREATOR, "/فتح زهو") is None  # بالتعطيل بس «تفعيل البوت»
    assert "تَـفْـعِـيـل" in await say(env, CREATOR, "/تفعيل البوت")
    assert await botstate.get_state(svc, GROUP) == botstate.ON


async def test_slash_arabic_parsing():
    from zhoo.core.commands import registry
    import zhoo.app  # noqa: F401
    assert registry.parse("/إيقاف زهو").command.key == "bot_pause"
    assert registry.parse("/start") is None
