"""رسم صور الكواكب والمجرات (بدون إنترنت): كل كوكب إله صورة ثابتة مرسومة من رقمه.

يحتاج مكتبة Pillow. إذا ما موجودة، الدوال ترجع None والكون يشتغل بدون صور.
"""
from __future__ import annotations

import io
import math
import random

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:          # pragma: no cover
    Image = None

SIZE = 512


def available() -> bool:
    return Image is not None


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _stars(img, rnd: random.Random, n: int = 260) -> None:
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = rnd.randrange(SIZE), rnd.randrange(SIZE)
        b = rnd.randint(90, 255)
        r = 1 if rnd.random() < 0.9 else 2
        tint = rnd.choice([(b, b, b), (b, b, 255), (255, b, b - 40 if b > 40 else b)])
        d.ellipse((x - r / 2, y - r / 2, x + r / 2, y + r / 2), fill=tint)


def _nebula(img, rnd: random.Random, color) -> Image:
    layer = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(7):
        cx, cy, r = rnd.randrange(SIZE), rnd.randrange(SIZE), rnd.randint(80, 220)
        c = tuple(max(0, min(255, int(v * rnd.uniform(0.25, 0.55)))) for v in color)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    layer = layer.filter(ImageFilter.GaussianBlur(60))
    return Image.blend(img, layer, 0.55)


def planet_png(seed: int, palette: tuple[tuple[int, int, int], tuple[int, int, int]], *, rings: bool,
               bands: int, craters: int, glow) -> bytes | None:
    if Image is None:
        return None
    rnd = random.Random(seed)
    img = Image.new("RGB", (SIZE, SIZE), (4, 6, 16))
    img = _nebula(img, rnd, glow)
    _stars(img, rnd)

    radius = rnd.randint(150, 180)
    cx = cy = SIZE // 2
    # سطح الكوكب: أشرطة ملونة متموجة
    surface = Image.new("RGB", (SIZE, SIZE), palette[0])
    ds = ImageDraw.Draw(surface)
    for i in range(bands):
        y = cy - radius + int((i + rnd.random() * 0.6) * 2 * radius / max(1, bands))
        h = rnd.randint(6, 26)
        col = _mix(palette[0], palette[1], rnd.random())
        wob = rnd.uniform(0, math.tau)
        pts = [(x, y + int(math.sin(x / 40 + wob) * 6)) for x in range(0, SIZE + 8, 8)]
        pts += [(x, y + h + int(math.sin(x / 33 + wob) * 6)) for x in range(SIZE, -8, -8)]
        ds.polygon(pts, fill=col)
    for _ in range(craters):
        x = cx + rnd.randint(-radius, radius)
        y = cy + rnd.randint(-radius, radius)
        r = rnd.randint(6, 24)
        ds.ellipse((x - r, y - r, x + r, y + r), fill=_mix(palette[0], (255, 255, 255), 0.18))
        ds.ellipse((x - r + 3, y - r + 3, x + r, y + r), fill=_mix(palette[0], (0, 0, 0), 0.3))
    surface = surface.filter(ImageFilter.GaussianBlur(2))

    # إضاءة كروية: فاتح من فوگ يسار، ظل من جوة يمين
    shade = Image.new("L", (SIZE, SIZE), 0)
    dsh = ImageDraw.Draw(shade)
    lx, ly = cx - radius * 0.45, cy - radius * 0.45
    for k in range(40, 0, -1):
        rr = radius * 1.75 * k / 40
        dsh.ellipse((lx - rr, ly - rr, lx + rr, ly + rr), fill=int(255 * (1 - k / 40) ** 0.7))
    dark = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    lit = Image.composite(surface, dark, shade.point(lambda v: min(255, 18 + int(v * 1.15))))

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))

    # هالة الغلاف الجوي
    halo = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    ImageDraw.Draw(halo).ellipse((cx - radius - 14, cy - radius - 14, cx + radius + 14, cy + radius + 14), fill=glow)
    halo = halo.filter(ImageFilter.GaussianBlur(18))
    img = Image.blend(img, halo, 0.45)

    ring_back = ring_front = None
    if rings:
        tilt = rnd.uniform(0.18, 0.32)
        rc = _mix(palette[1], (230, 220, 200), 0.4)
        ring_back = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        dr = ImageDraw.Draw(ring_back)
        for w in range(0, 46, 3):
            rx, ry = radius * 1.75 - w, (radius * 1.75 - w) * tilt
            dr.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=rc + (140 - w * 2,), width=2)
        ring_front = ring_back.copy()
        # الجزء الخلفي (فوگ الكوكب) ينرسم قبل الكوكب، والأمامي بعده
        ImageDraw.Draw(ring_back).rectangle((0, cy, SIZE, SIZE), fill=(0, 0, 0, 0))
        ImageDraw.Draw(ring_front).rectangle((0, 0, SIZE, cy), fill=(0, 0, 0, 0))
        img.paste(ring_back, (0, 0), ring_back)

    img.paste(lit, (0, 0), mask)
    if ring_front is not None:
        img.paste(ring_front, (0, 0), ring_front)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=86)
    return buf.getvalue()


def galaxy_png(seed: int, color) -> bytes | None:
    if Image is None:
        return None
    rnd = random.Random(seed)
    img = Image.new("RGB", (SIZE, SIZE), (3, 4, 12))
    _stars(img, rnd, 200)
    layer = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = cy = SIZE // 2
    arms = rnd.choice([2, 3, 4])
    twist = rnd.uniform(3.2, 4.6)
    for i in range(4200):
        arm = i % arms
        t = rnd.random() ** 0.8
        ang = arm * math.tau / arms + t * twist + rnd.gauss(0, 0.22)
        r = t * 220
        x = cx + math.cos(ang) * r + rnd.gauss(0, 7)
        y = cy + math.sin(ang) * r * 0.62 + rnd.gauss(0, 5)
        c = _mix((255, 245, 225), color, min(1, t * 1.3))
        s = rnd.choice([1, 1, 1, 2])
        d.ellipse((x - s, y - s, x + s, y + s), fill=c)
    glow = layer.filter(ImageFilter.GaussianBlur(6))
    core = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    ImageDraw.Draw(core).ellipse((cx - 42, cy - 28, cx + 42, cy + 28), fill=(255, 236, 200))
    core = core.filter(ImageFilter.GaussianBlur(22))
    for extra in (glow, layer, core):
        img = Image.blend(img, Image.composite(extra, img, extra.convert("L")), 0.85)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=86)
    return buf.getvalue()
