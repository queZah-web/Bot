"""أوامر الإعدادات الإضافية: الأسماء البديلة، معلومات المجموعة، المنشئ، إنشاء رابط، كليشة الايدي،
الاشتراك الإجباري، وتحميل تيك توك وساوند كلاود."""
from types import SimpleNamespace

from telegram.constants import ChatMemberStatus, ChatType

from zhoo.core.ranks import Rank
from zhoo.systems import channels, general, media
from zhoo.systems import youtube as yt
from tests.test_flow import ALI, BOT_ID, CREATOR, GROUP, SARA, env, say  # noqa: F401

CHANNEL = -1001234567890


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "مجموعة الاختبار", None)
    svc.command_limiter._hits.clear()


# ── أسماء بديلة ──
async def test_aliases(env):
    svc = env[0]
    await _setup(env)
    assert "انحفظ الرابط" in await say(env, CREATOR, "ضع رابط https://t.me/zhoo_group")
    assert "zhoo_group" in await say(env, ALI, "الرابط")
    assert "انمسح" in await say(env, CREATOR, "مسح الرابط")
    await say(env, CREATOR, "ضع قوانين احترام الكل")
    assert "احترام الكل" in await say(env, ALI, "القوانين")
    svc.command_limiter._hits.clear()
    assert str(ALI) in await say(env, ALI, "معلوماتي")


# ── معلومات المجموعة والمنشئ ──
async def test_group_info_and_creator(env):
    await _setup(env)
    out = await say(env, CREATOR, "المجموعه")
    assert "مَـعْـلُـومَـات الـمَـجْـمُـوعَـة" in out and str(GROUP) in out and "42" in out
    assert "Creator" in out and "مطفي" in out
    assert "يحتاج رتبة" in await say(env, ALI, "المجموعه")
    assert "Creator" in await say(env, ALI, "صاحب المجموعه")


async def test_link_create(env):
    svc = env[0]
    await _setup(env)
    out = await say(env, CREATOR, "انشاء رابط")
    assert "https://t.me/+abcdef" in out
    assert await svc.group_settings.get(GROUP, "invite_link") == "https://t.me/+abcdef"


# ── كليشة الايدي ──
async def test_id_template(env):
    svc = env[0]
    await _setup(env)
    assert "المتغيرات" in await say(env, CREATOR, "تعيين الايدي")
    assert "لازم تكون" in await say(env, CREATOR, "تعيين الايدي بدون متغيرات")
    out = await say(env, CREATOR, "تعيين الايدي\n✨ {الاسم}\n🆔 {الايدي}\n<b>x</b> {مجهول}")
    assert "انحفظت" in out and f"<code>{CREATOR}</code>" in out
    assert "&lt;b&gt;x&lt;/b&gt;" in out and "{مجهول}" in out      # نص المشرف ينهرب
    svc.command_limiter._hits.clear()
    out = await say(env, ALI, "ايدي")
    assert f"🆔 <code>{ALI}</code>" in out and "معلومات" not in out
    assert "الكليشة الحالية" in await say(env, CREATOR, "كليشة الايدي")
    assert "الأصلية" in await say(env, CREATOR, "حذف الايدي")
    svc.command_limiter._hits.clear()
    assert "معلومات" in await say(env, ALI, "ايدي")


def test_render_template_variants():
    out = general.render_id_template("{الرتبه} {المجموعه} {المعرف}", {"rank": "R", "group": "G", "username": "U"})
    assert out == "R G U"


# ── الاشتراك الإجباري ──
def _fake_channel(bot, *, bot_admin=True, members=()):
    async def get_chat(chat_id, **kw):
        if chat_id in ("@zhoo_channel", CHANNEL):
            return SimpleNamespace(id=CHANNEL, type=ChatType.CHANNEL, title="قناة زهو", username="zhoo_channel")
        if chat_id == "@agroup":
            return SimpleNamespace(id=-100999, type=ChatType.SUPERGROUP, title="g", username="agroup")
        raise __import__("telegram").error.BadRequest("chat not found")

    async def get_chat_member(chat_id, user_id, **kw):
        if chat_id != CHANNEL:
            raise __import__("telegram").error.BadRequest("not found")
        if user_id == BOT_ID:
            return SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR if bot_admin else ChatMemberStatus.MEMBER)
        return SimpleNamespace(status=ChatMemberStatus.MEMBER if user_id in members else ChatMemberStatus.LEFT)

    bot.get_chat = get_chat
    bot.get_chat_member = get_chat_member


async def test_fsub_add_validations(env):
    svc, bot, _ = env
    await _setup(env)
    _fake_channel(bot, bot_admin=False)
    assert "يوزر القناة" in await say(env, CREATOR, "اضف قناه")
    assert "ما لگيت" in await say(env, CREATOR, "اضف قناه @nothing_here")
    assert "مو قناة" in await say(env, CREATOR, "اضف قناه @agroup")
    assert "ترفعني مشرفة" in await say(env, CREATOR, "اضف قناه @zhoo_channel")
    svc.command_limiter._hits.clear()
    _fake_channel(bot, members={ALI})
    assert "قناة زهو" in await say(env, CREATOR, "اضف قناه https://t.me/zhoo_channel")
    assert "من قبل" in await say(env, CREATOR, "اضف قناه @zhoo_channel")
    assert "يحتاج رتبة" in await say(env, ALI, "اضف قناه @zhoo_channel")


