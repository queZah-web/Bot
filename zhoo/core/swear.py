"""محرك كشف السب: تطبيع ذكي + مطابقة حسب السياق + قواميس بطبقات + ذاكرة مؤقتة.

التطبيع يكشف التحايل:
  • التشكيل والتطويل والحروف المخفية          كـــسـمـك ، كُسمك
  • تكرار الحروف                              كسسسسمك
  • النقاط والشرطات والرموز والإيموجي          ك.س ، ك-س ، ك*س ، ك🌸س
  • الحروف المفرّقة بمسافات                    ك س م ك
  • أشكال الحروف (عراقي/فارسي/عرض تقديمي)       گ چ پ ڤ ک ی ﻙ
  • الأرقام والرموز بدل الحروف الإنجليزية       f*ck ، sh!t ، 𝐟𝐮𝐜𝐤
  • العبارات المتلزگة                          انعلابوك

المطابقة حسب السياق (مو بحث جزئي عشوائي):
  • الكلمة لازم تطابق «كلمة كاملة» بعد إزالة البادئات/اللواحق المعروفة فقط،
    فـ«عكس» و«كسرة» و«زبون» سليمة، بس «كس» و«ك.س» و«ك س» محظورة.
  • الكلمات القصيرة (3 حروف أو أقل) ما تقبل بادئات غير «يا»: «بعير» و«باير» سليمة.
  • الإهانات العامة (كلب، حمار) تنحظر بعبارة بس: «يا كلب» مو «الكلب نايم».

الأداء: كل البحث بجداول (dict) — آلاف الكلمات ما تبطئ الفحص، والنتائج تنحفظ بذاكرة مؤقتة.
"""
from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass

LIGHT, MEDIUM, SEVERE = 1, 2, 3
LEVELS = (LIGHT, MEDIUM, SEVERE)

_TASHKEEL = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ]")
_INVISIBLE = re.compile("[­͏؜ᅟᅠ឴឵᠎​-‏"
                        "‪-‮⁠-⁯ㅤ﻿ﾠ]")
_LETTERS = re.compile("[ء-يa-z]+")
_NON_LETTER = re.compile("[^ء-يa-z]")
_REPEAT = re.compile(r"(.)\1+")
_LATIN = re.compile("[a-z]")

_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    "ى": "ي", "ی": "ي", "ئ": "ي", "ې": "ي", "ے": "ي", "ۍ": "ي",
    "ؤ": "و", "ۆ": "و", "ۇ": "و",
    "ة": "ه", "ۃ": "ه", "ھ": "ه", "ہ": "ه", "ۀ": "ه",
    "ک": "ك", "گ": "ك", "ڪ": "ك", "ګ": "ك",
    "چ": "ج", "پ": "ب", "ڤ": "ف", "ڨ": "ق", "ژ": "ز", "ڒ": "ر",
    "ـ": "",  # التطويل
})
# حروف لاتينية متنكرة (سيريلية/يونانية) شكلها نفس الإنجليزية
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "к": "k",
    "і": "i", "ј": "j", "ѕ": "s", "т": "t", "м": "m", "н": "h", "в": "b",
    "α": "a", "ο": "o", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "τ": "t", "υ": "u",
})
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
                       "@": "a", "$": "s", "!": "i", "|": "i", "€": "e"})

# بادئات تُزال قبل المقارنة (الأطول أولاً)
PREFIXES = ("وال", "بال", "فال", "يال", "ولل", "يا", "ال", "لل", "و", "ف", "ب", "ل")
# لواحق مسموحة بعد الجذر (بدون «ي» و«ات» حتى ما نصيب: نيكي ، عرصات)
SUFFIXES = ("كم", "كن", "هم", "هن", "ها", "نا", "ك", "ج", "ه")
# لواحق الملكية لتصريف آخر كلمة بالعبارة (ابوك ← ابوج ، ابوكم ...)
_POSSESSIVE = ("ج", "كم", "كن", "ه", "ها", "هم")
MAX_SPREAD = 24      # أطول تسلسل حروف مفرّقة نفحص داخله
MAX_TEXT = 4096


