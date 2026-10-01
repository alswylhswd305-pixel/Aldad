"""
الضاد vNext — أمر(كلام طبيعي).

كل سطر مثل  احسب(خمس بيضات وسعر البيضة دينارين)  يمر بـ:
تنظيف ← تقطيع ← تحديد الأمر ← محلل خاص بالأمر ← شجرة ثابتة (AST) ← كود Python سطر بسطر.
إذا الجملة لها أكثر من معنى يغيّر النتيجة: ما نخمّن، نرفع DadError فيه الخيارات.
بدون ذكاء اصطناعي في هذا المسار.
"""
import json
import ast as py_ast
import os
import re
import sys
from aldad_syntax import DadError, split_then, strip_comment, check_syntax, one_group, spans, AI_DISABLED
from aldad_runtime import evaluate, number


# ============================================================================ تنظيف وتوحيد
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
_NORM = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ـ": ""})
MAX_LITERAL_DIGITS = 4096
MAX_DECIMAL_DIGITS = 308


def nk(w: str) -> str:
    """شكل موحد للمقارنة فقط (ما يغيّر كلام المستخدم)."""
    return w.translate(_NORM)


def key(w: str) -> str:
    """مفتاح الاسم: بدون «ال» وبدون ضمير الملكية — عمري / عمرك / العمر ← عمر."""
    k = nk(w)
    if k.startswith("ال") and len(k) > 3:
        k = k[2:]
    for suf in ("كم", "نا", "ي", "ك"):          # بدون «ه» — تختلط مع التاء المربوطة (البيضة ≠ البيض)
        if k.endswith(suf) and len(k) - len(suf) >= 2:
            k = k[: -len(suf)]
            break
    return k


TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|«[^»]*»|\d+(?:[.٫]\d+)?|>=|<=|==|!=|[+\-*/×÷%()=<>]|[^\W\d_][\w]*|\S')


def tokens(text: str):
    return [t if t[:1] in "\"'«" else t.translate(AR_DIGITS)
            for t in TOKEN_RE.findall(text) if t not in ("،", ",")]


def _quoted_value(text):
    if text.startswith("«") and text.endswith("»"):
        return text[1:-1]
    try:
        return py_ast.literal_eval(text)
    except (ValueError, SyntaxError):
        raise DadError("النص المقتبس غير صحيح؛ راجع علامات التنصيص.") from None


# ============================================================================ الأرقام بالحروف
def _table(pairs):
    return {nk(k): v for k, v in pairs}


UNITS = _table([("صفر", 0), ("واحد", 1), ("واحده", 1), ("وحده", 1), ("اثنين", 2), ("اثنان", 2), ("ثنين", 2), ("اثنتين", 2),
                ("ثنتين", 2), ("ثلاث", 3), ("ثلاثه", 3), ("ثلاثة", 3), ("اربع", 4), ("اربعه", 4), ("خمس", 5), ("خمسه", 5),
                ("ست", 6), ("سته", 6), ("سبع", 7), ("سبعه", 7), ("ثمان", 8), ("ثماني", 8), ("ثمانيه", 8), ("ثمن", 8),
                ("تسع", 9), ("تسعه", 9), ("عشر", 10), ("عشره", 10)])
TEENS = _table([("حدعش", 11), ("احدعش", 11), ("احدى عشر", 11), ("ثنعش", 12), ("اثنعش", 12), ("اطنعش", 12),
                ("ثلطعش", 13), ("ثلاثطعش", 13), ("اربعطعش", 14), ("خمسطعش", 15), ("سطعش", 16), ("سبعطعش", 17),
                ("ثمنطعش", 18), ("تسعطعش", 19)])
TENS = _table([("عشرين", 20), ("عشرون", 20), ("ثلاثين", 30), ("ثلاثون", 30), ("اربعين", 40), ("اربعون", 40),
               ("خمسين", 50), ("خمسون", 50), ("ستين", 60), ("ستون", 60), ("سبعين", 70), ("سبعون", 70),
               ("ثمانين", 80), ("ثمانون", 80), ("تسعين", 90), ("تسعون", 90)])
HUNDREDS = _table([("ميه", 100), ("مية", 100), ("مئه", 100), ("مئة", 100), ("مائه", 100), ("مائة", 100), ("ميتين", 200),
                   ("مئتين", 200), ("مئتان", 200), ("ثلاثميه", 300), ("اربعميه", 400), ("خمسميه", 500),
                   ("ستميه", 600), ("سبعميه", 700), ("ثمنميه", 800), ("تسعميه", 900)])
THOUSANDS = _table([("الف", 1000), ("الفين", 2000), ("الفان", 2000), ("الاف", 1000), ("الوف", 1000),
                    ("مليون", 1000000), ("مليونين", 2000000), ("ملايين", 1000000)])
FRACTIONS = _table([("نص", 0.5), ("نصف", 0.5), ("ربع", 0.25), ("ثلث", 1 / 3)])
UNIT_WORDS = {nk(w) for w in ("دينار", "درهم", "ريال", "فلس", "متر", "كيلو", "لتر", "ساعه", "دقيقه", "يوم",
                              "حبه", "قطعه", "سنه", "شهر", "اسبوع", "كرتون", "علبه")}


def _word_value(w):
    k = nk(w)
    for t in (UNITS, TEENS, TENS, FRACTIONS):
        if k in t:
            return ("n", t[k])
    if k in HUNDREDS:
        return ("h", HUNDREDS[k])
    if k in THOUSANDS:
        return ("k", THOUSANDS[k])
    # مثنى الوحدات: دينارين / ساعتين / يومين = 2
    for suf in ("ين", "ان"):
        if k.endswith(suf):
            stem = k[: -len(suf)]
            if stem in UNIT_WORDS or (stem.endswith("ت") and stem[:-1] + "ه" in UNIT_WORDS):
                return ("n", 2)
    return None


def read_number(tk, i):
    """يقرأ رقم (أرقام أو حروف) من tk[i]؛ يرجع (القيمة، الموقع الجديد) أو None."""
    t = tk[i]
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        digits = sum(ch.isdigit() for ch in t)
        if "." in t and digits > MAX_DECIMAL_DIGITS:
            raise DadError("الرقم العشري كبير جدًا — استخدم رقمًا أصغر.")
        if "." not in t and digits > MAX_LITERAL_DIGITS:
            raise DadError(f"الرقم كبير جدًا — الحد للأرقام المكتوبة مباشرة هو {MAX_LITERAL_DIGITS} خانة.")
        try:
            v = float(t) if "." in t else int(t)
        except (ValueError, OverflowError):
            raise DadError("الرقم كبير جدًا أو غير صالح للحساب.") from None
        return v, i + 1
    total, current, j, seen = 0, 0, i, False
    while j < len(tk):
        w = tk[j]
        if seen and w == "و" and j + 1 < len(tk) and _word_value(tk[j + 1]):
            j += 1; continue
        if seen and w.startswith("و") and _word_value(w[1:]):
            w = w[1:]
        wv = _word_value(w)
        if not wv:
            break
        kind, v = wv
        if kind == "n":
            current += v
        elif kind == "h":
            current = (current or 1) * v if v == 100 else current + v
        elif kind == "k":
            total += (current or 1) * v if v in (1000, 1000000) else v
            current = 0
        seen = True; j += 1
    if not seen:
        return None
    val = total + current
    return (int(val) if float(val).is_integer() else val), j


# ============================================================================ المتغيرات
def _name_token_ok(tok: str, first: bool = False) -> bool:
    """اسم الضاد يبدأ بكلمة، ويمكن أن يحتوي أرقامًا كأجزاء لاحقة: «سعر بيع 1»."""
    if re.fullmatch(r"[^\W\d_]\w*", tok):
        return True
    return (not first) and bool(re.fullmatch(r"\d+", tok))


def _phrase_nk(name: str) -> str:
    out = []
    for i, w in enumerate(tokens(str(name))):
        if _name_token_ok(w, first=(i == 0)):
            out.append(nk(w))
    return " ".join(out)


def _phrase_key(name: str) -> str:
    out = []
    for i, w in enumerate(tokens(str(name))):
        if _name_token_ok(w, first=(i == 0)):
            out.append(w if re.fullmatch(r"\d+", w) else key(w))
    return " ".join(out)


class Names:
    """جدول أسماء الضاد.

    المستخدم يقدر يسمي القيمة بعبارة عربية طبيعية فيها مسافات مثل «سعر القطعة».
    بايثون لا يقبل المسافات في اسم المتغير، لذلك نخزن اسماً داخلياً آمناً
    (مثلاً «سعر_القطعة») ونبقي الاسم العربي كواجهة فقط.
    """
    def __init__(self):
        self.by_key = {}
        self.aliases = {}
        self.functions = set()
        self.labels = {}
        self._seq = 0

    def _safe(self, name):
        raw = " ".join(str(name).split())
        if raw.isidentifier():
            if raw in self.labels and self.labels[raw] != raw:
                raise DadError(f"الاسم «{raw}» ملتبس مع «{self.labels[raw]}»؛ اختر اسمًا مختلفًا.")
            return raw
        cand = re.sub(r"\s+", "_", raw)
        cand = re.sub(r"[^\w]", "_", cand, flags=re.UNICODE).strip("_")
        if not cand or not cand.isidentifier():
            self._seq += 1
            cand = f"_dad_v_{self._seq}"
        base = cand
        n = 2
        while cand in self.labels and self.labels[cand] != raw:
            cand = f"{base}_{n}"; n += 1
        return cand

    def add(self, name, aliases=None):
        raw = " ".join(str(name).split())
        internal = self._safe(raw)
        self.labels[internal] = raw
        self.by_key[_phrase_nk(raw)] = internal
        self.by_key[nk(internal)] = internal
        for alias in [raw] + list(aliases or []):
            a = " ".join(str(alias).split())
            if not a:
                continue
            for k in (_phrase_nk(a), _phrase_key(a)):
                self.aliases.setdefault(k, set()).add(internal)
        # الاسم الداخلي نفسه يبقى قابلاً للاستخدام في المسار الكلاسيكي.
        self.by_key[nk(internal)] = internal
        self.aliases.setdefault(key(internal), set()).add(internal)
        return internal

    def find(self, w):
        raw = " ".join(str(w).split())
        parts = tokens(raw)
        if (not raw or not parts or not _name_token_ok(parts[0], first=True)
                or any(not _name_token_ok(t, first=(i == 0)) for i, t in enumerate(parts))):
            return None
        exact = self.by_key.get(nk(raw)) or self.by_key.get(_phrase_nk(raw))
        if exact:
            return exact
        hits = self.aliases.get(_phrase_nk(raw), set()) | self.aliases.get(_phrase_key(raw), set())
        if len(hits) > 1:
            options = [self.label(v) for v in sorted(hits)]
            raise DadError(f"الاسم «{raw}» ملتبس بين أكثر من قيمة. اكتب الاسم كاملًا.", options)
        return next(iter(hits), None)

    def label(self, internal):
        return self.labels.get(internal, internal)

    def match_tokens(self, tk, i):
        """أطول اسم معروف يبدأ عند tk[i]؛ يرجع (الاسم الداخلي، عدد الكلمات)."""
        # الاسم المركب يتكون من كلمات أسماء فقط. لا نعبر نصاً مقتبساً أو رقماً
        # أو علامة حساب؛ وإلا ««الباقي معك» الباقي» قد يبتلع النص المقتبس.
        stop = i
        while stop < len(tk):
            tok = tk[stop]
            if not _name_token_ok(tok, first=(stop == i)):
                break
            if nk(tok) in OP_WORDS:
                break
            stop += 1
        for j in range(stop, i, -1):
            cand = " ".join(tk[i:j])
            v = self.find(cand)
            if v:
                return v, j - i
        return None


# ============================================================================ تعبير حسابي
OP_WORDS = {nk(w): s for w, s in [("زائد", "+"), ("زايد", "+"), ("وزائد", "+"), ("زيد", "+"), ("اطرح", "-"), ("منه", "-"),
            ("اضرب", "*"), ("اقسم", "/"), ("تكعيب", "**3"), ("ناقص", "-"), ("الا", "-"),
            ("ضرب", "*"), ("ضربه", "*"), ("مضروب", "*"), ("مضروبه", "*"), ("قسمه", "/"), ("مقسوم", "/"),
            ("اس", "**"), ("تربيع", "**2")]}
SYM_OPS = {"+": "+", "-": "-", "*": "*", "×": "*", "/": "/", "÷": "/", "(": "(", ")": ")", "%": "%"}
FILLER = {nk(w) for w in ("احسب", "احسبلي", "كم", "يساوي", "يطلع", "الناتج", "ناتج", "النتيجة", "النتيجه", "لي",
                          "على", "في", "=", "؟", "?", "!", ".", "بالله", "لو", "سمحت")}


def items_of(text, names: Names):
    """يحول الكلام لقائمة عناصر: ('num',v) ('var',name) ('op',s) ('word',w)."""
    tk = tokens(text)
    out, i = [], 0
    while i < len(tk):
        t = tk[i]
        if len(t) > 2 and t[0] in "بو" and not read_number(tk, i) and read_number([t[1:]] + tk[i + 1:], 0):
            out.append(("word", t[0]))                          # بخمسة ← ب + خمسة ، وخمسة ← و + خمسة
            tk = tk[:i] + [t[1:]] + tk[i + 1:]
            continue
        if nk(t) == "جذر" and i + 1 < len(tk):                  # جذر 16 / جذر س / جذر سعر القطعة
            r = read_number(tk, i + 1)
            if r:
                out.append(("raw", f"({_fmt(r[0])}) ** 0.5")); i = r[1]; continue
            mm = names.match_tokens(tk, i + 1)
            if mm:
                vv, used = mm
                out.append(("raw", f"({vv}) ** 0.5")); i += 1 + used; continue
        r = read_number(tk, i)
        if r:
            out.append(("num", r[0]))
            frac = nk(t) in FRACTIONS and r[1] == i + 1
            i = r[1]
            if frac and i < len(tk) and nk(tk[i]) in ("من",):     # ثلث من 90
                i += 1
            if frac and i < len(tk) and (read_number(tk, i) or names.find(tk[i])):
                out.append(("op", "*"))                          # ثلث 90 / نص الراتب
            continue
        if t in SYM_OPS:
            out.append(("op", SYM_OPS[t])); i += 1; continue
        k = nk(t)
        if out and out[-1][0] == "num" and (k in UNIT_WORDS or k.rstrip("ات") in UNIT_WORDS or k in {"دنانير", "دراهم", "ريالات", "امتار", "كيلوات", "ساعات", "ايام", "حبات", "قطع"}):
            i += 1; continue                                    # نص دينار / 3 ساعات ← الوحدة ما تغيّر الحساب
        if k in OP_WORDS:
            out.append(("op", OP_WORDS[k])); i += 1; continue
        if k in ("في", "علي") and out and out[-1][0] in ("num", "var") and i + 1 < len(tk):
            nxt_num = read_number(tk, i + 1)
            nxt_var = names.match_tokens(tk, i + 1)
            if nxt_num or nxt_var:
                out.append(("op", "*" if k == "في" else "/")); i += 1; continue
        if t.startswith("و") and len(t) > 1 and (nk(t[1:]) in OP_WORDS):
            out.append(("op", OP_WORDS[nk(t[1:])])); i += 1; continue
        mm = names.match_tokens(tk, i)
        if mm:
            v, used = mm
            out.append(("var", v)); i += used; continue
        if t[:1] in "\"'«":
            out.append(("text", _quoted_value(t))); i += 1; continue
        out.append(("word", t)); i += 1
    return out


