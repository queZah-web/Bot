"""قوائم المحظورين/المكتومين/المقيدين بالأزرار: فك شخص، فك الكل بتأكيد، صفحات، ولوحة العقوبات."""
from types import SimpleNamespace

from telegram import User

from zhoo.core.ranks import Rank
from zhoo.systems import punish_lists as PL
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


async def _setup(env, n_banned=2):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    for i in range(n_banned):
        uid = 7000 + i
        await svc.users.upsert(uid, f"Banned{i}", None, None, False)
        await svc.punishments.add(GROUP, uid, "ban", CREATOR, None, None)
    await svc.users.upsert(8000, "Muted", None, None, False)
    await svc.punishments.add(GROUP, 8000, "mute", CREATOR, None, None)


def _buttons(kb):
    return [(b.text, b.callback_data) for row in kb.inline_keyboard for b in row]


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
    await PL.on_button(q, msg, svc, bot, code, action, value)
    return q, msg


async def test_list_shows_buttons(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "المحظورين")
    assert "Banned0" in out and "Banned1" in out and "∞" in out and "(2)" in out
    btns = _buttons(bot.last_kw["reply_markup"])
    assert btns[0] == ("🧹 الغاء حظر الكل", "pl:b:a:0")
    assert any(t.startswith("🕊 الغاء حظر 1. ") and t.endswith("∞") for t, _ in btns)
    assert ("📋 كل العقوبات", "pl:x:o:0") in btns


async def test_lift_one_person(env):
    svc, bot, _ = env
    await _setup(env)
    q, msg = await _press(env, "pl:b:u:7000")
    assert ("unban", 7000) in [(c[0], c[1]) for c in bot.calls]
    assert not await svc.punishments.is_active(GROUP, 7000, "ban")
    text, kb = msg.edits[-1]
    assert "انفك الحظر" in text and "Banned1" in text and "(1)" in text


async def test_lift_all_needs_confirm(env):
    svc, bot, _ = env
    await _setup(env)
    q, msg = await _press(env, "pl:b:a:0")
    assert "متأكد" in msg.edits[-1][0]
    assert await svc.punishments.is_active(GROUP, 7000, "ban")          # لسه ما انفك
    q, msg = await _press(env, "pl:b:y:0")
    assert "<b>2</b>" in msg.edits[-1][0]
    assert not await svc.punishments.list_active(GROUP, "ban")
    assert await svc.punishments.is_active(GROUP, 8000, "mute")         # المكتوم ما تأثر


async def test_ranks_respected(env):
    svc, bot, _ = env
    await _setup(env)
    q, _ = await _press(env, "pl:b:u:7000", user=ALI)                   # عضو
    assert q.alerts and "رتبة" in q.alerts[-1]
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    q, _ = await _press(env, "pl:b:u:7000", user=SARA)                  # أدمن ما يفك حظر (يحتاج مدير)
    assert "رتبة" in q.alerts[-1] and await svc.punishments.is_active(GROUP, 7000, "ban")
    q, msg = await _press(env, "pl:m:u:8000", user=SARA)                # بس يفك كتم
    assert not await svc.punishments.is_active(GROUP, 8000, "mute")


async def test_pages(env):
    svc, bot, _ = env
    await _setup(env, n_banned=23)
    await say(env, CREATOR, "المحظورين")
    btns = _buttons(bot.last_kw["reply_markup"])
    assert sum(1 for t, _ in btns if t.startswith("🕊")) == 10 and ("التالي ▶️", "pl:b:p:1") in btns
    _, msg = await _press(env, "pl:b:p:2")
    text, kb = msg.edits[-1]
    assert "21." in text and "الصفحة <b>3</b> من <b>3</b>" in text


async def test_panel_and_empty(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "العقوبات")
    assert "المحظورين: <b>2</b>" in out and "المكتومين: <b>1</b>" in out
    out = await say(env, CREATOR, "المقيدين")
    assert "فارغة" in out


async def test_warned_list_and_clear(env):
    svc, bot, _ = env
    await _setup(env, n_banned=0)
    for _ in range(2):
        await svc.punishments.add_warning(GROUP, 8000, CREATOR, None)
    out = await say(env, CREATOR, "المحذرين")
    assert "Muted" in out and "⚠️ 2" in out
    assert any(t.startswith("🤍 مسح تحذيرات 1.") for t, _ in _buttons(bot.last_kw["reply_markup"]))
    _, msg = await _press(env, "pl:w:u:8000")
    assert await svc.punishments.warning_count(GROUP, 8000) == 0 and "انمسحت" in msg.edits[-1][0]
    assert "المحذّرين: <b>0</b>" in await say(env, CREATOR, "العقوبات")
