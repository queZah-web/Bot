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
SUFFIXES = ("كم", "كن", "هم", "هن", "ها", "نا", "ات", "ين", "ك", "ج", "ه", "ي")
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
    out = [first, _merge_runs(second_parts)] if split_more else [first]
    joined = _merge_fragments(first)
    if joined is not None:
        out.append(joined)
    return out


# كلمات قصيرة شائعة ما نلزگها بالكلمة اللي وراها (حتى «ان يجي» ما تصير «انيجي»)
_COMMON_SHORT = frozenset("""
في من عن لا ما يا هو هي او ام ان اي لو بس هم مع قد لم لن كم شو اش ها هه يم ال اذ ذا تا هاي وي اه اي له لي لك
بي بك به بها كي حت شي يه ني نا تو اب اخ و ف ب ل
""".split())


def _merge_fragments(tokens: list[Token]) -> list[Token] | None:
    """قراءة ثالثة: الكلمة المقطوعة بمسافة (ا نيج ، ابن ج لب ، اف شخ) تنلزگ بجارتها."""
    if len(tokens) < 2 or not any(len(t.norm) <= 2 and t.norm not in _COMMON_SHORT for t in tokens):
        return None
    out: list[Token] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        frag = len(t.norm) <= 2 and t.norm not in _COMMON_SHORT
        if frag and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            out.append(Token(f"{t.orig} {nxt.orig}", _REPEAT.sub(r"\1", t.norm + nxt.norm), True))
            i += 2
        elif frag and out:
            prev = out.pop()
            out.append(Token(f"{prev.orig} {t.orig}", _REPEAT.sub(r"\1", prev.norm + t.norm), True))
            i += 1
        else:
            out.append(t)
            i += 1
    return out


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
        self.roots: dict[str, Entry] = {}    # جذر قوي: أي كلمة تبدي بيه (انيج ← انيجمك ، انيجابوق)
        self.bare: dict[str, Entry] = {}     # كلمة لوحدها بالضبط، بدون أي بادئة (ازبك ≠ الازبك)
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
        elif kind == "root":
            self.roots[norm] = entry
        elif kind == "bare":
            self.bare[norm] = entry
        else:
            self.exact[norm] = entry
        return entry

    def load(self, exact: dict[int, str], stems: dict[int, str], phrases: dict[int, list[str]],
             roots: dict[int, str] | None = None, bare: dict[int, str] | None = None) -> Lexicon:
        for kind, table in (("root", roots or {}), ("bare", bare or {})):
            for level, words in table.items():
                for w in words.split():
                    self.add(w, level, kind)
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
    # التكرار المضغوط: متناك + كم = متناككم ← انضغطت «متناكم»
    for suf in SUFFIXES:
        if len(suf) > 1 and cand.endswith(suf[1:]):
            base = cand[: len(cand) - len(suf) + 1]
            if len(base) >= 3 and base.endswith(suf[0]):
                for lx in layers:
                    e = lx.stems.get(base)
                    if e is not None:
                        return e
    return None


def match_word(norm: str, layers: tuple[Lexicon, ...]) -> Entry | None:
    """يطابق كلمة موحدة وحدة: كاملة، أو بعد بادئة معروفة، أو جذر + لاحقة معروفة."""
    for lx in layers:
        e = lx.bare.get(norm)
        if e is not None:
            return e
    cands = [(norm, "")]
    for p in PREFIXES:
        if norm.startswith(p) and len(norm) - len(p) >= 2:
            cands.append((norm[len(p):], p))
    if norm.startswith("ال") and len(norm) > 4:
        cands.append((norm[1:], "ال"))   # اللوطي ← انضغطت «الوطي» ← لوطي
    for cand, prefix in cands:
        for lx in layers:
            e = lx.exact.get(cand)
            if e is not None and (not prefix or len(cand) > 3 or prefix == "يا"):
                return e
        for lx in layers:
            for root, e in lx.roots.items():
                if cand.startswith(root):
                    return e
        if prefix and len(cand) < 3:
            continue
        e = _find_stem(cand, layers)
        if e is not None:
            return e
    return None


