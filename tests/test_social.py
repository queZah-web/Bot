"""اختبارات المرحلة 6: الملف، الشكر، الاقتراحات، الشكاوى، التصويت، الثنائيات."""
from types import SimpleNamespace

from zhoo.core.ranks import Rank
from zhoo.systems import feedback, social
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401

CHAT = SimpleNamespace(id=GROUP, title="g")


async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)
    await say(env, ALI, "هلا")
    await say(env, SARA, "هلا")


def _q(user_id, answers, name="U"):
    async def answer(text=None, show_alert=False):
        answers.append(text)
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id, full_name=name), answer=answer)


def _msg(edits, chat=CHAT):
    async def edit_text(text, reply_markup=None):
        edits.append((text, reply_markup))
    return SimpleNamespace(chat=chat, edit_text=edit_text, text_html="x")


# ── الملف والنبذة والشكر ──
async def test_profile_and_bio(env):
    await _setup(env)
    assert "انحفظت" in await say(env, ALI, "تعيين نبذتي أحب القراءة والسفر")
    out = await say(env, ALI, "ملفي")
    assert "أحب القراءة" in out and "الرسائل" in out and "الشكر" in out
    out = await say(env, SARA, "ملفه", reply_to=ALI)
    assert "أحب القراءة" in out
    assert "انمسحت" in await say(env, ALI, "حذف نبذتي")


async def test_thanks(env):
    await _setup(env)
    assert await say(env, ALI, "شكرا") is None  # بدون رد = كلام عادي
    assert await say(env, ALI, "شكرا على كلشي") is None
    assert "<b>1</b>" in await say(env, ALI, "شكراً", reply_to=SARA)
    assert "قبل شوية" in await say(env, ALI, "شكر", reply_to=SARA)
    assert "نفسك" in await say(env, ALI, "شكر", reply_to=ALI)
    assert "الأكثر شكراً" in await say(env, CREATOR, "الأكثر شكراً")


# ── الاقتراحات ──
async def test_suggestion_votes_and_decision(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, ALI, "اقتراح نسوي مسابقة أسبوعية")
    assert "#1" in out and "جديد" in out
    answers, edits = [], []
    msg = _msg(edits)
    await feedback.on_suggestion_button(_q(SARA, answers), msg, svc, bot, "1", "u")
    assert "👍" in answers[-1] and "👍 <b>1</b>" in edits[-1][0]
    await feedback.on_suggestion_button(_q(SARA, answers), msg, svc, bot, "1", "u")  # إلغاء
    assert "انلغى" in answers[-1]
    await feedback.on_suggestion_button(_q(SARA, answers), msg, svc, bot, "1", "a")
    assert "للأدمن" in answers[-1]
    await feedback.on_suggestion_button(_q(CREATOR, answers, "C"), msg, svc, bot, "1", "a")
    assert "مقبول" in edits[-1][0] and len(edits[-1][1].inline_keyboard) == 1
    assert "على كيفك" in await say(env, ALI, "اقتراح فكرة ثانية حلوة")
    assert "مسابقة" in await say(env, ALI, "الاقتراحات")


# ── الشكاوى ──
async def test_complaint_flow(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    bot.calls.clear()
    bot.dm.clear()
    await say(env, ALI, "شكوى واحد يزعجني بالخاص")
    assert ("delete",) == bot.calls[0][:1]  # رسالة الشكوى انمسحت
    recipients = {cid for cid, text in bot.dm if "شَـكْـوَى" in text}
    assert recipients == {CREATOR, SARA}
    assert "#1" in bot.dm[-1][1]  # تأكيد بالمجموعة
    out = await say(env, SARA, "الشكاوى")
    assert "يزعجني" in out
    assert "يحتاج رتبة" in await say(env, ALI, "الشكاوى")
    answers, edits = [], []
    await feedback.on_complaint_button(_q(SARA, answers), _msg(edits), svc, bot, "1")
    assert any(cid == ALI and "انحلّت" in t for cid, t in bot.dm)
    assert "ماكو شكوى" in await say(env, SARA, "حل شكوى 1")


# ── التصويت ──
def test_parse_poll():
    assert social.parse_poll("شنو نسوي؟\nمسابقة\nسهرة") == ("شنو نسوي؟", ["مسابقة", "سهرة"])
    assert social.parse_poll("شنو نسوي؟ مسابقة، سهرة، تحدي")[1] == ["مسابقة", "سهرة", "تحدي"]
    assert social.parse_poll("سؤال بلا خيارات") is None


async def test_poll_needs_vip(env):
    svc, bot, _ = env
    await _setup(env)
    assert "يحتاج رتبة" in await say(env, ALI, "تصويت شنو نسوي؟\nمسابقة\nسهرة")
    await svc.members.set_rank(GROUP, ALI, Rank.VIP, CREATOR)
    await say(env, ALI, "تصويت علني شنو نسوي؟\nمسابقة\nسهرة")
    assert ("poll", "شنو نسوي؟", ("مسابقة", "سهرة"), False) in bot.calls


# ── الثنائيات ──
async def test_pairs_consent_flow(env):
    svc, bot, _ = env
    await _setup(env)
    assert "معطّلة" in await say(env, ALI, "ارتباط", reply_to=SARA)
    await say(env, CREATOR, "تفعيل الثنائيات")
    assert "طَـلَـب" in await say(env, ALI, "ارتباط", reply_to=SARA)
    answers, edits = [], []
    msg = _msg(edits)
    await social.on_pair_button(_q(ALI, answers), msg, svc, str(ALI), str(SARA), "a")  # صاحب الطلب ما يقبل عن غيره
    assert "بس" in answers[-1] and not edits
    await social.on_pair_button(_q(SARA, answers, "Sara"), msg, svc, str(ALI), str(SARA), "a")
    assert "مَـبْـرُوك" in edits[-1][0]
    assert "مرتبط أصلاً" in await say(env, ALI, "ارتباط", reply_to=CREATOR)
    assert "شريكك" in await say(env, SARA, "شريكي")
    assert "💍" in await say(env, CREATOR, "الثنائيات")
    assert "مخفي" in await say(env, ALI, "اخفاء ارتباطي")
    assert "ماكو ثنائيات" in await say(env, CREATOR, "الثنائيات")
    assert "فك الارتباط" in await say(env, SARA, "فك الارتباط")
    assert await svc.social.partner_of(GROUP, ALI) is None


async def test_pair_reject(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "تفعيل الثنائيات")
    await say(env, ALI, "ارتباط", reply_to=SARA)
    answers, edits = [], []
    await social.on_pair_button(_q(SARA, answers, "Sara"), _msg(edits), svc, str(ALI), str(SARA), "r")
    assert "اعتذر" in edits[-1][0]
    assert await svc.social.partner_of(GROUP, ALI) is None
