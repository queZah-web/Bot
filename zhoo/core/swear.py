"""كاشف السب: يلگى الكلام المسيء حتى لو بنص كليشة طويلة أو مموّه.

يكشف:
  • التشكيل والتطويل والحروف المخفية  (كـــسـمـك)
  • تكرار الحروف                        (كسسسسمك)
  • الرموز والنقاط بين الحروف           (ك.س.م.ك ، ك*س*م*ك)
  • الحروف المفرّقة بمسافات              (ك س م ك)
  • الحروف العراقية والفارسية           (گ چ پ ڤ ک ی)
  • البادئات واللواحق                    (وكسمك ، يا كلب ، طيزك ، قحبتك)
  • العبارات المتلزگة                    (انعلابوك)

ويتجنب الإيجابيات الكاذبة: الكلمات القصيرة الحساسة (مثل «كس» و«زب») تنطابق
ككلمة كاملة فقط، فكلمات مثل «عكس» و«كسرة» و«زبون» ما تتأثر.
"""
from __future__ import annotations

import re

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_INVISIBLE = re.compile(r"[​-‏‪-‮⁦-⁩﻿­]")
_NON_LETTER = re.compile(r"[^ء-يa-z]")
_REPEAT = re.compile(r"(.)\1+")

_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي", "ی": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه",
    "ک": "ك", "گ": "ك", "چ": "ج", "پ": "ب", "ڤ": "ف", "ژ": "ز",
    "ـ": "",  # التطويل
})
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"})

# بادئات تُزال قبل المقارنة (الأطول أولاً)
_PREFIXES = ("وال", "بال", "فال", "يال", "يا", "ال", "لل", "و", "ف", "ب", "ل")
# لواحق مسموحة بعد الجذر (بدون «ي» و«ات» حتى ما نصيب كلمات مثل «نيكي» و«عرصات»)
_SUFFIXES = ("ك", "ج", "ه", "ها", "كم", "كن", "هم", "هن", "نا")
# الكلمات القصيرة (3 حروف أو أقل) تنطابق بس إذا جت وحدها أو بعد «يا»
# حتى ما نصيب: بعير، باير، فاير، واير، بكس، لكس، فكس...
_SHORT_PREFIXES = ("يا",)
# لواحق ملكية لتوليد صيغ العبارات (ابوك ← ابوج ، ابوكم ، ابوه ...)
_POSSESSIVE = ("ج", "كم", "كن", "ه", "ها", "هم")


def normalize_word(text: str) -> str:
    """توحيد كلمة أو نص: حروف موحدة، بدون تشكيل أو رموز، وبدون تكرار حروف."""
    text = _INVISIBLE.sub("", text.lower())
    text = _TASHKEEL.sub("", text).translate(_MAP)
    return _REPEAT.sub(r"\1", _NON_LETTER.sub("", text))


def tokenize(text: str) -> list[tuple[str, str]]:
    """يرجع [(الكلمة الأصلية، الكلمة الموحدة)] مع دمج الحروف المفرّقة (ك س م ك)."""
    raw = _INVISIBLE.sub("", text or "").split()
    out: list[tuple[str, str]] = []
    run_orig: list[str] = []
    run_norm: list[str] = []

    def flush_run() -> None:
        if len(run_norm) >= 2:
            out.append((" ".join(run_orig), _REPEAT.sub(r"\1", "".join(run_norm))))
        elif run_norm:
            out.append((run_orig[0], run_norm[0]))
        run_orig.clear()
        run_norm.clear()

    for word in raw:
        w = word.lower()
        if re.search(r"[a-z]", w):
            w = w.translate(_LEET)
        norm = normalize_word(w)
        if not norm:
            continue
        if len(norm) == 1:
            run_orig.append(word)
            run_norm.append(norm)
            continue
        flush_run()
        out.append((word, norm))
    flush_run()
    return out


# ── القاموس ───────────────────────────────────────────
# كلمات تنطابق ككلمة كاملة فقط (قصيرة أو حساسة)
_EXACT_RAW = """
كس كسك كسج كسه كسها كسكم كسمك كسامك كسختك كسعرضك كسابوك كسعرض كسختج كسمج
عير عيري عيرك عيرج عيره عيرها عيربيك عيربيج عيرابوك
اير ايري ايرك ايرج ايره ايربيك ايربيج
زب زبي زبك زبج زبه زبها زبر
نيك نيكك نيكج انيك انيكك انيكج ناكك ناكج
نيج نيجك نيجج انيج انيجك انيجج اتنيج تتنيج ينيج نياج نايج
لواط
قحبات كحبات كوادين قوادين معرصين لوطيين
fuck fuk fck fucking fucker motherfucker bitch bitches whore slut dick pussy asshole bastard cunt shit
"""

# جذور تقبل لواحق (طيز ← طيزك ، قحبه ← قحبتك)
_STEMS_RAW = """
طيز طياز
منيوج منيوك منيك منيكه متناك متناكه
قحبه كحبه قحاب كحاب
كواد كواده قواد قواده معرص معرصه عرص عرصه
شرموط شرموطه شراميط
فاجره عاهر عاهره زانيه لقيط
لوطي مخنث خنيث
ديوث ديوس
سرسري سرسريه
مازوخي مازوخيه
"""

