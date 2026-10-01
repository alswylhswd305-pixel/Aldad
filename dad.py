#!/usr/bin/env python3
"""
لغة الضاد — تكتب Python بالعربي.
الملف .ضاد يتحول لـ Python قبل التشغيل، فتاخذ كل مكتبات Python وكل قدرة الذكاء الاصطناعي.

الأوامر:
  python dad.py شغل   برنامج.ضاد      ← يحوله لـ Python ويشغله
  python dad.py حول   برنامج.ضاد      ← يحفظ نسخة برنامج.py
  python dad.py اعرض  برنامج.ضاد      ← يطبع نسخة Python
  python dad.py اقرأ  برنامج.py       ← يعرض كود Python بالعربي (للقراءة)
  python dad.py قاموس                 ← يطبع القاموس كامل
(وتشتغل بالإنجليزي بعد: run / py / read / dict)
"""
import io
import re
import sys
import tokenize
from pathlib import Path

# ----------------------------------------------------------------------------- قاموس لغة الضاد
# الكلمات المحجوزة (Python keywords)
KEYWORDS = {
    "لكل": "for", "في": "in", "طالما": "while", "إذا": "if", "وإلا_إذا": "elif", "وإلا": "else",
    "دالة": "def", "أرجع": "return", "صنف": "class", "استورد": "import", "من": "from", "باسم": "as",
    "حاول": "try", "عند_خطأ": "except", "أخيرا": "finally", "ارفع": "raise", "مع": "with",
    "تجاوز": "pass", "اكسر": "break", "و": "and", "أو": "or", "ليس": "not",
    "هو": "is", "صح": "True", "خطأ": "False", "لاشيء": "None", "دالة_سريعة": "lambda",
    "أعط": "yield", "عام": "global", "غير_محلي": "nonlocal", "تأكد": "assert", "احذف": "del",
    "غير_متزامن": "async", "انتظر": "await", "طابق": "match", "حالة": "case",
}
# الدوال الجاهزة (built-ins) وأسماء شائعة
BUILTINS = {
    "اطبع": "print", "أدخل": "input", "طول": "len", "مدى": "range", "افتح": "open",
    "صحيح": "int", "عشري": "float", "نص": "str", "منطقي": "bool", "قائمة": "list", "قاموس": "dict",
    "مجموعة": "set", "صف": "tuple", "نوع": "type", "من_نوع": "isinstance", "مرتب": "sorted",
    "معكوس": "reversed", "رقم": "enumerate", "اربط": "zip", "مجموع": "sum", "أصغر": "min",
    "أكبر": "max", "مطلق": "abs", "قرب": "round", "طبق": "map", "رشح": "filter", "أي": "any",
    "الكل": "all", "استثناء": "Exception", "نفسه": "self", "ترميز": "encoding",
    "حرف_من_رقم": "chr", "رقم_الحرف": "ord", "قوة": "pow", "قسمة_وباقي": "divmod", "التالي": "next",
    "كرر": "iter", "مساعدة": "help", "يملك": "hasattr", "هات_خاصية": "getattr", "حط_خاصية": "setattr",
    "الأب": "super", "كائن": "object", "نسق_قيمة": "format", "قابل_للاستدعاء": "callable", "خصائص": "dir",
    "خروج": "exit", "بايتات": "bytes",
    "خطأ_قيمة": "ValueError", "خطأ_نوع": "TypeError", "خطأ_مفتاح": "KeyError", "خطأ_فهرس": "IndexError",
    "ملف_غير_موجود": "FileNotFoundError", "قسمة_على_صفر": "ZeroDivisionError", "إيقاف_يدوي": "KeyboardInterrupt",
    "خطأ_اسم": "NameError", "خطأ_خاصية": "AttributeError",
    # مكتبات شائعة
    "عشوائي": "random", "وقت": "time", "رياضيات": "math", "نظام": "os", "جيسون": "json",
    "تاريخ_ووقت": "datetime", "مسارات": "pathlib", "طلبات": "requests", "نظام_بايثون": "sys",
    # معاملات شائعة داخل الأقواس
    "نهاية": "end", "فاصل": "sep", "مفتاح": "key", "عكسي": "reverse", "وضع": "mode",
}
# الدوال اللي تجي بعد النقطة (methods) — تُترجم فقط بعد "."
METHODS = {
    "أضف": "append", "مدد": "extend", "أدرج": "insert", "أزل": "remove", "اسحب": "pop",
    "رتب": "sort", "عد": "count", "موقع": "index", "قسم": "split", "اجمع": "join",
    "استبدل": "replace", "قص": "strip", "صغر": "lower", "كبر": "upper", "ابحث": "find",
    "يبدأ_ب": "startswith", "ينتهي_ب": "endswith", "نسق": "format", "مفاتيح": "keys",
    "قيم": "values", "عناصر": "items", "هات": "get", "حدث": "update", "اقرأ": "read",
    "اقرأ_الأسطر": "readlines", "اكتب": "write", "أغلق": "close",
    "اعكس": "reverse", "انسخ": "copy", "امسح": "clear", "ضم": "add", "قسم_أسطر": "splitlines",
    "رقمي": "isdigit", "حروفي": "isalpha", "عنون": "title", "وسط": "center", "أصفار_يسار": "zfill",
    "عدد_عشوائي": "randint", "اختر": "choice", "اخلط": "shuffle", "نم": "sleep", "الآن": "now",
    "جذر": "sqrt", "أرضية": "floor", "سقف": "ceil", "حمل": "load", "حمل_نص": "loads", "افرغ": "dump",
    "افرغ_نص": "dumps", "موجود": "exists", "مسار_كامل": "join", "قائمة_الملفات": "listdir",
    "اصنع_مجلد": "makedirs", "اقرأ_نص": "read_text", "اكتب_نص": "write_text", "مسار": "path",
    "هات_صفحة": "get", "جيسون_الرد": "json", "رمز_الحالة": "status_code",
}
# مقارنات بالكلام (تصير رموز)
OPERATORS = {
    "أكبر_من": ">", "أصغر_من": "<", "يساوي": "==", "لا_يساوي": "!=",
    "أكبر_أو_يساوي": ">=", "أصغر_أو_يساوي": "<=",
    "زائد": "+", "ناقص": "-", "ضرب": "*", "قسمة": "/",          # الحساب بالكلام في أي سطر: س = ص ضرب 2
}
AR_TO_PY = {**KEYWORDS, **BUILTINS}
PY_TO_AR = {v: k for k, v in AR_TO_PY.items()}
METHOD_PY_TO_AR = {}
for _ar, _py in METHODS.items():
    METHOD_PY_TO_AR.setdefault(_py, _ar)   # أول كلمة عربية هي المعتمدة للقراءة

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ARABIC_PUNCT = {"،": ",", "؛": ";"}