def _scan_view(tokens: list[Token], layers: tuple[Lexicon, ...], allowed: frozenset[str],
               levels: frozenset[int] | None = None) -> Hit | None:
    best: Hit | None = None
    top = max(levels) if levels else SEVERE

    def consider(found: str, entry: Entry, norm: str) -> bool:
        nonlocal best
        if levels is not None and entry.level not in levels:
            return False
        if entry.key in allowed or glue(entry.key) in allowed or norm in allowed:
            return False
        if best is None or entry.level > best.entry.level:
            best = Hit(found, entry)
        return best.entry.level == top

    norms = [t.norm for t in tokens]
    excused: set[int] = set()   # كلمات داخل عبارة مسموحة (سماح «يا كلب» يشمل «كلب» اللي بيها)
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
                        glued = glue(" ".join(norms[i:i + n]))
                        if entry.key in allowed or glue(entry.key) in allowed or glued in allowed:
                            excused.update(range(i, i + n))
                            continue
                        if consider(found, entry, glued):
                            return best
    # ٢) الكلمات
    for idx, t in enumerate(tokens):
        if idx in excused:
            continue
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


_RAW_CHALB = re.compile(r"(?<![\u0621-\u06ff])(?:يا\s*)?(?:ال)?چ+ل+ا?ب+[هة]?(?![\u0621-\u06ff])")
# كلمات المقدسات (للتمييز: كفر ≠ فشار ≠ سب)
_SACRED_KEYS = ("ربك", "ربج", "ربكم", "دينك", "دينج", "دينكم", "مذهبك", "مذهبج", "نبيك", "نبيج", "رسولك",
                "طايفتك", "الله", "القران", "rabak", "rabbak", "dinak", "deenak")


def category(entry: Entry) -> str:
    """نوع الإساءة للسبب: kufr (كفر) ، vulgar (فشار) ، insult (سب وإهانة)."""
    words = entry.key.split()
    if any(w in _SACRED_KEYS for w in words[1:]) or (len(words) == 1 and words[0].endswith(_SACRED_KEYS[:10])
                                                     and len(words[0]) > 4):
        return "kufr"
    return "vulgar" if entry.level == SEVERE else "insult"


MASK_CHAR = "•"
_ADDRESS = frozenset({"يا", "انت", "انتي", "ولك", "ولج", "اسكت", "اسكتي", "روح", "روحي"})
# كلمات عادية داخل العبارات ما نغطيها (يا حمار ← يا ح•••)
_PLAIN = frozenset(_clean(w) for w in (
    "يا انت انتي ابن بنت ولد الله على عليك عليج بيك بيج ابوك ابوج امك امج اختك اختج اهلك اهلج "
    "ربك دينك شرفك عرضك جدك والديك والدينك").split())


def _mask_word(word: str) -> str:
    """كلمة مسيئة ← نقاط بس (ولا حرف منها يطلع). الطول تقريبي حتى ما ينعرف شنو."""
    letters = [c for c in word if c.isalpha()]
    return MASK_CHAR * (3 if len(letters) <= 3 else 4)


_HTML_PART = re.compile(r"(<[^>]+>|&[#a-zA-Z0-9]+;)")