# عبارات (كلمتين أو أكثر)
_PHRASES_RAW = [
    "كس امك", "كس اختك", "كس عرضك", "كس ابوك", "كس اهلك", "كس امج", "كس اختج",
    "عير بيك", "عير ابوك", "اير بيك", "اير ابوك", "زب ابوك",
    "انعل ابوك", "انعل ابو ابوك", "انعل امك", "انعل والديك", "انعل والدينك", "انعل شرفك",
    "انعل دينك", "انعل ربك", "انعل اهلك", "انعل جدك", "انعل اختك", "انعل عرضك",
    "نعل ابوك", "نعال ابوك", "انعال ابوك",
    "يلعن ابوك", "يلعن امك", "يلعن دينك", "يلعن شرفك", "يلعن ربك", "يلعن اهلك", "يلعن والديك",
    "الله يلعنك", "لعنه على ابوك",
    "ابن القحبه", "ابن الكحبه", "ابن الشرموطه", "ابن الكواد", "ابن المنيوك", "ابن الزنا",
    "ابن زنا", "ولد زنا", "ابن الحرام", "بنت الحرام",
    "ابن الكلب", "ابن كلب", "بنت الكلب", "يا كلب", "كلب ابن كلب", "ابوك كلب",
    "ابن الجلب", "يا جلب", "جلب ابن جلب",
    "ابن الحمار", "يا حمار", "ابن الزمال", "يا زمال", "يا مطي", "ابن المطي",
    "يا حيوان", "ابن الحيوان", "يا خنزير", "ابن الخنزير",
    "يا وصخ", "يا وسخ", "يا سافل", "يا حقير", "يا ساقط", "يا منحط", "يا ساقطه", "يا حقيره",
    "زمال ابن زمال", "تفو عليك",
]


def _expand_phrase(phrase: str) -> set[str]:
    words = phrase.split()
    variants = {phrase}
    last = words[-1]
    if last.endswith("ك"):
        for suf in _POSSESSIVE:
            variants.add(" ".join(words[:-1] + [last[:-1] + suf]))
    return variants


class SwearDetector:
    def __init__(self) -> None:
        self.exact: set[str] = {normalize_word(w) for w in _EXACT_RAW.split()}
        self.stems: set[str] = {normalize_word(w) for w in _STEMS_RAW.split()}
        self.phrases: set[str] = set()
        for p in _PHRASES_RAW:
            for v in _expand_phrase(p):
                norm = " ".join(normalize_word(w) for w in v.split())
                self.phrases.add(norm)
                self.exact.add(norm.replace(" ", ""))  # العبارة متلزگة: انعلابوك

    # ── مطابقة كلمة ──
    def _candidates(self, token: str) -> list[tuple[str, str]]:
        """[(الكلمة بعد إزالة البادئة، البادئة)]"""
        cands = [(token, "")]
        for p in _PREFIXES:
            if token.startswith(p) and len(token) - len(p) >= 2:
                cands.append((token[len(p):], p))
        return cands

    def _match_token(self, token: str, exact: set[str], stems: set[str]) -> str | None:
        for cand, prefix in self._candidates(token):
            if prefix and len(cand) <= 3 and prefix not in _SHORT_PREFIXES:
                continue
            if cand in exact or cand in stems:
                return cand
            for stem in stems:
                if len(stem) < 3 or not cand.startswith(stem[:-1]):
                    continue
                bases = [stem]
                if stem.endswith("ه"):
                    bases.append(stem[:-1] + "ت")  # قحبه ← قحبتك
                for base in bases:
                    if cand.startswith(base) and cand[len(base):] in _SUFFIXES:
                        return stem
        return None

    def find(self, text: str, extra: set[str] | frozenset[str] = frozenset(),
             allowed: set[str] | frozenset[str] = frozenset()) -> str | None:
        """يرجع الكلمة/العبارة المسيئة الأولى (كما انكتبت بالرسالة) أو None."""
        if not text:
            return None
        tokens = tokenize(text)
        if not tokens:
            return None
        stems = self.stems | {w for w in extra if len(w) >= 3}
        exact = self.exact | set(extra)

        # ١) العبارات
        norm_tokens = [n for _, n in tokens]
        no_waw = [n[1:] if n[:1] in "وف" and len(n) > 3 else n for n in norm_tokens]  # وانعل ← انعل
        for seq in (norm_tokens, no_waw):
            joined = f" {' '.join(seq)} "
            for phrase in self.phrases:
                if f" {phrase} " in joined and phrase.replace(" ", "") not in allowed:
                    words = phrase.split()
                    idx = next((i for i in range(len(seq) - len(words) + 1)
                                if seq[i:i + len(words)] == words), None)
                    if idx is not None:
                        return " ".join(o for o, _ in tokens[idx:idx + len(words)])
                    return phrase

        # ٢) الكلمات
        for orig, norm in tokens:
            hit = self._match_token(norm, exact, stems)
            if hit and hit not in allowed and norm not in allowed:
                return orig
        return None


detector = SwearDetector()
