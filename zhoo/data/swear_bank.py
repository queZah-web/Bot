"""قاموس السب الأساسي (عراقي + عربي + إنجليزي + عربيزي).

المستويات:
  1 خفيف   — إهانات (يا حمار، يا حقير...)
  2 متوسط  — شتائم ولعن (انعل ابوك، ابن الكلب...)
  3 شديد   — كلام بذيء جنسي، والتجاوز على الدين والعرض

أنواع المطابقة (المحرك يقررها تلقائياً، وهنا نحددها صراحة):
  EXACT   — كلمة كاملة فقط، بدون بادئات (إلا «يا») وبدون لواحق: للكلمات القصيرة الحساسة
  STEMS   — جذر يقبل بادئات (و، ب، ال...) ولواحق ملكية (ك، ج، ه، كم...)
  PHRASES — عبارات؛ الكلمة الأخيرة تتصرف تلقائياً (ابوك ← ابوج، ابوكم...) وتنكشف حتى لو متلزگة

⚠️ أي كلمة جديدة لازم تنفحص ضد SAFE_WORDS (الاختبارات تسويها تلقائياً).
لا تضيف كلمة فصحى لها معنى سليم شائع ككلمة مفردة (مثل: قواد = قادة، عرصة = ساحة،
زبر = قطع/كتب، الزانية = آية، لواط = مصطلح فقهي، اير = Air) — خليها بعبارة («يا قواد»).
"""
from __future__ import annotations

LIGHT, MEDIUM, SEVERE = 1, 2, 3

EXACT: dict[int, str] = {
    SEVERE: """
        كس كسك كسج كسه كسها كسكم كسمك كسامك كسختك كسعرضك كسابوك كسعرض كسختج كسمج كسربك
        عير عيري عيرك عيرج عيره عيرها عيربيك عيربيج عيرابوك عيريبيك
        ايري ايرك ايرج ايربيك ايربيج
        زب زبي زبك زبج زبه زبها
        نيك نيكك نيكج انيك انيكك انيكج ناكك ناكج
        نيج نيجك نيجج انيج انيجك انيجج اتنيج تتنيج ينيج نياج نايج
        قحبات كحبات
        fuck fuk fck fucking fucker fucked motherfucker pussy cunt dick nigger
        kos kosomak kosomk ksomak kosmak kusomak kusumak kosokhtak kosokhtk
        ayre ayri ayrak 3ir 3iri 3irak neek neekak manyook manyok manyouk mnyok
    """,
    MEDIUM: """
        كوادين قوادين معرصين نغل عرص خرا خره
        bitch bitches whore slut asshole bastard shit
        sharmouta sharmota sharmoota ga7ba gahba kahba qahba qa7ba kawad gawad
    """,
    LIGHT: """
        teezak teezek
    """,
}

STEMS: dict[int, str] = {
    SEVERE: """
        طيز طياز
        منيوج منيوك منيك منيكه متناك متناكه
        قحبه كحبه قحاب كحاب
        شرموط شرموطه شراميط
    """,
    MEDIUM: """
        كواد كواده معرص معرصه
        فاجره عاهر عاهره
        لوطي لوطيين مخنث خنيث
        ديوث ديوس
    """,
    LIGHT: """
        سرسري سرسريه سرسريه
        مازوخي مازوخيه
        هتلي هتليه
    """,
}

_PHRASES_SEVERE = [
    "كس امك", "كس اختك", "كس عرضك", "كس ابوك", "كس اهلك", "كس امج", "كس اختج", "كس ربك",
    "عير بيك", "عيري بيك", "عير ابوك", "عير بامك", "اير بيك", "اير ابوك", "زب ابوك",
    "ابن القحبه", "ابن الكحبه", "ابن الشرموطه", "ابن المنيوك", "ابن المنيوج", "بنت القحبه",
    "انعل شرفك", "انعل عرضك", "انعل اختك", "يلعن شرفك", "يلعن عرضك",
    "انعل دينك", "انعل ربك", "يلعن دينك", "يلعن ربك", "انعل مذهبك",
]

_PHRASES_MEDIUM = [
    "انعل ابوك", "انعل ابو ابوك", "انعل امك", "انعل والديك", "انعل والدينك",
    "انعل اهلك", "انعل جدك", "انعل خلفتك", "انعل سلفاك",
    "نعل ابوك", "نعال ابوك", "انعال ابوك",
    "يلعن ابوك", "يلعن امك", "يلعن اهلك", "يلعن والديك", "يلعن جدك",
    "الله يلعنك", "لعنه على ابوك", "لعنة الله عليك",
    "ابن الكواد", "ابن القواد", "يا قواد", "انت قواد", "قواد ابن قواد",
    "ابن الزنا", "ابن زنا", "ولد زنا", "ابن الحرام", "بنت الحرام", "يا زانيه", "ابن الزانيه",
    "ابن النغل", "يا عرص", "ابن العرص",
    "خرا عليك", "خره عليك", "خرا بيك", "اكل خرا",
]