BLOCK_STARTS = ("إذا", "وإلا_إذا", "طالما", "لكل", "وإلا", "حاول", "عند_خطأ", "أخيرا", "مع", "دالة", "صنف")


def _split_top(line: str, word: str):
    """يقسم السطر على كلمة (مثل ثم) بشرط تكون خارج النصوص وكلمة كاملة."""
    parts, cur, i, quote = [], [], 0, None
    n = len(line)
    while i < n:
        ch = line[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and i + 1 < n: cur.append(line[i + 1]); i += 2; continue
            if ch == quote: quote = None
            i += 1; continue
        if ch in "\"'": quote = ch; cur.append(ch); i += 1; continue
        if ch == "#": cur.append(line[i:]); break
        if line.startswith(word, i):
            before = line[i - 1] if i else " "
            after = line[i + len(word)] if i + len(word) < n else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                parts.append("".join(cur)); cur = []; i += len(word); continue
        cur.append(ch); i += 1
    parts.append("".join(cur))
    return parts


def _phrase(seg: str) -> str:
    """جملة وحدة: قل / أضف ... إلى ..."""
    s = seg.strip()

    # «اسأل» اختصار طبيعي وثابت لـ input بدون ذكاء اصطناعي.
    # ما ندخل Regex الخاص فيه إلا إذا الكلمة موجودة؛ يحافظ على سرعة بقية الأسطر.
    if "اسأل" in s:
        #   اسأل «كم عمرك؟» في العمر   -> العمر = أدخل("كم عمرك؟")
        #   الاسم = اسأل «اسمك؟»       -> الاسم = أدخل("اسمك؟")
        #   اسأل «اضغط Enter»          -> أدخل("اضغط Enter")
        m = re.match(r"^([\w\u0600-\u06FF_]+)\s*=\s*اسأل\s+(.+)$", s)
        if m:
            name, prompt = m.group(1), m.group(2).strip()
            if not (prompt[:1] in "\"'«"):
                prompt = '"' + prompt.replace('"', "'") + '"'
            return f"{name} = _dad_ask({prompt})"
        m = re.match(r"^اسأل\s+(.+?)\s+في\s+([\w\u0600-\u06FF_]+)$", s)
        if m:
            prompt, name = m.group(1).strip(), m.group(2)
            if not (prompt[:1] in "\"'«"):
                prompt = '"' + prompt.replace('"', "'") + '"'
            return f"{name} = _dad_ask({prompt})"
        m = re.match(r"^اسأل\s+(.+)$", s)
        if m:
            prompt = m.group(1).strip()
            if not (prompt[:1] in "\"'«"):
                prompt = '"' + prompt.replace('"', "'") + '"'
            return f"_dad_ask({prompt})"

    m = re.match(r"^(?:قل|قول)\s+(?!\()(.+)$", s)
    if m:
        what = m.group(1).strip()
        plain = not (what[:1] in "\"'«" or re.search(r"[()\[\]{}=+\-*/<>,،.]", what))
        if plain and (" " in what or what not in _CURRENT_NAMES):
            what = '"' + what.replace('"', "'") + '"'      # قول هلا والله  ←  اطبع("هلا والله")
        return f"اطبع({what})"
    m = re.match(r"^(?:قل|قول)\s*(\(.*\))$", s)
    if m: return "اطبع" + m.group(1)
    m = re.match(r"^(?:ارسم لي|ارسملي|ارسم|رسم)\s+(?!\()(.+)$", s)
    if m:
        what = m.group(1).strip()
        if not (what[:1] in "\"'«" or re.search(r"[()\[\]{}=+]", what)):
            what = '"' + what.replace('"', "'") + '"'          # رسم شمس فوق بحر  ←  ارسم("شمس فوق بحر")
        return f"ارسم({what})"
    m = re.match(r"^أضف\s+(.+?)\s+إلى\s+([\w\u0600-\u06FF_.]+)$", s)
    if m: return f"{m.group(2)}.أضف({m.group(1)})"
    return s


_CURRENT_NAMES = set()


def humanize(src: str) -> str:
    """قواعد الكلام: كرر N مرات / ثم / قل / أضف ... إلى."""
    _CURRENT_NAMES.clear(); _CURRENT_NAMES.update(_user_names(src))
    out = []
    for line in src.split("\n"):
        ind = line[: len(line) - len(line.lstrip())]
        body = line.strip()
        # «كرر اسأل كم عمرك مرتين» — صيغة كلام طبيعية بدون أقواس.
        # نحوّلها للصيغة الحديثة قبل ما تمر على الضاد الكلاسيكية.
        if re.match(r"^كرر\s+.+\s+مرتين\s*$", body):
            out.append(ind + "كرر(" + body[len("كرر"):].strip() + ")")
            continue
        m = re.match(r"^كرر\s+(.+?)\s+(?:مرات|مرة)\s*:\s*$", body)
        if m:
            out.append(f"{ind}لكل _ في مدى({m.group(1)}):"); continue
        if not body or body.startswith("#"):
            out.append(line); continue
        parts = _split_top(body, "ثم")
        first = parts[0].strip()
        if len(parts) > 1 and first.startswith(BLOCK_STARTS) and not first.rstrip().endswith(":"):
            head, rest = first + ":", parts[1:]            # إذا الشرط ثم ...  =  إذا الشرط: ...
            out.append(ind + head + " " + "; ".join(_phrase(p) for p in rest))
        else:
            out.append(ind + "; ".join(_phrase(p) for p in parts))
    return "\n".join(out)



# ----------------------------------------------------------------------------- التصحيح التلقائي
# يقارن الكلمات بشكلها بدون نقاط (ع/غ، ب/ت/ث/ن/ي، ج/ح/خ، ف/ق، ة/ه، أ/إ/آ/ا…) ثم بفرق حرف واحد.
_SKELETON = str.maketrans({
    "ب": "ٮ", "ت": "ٮ", "ث": "ٮ", "ن": "ٮ", "ي": "ٮ", "ى": "ى", "ئ": "ٮ",
    "ج": "ح", "خ": "ح", "ذ": "د", "ز": "ر", "ش": "س", "ض": "ص", "ظ": "ط", "غ": "ع",
    "ق": "ڡ", "ف": "ڡ", "ة": "ه", "أ": "ا", "إ": "ا", "آ": "ا", "ؤ": "و", "ـ": "",
})
HUMAN_WORDS = ["قل", "قول", "اسأل", "احسب", "كمل", "أكمل", "كرر", "مرات", "ثم", "أضف", "إلى", "ارسم", "رسم"]


def _skel(w: str) -> str:
    return w.translate(_SKELETON)


def _dist1(a: str, b: str) -> bool:
    if a == b: return True
    if abs(len(a) - len(b)) > 1: return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    if len(a) > len(b): a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


_KNOWN = None


def _known_words():
    global _KNOWN
    if _KNOWN is None:
        words = list(KEYWORDS) + list(BUILTINS) + list(OPERATORS) + HUMAN_WORDS
        _KNOWN = {}
        for w in words:
            _KNOWN.setdefault(_skel(w), w)
        _KNOWN = (_KNOWN, words)
    return _KNOWN


def _user_names(src: str) -> set:
    names = set()
    for pat in (r"(?m)^\s*([^\W\d]\w*)\s*=(?!=)", r"اسأل\s+.+?\s+في\s+([\w\u0600-\u06FF_]+)(?:\s|$)",
                r"لكل\s+(.+?)\s+في\b", r"دالة\s+\w+\s*\(([^)]*)\)", r"def\s+\w+\s*\(([^)]*)\)",
                r"دالة\s+(\w+)", r"def\s+(\w+)", r"صنف\s+(\w+)", r"باسم\s+(\w+)", r"استورد\s+(\w+)"):
        for m in re.finditer(pat, src):
            names.update(re.findall(r"[^\W\d]\w*", m.group(1)))
    return names


def _command_spot(src, i, n):
    line_start = src.rfind("\n", 0, i) + 1
    before = src[line_start:i].strip()
    after = src[i + n:i + n + 2].lstrip()
    if src[i:i + 2] == "ال":                       # كلمات «ال...» غالباً أسماء — تتصحح بس إذا بعدها قوس
        return after.startswith("(")
    return before in ("", "ثم") or before.endswith((" ثم", ":")) or after.startswith("(")


def autocorrect(src: str):
    """يرجع (النص المصحح، قائمة التصحيحات). ما يلمس النصوص ولا التعليقات ولا أسماءك."""
    by_skel, words = _known_words()
    exact = set(words) | set(METHODS)
    mine = _user_names(src)
    fixes, out, i, n, quote = [], [], 0, len(src), None
    line = 1
    free_text = False          # بعد قل/قول/رسم بدون قوس: الباقي كلامك، ما يتصحح لين «ثم» أو آخر السطر
    while i < n:
        ch = src[i]
        if ch == "\n": line += 1; free_text = False
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n: out.append(src[i + 1]); i += 2; continue
            if src.startswith(quote, i): quote = None
            i += 1; continue
        if ch == "#":
            j = src.find("\n", i); j = n if j == -1 else j
            out.append(src[i:j]); i = j; continue
        if ch in "\"'«":
            quote = "»" if ch == "«" else ch; out.append(ch); i += 1; continue
        m = re.match(r"[^\W\d_][\w]*", src[i:]) if ch.isalpha() else None
        if m and "\u0600" <= ch <= "\u06FF" and free_text and m.group(0) != "ثم":
            out.append(m.group(0)); i += len(m.group(0)); continue
        if m and "\u0600" <= ch <= "\u06FF":
            w = m.group(0); fix = None
            if w == "ثم": free_text = False
            after_dot = i > 0 and src[i - 1] == "."
            attached = w[:1] in ("و", "ف") and (w[1:] in exact or _skel(w[1:]) in by_skel)   # وليس / فاطبع = حرف ملصوق
            if attached and w[1:] not in exact:
                fixed_rest = by_skel.get(_skel(w[1:]))
                if fixed_rest: fixes.append((line, w, w[0] + fixed_rest)); out.append(w[0] + fixed_rest); i += len(w); continue
            if not attached and w not in exact and w not in mine and not after_dot and len(w) >= 2:
                sk = _skel(w)
                if sk in by_skel:
                    fix = by_skel[sk]
                elif len(w) >= 4 and _command_spot(src, i, len(w)):
                    # فرق حرف كامل يُصحَّح بس مكان الأمر (أول السطر، بعد ثم، أو قبل قوس) — «الباقي» ما تصير «التالي»
                    cands = [k for k in words if len(k) >= 3 and _dist1(sk, _skel(k))]
                    if len(cands) == 1: fix = cands[0]
            final = fix if (fix and fix != w) else w
            if final != w:
                fixes.append((line, w, final))
            out.append(final)
            i += len(w)
            if final in ("قل", "قول", "اسأل", "رسم", "ارسم"):
                rest = src[i:src.find("\n", i) if src.find("\n", i) != -1 else n].lstrip()
                if rest and rest[0] != "(":
                    free_text = True
            continue
        out.append(ch); i += 1
    return "".join(out), fixes


# ----------------------------------------------------------------------------- تجهيز النص
def normalize_outside_strings(src: str) -> str:
    """الفاصلة العربية والأرقام العربية تتحول، بس خارج النصوص والتعليقات."""
    out, i, n = [], 0, len(src)
    quote = None
    while i < n:
        ch = src[i]
        if quote:                                   # داخل نص
            if ch == "\\":
                out.append(src[i:i + 2]); i += 2; continue
            if src.startswith(quote, i):
                out.append(quote); i += len(quote); quote = None; continue
            out.append(ch); i += 1; continue
        if ch == "#":                               # تعليق لين آخر السطر
            j = src.find("\n", i); j = n if j == -1 else j
            out.append(src[i:j]); i = j; continue
        if ch == "«":                               # «نص عربي» = "نص عربي"
            j = src.find("»", i + 1)
            if j != -1 and "\n" not in src[i:j]:
                out.append('"' + src[i + 1:j].replace('"', '\\"') + '"'); i = j + 1; continue
        if ch in "\"'":
            quote = ch * 3 if src.startswith(ch * 3, i) else ch
            out.append(quote); i += len(quote); continue
        out.append(ARABIC_PUNCT.get(ch, ch.translate(ARABIC_DIGITS))); i += 1
    return "".join(out)


def _unbalanced_bracket_error(src: str):
    from aldad_syntax import DadError, check_syntax
    try: check_syntax(src)
    except DadError as error: return error
    return DadError("فيه قوس أو نص ناقص في البرنامج؛ راجع آخر سطر.")


def _translate(src: str, names: dict, methods: dict) -> str:
    lines = src.splitlines(keepends=True)
    edits = []                                      # (row, col_start, col_end, new)
    prev = None
    try:
        tokens_list = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        raise _unbalanced_bracket_error(src) from None
    for tok in tokens_list:
        if tok.type == tokenize.NAME:
            after_dot = prev is not None and prev.type == tokenize.OP and prev.string == "."
            new = methods.get(tok.string) if after_dot else names.get(tok.string)
            if not new and not after_dot and names is AR_TO_PY:
                t = tok.string
                if t in OPERATORS:
                    new = OPERATORS[t]
                elif t[:1] in ("و", "ف") and t not in AR_TO_PY and (t[1:] in KEYWORDS or (t[0] == "ف" and t[1:] == "اطبع")):
                    new = ("and " if t[0] == "و" else "") + AR_TO_PY[t[1:]]      # وإذا / وليس / فاطبع — مو «وصف»
            if new:
                edits.append((tok.start[0], tok.start[1], tok.end[1], new))
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            prev = tok
    for row, a, b, new in sorted(edits, key=lambda e: (e[0], -e[1])):
        line = lines[row - 1]
        lines[row - 1] = line[:a] + new + line[b:]
    return "".join(lines)


LAST_FIXES = []


def to_python(dad_src: str, initial_names=None) -> str:
    import vnext
    dad_src, _ = vnext.expand(dad_src.lstrip("\ufeff"), initial_names)
    fixed, fixes = autocorrect(normalize_outside_strings(dad_src))
    LAST_FIXES[:] = fixes
    return _translate(humanize(fixed), AR_TO_PY, METHODS)


def to_arabic(py_src: str) -> str:
    return _translate(py_src, PY_TO_AR, METHOD_PY_TO_AR)



# ----------------------------------------------------------------------------- ارسم (بالذكاء المحلي)
def _lm_json(base, path, body=None, timeout=180):
    import json, urllib.request, urllib.parse, urllib.error
    url = base.rstrip("/") + path
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host not in ("localhost", "::1") and not host.startswith("127."):
        raise RuntimeError("ارسم يتصل بجهازك فقط (localhost).")
    data = None if body is None else json.dumps(body).encode("utf-8")
    for attempt in range(2):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as e:
            refused = isinstance(getattr(e, "reason", None), ConnectionRefusedError) or "10061" in str(e) or "refused" in str(e).lower()
            if not refused:
                raise
            if attempt == 0 and _start_lm_studio():
                continue
            raise RuntimeError("LM Studio مطفي. افتحه، ومن تبويب Developer حوّل Status إلى Running، "
                               "وتأكد إن فيه موديل محمّل — وبعدها اضغط ▶ مرة ثانية.") from None


def _start_lm_studio() -> bool:
    """يحاول يشغّل سيرفر LM Studio بأداة lms الرسمية إذا كانت مثبتة."""
    import os, shutil, subprocess, time
    exe = shutil.which("lms") or os.path.join(os.path.expanduser("~"), ".lmstudio", "bin", "lms.exe")
    if not exe or not os.path.exists(exe):
        return False
    try:
        print("⏳ LM Studio مطفي — أحاول أشغّله…", file=sys.stderr, flush=True)
        _TRUSTED[0] = True
        subprocess.run([exe, "server", "start"], capture_output=True, timeout=40,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        time.sleep(2)
        return True
    except Exception:
        return False
    finally:
        _TRUSTED[0] = False


def _clean_svg(text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?(?:</think>|$)", "", text or "")
    m = re.search(r"<svg[\s\S]*?</svg>", text, re.I)
    if not m:
        raise RuntimeError("الموديل ما رجّع رسمة. جرّب وصف أبسط أو موديل أقوى.")
    svg = m.group(0)
    svg = re.sub(r"<script[\s\S]*?</script>", "", svg, flags=re.I)
    svg = re.sub(r"<foreignObject[\s\S]*?</foreignObject>", "", svg, flags=re.I)
    svg = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg, flags=re.I)
    svg = re.sub(r"(href\s*=\s*[\"'])\s*(?:javascript|https?):[^\"']*", r"\1#", svg, flags=re.I)
    if "xmlns=" not in svg[:200]:
        svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return svg


def draw_svg(description: str, previous_svg: str = "", base: str = "", model: str = "") -> str:
    """يطلب من الموديل المحلي رسمة SVG (أو يعدّل رسمة سابقة) ويرجعها نظيفة."""
    import os
    base = base or os.environ.get("DAD_LM_BASE", "http://127.0.0.1:1234/v1")
    model = model or os.environ.get("DAD_MODEL", "")
    ids = [m.get("id") for m in _lm_json(base, "/models", timeout=8).get("data", []) if m.get("id") and "embed" not in m.get("id").lower()]
    if not ids:
        raise RuntimeError("ما في موديل محمّل في LM Studio.")
    if model not in ids:
        model = next((i for i in ids if "coder" in i.lower()), ids[0])
    no_think = " /no_think" if "qwen3" in model.lower() else ""
    system = ("You are an illustrator who draws with SVG code. Output ONLY one complete <svg> element with "
              "viewBox=\"0 0 512 512\". Flat, colorful, clear shapes; a full background; recognizable subject. "
              "No text unless asked. No scripts, no external images, no <foreignObject>.")
    if previous_svg:
        user = f"Here is the current drawing:\n{previous_svg}\n\nModify it: {description}\nReturn the full updated SVG.{no_think}"
    else:
        user = f"Draw: {description}{no_think}"
    r = _lm_json(base, "/chat/completions", {"model": model, "temperature": 0.4, "max_tokens": 6000, "stream": False,
                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}, timeout=300)
    return _clean_svg(r["choices"][0]["message"]["content"])


_DRAW_COUNT = [0]


def ارسم(وصف):
    """Legacy calls use the same deterministic shapes as natural statements."""
    import vnext
    return vnext._dad_svg(vnext.scene_svg(vnext.parse_draw(str(وصف))))


# ----------------------------------------------------------------------------- أوامر السطر
ERRORS_AR = {
    "NameError": "اسم غير معروف — غالباً كتبت اسم متغير أو دالة غلط، أو استخدمته قبل ما تعرّفه.",
    "SyntaxError": "خطأ في كتابة الجملة — ناقص قوس أو نقطتين «:» أو علامة تنصيص.",
    "IndentationError": "خطأ في المسافات أول السطر — الأسطر اللي تحت «إذا/لكل/دالة» لازم تكون مزاحة لداخل.",
    "TypeError": "نوع غلط — مثلاً تجمع رقم مع نص. حوّل واحد منهم بـ نص() أو صحيح().",
    "ValueError": "قيمة غلط — مثلاً تحوّل «abc» لرقم بـ صحيح().",
    "FileNotFoundError": "الملف مو موجود — تأكد من الاسم ومكان الملف.",
    "KeyError": "المفتاح مو موجود في القاموس — استخدم .هات() بدل الأقواس المربعة.",
    "IndexError": "رقم العنصر أكبر من طول القائمة.",
    "ZeroDivisionError": "قسمة على صفر — ما ينفع تقسم على صفر.",
    "UnicodeDecodeError": "مشكلة ترميز — افتح الملف بـ ترميز=\"utf-8\".",
    "ModuleNotFoundError": "المكتبة مو مثبتة — ثبتها بـ pip install.",
}


TYPE_AR = {"list": "قائمة", "str": "نص", "int": "رقم صحيح", "float": "رقم عشري", "dict": "قاموس", "NoneType": "لاشيء",
           "bool": "صح/خطأ", "tuple": "صف", "set": "مجموعة", "function": "دالة"}


class DadSafeError(PermissionError):
    """الوضع الآمن منع عملية."""


_TRUSTED = [False]


def _install_safe_mode(folder: str):
    """يمنع البرنامج من: مسح/نقل الملفات، الكتابة برا مجلده، تشغيل برامج ثانية، والنت (إلا LM Studio المحلي)."""
    import os, tempfile
    allowed = [os.path.realpath(folder), os.path.realpath(tempfile.gettempdir())]
    local = ("127.", "localhost", "::1")

    def inside(p):
        try:
            rp = os.path.realpath(os.fspath(p))
        except Exception:
            return True
        return any(rp == d or rp.startswith(d + os.sep) for d in allowed)

    def hook(event, args):
        if _TRUSTED[0]:
            return
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
            if writing and path is not None and not isinstance(path, int) and not inside(path):
                raise DadSafeError(f"الوضع الآمن منع الكتابة برا مجلد برنامجك: {os.path.basename(str(path))}")
        elif event in ("os.remove", "os.unlink", "os.rmdir", "shutil.rmtree"):
            raise DadSafeError(f"الوضع الآمن منع مسح: {os.path.basename(str(args[0]))}")
        elif event in ("os.rename", "os.replace", "shutil.move"):
            raise DadSafeError("الوضع الآمن منع نقل أو إعادة تسمية ملفات")
        elif event in ("os.system", "subprocess.Popen", "os.exec", "os.spawn", "os.startfile", "os.posix_spawn"):
            raise DadSafeError("الوضع الآمن منع تشغيل برامج ثانية من داخل برنامجك")
        elif event == "socket.connect":
            addr = args[1] if len(args) > 1 else None
            host = str(addr[0]) if isinstance(addr, tuple) and addr else str(addr)
            if not host.startswith(local):
                raise DadSafeError("الوضع الآمن منع الاتصال بالإنترنت")
        elif event == "urllib.Request":
            url = str(args[0]) if args else ""
            if not re.match(r"https?://(127\.|localhost|\[::1\])", url):
                raise DadSafeError("الوضع الآمن منع الاتصال بالإنترنت")

    sys.addaudithook(hook)


def _safe_enabled(src: str) -> bool:
    import os
    if os.environ.get("DAD_SAFE", "1") == "0":
        return False
    head = "\n".join(src.splitlines()[:5])
    return not re.search(r"#\s*(?:الوضع[_ ]الآمن\s*:\s*(?:لا|مطفي|off)|غير[_ ]آمن)", head)


def arabic_error(e) -> str:
    """الخطأ بالعربي بالكامل — بدون أسماء إنجليزية."""
    name, msg = type(e).__name__, str(e)
    from aldad_syntax import DadError
    if isinstance(e, DadError):
        return msg
    tr = lambda t: TYPE_AR.get(t, t)
    m = re.search(r"name '(.+?)' is not defined", msg)
    if name == "NameError" and m and m.group(1) == "الناتج":
        return "ما في «الناتج» لين الحين في هالمكان — احسب شي قبله. (الحساب اللي داخل دالة يبقى داخلها ولا يطلع منها.)"
    if name == "NameError" and m:
        return f"«{m.group(1)}» غير معروف — غالباً مكتوب غلط، أو استخدمته قبل ما تعرّفه أو تسأل عنه."
    if name == 'UnboundLocalError':
        return "القيمة غير معرّفة في هذا السياق؛ عرّفها أو اسأل عنها قبل استخدامها."
    if name in ("SyntaxError",) and getattr(e, "text", None) and re.match(r"\s*(إذا|اذا|لكل|طالما|دالة|وإلا|والا|وإلا_إذا|حاول|عند_خطأ|صنف|مع|if|for|while|def|else|elif|try|except|class|with)\b", e.text or "") and not (e.text or "").rstrip().endswith(":"):
        return "ناقص نقطتين «:» في آخر السطر — أسطر إذا/لكل/طالما/دالة تنتهي بـ «:»، أو استخدم إذا(...) بالأقواس."
    if name in ("SyntaxError",):
        return "خطأ في كتابة السطر — ناقص قوس ( ) أو نقطتين «:» أو علامة تنصيص، أو فيه كلمة مو في مكانها."
    if name in ("IndentationError", "TabError"):
        return "خطأ في المسافات أول السطر — الأسطر اللي تحت إذا/لكل/كرر/دالة لازم تكون مزاحة لداخل، وبنفس المسافة."
    m = re.search(r"unsupported operand type\(s\) for (.+?): '(\w+)' and '(\w+)'", msg)
    if m:
        return f"ما ينفع تسوي «{m.group(1)}» بين {tr(m.group(2))} و{tr(m.group(3))} — حوّل واحد منهم أول (صحيح( ) أو نص( ))."
    m = re.search(r'can only concatenate (\w+) \(not "(\w+)"\)', msg)
    if m:
        return f"ما ينفع تلصق {tr(m.group(1))} مع {tr(m.group(2))} — حوّل الرقم لنص بـ نص( )."
    if name == "ZeroDivisionError":
        return "قسمة على صفر — ما ينفع تقسم على صفر."
    m = re.search(r"No such file or directory: '(.+?)'", msg)
    if name == "FileNotFoundError":
        return f"الملف «{m.group(1) if m else ''}» مو موجود — تأكد من الاسم ومكانه."
    if name == "KeyError":
        return f"المفتاح {msg} مو موجود في القاموس."
    if name == "IndexError":
        return "رقم العنصر أكبر من طول القائمة."
    m = re.search(r"invalid literal for int\(\) with base 10: '(.*)'", msg)
    if m:
        return f"«{m.group(1)}» مو رقم صحيح."
    m = re.search(r"could not convert string to float: '(.*)'", msg)
    if m:
        return f"«{m.group(1)}» مو رقم."
    m = re.search(r"No module named '(.+?)'", msg)
    if m:
        return f"المكتبة «{m.group(1)}» مو مثبتة — ثبتها بـ pip install {m.group(1)}"
    m = re.search(r"'(\w+)' object has no attribute '(.+?)'", msg)
    if m:
        attr = m.group(2)
        ar_attr = next((a for a, p in METHODS.items() if p == attr), None)
        if attr == "append":
            return f"«أضف» تشتغل مع القوائم بس، وهذا {tr(m.group(1))}. سوّها قائمة أول، مثل: السلة = []"
        if ar_attr:
            return f"«{ar_attr}» مو أمر يصلح مع {tr(m.group(1))}."
        return f"هذا الأمر ما يصلح مع {tr(m.group(1))}."
    m = re.search(r"'(\w+)' object is not callable", msg)
    if m:
        return f"هذا {tr(m.group(1))}، مو دالة — لا تحط بعده أقواس."
    m = re.search(r"'(\w+)' object is not iterable", msg)
    if m:
        return f"ما ينفع تمر على {tr(m.group(1))} بـ لكل — لازم تكون قائمة."
    if name == "EOFError":
        return "البرنامج يسأل سؤال وما وصله جواب."
    if name == "ValueError" and re.search(r"[\u0600-\u06FF]", msg):
        return msg
    if name == "RecursionError":
        return "الدالة تنادي نفسها بلا نهاية."
    if name == "KeyboardInterrupt":
        return "انوقف البرنامج."
    if name == "MemoryError":
        return "البرنامج استهلك ذاكرة أكثر من اللازم."
    if name == "TypeError":
        return "نوع غلط — القيم اللي استخدمتها ما تنفع مع بعض هني."
    if name == "ValueError":
        return "قيمة غلط — القيمة ما تناسب العملية."
    if isinstance(e, DadSafeError):
        return msg + " — إذا تبي تسمح، حط أول سطر: # الوضع_الآمن: لا"
    if name == 'PermissionError':
        return "تعذّر الوصول للملف؛ راجع المكان وصلاحية القراءة أو الكتابة."
    if name in ('UnicodeError', 'UnicodeDecodeError'):
        return "تعذّرت قراءة النص؛ احفظ الملف بترميز UTF-8."
    if name == 'OSError':
        return "تعذّر فتح الملف أو حفظه؛ راجع الاسم والمكان."
    return "تعذّر تنفيذ هذا الأمر. راجع القيم وطريقة كتابة السطر."


def run_ui(path: Path, src: str):
    """برنامج واجهة ← صفحة HTML جنب البرنامج."""
    import os, ui, vnext
    try:
        prog = ui.compile_ui(src)
    except vnext.DadError as e:
        print("⚠ " + e.arabic(), file=sys.stderr); sys.exit(1)
    folder = os.environ.get("DAD_OUT_DIR") or str(path.resolve().parent)
    safe = re.sub(r'[\\/:*?"<>|]', "", prog.title) or "برنامجي"
    out = Path(folder) / f"{safe}.html"
    out.write_text(ui.to_html(prog, os.environ.get("DAD_LM_BASE", "http://127.0.0.1:1234/v1"), os.environ.get("DAD_MODEL", "")), encoding="utf-8")
    kinds = {"field": "حقل", "button": "زر", "label": "نص", "editor": "محرر", "box": "صندوق", "chat": "محادثة", "list": "قائمة"}
    print(f"✓ جهز برنامج «{prog.title}»: " + "، ".join(f"{kinds[w['kind']]} {w['name']}" for w in prog.widgets))
    print(f"@@DAD_APP@@{out}", flush=True)


def _looks_like_plain_text_line(line):
    """سطر كلام عادي: أول كلمة مو أمر ولا كلمة ضاد معروفة، وما فيه أقواس ولا = ولا نقطتين."""
    import vnext
    t = line.strip()
    if not t or re.search(r"[(=:\[\]{}#]", t):
        return False
    m = re.match(r"[^\W\d_][\w]*", t)
    if not m:
        return False
    known = set(vnext.COMMANDS) | {vnext.nk(k) for k in KEYWORDS} | {vnext.nk(k) for k in BUILTINS} \
        | {vnext.nk(w) for w in ("عرّف", "عرف", "برنامج", "افتح", "أضف", "اضف", "عند", "شخصية", "ثم", "كرر", "لكل", "كل", "لو")}
    return vnext.nk(m.group(0)) not in known


def run(path: Path):
    import vnext, os, ui
    src = path.read_text(encoding="utf-8")
    if ui.is_ui(src):
        return run_ui(path, src)
    try:
        code = to_python(src)
    except vnext.DadError as e:
        print("⚠ " + e.arabic(), file=sys.stderr); sys.exit(1)
    for ln, wrong, right in LAST_FIXES:
        print(f"✎ صححت «{wrong}» ← «{right}» (السطر {ln})", file=sys.stderr)
    for ln, note in vnext.NOTES:
        print(f"{note} (السطر {ln})", file=sys.stderr)
    os.environ.setdefault("DAD_OUT_DIR", str(path.resolve().parent))
    if os.environ.get("DAD_INTERACTIVE") == "1":
        import builtins, json as _json
        def _ask_live(prompt=""):
            token = os.environ.get('DAD_EVENT_TOKEN', '')
            marker = "@@DAD_ASK@@" + (token + ':' if token else '')
            sys.stdout.write("\n" + marker + _json.dumps(str(prompt).strip(), ensure_ascii=False) + "\n"); sys.stdout.flush()
            line = sys.stdin.readline()
            if line == "":
                raise EOFError("no answer")
            ans = line.rstrip("\r\n")
            sys.stdout.write(f"{str(prompt).strip()} {ans}\n"); sys.stdout.flush()
            return ans
        builtins.input = _ask_live
    sys.dont_write_bytecode = True
    if _safe_enabled(src):
        _install_safe_mode(os.environ["DAD_OUT_DIR"])
    try:
        env = {"__name__": "__main__", "__file__": str(path), "ارسم": ارسم}
        env.update(vnext.RUNTIME)
        _p = print
        _ar = {True: "صح", False: "خطأ", None: "لاشيء"}
        env["print"] = lambda *a, **k: _p(*[_ar.get(x, x) if isinstance(x, (bool, type(None))) else x for x in a], **k)
        exec(compile(code, str(path), "exec"), env)
    except SystemExit:
        raise
    except BaseException as e:
        if type(e).__name__ == "RuntimeError" and "LM Studio" in str(e):
            print(f"\n⚠ {e}", file=sys.stderr); sys.exit(1)
        line = getattr(e, "lineno", None) if isinstance(e, SyntaxError) else None
        tb = e.__traceback__
        while tb:                                            # آخر سطر من برنامجك (مو من داخل اللغة)
            if tb.tb_frame.f_code.co_filename == str(path):
                line = tb.tb_lineno
            tb = tb.tb_next
        if line and 0 < line <= len(vnext.SOURCE_MAP):
            line = vnext.SOURCE_MAP[line - 1]
        src_lines = src.splitlines()
        where = f"السطر {line}: " if line else ""
        msg = arabic_error(e)
        if isinstance(e, SyntaxError) and not isinstance(e, IndentationError) and line and 0 < line <= len(src_lines) \
                and _looks_like_plain_text_line(src_lines[line - 1]):
            msg = ("هذا السطر ما يبدأ بأمر معروف (قول، اسأل، احسب، أكمل، إذا، كرر، أضف…). "
                   "إذا لصقت نتيجة برنامج بالغلط، الصق البرنامج نفسه مو نتيجته.")
        print(f"\n⚠ {where}{msg}", file=sys.stderr)
        if line and 0 < line <= len(src_lines):
            print(f"  ← {src_lines[line - 1].strip()}", file=sys.stderr)
        sys.exit(1)




def _dad_num_show(v):
    return int(v) if isinstance(v, float) and v.is_integer() else v


def repl_server():
    """الطرفية التفاعلية: كل سطر ينفذ على طول والذاكرة تظل. بروتوكول: سطر JSON داخل ← سطر JSON طالع."""
    import builtins, contextlib, io, json, os, vnext
    os.environ.setdefault("DAD_OUT_DIR", os.getcwd())
    sys.dont_write_bytecode = True
    if _safe_enabled(""):
        _install_safe_mode(os.environ["DAD_OUT_DIR"])
    env = {"__name__": "__main__", "ارسم": ارسم}
    env.update(vnext.RUNTIME)
    _p = print
    _ar = {True: "صح", False: "خطأ", None: "لاشيء"}
    names = vnext.Names()
    answers = []
    live = False

    def fake_input(prompt=""):
        if not answers:
            if not live: raise EOFError("السطر يسأل سؤال وما في جواب")
            stdout.write(json.dumps({'event':'question', 'prompt':str(prompt).strip()}, ensure_ascii=False) + '\n'); stdout.flush()
            response = sys.stdin.readline()
            if not response: raise EOFError('ما وصل جواب السؤال')
            try: reply = json.loads(response)
            except ValueError: raise vnext.DadError('الجواب غير صحيح في الطرفية.') from None
            if reply.get('cancel'): raise vnext.DadError('أوقف المستخدم التشغيل عند السؤال.')
            if 'answer' not in reply: raise vnext.DadError('جاوب السؤال الحالي قبل كتابة أمر جديد.')
            answers.append(str(reply['answer']))
        sys.stdout.write(str(prompt))
        return answers.pop(0)
    builtins.input = fake_input
    stdout = sys.stdout
    for raw in sys.stdin:
        try:
            req = json.loads(raw)
        except ValueError:
            continue
        if req.get("reset"):
            env.clear(); env.update({"__name__": "__main__", "ارسم": ارسم}); env.update(vnext.RUNTIME); names = vnext.Names()
            stdout.write(json.dumps({"ok": True, "out": "✓ انمسحت الذاكرة", "err": ""}, ensure_ascii=False) + "\n"); stdout.flush(); continue
        code = str(req.get("code", "")).rstrip("\n")
        live = bool(req.get('live'))
        answers[:] = [str(a) for a in (req.get("answers") or [])]
        out, err = io.StringIO(), io.StringIO()
        ok = True
        try:
            new_code = to_python(code, names)
            names = vnext.LAST_NAMES
            n_new = len(code.split("\n"))
            env["print"] = lambda *a, **k: _p(*[_ar.get(x, x) if isinstance(x, (bool, type(None))) else x for x in a], **{**k, "file": k.get("file", out)})
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                for ln, wrong, right in LAST_FIXES:
                    print(f"✎ صححت «{wrong}» ← «{right}»", file=sys.stderr)
                expr = None
                if n_new == 1:
                    try:
                        expr = compile(new_code, "<الطرفية>", "eval")        # سطر قيمة ← نعرضها مثل Python
                    except SyntaxError:
                        expr = None
                if expr is not None:
                    val = eval(expr, env)
                    if val is not None and not new_code.strip().startswith(("_dad_", "print(")):
                        print(_ar.get(val, val) if isinstance(val, (bool, type(None))) else val)
                else:
                    exec(compile(new_code, "<الطرفية>", "exec"), env)
                    if n_new == 1 and re.match(r"^\s*الناتج = _dad_(?:num|calc)\(", new_code) and "الناتج" in env:
                        print("= " + str(_dad_num_show(env["الناتج"])))      # احسب في الطرفية يعرض النتيجة
        except vnext.DadError as e:
            ok = False; err.write("⚠ " + e.arabic().replace(f"السطر {e.line}: ", "") + "\n")
        except EOFError as e:
            ok = False; err.write("⚠ " + str(e) + "\n")
        except BaseException as e:
            ok = False
            if type(e).__name__ == "RuntimeError" and "LM Studio" in str(e):
                err.write("⚠ " + str(e) + "\n")
            else:
                err.write("⚠ " + arabic_error(e) + "\n")
        stdout.write(json.dumps({"ok": ok, "out": out.getvalue(), "err": err.getvalue()}, ensure_ascii=False) + "\n")
        stdout.flush()

def print_dictionary():
    for title, table in (("الكلمات المحجوزة", KEYWORDS), ("الدوال الجاهزة", BUILTINS), ("بعد النقطة", METHODS)):
        print(f"\n== {title} ==")
        for ar, py in table.items():
            print(f"  {ar:<14} ←  {py}")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 0
    cmd = argv[1]
    if cmd in ("طرفية", "repl"):
        repl_server(); return 0
    if cmd in ("قاموس", "dict"):
        print_dictionary(); return 0
    if len(argv) < 3:
        print("حدد اسم الملف."); return 1
    path = Path(argv[2])
    if cmd in ("شغل", "run"):
        run(path)
    elif cmd in ("حول", "py"):
        out = path.with_suffix(".py")
        out.write_text(to_python(path.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"انحفظ: {out}")
    elif cmd in ("عدل_رسمة", "redraw"):
        instruction = " ".join(argv[3:])
        svg = draw_svg(instruction, previous_svg=path.read_text(encoding="utf-8"))
        path.write_text(svg, encoding="utf-8")
        print(f"@@DAD_IMAGE@@{path}")
    elif cmd in ("اسئلة", "questions"):
        import vnext, ui, json as _j, ast as _ast
        if ui.is_ui(path.read_text(encoding="utf-8")):
            print("[]"); return 0
        try:
            code = to_python(path.read_text(encoding="utf-8"))
        except vnext.DadError:
            print("[]"); return 0

        # مهم: الواجهة تجمع الأجوبة قبل التشغيل. سابقاً كانت ترى «اسأل» داخل كرر مرة واحدة فقط،
        # لذلك كرر(2 مرات) كان يطلب جواباً واحداً ثم ينفد الإدخال في الدورة الثانية.
        # هنا نقرأ Python AST ونوسّع حلقات range ذات العدد الثابت، فيظهر السؤال للمستخدم كل مرة فعلياً.
        def _prompt_of_call(call):
            if not isinstance(call, _ast.Call):
                return None
            fn = call.func
            name = fn.id if isinstance(fn, _ast.Name) else None
            if name == "_dad_calc_ask":
                return "وش تبي أحسب؟"
            if name not in ("_dad_ask", "input"):
                return None
            if call.args and isinstance(call.args[0], _ast.Constant) and isinstance(call.args[0].value, str):
                return call.args[0].value
            return "سؤال"

        def _const_range_count(call):
            if not (isinstance(call, _ast.Call) and isinstance(call.func, _ast.Name) and call.func.id == "range"):
                return None
            vals = []
            for a in call.args:
                if isinstance(a, _ast.Constant) and isinstance(a.value, int):
                    vals.append(a.value)
                else:
                    return None
            try:
                if len(vals) == 1: return max(0, vals[0])
                if len(vals) == 2: return max(0, len(range(vals[0], vals[1])))
                if len(vals) == 3: return max(0, len(range(vals[0], vals[1], vals[2])))
            except Exception:
                return None
            return None

        def _collect(nodes, mult=1):
            out = []
            for node in nodes:
                if isinstance(node, _ast.For):
                    n = _const_range_count(node.iter)
                    if n is not None and n <= 1000:
                        out.extend(_collect(node.body, mult * n))
                        out.extend(_collect(node.orelse, mult))
                        continue
                prompts = []
                for sub in _ast.walk(node):
                    # لا ندخل جسم For هنا؛ نعالجه فوق حتى لا نكرر مرتين.
                    if sub is not node and isinstance(sub, (_ast.For, _ast.While, _ast.FunctionDef, _ast.AsyncFunctionDef, _ast.Lambda)):
                        continue
                    if isinstance(sub, _ast.Call):
                        q = _prompt_of_call(sub)
                        if q is not None:
                            prompts.append(q)
                for q in prompts:
                    out.extend([q] * mult)
            return out

        try:
            tree = _ast.parse(code)
            qs = _collect(tree.body)
        except Exception:
            # رجوع للطريقة القديمة إذا ظهر Python غير متوقع.
            qs = []
            for m in re.finditer(r"_dad_calc_ask\(|(?:_dad_ask|input)\(\s*(\"(?:[^\"\\]|\\.)*\"|'[^']*')?", code):
                if m.group(0).startswith("_dad_calc_ask"):
                    qs.append("وش تبي أحسب؟"); continue
                try: qs.append(_j.loads(m.group(1)) if m.group(1) and m.group(1)[0] == '"' else (m.group(1) or "سؤال").strip("'"))
                except Exception: qs.append("سؤال")
        print(_j.dumps(qs, ensure_ascii=False))
    elif cmd in ("اعرض", "show"):
        import vnext
        try:
            print(to_python(path.read_text(encoding="utf-8")))
        except vnext.DadError as e:
            print("⚠ " + e.arabic())
    elif cmd in ("اقرأ", "read"):
        print(to_arabic(path.read_text(encoding="utf-8")))
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    from aldad_syntax import DadError
    try:
        raise SystemExit(main(sys.argv))
    except DadError as error:
        print("⚠ " + error.arabic(), file=sys.stderr)
        raise SystemExit(1)
    except (Exception, KeyboardInterrupt) as error:
        print("⚠ " + arabic_error(error), file=sys.stderr)
        raise SystemExit(1)
