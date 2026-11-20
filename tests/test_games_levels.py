"""اختبارات المرحلة 7: المستويات والألعاب."""
import time
from types import SimpleNamespace

import pytest

from zhoo.core import levels as L
from zhoo.data import game_bank as bank
from zhoo.systems import games
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)
    await say(env, ALI, "هلا")
    await say(env, SARA, "هلا")


# ── معادلة المستويات ──
def test_level_math():
    assert [L.threshold(n) for n in (1, 2, 5, 10)] == [100, 300, 1500, 5500]
    assert L.level_for(0) == 0 and L.level_for(99) == 0 and L.level_for(100) == 1 and L.level_for(5500) == 10
    level, have, need, ratio = L.progress(400)
    assert (level, have, need) == (2, 100, 300) and abs(ratio - 1 / 3) < 1e-9
    assert L.title_for(0) == "مبتدئ 🌱" and L.title_for(12) == "متألق 🌟" and L.title_for(99) == "خارق 💎"
    assert L.bar(0.5) == "▰▰▰▰▰▱▱▱▱▱"
    assert "🏆 بطل المسابقات" in L.badges(0, 0, 10, 0, None, 0)


# ── بنك المحتوى ──
def test_bank_is_valid():
    for level, items in bank.QUIZ.items():
        assert len(items) >= 15, level
        for q, answers in items:
            assert q.endswith("؟") and answers and games.make_keys(answers), q
    for q, answers in bank.RIDDLES:
        assert games.make_keys(answers), q
    for w in bank.WORDS:
        assert games.answer_keys(w), w
    assert len(bank.WORDS) >= 50 and len(bank.PHRASES) >= 20 and len(bank.RIDDLES) >= 20


def test_answer_matching_is_flexible():
    keys = games.make_keys(["الأسد", "السبع"])
    for guess in ("الاسد", "أسد", "اسد!", "  الأسَد  "):
        assert games.answer_keys(guess) & keys, guess
    assert games.answer_keys("١٩١٤") & games.make_keys(["1914"])
    assert games.answer_keys("ثاني اوكسيد الكاربون") & games.make_keys(bank.QUIZ["medium"][3][1])
    assert not games.answer_keys("نمر") & keys


# ── الخبرة ──
async def test_xp_from_messages_with_cooldown_and_no_spam(env):
    svc = env[0]
    await _setup(env)
    svc.xp_seen.clear()
    xp0, _ = await svc.levels.get(GROUP, ALI)
    await say(env, ALI, "مرحبا بالجميع شلونكم")
    xp1, _ = await svc.levels.get(GROUP, ALI)
    assert 8 <= xp1 - xp0 <= 15
    await say(env, ALI, "رسالة ثانية بسرعة")  # داخل المهلة
    assert (await svc.levels.get(GROUP, ALI))[0] == xp1
    svc.xp_seen[(GROUP, ALI)] = (time.monotonic() - 100, svc.xp_seen[(GROUP, ALI)][1])
    await say(env, ALI, "مرحبا بالجميع شلونكم")  # نفس الرسالة = ما تنحسب
    assert (await svc.levels.get(GROUP, ALI))[0] == xp1
    svc.xp_seen[(GROUP, ALI)] = (time.monotonic() - 100, "x")
    await say(env, ALI, "ok")  # أقل من 3 حروف ما تنحسب
    assert (await svc.levels.get(GROUP, ALI))[0] == xp1


async def test_level_card_and_boards(env):
    svc = env[0]
    await _setup(env)
    await svc.levels.add_xp(GROUP, ALI, 650)
    await svc.levels.add_xp(GROUP, SARA, 120)
    out = await say(env, ALI, "مستواي")
    assert "المستوى: <b>3</b>" in out and "#1" in out and "▰" in out
    assert "U3000003" in await say(env, CREATOR, "ترتيب المستويات")
    assert "U3000003" in await say(env, CREATOR, "ترتيب الأسبوع")
    assert "م3" in await say(env, CREATOR, "ترتيب المستويات")
    assert "مبتدئ" in await say(env, CREATOR, "الألقاب")
    assert "المستوى" in await say(env, ALI, "ملفي")


async def test_levels_toggle(env):
    await _setup(env)
    await say(env, CREATOR, "تعطيل المستويات")
    assert "معطّلة" in await say(env, ALI, "مستواي")


# ── الألعاب ──
async def _start(env, kind, level=None):
    svc, bot, ctx = env
    user = SimpleNamespace(id=CREATOR, full_name="C")
    err = await games.start(ctx, svc, GROUP, user, kind, level)
    assert err is None, err
    return svc.games[GROUP]