# ── التطبيع ─────────────────────────────────────────
def prepare(text: str) -> str:
    """تطبيع النص كله مع الإبقاء على المسافات والرموز (حتى نقسمه بعدين)."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = _INVISIBLE.sub("", text).translate(_HOMOGLYPHS)
    return _TASHKEEL.sub("", text).translate(_MAP)


def _clean(part: str) -> str:
    """كلمة واحدة بعد prepare: أرقام/رموز الإنجليزي ← حروف، شيل الباقي، واضغط التكرار."""
    if _LATIN.search(part):
        part = part.translate(_LEET)
    return _REPEAT.sub(r"\1", _NON_LETTER.sub("", part))


def normalize_word(text: str) -> str:
    """توحيد كلمة أو نص كامل لصيغة وحدة بدون مسافات."""
    return _clean(prepare(text))


def glue(norm: str) -> str:
    """عبارة موحدة ← صيغتها المتلزگة (بدون مسافات، والتكرار مضغوط مثل أي كلمة)."""
    return _REPEAT.sub(r"\1", norm.replace(" ", ""))


def normalize_phrase(text: str) -> str:
    """توحيد عبارة مع الإبقاء على حدود الكلمات: «انعـل  أبوك» ← «انعل ابوك»."""
    return " ".join(w for w in (normalize_word(p) for p in (text or "").split()) if w)


@dataclass(frozen=True, slots=True)
class Token:
    orig: str
    norm: str
    spread: bool = False   # حروف مفرّقة (ك س م ك) — نفحص داخلها كمان


def _merge_runs(parts: list[tuple[str, str]]) -> list[Token]:
    """يدمج الحروف المفردة المتتالية بكلمة وحدة: ك س م ك ← كسمك."""
    out: list[Token] = []
    run_o: list[str] = []
    run_n: list[str] = []

    def flush() -> None:
        if len(run_n) >= 2:
            out.append(Token(" ".join(run_o), _REPEAT.sub(r"\1", "".join(run_n)), True))
        elif run_n:
            out.append(Token(run_o[0], run_n[0]))
        run_o.clear()
        run_n.clear()

    for orig, norm in parts:
        if not norm:
            continue  # إيموجي أو رموز بس: ما تقطع تسلسل الحروف
        if len(norm) == 1:
            run_o.append(orig)
            run_n.append(norm)
            continue
        flush()
        out.append(Token(orig, norm))
    flush()
    return out


def views(text: str) -> list[list[Token]]:
    """قراءتين للرسالة:
    ١) بالمسافات: الرموز داخل الكلمة تنشال  (ك.س ، كس🌸مك ← كلمة وحدة)
    ٢) بكل فاصل: الرموز تفصل الكلمات      (مرحبا.كسمك ← كلمتين)
    """
    raw = (text or "")[:MAX_TEXT].split()
    if not raw:
        return []
    prepped = [prepare(w) for w in raw]
    first = _merge_runs([(o, _clean(p)) for o, p in zip(raw, prepped)])
    second_parts: list[tuple[str, str]] = []
    split_more = False
    for p in prepped:
        if _LATIN.search(p):
            p = p.translate(_LEET)
        pieces = _LETTERS.findall(p)
        if len(pieces) > 1:
            split_more = True
        second_parts += [(x, _REPEAT.sub(r"\1", x)) for x in pieces]
    if not split_more:
        return [first]
    return [first, _merge_runs(second_parts)]


def tokenize(text: str) -> list[tuple[str, str]]:
    """[(الكلمة الأصلية، الموحدة)] — القراءة الأولى (للتوافق والاختبارات)."""
    v = views(text)
    return [(t.orig, t.norm) for t in v[0]] if v else []


# ── القاموس ─────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Entry:
    key: str        # الصيغة الموحدة (العبارة بمسافات)
    text: str       # مثل ما انكتبت
    level: int
    kind: str       # exact | stem | phrase
    source: str     # base | global | group


@dataclass(frozen=True, slots=True)
class Hit:
    found: str      # مثل ما انكتب بالرسالة
    entry: Entry


def _phrase_variants(words: list[str]) -> set[tuple[str, ...]]:
    variants = {tuple(words)}
    last = words[-1]
    if len(words) > 1 and last.endswith("ك") and len(last) >= 3:
        for suf in _POSSESSIVE:
            variants.add(tuple(words[:-1] + [last[:-1] + suf]))
    return variants


class Lexicon:
    """طبقة قاموس وحدة (أساسي / عام / مجموعة). كل البحث O(1)."""

    def __init__(self, source: str = "base") -> None:
        self.source = source
        self.exact: dict[str, Entry] = {}
        self.stems: dict[str, Entry] = {}
        self.phrases: dict[str, list[tuple[tuple[str, ...], Entry]]] = {}
        self.entries: dict[str, Entry] = {}
        self.version = 0      # يتغير كل ما ينبني القاموس من جديد (مفتاح الذاكرة المؤقتة)

    def __len__(self) -> int:
        return len(self.entries)

    @staticmethod
    def auto_kind(norm: str) -> str:
        if " " in norm:
            return "phrase"
        return "exact" if len(norm) <= 3 or _LATIN.search(norm) else "stem"

    def add(self, text: str, level: int, kind: str | None = None) -> Entry | None:
        norm = normalize_phrase(text)
        if len(glue(norm)) < 2:
            return None
        kind = kind or self.auto_kind(norm)
        entry = Entry(norm, text.strip(), level, kind, self.source)
        self.entries[norm] = entry
        if kind == "phrase":
            for words in _phrase_variants(norm.split()):
                self.phrases.setdefault(words[0], []).append((words, entry))
                self.exact.setdefault(glue(" ".join(words)), entry)   # متلزگة: انعلابوك
        elif kind == "stem":
            self.stems[norm] = entry
        else:
            self.exact[norm] = entry
        return entry

    def load(self, exact: dict[int, str], stems: dict[int, str], phrases: dict[int, list[str]]) -> Lexicon:
        for level, words in exact.items():
            for w in words.split():
                self.add(w, level, "exact")
        for level, words in stems.items():
            for w in words.split():
                self.add(w, level, "stem")
        for level, items in phrases.items():
            for p in items:
                self.add(p, level, "phrase")
        return self


def _find_stem(cand: str, layers: tuple[Lexicon, ...]) -> Entry | None:
    for lx in layers:
        e = lx.stems.get(cand)
        if e is not None:
            return e
    for suf in SUFFIXES:
        if not cand.endswith(suf) or len(cand) - len(suf) < 3:
            continue
        base = cand[: -len(suf)]
        for lx in layers:
            e = lx.stems.get(base)
            if e is None and base.endswith("ت"):
                e = lx.stems.get(base[:-1] + "ه")       # قحبه ← قحبتك
            if e is not None:
                return e
    return None


def match_word(norm: str, layers: tuple[Lexicon, ...]) -> Entry | None:
    """يطابق كلمة موحدة وحدة: كاملة، أو بعد بادئة معروفة، أو جذر + لاحقة معروفة."""
    cands = [(norm, "")]
    for p in PREFIXES:
        if norm.startswith(p) and len(norm) - len(p) >= 2:
            cands.append((norm[len(p):], p))
    for cand, prefix in cands:
        for lx in layers:
            e = lx.exact.get(cand)
            if e is not None and (not prefix or len(cand) > 3 or prefix == "يا"):
                return e
        if prefix and len(cand) < 3:
            continue
        e = _find_stem(cand, layers)
        if e is not None:
            return e
    return None


def _scan_view(tokens: list[Token], layers: tuple[Lexicon, ...], allowed: frozenset[str]) -> Hit | None:
    best: Hit | None = None

    def consider(found: str, entry: Entry, norm: str) -> bool:
        nonlocal best
        if entry.key in allowed or glue(entry.key) in allowed or norm in allowed:
            return False
        if best is None or entry.level > best.entry.level:
            best = Hit(found, entry)
        return best.entry.level == SEVERE

    norms = [t.norm for t in tokens]
    # ١) العبارات (الكلمة الأولى ممكن تجي بواو/فاء: وانعل ، فيلعن)
    for i, first in enumerate(norms):
        firsts = [first]
        if first[:1] in ("و", "ف") and len(first) > 3:
            firsts.append(first[1:])
        for f in firsts:
            for lx in layers:
                for words, entry in lx.phrases.get(f, ()):
                    n = len(words)
                    if tuple(norms[i + 1:i + n]) == words[1:] and i + n <= len(norms):
                        found = " ".join(t.orig for t in tokens[i:i + n])
                        if consider(found, entry, glue(" ".join(norms[i:i + n]))):
                            return best
    # ٢) الكلمات
    for t in tokens:
        e = match_word(t.norm, layers)
        if e is not None and consider(t.orig, e, t.norm):
            return best
        if t.spread and e is None and len(t.norm) <= MAX_SPREAD:
            # حروف مفرّقة: نفحص المقاطع الداخلية كمان (ا ب ك س ← كس)
            s = t.norm
            for a in range(len(s) - 1):
                for b in range(a + 2, len(s) + 1):
                    sub = s[a:b]
                    for lx in layers:
                        e2 = lx.exact.get(sub) or lx.stems.get(sub)
                        if e2 is not None and consider(t.orig, e2, sub):
                            return best
    return best


class SwearDetector:
    """الكاشف: القاموس الأساسي + أي طبقات إضافية (عام/مجموعة) + ذاكرة مؤقتة للنتائج."""

    CACHE_SIZE = 4096

    def __init__(self) -> None:
        from zhoo.data import swear_bank as bank
        self.base = Lexicon("base").load(bank.EXACT, bank.STEMS, bank.PHRASES)
        self._cache: OrderedDict = OrderedDict()
        self._extra_cache: dict[frozenset, Lexicon] = {}

    def scan(self, text: str, layers: tuple[Lexicon, ...] = (),
             allowed: frozenset[str] = frozenset(), cache_key=None) -> Hit | None:
        """يرجع أشد مخالفة بالرسالة (أو None). الطبقات الأولى لها الأولوية."""
        if not text:
            return None
        key = (cache_key, text, allowed) if cache_key is not None else None
        if key is not None and key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        all_layers = (*layers, self.base)
        best: Hit | None = None
        for view in views(text):
            hit = _scan_view(view, all_layers, allowed)
            if hit is not None and (best is None or hit.entry.level > best.entry.level):
                best = hit
                if best.entry.level == SEVERE:
                    break
        if key is not None:
            self._cache[key] = best
            if len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)
        return best

    def find(self, text: str, extra=frozenset(), allowed=frozenset()) -> str | None:
        """واجهة مبسطة: يرجع الكلمة/العبارة المسيئة مثل ما انكتبت، أو None."""
        layers: tuple[Lexicon, ...] = ()
        if extra:
            fz = frozenset(extra)
            lx = self._extra_cache.get(fz)
            if lx is None:
                lx = Lexicon("group")
                for w in fz:
                    lx.add(w, MEDIUM)
                if len(self._extra_cache) > 256:
                    self._extra_cache.clear()
                self._extra_cache[fz] = lx
            layers = (lx,)
        hit = self.scan(text, layers, frozenset(allowed))
        return hit.found if hit else None

    def collisions(self, entry_text: str, level: int, safe_items: list[str] | None = None) -> list[str]:
        """الكلمات السليمة اللي راح تنحظر لو انضافت هاي الكلمة (فحص قبل الاعتماد)."""
        if safe_items is None:
            from zhoo.data.swear_bank import safe_items as _items
            safe_items = _items()
        probe = Lexicon("probe")
        if probe.add(entry_text, level) is None:
            return []
        bad: list[str] = []
        for item in safe_items:
            if item not in bad and any(_scan_view(v, (probe,), frozenset()) for v in views(item)):
                bad.append(item)
        return bad


detector = SwearDetector()
