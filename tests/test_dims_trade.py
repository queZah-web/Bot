"""تجارة الأبعاد (شراء، سفر، أحداث، بيع، مخزن) والمقايضة بين الناس (ذرية) والوصف."""
import random
from types import SimpleNamespace

import pytest
from telegram import User

from zhoo.core import universe as U
from zhoo.database.db import now
from zhoo.systems import dims, market, space, trade
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


async def _setup(env, cash=0):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    trade._offers.clear()
    for uid in (ALI, SARA):
        await svc.users.upsert(uid, f"U{uid}", None, None, False)
        if cash:
            await svc.economy.change(GROUP, uid, cash, "admin_give")


async def _say(env, user, text, **kw):
    env[0].command_limiter._hits.clear()
    env[0].flood.reset((GROUP, user))
    return await say(env, user, text, **kw)


async def _cash(svc, uid):
    return (await svc.economy.wallet(GROUP, uid))["balance"]


async def _arrive(svc, uid):
    await svc.db.execute("UPDATE dim_state SET arrive_at = ? WHERE user_id = ?", (now() - 1, uid))


# ── البيانات ──
def test_every_resource_has_a_route():
    for r in dims.RES.values():
        assert any(r.key in d.produces for d in dims.DIMS.values()), r.key
        assert any(r.key in d.demands for d in dims.DIMS.values()), r.key
        assert r.about


def test_route_is_profitable_but_spread_exists():
    earth, time_dim = dims.DIMS["earth"], dims.DIMS["time"]
    tablet = dims.RES["tablet"]
    assert dims.sell_price(time_dim, tablet) > dims.buy_price(earth, tablet)
    assert dims.sell_price(earth, tablet) < dims.buy_price(earth, tablet)     # البيع بنفس المكان خسارة
    assert dims.buy_price(time_dim, tablet) is None                         # ما ينباع هناك


def test_content_clean():
    from zhoo.core.swear import detector
    texts = [d.about for d in dims.DIMS.values()] + [r.about for r in dims.RES.values()] + list(market.DESCS.values())
    assert not [t for t in texts if detector.find(t)]
    assert set(market.DESCS) == set(market.ITEM_MAP)


# ── رحلة تجارية كاملة ──
async def test_full_trade_route(env, monkeypatch):
    svc, bot, _ = env
    await _setup(env, cash=10_000)
    assert "البعد الأرضي" in await _say(env, ALI, "الابعاد")
    out = await _say(env, ALI, "شراء لوح سومري 5")
    assert "اشتريت <b>5</b>" in out
    assert "ما ينباع" in await _say(env, ALI, "شراء رمل الزمن")
    monkeypatch.setattr(dims.random, "Random", random.Random)
    out = await _say(env, ALI, "سافر بعد الزمن")
    assert "انْـطِـلَاق" in out
    assert "بالطريق" in await _say(env, ALI, "بيع لوح سومري 5")
    await svc.db.execute("UPDATE dim_state SET event = 'calm'")
    await _arrive(svc, ALI)
    before = await _cash(svc, ALI)
    out = await _say(env, ALI, "بيع لوح سومري 5")
    assert "بعت <b>5</b>" in out and "📈" in out
    assert await _cash(svc, ALI) > before
    st = await dims.state(svc, GROUP, ALI)
    assert st["dim"] == "time" and st["dest"] is None


async def test_pirates_take_cargo_once(env):
    svc, bot, _ = env
    await _setup(env, cash=10_000)
    await _say(env, ALI, "شراء غبار النجوم 10")
    await _say(env, ALI, "سافر البعد الظلي")
    await svc.db.execute("UPDATE dim_state SET event = 'pirates'")
    await _arrive(svc, ALI)
    _, note1 = await dims.settle(svc, GROUP, ALI)
    _, note2 = await dims.settle(svc, GROUP, ALI)                      # مرة ثانية: ولا شي
    assert "قراصنة" in note1 and note2 is None
    left = (await dims.cargo(svc, GROUP, ALI))["stardust"][0]
    assert 5 <= left <= 8


async def test_capacity_and_upgrade(env):
    svc, bot, _ = env
    await _setup(env, cash=50_000)
    assert "مخزنك ما يكفي" in await _say(env, ALI, "شراء غبار النجوم 11")
    assert "20" in await _say(env, ALI, "توسيع المخزن")
    assert "اشتريت <b>11</b>" in await _say(env, ALI, "شراء غبار النجوم 11")
    assert "غبار النجوم" in await _say(env, ALI, "مخزني")


async def test_travel_needs_fee(env):
    await _setup(env)
    assert "الكاش ما يكفي" in await _say(env, ALI, "سافر بعد العنقاء")
    assert "أصلاً" in await _say(env, ALI, "سافر البعد الأرضي")


