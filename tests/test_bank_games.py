"""الألعاب الجديدة + «ماعرف» + صور اللعبة + بنك زهو."""
import random
from types import SimpleNamespace

import pytest
from telegram import Chat, Message, PhotoSize, Update, User

from zhoo.core import texts as T
from zhoo.data import game_bank as bank
from zhoo.handlers import router
from zhoo.systems import bank as B
from zhoo.systems import game_pics, games
from tests.test_flow import ALI, CREATOR, DEV, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")
NEW = ["picture", "flag", "capital", "opposite", "proverb", "truefalse", "count", "split"]


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()


async def _say(env, user, text, **kw):
    env[0].command_limiter._hits.clear()
    env[0].flood.reset((GROUP, user))
    return await say(env, user, text, **kw)


async def _start(env, kind, who=CREATOR):
    svc, bot, ctx = env
    svc.games.pop(("cd", GROUP), None)
    err = await games.start(ctx, svc, GROUP, SimpleNamespace(id=who, full_name="C"), kind)
    assert err is None, err
    return svc.games[GROUP]


# ── الألعاب الجديدة ──
@pytest.mark.parametrize("kind", NEW)
async def test_new_games_correct_answer_wins(env, kind):
    svc, bot, _ = env
    await _setup(env)
    for _ in range(5):                                # كذا سؤال عشوائي من كل لعبة
        game = await _start(env, kind)
        assert any("الجائزة" in (t or "") for t in bot.sent)
        assert await _say(env, SARA, "جواب غلط تماماً") is None
        out = await _say(env, ALI, game.display.replace(" ✅", "").replace(" ❌", ""))
        assert out and "جَـوَاب صَـح" in out, (kind, game.display)


async def test_picture_emoji_sent_alone(env):
    svc, bot, _ = env
    await _setup(env)
    bot.sent.clear()
    game = await _start(env, "picture")
    assert game.media[0] == "emoji" and bot.sent[-1] == game.media[1]     # الإيموجي برسالة لحاله (كبير)


async def test_split_needs_spaced_letters(env):
    await _setup(env)
    game = await _start(env, "split")
    word = game.display.replace(" ", "")
    assert await _say(env, ALI, word) is None                              # الكلمة نفسها ما تنحسب
    assert "جَـوَاب صَـح" in await _say(env, ALI, game.display)


async def test_truefalse_one_try_each(env):
    await _setup(env)
    game = await _start(env, "truefalse")
    wrong = "خطأ" if game.display.startswith("صح") else "صح"
    right = "صح" if game.display.startswith("صح") else "خطأ"
    assert await _say(env, ALI, wrong) is None
    assert await _say(env, ALI, right) is None                            # محاولته راحت
    assert "جَـوَاب صَـح" in await _say(env, SARA, right)


async def test_count_one_try(env):
    await _setup(env)
    game = await _start(env, "count")
    n = int(game.display)
    assert await _say(env, ALI, str(n + 1)) is None
    assert await _say(env, ALI, str(n)) is None
    assert "جَـوَاب صَـح" in await _say(env, SARA, str(n))


# ── ماعرف ──
async def test_starter_gives_up(env):
    svc = env[0]
    await _setup(env)
    game = await _start(env, "capital")
    assert await _say(env, ALI, "ماعرف") is None                          # مو صاحب اللعبة
    assert GROUP in svc.games
    out = await _say(env, CREATOR, "ما اعرف")
    assert "انْـكِـشَـف" in out and game.display in out and GROUP not in svc.games


async def test_menu_has_new_games(env):
    await _setup(env)
    await _say(env, CREATOR, "الالعاب")
    kb = env[1].last_kw["reply_markup"].inline_keyboard
    kinds = {b.callback_data for row in kb for b in row}
    assert {f"gm:{k}" for k in NEW} <= kinds


def test_content_has_no_duplicates_and_is_clean():
    from zhoo.core.swear import detector
    for name in ("PICTURES", "FLAGS", "CAPITALS", "OPPOSITES", "PROVERBS", "TRUE_FALSE"):
        items = [x[0] for x in getattr(bank, name)]
        assert len(items) == len(set(items)), name
    qs = [q for lvl in bank.QUIZ.values() for q, _ in lvl]
    assert len(qs) == len(set(qs)) and len(qs) >= 100
    assert not [w for p in bank.PICTURES for w in p[1] if detector.find(w)]


