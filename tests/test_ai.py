"""اختبارات الذكاء الاصطناعي بعميل وهمي (بدون إنترنت وبدون تكلفة)."""
from dataclasses import replace
from types import SimpleNamespace

import anthropic
import httpx2

from zhoo.core.ranks import Rank
from zhoo.systems import ai
from tests.test_flow import ALI, CREATOR, DEV, GROUP, SARA, env, say  # noqa: F401


class FakeAI:
    def __init__(self, text="هلا، هذا جواب تجريبي 🌸", stop="end_turn", exc=None):
        self.text, self.stop, self.exc, self.calls = text, stop, exc, []
        self.beta = self
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        return SimpleNamespace(stop_reason=self.stop, content=[SimpleNamespace(type="text", text=self.text)],
                               usage=SimpleNamespace(input_tokens=120, output_tokens=40))


def _with_key(svc, fake=None):
    svc.settings = replace(svc.settings, anthropic_key="sk-ant-test-key-1234567890")
    svc.ai_client = fake or FakeAI()
    return svc.ai_client


async def _setup(env, on=True):
    svc = env[0]
    await svc.groups.upsert(GROUP, "مجموعة الاختبار", None)
    fake = _with_key(svc)
    ai._user_limiter._hits.clear()
    if on:
        await say(env, CREATOR, "تفعيل الذكاء")
    return fake


