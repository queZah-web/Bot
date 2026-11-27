"""محرك الكون: كل كوكب يتولّد من رقمه (نفس الرقم = نفس الكوكب دائماً)، فما نحتاج نخزن 30 ألف كوكب.

الكود: «رقم المجرة-رقم الكوكب» مثل 2-1250.
السعر = الأساس × سوق المجرة اليوم (±) × التخفيض (إذا المجرة عليها تخفيض بهاي الفترة).
البيع للبنك المركزي = 85% من سعر السوق بدون تخفيض ← اشتري بالتخفيض وبيع بعدين وتربح.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from functools import lru_cache

from zhoo.data import space_bank as B

SELL_RATE = 0.85
SALE_SLOT = 6 * 3600           # كل 6 ساعات تتبدل التخفيضات
SALE_GALAXIES = 2
INCOME_RATE = (0.008, 0.016)   # الدخل اليومي من سعر الأساس
GALAXY_KEYS = [g[0] for g in B.GALAXIES]


@dataclass(frozen=True)
class Galaxy:
    num: int
    key: str
    name: str
    emoji: str
    color: tuple[int, int, int]
    mult: float
    count: int
    about: str


GALAXIES = [Galaxy(i + 1, *g) for i, g in enumerate(B.GALAXIES)]


@dataclass(frozen=True)
class Planet:
    galaxy: int
    idx: int
    name: str
    kind: str
    rarity: str
    diameter: int
    moons: int
    temp: int
    life: bool
    base: int
    income: int
    rings: bool
    seed: int

    @property
    def code(self) -> str:
        return f"{self.galaxy}-{self.idx}"


def galaxy(num: int) -> Galaxy | None:
    return GALAXIES[num - 1] if 1 <= num <= len(GALAXIES) else None


def find_galaxy(text: str) -> Galaxy | None:
    from zhoo.core.normalize import normalize
    t = normalize((text or "").replace("مجرة", "").replace("مجره", "").strip())
    if t.isdigit():
        return galaxy(int(t))
    for g in GALAXIES:
        if t and (t == normalize(g.name) or t in normalize(g.name)):
            return g
    return None


def _pick(rnd: random.Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rnd.choices(keys, weights=[weights[k] for k in keys])[0]


@lru_cache(maxsize=20000)
def planet(gnum: int, idx: int) -> Planet | None:
    g = galaxy(gnum)
    if g is None or not 1 <= idx <= g.count:
        return None
    seed = gnum * 1_000_003 + idx * 7919
    rnd = random.Random(seed)
    weights = {k: v[2] for k, v in B.RARITIES.items()}
    if g.key == "zhoo":                      # مجرة زهو: الندرة أعلى
        weights = {"common": 40, "rare": 35, "epic": 18, "legendary": 7}
    rarity = _pick(rnd, weights)
    kind = _pick(rnd, B.TYPE_WEIGHTS[rarity])
    t = B.PLANET_TYPES[kind]
    diameter = rnd.randint(*t[7]) // 10 * 10
    size_f = 0.75 + 0.75 * (diameter - t[7][0]) / max(1, t[7][1] - t[7][0])
    lo, hi = B.RARITIES[rarity][3], B.RARITIES[rarity][4]
    base = int(rnd.randint(lo, hi) * g.mult * size_f) // 10 * 10
    name = rnd.choice(B.NAME_START) + rnd.choice(B.NAME_END)
    return Planet(
        galaxy=gnum, idx=idx, name=name, kind=kind, rarity=rarity, diameter=diameter,
        moons=rnd.choice([0, 0, 1, 1, 2, 3, 4, 5, 7]) if kind != "gas" else rnd.randint(2, 30),
        temp=rnd.randint(*t[8]), life=rnd.random() < t[9], base=base,
        income=max(5, int(base * rnd.uniform(*INCOME_RATE))), rings=rnd.random() < t[4], seed=seed,
    )


def parse_code(text: str) -> Planet | None:
    raw = (text or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")).replace(" ", "").replace("/", "-")
    if raw.count("-") != 1:
        return None
    a, b = raw.split("-")
    if not (a.isdigit() and b.isdigit()):
        return None
    return planet(int(a), int(b))


# ── السوق والتخفيضات ────────────────────────────────
def _day(ts: float | None = None) -> int:
    return int((ts or time.time()) + 3 * 3600) // 86400       # يوم بتوقيت بغداد


def market_factor(gnum: int, ts: float | None = None) -> float:
    """سوق المجرة اليوم: بين -15% و +20%."""
    return round(random.Random(_day(ts) * 131 + gnum).uniform(0.85, 1.20), 3)


def sale_slot(ts: float | None = None) -> int:
    return int(ts or time.time()) // SALE_SLOT


def sales(ts: float | None = None) -> dict[int, int]:
    """المجرات اللي عليها تخفيض هسه ← نسبة التخفيض."""
    rnd = random.Random(sale_slot(ts) * 977)
    picks = rnd.sample(range(1, len(GALAXIES) + 1), SALE_GALAXIES)
    return {g: rnd.choice([20, 25, 30, 35, 40, 50]) for g in picks}


def sale_left(ts: float | None = None) -> int:
    now = int(ts or time.time())
    return SALE_SLOT - now % SALE_SLOT


def market_price(p: Planet, ts: float | None = None) -> int:
    return int(p.base * market_factor(p.galaxy, ts)) // 10 * 10


def buy_price(p: Planet, ts: float | None = None) -> tuple[int, int]:
    """(السعر، نسبة التخفيض)"""
    off = sales(ts).get(p.galaxy, 0)
    return int(market_price(p, ts) * (100 - off) / 100) // 10 * 10, off


def sell_price(p: Planet, ts: float | None = None) -> int:
    return int(market_price(p, ts) * SELL_RATE) // 10 * 10


@lru_cache(maxsize=64)
def rarest(gnum: int, rarity: str = "legendary", limit: int = 30) -> tuple[int, ...]:
    g = galaxy(gnum)
    out = []
    for i in range(1, g.count + 1):
        if planet(gnum, i).rarity == rarity:
            out.append(i)
            if len(out) >= limit:
                break
    return tuple(out)


def random_planet(rnd: random.Random | None = None, gnum: int | None = None) -> Planet:
    rnd = rnd or random
    g = galaxy(gnum) if gnum else rnd.choices(GALAXIES, weights=[1 / g.mult for g in GALAXIES])[0]
    return planet(g.num, rnd.randint(1, g.count))


def art_args(p: Planet) -> dict:
    t = B.PLANET_TYPES[p.kind]
    return dict(palette=t[2], rings=p.rings, bands=t[5], craters=t[6], glow=t[3])
