"""اختبارات المرحلة 8: الاقتصاد الافتراضي."""
import time
from types import SimpleNamespace

import pytest

from zhoo.repositories.economy import InsufficientFunds
from zhoo.repositories.levels import today
from zhoo.systems import economy, games
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)
    await say(env, ALI, "هلا")
    await say(env, SARA, "هلا")


# ── المحفظة الذرية ──
async def test_balance_never_negative_and_logged(env):
    svc = env[0]
    await _setup(env)
    assert await svc.economy.change(GROUP, ALI, 100, "admin_give") == 100
    with pytest.raises(InsufficientFunds):
        await svc.economy.change(GROUP, ALI, -150, "buy")
    assert (await svc.economy.wallet(GROUP, ALI))["balance"] == 100
    hist = await svc.economy.history(GROUP, ALI)
    assert len(hist) == 1 and hist[0]["balance_after"] == 100


async def test_transfer_is_atomic(env):
    svc = env[0]
    await _setup(env)
    await svc.economy.change(GROUP, ALI, 50, "admin_give")
    with pytest.raises(InsufficientFunds):
        await svc.economy.transfer(GROUP, ALI, SARA, 100, 5)
    assert (await svc.economy.wallet(GROUP, ALI))["balance"] == 50
    assert (await svc.economy.wallet(GROUP, SARA))["balance"] == 0


# ── المكافأة اليومية ──
async def test_daily_reward_and_streak(env):
    svc = env[0]
    await _setup(env)
    out = await say(env, ALI, "راتب")
    assert "+50" in out and "<b>1</b> 🔥" in out
    assert "ارجع بعد" in await say(env, ALI, "المكافأة اليومية")
    # بعد 21 ساعة: السلسلة تكبر
    await svc.economy.set_daily(GROUP, ALI, 1, int(time.time()) - 21 * 3600)
    out = await say(env, ALI, "راتب")
    assert "+60" in out and "<b>2</b> 🔥" in out
    # بعد 3 أيام: السلسلة ترجع 1
    await svc.economy.set_daily(GROUP, ALI, 5, int(time.time()) - 72 * 3600)
    assert "<b>1</b> 🔥" in await say(env, ALI, "راتب")
    assert "<b>160</b>" in await say(env, ALI, "محفظتي")


# ── المهام ──
async def test_missions_complete_once(env):
    svc, bot, ctx = env
    await _setup(env)
    chat = SimpleNamespace(id=GROUP)
    user = SimpleNamespace(id=7777001, full_name="New")
    for _ in range(14):
        await economy.mission(ctx, svc, chat, user, "messages")
    assert (await svc.economy.wallet(GROUP, 7777001))["balance"] == 0
    await economy.mission(ctx, svc, chat, user, "messages")
    assert (await svc.economy.wallet(GROUP, 7777001))["balance"] == 40
    await economy.mission(ctx, svc, chat, user, "messages")  # ما تنحسب مرتين
    assert (await svc.economy.wallet(GROUP, 7777001))["balance"] == 40
    out = await say(env, 7777001, "مهامي")
    assert "✅ 💬" in out and "15/15" in out


async def test_game_win_gives_coins_and_mission(env):
    svc, bot, ctx = env
    await _setup(env)
    await games.start(ctx, svc, GROUP, SimpleNamespace(id=CREATOR, full_name="C"), "riddle")
    game = svc.games[GROUP]
    await say(env, ALI, game.display)
    bal = (await svc.economy.wallet(GROUP, ALI))["balance"]
    assert bal == game.xp + economy.MISSIONS["win"][1]


