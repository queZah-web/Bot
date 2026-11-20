"""اختبارات يوتيوب (بمحاكاة يوتيوب — بدون إنترنت)."""
from types import SimpleNamespace

from zhoo.systems import youtube
from tests.test_flow import ALI, GROUP, SARA, env, say  # noqa: F401

FAKE = [
    {"id": "aaaaaaaaaaa", "title": "زيارة عاشوراء - باسم الكربلائي", "duration": 1800, "channel": "قناة", "live": False},
    {"id": "bbbbbbbbbbb", "title": "مقطع طويل جداً", "duration": 5 * 3600, "channel": "قناة", "live": False},
]
downloads = []


def fake_search(query, proxy):
    return FAKE if "عاشوراء" in query else []


def fake_download(video_id, folder, proxy):
    downloads.append(video_id)
    path = folder / f"{video_id}.mp3"
    path.write_bytes(b"ID3 fake mp3 data")
    return path, {"title": FAKE[0]["title"], "uploader": "قناة", "duration": 1800}


def _setup(monkeypatch):
    monkeypatch.setattr(youtube, "search_impl", fake_search)
    monkeypatch.setattr(youtube, "download_impl", fake_download)
    monkeypatch.setattr(youtube, "available", lambda: True)
    youtube._user_limiter._hits.clear()
    downloads.clear()


class _Status:
    def __init__(self, edits):
        self.chat = SimpleNamespace(id=GROUP)
        self.message_id = 1
        self.edits = edits

    async def edit_text(self, text, reply_markup=None):
        self.edits.append((text, reply_markup))

    async def delete(self):
        self.edits.append(("<deleted>", None))


async def test_search_shows_buttons(env, monkeypatch):
    svc, bot, _ = env
    _setup(monkeypatch)
    await svc.groups.upsert(GROUP, "g", None)
    assert "مثال" in await say(env, ALI, "يوت")
    await say(env, ALI, "يوت زيارة عاشوراء")
    assert any("دا أدور" in t for t in bot.sent)
    entry = next(iter(svc.yt_results.values()))
    assert entry[0] == ALI and "aaaaaaaaaaa" in entry[1]


async def test_choose_downloads_and_caches(env, monkeypatch):
    svc, bot, _ = env
    _setup(monkeypatch)
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    svc.yt_results[(GROUP, 1)] = (ALI, {r["id"]: r for r in FAKE}, __import__("time").time())
    q = SimpleNamespace(from_user=SimpleNamespace(id=SARA, full_name="S"), answer=answer)
    await youtube.on_button(q, _Status(edits), svc, bot, str(ALI), "aaaaaaaaaaa")
    assert "لصاحب الطلب" in answers[-1]  # غيره ما يگدر يختار

    q = SimpleNamespace(from_user=SimpleNamespace(id=ALI, full_name="A"), answer=answer)
    await youtube.on_button(q, _Status(edits), svc, bot, str(ALI), "bbbbbbbbbbb")
    assert "ساعة" in answers[-1]  # الطويل ينرفض قبل التحميل
    await youtube.on_button(q, _Status(edits), svc, bot, str(ALI), "aaaaaaaaaaa")
    audio = [c for c in bot.calls if c[0] == "audio"][-1]
    assert audio[2].endswith(".mp3") and downloads == ["aaaaaaaaaaa"]
    assert "زيارة عاشوراء" in bot.sent[-1] and edits[-1][0] == "<deleted>"
    assert GROUP not in svc.yt_busy

    # المرة الثانية: من الذاكرة بدون تحميل
    svc.yt_results[(GROUP, 1)] = (ALI, {r["id"]: r for r in FAKE}, __import__("time").time())
    await youtube.on_button(q, _Status(edits), svc, bot, str(ALI), "aaaaaaaaaaa")
    assert downloads == ["aaaaaaaaaaa"]
    assert [c for c in bot.calls if c[0] == "audio"][-1][3] == "AUDIO-FILE-ID"


async def test_download_failure_is_friendly(env, monkeypatch):
    svc, bot, _ = env
    _setup(monkeypatch)

    def boom(video_id, folder, proxy):
        raise RuntimeError("Sign in to confirm you're not a bot")

    monkeypatch.setattr(youtube, "download_impl", boom)
    edits = []
    await youtube.deliver(bot, svc, _Status(edits), SimpleNamespace(id=ALI, full_name="A"), FAKE[0])
    assert "ما گدرت أحمّله" in edits[-1][0] and GROUP not in svc.yt_busy


async def test_no_results_and_cooldown(env, monkeypatch):
    svc, bot, _ = env
    _setup(monkeypatch)
    await svc.groups.upsert(GROUP, "g", None)
    await say(env, ALI, "يوت شي ماكو منه")
    assert not svc.yt_results  # ماكو نتائج = ماكو أزرار
    assert "على كيفك" in await say(env, ALI, "يوت زيارة عاشوراء")


async def test_feature_toggle(env, monkeypatch):
    _setup(monkeypatch)
    await env[0].groups.upsert(GROUP, "g", None)
    from tests.test_flow import CREATOR
    await say(env, CREATOR, "تعطيل اليوتيوب")
    assert "معطّل" in await say(env, ALI, "يوت زيارة عاشوراء")


def test_clock():
    assert youtube.clock(65) == "1:05" and youtube.clock(3725) == "1:02:05"