# ── الإهانات (فئة خفيفة) — مذكر ومؤنث، عربي وعراقي ──
# كل اسم ينولد منه: «يا X» و«انت X» و«انتي X» و«زهو X»، والحيوانات كمان «ابن الX» و«بنت الX».
# ونفس الأسماء تنحسب إهانة إذا انكتبت لوحدها كرد على شخص (أو على زهو): رد بـ «قذر» = إهانة.
INSULTS_ANIMALS = [
    "كلب", "كلبه", "جلب", "جلبه", "حمار", "حماره", "زمال", "مطي", "مطيه", "حيوان", "حيوانه",
    "خنزير", "خنزيره", "جحش", "جحشه", "بغل", "بغله", "قرد", "قرده", "هايشه", "هايش", "ثور",
    "بقره", "جاموسه", "جاموس", "صرصور", "صرصوره", "عجل",
]
INSULTS_PEOPLE = [
    "حقير", "حقيره", "سافل", "سافله", "واطي", "واطيه", "نذل", "نذله", "وسخ", "وسخه", "وصخ", "وصخه",
    "منحط", "منحطه", "جايف", "جايفه", "زباله", "قندره", "قذر", "قذره", "لعين", "لعينه", "ملعون", "ملعونه",
    "نجس", "نجسه", "عفن", "عفنه", "معفن", "معفنه", "خسيس", "خسيسه", "دنيء", "دنيئه", "حثاله",
    "ساقط", "ساقطه", "لقيط", "لقيطه",
    # المزاح الخفيف مسموح: غبي، اهبل، مخبل، تافه، خايس، نعال، زربة، اغبر...
]
# أسماء «يا X» بس (لأن «انت X» ممكن تكون كلام عادي: انت دايح؟)
_INSULTS_YA_ONLY: list[str] = []
# «ابن الX / بنت الX»
_PARENT_INSULTS = INSULTS_ANIMALS + ["قندره", "جبه", "زباله", "وسخه", "حقيره", "سافله", "لعينه", "ملعونه",
                                      "نجسه", "قذره", "منحطه", "جايفه"]


def _light_phrases() -> list[str]:
    out: list[str] = []
    for w in INSULTS_ANIMALS + INSULTS_PEOPLE:
        out += [f"يا {w}", f"انت {w}", f"انتي {w}", f"زهو {w}"]
    for w in _PARENT_INSULTS:
        out += [f"ابن ال{w}", f"بنت ال{w}", f"يا ابن ال{w}", f"يا بنت ال{w}"]
    for w in _INSULTS_YA_ONLY:
        out.append(f"يا {w}")
    out += [
        "ابن كلب", "كلب ابن كلب", "ابوك كلب", "جلب ابن جلب", "زمال ابن زمال", "مطي ابن مطي", "حمار ابن حمار",
        "تفو عليك", "تفو عليج", "تفو بوجهك", "اجب عليك", "اجب عليج", "جب عليك",
        "وجهك قندره", "وجهج قندره", "يا وجه القندره", "يا وجه النحس",
    ]
    return out


PHRASES: dict[int, list[str]] = {
    SEVERE: _PHRASES_SEVERE,
    MEDIUM: _PHRASES_MEDIUM,
    LIGHT: _light_phrases(),
}