def _fmt(v):
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def math_expr(items):
    """يرجع (تعبير Python، وصف عربي) إذا كانت العناصر حساب صافي، وإلا None."""
    core = [x for x in items if not (x[0] == "word" and nk(x[1]) in FILLER)]
    if not core or any(x[0] in ("word", "text") for x in core):
        return None
    parts, show = [], []
    for kind, v in core:
        if kind == "raw":
            parts.append(v); show.append(v); continue
        if kind == "num":
            parts.append(_fmt(v)); show.append(_fmt(v))
        elif kind == "var":
            parts.append(v); show.append(v)
        else:
            if v == "%":
                parts.append("/100"); show.append("%")
            else:
                parts.append(v); show.append({"*": "×", "/": "÷"}.get(v, v))
    # رقمين ورا بعض بدون عملية = غامض
    for a, b in zip(core, core[1:]):
        if a[0] in ("num", "var", "raw") and b[0] in ("num", "var", "raw"):
            return None
    expr = " ".join(parts)
    try:
        compile(expr, "<احسب>", "eval")
    except SyntaxError:
        return None
    return expr, " ".join(show)


def literal_fi_math(text, names: Names):
    """
    يحسم تضارب كلمة «في» بدون كسر معناها العربي:
    - بين أرقام صريحة فقط: ضرب (3 في 4 = 12).
    - مع أسماء/قوائم/أوامر: تظل «في» بمعنى داخل/إلى، والمسار الكلاسيكي يتكفل بها.

    هذا المسار مقصود للعبارات الحسابية الحرة والإسناد مثل:
        3 في 4
        س = خمسة في ثلاثة
    ولا يمس: لكل عنصر في السلة / اسأل ... في العدد / احفظ ... في ملف.
    """
    tk = tokens(text)
    if not tk or not any(nk(t) == "في" for t in tk):
        return None
    # لازم تبدأ برقم صريح؛ بهذا ما نخطف معنى «في» من الجمل العادية أو اختبار العضوية.
    first = read_number(tk, 0)
    if not first:
        return None
    its = items_of(text, names)
    # خارج «احسب» نكون محافظين: الضرب بـ«في» هنا للأرقام الصريحة فقط.
    if any(k == "var" for k, _ in its):
        return None
    if sum(1 for k, _ in its if k == "num") < 2:
        return None
    me = math_expr(its)
    if not me or not any(k == "op" and v == "*" for k, v in its):
        return None
    return me[0]


# ============================================================================ المحللات المتخصصة (ترجع AST)
LIST_FUNCS = {nk(k): f for k, f in [("مجموع", "sum"), ("المجموع", "sum"), ("اجمالي", "sum"), ("أكبر", "max"), ("اكبر", "max"),
              ("اعلى", "max"), ("أعلى", "max"), ("أصغر", "min"), ("اصغر", "min"), ("اقل", "min"), ("أقل", "min"),
              ("ادنى", "min"), ("متوسط", "_dad_mean"), ("معدل", "_dad_mean"), ("عدد", "_dad_count"), ("طول", "_dad_count")]}


def list_query(text, names):
    """«مجموع السلة» / «أكبر الأسعار» ← تعبير، أو None."""
    tk = [t for t in tokens(text) if nk(t) not in ("كم", "ما", "وش", "هو", "هي", "في")]
    if len(tk) >= 2 and nk(tk[0]) in LIST_FUNCS:
        v = names.find(" ".join(tk[1:]))
        if v:
            return f"{LIST_FUNCS[nk(tk[0])]}({v})"
    return None



# ---------------------------------------------------------------- قصص حسابية + تحويل وحدات
_PLUS = {nk(w) for w in ("زاد", "زادت", "زادو", "جاني", "جاتني", "جانا", "ربحت", "كسبت", "حصلت", "اخذت", "استلمت", "انضاف",
                         "اضفت", "ضفت", "زودت", "اشتريت", "جبت", "دخل", "نزل", "اضاف", "وصلني")}
_MINUS = {nk(w) for w in ("صرفت", "دفعت", "خسرت", "عطيت", "اعطيت", "بعت", "نقص", "نقصت", "اكلت", "شلت", "راح", "راحت",
                          "سحبت", "ضاع", "ضاعت", "انكسر", "انكسرت", "طلع", "طلعت", "استهلكت", "سددت", "رجعت", "تبرعت")}
_START = {nk(w) for w in ("عندي", "معي", "كان", "كانت", "عندنا", "معنا", "بالحساب", "رصيدي", "فيه", "في")}
_DIVV = {nk(w) for w in ("وزعت", "قسمت", "قسمتها", "وزعتها", "تقسم", "توزع")}


def parse_story(text, names):
    """«عندي 10 دنانير وصرفت 3 وجاني 5» ← 10 - 3 + 5."""
    tk = tokens(text)
    i, expr, seen_verb, first = 0, [], False, None
    sign = None
    while i < len(tk):
        t = tk[i]; k = nk(t[1:]) if t.startswith("و") and len(t) > 2 and nk(t[1:]) in (_PLUS | _MINUS | _DIVV) else nk(t)
        if k in _PLUS: sign = "+"; seen_verb = True; i += 1; continue
        if k in _MINUS: sign = "-"; seen_verb = True; i += 1; continue
        if k in _DIVV: sign = "/"; seen_verb = True; i += 1; continue
        r = read_number(tk, i) if not (t in ("ب",)) else None
        if r:
            val = _fmt(r[0])
            if first is None:
                first = val; expr.append(val)
            elif sign:
                expr.append(f"{sign} {val}"); sign = None
            else:
                return None                                  # رقم بدون فعل بينهم = مو قصة
            i = r[1]; continue
        mm = names.match_tokens(tk, i)
        if mm:
            vv, used = mm
            if first is None:
                first = vv; expr.append(vv); i += used; continue
            if sign:
                expr.append(f"{sign} {vv}"); sign = None; i += used; continue
            # Two values without a story verb belong to ordinary arithmetic.
            # Do not scan inside a full name and accidentally resolve its alias.
            return None
        i += 1
    if sign is not None:
        raise DadError("العملية ناقصة في القصة: اكتب قيمة بعد آخر فعل حسابي.")
    if not seen_verb or first is None or len(expr) < 2:
        return None
    return " ".join(expr)


UNITS_CONV = {}
for _grp in [[("طن", 1000000), ("كيلو", 1000), ("كيلوجرام", 1000), ("كغ", 1000), ("جرام", 1), ("غرام", 1), ("جم", 1)],
             [("كيلومتر", 100000), ("متر", 100), ("سنتي", 1), ("سانتي", 1), ("سنتيمتر", 1), ("سم", 1), ("مليمتر", 0.1), ("ملي", 0.1)],
             [("سنه", 31536000), ("اسبوع", 604800), ("يوم", 86400), ("ساعه", 3600), ("دقيقه", 60), ("ثانيه", 1)],
             [("لتر", 1000), ("مل", 1), ("مليلتر", 1)],
             [("دينار", 1000), ("فلس", 1)]]:
    for _n, _f in _grp:
        UNITS_CONV[nk(_n)] = (id(_grp), _f)
_PLURALS = {nk(k): nk(v) for k, v in [("كيلوات", "كيلو"), ("جرامات", "جرام"), ("غرامات", "غرام"), ("امتار", "متر"), ("سنتيات", "سنتي"),
            ("ساعات", "ساعه"), ("دقايق", "دقيقه"), ("دقائق", "دقيقه"), ("ثواني", "ثانيه"), ("ايام", "يوم"), ("اسابيع", "اسبوع"),
            ("سنين", "سنه"), ("سنوات", "سنه"), ("لترات", "لتر"), ("دنانير", "دينار"), ("فلوس", "فلس"), ("اطنان", "طن")]}


def _unit(w):
    k = nk(w)
    for pre in ("بال", "بـ", "ب", "لل", "ال", "ل"):
        if k.startswith(pre) and (k[len(pre):] in UNITS_CONV or k[len(pre):] in _PLURALS):
            k = k[len(pre):]; break
    k = _PLURALS.get(k, k)
    return k if k in UNITS_CONV else None


def parse_convert(text, names=None):
    """«3 كيلو بالجرام» / «كم دقيقة في ساعتين» ← تحويل."""
    tk = tokens(text)
    num, u_from, u_to = None, None, None
    i = 0
    while i < len(tk):
        t = tk[i]
        r = read_number(tk, i)
        vv = names.find(t) if (names is not None and not r and num is None and i + 1 < len(tk) and _unit(tk[i + 1])) else None
        if vv:                                                  # الباقي دينار بالفلوس
            num = vv; u_from = _unit(tk[i + 1]); i += 2; continue
        if r and num is None:
            num = r[0]; i = r[1]
            dual = None
            if r[1] == tk.index(t) + 1 and nk(t).endswith(("ين", "ان")) and not re.fullmatch(r"\d+", t):
                stem = t[:-2]
                dual = _unit(stem) or (_unit(stem[:-1] + "ه") if stem.endswith("ت") else None)   # ساعتين / يومين
            if dual and u_from is None:
                u_from = dual
            elif i < len(tk) and _unit(tk[i]) and u_from is None:
                u_from = _unit(tk[i]); i += 1
            continue
        u = _unit(t)
        if u:
            if u_from is None and num is None:
                u_to = u_to or u                               # كم دقيقة في ...
            elif u_from is None:
                u_from = u
            else:
                u_to = u
        elif nk(t).endswith(("تين", "ين")) and _unit(t[:-3] + "ه" if t.endswith("تين") else t[:-2]):
            num = 2 if num is None else num; u_from = _unit(t[:-3] + "ه" if t.endswith("تين") else t[:-2])
        i += 1
    if num is None or not u_from or not u_to or u_from == u_to:
        return None
    (g1, f1), (g2, f2) = UNITS_CONV[u_from], UNITS_CONV[u_to]
    if g1 != g2:
        raise DadError(f"ما ينفع أحول «{u_from}» إلى «{u_to}» — نوعين مختلفين.")
    base = num if isinstance(num, str) else _fmt(num)
    return f"{base} * {f1} / {f2}"

