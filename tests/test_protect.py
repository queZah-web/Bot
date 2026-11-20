"""اختبارات الحماية."""
from types import SimpleNamespace

from telegram import Chat, Message, MessageEntity, Update, User

from zhoo.core import guards
from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.systems import protect
from tests.test_flow import ALI, BOT_ID, CREATOR, GROUP, SARA, _mid, env, make_update, say  # noqa: F401


def _msg(text, entities=()):
    chat = Chat(GROUP, Chat.SUPERGROUP, title="g", username="mygroup")
    return Message(1, None, chat, from_user=User(ALI, "A", False), text=text, entities=list(entities))


# ── الكشف ──
def test_link_detection_and_whitelist():
    m = _msg("شوف https://youtube.com/x و t.me/spamchan و t.me/mygroup",
             [MessageEntity(MessageEntity.URL, 4, 21)])
    bad = guards.forbidden_links(m, {"youtube.com"}, "mygroup")
    assert bad == ["t.me/spamchan"]
    assert guards.forbidden_links(_msg("هلا شلونكم"), set(), None) == []


def test_text_link_entity():
    m = _msg("اضغط هنا", [MessageEntity(MessageEntity.TEXT_LINK, 0, 4, url="https://evil.com/a")])
    assert guards.forbidden_links(m, set(), None) == ["https://evil.com/a"]
    assert guards.forbidden_links(m, {"evil.com"}, None) == []


def test_clean_domain():
    assert guards.clean_domain("https://www.YouTube.com/watch") == "youtube.com"
    assert guards.clean_domain("مو رابط") is None


def test_trackers():
    f = guards.FloodTracker(window=5)
    assert [f.hit((1, 1), now=t) for t in (0, 1, 2)] == [1, 2, 3]
    assert f.hit((1, 1), now=10) == 1
    r = guards.RepeatTracker(window=60)
    assert [r.hit((1, 1), "هلا", now=t) for t in (0, 1, 2)] == [1, 2, 3]
    assert r.hit((1, 1), "شي ثاني", now=3) == 1


# ── التدفق ──
async def _set_level(env, level):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    await protect._apply_level(svc, GROUP, level, CREATOR)


async def test_links_deleted_with_escalation(env):
    svc, bot, _ = env
    await _set_level(env, "medium")
    bot.calls.clear()
    out = await say(env, ALI, "تعال هنا t.me/spam1")
    assert bot.calls[0][0] == "delete" and "(1/3)" in out
    bot.calls.clear()
    out = await say(env, ALI, "t.me/spam2")
    assert bot.calls[0][0] == "delete" and out is None  # التنبيه مرة وحدة كل 20 ثانية حتى ما نزعج
    out = await say(env, ALI, "t.me/spam3")
    assert "تِـلْـقَـائِـيًّـا" in out
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_vip_is_exempt(env):
    svc, bot, _ = env
    await _set_level(env, "medium")
    await svc.members.set_rank(GROUP, SARA, Rank.VIP, CREATOR)
    bot.calls.clear()
    await say(env, SARA, "t.me/whatever")
    assert not any(c[0] == "delete" for c in bot.calls)


async def test_links_off_in_light_level(env):
    bot = env[1]
    await _set_level(env, "light")
    bot.calls.clear()
    await say(env, ALI, "t.me/whatever")
    assert not bot.calls


async def test_flood_mutes_immediately(env):
    svc, bot, _ = env
    await _set_level(env, "light")
    for i in range(protect.FLOOD_LIMIT):
        await say(env, ALI, f"رسالة {i}")
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_mass_mention(env):
    bot = env[1]
    await _set_level(env, "light")
    text = " ".join(f"@user{i}" for i in range(7))
    ents = [MessageEntity(MessageEntity.MENTION, text.index(f"@user{i}"), len(f"@user{i}")) for i in range(7)]
    chat = Chat(GROUP, Chat.SUPERGROUP, title="g")
    msg = Message(next(_mid), None, chat, from_user=User(ALI, "A", False), text=text, entities=ents)
    msg.set_bot(bot)
    bot.calls.clear()
    await router.on_message(Update(next(_mid), message=msg), env[2])
    assert bot.calls and bot.calls[0][0] == "delete"


