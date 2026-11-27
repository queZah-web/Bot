"""الكون (كواكب ومجرات وصور وتخفيضات وسوق اللاعبين)، سوق الممتلكات، الأرباح، الثروة، والألعاب الجديدة."""
import random
from types import SimpleNamespace

import pytest
from telegram import User

from zhoo.core import space_art, universe as U
from zhoo.data import space_bank as SB
from zhoo.systems import games, market, space
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


async def _setup(env, cash=0):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    for uid in (ALI, SARA):
        await svc.users.upsert(uid, f"U{uid}", None, None, False)
        if cash:
            await svc.economy.change(GROUP, uid, cash, "admin_give")


async def _say(env, user, text, **kw):
    env[0].command_limiter._hits.clear()
    env[0].flood.reset((GROUP, user))
    return await say(env, user, text, **kw)


def _cheap() -> U.Planet:
    for i in range(1, 3001):
        p = U.planet(1, i)
        if p.rarity == "common" and 1 not in U.sales():
            return p
    return U.planet(1, 1)


# ── الكون: التوليد ──
def test_universe_is_huge_and_stable():
    assert len(U.GALAXIES) == 14 and sum(g.count for g in U.GALAXIES) >= 30000
    assert U.planet(2, 1250) == U.planet(2, 1250)                     # نفس الرقم = نفس الكوكب
    assert U.planet(99, 1) is None and U.planet(1, 999999) is None
    assert U.parse_code("٢-١٢٥٠").code == "2-1250" and U.parse_code("abc") is None
    assert U.find_galaxy("اندروميدا").num == 2 and U.find_galaxy("مجرة 3").num == 3


def test_prices_and_sales():
    p = U.planet(3, 77)
    assert U.sell_price(p) < U.market_price(p)
    sales = U.sales()
    assert len(sales) == 2 and all(20 <= v <= 50 for v in sales.values())
    g, off = next(iter(sales.items()))
    sp = U.planet(g, 5)
    assert U.buy_price(sp) == (int(U.market_price(sp) * (100 - off) / 100) // 10 * 10, off)
    assert 0 < U.sale_left() <= U.SALE_SLOT


@pytest.mark.skipif(not space_art.available(), reason="Pillow مو موجودة")
def test_planet_and_galaxy_images():
    p = U.planet(1, 10)
    png = space_art.planet_png(p.seed, **U.art_args(p))
    assert png[:2] == b"\xff\xd8" and len(png) > 5000                 # JPEG
    assert space_art.galaxy_png(3, (200, 150, 255))[:2] == b"\xff\xd8"


def test_space_content_clean():
    from zhoo.core.swear import detector
    names = {s + e for s in SB.NAME_START for e in SB.NAME_END}
    assert not [n for n in names if detector.find(n)]
    assert not [f for f in SB.COSMIC_FACTS + SB.FACTS if detector.find(f)]


# ── الكون: الأوامر ──
async def test_planet_card_and_buy_sell(env):
    svc, bot, _ = env
    await _setup(env, cash=10_000)
    p = _cheap()
    await _say(env, ALI, f"كوكب {p.code}")
    assert any(p.name in (t or "") and "متاح للشراء" in (t or "") for t in bot.sent)
    out = await _say(env, ALI, f"شراء كوكب {p.code}")
    assert "صار يملك" in out
    assert (await svc.economy.wallet(GROUP, ALI))["balance"] == 10_000 - U.buy_price(p)[0]
    assert "انشرى" in await _say(env, SARA, f"شراء كوكب {p.code}") or "مالك" in await _say(env, SARA, f"شراء كوكب {p.code}")
    assert "مو إلك" in await _say(env, SARA, f"بيع كوكب {p.code}")
    assert "كواكب" in await _say(env, ALI, "كواكبي") or p.name in await _say(env, ALI, "كواكبي")
    out = await _say(env, ALI, f"بيع كوكب {p.code}")
    assert "انباع" in out
    assert not await space.owned_by(svc, GROUP, ALI)


async def test_player_market(env):
    svc, bot, _ = env
    await _setup(env, cash=10_000)
    p = _cheap()
    await _say(env, ALI, f"شراء كوكب {p.code}")
    assert "انعرض" in await _say(env, ALI, f"عرض كوكب {p.code} 2000")
    assert p.code in await _say(env, SARA, "سوق الكواكب")
    s_before = (await svc.economy.wallet(GROUP, SARA))["balance"]
    a_before = (await svc.economy.wallet(GROUP, ALI))["balance"]
    result, price, seller = await space.buy_listed(svc, GROUP, SARA, p)
    assert result == "ok" and seller == ALI
    assert (await svc.economy.wallet(GROUP, SARA))["balance"] == s_before - 2000
    assert (await svc.economy.wallet(GROUP, ALI))["balance"] == a_before + 1900       # عمولة 5%
    assert [x.code for x in await space.owned_by(svc, GROUP, SARA)] == [p.code]


async def test_no_funds_and_limits(env):
    svc, bot, _ = env
    await _setup(env)
    p = _cheap()
    assert "ما يكفي" in await _say(env, ALI, f"شراء كوكب {p.code}")
    assert "كود" in await _say(env, ALI, "شراء كوكب")


async def test_universe_menu_buttons(env):
    svc, bot, _ = env
    await _setup(env, cash=10_000)
    out = await _say(env, ALI, "الكون")
    assert "30,500" in out and "التخفيضات" in out
    data = {b.callback_data for row in bot.last_kw["reply_markup"].inline_keyboard for b in row}
    assert "sp:g:1:0" in data and "sp:e:0:0" in data
    # زر الشراء
    p = _cheap()
    alerts = []

    async def answer(text=None, show_alert=False):
        alerts.append(text)

    async def edit_reply_markup(reply_markup=None):
        pass
    q = SimpleNamespace(from_user=User(ALI, "A", False), answer=answer)
    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_reply_markup=edit_reply_markup)
    await space.on_button(q, msg, svc, bot, "b", str(p.galaxy), str(p.idx))
    assert "مبارك" in alerts[-1]
    q2 = SimpleNamespace(from_user=User(SARA, "S", False), answer=answer)
    await space.on_button(q2, msg, svc, bot, "S", str(p.galaxy), str(p.idx))   # مو مالكه
    assert "مو إلك" in alerts[-1]
    await space.on_button(q, msg, svc, bot, "S", str(p.galaxy), str(p.idx))
    assert "انباع" in alerts[-1]