async def test_dims_buttons(env):
    svc, bot, ctx = env
    await _setup(env, cash=5000)
    edits, alerts = [], []

    async def answer(text=None, show_alert=False):
        alerts.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append(text)
    q = SimpleNamespace(from_user=User(ALI, "A", False), answer=answer)
    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text)
    await dims.on_button(q, msg, svc, ctx, "m", "0")
    assert "يبيع" in edits[-1]
    await dims.on_button(q, msg, svc, ctx, "b", "tablet")
    assert "اشتريت" in alerts[-1] and "حمولتك" in edits[-1]
    await dims.on_button(q, msg, svc, ctx, "t", "mirror")
    assert "مسافر" in edits[-1]


# ── المقايضة ──
def test_parse_goods():
    assert trade.parse_good("5000") == trade.Good("cash", "cash", 5000)
    assert trade.parse_good("5k") == trade.Good("cash", "cash", 5000)
    assert trade.parse_good("كوكب 2-1250").kind == "planet"
    assert trade.parse_good("خاتم 3") == trade.Good("asset", "ring", 3)
    assert trade.parse_good("رماد العنقاء 2") == trade.Good("res", "phoenixash", 2)
    assert trade.parse_good("شي غريب") is None
    assert len(trade.parse_side("خاتم 2 + 1000")) == 2


async def _press(env, action, offer_id, user):
    svc = env[0]
    alerts, edits = [], []

    async def answer(text=None, show_alert=False):
        alerts.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append(text)

    async def edit_reply_markup(reply_markup=None):
        pass
    q = SimpleNamespace(from_user=User(user, "U", False), answer=answer)
    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text, edit_reply_markup=edit_reply_markup)
    await trade.on_button(q, msg, svc, action, offer_id)
    return alerts, edits


async def test_barter_full_swap(env):
    svc, bot, _ = env
    await _setup(env, cash=100_000)
    await _say(env, ALI, "شراء خاتم 3")
    p = U.planet(1, 7)
    await svc.db.execute("INSERT INTO space_planets (chat_id, galaxy, idx, owner_id, paid, bought_at) VALUES (?, 1, 7, ?, 1, 1)",
                         (GROUP, SARA))
    out = await _say(env, ALI, f"مقايضة خاتم 2 + 1000 مقابل كوكب {p.code}", reply_to=SARA)
    assert "عَـرْض مُـقَـايَـضَـة" in out
    offer_id = next(iter(trade._offers))
    alerts, _ = await _press(env, "a", offer_id, ALI)                   # مو إله
    assert "مو إلك" in alerts[-1]
    a_cash, s_cash = await _cash(svc, ALI), await _cash(svc, SARA)
    _, edits = await _press(env, "a", offer_id, SARA)
    assert "تمت المقايضة" in edits[-1]
    assert (await market.holdings(svc, GROUP, SARA))["ring"][0] == 2
    assert (await market.holdings(svc, GROUP, ALI))["ring"][0] == 1
    assert await _cash(svc, ALI) == a_cash - 1000 and await _cash(svc, SARA) == s_cash + 1000
    assert (await space.owner_row(svc, GROUP, p))["owner_id"] == ALI
    assert offer_id not in trade._offers


async def test_barter_fails_atomically(env):
    svc, bot, _ = env
    await _setup(env, cash=100_000)
    await _say(env, ALI, "شراء خاتم 1")
    await _say(env, ALI, "مقايضة خاتم 1 مقابل 5000", reply_to=SARA)
    offer_id = next(iter(trade._offers))
    await _say(env, ALI, "بيع خاتم 1")                                  # باعه قبل القبول
    _, edits = await _press(env, "a", offer_id, SARA)
    assert "ما تمت" in edits[-1]
    assert await _cash(svc, SARA) == 100_000                            # ولا فلس راح


async def test_barter_validation_and_cancel(env):
    svc, bot, _ = env
    await _setup(env, cash=1000)
    assert "بالرد" in await _say(env, ALI, "مقايضة خاتم مقابل 10")
    assert "ما عندك" in await _say(env, ALI, "مقايضة خاتم مقابل 10", reply_to=SARA)
    assert "ما فهمت" in await _say(env, ALI, "مقايضة شي_غريب مقابل 10", reply_to=SARA)
    await _say(env, ALI, "مقايضة 500 مقابل 600", reply_to=SARA)
    offer_id = next(iter(trade._offers))
    alerts, _ = await _press(env, "c", offer_id, SARA)
    assert "صاحب العرض" in alerts[-1]
    _, edits = await _press(env, "c", offer_id, ALI)
    assert "انلغى" in edits[-1]
    alerts, _ = await _press(env, "a", offer_id, SARA)
    assert "انتهى" in alerts[-1]


# ── الوصف ──
@pytest.mark.parametrize("q,expect", [
    ("لامبورغيني", "صوت محركها"), ("رماد العنقاء", "ينباع رخيص"), ("بعد الزمن", "السفر"),
    ("مجرة بابل", "الكواكب"), ("2-1250", "الكود"), ("كوفي شوب", "الدخل اليومي"),
])
async def test_describe(env, q, expect):
    await _setup(env)
    assert expect in await _say(env, ALI, f"وصف {q}")