class SwearDetector:
    """الكاشف: القاموس الأساسي + أي طبقات إضافية (عام/مجموعة) + ذاكرة مؤقتة للنتائج."""

    CACHE_SIZE = 4096

    def __init__(self) -> None:
        from zhoo.data import swear_bank as bank
        self.base = Lexicon("base").load(bank.EXACT, bank.STEMS, bank.PHRASES, bank.ROOTS, bank.BARE)
        self._cache: OrderedDict = OrderedDict()
        self._extra_cache: dict[frozenset, Lexicon] = {}
        self.global_layer: Lexicon | None = None   # القاموس العام (من المطور) — يستخدمه فلتر الرسائل الطالعة
        # أسماء الإهانة المفردة (تنحسب بس إذا انكتبت كرد على شخص)
        self.insult_nouns = frozenset(_clean(prepare(w)) for w in bank.INSULTS_ANIMALS + bank.INSULTS_PEOPLE)

    def scan(self, text: str, layers: tuple[Lexicon, ...] = (),
             allowed: frozenset[str] = frozenset(), cache_key=None,
             levels: frozenset[int] | None = None) -> Hit | None:
        """يرجع أشد مخالفة بالرسالة (أو None). الطبقات الأولى لها الأولوية.

        levels: الفئات المقفولة بس (مثلاً الإهانات مقفولة والفشار مفتوح).
        """
        if not text or levels is not None and not levels:
            return None
        key = (cache_key, text, allowed, levels) if cache_key is not None else None
        if key is not None and key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        all_layers = (*layers, self.base)
        best: Hit | None = None
        for view in views(text):
            hit = _scan_view(view, all_layers, allowed, levels)
            if hit is not None and (best is None or hit.entry.level > best.entry.level):
                best = hit
                if best.entry.level == (max(levels) if levels else SEVERE):
                    break
        if best is None and (levels is None or LIGHT in levels):
            raw = self.raw_insult(text)
            if raw is not None and raw.entry.key not in allowed:
                best = raw
        if key is not None:
            self._cache[key] = best
            if len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)
        return best

    def raw_insult(self, text: str) -> Hit | None:
        """«چلب» بالچيم العراقية (قبل التوحيد، لأن «جلب» بالفصحى = يجيب)."""
        m = _RAW_CHALB.search(_TASHKEEL.sub("", text or "").replace("ـ", ""))
        if m is None:
            return None
        return Hit(m.group(0), Entry("چلب", "چلب", LIGHT, "bare", "base"))

    def reply_insult(self, text: str) -> Hit | None:
        """رد على شخص بإهانة مفردة: «قذر» ، «يا حمار وسخ» ، «انتي هايشه» ← إهانة (خفيفة).

        الكلمة لوحدها بالكلام العادي سليمة («الكلب نايم»)، بس كرد على شخص مقصودة بيه.
        """
        v = views(text)
        if not v:
            return None
        norms = [t.norm for t in v[0]]
        while norms and norms[0] in _ADDRESS:
            norms = norms[1:]
        if not 1 <= len(norms) <= 3:
            return None
        words = [n[2:] if n.startswith("ال") and n[2:] in self.insult_nouns else n for n in norms if n != "و"]
        if words and all(w in self.insult_nouns for w in words):
            key = " ".join(words)
            return Hit(text.strip(), Entry(key, key, LIGHT, "reply", "base"))
        return None

    def mask(self, text: str, layers: tuple[Lexicon, ...] = ()) -> str:
        """يرجع النص بعد تغطية كل كلمة مسيئة (ما نطلع أي كلمة بذيئة من البوت)."""
        if not text:
            return text
        all_layers = (*layers, self.base)
        parts = re.split(r"(\s+)", text)
        idx = [i for i, p in enumerate(parts) if p and not p.isspace()]
        norms = [_clean(prepare(parts[i])) for i in idx]
        bad: set[int] = set()
        # كلمات مفردة
        for k, n in enumerate(norms):
            if n and match_word(n, all_layers) is not None:
                bad.add(k)
        # عبارات (يا حمار، انعل ابوك...)
        for k, first in enumerate(norms):
            for f in (first, first[1:] if first[:1] in ("و", "ف") and len(first) > 3 else None):
                if not f:
                    continue
                for lx in all_layers:
                    for words, _ in lx.phrases.get(f, ()):
                        if tuple(norms[k + 1:k + len(words)]) == words[1:]:
                            span = [x for x in range(k, k + len(words)) if norms[x] not in _PLAIN]
                            bad.update(span or range(k, k + len(words)))
        # حروف مفرّقة (ك س م ك)
        k = 0
        while k < len(norms):
            if len(norms[k]) == 1:
                j = k
                while j < len(norms) and len(norms[j]) <= 1:
                    j += 1
                joined = _REPEAT.sub(r"\1", "".join(norms[k:j]))
                if j - k >= 2 and (match_word(joined, all_layers) or self.scan(joined, layers)):
                    bad.update(range(k, j))
                k = j
            else:
                k += 1
        if not bad:
            return text
        for k in bad:
            parts[idx[k]] = _mask_word(parts[idx[k]])
        return "".join(parts)

    def mask_html(self, text: str) -> str:
        """نفس mask بس لنص HTML: الوسوم (<b> ، <a href>) ما تنلمس، والكلام بينها ينفحص."""
        if not text:
            return text
        layers = (self.global_layer,) if self.global_layer is not None else ()
        parts = _HTML_PART.split(text)
        for i in range(0, len(parts), 2):   # الأجزاء الزوجية = كلام، الفردية = وسوم
            if parts[i].strip():
                parts[i] = self.mask(parts[i], layers)
        return "".join(parts)

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

    def collisions(self, entry_text: str, level: int, safe_items: list[str] | None = None,
                   kind: str | None = None) -> list[str]:
        """الكلمات السليمة اللي راح تنحظر لو انضافت هاي الكلمة (فحص قبل الاعتماد)."""
        if safe_items is None:
            from zhoo.data.swear_bank import safe_items as _items
            safe_items = _items()
        probe = Lexicon("probe")
        if probe.add(entry_text, level, kind) is None:
            return []
        bad: list[str] = []
        for item in safe_items:
            if item not in bad and any(_scan_view(v, (probe,), frozenset()) for v in views(item)):
                bad.append(item)
        return bad


detector = SwearDetector()