def parse_calc(text, names: Names):
    if re.match(r"^كم(?:\s|$)", text.strip()):
        ask = parse_ask(text, names)
        return {"op": "SEQ", "body": [ask, {"op": "CALC", "expr": ask["var"], "say": text.strip()}]}
    tk = tokens(text)
    # لا نتسامح مع رموز زائدة تغيّر المعنى بصمت. النقطة مسموحة فقط كعلامة نهاية جملة.
    if "." in tk[:-1]:
        raise DadError("في الحساب نقطة بمكان غير صحيح — احذفها أو ضعها في نهاية الجملة.")
    if len(tk) >= 2 and tk[0] in ("+", "-") and tk[1] in ("+", "-"):
        raise DadError(f"فيه علامتان متتاليتان «{tk[0]}{tk[1]}» — اكتب علامة واحدة فقط.")
    if tk and (nk(tk[-1]) in OP_WORDS or tk[-1] in ("+", "-", "*", "/", "×", "÷")):
        op = OP_WORDS.get(nk(tk[-1]), tk[-1])
        if op not in ("**2", "**3"):
            raise DadError(f"ما فهمت الحساب — العملية ناقصة: اكتب رقمًا أو قيمة بعد «{tk[-1]}».")
    for a, b in zip(tk, tk[1:]):
        oa, ob = OP_WORDS.get(nk(a), SYM_OPS.get(a)), OP_WORDS.get(nk(b), SYM_OPS.get(b))
        if oa in ("+", "-", "*", "/", "**") and ob in ("*", "/", "**"):
            raise DadError(f"فيه عمليتين متتاليتين «{a} {b}»؛ اكتب قيمة بينهما.")
    lq = list_query(text, names)
    if lq:
        return {"op": "CALC", "expr": lq, "say": text.strip()}
    cv = parse_convert(text, names)
    if cv:
        return {"op": "CALC", "expr": cv, "say": text.strip()}
    st = parse_story(text, names)
    if st:
        return {"op": "CALC", "expr": st, "say": st}
    calc_tokens = tokens(text)
    has_arith = any((nk(t) in OP_WORDS) or (t in SYM_OPS and t not in ("(", ")")) for t in calc_tokens)
    m = None if has_arith else re.match(r"^(?:كم\s+)?(?:عدد|طول)\s+(.+?)\s*[؟?]?$", text.strip())
    if m:
        thing = m.group(1).strip(); v = names.find(thing)
        if not v:
            head, _phrase = _count_subject(thing)
            v = names.find(head)
        if not v:
            ask = _ask_for(thing, names)
            return {"op": "SEQ", "body": [ask, {"op": "CALC", "expr": f"_dad_count({ask['var']})", "say": f"عدد {ask['var']}"}]}
        return {"op": "CALC", "expr": f"_dad_count({v})", "say": f"عدد {v}"}
    items = items_of(text, names)
    nums = [x for x in items if x[0] in ("num", "var")]
    words = {nk(x[1]) for x in items if x[0] == "word"}
    ops = [x for x in items if x[0] == "op"]
    raw = nk(text)
    # 1) نسبة: 10% من 200 / خصم 10% على 200
    m = re.search(r"(خصم)?\s*([\d.]+|[^\s]+)\s*(?:%|بالميه|بالمئه|في المئه|في الميه)\s*(?:من|علي)\s*(.+)$", raw.translate(AR_DIGITS))
    if m:
        a = read_number(tokens(m.group(2)), 0); b = items_of(m.group(3), names)
        bexp = math_expr(b)
        if a and bexp:
            if m.group(1):
                return {"op": "CALC", "expr": f"({bexp[0]}) - ({bexp[0]}) * {_fmt(a[0])} / 100", "say": f"{bexp[1]} ناقص {_fmt(a[0])}%"}
            return {"op": "CALC", "expr": f"({bexp[0]}) * {_fmt(a[0])} / 100", "say": f"{_fmt(a[0])}% من {bexp[1]}"}
    # 2) عدد × سعر الواحد
    price_words = {nk(w) for w in ("سعر", "بسعر", "وسعر", "ثمن", "وثمن", "قيمه", "الحبه", "للحبه", "الواحد", "الواحده",
                                   "للواحد", "للواحده", "كل", "حق")}
    if len(nums) == 2 and not ops and (words & price_words or any(w.startswith(("سعر", "وسعر", "بسعر")) for w in words)):
        a, b = nums
        va = _fmt(a[1]) if a[0] == "num" else a[1]
        vb = _fmt(b[1]) if b[0] == "num" else b[1]
        return {"op": "CALC", "expr": f"{va} * {vb}", "say": f"{va} × {vb}"}
    # 3) مجموع صريح
    if words & {nk(w) for w in ("اجمع", "مجموع", "المجموع", "جمع", "اجمالي", "الاجمالي")} and len(nums) >= 2 and not ops:
        vals = [_fmt(x[1]) if x[0] == "num" else x[1] for x in nums]
        return {"op": "CALC", "expr": " + ".join(vals), "say": " + ".join(vals)}
    # 4) «اثنين بخمسة» — غامض، ما نخمن
    tk = tokens(text)
    for i, t in enumerate(tk):
        if (t == "ب" or (t.startswith("ب") and (_word_value(t[1:]) or t[1:].isdigit()))) and len(nums) == 2 and not ops:
            a, b = (_fmt(x[1]) if x[0] == "num" else x[1] for x in nums)
            raise DadError(f"ما فهمت «{text.strip()}» — «ب» ممكن تكون أكثر من عملية.",
                           [f"احسب({a} زائد {b})  = {a} + {b}", f"احسب({a} ضرب {b})  = {a} × {b}",
                            f"احسب({a} حبات وسعر الحبة {b})"])
    # 5) رقمين بينهم «و» فقط = جمع (معنى واحد واضح)
    if len(nums) == 2 and not ops and any(x[0] == "word" and x[1] == "و" for x in items) and all(x[0] != "word" or nk(x[1]) in FILLER | {"و"} for x in items):
        vals = [_fmt(x[1]) if x[0] == "num" else x[1] for x in nums]
        return {"op": "CALC", "expr": " + ".join(vals), "say": " + ".join(vals)}
    # 6) حساب صافي: 5 زائد 3 / (2 + 3) × 4 / العمر ناقص 5
    me = math_expr(items)
    if me:
        return {"op": "CALC", "expr": me[0], "say": me[1]}
    unknown = [x[1] for x in items if x[0] == "word" and nk(x[1]) not in FILLER]
    if not text.strip():
        raise DadError("«احسب» فاضية — ما فيها شي أحسبه. شيلها، أو اكتب وش تحسب:",
                       ["احسب(العدد ضرب 2)", "احسب(خمس بيضات وسعر البيضة دينارين)"])
    if not nums and not ops and not unknown:                 # «احسب الناتج» — ما في شي ينحسب
        known = [n for k, n in names.by_key.items() if k == nk(n) and n != "الناتج"]
        v = known[-1] if known else "العدد"
        raise DadError(f"«احسب» تحتاج شي تحسبه — وش تبي تسوي بـ «{v}»؟",
                       [f"احسب({v} ضرب 2)", f"احسب({v} زائد 10)", f"احسب(10% من {v})"])
    hint = f" ما أعرف: «{'، '.join(unknown[:3])}»." if unknown else ""
    vals = [_fmt(x[1]) if x[0] == "num" else x[1] for x in nums]
    if len(vals) >= 2:
        a, b = vals[0], vals[1]
        opts = [f"احسب({a} زائد {b})", f"احسب({a} ناقص {b})", f"احسب({a} ضرب {b})", f"احسب({a} قسمة {b})"]
    elif len(vals) == 1:
        opts = [f"احسب({vals[0]} زائد 1)", f"احسب(جذر {vals[0]})", f"احسب(10% من {vals[0]})"]
    else:
        opts = ["احسب(5 زائد 3)", "احسب(خمس بيضات وسعر البيضة دينارين)", "احسب(10% من 200)"]
    raise DadError(f"ما فهمت الحساب في «{text.strip()}» — راجع القيم وعلامة العملية.{hint}", opts)


def _ask_for(thing, names):
    head, phrase = _count_subject(thing)
    name = head if nk(head).startswith("ال") else "ال" + head
    names.add(name)
    shown = phrase or name
    prompt = shown if re.match(r"^(?:كم\s+)?(?:عدد|طول)\b", shown) else f"كم عدد {shown}"
    if not re.search(r"[؟?]\s*$", prompt):
        prompt += "؟"
    return {"op": "INPUT", "var": name, "prompt": prompt, "numeric": True}


_IDENT_RE = re.compile(r"^[^\W\d]\w*$")
_COUNT_PREP = {nk(w) for w in (
    "في", "من", "على", "عن", "إلى", "الى", "عند", "لدى",
    "داخل", "وسط", "جنب", "فوق", "تحت", "بين", "مع",
)}


def _count_subject(thing: str):
    """موضوع «كم عدد/طول ...» كاسم متغير صالح + عبارة السؤال.

    «البيض» تبقى اسماً واحداً. «البيض في السلة» / «بيض في سلة»: المعدود أول كلمة،
    والباقي وصف مكان في نص السؤال — مو جزء من اسم المتغير.
    توليد اسم فيه مسافات كان يطلع بايثون ينهار ورسالة أقواس مضللة.
    كلام زيادة بدون حرف جر → خطأ عربي، بدون تخمين.
    """
    t = " ".join((thing or "").split())
    if not t:
        raise DadError("بعد «عدد» لازم اسم المعدود، مثل: كم عدد البيض")
    if _IDENT_RE.match(t):
        return t, t
    tk = [w for w in tokens(t) if w not in ("؟", "?")]
    head = tk[0] if tk else ""
    if not _IDENT_RE.match(head) or nk(head) in _COUNT_PREP:
        raise DadError(f"ما فهمت المعدود في «{t}». استخدم كلمة واحدة، مثل: كم عدد البيض")
    rest = tk[1:]
    if not rest:
        return head, t
    if nk(rest[0]) in _COUNT_PREP:
        return head, t
    raise DadError(
        f"ما فهمت «{t}» بعد «عدد» — الجزء «{' '.join(rest)}» مو اسم واحد ولا وصف مكان (في/من/على).",
        [f"كم عدد {head}"],
    )


def _unknown_count(thing):
    name = thing if nk(thing).startswith("ال") else "ال" + thing
    return DadError(f"ما أعرف كم «{thing}» عندك — لازم تقول لي أول.",
                    [f"{name} = 12", f"اسأل(كم عدد {name})", f"{name} = [\"بيضة\"، \"بيضة\"]"])


def parse_output(text, names: Names):
    t = text.strip()
    if not t:
        return {"op": "OUTPUT", "expr": '""'}
    if len(tokens(t)) == 1 and t[:1] in "\"'«":
        return {"op": "OUTPUT", "expr": json.dumps(_quoted_value(t), ensure_ascii=False)}
    if re.fullmatch(r'[-+]?\d+(?:[.٫]\d+)?', t):
        return {"op": "OUTPUT", "expr": t.translate(AR_DIGITS)}
    if re.match(r"^كم(?:\s|$)", t):
        ask = parse_ask(t, names)
        return {"op": "SEQ", "body": [ask, {"op": "OUTPUT", "expr": ask["var"]}]}
    full = names.find(t.rstrip("؟?"))
    if full:                                                # «عدد مرات التكرار» اسم كامل ← قيمته، مو طلب عدّ
        return {"op": "OUTPUT", "expr": full}
    m = re.match(r"^(?:كم\s+)?(?:عدد|طول)\s+(.+?)\s*[؟?]?$", t)
    if m:
        thing = m.group(1).strip()
        v = names.find(thing)
        if not v:
            head, _phrase = _count_subject(thing)
            v = names.find(head)
        if not v:
            raise _unknown_count(thing)
        return {"op": "OUTPUT", "expr": f"_dad_count({v})"}
    v = names.find(t.rstrip("؟?"))
    if v:
        return {"op": "OUTPUT", "expr": v}
    tq = nk(t.rstrip("؟? "))
    if tq in (nk("الناتج"), nk("المحتوى")):                   # قل(الناتج) قبل أي احسب
        raise DadError(f"ما في «{t}» لين الحين — {'احسب شي قبله' if tq == nk('الناتج') else 'افتح ملف قبله'}.",
                       ["احسب(5 زائد 3) ثم قل(الناتج)"] if tq == nk("الناتج") else ["افتح(ملف.txt) ثم قل(المحتوى)"])
    if re.fullmatch(r"(?:كم\s+)?(?:الساعه|الساعة|الوقت)", t.rstrip("؟? ")):
        return {"op": "OUTPUT", "expr": "_dad_now('time')"}
    if re.fullmatch(r"(?:وش\s+|ما\s+|شنو\s+)?(?:التاريخ|اليوم|تاريخ\s+اليوم)", t.rstrip("؟? ")):
        return {"op": "OUTPUT", "expr": "_dad_now('date')"}
    lq = list_query(t, names)
    if lq:
        return {"op": "OUTPUT", "expr": lq}
    if _has_cmp([nk(x) for x in tokens(t)]):                   # قل(5 أكبر من 3) ← صح
        try:
            return {"op": "OUTPUT", "expr": f"_dad_bool({parse_cond(t, names)['cond']})"}
        except DadError:
            pass
    items = items_of(t, names)
    if any(x[0] == "op" for x in items) or (any(x[0] == "var" for x in items) and not any(x[0] in ("word", "text") for x in items)):
        me = math_expr(items)
        if me:
            return {"op": "OUTPUT", "expr": _evaluate_call(me[0])}
    unknown_w = [x[1] for x in items if x[0] == "word" and nk(x[1]) not in FILLER]
    if any(x[0] == "op" for x in items) and unknown_w and any(x[0] in ("num", "var") for x in items):
        return {"op": "OUTPUT", "expr": json.dumps(t, ensure_ascii=False),
                "note": f"ما عرفت «{unknown_w[0]}» — طبعت السطر ككلام. إذا تقصد حساب، عرّفه أول."}
    # كلام + متغيرات: «هلا الاسم» ← هلا + قيمة الاسم
    has_text = any(x[0] == "text" for x in items)
    if any(x[0] == "var" for x in items) and (len(items) <= 6 or has_text):
        parts, j = [], 0
        while j < len(items):
            kind, val = items[j]
            if kind == "word" and nk(val) in LIST_FUNCS and j + 1 < len(items) and items[j + 1][0] == "var":
                parts.append(f"{LIST_FUNCS[nk(val)]}({items[j + 1][1]})"); j += 2; continue
            if kind == "var": parts.append(val)
            elif kind == "num": parts.append(_fmt(val))
            else: parts.append(json.dumps(val, ensure_ascii=False))
            j += 1
        return {"op": "OUTPUT", "expr": ", ".join(parts)}
    one = t.rstrip("؟?.! ")
    if re.fullmatch(r"ال[^\W\d_]\w*", one):                    # كلمة وحدة تبدأ بـ «ال» وما انعرفت: نطبعها وننبه
        return {"op": "OUTPUT", "expr": json.dumps(t, ensure_ascii=False),
                "note": f"«{one}» مو متغير معروف — طبعتها ككلام. إذا تقصد متغير، عرّفه أول."}
    return {"op": "OUTPUT", "expr": json.dumps(t, ensure_ascii=False)}


QUESTION_WORDS = {nk(w) for w in ("كم", "وش", "شو", "شنو", "ايش", "ما", "ماهو", "ماهي", "هل", "متى", "وين", "اين",
                                  "كيف", "شلون", "منو", "من", "اش", "شنهو")}


def _implicit_value_name(q: str):
    """يستخرج اسم القيمة من سؤال طبيعي بدون ذكاء اصطناعي.

    القاعدة ثابتة:
    - نشيل كلمة السؤال الأولى مثل «كم».
    - نأخذ العبارة إلى أول حرف جر سياقي (في/من/على...).
    - العبارة كلها اسم واحد، حتى لو فيها أكثر من كلمة: «سعر القطعة»، «عدد البيض».
    """
    words = [w for w in tokens(q) if re.match(r"[^\W\d_]", w)]
    if words and nk(words[0]) in QUESTION_WORDS:
        words = words[1:]
    if not words:
        return None, []
    subject = words
    if not subject:
        return None, []
    raw_phrase = " ".join(subject)

    # كلمة واحدة تبقى متوافقة مع الضاد القديمة: «عمرك» -> «العمر»، «اسمك» -> «الاسم».
    if len(subject) == 1:
        w = subject[0]
        phrase = w if nk(w).startswith("ال") else "ال" + key(w)
        aliases = [raw_phrase] if nk(raw_phrase) != nk(phrase) else []
        return phrase, aliases

    phrase = raw_phrase
    aliases = []

    # الاسم الكامل يبقى هو المرجع الحقيقي حتى نفرّق بين:
    # «عدد البيض في السلة» و«عدد البيض في الثلاجة».
    # لكن نضيف الجزء قبل حرف الجر كاسم مختصر طبيعي إذا كان وحيدًا وغير ملتبس.
    context_preps = {nk(w) for w in ("في", "من", "على", "عن", "إلى", "الى", "عند", "لدى", "داخل", "وسط", "جنب", "فوق", "تحت", "بين", "مع")}
    for i, w in enumerate(subject):
        if i >= 1 and nk(w) in context_preps:
            base = " ".join(subject[:i]).strip()
            if base and nk(base) != nk(phrase):
                aliases.append(base)
            break

    # توافق خلفي: الصيغ القديمة كانت تحفظ أول مفهوم فقط (السعر، البيض...).
    descriptors = {nk(w) for w in ("عدد", "كميه", "كمية", "مقدار", "قيمه", "قيمة", "حجم", "وزن")}
    alias_word = subject[1] if len(subject) > 1 and nk(subject[0]) in descriptors else subject[0]
    alias = alias_word if nk(alias_word).startswith("ال") else "ال" + key(alias_word)
    if nk(alias) != nk(phrase) and all(nk(alias) != nk(a) for a in aliases):
        aliases.append(alias)
    return phrase, aliases


