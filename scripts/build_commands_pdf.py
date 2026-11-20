"""يبني «دليل أوامر زهو» (PDF) تلقائياً من سجل الأوامر — شغّله بعد أي أمر جديد:

    python scripts/build_commands_pdf.py

يحتاج Node.js + Playwright + Chromium (على الحاسبة، مو بالموبايل).
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import zhoo.app  # noqa: E402,F401 — يسجل كل الأوامر
from zhoo import __version__  # noqa: E402
from zhoo.core.commands import registry  # noqa: E402
from zhoo.core.ranks import RANK_EMOJI, RANK_NAMES, Rank  # noqa: E402
from zhoo.keyboards.menus import SECTIONS  # noqa: E402

OUT = ROOT / "docs" / "ZHOO_Commands.pdf"
HIDDEN = {"watch_toggle"}   # أوامر مخفية ما تنكتب بالدليل
RANK_COLORS = {
    Rank.MEMBER: "#7c8b9a", Rank.VIP: "#d4a017", Rank.ADMIN: "#2e9c6a", Rank.SUPERVISOR: "#2878c8",
    Rank.MANAGER: "#7a4fd1", Rank.GENERAL_MANAGER: "#c2457a", Rank.OWNER: "#c0392b",
    Rank.PRIMARY_OWNER: "#a8326e", Rank.CREATOR: "#5a3d2b", Rank.DEVELOPER: "#111827",
}
SECTION_NOTES = {
    "punish": "العقوبات تقبل مدة وسبب: <code>كتم @user 30د سبام</code> ⋅ الوحدات: د دقيقة، س ساعة، ي يوم، ا أسبوع",
    "locks": "كل قفل يقبل عقوبة بعده: <code>قفل الصور بالكتم</code> ⋅ الأوضاع: بالمسح، بالتحذير، بالكتم، بالتقييد، بالطرد",
    "ranks": "كل رتبة ترفع وتنزّل اللي تحتها بس ⋅ ويا كل رفع تطلع لوحة صلاحيات بالأزرار",
    "ai": "الذكاء مطفي افتراضياً ⋅ يحتاج مفتاح Claude من المطور + <code>تفعيل الذكاء</code> من المالك",
}

e = html.escape


def rank_badge(rank: Rank) -> str:
    name = "الكل" if rank == Rank.MEMBER else RANK_NAMES[rank]
    emoji = "👥" if rank == Rank.MEMBER else RANK_EMOJI[rank]
    return f'<span class="badge" style="--c:{RANK_COLORS.get(rank, "#555")}">{emoji} {e(name)}</span>'


def command_rows(section_key: str) -> list[str]:
    cmds = [c for c in registry.commands if c.section == section_key and c.key not in HIDDEN]
    cmds.sort(key=lambda c: (c.order, c.min_rank, c.key))
    rows = []
    for c in cmds:
        if c.key.startswith("demote_") and c.key != "demote":
            continue   # ينكتب ويا «رفع» بنفس السطر
        names = list(c.names)
        main = names[0]
        if c.key.startswith("promote_"):   # «رفع مدير» + «تنزيل مدير» بسطر واحد
            main = f"رفع / تنزيل {main.replace('رفع ', '', 1)}"
            names = [main] + [n.replace("رفع ", "رفع / تنزيل ", 1) for n in names[1:]]
        alts = [n for n in names[1:] if n != main][:4]
        usage = f'<div class="usage">✍️ {e(c.usage)}</div>' if c.usage else ""
        where = ' <span class="where">🔒 بالخاص</span>' if c.where == "private" else ""
        alt_html = f'<div class="alts">{" ⋅ ".join(e(a) for a in alts)}</div>' if alts else ""
        rows.append(
            f'<tr><td class="cmd"><div class="name">{e(main)}{where}</div>{alt_html}{usage}</td>'
            f'<td class="desc">{e(c.description)}</td><td class="who">{rank_badge(Rank(c.min_rank))}</td></tr>')
    return rows


def sections_html() -> tuple[str, list[tuple[str, str, int]]]:
    parts, toc = [], []
    for s in SECTIONS:
        rows = command_rows(s.key)
        if not rows:
            continue
        toc.append((s.emoji, s.title, len(rows)))
        note = f'<div class="note">💡 {SECTION_NOTES[s.key]}</div>' if s.key in SECTION_NOTES else ""
        dev = ' <span class="devtag">خاص بالمطور</span>' if s.key == "dev" else ""
        parts.append(
            f'<section class="sec"><h2><span class="sec-emoji">{s.emoji}</span> {e(s.title)}{dev}'
            f'<span class="count">{len(rows)} أمر</span></h2>{note}'
            '<table><thead><tr><th>الأمر</th><th>شنو يسوي</th><th>منو يكدر</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></section>")
    return "".join(parts), toc


EMBLEM = """
<svg viewBox="0 0 240 260" class="emblem" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f9c6d8"/><stop offset="1" stop-color="#b48ee8"/>
    </linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity=".95"/><stop offset="1" stop-color="#ffe9f2" stop-opacity=".9"/>
    </linearGradient>
  </defs>
  <path d="M120 18 L212 52 V128 C212 186 172 226 120 246 C68 226 28 186 28 128 V52 Z" fill="url(#g1)"/>
  <path d="M120 34 L198 63 V128 C198 177 164 212 120 230 C76 212 42 177 42 128 V63 Z" fill="url(#g2)"/>
  <path d="M86 70 L98 46 L110 64 L120 40 L130 64 L142 46 L154 70 Z" fill="#d4a017"/>
  <circle cx="98" cy="46" r="4" fill="#d4a017"/><circle cx="120" cy="40" r="4.5" fill="#d4a017"/>
  <circle cx="142" cy="46" r="4" fill="#d4a017"/>
  <text x="120" y="152" text-anchor="middle" font-family="Amiri" font-weight="700" font-size="62"
        fill="#7a3b69">زَهـو</text>
  <text x="120" y="190" text-anchor="middle" font-family="Cairo" font-weight="800" font-size="20"
        letter-spacing="6" fill="#a8326e">ZHOO</text>
  <g transform="translate(120 214)">
    <circle r="7" fill="#f28db2"/><circle cx="-12" r="5" fill="#f7b6cd"/><circle cx="12" r="5" fill="#f7b6cd"/>
  </g>
