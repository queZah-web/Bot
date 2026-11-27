"""مالك زهو بكل مجموعة، ردود السلام (إيقاف + 5 ثواني)، الأقفال الجديدة، استثناء المميز، وحالة الأقفال."""
from telegram import Chat, Document, File, Message, MessageEntity, PhotoSize, Sticker, Update, User

from zhoo.core.ranks import Rank
from zhoo.data import extras_bank as bank
from zhoo.handlers import router
from zhoo.systems import extras, protect
from tests.test_flow import ALI, BOT_ID, CREATOR, DEV, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()
    extras._source_limiter._hits.clear()
    extras._chat_source_limiter._hits.clear()


async def _send(env, user_id, **kw):
    svc, bot, ctx = env
    msg = Message(next(_mid), None, CHAT, from_user=User(user_id, f"U{user_id}", False), **kw)
    msg.set_bot(bot)
    bot.calls.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return [c[0] for c in bot.calls]


def _sticker(*, animated=False, video=False, premium=False):
    return Sticker("s", "u", 1, 1, animated, video, "regular",
                   premium_animation=File("p", "pu") if premium else None)


# ── ١) لهجة عراقية: كلمات ممنوعة بالردود ──
def test_replies_are_iraqi_only():
    banned = ("لبيه", "مرحبتين", "هلا وغلا", "حيّاك", "حياك", "الفل", "منيح", "كيفك", "وش ", "عساك", "شو ")
    texts = [r for _, replies in bank.REPLY_GROUPS.values() for r in replies]
    from zhoo.core import texts as T
    texts += list(T.ZHOO_REPLIES) + [T.DEFAULT_WELCOME, T.DEFAULT_GOODBYE]
    for t in texts:
        for word in banned:
            assert word not in t, (word, t)


# ── ٢) ردود السلام: كل 5 ثواني لنفس الشخص + أمر الإيقاف ──
async def test_greeting_every_5_seconds_per_person(env):
    await _setup(env)
    extras._source_limiter.max_hits = 1
    assert "وعليكم السلام" in await say(env, ALI, "السلام عليكم")
    assert await say(env, ALI, "مساء الخير") is None          # نفس الشخص خلال 10 ثواني
    assert "مسا" in await say(env, SARA, "مساء الخير")         # شخص ثاني ينرد عليه
    extras._source_limiter._hits.clear()                       # = مرت 10 ثواني
    assert "مسا" in await say(env, ALI, "مساء الخير")


async def test_stop_greeting_replies_keeps_commands(env):
    svc = env[0]
    await _setup(env)
    out = await say(env, CREATOR, "ايقاف ردود السلام")
    assert "إِيـقَـاف رُدُود الـسَّـلَام" in out and "الطرد والحظر" in out
    assert "موقوفة من قبل" in await say(env, CREATOR, "ايقاف ردود السلام")
    for text in ("السلام عليكم", "هلا", "صباح الخير", "مساء الخير", "شكرا زهو"):
        extras._source_limiter._hits.clear()
        assert await say(env, ALI, text) is None, text
    svc.command_limiter._hits.clear()
    assert str(ALI) in await say(env, ALI, "ايدي")             # الأوامر شغّالة
    assert await say(env, ALI, "زهو") is not None              # نداء زهو أمر، يبقى
    assert "يحتاج رتبة" in await say(env, ALI, "تشغيل ردود السلام")
    assert "تَـشْـغِـيـل" in await say(env, CREATOR, "تشغيل ردود السلام")
    extras._source_limiter._hits.clear()
    assert "وعليكم السلام" in await say(env, ALI, "السلام عليكم")