def parse_ask(text, names: Names):
    t = text.strip()
    if not t:
        raise DadError("«اسأل» تحتاج السؤال؛ مثل: اسأل كم العدد.")
    m = re.match(r"^(.+?)\s+واحفظ\s+في\s+(.+?)\s*$", t)
    if not m:
        old = re.match(r"^(.+?)\s+في\s+([^\W\d]\w*)\s*$", t)
        if old:
            words = [w for w in tokens(old.group(1)) if nk(w) not in QUESTION_WORDS]
            # Compatibility: a repeated subject is an explicit destination.
            # A place such as «السلة» stays part of the question and its name.
            if (words and key(words[0]) == key(old.group(2))) or old.group(1)[:1] in "\"'«":
                m = old
    if m:
        q, explicit_var = m.group(1).strip(), m.group(2)
    else:
        q, explicit_var = t, None
    q = q.strip()
    if len(tokens(q)) == 1 and q[:1] in "\"'«":
        q = _quoted_value(q)
    tk = [w for w in tokens(q) if re.match(r"[^\W\d_]", w)]
    if explicit_var is None:
        phrase, aliases = _implicit_value_name(q)
        if not phrase:
            raise DadError(f"ما عرفت وين أحفظ جواب «{q}». اكتب: اسأل({q} في الاسم)")
        _check_user_name(phrase)
        var = names.add(phrase, aliases=aliases)
    else:
        _check_user_name(explicit_var)
        var = names.add(explicit_var)
    numeric = bool(tk) and nk(tk[0]) == "كم"
    prompt = q if re.search(r"[؟?]\s*$", q) else q + "؟"
    node = {"op": "INPUT", "var": var, "prompt": prompt, "numeric": numeric}
    return node


COMPARATORS = [  # (كلمات موحدة، رمز) — الأطول أول
    (("اكبر", "من", "او", "يساوي"), ">="), (("اكثر", "من", "او", "يساوي"), ">="),
    (("اصغر", "من", "او", "يساوي"), "<="), (("اقل", "من", "او", "يساوي"), "<="),
    (("لا", "يساوي"), "!="), (("مو", "يساوي"), "!="), (("ما", "يساوي"), "!="), (("ليس",), "!="), (("مو",), "!="),
    (("اكبر", "من"), ">"), (("اكثر", "من"), ">"), (("فوق",), ">"),
    (("اصغر", "من"), "<"), (("اقل", "من"), "<"), (("تحت",), "<"),
    (("يساوي",), "=="), (("هو",), "=="), (("هي",), "=="),
    ((">=",), ">="), (("<=",), "<="), (("!=",), "!="), (("==",), "=="), (("=",), "=="), ((">",), ">"), (("<",), "<"),
]


def _operand(tk, names, side):
    text = " ".join(tk)
    if not tk:
        raise DadError("الشرط ناقص.")
    items = items_of(text, names)
    me = math_expr(items)
    if me:
        return me[0]
    if len(items) == 1 and items[0][0] == "text":
        return json.dumps(items[0][1], ensure_ascii=False)
    if side == "right":
        return json.dumps(text, ensure_ascii=False)   # إذا(الاسم يساوي سعود) ← نص
    raise DadError(f"ما أعرف شنو «{text}» في الشرط. عرّفه أول أو اسأل عنه بـ اسأل(...).")


def _logical_token_is_inside_comparator(norm, pos):
    """لا نفصل «أو/و» إذا كانت جزءًا من مقارنة مركبة مثل «أكبر من أو يساوي»."""
    for start in range(max(0, pos - 4), pos + 1):
        hit = _find_cmp(norm, start)
        if hit:
            length, _ = hit
            if start <= pos < start + length:
                return True
    return False


def parse_cond(text, names: Names):
    """Boolean groups have ordinary precedence: grouping, comparison, و, أو.

    المقارنات لا تُحسم من شكل الكلمات وحده. قد تكون كلمات مثل «لا يساوي»
    جزءًا من اسم متغير مركب؛ لذلك لا نعتمد عامل المقارنة إلا إذا كان ما قبله
    قيمة/اسمًا صالحًا فعلًا.
    """
    def condition(tk):
        if not tk:
            raise DadError("الشرط ناقص.")
        while tk[0] == "(" and tk[-1] == ")" and one_group(" ".join(tk)):
            tk = tk[1:-1]
            if not tk:
                raise DadError("الشرط ناقص داخل الأقواس.")
        norm = [nk(t) for t in tk]

        for join, symbol in (("او", "or"), ("و", "and")):
            depth = 0
            for i, token in enumerate(tk):
                if token == "(":
                    depth += 1
                elif token == ")":
                    depth -= 1
                elif (depth == 0 and norm[i] == join
                      and not _logical_token_is_inside_comparator(norm, i)
                      and _has_cmp(norm[:i]) and _has_cmp(norm[i + 1:])):
                    try:
                        left_cond = condition(tk[:i])
                        right_cond = condition(tk[i + 1:])
                    except DadError:
                        continue
                    return f"({left_cond} {symbol} {right_cond})"

        candidates = []
        first_error = None
        depth = 0
        for i, token in enumerate(tk):
            if token == "(":
                depth += 1
                continue
            if token == ")":
                depth -= 1
                continue
            if depth != 0:
                continue
            hit = _find_cmp(norm, i)
            if not hit:
                continue
            length, symbol = hit
            try:
                left = _operand(tk[:i], names, "left")
                right = _operand(tk[i + length:], names, "right")
            except DadError as exc:
                if first_error is None:
                    first_error = exc
                continue
            candidates.append((i, length, symbol, left, right))

        if len(candidates) == 1:
            _, _, symbol, left, right = candidates[0]
            return f"({left} {symbol} {right})"
        if len(candidates) > 1:
            raise DadError(
                f"الشرط ملتبس في «{' '.join(tk)}»: كلمات المقارنة تظهر أيضًا داخل اسم معروف. "
                "غيّر اسم المتغير أو بسّط الشرط حتى يكون عامل المقارنة واضحًا."
            )
        if first_error is not None:
            raise first_error
        raise DadError(f"ما لقيت مقارنة في «{' '.join(tk)}». استخدم أكبر من أو أصغر من أو يساوي.")
    return {"op":"IF", "cond":condition(tokens(text.strip().rstrip(":")))}


def _find_cmp(norm, s):
    for words, sym in COMPARATORS:
        if tuple(norm[s:s + len(words)]) == words:
            return len(words), sym
    return None


def _has_cmp(norm):
    return any(_find_cmp(norm, s) for s in range(len(norm)))


# ============================================================================ ارسم — مشهد بقوالب ثابتة (بدون ذكاء)
COLORS = {nk(k): v for k, v in [("احمر", "#D84A3A"), ("حمراء", "#D84A3A"), ("ازرق", "#2F6FD0"), ("زرقاء", "#2F6FD0"),
          ("اخضر", "#3A9D5D"), ("خضراء", "#3A9D5D"), ("اصفر", "#F2C230"), ("صفراء", "#F2C230"), ("ابيض", "#F5F5F0"),
          ("بيضاء", "#F5F5F0"), ("اسود", "#2A2A2A"), ("سوداء", "#2A2A2A"), ("برتقالي", "#EE8A2C"), ("برتقاليه", "#EE8A2C"),
          ("بنفسجي", "#7E5BC4"), ("بنفسجيه", "#7E5BC4"), ("وردي", "#E07BA8"), ("ورديه", "#E07BA8"), ("بني", "#8A5A36"),
          ("بنيه", "#8A5A36"), ("رمادي", "#8E959C"), ("رماديه", "#8E959C")]}
OBJECTS = {}
for _names, _obj in [(("سفينه", "سفينة", "سفين", "سفن", "قارب", "مركب", "بوم", "لنج"), "ship"), (("بحر", "البحر", "موج", "شاطئ"), "sea"),
                     (("شمس", "الشمس"), "sun"), (("قمر", "القمر"), "moon"), (("نجوم", "نجمه", "نجوم"), "stars"),
                     (("بيت", "منزل", "بيوت"), "house"), (("شجره", "شجرة", "اشجار", "شجر"), "tree"), (("نخله", "نخلة", "نخيل"), "palm"),
                     (("جبل", "جبال"), "mountain"), (("غيمه", "غيوم", "سحاب", "سحابه"), "cloud"), (("ليل", "بالليل", "الليل"), "night")]:
    for _n in _names:
        OBJECTS[key(_n)] = _obj
POS = {nk("يمين"): 0.78, nk("اليمين"): 0.78, nk("يسار"): 0.22, nk("اليسار"): 0.22, nk("الوسط"): 0.5, nk("وسط"): 0.5, nk("النص"): 0.5}
DEFAULT_X = {"ship": 0.5, "house": 0.3, "tree": 0.62, "palm": 0.86, "mountain": 0.5, "cloud": 0.3, "sun": 0.82, "moon": 0.8}
NAME_RE = re.compile(r"(?:و?اسمه?ا?|و?اسمها|مكتوب عليه?ا?)\s+(.+?)(?:\s+(?:و|في|على)\s|$)")


def parse_draw(text):
    if not text.strip():
        raise DadError("حدد الرسم المطلوب؛ مثل: ارسم سفينة في البحر.")
    raw = re.sub(r"^(?:لي|لنا)\s+", "", text.strip()).strip("«»\"")
    label = None
    m = NAME_RE.search(raw)
    if m:
        label = m.group(1).strip(" «»\"")
        raw = raw[: m.start()] + " " + raw[m.end():]
    objs, unknown, last = [], [], None
    for w in tokens(raw):
        k = key(w.lstrip("و") if w.startswith("و") and len(w) > 2 and key(w[1:]) in OBJECTS else w)
        n = nk(w.lstrip("و")) if w.startswith("و") and len(w) > 2 else nk(w)
        if k in OBJECTS:
            last = {"type": OBJECTS[k], "color": None, "x": None}; objs.append(last); continue
        if n in COLORS and last:
            last["color"] = COLORS[n]; continue
        if n in POS and last:
            last["x"] = POS[n]; continue
        if re.match(r"[^\W\d_]", w) and n not in {nk(x) for x in ("في", "على", "فوق", "تحت", "و", "مع", "جنب", "عند", "كبيره", "كبير", "صغيره", "صغير", "لونها", "لونه", "داخل")}:
            unknown.append(w)
    kinds = {o["type"] for o in objs}
    if not objs:
        raise DadError(f"ما أعرف أرسم «{text.strip()}» بالأشكال الثابتة. جرّب سفينة أو بيتًا أو شجرة.")
    stop = {nk(x) for x in ("مشهد", "صوره", "صورة", "رسمه", "رسمة", "حلو", "حلوه", "جميل", "جميله", "كبير", "كبيره", "صغير", "صغيره",
                            "ملون", "ملونه", "واحد", "واحده", "لي", "لنا", "هادي", "هاديه", "وسط", "اليمين", "اليسار", "يمين", "يسار", "النص")}
    unknown = [w for w in unknown if nk(w) not in stop and nk(w.lstrip("و")) not in stop and not read_number([w], 0)]
    if unknown:
        raise DadError(f"ما أعرف أرسم «{'، '.join(unknown)}» بالأشكال الثابتة. أوقف الرسم حتى توضّح الوصف.")
    return {"op": "DRAW", "objects": objs, "label": label, "night": bool(kinds & {"moon", "stars", "night"}),
            "sea": "sea" in kinds, "unknown": unknown, "text": text.strip()}


