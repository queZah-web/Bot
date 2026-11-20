"""التحميل بالرابط: «تيك <رابط>» ← فيديو تيك توك ، «ساوند <رابط>» ← صوت ساوند كلاود.

- يستخدم yt-dlp مثل يوتيوب، وبنفس الحدود: تحميل واحد بكل مجموعة، تحميلين على البوت كله،
  ومهلة لكل شخص، و50 ميگا (حد تيليجرام للبوتات).
- الروابط لازم تكون من نفس الموقع بالضبط (ما نحمّل أي رابط ثاني).
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
from pathlib import Path

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext
from zhoo.core.fmt import esc, mention
from zhoo.systems import youtube as yt

log = logging.getLogger(__name__)
S = "group"

LIMITS = {"tiktok": 15 * 60, "soundcloud": 60 * 60}
LIMIT_LABELS = {"tiktok": "15 دقيقة", "soundcloud": "ساعة"}
URL_RE = {
    "tiktok": re.compile(r"^https?://(?:(?:www|m|vm|vt)\.)?tiktok\.com/\S+$", re.I),
    "soundcloud": re.compile(r"^https?://(?:(?:www|m|on)\.)?soundcloud\.com/\S+$|^https?://snd\.sc/\S+$", re.I),
}


class TooLong(Exception):
    pass


def _download_sync(url: str, folder: Path, proxy: str | None, site: str) -> tuple[Path, dict]:
    import yt_dlp
    audio = site == "soundcloud"
    opts = yt._base_opts(proxy) | {
        "format": "bestaudio/best" if audio else "best[ext=mp4][vcodec!=none][acodec!=none]/best[ext=mp4]/best",
        "outtmpl": str(folder / "media.%(ext)s"),
        "max_filesize": yt.MAX_BYTES,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if (info.get("duration") or 0) > LIMITS[site]:
            raise TooLong(info.get("duration"))
        ydl.process_info(info)
    files = sorted(folder.glob("media.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not files or files[0].stat().st_size > yt.MAX_BYTES:
        raise yt.TooBig("no file")
    return files[0], info


download_impl = _download_sync   # الاختبارات تبدّله


def _accept(site: str):
    return lambda rest: bool(rest.split()) and rest.split()[0].lower().startswith(("http://", "https://"))


async def _run(cx: CommandContext, site: str) -> None:
    url = cx.args[0] if cx.args else ""
    if not url:
        await cx.reply(T.DL_NEED_URL.format(example=T.DL_EXAMPLES[site]))
        return
    if not URL_RE[site].match(url) or len(url) > 300:
        await cx.reply(T.DL_BAD_URL.format(site=T.DL_SITES[site]))
        return
    if not yt.available():
        await cx.reply(T.YT_NO_LIB)
        return
    svc, chat_id = cx.services, cx.chat.id
    if chat_id in svc.yt_busy:
        await cx.reply(T.YT_BUSY)
        return
    if not yt._user_limiter.hit(cx.user.id):
        await cx.reply(T.YT_WAIT.format(left=f"{yt.USER_COOLDOWN} ثانية"))
        return
    status = await cx.reply(T.DL_DOWNLOADING.format(site=T.DL_SITES[site]))
    svc.yt_busy.add(chat_id)
    folder = Path(tempfile.mkdtemp(prefix=f"zhoo-{site}-"))
    who = mention(cx.user.id, cx.user.full_name)
    try:
        async with yt._global:
            path, info = await asyncio.wait_for(
                asyncio.to_thread(download_impl, url, folder, svc.settings.proxy_url, site), 600)
        title = (info.get("title") or T.DL_SITES[site])[:200]
        with open(path, "rb") as f:
            if site == "soundcloud":
                await cx.bot.send_audio(
                    chat_id, f, title=title[:64], performer=(info.get("uploader") or "")[:64],
                    duration=int(info.get("duration") or 0), filename=f"{title[:60]}{path.suffix}",
                    caption=T.DL_CAPTION_AUDIO.format(title=esc(title), artist=esc(info.get("uploader") or "SoundCloud"),
                                                      dur=yt.clock(info.get("duration")), mention=who))
            else:
                await cx.bot.send_video(chat_id, f, caption=T.DL_CAPTION_VIDEO.format(title=esc(title), mention=who),
                                        supports_streaming=True)
        await svc.audit.log(site, chat_id=chat_id, actor_id=cx.user.id)
        await yt._delete(status)
    except TooLong as e:
        await yt._edit(status, T.DL_TOO_LONG.format(dur=yt.clock(e.args[0] if e.args else 0),
                                                    limit=LIMIT_LABELS[site]))
    except yt.TooBig:
        await yt._edit(status, T.YT_TOO_BIG)
    except Exception as e:  # noqa: BLE001 — شبكة، رابط خاص، حجب...
        log.info("فشل تحميل %s: %s", site, e)
        await yt._edit(status, T.DL_FAILED)
    finally:
        svc.yt_busy.discard(chat_id)
        shutil.rmtree(folder, ignore_errors=True)


@registry.command("tiktok", ("تيك", "تيك توك", "تيكتوك"), section=S, args="text", usage="رابط المقطع",
                  accept=_accept("tiktok"), description="يحمّل فيديو تيك توك من الرابط", order=71)
async def cmd_tiktok(cx: CommandContext) -> None:
    await _run(cx, "tiktok")


@registry.command("soundcloud", ("ساوند", "ساوند كلاود", "ساوندكلاود"), section=S, args="text", usage="رابط المقطع",
                  accept=_accept("soundcloud"), description="يحمّل صوت ساوند كلاود من الرابط", order=72)
async def cmd_soundcloud(cx: CommandContext) -> None:
    await _run(cx, "soundcloud")