@pytest.mark.parametrize("kind", ["quiz", "scramble", "riddle", "math", "daily"])
async def test_each_game_correct_answer_wins(env, kind):
    svc = env[0]
    await _setup(env)
    game = await _start(env, kind)
    assert "الجائزة" in env[1].sent[-1]
    assert await say(env, SARA, "جواب غلط تماماً") is None
    out = await say(env, ALI, game.display)
    assert "جَـوَاب صَـح" in out and f"+{game.xp}" in out
    xp, wins = await svc.levels.get(GROUP, ALI)
    assert wins == 1 and xp >= game.xp
    assert GROUP not in svc.games


async def test_typing_game_rejects_copy_paste(env):
    svc = env[0]
    await _setup(env)
    game = await _start(env, "typing")
    copied = games.ZWNJ.join(game.display)
    await say(env, ALI, copied)
    assert any("النسخ" in m for m in env[1].sent)  # (لو العبارة تحية، زهو ترد عليها بعد التنبيه)
    assert "جَـوَاب صَـح" in await say(env, SARA, game.display)


async def test_one_game_at_a_time_and_timeout(env):
    svc, bot, ctx = env
    await _setup(env)
    game = await _start(env, "riddle")
    assert "شغّالة" in await say(env, ALI, "لغز")
    game.started_at -= 1000  # خلص الوقت
    await say(env, ALI, "جواب متأخر")
    assert "خِـلَـص الـوَقْـت" in bot.sent[-1] and game.display in bot.sent[-1]
    assert GROUP not in svc.games


async def test_stop_permissions(env):
    svc = env[0]
    await _setup(env)
    await say(env, ALI, "لغز")
    assert "اللي بدأ" in await say(env, SARA, "ايقاف اللعبة")
    assert "توقفت" in await say(env, ALI, "ايقاف اللعبة")
    assert "ماكو لعبة" in await say(env, ALI, "ايقاف اللعبة")


async def test_duel_only_two_players(env):
    svc = env[0]
    await _setup(env)
    out = await say(env, ALI, "تحدي", reply_to=SARA)
    game = svc.games[GROUP]
    assert game.players == frozenset({ALI, SARA})
    assert await say(env, CREATOR, game.display) is None  # الثالث ما ينحسب
    assert "جَـوَاب صَـح" in await say(env, SARA, game.display)
    svc.games.pop(("cd", GROUP), None)
    assert "نفسك" in await say(env, ALI, "تحدي", reply_to=ALI)


async def test_daily_riddle_once_per_day(env):
    svc = env[0]
    await _setup(env)
    game = await _start(env, "daily")
    await say(env, ALI, game.display)
    svc.games.pop(("cd", GROUP), None)
    assert "انحل من قبل" in await say(env, SARA, "لغز اليوم")


async def test_games_menu_and_button(env):
    svc, bot, ctx = env
    await _setup(env)
    assert "اختار لعبة" in await say(env, ALI, "الالعاب")
    answers = []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    q = SimpleNamespace(from_user=SimpleNamespace(id=ALI, full_name="A"), answer=answer)
    await games.on_menu_button(q, SimpleNamespace(chat=SimpleNamespace(id=GROUP)), svc, ctx, "scramble")
    assert answers[-1] == "🎮" and svc.games[GROUP].kind == "scramble"
    await games.on_menu_button(q, SimpleNamespace(chat=SimpleNamespace(id=GROUP)), svc, ctx, "quiz")
    assert "شغّالة" in answers[-1]


async def test_games_toggle_and_wins_board(env):
    await _setup(env)
    game = await _start(env, "riddle")
    await say(env, ALI, game.display)
    assert "U3000003" in await say(env, CREATOR, "ترتيب المسابقات")
    await say(env, CREATOR, "تعطيل الالعاب")
    assert "معطّلة" in await say(env, ALI, "لغز")


async def test_paused_bot_ignores_answers(env):
    svc = env[0]
    await _setup(env)
    game = await _start(env, "riddle")
    await say(env, CREATOR, "ايقاف زهو")
    assert await say(env, ALI, game.display) is None


async def test_answer_that_looks_like_a_command(env):
    """جواب لغز «الساعة» هو نفسه اسم أمر الوقت — لازم ينحسب جواب مو أمر."""
    svc = env[0]
    await _setup(env)
    game = await _start(env, "riddle")
    game.keys = games.make_keys(["الساعة"])
    game.display = "الساعة"
    assert "جَـوَاب صَـح" in await say(env, ALI, "الساعة")
    assert "ببغداد" in await say(env, ALI, "الساعة")  # بعد اللعبة يرجع أمر عادي