def scene_svg(ast):
    W, H = 640, 400
    night, sea = ast["night"], ast["sea"]
    horizon = 250 if sea else 300
    sky = ("#1B2440", "#2E3D6B") if night else ("#8EC9F0", "#DDF1FC")
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
         f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[0]}"/><stop offset="1" stop-color="{sky[1]}"/></linearGradient></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']
    if sea:
        s.append(f'<rect y="{horizon}" width="{W}" height="{H - horizon}" fill="{"#1D3F6E" if night else "#2E86C1"}"/>')
        for y in range(horizon + 18, H, 26):
            s.append(f'<path d="M0 {y} ' + " ".join(f"q20 -8 40 0 t40 0" for _ in range(1)) + " " + " ".join("t40 0" for _ in range(15)) + f'" stroke="#FFFFFF" stroke-opacity=".35" fill="none" stroke-width="2"/>')
    else:
        s.append(f'<rect y="{horizon}" width="{W}" height="{H - horizon}" fill="{"#2F4A2A" if night else "#7CBF5E"}"/>')
    if night and not any(o["type"] in ("stars", "moon", "sun") for o in ast["objects"]):
        ast = dict(ast, objects=[{"type": "stars", "color": None, "x": None}, {"type": "moon", "color": None, "x": None}] + ast["objects"])
    order = {"stars": 0, "night": 0, "moon": 1, "sun": 1, "cloud": 2, "mountain": 3, "sea": 4, "house": 5, "tree": 6, "palm": 6, "ship": 7}
    for o in sorted(ast["objects"], key=lambda o: order.get(o["type"], 9)):
        t, c = o["type"], o["color"]
        x = int(W * (o["x"] if o["x"] is not None else DEFAULT_X.get(t, 0.5)))
        if t == "sun" and not night:
            s.append(f'<circle cx="{x}" cy="70" r="38" fill="{c or "#F7C948"}"/>')
        elif t in ("moon",) or (t == "sun" and night):
            s.append(f'<circle cx="{x}" cy="70" r="30" fill="{c or "#F4F1D0"}"/><circle cx="{x + 12}" cy="62" r="26" fill="{sky[0]}"/>')
        elif t == "stars":
            for sx, sy in ((60, 40), (140, 90), (230, 30), (320, 70), (410, 40), (520, 100), (590, 45), (270, 120)):
                s.append(f'<circle cx="{sx}" cy="{sy}" r="2.2" fill="#FFF8D6"/>')
        elif t == "cloud":
            s.append(f'<g fill="{c or "#FFFFFF"}" opacity=".92"><circle cx="{x}" cy="80" r="22"/><circle cx="{x + 24}" cy="70" r="28"/><circle cx="{x + 52}" cy="82" r="20"/></g>')
        elif t == "mountain":
            s.append(f'<path d="M{x - 200} {horizon} L{x - 60} {horizon - 130} L{x + 60} {horizon} Z" fill="{c or "#6F7F8F"}"/><path d="M{x - 20} {horizon} L{x + 90} {horizon - 100} L{x + 210} {horizon} Z" fill="{c or "#5B6B7B"}"/>')
        elif t == "house":
            y0 = horizon + 20
            s.append(f'<rect x="{x - 55}" y="{y0 - 80}" width="110" height="80" fill="{c or "#E8D3A8"}"/><path d="M{x - 68} {y0 - 78} L{x} {y0 - 130} L{x + 68} {y0 - 78} Z" fill="#B5523B"/><rect x="{x - 14}" y="{y0 - 40}" width="28" height="40" fill="#7A4A2A"/>')
        elif t == "tree":
            y0 = horizon + 25
            s.append(f'<rect x="{x - 8}" y="{y0 - 70}" width="16" height="70" fill="#7A4A2A"/><circle cx="{x}" cy="{y0 - 95}" r="42" fill="{c or "#3E9A4E"}"/>')
        elif t == "palm":
            y0 = horizon + 25
            s.append(f'<path d="M{x - 6} {y0} Q{x + 4} {y0 - 70} {x + 2} {y0 - 140}" stroke="#8A5A36" stroke-width="12" fill="none"/>')
            for dx, dy in ((-60, 10), (60, 10), (-45, -25), (45, -25), (0, -40)):
                s.append(f'<path d="M{x + 2} {y0 - 140} Q{x + dx / 2} {y0 - 160 + dy / 2} {x + dx} {y0 - 130 + dy}" stroke="{c or "#2E8B3E"}" stroke-width="8" fill="none" stroke-linecap="round"/>')
        elif t == "ship":
            y0 = horizon + 8 if sea else horizon + 30
            hull = c or "#7A3E2A"
            s.append(f'<path d="M{x - 110} {y0 - 30} L{x + 110} {y0 - 30} L{x + 80} {y0 + 10} L{x - 80} {y0 + 10} Z" fill="{hull}"/>'
                     f'<rect x="{x - 4}" y="{y0 - 150}" width="8" height="120" fill="#5A3A22"/>'
                     f'<path d="M{x + 4} {y0 - 145} L{x + 80} {y0 - 45} L{x + 4} {y0 - 45} Z" fill="#FAFAF2"/>'
                     f'<path d="M{x - 4} {y0 - 130} L{x - 70} {y0 - 45} L{x - 4} {y0 - 45} Z" fill="#EDEDE2"/>')
            if ast.get("label"):
                lbl = ast["label"].replace("&", "&amp;").replace("<", "&lt;")
                s.append(f'<text x="{x}" y="{y0 - 5}" text-anchor="middle" font-family="Tahoma, Segoe UI, sans-serif" font-size="20" fill="#FFFFFF" direction="rtl">{lbl}</text>')
                ast = dict(ast, label=None)
    if ast.get("label"):
        lbl = ast["label"].replace("&", "&amp;").replace("<", "&lt;")
        s.append(f'<text x="{W // 2}" y="{H - 16}" text-anchor="middle" font-family="Tahoma, Segoe UI, sans-serif" font-size="22" fill="#FFFFFF" direction="rtl">{lbl}</text>')
    s.append("</svg>")
    return "".join(s)


# ============================================================================ افتح / احفظ / كرر
def _destination(text, words):
    """A storage separator is a word outside quotes and value parentheses."""
    for i, _, depth in spans(text):
        if depth != 0 or (i and not text[i-1].isspace()): continue
        for word in words:
            end = i + len(word)
            if text.startswith(word, i) and end < len(text) and text[end].isspace():
                left, right = text[:i].strip(), text[end:].strip()
                if left and right: return left, right
    return None


def parse_add(text, names: Names):
    m = _destination(text.strip(), ('إلى', 'الى', 'ل', 'على'))
    if not m:
        raise DadError(f"ما فهمت وش أضيف ووين في «{text.strip()}». مثل: أضف تفاح إلى السلة")
    what, target = m
    t = names.find(target)
    if not t:
        raise DadError(f"ما أعرف «{target}». سوّها أول:", [f"{target} = []"])
    me = math_expr(items_of(what, names))                     # 5 ← رقم ، خمسة ← 5 ، س ضرب 2 ← حساب
    item = me[0] if me else parse_output(what, names)["expr"]  # تفاح ← "تفاح" ، الاسم ← قيمته
    return {"op": "ADD", "target": t, "expr": item}


def parse_open(text):
    if not text.strip():
        raise DadError("«افتح» تحتاج اسم الملف؛ مثل: افتح نتيجة.txt.")
    m = re.match(r"^(?:ملف\s+)?[\"«]?(.+?)[\"»]?\s*$", text.strip())
    return {"op": "READ", "path": m.group(1)}


def parse_save(text, names: Names):
    m = _destination(text.strip(), ('في',))
    if not m:
        raise DadError(f"ما فهمت وش أحفظ ووين في «{text.strip()}». مثل: احفظ(الناتج في نتيجة.txt)")
    src, dest = m
    if src.startswith("["):
        try:
            outside = {i for i, _, _ in spans(src)}
            literal = ''.join((',' if ch == '،' else ch.translate(AR_DIGITS)) if i in outside else ch for i, ch in enumerate(src))
            literal = TOKEN_RE.sub(lambda x: json.dumps(_quoted_value(x.group()), ensure_ascii=False) if x.group()[:1] in "\"'«" else x.group(), literal)
            value = py_ast.literal_eval(literal)
            if not isinstance(value, list): raise ValueError()
            what = repr(value)
        except (ValueError, SyntaxError):
            raise DadError("القائمة في «احفظ» غير صحيحة؛ افصل القيم بفواصل وأغلق الأقواس.") from None
    else:
        value = parse_output(src, names)
        if value['op'] != 'OUTPUT': raise DadError("«احفظ» تحتاج قيمة جاهزة؛ اسأل عنها أولًا.")
        what = value['expr']
    is_file = dest.startswith("ملف ") or dest[:1] in "\"'«" or any(x in dest for x in (".", "/", "\\"))
    if is_file:
        path = re.sub(r"^ملف\s+", "", dest).strip().strip("\"'«»")
        return {"op": "WRITE", "expr": what, "path": path}
    _check_user_name(dest)
    return {"op": "SAVE_VAR", "var": names.add(dest), "expr": what}


TIMES_RE = re.compile(r"^(.*?)\s*(\S+(?:\s+\S+)?)\s+(?:مرات|مره|مرة|مرّات)\s*(.*)$")


def parse_repeat(text, names: Names):
    t = text.strip()
    if re.match(r"^-\s*\d+(?:\.\d+)?\s*(?:مرات|مرة|مره)?$", t.translate(AR_DIGITS)):
        raise DadError("عدد مرات «كرر» لا يجوز أن يكون سالبًا.")
    t = re.sub(r"(?<!\S)مرتين(?!\S)", "2 مرات", t)
    t = re.sub(r"^(?:مرة|مره)(?:\s+(?:وحدة|وحده|واحدة|واحده))?$", "1 مرات", t)
    # كلام طبيعي شائع: «كرر اسأل ... مرتين» = مرتان بالضبط.
    # نفصله قبل TIMES_RE لأن «مرتين» كلمة واحدة وما فيها رقم مستقل.
    m2 = re.match(r"^(.*?)\s+مرتين\s*$", t)
    if m2:
        count, rest = 2, m2.group(1).strip()
        inner = None
        if rest:
            inner = parse_statement(rest, names, loose=True)
            if inner is None:
                raise DadError(f"ما فهمت وش أكرر في «{rest}». مثل: كرر(اسأل كم عمرك مرتين)")
        return {"op": "REPEAT", "count": count, "body": inner}
    m = TIMES_RE.match(t)
    count, rest = None, t
    if m:
        before, num_words, after = m.group(1), m.group(2), m.group(3)
        tk = tokens(num_words)
        for s in range(len(tk)):
            r = read_number(tk, s)
            if r and r[1] == len(tk):
                count = r[0]
                rest = (before + " " + " ".join(tk[:s]) + " " + after).strip()
                break
    if count is None and m:
        # العدد متغير: «كرر(العدد مرات)» / «كرر(قل هلا العدد مرات)»
        before, num_words, after = m.group(1), m.group(2), m.group(3)
        tk = tokens(num_words)
        if tk and names.find(tk[-1]):
            count = names.find(tk[-1])
            rest = (before + " " + " ".join(tk[:-1]) + " " + after).strip()
    if count is None:
        tk = tokens(t)
        r = read_number(tk, 0) if tk else None
        if r:
            count, rest = r[0], " ".join(tk[r[1]:])
        elif tk and names.find(tk[0]) and len(tk) == 1:
            count, rest = names.find(tk[0]), ""
        elif len(tk) == 1 and re.fullmatch(r"\d+", tk[0]):
            count, rest = int(tk[0]), ""
        else:
            raise DadError(f"ما عرفت كم مرة في «{t}». حدد العدد، مثل: كرر 3 مرات  أو  كرر(قل هلا 3 مرات)",
                           ["كرر 3 مرات", f"كرر({t} 3 مرات)"])
    inner = None
    if rest:
        inner = parse_statement(rest, names, loose=True)
        if inner is None:
            raise DadError(f"ما فهمت وش أكرر في «{rest}». مثل: كرر(قل مرحبا خمس مرات)")
    return {"op": "REPEAT", "count": count, "body": inner}




# ============================================================================ الدوال الطبيعية — 1.8
_DEFINE_RE = re.compile(r"^(?:عرّف|عرف)\s+(?:دالة\s+)?(?:اسمها\s+)?([^\W\d]\w*)\s*(.*?)\s*:?\s*$")
_DEFINE_RET_RE = re.compile(r"\s+(?:و?يرجع|و?ترجع|و?أرجع|و?ارجع)\s+(.+)$")
_DEFINE_TAKES_RE = re.compile(r"^(?:ياخذ|يأخذ|ياخد|يأخد|يستقبل|مدخلاته?|معاملاته?)\s+(.+)$")
_DEFINE_NONE_RE = re.compile(r"^(?:بدون\s+(?:مدخلات|معاملات|قيم)|ما\s+ياخذ\s+شي|ما\s+يأخذ\s+شي)\s*$")


def _copy_names(names):
    n = Names()
    n.by_key.update(names.by_key)
    n.labels.update(getattr(names, "labels", {}))
    n.aliases.update({k: set(v) for k, v in names.aliases.items()})
    n.functions.update(names.functions)
    n._seq = getattr(names, "_seq", 0)
    return n


def _define_params(text):
    """يفهم: «ياخذ س» / «ياخذ أ و ب» / «بدون مدخلات»."""
    t = text.strip().strip(':').strip()
    if not t or _DEFINE_NONE_RE.match(t):
        return []
    m = _DEFINE_TAKES_RE.match(t)
    if not m:
        raise DadError("بعد اسم الدالة اكتب وش تاخذ، مثل: عرّف جمع ياخذ أ و ب")
    raw = m.group(1).strip()
    raw = re.sub(r"^(?:متغيرات?|قيم|مدخلات)\s+", "", raw)
    # الفاصلة أو «و» بين الأسماء. ما نفصل الواو الملصوقة داخل الاسم.
    parts = [x.strip() for x in re.split(r"\s*(?:،|,)\s*|\s+و\s+", raw) if x.strip()]
    if not parts:
        raise DadError("ما لقيت أسماء المدخلات بعد «ياخذ».")
    bad = [x for x in parts if not re.fullmatch(r"[^\W\d]\w*", x)]
    if bad:
        raise DadError(f"اسم المدخل لازم يكون كلمة وحدة. ما فهمت: «{bad[0]}»")
    if len(set(parts)) != len(parts):
        raise DadError("فيه اسم مدخل مكرر في تعريف الدالة.")
    return parts


def parse_define(text, names: Names):
    """عرّف ضعف ياخذ س [ويرجع س ضرب 2] ← def ضعف(س): ..."""
    t = text.strip()
    m = _DEFINE_RE.match(t)
    if not m:
        return None
    name, rest = m.group(1), m.group(2).strip()
    ret = None
    mr = _DEFINE_RET_RE.search(" " + rest)
    if mr:
        # +1 لأننا أضفنا مسافة في بداية النص للبحث
        start = max(0, mr.start() - 1)
        ret = mr.group(1).strip().rstrip(':').strip()
        rest = rest[:start].strip()
    params = _define_params(rest)
    _check_user_name(name)
    names.functions.add(name)
    local = _copy_names(names)
    for param in params:
        _check_user_name(param)
        local.add(param)
    ast = {"op": "DEFINE", "name": name, "params": params, "return_expr": None}
    if ret:
        out = parse_output(ret, local)
        if out.get("op") != "OUTPUT":
            raise DadError("الجزء بعد «يرجع» لازم يكون قيمة أو حساب بسيط.")
        ast["return_expr"] = out["expr"]
    return ast

# ============================================================================ توزيع الأوامر
COMMANDS = {}
for _w, _c in [("قل", "OUT"), ("قول", "OUT"), ("اطبع", "OUT"), ("اعرض", "OUT"), ("اسأل", "ASK"), ("اسال", "ASK"),
               ("احسب", "CALC"), ("احسبلي", "CALC"), ("أكمل", "CONTINUE"), ("اكمل", "CONTINUE"), ("كمل", "CONTINUE"),
               ("ارسم", "DRAW"), ("رسم", "DRAW"), ("ارسملي", "DRAW"),
               ("إذا", "IF"), ("اذا", "IF"), ("لو", "IF"), ("وإلا إذا", "ELIF"), ("والا اذا", "ELIF"), ("كرر", "REPEAT"),
               ("افتح", "OPEN"), ("احفظ", "SAVE"), ("أضف", "ADD"), ("اضف", "ADD"), ("ضيف", "ADD"),
               ("اطلب", "AI"), ("أطلب", "AI"), ("حلل", "EXPLAIN"), ("حللي", "EXPLAIN"), ("اشرح", "EXPLAIN")]:
    COMMANDS[nk(_w)] = _c

