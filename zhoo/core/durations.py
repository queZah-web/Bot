"""تحليل المدد العربية: 10د ، 2س ، 3ي ، 1ا ، «ساعة» ، «يومين»..."""
from __future__ import annotations

import re

from zhoo.core.normalize import normalize

MIN_SECONDS = 60
MAX_SECONDS = 365 * 86400

_UNITS: dict[str, int] = {}
for names, secs in (
    (("د", "دقيقه", "دقايق", "دقائق", "دقيقة", "m", "min"), 60),
    (("س", "ساعه", "ساعات", "ساعة", "h"), 3600),
    (("ي", "يوم", "ايام", "d"), 86400),
    (("ا", "اسبوع", "اسابيع", "w"), 7 * 86400),
):
    for n in names:
        _UNITS[normalize(n)] = secs

_WORDS = {  # مدد مكتوبة بالكلمات
    normalize("دقيقه"): 60, normalize("ساعه"): 3600, normalize("ساعتين"): 7200,
    normalize("يوم"): 86400, normalize("يومين"): 2 * 86400,
    normalize("اسبوع"): 7 * 86400, normalize("اسبوعين"): 14 * 86400,
    normalize("شهر"): 30 * 86400,
}

_NUM_UNIT = re.compile(r"^(\d{1,4})\s*([^\d\s]+)$")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


class DurationError(ValueError):
    pass


def parse_duration(text: str) -> tuple[int | None, str]:
    """يقرأ مدة اختيارية من بداية النص.

    يرجع (الثواني أو None، باقي النص). يرفع DurationError إذا كانت المدة خارج الحدود.
    """
    text = (text or "").strip()
    if not text:
        return None, ""
    parts = text.split(maxsplit=2)
    first = normalize(parts[0].translate(_DIGITS))

    seconds: int | None = None
    used = 0
    m = _NUM_UNIT.match(first)
    if m and m.group(2) in _UNITS:
        seconds, used = int(m.group(1)) * _UNITS[m.group(2)], 1
    elif first.isdigit() and len(parts) > 1 and normalize(parts[1]) in _UNITS:
        seconds, used = int(first) * _UNITS[normalize(parts[1])], 2
    elif first in _WORDS:
        seconds, used = _WORDS[first], 1

    if seconds is None:
        return None, text
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise DurationError(text)
    rest = text.split(maxsplit=used)[used] if len(text.split(maxsplit=used)) > used else ""
    return seconds, rest.strip()


def format_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds % (7 * 86400) == 0:
        n = seconds // (7 * 86400)
        return "أسبوع" if n == 1 else f"{n} أسابيع"
    if seconds % 86400 == 0:
        n = seconds // 86400
        return "يوم" if n == 1 else ("يومين" if n == 2 else f"{n} أيام")
    if seconds % 3600 == 0:
        n = seconds // 3600
        return "ساعة" if n == 1 else ("ساعتين" if n == 2 else f"{n} ساعات")
    n = max(1, seconds // 60)
    return "دقيقة" if n == 1 else ("دقيقتين" if n == 2 else f"{n} دقيقة")