async def test_needs_key_and_owner_consent(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    assert "يحتاج مفتاح" in await say(env, CREATOR, "تفعيل الذكاء")  # بدون مفتاح
    _with_key(svc)
    assert "مطفي" in await say(env, ALI, "اسأل شلونك")  # الذكاء مطفي افتراضياً
    assert "يحتاج رتبة" in await say(env, ALI, "تفعيل الذكاء")  # التشغيل للمالك
    out = await say(env, CREATOR, "تفعيل الذكاء")
    assert "للشفافية" in out and "Anthropic" in out and "بالذاكرة بس" in out


async def test_ask_uses_persona_rules_and_kb(env):
    svc = env[0]
    fake = await _setup(env)
    await say(env, CREATOR, "تعيين القوانين ممنوع السبام")
    await say(env, CREATOR, "تعيين معلومات الذكاء المسابقة كل جمعة الساعة 9")
    out = await say(env, ALI, "اسأل وكت المسابقة؟")
    assert out.startswith("🧠") and "جواب تجريبي" in out
    call = fake.calls[-1]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in call["betas"]
    assert call["output_config"] == {"effort": "low"}
    assert "عراقية" in call["system"] and "كل جمعة" in call["system"] and "ممنوع السبام" in call["system"]
    assert "وكت المسابقة" in call["messages"][0]["content"]
    assert "thinking" not in call  # Opus 5.5: التفكير تكيّفي تلقائياً


async def test_summary_uses_memory_buffer_only(env):
    svc = env[0]
    fake = await _setup(env)
    await svc.members.set_rank(GROUP, ALI, Rank.VIP, CREATOR)
    assert "قليلة" in await say(env, ALI, "لخص")
    for i in range(12):
        svc.flood.reset((GROUP, SARA))
        await say(env, SARA, f"نتناقش عن الرحلة رقم {i}")
    await say(env, ALI, "لخص")
    prompt = fake.calls[-1]["messages"][0]["content"]
    assert "<messages>" in prompt and "الرحلة رقم 11" in prompt
    # ما ينحفظ شي بقاعدة البيانات، والإيقاف يمسح الذاكرة
    assert await svc.db.fetchval("SELECT COUNT(*) FROM audit_logs WHERE details LIKE '%الرحلة%'") == 0
    await say(env, CREATOR, "تعطيل الذكاء")
    assert GROUP not in svc.chat_buffer


async def test_messages_not_buffered_when_off(env):
    svc = env[0]
    await _setup(env, on=False)
    await say(env, SARA, "رسالة سرية")
    assert GROUP not in svc.chat_buffer


async def test_daily_group_quota_and_usage_recording(env):
    svc = env[0]
    await _setup(env)
    await say(env, CREATOR, "حد الذكاء 2")
    for q in ("اسأل سؤال واحد", "اسأل سؤال ثاني"):
        ai._user_limiter._hits.clear()
        svc.command_limiter._hits.clear()
        assert "جواب تجريبي" in await say(env, ALI, q)
    ai._user_limiter._hits.clear()
    assert "خلصت حصة" in await say(env, ALI, "اسأل سؤال ثالث")
    row = await svc.db.fetchone("SELECT requests, input_tokens, output_tokens FROM ai_usage WHERE chat_id = ?",
                                (GROUP,))
    assert tuple(row) == (2, 240, 80)


async def test_user_cooldown(env):
    await _setup(env)
    await say(env, ALI, "اسأل أول سؤال")
    assert "على كيفك" in await say(env, ALI, "اسأل ثاني سؤال")


async def test_errors_are_friendly(env):
    svc = env[0]
    await _setup(env)
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    for exc, expected in (
        (anthropic.APIConnectionError(message="x", request=req), "الـ VPN"),
        (anthropic.AuthenticationError("bad", response=httpx2.Response(401, request=req), body=None), "مفتاح"),
        (anthropic.RateLimitError("slow", response=httpx2.Response(429, request=req), body=None), "مزدحمة"),
    ):
        svc.ai_client = FakeAI(exc=exc)
        ai._user_limiter._hits.clear()
        svc.command_limiter._hits.clear()
        assert expected in await say(env, ALI, "اسأل أي شي"), expected
    svc.ai_client = FakeAI(stop="refusal")
    ai._user_limiter._hits.clear()
    assert "ما أگدر أجاوب" in await say(env, ALI, "اسأل شي ممنوع")


async def test_staff_tools(env):
    svc = env[0]
    fake = await _setup(env)
    assert "رد على الرسالة" in await say(env, CREATOR, "اقترح رد")
    assert "رَد مُـقْـتَـرَح" in await say(env, CREATOR, "اقترح رد", reply_to=ALI)
    assert "أَفْـكَـار" in await say(env, CREATOR, "افكار مسابقات رمضان")
    assert "ماكو اقتراحات" in await say(env, CREATOR, "صنف الاقتراحات")
    svc.command_limiter._hits.clear()  # رسائل الاختبار السريعة
    out = await say(env, CREATOR, "ساعدني بالاعدادات مجموعة دراسية بيها سبام روابط")
    assert "مُـسَـاعِـد الإِعْـدَادَات" in out
    assert "لا تخترعين" in fake.calls[-1]["messages"][0]["content"]
    assert "يحتاج رتبة" in await say(env, ALI, "افكار مسابقات")


async def test_cheaper_model_skips_fallbacks(env):
    svc = env[0]
    fake = await _setup(env)
    svc.settings = replace(svc.settings, ai_model="claude-haiku-5-5")
    await say(env, ALI, "اسأل شي بسيط")
    assert fake.calls[-1]["model"] == "claude-haiku-5-5" and "fallbacks" not in fake.calls[-1]


async def test_usage_report_for_developer(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, ALI, "اسأل شي")
    from telegram import Chat, Message, Update, User
    from tests.test_flow import _mid
    from zhoo.handlers import router
    msg = Message(next(_mid), None, Chat(DEV, Chat.PRIVATE), from_user=User(DEV, "D", False), text="استهلاك الذكاء")
    msg.set_bot(bot)
    bot.sent.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    assert "اِسْـتِـهْـلَاك" in bot.sent[-1] and "claude-opus-5-5" in bot.sent[-1]


def test_api_key_is_redacted_in_logs():
    import logging
    from zhoo.core.logging_setup import RedactingFormatter
    f = RedactingFormatter("%(message)s", [])
    rec = logging.LogRecord("x", logging.INFO, "", 0, "key=sk-ant-api03-SECRETSECRET123", None, None)
    assert "SECRET" not in f.format(rec)
