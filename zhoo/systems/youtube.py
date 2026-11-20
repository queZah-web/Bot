"""يوتيوب كصوت: «يوت زيارة عاشوراء» ← 5 نتائج بالأزرار ← تختار ← يوصلك ملف صوت.

- إذا ffmpeg موجود: يتحول mp3. إذا لا (مثل Pydroid): m4a، وتيليجرام يشغّله صوت عادي.
- الحدود: ساعة وحدة، و50 ميگا (حد تيليجرام للبوتات).
- كل مقطع ينحمّل مرة وحدة: بعدها ينرسل فوراً من تيليجرام (yt_cache).
- تحميل واحد بكل مجموعة بنفس الوقت، وتحميلين بالكثير على البوت كله.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import time
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.ratelimit import RateLimiter
from zhoo.database.db import now

log = logging.getLogger(__name__)
S = "group"

MAX_DURATION = 60 * 60
MAX_BYTES = 49 * 1024 * 1024
RESULTS = 5
USER_COOLDOWN = 30
RESULTS_TTL = 10 * 60
_global = asyncio.Semaphore(2)
_user_limiter = RateLimiter(1, USER_COOLDOWN)


class TooLong(Exception):
    pass


class TooBig(Exception):
    pass


def available() -> bool:
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


def clock(seconds: int | float | None) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _base_opts(proxy: str | None) -> dict:
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 20}
    if proxy:
        opts["proxy"] = proxy
    return opts


# ── العمليات الثقيلة (تشتغل بخيط منفصل) ─────────────
def _search_sync(query: str, proxy: str | None) -> list[dict]:
    import yt_dlp
    opts = _base_opts(proxy) | {"skip_download": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{RESULTS}:{query}", download=False)
    out = []
    for e in info.get("entries") or []:
        if not e or not e.get("id"):
            continue
        out.append({"id": e["id"], "title": e.get("title") or "—", "duration": e.get("duration"),
                    "channel": e.get("channel") or e.get("uploader") or "", "live": e.get("live_status") == "is_live"})
    return out


def _download_sync(video_id: str, folder: Path, proxy: str | None) -> tuple[Path, dict]:
    import yt_dlp
    opts = _base_opts(proxy) | {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "max_filesize": MAX_BYTES,
    }
    if shutil.which("ffmpeg"):
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}]
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        if info.get("live_status") == "is_live":
            raise TooLong("live")
        if (info.get("duration") or 0) > MAX_DURATION:
            raise TooLong(info.get("duration"))
        ydl.process_info(info)
    files = sorted(folder.glob(f"{video_id}.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not files:
        raise TooBig("no file")  # yt-dlp يتجاوز الملف إذا أكبر من الحد
    if files[0].stat().st_size > MAX_BYTES:
        raise TooBig(files[0].stat().st_size)
    return files[0], info


# نسمح للاختبارات تبدّلهن
search_impl = _search_sync
download_impl = _download_sync


# ── الأمر ───────────────────────────────────────────
@registry.command("youtube", ("يوت", "يوتيوب", "بحث يوتيوب"), section=S, args="text", usage="اللي تدور عليه",
                  description="يدور بيوتيوب ويدزلك صوت (mp3)", order=70)
async def cmd_youtube(cx: CommandContext) -> None:
    query = " ".join(cx.raw_args.split())[:100]
    if not query:
        await cx.reply(T.YT_NEED_QUERY)
        return
    if not available():
        await cx.reply(T.YT_NO_LIB)
        return
    if not _user_limiter.hit(cx.user.id):
        await cx.reply(T.YT_WAIT.format(left=f"{USER_COOLDOWN} ثانية"))
        return
    status = await cx.reply(T.YT_SEARCHING.format(query=esc(query)))
    try:
        results = await asyncio.wait_for(asyncio.to_thread(search_impl, query, cx.services.settings.proxy_url), 40)
    except Exception as e:  # noqa: BLE001 — أي خطأ شبكة/حجب
        log.info("فشل بحث يوتيوب: %s", e)
        await _edit(status, T.YT_FAILED)
        return
    if not results:
        await _edit(status, T.YT_NONE)
        return
    uid = cx.user.id
    cx.services.yt_results[(cx.chat.id, status.message_id)] = (uid, {r["id"]: r for r in results}, time.time())
    buttons = [[InlineKeyboardButton(f"🎵 {r['title'][:45]} ⋅ {clock(r['duration'])}",
                                     callback_data=f"yt:{uid}:{r['id']}")] for r in results]
    await _edit(status, T.YT_RESULTS.format(query=esc(query)), InlineKeyboardMarkup(buttons))


async def _edit(msg: Message, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    try:
        await msg.edit_text(text, reply_markup=kb)
    except (BadRequest, AttributeError):
        pass


# ── اختيار نتيجة ────────────────────────────────────
async def on_button(q, msg: Message, svc: Services, bot, uid_raw: str, video_id: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.YT_NOT_YOURS, show_alert=True)
        return
    entry = svc.yt_results.get((msg.chat.id, msg.message_id))
    if entry is None or time.time() - entry[2] > RESULTS_TTL or video_id not in entry[1]:
        await q.answer(T.YT_EXPIRED, show_alert=True)
        return
    if msg.chat.id in svc.yt_busy:
        await q.answer(T.YT_BUSY.replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    info = entry[1][video_id]
    if info.get("live"):
        await q.answer(T.YT_LIVE.replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    if info.get("duration") and info["duration"] > MAX_DURATION:
        await q.answer(T.YT_TOO_LONG.replace(f"{T.BULLET} ", "").replace("<b>", "").replace("</b>", "")
                       .format(dur=clock(info["duration"])), show_alert=True)
        return
    svc.yt_results.pop((msg.chat.id, msg.message_id), None)
    await q.answer("🎧")
    await _edit(msg, T.YT_DOWNLOADING.format(title=esc(info["title"])))
    await deliver(bot, svc, msg, q.from_user, info)


async def deliver(bot, svc: Services, status: Message, user: User, info: dict) -> None:
    chat_id, vid = status.chat.id, info["id"]
    caption = T.YT_CAPTION.format(title=esc(info["title"]), channel=esc(info.get("channel") or "YouTube"),
                                  dur=clock(info.get("duration")), mention=mention(user.id, user.full_name))
    cached = await svc.db.fetchone("SELECT file_id FROM yt_cache WHERE video_id = ?", (vid,))
    if cached is not None:
        try:
            await bot.send_audio(chat_id, cached["file_id"], caption=caption)
            await _delete(status)
            return
        except TelegramError:
            await svc.db.execute("DELETE FROM yt_cache WHERE video_id = ?", (vid,))

    svc.yt_busy.add(chat_id)
    folder = Path(tempfile.mkdtemp(prefix="zhoo-yt-"))
    try:
        async with _global:
            path, meta = await asyncio.wait_for(
                asyncio.to_thread(download_impl, vid, folder, svc.settings.proxy_url), 600)
        with open(path, "rb") as f:
            sent = await bot.send_audio(
                chat_id, f, caption=caption, title=(meta.get("title") or info["title"])[:64],
                performer=(meta.get("uploader") or info.get("channel") or "")[:64],
                duration=int(meta.get("duration") or info.get("duration") or 0),
                filename=f"{(meta.get('title') or info['title'])[:60]}{path.suffix}")
        file_id = getattr(getattr(sent, "audio", None), "file_id", None)
        if file_id:
            await svc.db.execute(
                "INSERT OR REPLACE INTO yt_cache (video_id, file_id, title, duration, created_at) VALUES (?, ?, ?, ?, ?)",
                (vid, file_id, info["title"], info.get("duration"), now()))
        await svc.audit.log("youtube", chat_id=chat_id, actor_id=user.id, details={"id": vid})
        await _delete(status)
    except TooLong as e:
        await _edit(status, T.YT_LIVE if str(e) == "live" else T.YT_TOO_LONG.format(dur=clock(info.get("duration"))))
    except TooBig:
        await _edit(status, T.YT_TOO_BIG)
    except Exception as e:  # noqa: BLE001
        log.info("فشل تحميل يوتيوب %s: %s", vid, e)
        await _edit(status, T.YT_FAILED)
    finally:
        svc.yt_busy.discard(chat_id)
        shutil.rmtree(folder, ignore_errors=True)


async def _delete(msg: Message) -> None:
    try:
        await msg.delete()
    except (TelegramError, AttributeError):
        pass