# ── كلمات سليمة تشبه السب: لازم ما تنحظر أبداً (الشرطة السفلية تعني مسافة) ──
# أي كلمة تنضاف للقاموس (أساسي أو من المشرفين) تنفحص ضدها قبل الاعتماد.
SAFE_WORDS = """
عكس العكس بالعكس عكسه انعكاس كسرة كسر مكسور انكسر كسل كسلان كسب مكسب اكتساب كسوة كساء
كسوف كسرات كسارة مكسرات اكسسوارات اكسسوار مكسيك فكس بكس لكس تكسي تاكسي كسكسي كسبرة
زبون زبائن زبيب زبدة زبادي زبرجد زبر الزبور زبير الزبير زبيدة زبالة
بعير العير النفير غير غيرك غيره خير خيرك طير طيور سير مسير تعيير تعيرني عيران
باير فاير واير اير لاين اير بودز ماك بوك اير ايران ايراني طاير ايره
نيكول نيكي نيكولا نيكاراغوا ونيك
طيزان
قحط قحب
كوادر الكوادر كوادرنا قادة قواد_الجيش
عرصات عرصة الدار
الزانية والزاني فاجلدوا الزنا
لوط قوم_لوط اللواط
ديوان دين دينك ربك ربنا الله
الكلب كلاب جلب يجلب جلبنا حمار الحمار زمالة زميل مطية حيوانات خنزير
ساقط ساقطة سقط حقيبة سافر سافرة واطية نذر وسخ_الثياب
ابوك امك اختك اخوك اهلك شرفك عرضك ديني
الشيطان_اللعين اعوذ_بالله_من_الشيطان_اللعين قندرة_جديدة اشتريت_قندره حليب_البقرة ثور_هائج جبة_صوف
السطل_مليان الكلب_نايم_بالبيت حمار_الوحش الطلي_والخروف العجل_المشوي
الحس_الوطني ان_يجي لازم_ان_يجيب_الغدا ان_يكون انيقة انيق نيجيريا نيكول فشخرة افشاء_السر الازبك
ازبكستان ازبكي منيو_المطعم انفسخ_العقد بغي_الظالم الخراج ابو_الحسن الزاني_والزانية حكم_اللواط البزاز محل_البزاز جلاخ_السكاكين
مصلي_الجمعة الناجي ازبكستان الازبك فرخ_الدجاج فرخ_الحمام خول_له دين_الله ابو_حرام_الدين
sara sarah ears arsenal art nick nike zina tiz tez eri eric kiss class pass bass mass kus
her here every error neck user order
غبي غبيه يا_غبي يا_غبيه نعال زربه اغبر اهبل يا_اهبل مخبل تافه خايس يا_خايس طلي سطل الكلب_نايم
الشيطان_الملعون الشيطان_اللعين
ابو_شارع_فلسطين دين_الاسلام سددت_دين_ابوك
شكرا مرحبا صباح الخير مساء النور حبيبي حبيبتي الله يحفظك تسلم
انعكاسات تكسير مكاسب كسالى كسوة_العيد
kiss kissing kids cos cost costs nick nickname dickens bass class pass assess assessment
scunthorpe shiitake cocktail analysis therapist grape skills
ayran kosovo
"""


def safe_items() -> list[str]:
    """الكلمات السليمة كقائمة (الشرطة السفلية = مسافة: قواد_الجيش ← قواد الجيش)."""
    return [w.replace("_", " ") for w in SAFE_WORDS.split()]


# ════════════════════════════════════════════════════════════════════
# القاموس العراقي الموسع (مرتب من ملف المالكة + إضافات فشار وكفر عراقية)
# الصيغ ويا البادئات (ب، ف، و، ال) واللواحق (ك، ج، ه، ها، كم، ي، ات، ين) تنكشف تلقائياً،
# فهنا نكتب الأصل بس. والكلمات اللي إلها معنى سليم بالفصحى تنضاف كعبارات بس.
# ════════════════════════════════════════════════════════════════════
_RELATIONS = ("ابن", "بنت", "ولد", "ابو", "ام", "اخت", "اخو", "اولاد", "اخوات", "خوات")
# «ابن الـ...» ونحوها
_FAMILY_VULGAR = ("ديوث", "زنا", "شرموطه", "عاهره", "عرص", "قحبه", "كحبه", "قواد", "كواد", "منيوجه",
                  "منيوكه", "مومسه", "حرام", "متناكه", "داعره", "فرخه")
_FAMILY_INSULT = ("جلب", "كلب", "حمار", "حيوان", "خنزير", "زباله", "وسخه", "شارع", "شوارع", "زمال", "مطي")
# أفعال تنقال على الأهل
_CURSE_VERBS = ("يلعن", "انعل", "نعل", "الله يلعن", "بول على", "بول علي", "خرا على", "خرا علي")
_SEXUAL_VERBS = ("افشخ", "فشخ", "جلخ", "انيج", "نيج", "نيك", "انيك")
_FAMILY_OBJECTS = ("ابوك", "امك", "اختك", "اخوك", "اهلك", "بنتك", "خالتك", "عمتك", "زوجتك", "شرفك", "عرضك",
                   "جدك", "خلفتك", "سلفاك")