# أسماء محجوزة لا يجوز للمستخدم أن يحولها إلى متغيرات عادية.
# هذا يمنع كسر معنى اللغة مثل: الناتج = 5 أو ثم = 3.
RESERVED_NAMES = {nk(w) for w in (
    "قل", "قول", "اطبع", "اعرض", "اسأل", "اسال", "احسب", "احسبلي",
    "كمل", "أكمل", "اكمل", "كرر", "إذا", "اذا", "وإلا", "والا", "لكل", "ثم", "كم",
    "ارسم", "افتح", "احفظ", "أضف", "اضف", "اطلب", "حلل",
    "الناتج", "الرد", "المحتوى"
)}

def _check_user_name(name):
    raw = " ".join(str(name).split())
    if nk(raw) in RESERVED_NAMES or (len(raw.split()) == 1 and key(raw) in {key(w) for w in RESERVED_NAMES}):
        raise DadError(f"«{name}» اسم محجوز في لغة الضاد — اختر اسم ثاني للمتغير.")
    parts = tokens(raw)
    valid = bool(parts) and _name_token_ok(parts[0], first=True) and all(
        _name_token_ok(t, first=(i == 0)) for i, t in enumerate(parts)
    )
    if raw.startswith("_dad") or not valid:
        raise DadError(f"الاسم «{name}» غير صالح؛ يبدأ بكلمة ويمكن أن يحتوي أرقامًا بعدها، مثل «سعر بيع 1».")

_SK = str.maketrans({"ب": "ٮ", "ت": "ٮ", "ث": "ٮ", "ن": "ٮ", "ي": "ٮ", "ج": "ح", "خ": "ح", "ذ": "د", "ز": "ر",
                     "ش": "س", "ض": "ص", "ظ": "ط", "غ": "ع", "ق": "ڡ", "ف": "ڡ"})
_CMD_SK = {nk(k).translate(_SK): c for k, c in COMMANDS.items()}