# ── صور اللعبة المضافة ──
async def _send_photo(env, user, file_id="PHOTO1"):
    svc, bot, ctx = env
    photo = [PhotoSize(file_id, "u", 10, 10)]
    msg = Message(next(_mid), None, CHAT, from_user=User(user, "U", False), photo=photo)
    msg.set_bot(bot)
    bot.sent.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return bot.sent[-1] if bot.sent else None


async def test_add_custom_picture_and_play(env, monkeypatch):
    svc, bot, _ = env
    await _setup(env)
    assert await _say(env, CREATOR, "اضف صورة للعبة") is None            # المطور بس
    assert "ارسل الصورة" in await _say(env, CREATOR, "اضف صورة للعبة مجموعة")
    assert "مو ملف" in await _say(env, CREATOR, "نص")
    assert "اكتب اسم" in await _send_photo(env, CREATOR)
    assert "تَـمَّ حِـفْـظ" in await _say(env, CREATOR, "برج إيفل، ايفل")
    monkeypatch.setattr(game_pics, "CUSTOM_CHANCE", 1.0)
    game = await _start(env, "picture")
    assert game.media == ("photo", "PHOTO1")
    assert "جَـوَاب صَـح" in await _say(env, ALI, "ايفل")
    assert "1" in await _say(env, CREATOR, "صور اللعبة")
    assert "انمسحت" in await _say(env, CREATOR, "مسح صورة اللعبة مجموعة برج ايفل")
    # المطور: صورة عامة
    await _say(env, DEV, "اضف صورة للعبة")
    await _send_photo(env, DEV, "PHOTO2")
    assert "بكل المجموعات" in await _say(env, DEV, "قلعة")


# ── البنك ──
async def _open(env, user):
    svc, bot, ctx = env
    q = SimpleNamespace(from_user=User(user, f"U{user}", False), answers=[])

    async def answer(text=None, show_alert=False):
        q.answers.append(text)
    q.answer = answer
    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edits=[])

    async def edit_text(text, reply_markup=None):
        msg.edits.append(text)
    msg.edit_text = edit_text
    await B.on_card_button(q, msg, svc, str(user), "diamond")
    return msg.edits[-1]


async def test_open_account_card_and_bonus(env):
    svc = env[0]
    await _setup(env)
    assert "انشاء حساب بنكي" in await _say(env, ALI, "حسابي")
    assert "اختار شكل بطاقتك" in await _say(env, ALI, "انشاء حساب بنكي")
    out = await _open(env, ALI)
    assert "الماسية" in out and "500" in out
    assert await B.cash(svc, GROUP, ALI) == 500
    assert "عندك حساب من قبل" in await _say(env, ALI, "انشاء حساب بنكي")
    # زر شخص ثاني ما يشتغل
    await _open(env, ALI)
    assert await B.cash(svc, GROUP, ALI) == 500                            # ما تنعطى الهدية مرتين


async def test_deposit_withdraw(env):
    svc = env[0]
    await _setup(env)
    await _open(env, ALI)
    assert "تَـمَّ الإِيـدَاع" in await _say(env, ALI, "ايداع 300")
    acc = await B.account(svc, GROUP, ALI)
    assert acc["balance"] == 300 and await B.cash(svc, GROUP, ALI) == 200
    assert "ما يكفي" in await _say(env, ALI, "سحب 5000")
    assert "تَـمَّ الـسَّـحْـب" in await _say(env, ALI, "سحب الكل")
    assert (await B.account(svc, GROUP, ALI))["balance"] == 0 and await B.cash(svc, GROUP, ALI) == 500
    assert "تَـمَّ الإِيـدَاع" in await _say(env, ALI, "ايداع الكل")
    assert await B.cash(svc, GROUP, ALI) == 0
    assert "الماسية" in await _say(env, ALI, "حسابي")


