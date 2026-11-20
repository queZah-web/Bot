"""اختبارات المرحلة 5: الأقفال، الترحيب، القوانين، الرابط، الإحصائيات، الإعدادات."""
from types import SimpleNamespace

from telegram import Chat, Message, PhotoSize, Sticker, Update, User

from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.systems import group, locks, protect
from tests.test_flow import ALI, CREATOR, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="مجموعة <زهو>")


async def _photo_from(env, user_id):
    svc, bot, ctx = env
    photo = [PhotoSize("f", "u", 10, 10)]
    msg = Message(next(_mid), None, CHAT, from_user=User(user_id, "U", False), photo=photo)
    msg.set_bot(bot)
    bot.calls.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return bot.calls


def test_media_detection():
    sticker = Sticker("f", "u", 10, 10, False, False, "regular")
    m = Message(1, None, CHAT, sticker=sticker)
    assert locks.media_lock(m) == "stickers"
    assert locks.media_lock(Message(1, None, CHAT, text="هلا")) is None


async def test_lock_photos_and_vip_exempt(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    out = await say(env, CREATOR, "قفل الصور")
    assert "تَـمَّ الـقَـفْـل" in out
    assert "مقفولة من قبل" in await say(env, CREATOR, "قفل صور")
    calls = await _photo_from(env, ALI)
    assert calls[0][0] == "delete"
    await svc.members.set_rank(GROUP, SARA, Rank.VIP, CREATOR)
    assert await _photo_from(env, SARA) == []
    assert "تَـمَّ الـفَـتْـح" in await say(env, CREATOR, "فتح الصور")
    assert await _photo_from(env, ALI) == []


async def test_lock_links_shares_guard_setting(env):
    await say(env, CREATOR, "قفل الروابط")
    assert (await protect.guards_state(env[0], GROUP))["links"] is True


async def test_lock_all_and_chat(env):
    svc, bot, _ = env
    await say(env, CREATOR, "قفل الكل")
    state = await locks.lock_state(svc, GROUP)
    assert all(state[k] for k in locks.ALL_KEYS) and not state["chat"]
    await say(env, CREATOR, "قفل الدردشة")
    assert ("chat_perms", False) in bot.calls
    await say(env, CREATOR, "فتح الدردشة")
    assert ("chat_perms", True) in bot.calls


async def test_lock_needs_admin(env):
    assert "يحتاج رتبة" in await say(env, ALI, "قفل الصور")


async def test_casual_sentences_not_commands(env):
    assert await say(env, ALI, "قفل الباب وراك") is None
    assert await say(env, ALI, "الترحيب حلو") is None


# ── الترحيب ──
def test_render_escapes_and_fills():
    u = User(5, "<b>x</b>", False, username="xx")
    out = group.render("هلا {الاسم} بـ {المجموعة} رقم {العدد} <i>", u, CHAT, 42)
    assert "&lt;b&gt;x&lt;/b&gt;" in out and "&lt;زهو&gt;" in out and "<b>42</b>" in out and "&lt;i&gt;" in out


async def test_welcome_on_join_and_custom_template(env):
    svc, bot, ctx = env
    await svc.groups.upsert(GROUP, "g", None)
    newbie = User(5550009, "Noor", False)
    msg = Message(next(_mid), None, CHAT, from_user=newbie, new_chat_members=[newbie])
    msg.set_bot(bot)
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert "أهلاً وسهلاً" in bot.sent[-1] and "Noor" in bot.sent[-1]

    out = await say(env, CREATOR, "تعيين الترحيب نورتنا يا {الاسم} 🌸\nاقرأ القوانين")
    assert "تم حفظ" in out
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert "نورتنا يا" in bot.sent[-1] and "اقرأ القوانين" in bot.sent[-1]

    await say(env, CREATOR, "تعطيل الترحيب")
    bot.sent.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert bot.sent == []


async def test_goodbye(env):
    svc, bot, ctx = env
    await svc.groups.upsert(GROUP, "g", None)
    await say(env, CREATOR, "تفعيل التوديع")
    leaver = User(5550010, "Sam", False)
    msg = Message(next(_mid), None, CHAT, from_user=leaver, left_chat_member=leaver)
    msg.set_bot(bot)
    bot.sent.clear()
    await group.on_left_member(Update(next(_mid), message=msg), ctx)
    assert "وداعاً" in bot.sent[-1]
    # المطرود ما ينودّع
    msg = Message(next(_mid), None, CHAT, from_user=User(CREATOR, "C", False), left_chat_member=leaver)
    msg.set_bot(bot)
    bot.sent.clear()
    await group.on_left_member(Update(next(_mid), message=msg), ctx)
    assert bot.sent == []


# ── القوانين والرابط والإحصائيات ──
async def test_rules(env):
    assert "لم تُضف" in await say(env, ALI, "القوانين")
    assert "تم حفظ" in await say(env, CREATOR, "تعيين القوانين 1- الاحترام\n2- لا سبام")
    out = await say(env, ALI, "القوانين")
    assert "الاحترام" in out and "لا سبام" in out


async def test_link(env):
    out = await say(env, ALI, "الرابط")
    assert "https://t.me/+abcdef" in out
    assert "غير صحيح" in await say(env, CREATOR, "تعيين الرابط google.com")
    await say(env, CREATOR, "تعيين الرابط https://t.me/+custom")
    assert "+custom" in await say(env, ALI, "الرابط")


async def test_stats(env):
    await say(env, ALI, "هلا")
    out = await say(env, CREATOR, "الإحصائيات")
    assert "42" in out and "الأكثر تفاعلاً" in out


# ── لوحة الإعدادات ──
async def test_settings_panel_buttons(env):
    svc, bot, _ = env
    await svc.groups.upsert(GROUP, "g", None)
    assert "إعدادات" in await say(env, CREATOR, "الإعدادات")
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append((text, reply_markup))

    msg = SimpleNamespace(chat=CHAT, edit_text=edit_text)
    q = SimpleNamespace(from_user=SimpleNamespace(id=CREATOR), answer=answer)
    await group.on_settings_button(q, msg, svc, bot, str(CREATOR), "wl", "-")
    assert await svc.group_settings.get(GROUP, "warn_limit") == "4"
    await group.on_settings_button(q, msg, svc, bot, str(CREATOR), "wa", "-")
    assert await svc.group_settings.get(GROUP, "warn_action") == "kick"
    await group.on_settings_button(q, msg, svc, bot, str(CREATOR), "tw", "-")
    assert await svc.group_settings.get(GROUP, "welcome_on") == "0"
    # التنقل للأقفال فيه زر رجوع
    await group.on_settings_button(q, msg, svc, bot, str(CREATOR), "locks", "-")
    kb = edits[-1][1]
    assert any(b.callback_data.startswith("st:") for row in kb.inline_keyboard for b in row)
    # عضو عادي ما يعدّل
    q2 = SimpleNamespace(from_user=SimpleNamespace(id=ALI), answer=answer)
    await group.on_settings_button(q2, msg, svc, bot, str(ALI), "wl", "-")
    assert "مدير" in answers[-1]