async def test_emperors_and_sales(env):
    svc, bot, _ = env
    await _setup(env, cash=50_000)
    p = _cheap()
    await _say(env, ALI, f"شراء كوكب {p.code}")
    assert "🥇" in await _say(env, ALI, "اباطرة الكون")
    assert "تخفيض" in await _say(env, ALI, "التخفيضات")
    assert "أندروميدا" in "".join(t or "" for t in [await _say(env, ALI, "مجرة 2")] + bot.sent)


async def test_facts(env):
    await _setup(env)
    assert "هَـل تَـعْـلَـم" in await _say(env, ALI, "معلومة")
    assert "كَـوْنِـيَّـة" in await _say(env, ALI, "معلومة كونية")


# ── السوق ──
def test_market_prices_move_daily():
    it = market.ITEM_MAP["diamond"]
    assert abs(market.price(it) - it.base) <= it.base * it.vol + 10
    assert market.sell_price(it) < market.price(it)
    assert market.find_item("لامبورغيني 2") == (market.ITEM_MAP["lambo"], 2)
    assert market.find_item("شي غريب")[0] is None


async def test_market_buy_sell_and_worth(env):
    svc, bot, _ = env
    await _setup(env, cash=100_000)
    out = await _say(env, ALI, "شراء خاتم 3")
    assert "3 × 💍" in out
    assert "💍" in await _say(env, ALI, "املاكي")
    assert "ما عندك عدد كافي" in await _say(env, ALI, "بيع خاتم 9")
    assert "باع" in await _say(env, ALI, "بيع خاتم 1")
    assert (await market.holdings(svc, GROUP, ALI))["ring"][0] == 2
    out = await _say(env, ALI, "ثروتي")
    assert "المجموع" in out and "الأملاك" in out
    assert "ما لگيت" in await _say(env, ALI, "شراء شي_غريب")


async def test_passive_income(env):
    svc, bot, _ = env
    await _setup(env, cash=100_000)
    assert "ما عندك دخل" in await _say(env, ALI, "ارباحي")
    await _say(env, ALI, "شراء كوفي شوب")
    out = await _say(env, ALI, "ارباحي")
    assert "أَرْبَـاحُـك" in out and "+300" in out
    assert "تجهز بعد" in await _say(env, ALI, "ارباحي")


async def test_market_menu_button(env):
    svc, bot, _ = env
    await _setup(env, cash=5000)
    await _say(env, ALI, "السوق")
    edits, alerts = [], []

    async def answer(text=None, show_alert=False):
        alerts.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append(text)
    q = SimpleNamespace(from_user=User(ALI, "A", False), answer=answer)
    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text)
    await market.on_button(q, msg, svc, "c", "jewels")
    assert "خاتم ذهب" in edits[-1]
    await market.on_button(q, msg, svc, "b", "ring")
    assert "اشتريت" in alerts[-1] and "عندك 1" in edits[-1]


# ── الألعاب الجديدة ──
async def _start(env, kind):
    svc, bot, ctx = env
    svc.games.pop(("cd", GROUP), None)
    err = await games.start(ctx, svc, GROUP, SimpleNamespace(id=CREATOR, full_name="C"), kind)
    assert err is None
    return svc.games[GROUP]


async def test_guess_number_hints(env):
    await _setup(env)
    game = await _start(env, "guess")
    n = int(game.display)
    env[0].notice_limiter._hits.clear()
    low = await _say(env, ALI, str(n - 1)) if n > 1 else None
    if low is not None:
        assert low == "⬆️ أكبر"
    env[0].notice_limiter._hits.clear()
    if n < 100:
        assert await _say(env, SARA, str(n + 1)) == "⬇️ أصغر"
    assert "جَـوَاب صَـح" in await _say(env, ALI, str(n))


async def test_space_quiz(env):
    await _setup(env)
    for _ in range(5):
        game = await _start(env, "space")
        assert "جَـوَاب صَـح" in await _say(env, ALI, game.display)


async def test_menu_sections(env):
    await _setup(env)
    await _say(env, ALI, "الالعاب")
    rows = env[1].last_kw["reply_markup"].inline_keyboard
    assert rows[0][0].text.startswith("━━") and rows[0][0].callback_data == "gm:-"