async def test_whitelist_commands(env):
    svc = env[0]
    await _set_level(env, "medium")
    assert "تم السماح" in await say(env, CREATOR, "سماح رابط https://www.youtube.com/watch?v=1")
    assert "youtube.com" in await say(env, CREATOR, "الروابط المسموحة")
    env[1].calls.clear()
    await say(env, ALI, "https://youtube.com/abc")
    assert not any(c[0] == "delete" for c in env[1].calls)
    assert "تم منع" in await say(env, CREATOR, "منع رابط youtube.com")


async def test_level_command_and_panel(env):
    await say(env, CREATOR, "هلا")
    assert "صارم" in await say(env, CREATOR, "مستوى الحماية صارم")
    out = await say(env, CREATOR, "إعدادات الحماية")
    assert "🔥 صارم" in out
    assert "يحتاج رتبة" in await say(env, ALI, "مستوى الحماية خفيف")


async def test_panel_buttons(env):
    svc, bot, _ = env
    await _set_level(env, "light")
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append(text)

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text)
    q = SimpleNamespace(from_user=SimpleNamespace(id=ALI), answer=answer)
    await protect.on_panel_button(q, msg, svc, bot, str(ALI), "t", "links")
    assert "مدير" in answers[-1]
    q = SimpleNamespace(from_user=SimpleNamespace(id=CREATOR), answer=answer)
    await protect.on_panel_button(q, msg, svc, bot, str(CREATOR), "t", "links")
    assert (await protect.guards_state(svc, GROUP))["links"] is True
    assert "مخصص" in edits[-1]
    await protect.on_panel_button(q, msg, svc, bot, str(ALI), "p", "strict")
    assert "ليست لك" in answers[-1]


async def test_captcha_flow(env):
    svc, bot, ctx = env
    await _set_level(env, "strict")
    newbie = User(5550001, "New", False)
    chat = Chat(GROUP, Chat.SUPERGROUP, title="g")
    msg = Message(next(_mid), None, chat, from_user=newbie, new_chat_members=[newbie])
    msg.set_bot(bot)
    bot.calls.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert bot.calls[0][0] == "restrict" and bot.calls[0][2] is False
    assert "لست روبوت" in bot.sent[-1] or "روبوت" in bot.sent[-1]

    answers = []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def delete():
        pass

    cmsg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), delete=delete)
    await protect.on_captcha_button(SimpleNamespace(from_user=SimpleNamespace(id=ALI), answer=answer),
                                    cmsg, svc, bot, str(newbie.id))
    assert "مخصص" in answers[-1]
    await protect.on_captcha_button(SimpleNamespace(from_user=SimpleNamespace(id=newbie.id), answer=answer),
                                    cmsg, svc, bot, str(newbie.id))
    assert "تم التحقق" in answers[-1]
    assert await svc.captcha.pop(GROUP, newbie.id) is None


async def test_captcha_expiry_kicks(env):
    svc, bot, ctx = env
    await svc.captcha.add(GROUP, 5550002, 77, ttl=-1)
    bot.calls.clear()
    await protect.sweep_captcha(ctx)
    assert [c[0] for c in bot.calls] == ["ban", "unban", "delete"]


async def test_intruder_bot_kicked(env):
    svc, bot, ctx = env
    await _set_level(env, "light")
    intruder = User(6660001, "SpamBot", True)
    chat = Chat(GROUP, Chat.SUPERGROUP, title="g")
    msg = Message(next(_mid), None, chat, from_user=User(ALI, "A", False), new_chat_members=[intruder])
    msg.set_bot(bot)
    bot.calls.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert bot.calls == [("ban", intruder.id, None)]
    # المنشئ يكدر يضيف بوت
    msg = Message(next(_mid), None, chat, from_user=User(CREATOR, "C", False), new_chat_members=[intruder])
    msg.set_bot(bot)
    bot.calls.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert bot.calls == []
