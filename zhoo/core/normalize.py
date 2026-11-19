"""توحيد النص العربي قبل مطابقة الأوامر."""
from __future__ import annotations

import re

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_INVISIBLE = re.compile(r"[​-‏‪-‮⁦-⁩﻿]")
_TATWEEL = "ـ"
_SPACES = re.compile(r"\s+")

_LETTERS = str.maketrans(
    {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ى": "ي", "ی": "ي", "ئ": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ک": "ك",
        "گ": "ك",
    }
)


def normalize(text: str) -> str:
    """يزيل التشكيل والتطويل والرموز المخفية ويوحد الحروف والمسافات."""
    if not text:
        return ""
    text = _INVISIBLE.sub("", text)
    text = _TASHKEEL.sub("", text)
    text = text.replace(_TATWEEL, "")
    text = text.translate(_LETTERS)
    text = _SPACES.sub(" ", text).strip()
    return text.lower()


_TOKEN = re.compile(r"\S+")


def split_tokens(text: str) -> list[tuple[str, int, int]]:
    """يرجع الكلمات مع موقع بدايتها ونهايتها في النص الأصلي."""
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(text or "")]