def _edit1(a, b):
    """True إذا الفرق تعديل واحد فقط: حرف ناقص/زائد/مبدل. للأوامر القصيرة نتشدد."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    i = j = dif = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1; j += 1
        else:
            dif += 1; j += 1
            if dif > 1:
                return False
    return True

def _cmd_of(word):
    """يتحمل اختلاف النقاط وخطأ كتابة واحد في الأمر، بدون تخمين الكلمات العادية."""
    k = nk(word)
    exact = COMMANDS.get(k) or _CMD_SK.get(k.translate(_SK))
    if exact:
        return exact
    # لا نصحح الكلمات القصيرة جداً لأنها قد تكون كلاماً عادياً.
    if len(k) < 4:
        return None
    matches = {c for w, c in COMMANDS.items() if len(w) >= 4 and _edit1(k, w)}
    return next(iter(matches)) if len(matches) == 1 else None


CALL_RE = re.compile(r"^\s*(وإلا إذا|والا اذا|[^\W\d_]+)\s*\((.*)\)\s*(:?)\s*$")


LOOSE_OK = {"OUT", "ASK", "CALC", "CONTINUE", "DRAW", "SAVE", "OPEN", "ADD", "AI", "EXPLAIN"}   # إذا/كرر بدون أقواس = صيغة الضاد القديمة


def _cmd_words(text):
    """مواقع كلمات الأوامر خارج النصوص."""
    hits = []
    visible = {i for i, _ch, depth in spans(text) if depth == 0}
    text_end = len(text.rstrip())
    text_start = len(text) - len(text.lstrip())
    for m in re.finditer(r'[^\W\d_][\w]*', text):
        w = m.group(0)
        if m.start() not in visible:
            continue
        # تصحيح خطأ إملائي للأمر مسموح فقط إذا الكلمة في طرف السطر.
        # داخل الكلام نطلب أمراً حقيقياً، حتى لا تتحول «الطلب» إلى «اطلب».
        if m.start() == text_start or m.end() == text_end:
            c = _cmd_of(w)
        else:
            k = nk(w)
            c = COMMANDS.get(k) or _CMD_SK.get(k.translate(_SK))
        if c in LOOSE_OK:
            hits.append((m.start(), m.end(), w, c))
    return hits


_one_group = one_group


def _has_block(lines, no):
    """السطر رقم no (من 1) تحته أسطر مزاحة أكثر منه؟"""
    cur = lines[no - 1].expandtabs(4); ind = len(cur) - len(cur.lstrip())
    nxt = next((j for j in range(no, len(lines)) if lines[j].strip() and not lines[j].strip().startswith("#")), None)
    return nxt is not None and len(lines[nxt].expandtabs(4)) - len(lines[nxt].expandtabs(4).lstrip()) > ind


def natural_line_safe(text):
    try:
        return natural_line(text)
    except DadError:
        return "cmd"


def natural_line(text):
    """«احسب كم عدد البيض» / «كم عدد البيض احسب» ← احسب(كم عدد البيض). None إذا ما ينطبق."""
    t = text.strip()
    if not t or "(" in t.split(None, 1)[0]:
        return None
    hits = _cmd_words(t)
    if not hits:
        return None
    first, last = hits[0], hits[-1]
    starts, ends = first[0] == 0, last[1] == len(t.rstrip("؟?.! "))
    # جزء «ثم» الواحد أمر واحد. إذا بدأ بأمر، باقي الكلام محتواه حتى لو فيه
    # كلمات أوامر (قول ... احسب / أكمل / اسأل). أمران حقيقيان يفصلهم «ثم».
    # الصيغة المقلوبة تبقى: الجملة لا تبدأ بأمر وتنتهي بأمر واحد — «كم عدد البيض احسب».
    if starts:
        rest = t[first[1]:].strip()
        if _one_group(rest):
            return f"{first[2]}{rest}"
        return f"{first[2]}({rest})"
    if ends and len(hits) == 1:
        return f"{last[2]}({t[:last[0]].strip()})"
    return None


# 1.9.13 — الوسائط: «شغّل صوت (x.mp3)» · «شغّل فيديو (x.mp4)» · «اعرض صورة (x.jpg)»
MEDIA_RE = re.compile(r"^\s*(?:(?:شغّل|شغل|شغِّل|شغِل)\s+(?P<av>صوت|الصوت|فيديو|الفيديو|فديو)|(?:اعرض|أعرض)\s+(?P<img>صورة|صوره|الصورة|الصوره))(?:\s+(?P<rest>.*?))?\s*$")
MEDIA_EXT = {"audio": (".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"),
             "video": (".mp4", ".webm", ".ogv", ".mov", ".m4v"),
             "image": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")}
MEDIA_AR = {"audio": "صوت", "video": "فيديو", "image": "صورة"}


def is_media(text):
    return bool(MEDIA_RE.match(text or ""))


def parse_media(text, names):
    m = MEDIA_RE.match(text)
    word = nk(m.group("av") or "")
    kind = "image" if m.group("img") else ("video" if ("فيديو" in word or "فديو" in word) else "audio")
    rest = (m.group("rest") or "").strip()
    if _one_group(rest):
        rest = rest[1:-1].strip()
    rest = rest.strip("«»\"' ")
    if not rest:
        ex = {"audio": "شغّل صوت (أذان.mp3)", "video": "شغّل فيديو (رحلة.mp4)", "image": "اعرض صورة (بيتي.jpg)"}[kind]
        raise DadError(f"حدد اسم ملف ال{MEDIA_AR[kind]}.", [ex])
    v = names.find(rest)                                  # اسم الملف محفوظ في متغير
    expr = v if v else json.dumps(rest, ensure_ascii=False)
    return {"op": "MEDIA", "kind": kind, "expr": expr, "text": rest}


def _outside_quotes(s):
    """النص بدون اللي داخل "..." و«...» — الأقواس داخل نص محمي مو كود."""
    return re.sub(r'"(?:[^"\\]|\\.)*"|«[^»]*»', '""', s)


def parse_statement(text, names: Names, loose=False):
    """أمر(كلام) — أو في وضع loose: «قل مرحبا» بدون أقواس (داخل كرر)."""
    if is_media(text):
        return parse_media(text, names)
    m = CALL_RE.match(text)
    if m and _cmd_of(m.group(1)):
        cmd, body = _cmd_of(m.group(1)), m.group(2)
        if not one_group(text[text.index('('):]):
            raise DadError('فيه أكثر من أمر في السطر؛ حط بينهم «ثم».')
        outside = _outside_quotes(body)
        call_words = re.findall(r"([^\W\d_]\w*)\s*\(", outside)
        nested_call = any(w in names.functions or nk(w) in {nk(x) for x in ('صحيح', 'عشري', 'نص', 'مدى', 'طول', 'مجموع', 'أكبر', 'أصغر', 'قرّب')} for w in call_words)
        nested_call = nested_call or bool(re.search(r'\w+(?:\.\w+)+\s*\(', outside))
        has_struct = re.search(r"[\[{]", outside)
        has_paren = "(" in outside or ")" in outside
        # الأقواس الحسابية للتجميع جزء رسمي من «احسب»: (2 + 3) × 4.
        # استدعاء دالة مثل ضعف(5)، والقوائم/القواميس، تظل للمسار القديم.
        legacy_nested = (has_struct and cmd not in ('SAVE', 'OUT')) or (nested_call and cmd not in ('SAVE', 'CONTINUE', 'IF', 'ELIF'))
        if nk(m.group(1)) == "اطبع" or (legacy_nested and cmd not in ("EXPLAIN", "AI")):
            return None                                        # صيغة الضاد القديمة / Python — تمشي في المسار القديم
    elif loose:
        w = text.strip().split(None, 1)
        if not w or not _cmd_of(w[0]):
            return None
        cmd, body = _cmd_of(w[0]), (w[1] if len(w) > 1 else "")
    else:
        return None
    if cmd in ('OUT', 'ASK', 'CALC'):
        label = {'OUT': 'قول', 'ASK': 'اسأل', 'CALC': 'احسب'}[cmd]
        ambiguity = _command_ambiguity(label + ' ' + body)
        if ambiguity:
            raise DadError(ambiguity)
    if cmd == "OUT":
        return parse_output(body, names)
    if cmd == "ASK":
        return parse_ask(body, names)
    if cmd == "CALC":
        if not body.strip():
            names.add("الناتج"); return {"op": "CALC_ASK"}         # «احسب» لحالها ← تسأل وش تحسب
        a = parse_calc(body, names); names.add("الناتج"); return a
    if cmd == "CONTINUE":
        if not body.strip():
            raise DadError("«أكمل» ناقصة — اكتب شنو تبي تكمل على القيمة السابقة.",
                           ["أكمل ناقص 4", "أكمل زائد 2", "أكمل ضرب 3"])
        # «أكمل» إذا نجحت تنتج «الناتج»، فنعرّفه الآن حتى يقدر الجزء التالي بنفس السطر يقول الناتج.
        names.add("الناتج")
        # ما نفسر الحساب هنا؛ لازم نعرف الأمر السابق أولاً في expand.
        return {"op": "CONTINUE_RAW", "text": body.strip()}
    if cmd == "AI":
        return parse_ai(body, names)
    if cmd == "EXPLAIN":
        return parse_explain(body, names)
    if cmd == "DRAW":
        return parse_draw(body)
    if cmd in ("IF", "ELIF"):
        a = parse_cond(body, names); a["op"] = cmd; return a
    if cmd == "REPEAT":
        return parse_repeat(body, names)
    if cmd == "OPEN":
        names.add("المحتوى"); return parse_open(body)
    if cmd == "SAVE":
        return parse_save(body, names)
    if cmd == "ADD":
        return parse_add(body, names)
    return None



# ============================================================================ اطلب (الذكاء المحلي) و حلل (فهم بدون تنفيذ)
def parse_ai(text, names: Names):
    raise DadError(AI_DISABLED)


_OBJ_AR = {"ship": "سفينة", "sea": "بحر", "sun": "شمس", "moon": "قمر", "stars": "نجوم", "house": "بيت", "tree": "شجرة",
           "palm": "نخلة", "mountain": "جبال", "cloud": "غيوم", "night": "ليل"}
_SYM_AR = {">=": "أكبر من أو يساوي", "<=": "أصغر من أو يساوي", "!=": "مو يساوي", "==": "يساوي", ">": "أكبر من", "<": "أصغر من",
           " and ": " و ", " or ": " أو ", "_dad_count": "عدد", "**": "أس", "*": "×", "/": "÷"}


def _readable(expr):
    s = str(expr)
    for k, v in _SYM_AR.items():
        s = s.replace(k, f" {v} " if k.strip() not in ("and", "or", "_dad_count") else v)
    return re.sub(r"\s+", " ", s.replace('"', "«", 1).replace('"', "»", 1)).strip()


def _try_value(expr):
    if re.fullmatch(r"[\d\s.+\-*/()]+", str(expr)):
        try:
            return _fmt(round(eval(expr, {"__builtins__": {}}, {}), 6))
        except Exception:
            return None
    return None


def describe(a):
    op = a["op"]
    if op == "OUTPUT":
        e = a["expr"]
        if e.startswith('"'):
            return f"يعرض الكلام: {json.loads(e)}"
        return f"يعرض قيمة: {_readable(e)}"
    if op == "INPUT":
        return f"يسأل «{a['prompt']}» ويحفظ الجواب في «{a['var']}»" + (" كرقم" if a.get("numeric") else "")
    if op == "CALC":
        val = _try_value(a["expr"])
        return f"يحسب: {_readable(a.get('say') or a['expr'])}" + (f" = {val}" if val is not None else "") + " ← ويحفظه في «الناتج»"
    if op == "CALC_ASK":
        return "يسألك وش تبي تحسب، ويحسبه"
    if op == "CONTINUE_RAW":
        return f"يكمل على قيمة الأمر السابق: {a['text']}"
    if op == "SEQ":
        return " ثم ".join(describe(x) for x in a["body"])
    if op in ("IF", "ELIF"):
        return f"شرط: إذا {_readable(a['cond'])} ← ينفذ الأسطر اللي تحته"
    if op == "MEDIA":
        return {"audio": "يشغّل صوت", "video": "يشغّل فيديو", "image": "يعرض صورة"}[a["kind"]] + f": «{a['text']}»"
    if op == "REPEAT_POST":
        return f"يكرر «{describe(a['body'])}» {a['count']} مرات"
    if op == "REPEAT":
        return f"يكرر {a['count']} مرات" + (f": {describe(a['body'])}" if a.get("body") else " الأسطر اللي تحته")
    if op == "FOREACH":
        return f"يمر على كل عنصر في «{a['coll']}» باسم «{a['item']}»" + (f": {describe(a['body'])}" if a.get("body") else "")
    if op == "DRAW":
        s = "يرسم مباشرة: " + "، ".join(_OBJ_AR.get(o["type"], o["type"]) for o in a["objects"])
        if a.get("label"): s += f" واسمها «{a['label']}»"
        if a.get("unknown"): s += f" — وما يعرف يرسم «{'، '.join(a['unknown'])}» إلا بالذكاء"
        return s
    if op == "DRAW_AI":
        return f"يرسم بالذكاء المحلي: {a['text']}"
    if op == "ADD":
        return f"يضيف {_readable(a['expr'])} إلى «{a['target']}»"
    if op == "READ":
        return f"يفتح الملف «{a['path']}» ويحط محتواه في «المحتوى»"
    if op == "WRITE":
        return f"يحفظ {_readable(a['expr'])} في الملف «{a['path']}»"
    if op == "AI":
        src = f"قيمة «{a['direct']}»" if a.get("direct") else f"«{a['prompt']}»"
        extra = f" ومعه قيم: {'، '.join(a['ctx'])}" if a.get("ctx") else ""
        return f"يرسل {src} للذكاء المحلي{extra}، ويحفظ الرد في «{a['var']}»"
    return "أمر"


def parse_explain(text, names: Names):
    t = text.strip()
    if not t:
        return {"op": "EXPLAIN", "msg": "اكتب شي أحلله، مثل: حلل(خمس بيضات وسعر البيضة دينارين)"}
    look = _copy_names(names)                                  # نسخة: التحليل ما يغيّر حالة البرنامج
    try:
        a = parse_foreach(t, look) if re.match(r"^(?:لكل|كل)\s", t) else None
        stmt = natural_line(t) or t
        a = a or parse_statement(stmt, look)
        if a is None:
            a = parse_calc(t, look)
        msg = describe(a)
    except DadError as e:
        msg = "ما فهمت: " + str(e) + ((" — تقصد: " + " / ".join(e.options[:3])) if e.options else "")
    return {"op": "EXPLAIN", "msg": msg}

# ============================================================================ من AST إلى Python (سطر مقابل سطر)
def _evaluate_call(expr, continuing=False):
    # Explicit value references preserve Python's closure binding while the
    # arithmetic itself stays in the checked Aldad evaluator.
    builtins = {'sum', 'max', 'min', '_dad_mean', '_dad_count', 'القيمة_الفعالة'}
    references = sorted({n.id for n in py_ast.walk(py_ast.parse(expr, mode='eval')) if isinstance(n, py_ast.Name)} - builtins)
    values = '{' + ', '.join(f'{json.dumps(n, ensure_ascii=False)}: {n}' for n in references) + '}'
    scope = f'dict(locals(), **{values})' if references else 'locals()'
    flag = ', True' if continuing else ''
    return f'_dad_evaluate({json.dumps(expr, ensure_ascii=False)}, globals(), {scope}{flag})'


def codegen(a):
    op = a["op"]
    if op == "SEQ":
        return "\n".join(codegen(x) for x in a["body"])
    if op == "OUTPUT":
        if a.get("note"):
            return f"_dad_note({json.dumps(a['note'], ensure_ascii=False)}); _dad_show({a['expr']})"
        return f"_dad_show({a['expr']})"
    if op == "INPUT":
        if not _IDENT_RE.match(a.get("var") or ""):
            raise DadError(f"الاسم «{a.get('var')}» مو صالح لحفظ الجواب — لازم كلمة واحدة بدون مسافات.")
        targets = " = ".join([a["var"]] + [x for x in a.get("also", []) if _IDENT_RE.match(x)])
        return f"{targets} = _dad_ask({json.dumps(a['prompt'], ensure_ascii=False)}, {a['numeric']}); _dad_active = {a['var']}"
    if op == "CALC":
        return f"الناتج = _dad_calc({_evaluate_call(a['expr'], bool(a.get('continued_from')))}); _dad_active = الناتج"
    if op == "SAVE_VAR":
        return f"{a['var']} = {a['expr']}"
    if op == "DEFINE":
        head = f"def {a['name']}({', '.join(a.get('params', []))}):"
        return head + (f" return {a['return_expr']}" if a.get('return_expr') is not None else "")
    if op == "DRAW":
        return f"_dad_svg({json.dumps(scene_svg(a), ensure_ascii=False)})"
    if op == "ELSE":
        return "else:"
    if op == "IF":
        return f"if {a['cond']}:"
    if op == "ELIF":
        return f"elif {a['cond']}:"
    if op == "MEDIA":
        return f"_dad_media({json.dumps(a['kind'])}, {a['expr']})"
    if op == "REPEAT_POST":
        return f"for _ in range(_dad_times({a['count']})):\n" + "\n".join("    " + line for line in codegen(a['body']).splitlines())
    if op == "REPEAT":
        cnt = f"_dad_times({a['count']})" if isinstance(a["count"], str) else str(_dad_times(a['count']))
        head = f"for _ in range({cnt}):"
        return head + ("\n" + "\n".join("    " + x for x in codegen(a["body"]).splitlines()) if a.get("body") else "")
    if op == "ADD":
        return f"{a['target']}.append({a['expr']})"
    if op == "EXPLAIN":
        return f"_dad_explain({json.dumps(a['msg'], ensure_ascii=False)})"
    if op == "CALC_ASK":
        return "الناتج = _dad_calc_ask(globals(), locals()); _dad_active = الناتج"
    if op == "CONTINUE_RAW":
        raise DadError("«أكمل» لازم ترتبط بأمر سابق يعطي قيمة.")
    if op == "FOREACH":
        head = f"for {a['item']} in {a['coll']}:"
        return head + ("\n" + "\n".join("    " + x for x in codegen(a["body"]).splitlines()) if a.get("body") else "")
    if op == "READ":
        return f"المحتوى = _dad_read({json.dumps(a['path'], ensure_ascii=False)})"
    if op == "WRITE":
        return f"_dad_write({json.dumps(a['path'], ensure_ascii=False)}, {a['expr']})"
    raise DadError("أمر غير معروف")


def _ensure_exec(code: str, src: str):
    """لو المحرك ولّد بايثون ينهار، نوقف بخطأ عربي على السطر الأصلي — مو رسالة أقواس مضللة."""
    probe = code + ("\n    pass" if code.rstrip().endswith(":") else "")
    try:
        compile(probe, "<ضاد>", "exec")
    except SyntaxError:
        raise DadError(f"ما قدرت أحول السطر لبرنامج صالح. راجع: «{src}».")


_split_then = split_then


FOREACH_RE = re.compile(r"^(?:لكل|كل)\s+([^\W\d]\w*)\s+(?:في|من)\s+(.+?)\s*:?\s*$")


def parse_foreach(body, names):
    m = FOREACH_RE.match(body)
    if not m: return None
    item, remainder = m.group(1), m.group(2).rstrip(":").strip()
    _check_user_name(item)
    if re.match(r"مدى\s*\(", remainder): return None  # old range form
    words = tokens(remainder)
    match = names.match_tokens(words, 0) if words else None
    if not match:
        label = words[0] if words else remainder
        raise DadError(f"ما أعرف «{label}» — سوّها قائمة أول.", [f"{label} = []"])
    coll, used = match
    rest = remainder.split(None, used)[used] if len(remainder.split(None, used)) > used else ""
    names.add(item)
    rest = re.sub(r"^ثم\s+", "", rest)
    inner = _parse_part(rest, names) if rest else None
    if rest and inner is None: raise DadError(f"ما فهمت وش أسوي لكل «{item}»: «{rest}».")
    return {"op":"FOREACH", "item":item, "coll":coll, "body":inner}


ELSE_RE = re.compile(r"^(وإلا|والا|غير ذلك|وإلا:|والا:)\s*:?\s*$")


NOTES = []          # ملاحظات وقت التحويل: [(رقم السطر، نص)] — تنطبع مع ✎ ولا توقف البرنامج


def _command_ambiguity(part):
    """Reject two possible commands without a separator before any execution."""
    t = part.strip()
    if not t or "(" in t.split(None, 1)[0]:
        return None
    # Content is never spell-corrected into a second command. For example,
    # العرض and الطلب are ordinary names, not اعرض and اطلب.
    hits = [h for h in _cmd_words(t) if nk(h[2]) in COMMANDS]
    if len(hits) < 2:
        return None
    first, last = hits[0], hits[-1]
    if first[3] not in ('OUT', 'ASK', 'CALC'):
        return None
    body = t[first[1]:].strip()
    if len(tokens(body)) <= (2 if first[3] == 'ASK' else 1):
        return None
    if first[0] != (len(t) - len(t.lstrip())) or last[1] != len(t.rstrip("؟?.! ")):
        return None
    later = []
    for h in hits[1:]:
        if h[2] not in later:
            later.append(h[2])
    words = " و".join(f"«{w}»" for w in later)
    return f"فيه أمرين بدون «ثم»: «{first[2]}» و{words}. افصل الأوامر بـ «ثم»، أو ضع الكلام الحرفي بين «»."


SOURCE_MAP = []  # generated line -> original Aldad line
LAST_NAMES = None


def _resolve_continue(node, names):
    if node is None:
        return None
    if node['op'] == 'CONTINUE_RAW':
        text = node['text']
        tk = tokens(text)
        first = nk(tk[0]) if tk else ''
        if first not in OP_WORDS and (not tk or tk[0] not in ('+', '-', '*', '/', '×', '÷')):
            raise DadError('«كمل» تحتاج عملية بعد القيمة القديمة، مثل: كمل زائد 2.')
        local = _copy_names(names)
        local.add('القيمة_الفعالة')
        result = parse_calc('القيمة_الفعالة ' + text, local)
        if result['op'] != 'CALC':
            raise DadError('ما فهمت تكملة القيمة القديمة — اكتب عملية واضحة.')
        result['continued_from'] = 'القيمة_الفعالة'
        names.add('الناتج')
        return result
    if node['op'] in ('REPEAT', 'REPEAT_POST', 'FOREACH') and node.get('body'):
        node['body'] = _resolve_continue(node['body'], names)
    elif node['op'] == 'SEQ':
        node['body'] = [_resolve_continue(x, names) for x in node['body']]
    return node


def _parse_part(part, names):
    if is_media(part): return parse_media(part, names)
    if ELSE_RE.match(part): return {'op': 'ELSE'}
    define = parse_define(part, names)
    if define: return define
    foreach = parse_foreach(part, names)
    if foreach: return foreach
    part = re.sub(r'^((?:اسأل|أسأل|اسال)\s*)\((.*)\)\s+في\s+([^\W\d]\w*)\s*$', r'\1(\2 في \3)', part)
    # Block and inline forms go through the same command parser.
    match = re.match(r'^(إذا|اذا|لو|وإلا إذا|والا اذا|كرر)\s+(.+?)\s*:?$', part)
    if match and not part.rstrip().endswith(':'):
        part = f'{match.group(1)}({match.group(2)})'
    normalized = natural_line(part) or part
    node = parse_statement(normalized, names)
    return _resolve_continue(node, names)


def _emit_sequence(nodes):
    """Lower statement ASTs into blocks; no exec-in-exec or static context."""
    lines = []
    for i, node in enumerate(nodes):
        code = codegen(node)
        lines.extend(code.splitlines())
        if node['op'] in ('IF', 'ELIF', 'ELSE') and i + 1 < len(nodes):
            lines.extend('    ' + line for line in _emit_sequence(nodes[i+1:]).splitlines())
            break
    return '\n'.join(lines)


def expand(src: str, initial_names=None):
    """Parse sentences -> statement AST -> lower blocks, preserving a source map.

    Natural statements are checked here. The old adapter is retained only for
    legacy constructs (functions, imports, assignment, collection literals).
    Context is deliberately absent from parsing: it lives in executed scopes.
    """
    global LAST_NAMES
    NOTES.clear(); SOURCE_MAP.clear()
    check_syntax(src)
    names = _copy_names(initial_names) if initial_names is not None else Names()
    names.first_def = {}
    lines = src.split('\n')
    declarations = {0: []}
    declaration_scopes = [(0, -1)]
    # Legacy declarations allow names to be recognized before translation.
    for no, raw in enumerate(lines, 1):
        body = strip_comment(raw.strip())
        if not body: continue
        width = len(raw.expandtabs(4)) - len(raw.expandtabs(4).lstrip())
        while len(declaration_scopes) > 1 and width <= declaration_scopes[-1][1]: declaration_scopes.pop()
        scope = declaration_scopes[-1][0]
        ident = r'[^\W\d]\w*'
        binding = re.match(rf'^(\(?\s*{ident}(?:\s*[،,]\s*{ident})*\s*\)?)\s*(?:[+\-*/%]?=)(?!=)', body)
        if binding:
            for label in re.findall(ident, binding.group(1)):
                try: _check_user_name(label)
                except DadError as e: e.line = no; raise
                declarations[scope].append(label)
        function = re.match(rf'^دالة\s+({ident})\s*\((.*?)\)', body)
        if function:
            labels = [function.group(1)] + [x.split('=')[0].strip() for x in re.split('[،,]', function.group(2)) if x.strip()]
            for label in labels:
                try: _check_user_name(label)
                except DadError as e: e.line = no; raise
            if scope == 0: names.functions.add(function.group(1))
        # Diagnose a reserved word in a binding before treating it as a separator.
        if re.match(r'^(?:اسأل|اسال)\s+كم\s+ثم\s*$', body) or re.match(r'^احفظ\s+.+\s+في\s+ثم\s*$', body) or re.search(r'^(?:عرّف|عرف)\s+.+\s+ياخذ\s+ثم(?:\s+و?يرجع\b|$)', body):
            e = DadError('«ثم» اسم محجوز في لغة الضاد — اختر اسمًا آخر.'); e.line = no; raise e
        define = re.match(r'^دالة\s+([^\W\d]\w*)', body)
        if define and scope == 0: names.functions.add(define.group(1))
        assign = re.match(r'^([^\W\d]\w*)\s*=(?!=)', body)
        if assign:
            try: _check_user_name(assign.group(1))
            except DadError as e: e.line = no; raise
            declarations[scope].append(assign.group(1))
            names.first_def.setdefault(key(assign.group(1)), no)
        for m in re.finditer(r'لكل\s+(.+?)\s+في\b', body):
            for name in re.findall(r'[^\W\d]\w*', m.group(1)):
                try: _check_user_name(name)
                except DadError as e: e.line = no; raise
                declarations[scope].append(name)
        if re.match(r'^(?:عرّف|عرف|دالة)\s+', body) and _has_block(lines, no):
            declarations[no] = []
            declaration_scopes.append((no, width))
    for label in declarations[0]: names.add(label)
    root_names = names
    scopes = [(-1, root_names)]
    out, asts = [], []
    for no, raw in enumerate(lines, 1):
        ind = raw[:len(raw)-len(raw.lstrip())].expandtabs(4)
        body = strip_comment(raw.strip())
        if not body:
            out.append(raw); SOURCE_MAP.append(no); continue
        while len(scopes) > 1 and len(ind) <= scopes[-1][0]: scopes.pop()
        names = scopes[-1][1]
        names.current_line = no
        if body.startswith('ثم ') or body.startswith('ثم\t'):
            body = body[2:].strip()
        parts = _split_then(body)
        parsed = []
        try:
            for pos, part in enumerate(parts):
                if not part:
                    raise DadError('في آخر السطر «ثم» وما بعدها أمر.' if pos == len(parts)-1 else 'فيه «ثم» زيادة — ما في أمر بين «ثم» و«ثم».')
                note = _command_ambiguity(part)
                if note: raise DadError(note)
                if re.fullmatch(r'(?:كرر|كرّر)\s*(?:\(\s*\))?\s*:?', part):
                    raise DadError('حدد كم مرة وشنو تبي تكرر.', ['كرر 3 مرات'])
                if re.match(r'^كم(?:\s|$)', part) and natural_line(part) is None:
                    raise DadError('«كم» كلمة سؤال وليست أمراً لوحدها. اكتب قبلها اسأل أو قول أو احسب.')
                node = _parse_part(part, names)
                if node is None:
                    if len(parts) > 1:
                        raise DadError(f'بعد «ثم» لازم يبدأ أمر معروف، وما فهمت «{part}».')
                    # The legacy adapter handles these lines only.
                    ma = re.match(r'^([^\W\d]\w*)\s*=\s*(.+)$', body)
                    fi = literal_fi_math(ma.group(2) if ma else body, names)
                    code = f'{ma.group(1)} = {fi}' if ma and fi is not None else (fi if fi is not None else body)
                    out.append(ind+code); SOURCE_MAP.append(no)
                    break
                if node['op'] == 'REPEAT' and not node.get('body'):
                    if len(parts) == 1 and _has_block(lines, no):
                        parsed.append(node); continue
                    if not parsed:
                        raise DadError('لا يوجد أمر سابق لتكراره.', ['قول هلا ثم كرر 3 مرات'])
                    prev = parsed.pop()
                    if prev['op'] in ('REPEAT', 'REPEAT_POST'):
                        raise DadError('«كرر» ما تكرر «كرر». اختر أمراً عادياً قبلها.')
                    if prev['op'] in ('IF', 'ELIF', 'ELSE', 'DEFINE', 'FOREACH'):
                        raise DadError('كرر أمرًا مكتملًا أو استخدم أسطرًا مزاحة للتكرار.')
                    node = {'op':'REPEAT_POST', 'count':node['count'], 'body':prev}
                parsed.append(node)
            else:
                code = _emit_sequence(parsed)
                out.extend(ind+x for x in code.splitlines()); SOURCE_MAP.extend([no]*len(code.splitlines()))
                asts.append((no, parsed))
                last = parsed[-1]
                if last['op'] == 'DEFINE' and last.get('return_expr') is None:
                    child = _copy_names(names)
                    for label in last['params'] + declarations.get(no, []): child.add(label)
                    scopes.append((len(ind), child))
                if last['op'] in ('IF', 'ELIF', 'ELSE') or (last['op'] in ('REPEAT', 'FOREACH') and not last.get('body')) or (last['op'] == 'DEFINE' and last.get('return_expr') is None):
                    if not _has_block(lines, no):
                        word = {'IF':'إذا','ELIF':'إذا','ELSE':'وإلا','FOREACH':'لكل','DEFINE':'عرّف','REPEAT':'كرر'}[last['op']]
                        raise DadError(f'الأسطر اللي تحت «{word}» لازم تكون مزاحة لداخل (اضغط Tab قبلها).', ['⇥ قول هلا'])
        except DadError as e:
            e.line = e.line or no; raise
    LAST_NAMES = root_names
    return '\n'.join(out), asts


# ============================================================================ دوال التشغيل (تنحقن في البرنامج)
def _dad_calc(v):
    """نتيجة «احسب» لازم تكون رقم — «سعود» × 4 ما تصير «سعودسعودسعودسعود» بصمت."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        shown = str(v)
        shown = shown[:25] + ("…" if len(shown) > 25 else "")
        raise ValueError(f"«احسب» لقت كلام مو رقم (طلع «{shown}») — تأكد إن القيم اللي تحسبها أرقام، مثل جواب «كم».")
    return _dad_num(v)