async def test_fsub_blocks_non_members_and_button(env):
    svc, bot, _ = env
    await _setup(env)
    _fake_channel(bot, members={SARA})
    await say(env, CREATOR, "اضف قناه @zhoo_channel")
    bot.calls.clear()
    await say(env, ALI, "هلا")
    assert bot.calls and bot.calls[0][0] == "delete"
    assert "اشترك بالقناة" in bot.sent[-1]
    kb = bot.last_kw["reply_markup"].inline_keyboard
    assert kb[0][0].url == "https://t.me/zhoo_channel" and kb[1][0].callback_data == f"fs:{ALI}"
    bot.calls.clear()
    await say(env, SARA, "هلا")                          # مشتركة
    assert not [c for c in bot.calls if c[0] == "delete"]
    await svc.members.set_rank(GROUP, ALI, Rank.ADMIN, CREATOR)
    bot.calls.clear()
    await say(env, ALI, "هلا")                           # المشرفين مستثنين
    assert not [c for c in bot.calls if c[0] == "delete"]

    # زر «اشتركت»: يعيد الفحص بدون الذاكرة المؤقتة
    answers = []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    deleted = []

    async def delete():
        deleted.append(True)

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), delete=delete)
    q = SimpleNamespace(from_user=SimpleNamespace(id=SARA), answer=answer)
    await channels.on_button(q, msg, svc, bot, str(ALI))
    assert "لصاحب الرسالة" in answers[-1]
    q.from_user.id = ALI
    await channels.on_button(q, msg, svc, bot, str(ALI))
    assert "بعدك" in answers[-1]
    _fake_channel(bot, members={ALI})
    await channels.on_button(q, msg, svc, bot, str(ALI))
    assert "تم التحقق" in answers[-1] and deleted


async def test_fsub_check_errors_fail_open(env):
    svc, bot, _ = env
    await _setup(env)
    _fake_channel(bot)
    await say(env, CREATOR, "اضف قناه @zhoo_channel")

    async def broken(chat_id, user_id, **kw):
        raise __import__("telegram").error.Forbidden("bot was kicked")

    bot.get_chat_member = broken
    bot.calls.clear()
    await say(env, ALI, "هلا")
    assert not [c for c in bot.calls if c[0] == "delete"]


async def test_fsub_list_remove_clear(env):
    svc, bot, _ = env
    await _setup(env)
    _fake_channel(bot)
    assert "مطفي" in await say(env, CREATOR, "القنوات")
    await say(env, CREATOR, "اضف قناه @zhoo_channel")
    assert "قناة زهو" in await say(env, CREATOR, "القنوات")
    assert "مو مضافة" in await say(env, CREATOR, "حذف قناه @other_chan")
    assert "انشالت" in await say(env, CREATOR, f"حذف قناه {CHANNEL}")
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "اضف قناه @zhoo_channel")
    assert "انطفى" in await say(env, CREATOR, "تعطيل الاشتراك الاجباري")
    assert await channels.load(svc, GROUP) == []


# ── التحميل ──
def _fake_download(monkeypatch, info, size=1000):
    def impl(url, folder, proxy, site):
        path = folder / ("media.mp4" if site == "tiktok" else "media.m4a")
        path.write_bytes(b"x" * size)
        return path, info
    monkeypatch.setattr(media, "download_impl", impl)


async def test_tiktok_and_soundcloud(env, monkeypatch):
    svc, bot, _ = env
    await _setup(env)
    yt._user_limiter._hits.clear()
    assert "مو رابط تيك توك" in await say(env, ALI, "تيك https://example.com/video")
    assert await say(env, ALI, "تيك توك حلو") is None                 # كلام عادي مو أمر
    _fake_download(monkeypatch, {"title": "مقطع حلو", "duration": 30})
    await say(env, ALI, "تيك https://vm.tiktok.com/ZMabc/")
    assert any("[video:" in m and "مقطع حلو" in m for m in bot.sent)
    yt._user_limiter._hits.clear()
    _fake_download(monkeypatch, {"title": "اغنية", "uploader": "فنان", "duration": 200})
    await say(env, ALI, "ساوند https://soundcloud.com/artist/song")
    assert ("audio", GROUP, "اغنية.m4a", 1000) in bot.calls
    assert GROUP not in svc.yt_busy


async def test_download_limits_and_feature_toggle(env, monkeypatch):
    svc, bot, _ = env
    await _setup(env)
    yt._user_limiter._hits.clear()
    bot.edits = []

    async def fake_edit(msg, text, kb=None):
        bot.edits.append(text)
    monkeypatch.setattr(yt, "_edit", fake_edit)

    def too_long(url, folder, proxy, site):
        raise media.TooLong(3600)
    monkeypatch.setattr(media, "download_impl", too_long)
    await say(env, ALI, "تيك https://www.tiktok.com/@a/video/1")
    assert "الحد الأقصى 15 دقيقة" in bot.edits[-1]
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "تعطيل التحميل")
    yt._user_limiter._hits.clear()
    out = await say(env, ALI, "تيك https://vm.tiktok.com/ZMabc/")
    assert out is not None and "معطّل" in out
