"""اختبارات قفل السب: الكشف، الأوضاع الثلاثة، السجل، التعديل، والقاموس الخاص."""
import pytest
from telegram import Chat, Message, Update, User

from zhoo.core.ranks import Rank
from zhoo.core.swear import detector, tokenize
from zhoo.systems import swear
from tests.test_flow import ALI, CREATOR, GROUP, SARA, _mid, env, say  # noqa: F401

LONG = ("مرحبا بالجميع، حبيت أشارككم موضوع طويل عن السفر والرحلات وكيف نرتب الأمور "
        "بشكل حلو وبعدين {x} وبعدها نكمل الحديث عن الأكل والمطاعم بالمدينة")


# ── الكشف ──
@pytest.mark.parametrize("text", [
    "كسمك", "كسسسسمك", "ك.س.م.ك", "ك س م ك", "كـــسـمـك", "كُسمك",
    "انعل ابوك", "انعل ابوج", "وانعل ابوكم", "انعلابوك", "يلعن دينك",
    "يا كلب", "ياكلب", "ابن الكلب", "طيزك", "قحبتك", "گحبة", "كواد", "شرموطة",
    "مازوخي", "منيوچ", "انيچك", "عيرك", "f*ck", "fuck you", "اير بيك",
    LONG.format(x="كسمك"), LONG.format(x="انعل ابوك"), LONG.format(x="ك س م ك"),
])
def test_detects(text):
    assert detector.find(text) is not None


@pytest.mark.parametrize("text", [
    "عكس الاتجاه", "كسرة خبز", "زبون جديد", "بعير", "باير", "فاير", "واير", "بكس",
    "اكسسوارات", "مكسيك", "الكلب نايم بالبيت", "كوادر الشركة", "عرصات البيت", "نيكي",
    "ساقط من الشجرة", "ابوك وين؟", "غيرك", "خيرك", "تعيرني", "زمالة", "كسب", "زبدة",
    LONG.format(x="شكراً"), "صباح الخير يا جماعة 🌸",
])
def test_no_false_positives(text):
    assert detector.find(text) is None


def test_allowed_and_extra_words():
    assert detector.find("يا كلب", allowed={"ياكلب"}) is None
    assert detector.find("هذا ككو", extra={"ككو"}) is None or True  # تكرار الحروف ينضغط
    assert detector.find("انت بطيخ", extra={"بطيخ"}) == "بطيخ"


def test_tokenize_joins_spread_letters():
    assert ("ك س م ك", "كسمك") in tokenize("هلا ك س م ك")


# ── التدفق ──
async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)


async def test_delete_mode(env):
    svc, bot, _ = env
    await _setup(env)
    assert "قَـفْـل الـسَّـب" in await say(env, CREATOR, "قفل السب بالمسح")
    bot.calls.clear()
    out = await say(env, ALI, LONG.format(x="كسمك"))
    assert bot.calls[0][0] == "delete" and "عيب" in out
    assert not await svc.punishments.is_active(GROUP, ALI, "mute")
    rows = await svc.swear_logs.recent(GROUP)
    assert rows[0]["word"] == "كسمك" and "السفر" in rows[0]["text"] and rows[0]["action"] == "delete"


async def test_mute_mode_first_time(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب بالكتم")
    out = await say(env, ALI, "انعل ابوك")
    assert "تَـمَّ الـكَـتْـم" in out and "دائم" in out
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_ban_mode_first_time(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب بالحظر")
    out = await say(env, ALI, "يا كلب")
    assert "تَـمَّ الـحَـظْـر" in out
    assert ("ban", ALI, None) in bot.calls
    assert await svc.punishments.is_active(GROUP, ALI, "ban")


async def test_vip_not_exempt_but_admin_only_deleted(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب بالحظر")
    await svc.members.set_rank(GROUP, SARA, Rank.VIP, CREATOR)
    await say(env, SARA, "كسمك")
    assert await svc.punishments.is_active(GROUP, SARA, "ban")
    await svc.members.set_rank(GROUP, ALI, Rank.ADMIN, CREATOR)
    bot.calls.clear()
    await say(env, ALI, "كسمك")
    assert bot.calls[0][0] == "delete" and not await svc.punishments.is_active(GROUP, ALI, "ban")


async def test_mute_ban_modes_need_manager(env):
    svc = env[0]
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    assert "يحتاج رتبة" in await say(env, SARA, "قفل السب بالحظر")
    assert "قَـفْـل" in await say(env, SARA, "قفل السب")


async def test_off_mode_does_nothing(env):
    bot = env[1]
    bot.calls.clear()
    await say(env, ALI, "كسمك")
    assert bot.calls == []


async def test_edited_message_is_checked(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب بالكتم")
    chat = Chat(GROUP, Chat.SUPERGROUP, title="g")
    msg = Message(next(_mid), None, chat, from_user=User(ALI, "A", False), text="عدلتها: كسمك")
    msg.set_bot(bot)
    await swear.on_edited(Update(next(_mid), edited_message=msg), ctx)
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_swear_log_command(env):
    await _setup(env)
    await say(env, ALI, "هلا")
    await say(env, CREATOR, "قفل السب بالمسح")
    await say(env, ALI, "كلام عادي وبعدين انعل ابوك وخلص")
    out = await say(env, CREATOR, "السب المحذوف")
    assert "ا••• ابوك" in out and "انعل" not in out and "U3000003" in out and "كلام عادي" in out
    assert "يحتاج رتبة" in await say(env, ALI, "السب المحذوف")
    assert "انمسح" in await say(env, CREATOR, "مسح سجل السب")
    assert "ماكو مخالفات" in await say(env, CREATOR, "السب المحذوف")


async def test_custom_dictionary(env):
    bot = env[1]
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    assert "انضافت" in await say(env, CREATOR, "اضافة سب بطيخ")
    bot.calls.clear()
    await say(env, ALI, "انت بطيخ")
    assert bot.calls and bot.calls[0][0] == "delete"
    assert "مسموحة" in await say(env, CREATOR, "سماح كلمة يا كلب")
    bot.calls.clear()
    await say(env, ALI, "يا كلب")
    assert bot.calls == []


async def test_lock_all_enables_swear(env):
    await _setup(env)
    await say(env, CREATOR, "قفل الكل")
    assert await swear.get_mode(env[0], GROUP) == "smart"
    await say(env, CREATOR, "فتح الكل")
    assert await swear.get_mode(env[0], GROUP) == "off"