# كفر وتجاوز على المقدسات (عراقي)
_SACRED = ("ربك", "دينك", "مذهبك", "نبيك", "رسولك", "طايفتك", "الله", "القران", "ربكم", "دينكم")
_BODY_WORDS = ("كس", "عير", "زب", "طيز")
_KUFR_VERBS = ("يلعن", "انعل", "نعل", "الله يلعن", "كس", "عير", "زب", "طيز", "نيج", "نيك", "انيج", "افشخ",
               "فشخ", "جلخ", "بول على", "بول علي", "خرا على", "خرا علي", "خرا ب")


def _expanded() -> tuple[dict[int, str], dict[int, str], dict[int, list[str]]]:
    exact = {
        SEVERE: """
            كسم كسي كسهم كسمه كسخت كسختي ازبج اخرا امصلي الحسلي انفشخ فاشخ فشخت فشخك فشخج فشخه
            جلخت جلخني ناك بعبص بعبوص بعبصك بزازج بزازك بزازها بزازكم بزازهم مفشوخ مفشوخه مصني مصيلي
            kos koss kosomak kosomk kosomek kosmak kosamk ksomak ksmk kusomak
            zib zibi zibk zibik zibak zebi zebbi zebk zebik zebak zubi
            3yri 3yrak 3yrk 3ayri eyri
            nayek nayej nayik nayij nayjk nayeg niyak niyej niyik nyak anik anayek anayej
            manyok mnyok manyuk munyuk menyok minyuk manyoj manyooj manyog manyoog manyoga
            mnyoj mnyooj mnyoog mnyoga mitnak metnak mtnak mutnak mtnaak metnaka mitnaka mtnaka mtnaaka mutnaka
            teezi teezk teiz tizi tizk tizak
            fashkh fshkh fashakh fshakh fashkha fashakhk fashakhet
            jalakh jlakh jalkh jlkh majlakh mjalakh jalakhni jalakni jalakhet
        """,
        MEDIUM: """
            خراك
            sharmoota sharmouta shrmota sharmuta sharmoto sharmoots sharmoot sharamit
            qahbe qahbat qahab kahbi kahbeh kahbe kahbat kahbah kahab
            qawwad qawwed qawad kawwed kawwad gawwad
            dayouth dayoos dyuth dyooth dayyuth dayyouth dayuth dayus dayous dayoth dayooth dayoot
            khanith khnith khaneeth khanees khanis mkhanith mkhanath mkhanas
            lawat lwat lawati lwati lawaty lwaty lawaati lwaati luti
            mumis moomis momis mo3ars mu3ars mo3rs
            3ahera 3ahir 3ahira 3ahrah
            khara kharaa khra khrah khare khara3 farkh frkh farikh farikha khawal khawl
        """,
    }
    stems = {
        SEVERE: "نياك نياكه",
        MEDIUM: """
            داعر داعره داعرات داعرين ديايث خنيثه مخنوث مخنوثه مومس مومسه مومسات
            شرموطات عاهرات عاهرين قحابات منيوجين منيوكين متناكين مخنثين خنيثين ديوثين
        """,
    }
    phrases: dict[int, list[str]] = {SEVERE: [], MEDIUM: [], LIGHT: []}
    # «حرام/شارع» بدون «ال» ممكن تكون أسماء (ابو حرام الدين، ابو شارع) — بس ويا ابن/بنت/ولد/اولاد
    loose = {"حرام", "شارع", "شوارع"}
    children = ("ابن", "بنت", "ولد", "اولاد")
    for rel in _RELATIONS:
        for t in _FAMILY_VULGAR:
            phrases[MEDIUM] += [f"{rel} ال{t}"] + ([f"{rel} {t}"] if t not in loose or rel in children else [])
        for t in _FAMILY_INSULT:
            phrases[LIGHT] += [f"{rel} ال{t}"] + ([f"{rel} {t}"] if t not in loose or rel in children else [])
    for v in _CURSE_VERBS:
        phrases[MEDIUM] += [f"{v} {o}" for o in _FAMILY_OBJECTS]
    for v in _SEXUAL_VERBS:
        phrases[SEVERE] += [f"{v} {o}" for o in _FAMILY_OBJECTS]
    for v in _KUFR_VERBS:
        # «كس/زب + الله» متلزگة تصير كلمات سليمة (كسالة، زبالة) — وكلمات الجسد لوحدها تنكشف أصلاً
        objects = _SACRED if v not in _BODY_WORDS else [o for o in _SACRED if o not in ("الله", "القران")]
        phrases[SEVERE] += [f"{v} {o}" for o in objects]
    phrases[MEDIUM] += [
        "يلعن ابو", "انعل ابو", "يلعن اللي خلفك", "يلعن اللي جابك", "يلعن ابو اللي جابك", "يا خول", "يا فرخ",
        "يا فرخه", "يا داعر", "يا داعره", "يا مومس", "يا ديوث", "يا قحبه", "يا كحبه", "يا شرموطه",
    ]
    phrases[LIGHT] += ["كل تبن", "اخرس ولك", "اخرسي ولج", "انجب ولك", "سد حلكك", "سدي حلكج"]
    # «دين امك» وأمثالها (بدون «دين ابوك/اخوك...» لأن الدَّين كلام عادي: سددت دين ابوك)
    phrases[MEDIUM] += [f"دين {o}" for o in ("امك", "اختك", "عرضك", "شرفك")]
    phrases[SEVERE] += ["دين ربك", "دين ربج"]
    # عربيزي: العائلة + أل التعريف بكل صيغها
    lat_rel = ("abn", "ibn", "ibin", "ebn", "bint", "bnt", "abo", "abu", "umm", "ukht", "ukhet", "akho",
               "walad", "wlad")
    lat_vulgar = ("dayouth", "kahba", "qahba", "kawad", "qawwad", "manyok", "mnyok", "sharmoota", "sharmouta",
                  "ars", "3ars", "zina", "haram")
    lat_insult = ("kalb", "jalb", "hayawan", "khanzeer", "wasikha", "zibala")
    for rel in lat_rel:
        for art in ("", "al ", "el ", "il ", "l "):
            phrases[MEDIUM] += [f"{rel} {art}{t}" for t in lat_vulgar]
            phrases[LIGHT] += [f"{rel} {art}{t}" for t in lat_insult]
    for v in ("yl3n", "yil3an", "yel3an", "yla3n", "yilaan", "yilan", "yalaan", "yel3n"):
        phrases[MEDIUM] += [f"{v} {o}" for o in ("abook", "abouk", "abok", "abuk", "omak", "ummak", "ummik",
                                                 "omik", "ukhtak", "ikhtak", "okhtak", "ahlak")]
        phrases[SEVERE] += [f"{v} {o}" for o in ("dinak", "rabak", "rabbak", "deenak")]
    phrases[MEDIUM] += ["khara bik", "khara 3alek", "5ara bik", "5ara 3alek", "kol khara"]
    return exact, stems, phrases


