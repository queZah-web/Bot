"""أدوات الكشف للحماية — دوال صافية وسريعة وقابلة للاختبار.

لا تنفذ أي عقوبة هنا؛ فقط تكتشف وتعدّ.
"""
from __future__ import annotations

import hashlib
import re
import time
from collections import deque

from telegram import Message, MessageEntity

from zhoo.core.normalize import normalize

# روابط بدون كيان (مثل t.me/xxx المكتوبة بشكل ملتوي)
_URL_RE = re.compile(r"(?i)(?:https?://|www\.|\b(?:t|telegram)\.(?:me|dog)/)[^\s]+")
_TG_HOSTS = {"t.me", "telegram.me", "telegram.dog"}


# ── الروابط ────────────────────────────────────────
def extract_links(msg: Message) -> list[str]:
    links: list[str] = []
    for entities in (msg.parse_entities(), msg.parse_caption_entities()):
        for ent, text in entities.items():
            if ent.type == MessageEntity.URL:
                links.append(text)
            elif ent.type == MessageEntity.TEXT_LINK and ent.url:
                links.append(ent.url)
    for text in (msg.text, msg.caption):
        if text:
            links.extend(_URL_RE.findall(text))
    return links


def split_link(link: str) -> tuple[str, str]:
    """يرجع (المضيف، المسار) بحروف صغيرة."""
    link = link.strip().lower()
    link = re.sub(r"^[a-z]+://", "", link)
    host, _, path = link.partition("/")
    host = host.split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host, path


def clean_domain(text: str) -> str | None:
    host, _ = split_link(text)
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", host or ""):
        return None
    return host


def link_allowed(link: str, whitelist: set[str], chat_username: str | None) -> bool:
    host, path = split_link(link)
    if host in _TG_HOSTS and chat_username and path.split("/")[0].split("?")[0] == chat_username.lower():
        return True  # رابط المجموعة نفسها
    return any(host == d or host.endswith("." + d) for d in whitelist)


def forbidden_links(msg: Message, whitelist: set[str], chat_username: str | None) -> list[str]:
    return [l for l in extract_links(msg) if not link_allowed(l, whitelist, chat_username)]


# ── المنشن ─────────────────────────────────────────
def count_mentions(msg: Message) -> int:
    n = 0
    for ent in list(msg.entities or ()) + list(msg.caption_entities or ()):
        if ent.type in (MessageEntity.MENTION, MessageEntity.TEXT_MENTION):
            n += 1
    return n


def is_forward(msg: Message) -> bool:
    return msg.forward_origin is not None and not msg.is_automatic_forward


# ── عدّادات بالذاكرة ───────────────────────────────
class _Bounded:
    MAX_KEYS = 50_000

    def _trim(self, store: dict) -> None:
        if len(store) > self.MAX_KEYS:
            store.clear()


class FloodTracker(_Bounded):
    """كم رسالة أرسل العضو خلال آخر X ثانية."""

    def __init__(self, window: float = 5.0):
        self.window = window
        self._hits: dict[tuple[int, int], deque[float]] = {}

    def hit(self, key: tuple[int, int], now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        self._trim(self._hits)
        q = self._hits.setdefault(key, deque())
        q.append(now)
        while q and now - q[0] > self.window:
            q.popleft()
        return len(q)

    def reset(self, key: tuple[int, int]) -> None:
        self._hits.pop(key, None)


class RepeatTracker(_Bounded):
    """كم مرة كرر العضو نفس الرسالة ورا بعض خلال نافذة زمنية."""

    def __init__(self, window: float = 60.0):
        self.window = window
        self._last: dict[tuple[int, int], tuple[str, int, float]] = {}

    @staticmethod
    def fingerprint(text: str) -> str:
        return hashlib.blake2b(normalize(text).encode(), digest_size=8).hexdigest()

    def hit(self, key: tuple[int, int], text: str, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        self._trim(self._last)
        fp = self.fingerprint(text)
        prev = self._last.get(key)
        if prev and prev[0] == fp and now - prev[2] <= self.window:
            count = prev[1] + 1
        else:
            count = 1
        self._last[key] = (fp, count, now)
        return count


class StrikeTracker(_Bounded):
    """مخالفات العضو خلال نافذة (للعقوبة المتدرجة)."""

    def __init__(self, window: float = 1800.0):
        self.window = window
        self._hits: dict[tuple[int, int], deque[float]] = {}

    def add(self, key: tuple[int, int], now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        self._trim(self._hits)
        q = self._hits.setdefault(key, deque())
        q.append(now)
        while q and now - q[0] > self.window:
            q.popleft()
        return len(q)

    def reset(self, key: tuple[int, int]) -> None:
        self._hits.pop(key, None)