async def test_free_money_cooldowns(env):
    svc = env[0]
    await _setup(env)
    await _open(env, ALI)
    assert "بخشيش" in await _say(env, ALI, "بخشيش")
    assert "يرجع بعد" in await _say(env, ALI, "بخشيش")
    assert "+" in await _say(env, ALI, "كنز")
    assert "يرجع بعد" in await _say(env, ALI, "كنز")
    assert "عَـجَـلَـة" in await _say(env, ALI, "عجلة الحظ")
    assert "يرجع بعد" in await _say(env, ALI, "عجلة الحظ")
    assert await B.cash(svc, GROUP, ALI) > 500 or await B.wait_left(svc, GROUP, ALI, "shield")


async def test_luck_invest_speculate_keep_balance_valid(env, monkeypatch):
    svc = env[0]
    await _setup(env)
    await _open(env, ALI)
    assert "اكتب مبلغ" in await _say(env, ALI, "حظ")
    assert "اكتب مبلغ" in await _say(env, ALI, "حظ 10")                      # أقل من الحد
    assert "ما يكفي" in await _say(env, ALI, "حظ 9999")
    monkeypatch.setattr(random, "random", lambda: 0.1)
    assert "ربحت" in await _say(env, ALI, "حظ 100")
    assert await B.cash(svc, GROUP, ALI) == 600
    assert "يرجع بعد" in await _say(env, ALI, "حظ 100")
    assert "ربحت" in await _say(env, ALI, "استثمار 100")
    monkeypatch.setattr(random, "random", lambda: 0.9)
    before = await B.cash(svc, GROUP, ALI)
    assert "خسرت" in await _say(env, ALI, "مضاربة الكل")
    assert 0 <= await B.cash(svc, GROUP, ALI) < before


async def test_rob_rules(env, monkeypatch):
    svc = env[0]
    await _setup(env)
    await _open(env, ALI)
    await _open(env, SARA)
    assert "بالرد" in await _say(env, ALI, "زرف")
    assert "تزرف نفسك" in await _say(env, ALI, "زرف", reply_to=ALI)
    monkeypatch.setattr(random, "random", lambda: 0.1)                   # ينجح
    out = await _say(env, ALI, "زرف", reply_to=SARA)
    assert "زَرْفَـة نَـاجْـحَـة" in out
    assert await B.cash(svc, GROUP, ALI) > 500 and await B.cash(svc, GROUP, SARA) < 500
    assert "يرجع بعد" in await _say(env, ALI, "زرف", reply_to=SARA)
    # فلوس البنك محمية، والحماية تمنع الزرف
    await _say(env, SARA, "ايداع الكل")
    await svc.db.execute("DELETE FROM bank_cooldowns")
    assert "ما عنده كاش" in await _say(env, ALI, "زرف", reply_to=SARA)
    await svc.economy.change(GROUP, SARA, 3000, "admin_give")
    assert "تَـمَّ تَـفْـعِـيـل الـحِـمَـايَـة" in await _say(env, SARA, "حماية")
    assert "عنده حماية" in await _say(env, ALI, "زرف", reply_to=SARA)
    # الفشل = غرامة للمزروف
    await svc.db.execute("DELETE FROM bank_cooldowns")
    monkeypatch.setattr(random, "random", lambda: 0.9)
    s_before = await B.cash(svc, GROUP, SARA)
    assert "انْـكِـشَـفَـت" in await _say(env, ALI, "زرف", reply_to=SARA)
    assert await B.cash(svc, GROUP, SARA) > s_before
    assert "🥇" in await _say(env, ALI, "توب الحرامية")


async def test_richest_counts_bank(env):
    svc = env[0]
    await _setup(env)
    await _open(env, ALI)
    await _say(env, ALI, "ايداع الكل")
    assert "500" in await _say(env, ALI, "الاغنى")


async def test_bank_menu_and_economy_off(env):
    await _setup(env)
    assert "بَـنْـك زَهـو" in await _say(env, ALI, "البنك")
    await _say(env, CREATOR, "تعطيل الاقتصاد")
    assert "معطّل" in await _say(env, ALI, "حسابي")