def _merge() -> None:
    exact, stems, phrases = _expanded()
    for level, words in exact.items():
        EXACT[level] = EXACT.get(level, "") + "\n" + words
    for level, words in stems.items():
        STEMS[level] = STEMS.get(level, "") + "\n" + words
    for level, items in phrases.items():
        PHRASES.setdefault(level, [])
        PHRASES[level] = PHRASES[level] + [p for p in dict.fromkeys(items)]


_merge()



# ════════════════════════════════════════════════════════════════════
# من ملف «SSSB» (أشكال التحايل): بدل آلاف السطور، جذور قوية + كلمات لوحدها
# • ROOTS: أي كلمة تبدي بالجذر تنكشف (انيجمك ، انيجابوق ، افشخبوك ، كسمخك) — جذور ما يبدي بيها كلام سليم
# • BARE: تنكشف بس إذا انكتبت لوحدها بالضبط (ازبك ≠ الازبك/ازبكستان)
# والكلمة المقطوعة بمسافة (ا نيج ، ابن ج لب ، اف شخ) يلزگها المحرك تلقائياً.
# ════════════════════════════════════════════════════════════════════
ROOTS: dict[int, str] = {
    SEVERE: """
        انيج ينيج تنيج انيك افشخ افشح يفشخ مفشوخ كسام افجخ كسمك كسمخ كصمخ كشمخ قسمخ كسمح كسخت
        منيوج منيوك متناك نياك شرموط شراميط
    """,
    MEDIUM: """
        ديوث معرص عاهر مومس خنيث
    """,
}
BARE: dict[int, str] = {
    # إهانات قوية تنحذف حتى لو انكتبت لوحدها (بس لوحدها: «الكلب نايم» سليمة)
    LIGHT: """
        كلب كلبه قذر قذره حقير حقيره سافل سافله نذل نذله منحط منحطه حثاله خسيس خسيسه
        ملعون ملعونه لعين لعينه
    """,
    SEVERE: """
        ازبك ازبكج ازبكك ازبكه ازبكها اذبك اذبكج اذبكك اذبكه ازبق ازبقك ازبقج ازبقه
        انفشخ انفشخج انفشخك انفشخه انفشخها افشخك افشخج افشخه
        كحبج كحبك كحبي قحبج قحبك فشختك فشختج
    """,
}
