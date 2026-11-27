"""قوائم الرتب بالأزرار: تنزيل شخص أو الكل بتأكيد، وبقواعد الرتب."""
from types import SimpleNamespace

from telegram import User

from zhoo.core.ranks import Rank
from zhoo.systems import rank_lists as RL
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


async def _setup(env, n=2):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    for i in range(n):
        await svc.users.upsert(9100 + i, f"Vip{i}", None, None, False)
        await svc.members.set_rank(GROUP, 9100 + i, Rank.VIP, CREATOR)


def _buttons(kb):
    return [(b.text, b.callback_data) for row in kb.inline_keyboard for b in row] if kb else []


async def _press(env, data, user=CREATOR):
    svc, bot, _ = env
    q = SimpleNamespace(from_user=User(user, f"U{user}", False), alerts=[])

    async def answer(text=None, show_alert=False):
        q.alerts.append(text)
    q.answer = answer
    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edits=[])

    async def edit_text(text, reply_markup=None):
        msg.edits.append((text, reply_markup))
    msg.edit_text = edit_text
    _, code, action, value = data.split(":")
    await RL.on_button(q, msg, svc, bot, code, action, value)
    return q, msg


async def test_list_has_buttons_for_admins_only(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "المميزين")
    assert "Vip0" in out and "(2)" in out
    btns = _buttons(bot.last_kw["reply_markup"])
    assert btns[0][0].startswith("🧹 تنزيل كل") and any(t.startswith("⬇️ تنزيل 1.") for t, _ in btns)
    svc.command_limiter._hits.clear()
    await say(env, ALI, "المميزين")                                     # عضو: قائمة بلا أزرار
    assert bot.last_kw.get("reply_markup") is None


async def test_demote_one_and_all(env):
    svc, bot, _ = env
    await _setup(env, n=3)
    v = int(Rank.VIP)
    _, msg = await _press(env, f"rl:{v}:u:9100")
    assert await svc.members.get_rank(GROUP, 9100) == Rank.MEMBER and "انزل" in msg.edits[-1][0]
    _, msg = await _press(env, f"rl:{v}:a:0")
    assert "متأكد" in msg.edits[-1][0] and await svc.members.get_rank(GROUP, 9101) == Rank.VIP
    _, msg = await _press(env, f"rl:{v}:y:0")
    assert "<b>2</b>" in msg.edits[-1][0]
    assert await svc.members.get_rank(GROUP, 9101) == Rank.MEMBER == await svc.members.get_rank(GROUP, 9102)


async def test_rank_rules(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    await svc.members.set_rank(GROUP, ALI, Rank.ADMIN, CREATOR)
    a = int(Rank.ADMIN)
    q, _ = await _press(env, f"rl:{a}:u:{ALI}", user=SARA)               # أدمن ما ينزل أدمن
    assert q.alerts and "رتبة" in q.alerts[-1] and await svc.members.get_rank(GROUP, ALI) == Rank.ADMIN
    q, _ = await _press(env, f"rl:{int(Rank.VIP)}:u:9100", user=SARA)   # بس ينزل مميز
    assert await svc.members.get_rank(GROUP, 9100) == Rank.MEMBER


async def test_pages(env):
    svc, bot, _ = env
    await _setup(env, n=14)
    _, msg = await _press(env, f"rl:{int(Rank.VIP)}:p:1")
    text, kb = msg.edits[-1]
    assert "11." in text and "الصفحة <b>2</b> من <b>2</b>" in text
