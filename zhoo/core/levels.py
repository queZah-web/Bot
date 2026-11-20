"""معادلة المستويات والألقاب — دوال صافية قابلة للاختبار.

الخبرة المطلوبة للوصول لمستوى L = 50 × L × (L + 1)
  المستوى 1 = 100 ، 2 = 300 ، 5 = 1,500 ، 10 = 5,500 ، 20 = 21,000 ، 30 = 46,500
"""
from __future__ import annotations

TITLES: tuple[tuple[int, str], ...] = (
    (0, "مبتدئ 🌱"),
    (3, "نشيط ✨"),
    (7, "متفاعل 💫"),
    (12, "متألق 🌟"),
    (20, "نجم ⭐"),
    (30, "أسطورة 👑"),
    (45, "خارق 💎"),
)
MAX_LEVEL = 100


def threshold(level: int) -> int:
    return 50 * level * (level + 1)


def level_for(xp: int) -> int:
    level = 0
    while level < MAX_LEVEL and threshold(level + 1) <= xp:
        level += 1
    return level


def title_for(level: int) -> str:
    return next(t for need, t in reversed(TITLES) if level >= need)


def progress(xp: int) -> tuple[int, int, int, float]:
    """(المستوى، الخبرة داخل المستوى، المطلوب للمستوى الجاي، النسبة)"""
    level = level_for(xp)
    start, end = threshold(level), threshold(level + 1)
    have, need = xp - start, end - start
    return level, have, need, (have / need if need else 1.0)


def bar(ratio: float, width: int = 10) -> str:
    full = max(0, min(width, round(ratio * width)))
    return "▰" * full + "▱" * (width - full)


def badges(messages: int, thanks: int, wins: int, level: int, avg_rating: float | None, voters: int) -> list[str]:
    out = []
    if messages >= 1000:
        out.append("💬 ثرثار")
    if thanks >= 25:
        out.append("🤍 محبوب")
    if wins >= 10:
        out.append("🏆 بطل المسابقات")
    if level >= 10:
        out.append("🌟 متألق")
    if avg_rating is not None and voters >= 5 and avg_rating >= 8:
        out.append("✨ إنسان جميل")
    return out