# ── المتجر ──
async def test_shop_buy_equip_and_profile(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.economy.change(GROUP, ALI, 1000, "admin_give")
    assert "المتجر" in (await say(env, ALI, "المتجر")).replace("الـمَـتْـجَـر", "المتجر")
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append((text, reply_markup))

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), text="الـمَـتْـجَـر", edit_text=edit_text)
    q = SimpleNamespace(from_user=SimpleNamespace(id=ALI), answer=answer)
    await economy.on_shop_button(q, msg, svc, str(ALI), "b", "t_crown")
    assert "اشتريت" in answers[-1]
    await economy.on_shop_button(q, msg, svc, str(ALI), "b", "f_wings")
    w = await svc.economy.wallet(GROUP, ALI)
    assert "ما يكفي" in answers[-1] and w["balance"] == 200  # الإطار (500) ما يكفيه الباقي
    out = await say(env, SARA, "ملفه", reply_to=ALI)
    assert "👑 ملكي" in out and "الرصيد" in out
    # نزع اللقب
    await economy.on_shop_button(q, msg, svc, str(ALI), "e", "t_crown")
    assert "نزعت" in answers[-1]
    # متجر غيرك
    q2 = SimpleNamespace(from_user=SimpleNamespace(id=SARA), answer=answer)
    await economy.on_shop_button(q2, msg, svc, str(ALI), "b", "t_star")
    assert "مو إلك" in answers[-1]


async def test_frame_wraps_name(env):
    svc = env[0]
    await _setup(env)
    await svc.economy.change(GROUP, ALI, 600, "admin_give")
    await svc.economy.buy(GROUP, ALI, "f_wings", 500, "frame_item")
    assert "꧁ " in await say(env, ALI, "ملفي")


async def test_custom_title(env):
    svc = env[0]
    await _setup(env)
    assert "ما يكفي" in await say(env, ALI, "لقب مخصص ملك الضحك")
    await svc.economy.change(GROUP, ALI, 1200, "admin_give")
    assert "مو مقبول" in await say(env, ALI, "لقب مخصص يا كلب")
    assert "ملك الضحك" in await say(env, ALI, "لقب مخصص ملك الضحك")
    assert "ملك الضحك" in await say(env, ALI, "ملفي")
    assert "ملك الضحك" in await say(env, ALI, "ممتلكاتي")


# ── التحويل ──
async def test_transfer_rules(env):
    svc = env[0]
    await _setup(env)
    await svc.economy.change(GROUP, ALI, 1000, "admin_give")
    assert "50 رسالة" in await say(env, ALI, "تحويل 100", reply_to=SARA)  # حساب جديد
    await svc.members.add_message_counts([(GROUP, ALI, 60, 1)])
    assert "تحويل" in await say(env, ALI, "تحويل 5", reply_to=SARA)  # أقل من الحد = شرح
    assert "نفسك" in await say(env, ALI, "تحويل 100", reply_to=ALI)
    out = await say(env, ALI, "تحويل 100", reply_to=SARA)
    assert "تَـمَّ الـتَّـحْـوِيـل" in out and "<b>5</b>" in out
    assert (await svc.economy.wallet(GROUP, ALI))["balance"] == 895
    assert (await svc.economy.wallet(GROUP, SARA))["balance"] == 100
    assert "ما يكفي" in await say(env, ALI, "تحويل 4000", reply_to=SARA)
    svc.flood.reset((GROUP, ALI))  # رسائل الاختبار السريعة تحسبها الحماية إغراق
    svc.command_limiter._hits.clear()  # ونفس الشي لحد الأوامر (5 كل 10 ثواني)
    assert "للحد اليومي" in await say(env, ALI, "تحويل 5000", reply_to=SARA)
    assert "تحويل صادر" in await say(env, ALI, "سجل محفظتي")
    assert "U3000003" in await say(env, CREATOR, "الأغنى")


# ── الإدارة ──
async def test_admin_give_take_needs_owner(env):
    svc = env[0]
    await _setup(env)
    assert "يحتاج رتبة" in await say(env, ALI, "اضافة زهرات 100", reply_to=SARA)
    assert "<b>500</b>" in await say(env, CREATOR, "اضافة زهرات 500", reply_to=SARA)
    assert "<b>0</b>" in await say(env, CREATOR, "خصم زهرات 9999", reply_to=SARA)  # ما ينزل تحت الصفر
    await say(env, CREATOR, "تعطيل الاقتصاد")
    assert "معطّل" in await say(env, ALI, "محفظتي")