# ── ٣) مالك زهو بكل مجموعة ──
async def test_developer_controls_any_group(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, DEV, "حظر", reply_to=ALI)
    assert "تَـمَّ الـحَـظْـر" in out and ("ban", ALI, None) in bot.calls
    svc.command_limiter._hits.clear()
    assert "مالك" in await say(env, DEV, "رفع مالك", reply_to=SARA)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.OWNER
    # زهو موقوفة بالمجموعة: تسكت حتى ويه المطور (بس أوامر التشغيل)
    await say(env, CREATOR, "ايقاف زهو")
    assert await say(env, CREATOR, "ايدي") is None
    assert await say(env, DEV, "ايدي") is None
    # ومحد يكدر يعاقبه
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "فتح زهو")
    out = await say(env, CREATOR, "حظر", reply_to=DEV)
    assert ("ban", DEV, None) not in bot.calls


async def test_developer_join_greeting_bypasses_join_lock(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, CREATOR, "قفل الدخول")
    dev = User(DEV, "Dev", False)
    msg = Message(next(_mid), None, CHAT, from_user=dev, new_chat_members=[dev])
    msg.set_bot(bot)
    bot.calls.clear()
    bot.sent.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert "مَـالِـك زَهْـو" in bot.sent[-1]
    assert not [c for c in bot.calls if c[0] == "ban"]


# ── ٤) الأقفال الجديدة + استثناء المميز ──
async def test_new_sticker_and_emoji_locks(env):
    await _setup(env)
    await say(env, CREATOR, "قفل الملصقات المتحركة")
    assert (await _send(env, ALI, sticker=_sticker(animated=True)))[0] == "delete"
    assert (await _send(env, ALI, sticker=_sticker(video=True)))[0] == "delete"
    assert "delete" not in await _send(env, ALI, sticker=_sticker())           # العادي مسموح
    await say(env, CREATOR, "قفل الملصقات المميزة")
    assert (await _send(env, ALI, sticker=_sticker(premium=True)))[0] == "delete"
    await say(env, CREATOR, "قفل الايموجي المميز")
    ent = MessageEntity(MessageEntity.CUSTOM_EMOJI, 0, 2, custom_emoji_id="1")
    assert (await _send(env, ALI, text="😀 هلا", entities=[ent]))[0] == "delete"
    assert "delete" not in await _send(env, ALI, text="😀 هلا")


async def test_vip_exempt_from_media_but_not_files(env):
    svc = env[0]
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.VIP, CREATOR)
    for cmd in ("قفل الصور", "قفل الملصقات", "قفل الملصقات المميزة", "قفل الملفات", "قفل الروابط"):
        await say(env, CREATOR, cmd)
        svc.command_limiter._hits.clear()
    photo = [PhotoSize("f", "u", 1, 1)]
    assert "delete" not in await _send(env, SARA, photo=photo)                   # المميز: صور ✅
    assert "delete" not in await _send(env, SARA, sticker=_sticker(premium=True))  # ملصقات مميزة ✅
    assert (await _send(env, SARA, document=Document("d", "du")))[0] == "delete"  # ملفات ❌
    assert (await _send(env, SARA, text="شوفوا https://example.com"))[0] == "delete"  # روابط ❌
    assert (await _send(env, ALI, photo=photo))[0] == "delete"                    # العضو العادي ❌
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    assert "delete" not in await _send(env, SARA, document=Document("d", "du"))   # الأدمن ✅


# ── ٥) حالة الأقفال ──
async def test_locks_status(env):
    await _setup(env)
    await say(env, CREATOR, "قفل الصور")
    await say(env, CREATOR, "قفل الرياكت")
    await say(env, CREATOR, "قفل الملفات بالكتم")
    await say(env, CREATOR, "ايقاف ردود السلام")
    out = await say(env, ALI, "حالة الاقفال")
    assert "تم إيقاف <b>الصور</b>" in out and "تم إيقاف <b>الرياكت</b>" in out
    assert "تم إيقاف <b>الملفات</b> ⋅ 🔇 كتم ساعة" in out
    assert "🎬 الفيديو" in out                     # من المسموحات
    assert "ردود زهو" in out                       # ميزة معطّلة
    assert out.count("🌟") >= 3                    # الصور والرياكت (+ الشرح)