def _dad_num(v):
    return int(v) if isinstance(v, float) and v.is_integer() else (round(v, 6) if isinstance(v, float) else v)


def _dad_show(*vals):
    print(*[('صح' if v else 'خطأ') if isinstance(v, bool) else ('لاشيء' if v is None else _dad_num(v) if isinstance(v, (int, float)) else v) for v in vals])


def _dad_ask(prompt, numeric=False):
    ans = input(prompt + " ")
    if not sys.stdin.isatty() and os.environ.get("DAD_INTERACTIVE") != "1":
        print(ans)                                            # يبين الجواب تحت السؤال في لوحة النتائج
    if numeric:
        t = ans.translate(AR_DIGITS).strip()
        r = read_number(tokens(t), 0) if t else None
        if r and r[1] == len(tokens(t)):
            return r[0]
        me = math_expr(items_of(t, Names())) if t else None      # جواب فيه حساب: 2+5 / خمسة زائد اثنين
        if me:
            val = _dad_num(evaluate(me[0], {}, {}))
            print(f"= {val}")
            return val
        raise DadError(f"جواب «كم» يحتاج رقمًا؛ «{ans}» ليس رقمًا أو حسابًا واضحًا.")
    return ans


def _dad_explain(msg):
    print("🔍 تحليل (بدون تنفيذ): " + msg)


def _dad_calc_ask(g, l=None):
    text = input("وش تبي أحسب؟ ")
    if not sys.stdin.isatty() and os.environ.get("DAD_INTERACTIVE") != "1":
        print(text)
    names = Names()
    scope = {**g, **(l or {})}
    for k in scope:
        if re.match(r"[\u0600-\u06FF]", k):
            aliases = [k.replace("_", " ")] if "_" in k else None
            names.add(k, aliases=aliases)

    # داخل سؤال «احسب»، العلامة في بداية الجواب عملية على آخر قيمة فعالة:
    # 22 ثم -4 = 18. خارج هذا السؤال تبقى -4 عددًا سالبًا عاديًا.
    # ندعم الرموز الشائعة والرموز الطباعية × ÷ − مع أو بدون مسافة.
    stripped = text.strip()
    symbol_relative = {"+": "+", "-": "-", "−": "-", "*": "*", "×": "*", "/": "/", "÷": "/"}
    if stripped and stripped[0] in symbol_relative:
        if "_dad_active" not in scope:
            raise DadError("كتبت عملية على قيمة سابقة، لكن ما في قيمة سابقة — اسأل أو احسب أولًا.")
        op = symbol_relative[stripped[0]]
        rest = stripped[1:].strip()
        if not rest:
            raise DadError(f"العملية ناقصة — اكتب قيمة بعد «{stripped[0]}»، مثل: {stripped[0]}4.")
        a = parse_calc(rest, names)
        if a.get("op") != "CALC":
            raise DadError("هذا يحتاج بيانات ما عندي — عرّفها أول.")
        expr = f"القيمة_الفعالة {op} ({a['expr']})"
        val = _dad_calc(evaluate(expr, g, scope, continuing=True))
        print(f"= {val}")
        return val

    # وإذا كتب كلمة نسبية مثل «اطرح 4»، نطبق نفس القاعدة.
    tk = tokens(text)
    relative = {
        nk("زائد"): "+", nk("زايد"): "+", nk("زيد"): "+",
        nk("اطرح"): "-", nk("ناقص"): "-",
        nk("اضرب"): "*", nk("ضرب"): "*",
        nk("اقسم"): "/", nk("قسمة"): "/", nk("قسمه"): "/",
    }
    if tk and nk(tk[0]) in relative:
        if "_dad_active" not in scope:
            raise DadError("كتبت عملية على قيمة سابقة، لكن ما في قيمة سابقة — اسأل أو احسب أولًا.")
        rest = text.strip()[len(tk[0]):].strip()
        if not rest:
            raise DadError(f"العملية ناقصة — اكتب قيمة بعد «{tk[0]}»، مثل: {tk[0]} 4.")
        a = parse_calc(rest, names)
        if a.get("op") != "CALC":
            raise DadError("هذا يحتاج بيانات ما عندي — عرّفها أول.")
        expr = f"القيمة_الفعالة {relative[nk(tk[0])]} ({a['expr']})"
        val = _dad_calc(evaluate(expr, g, scope, continuing=True))
        print(f"= {val}")
        return val

    a = parse_calc(text, names)
    if a.get("op") != "CALC":
        raise DadError("هذا يحتاج بيانات ما عندي — عرّفها أول.")
    val = _dad_calc(evaluate(a["expr"], g, scope))
    print(f"= {val}")
    return val


def _dad_mean(x):
    x = list(x)
    return _dad_num(sum(x) / len(x)) if x else 0


def _dad_bool(v):
    return "صح" if v else "خطأ"


def _dad_now(kind):
    import datetime
    n = datetime.datetime.now()
    return n.strftime("%H:%M") if kind == "time" else n.strftime("%Y/%m/%d")


def _dad_note(msg):
    print("✎ " + msg, file=sys.stderr)


def _dad_media(kind, path):
    """يتحقق من الملف قبل ما يرسله للـIDE. أي مشكلة ← خطأ عربي واضح، مو صمت."""
    p = str(path if path is not None else "").strip().strip("«»\"' ")
    if not p:
        raise ValueError(f"حدد اسم ملف ال{MEDIA_AR[kind]}.")
    base = os.environ.get("DAD_OUT_DIR") or os.getcwd()
    full = p if os.path.isabs(p) else os.path.join(base, p)
    ext = os.path.splitext(p)[1].lower()
    if ext not in MEDIA_EXT[kind]:
        allowed = "، ".join(e[1:] for e in MEDIA_EXT[kind])
        if not ext:
            raise ValueError(f"«{p}» ما فيه نوع ملف — اكتب الاسم كامل مع النوع، مثل «{p}{MEDIA_EXT[kind][0]}».")
        raise ValueError(f"«{p}» مو ملف {MEDIA_AR[kind]} — الأنواع المقبولة: {allowed}.")
    if not os.path.isfile(full):
        raise FileNotFoundError(2, "No such file or directory", p)
    if os.environ.get("DAD_MEDIA") == "1":                # داخل ضاد IDE: يعرض/يشغّل فعلياً
        print(f"@@DAD_MEDIA@@{kind}|{os.path.abspath(full)}", flush=True)
    else:                                                 # برا الـIDE: نقول وش صار بوضوح
        icon = {"audio": "🔊", "video": "🎬", "image": "🖼"}[kind]
        print(f"{icon} {MEDIA_AR[kind]}: {p} — يشتغل داخل ضاد IDE.", flush=True)


def _dad_times(n):
    """عدد مرات كرر من متغير: لازم يكون رقم صحيح."""
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        t = str(n).translate(AR_DIGITS).strip()
        r = read_number(tokens(t), 0) if t else None
        if not r or r[1] != len(tokens(t)):
            raise DadError(f"عدد مرات «كرر» لازم يكون رقمًا، ولقيت «{n}»")
        n = r[0]
    if n < 0:
        raise DadError(f"عدد مرات «كرر» لا يكون سالبًا؛ لقيت «{n}».")
    if isinstance(n, float) and (not __import__('math').isfinite(n) or n != int(n)):
        raise DadError(f"عدد مرات «كرر» لازم يكون رقمًا صحيحًا، ولقيت «{n}»")
    return int(n)


def _dad_count(x):
    return len(x) if hasattr(x, "__len__") and not isinstance(x, str) else x


_SVG_N = [0]


def _dad_svg(svg):
    folder = os.environ.get("DAD_OUT_DIR") or os.getcwd()
    _SVG_N[0] += 1
    path = os.path.join(folder, f"رسمة_{_SVG_N[0]}.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"@@DAD_IMAGE@@{path}", flush=True)


def _dad_read(path):
    p = path if os.path.isabs(path) else os.path.join(os.environ.get("DAD_OUT_DIR") or os.getcwd(), path)
    with open(p, encoding="utf-8") as f:
        return f.read()


def _dad_write(path, value):
    p = path if os.path.isabs(path) else os.path.join(os.environ.get("DAD_OUT_DIR") or os.getcwd(), path)
    with open(p, "w", encoding="utf-8") as f:
        f.write(str(_dad_num(value) if isinstance(value, (int, float)) else value))
    print(f"✓ انحفظ في {os.path.basename(p)}")


RUNTIME = {"_dad_evaluate": evaluate, "_dad_media": _dad_media, "_dad_calc": _dad_calc, "_dad_times": _dad_times, "_dad_explain": _dad_explain, "_dad_calc_ask": _dad_calc_ask, "_dad_mean": _dad_mean, "_dad_bool": _dad_bool, "_dad_now": _dad_now, "_dad_note": _dad_note, "_dad_num": _dad_num, "_dad_show": _dad_show, "_dad_ask": _dad_ask, "_dad_count": _dad_count,
           "_dad_svg": _dad_svg, "_dad_read": _dad_read, "_dad_write": _dad_write}