</svg>
"""

CHAT_PREVIEW = """
<div class="phone">
  <div class="bubble me">زهو</div>
  <div class="bubble bot"><b>زَهـو</b><br>عيوني، آني هنا 🤍</div>
  <div class="bubble me">الاوامر</div>
  <div class="bubble bot"><b>✿ قائمة أوامر زهو 🎀</b><br>─── ⋆⋅🤍⋅⋆ ───<br>◈ رتبتك: 🏛 صاحب المجموعة<br>◈ اختار القسم اللي تريده 🌸
    <div class="btns"><span>🧭 العامة</span><span>👥 الرتب</span><span>⛔ العقوبات</span><span>🛡 الحماية</span>
    <span>🔒 القفل</span><span>⚙️ الإعدادات</span><span>🎮 الألعاب</span><span>💰 الاقتصاد</span></div></div>
  <div class="bubble me">حظر <i>(بالرد على شخص)</i></div>
  <div class="bubble bot"><b>✿ تَـمَّ الـحَـظْـر 🚫</b><br>◈ العضو: فلان<br>◈ بواسطة: انت
    <div class="btns"><span>🕊 فك الحظر</span></div></div>
</div>
"""


def build_html() -> str:
    body, toc = sections_html()
    total = sum(n for _, _, n in toc)
    toc_html = "".join(f'<div class="toc-item"><span>{em} {e(n)}</span><b>{c}</b></div>' for em, n, c in toc)
    ladder = "".join(
        f'<div class="rung" style="--c:{RANK_COLORS[r]}"><span>{RANK_EMOJI[r]} {e(RANK_NAMES[r])}</span>'
        f'<small>{e(how)}</small></div>'
        for r, how in [
            (Rank.DEVELOPER, "مالكة زهو — كل المجموعات"), (Rank.CREATOR, "منشئ المجموعة بتيليجرام"),
            (Rank.PRIMARY_OWNER, "يرفعه صاحب المجموعة"), (Rank.OWNER, "تعطيل زهو، الذكاء، التقارير"),
            (Rank.GENERAL_MANAGER, "يرفع مدراء وأقل"), (Rank.MANAGER, "الحظر والإعدادات"),
            (Rank.SUPERVISOR, "الطرد + مشرف بتيليجرام"), (Rank.ADMIN, "الكتم والتقييد والأقفال"),
            (Rank.VIP, "يرسل الصور والملصقات المقفولة"), (Rank.MEMBER, "الأوامر العامة والألعاب"),
        ])
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&family=Amiri:wght@700&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 14mm 12mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Cairo, 'Noto Color Emoji', sans-serif; color: #2b2233; margin: 0; font-size: 10.5pt; line-height: 1.6; }}
code {{ font-family: Cairo; background: #f6eef8; color: #7a3b69; padding: 0 5px; border-radius: 4px; }}
.cover {{ height: 265mm; display: flex; flex-direction: column; align-items: center; justify-content: center;
          text-align: center; background: radial-gradient(circle at 30% 20%, #ffe3ef 0, #fff 45%),
          radial-gradient(circle at 80% 85%, #ece2ff 0, transparent 45%); border-radius: 18px; page-break-after: always; }}
.emblem {{ width: 78mm; filter: drop-shadow(0 10px 22px rgba(168,50,110,.25)); }}
.cover h1 {{ font-family: Amiri; font-size: 40pt; margin: 6mm 0 0; color: #7a3b69; }}
.cover .sub {{ font-size: 14pt; color: #a8326e; font-weight: 600; margin-top: 2mm; }}
.cover .line {{ color: #c79bc0; letter-spacing: 3px; margin: 5mm 0; }}
.cover .stats {{ display: flex; gap: 6mm; margin-top: 4mm; }}
.cover .stat {{ background: #fff; border: 1.5px solid #f1d3e3; border-radius: 14px; padding: 3mm 7mm; min-width: 34mm; }}
.cover .stat b {{ display: block; font-size: 20pt; color: #a8326e; }}
.cover .ver {{ margin-top: 10mm; color: #9a8aa5; font-size: 9pt; }}
h2 {{ font-size: 15pt; color: #fff; background: linear-gradient(90deg, #a8326e, #7a4fd1); padding: 2.5mm 5mm;
      border-radius: 12px; margin: 0 0 3mm; display: flex; align-items: center; gap: 3mm; }}
h2 .count {{ margin-inline-start: auto; font-size: 9.5pt; background: rgba(255,255,255,.22); padding: 0 4mm; border-radius: 99px; }}
.devtag {{ font-size: 8.5pt; background: #111827; padding: 0 3mm; border-radius: 99px; }}
.guide {{ page-break-after: always; }}
.steps {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; margin-bottom: 3.5mm; }}
.step {{ border: 1.5px solid #f1d3e3; border-radius: 14px; padding: 2.5mm 4mm; background: #fffafc; }}
.step .n {{ display: inline-grid; place-items: center; width: 8mm; height: 8mm; border-radius: 50%; background: #a8326e;
            color: #fff; font-weight: 800; margin-left: 2mm; }}
.step b {{ color: #7a3b69; }}
.step p {{ margin: 1mm 0 0; color: #5b4d63; font-size: 9pt; line-height: 1.5; }}
.two {{ display: grid; grid-template-columns: 1.05fr .95fr; gap: 4mm; }}
.box {{ border: 1.5px solid #e7dcf5; border-radius: 14px; padding: 3mm; background: #fcfaff; }}
.box h3 {{ margin: 0 0 1.5mm; color: #7a4fd1; font-size: 11pt; }}
.rung {{ display: flex; justify-content: space-between; align-items: center; border-right: 5px solid var(--c);
         background: #fff; padding: .6mm 3mm; margin-bottom: 1mm; border-radius: 6px; font-weight: 600; font-size: 9.5pt; }}
.rung small {{ color: #7d6f87; font-weight: 400; font-size: 8.6pt; }}
.tips ul {{ margin: 0; padding-right: 5mm; }} .tips li {{ margin-bottom: .6mm; font-size: 9pt; line-height: 1.5; }}
.phone {{ background: #17212b; border-radius: 18px; padding: 3mm; }}
.bubble {{ max-width: 90%; padding: 1.5mm 3mm; border-radius: 12px; margin-bottom: 1.6mm; font-size: 8.6pt; line-height: 1.45; }}
.bubble.me {{ background: #2b5278; color: #fff; margin-right: auto; width: fit-content; }}
.bubble.bot {{ background: #182533; color: #e8eef5; border: 1px solid #2a3b4d; }}
.bubble.bot b {{ color: #f3a6c8; }}
.btns {{ display: flex; flex-wrap: wrap; gap: 1.5mm; margin-top: 2mm; }}
.btns span {{ background: #2a3b4d; color: #dbe7f3; border-radius: 7px; padding: .6mm 2.5mm; font-size: 8.4pt; }}
.toc {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5mm; }}
.toc-item {{ display: flex; justify-content: space-between; background: #fff; border: 1px solid #efe2f3; border-radius: 8px;
             padding: .4mm 2.5mm; font-size: 8.6pt; }}
.toc-item b {{ color: #a8326e; }}
.sec {{ margin-bottom: 7mm; }}
.note {{ background: #fff7e6; border: 1px solid #f6d999; border-radius: 10px; padding: 2mm 4mm; margin-bottom: 2.5mm; font-size: 9.3pt; }}
table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 9.4pt; }}
thead th {{ background: #f6eef8; color: #7a3b69; text-align: right; padding: 1.8mm 3mm; font-weight: 800; }}
thead th:first-child {{ border-radius: 0 10px 10px 0; }} thead th:last-child {{ border-radius: 10px 0 0 10px; }}
tbody tr {{ break-inside: avoid; }}
tbody td {{ padding: 2mm 3mm; border-bottom: 1px solid #f1e8f4; vertical-align: top; }}
tbody tr:nth-child(even) td {{ background: #fdfbfe; }}
td.cmd {{ width: 36%; }} td.who {{ width: 17%; white-space: nowrap; }}
.name {{ font-weight: 800; color: #2b2233; font-size: 10.2pt; }}
.alts {{ color: #8c7d96; font-size: 8.4pt; }}
.usage {{ color: #2878c8; font-size: 8.4pt; }}
.where {{ font-size: 8pt; color: #c0392b; font-weight: 600; }}
.badge {{ display: inline-block; border: 1.5px solid var(--c); color: var(--c); border-radius: 99px; padding: 0 2.5mm;
          font-size: 8.6pt; font-weight: 700; background: #fff; }}
.end {{ text-align: center; color: #a8326e; margin-top: 8mm; font-family: Amiri; font-size: 16pt; }}
</style></head><body>

<div class="cover">
  {EMBLEM}
  <h1>دليل أوامر زهو</h1>
  <div class="sub">بوت حماية وإدارة المجموعات 🛡 بروح عراقية 🤍</div>
  <div class="line">─── ⋆⋅🤍⋅⋆ ───</div>
  <div class="stats">
    <div class="stat"><b>{total}</b>أمر</div>
    <div class="stat"><b>{len(toc)}</b>قسم</div>
    <div class="stat"><b>10</b>رتب</div>
  </div>
  <div class="ver">الإصدار {e(__version__)}</div>
</div>

<div class="guide">
  <h2>🚀 شلون تبدأ بزهو؟ <span class="count">4 خطوات</span></h2>
  <div class="steps">
    <div class="step"><span class="n">1</span><b>ضيف زهو للمجموعة</b>
      <p>افتح زهو بتيليجرام ← «إضافة إلى مجموعة» ← اختار مجموعتك.</p></div>
    <div class="step"><span class="n">2</span><b>ارفعها مشرفة</b>
      <p>إعدادات المجموعة ← المشرفين ← زهو، وانطيها: حذف الرسائل، حظر المستخدمين، دعوة المستخدمين، تثبيت الرسائل، تغيير المعلومات، وإضافة مشرفين.</p></div>
    <div class="step"><span class="n">3</span><b>اكتب «الاوامر»</b>
      <p>تطلع قائمة بالأزرار حسب رتبتك، اضغط على أي قسم وتشوف أوامره وشرحها.</p></div>
    <div class="step"><span class="n">4</span><b>رتّب الإدارة والحماية</b>
      <p>ارفع طاقمك (<code>رفع مدير</code> بالرد)، وشغّل الحماية: <code>مستوى الحماية متوسط</code> و <code>قفل السب</code>.</p></div>
  </div>
  <div class="two">
    <div>
      <div class="box"><h3>🎖 سُلّم الرتب</h3>{ladder}</div>
      <div class="box tips" style="margin-top:4mm"><h3>✨ نصايح سريعة</h3><ul>
        <li><b>بالرد/اليوزر/الايدي</b>: رد على رسالة الشخص، أو اكتب <code>@يوزره</code> أو ايديه بعد الأمر.</li>
        <li><b>المدة</b>: <code>كتم 30د</code> ⋅ <code>حظر 2ي</code> ⋅ بدون مدة = دائم.</li>
        <li><b>الغاء</b>: يوقف أي أمر يطلب منك خطوات (مثل اضف رد).</li>
        <li><b>الأزرار</b>: أغلب القوائم بيها أزرار، اضغط بدل ما تكتب.</li>
        <li><b>ايقاف زهو</b> يسكتها مؤقتاً، و<b>فتح زهو</b> يرجعها.</li>
      </ul></div>
    </div>
    <div>{CHAT_PREVIEW}
      <div class="box" style="margin-top:4mm"><h3>📚 الأقسام</h3><div class="toc">{toc_html}</div></div>
    </div>
  </div>
</div>

{body}
<div class="end">✿ زهو بالخدمة دايماً 🤍 ✿</div>
</body></html>"""


_NODE_RENDER = r"""
const { chromium } = require('playwright');
(async () => {
  const [src, out] = process.argv.slice(1);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + src, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: out, format: 'A4', printBackground: true, displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;text-align:center;font-size:8px;color:#a8326e">' +
      '✿ زهو ⋅ <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: { top: '14mm', bottom: '16mm', left: '12mm', right: '12mm' } });
  await browser.close();
})();
"""


def main() -> None:
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "commands.html"
        src.write_text(build_html(), encoding="utf-8")
        if "--html" in sys.argv:
            (ROOT / "docs" / "commands_preview.html").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["node", "-e", _NODE_RENDER, str(src), str(OUT)], check=True)
    print(f"✅ {OUT}")


if __name__ == "__main__":
    main()
