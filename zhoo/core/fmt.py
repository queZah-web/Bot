"""أدوات تنسيق آمنة (HTML) للرسائل."""
from __future__ import annotations

import html


def esc(text: object) -> str:
    return html.escape(str(text), quote=False)


def short_name(name: str | None, limit: int = 30) -> str:
    name = (name or "").strip() or "بدون اسم"
    return name if len(name) <= limit else name[: limit - 1] + "…"


def mention(user_id: int, name: str | None) -> str:
    return f'<a href="tg://user?id={int(user_id)}">{esc(short_name(name))}</a>'


def username_text(username: str | None) -> str:
    return f"@{esc(username)}" if username else "ماكو"


def duration(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} يوم")
    if hours:
        parts.append(f"{hours} ساعة")
    if minutes or not parts:
        parts.append(f"{minutes} دقيقة")
    return " و ".join(parts)


def activity_level(count: int) -> str:
    if count >= 5000:
        return "أسطوري 👑"
    if count >= 2000:
        return "نار 🔥"
    if count >= 500:
        return "متفاعل جداً ⚡"
    if count >= 100:
        return "متفاعل ✨"
    if count >= 20:
        return "عادي 🙂"
    return "خامل 😴"
