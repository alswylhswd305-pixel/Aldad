"""
واجهات الضاد 1.0 — برامج بنوافذ وأزرار وحقول.

    برنامج اسمه "حاسبتي"
    افتح نافذة اسمها "الحاسبة"
    أضف حقل اسمه العدد
    أضف حقل اسمه السعر
    أضف زر اسمه "احسب"
    أضف نص اسمه النتيجة
    عند ضغط "احسب"
        احسب العدد ضرب السعر
        ضع الناتج في النتيجة

البرنامج يتحول لصفحة واحدة (HTML) تشتغل في أي متصفح، بدون إنترنت.
داخل «عند ضغط»: احسب · ضع ... في ... · امسح · قل · إذا(...) / وإلا
"""
import html
import ast
import json
import re

import vnext
from vnext import DadError, Names, nk

WIDGETS = {nk(k): v for k, v in [("حقل", "field"), ("خانة", "field"), ("زر", "button"), ("نص", "label"), ("عنوان", "label"),
           ("محرر", "editor"), ("صندوق", "box"), ("مربع", "box"), ("رقم", "field"), ("محادثة", "chat"), ("دردشة", "chat"),
           ("قائمة", "list"), ("لائحة", "list")]}
UI_LINE = re.compile(r"^\s*(?:برنامج\s+اسمه|افتح\s+(?:نافذة|شاشة)|أضف\s+(?:حقل|خانة|زر|نص|عنوان|محرر|صندوق|مربع|محادثة|دردشة|قائمة|لائحة)\b|اضف\s+(?:حقل|زر|نص|محادثة|قائمة|لائحة)\b|عند\s+ضغط|شخصية\s+الذكاء)")


def is_ui(src: str) -> bool:
    return any(UI_LINE.match(l) for l in src.splitlines())


def _unq(s):
    return s.strip().strip('"«»\'').strip()


def _js_expr(py_expr, known, getter="VN"):
    """Translate the parsed value tree, preserving grouping and field names."""
    labels = {re.sub(r'\s+', '_', n): n for n in known}
    ops = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/', ast.Pow: '**', ast.Mod: '%'}
    comparisons = {ast.Eq:'===', ast.NotEq:'!==', ast.Gt:'>', ast.GtE:'>=', ast.Lt:'<', ast.LtE:'<='}

    def emit(node):
        if isinstance(node, ast.Constant): return json.dumps(node.value, ensure_ascii=False)
        if isinstance(node, ast.Name):
            if node.id == 'القيمة_الفعالة': return 'ACTIVE()'
            if node.id not in labels: raise DadError(f'«{node.id}» غير معروف في النافذة.')
            return f'{getter}({json.dumps(labels[node.id], ensure_ascii=False)})'
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return f'BIN({json.dumps(ops[type(node.op)])},{emit(node.left)},{emit(node.right)})'
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return f'({"-" if isinstance(node.op, ast.USub) else "+"}NUM({emit(node.operand)}))'
        if isinstance(node, ast.BoolOp):
            return '(' + (' && ' if isinstance(node.op, ast.And) else ' || ').join(emit(x) for x in node.values) + ')'
        if isinstance(node, ast.Compare):
            values = [node.left] + node.comparators
            return '(' + ' && '.join(f'({emit(a)} {comparisons[type(op)]} {emit(b)})' for a, op, b in zip(values, node.ops, values[1:])) + ')'
        if isinstance(node, ast.Tuple): return '[' + ','.join(emit(x) for x in node.elts) + '].join(" ")'
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == '_dad_evaluate' and isinstance(node.args[0], ast.Constant):
                return emit(ast.parse(node.args[0].value, mode='eval').body)
            calls = {'sum':'SUM', 'max':'MAX', 'min':'MIN', '_dad_count':'CNT', '_dad_mean':'MEAN'}
            if node.func.id in calls and len(node.args) == 1:
                return f'{calls[node.func.id]}({emit(node.args[0])})'
        raise DadError('هذا التعبير غير مدعوم في النافذة.')
    try:
        return emit(ast.parse(py_expr, mode='eval').body)
    except (SyntaxError, KeyError):
        raise DadError('التعبير في النافذة ناقص أو غير صحيح.') from None


class UIProgram:
    def __init__(self):
        self.title = "برنامجي"
        self.window = None
        self.widgets = []            # {kind, name, label}
        self.events = {}             # اسم الزر ← كود JS
        self.startup = []            # أسطر برا الأحداث (قل ...)
        self.uses_ai = False
        self.dark = False
        self.full = False
        self.persona = "أنت مساعد داخل برنامج مكتوب بلغة الضاد. أجب بالعربية باختصار ووضوح."

    def names(self):
        n = Names()
        for w in self.widgets:
            n.add(w["name"])
        n.add("الناتج")
        return n

    def find(self, name):
        k = nk(_unq(name))
        for w in self.widgets:
            if nk(w["name"]) == k or vnext.key(w["name"]) == vnext.key(_unq(name)):
                return w
        return None


def _action(line, prog: UIProgram, no):
    """سطر داخل «عند ضغط» ← JS."""
    t = line.strip()
    known = {w["name"] for w in prog.widgets} | {"الناتج"}
    names = prog.names()
    m = re.match(r"^(?:احسب|احسبلي)(?:\s+(.+)|\((.*)\))\s*$", t)
    if m:
        a = vnext.parse_calc(m.group(1) if m.group(1) is not None else m.group(2), names)
        if a.get("op") != "CALC":
            raise DadError("هذا الحساب يحتاج بيانات ما عندي داخل الواجهة.")
        return f'R["الناتج"]=NUM({_js_expr(a["expr"], known)});R["_active"]=R["الناتج"];'
    m = re.match(r'^(?:كمل|أكمل|اكمل)(?:\s+(.+)|\((.*)\))\s*$', t)
    if m:
        a = vnext._resolve_continue({'op':'CONTINUE_RAW', 'text':m.group(1) if m.group(1) is not None else m.group(2)}, names)
        return f'R["الناتج"]=NUM({_js_expr(a["expr"], known)});R["_active"]=R["الناتج"];'
    m = re.match(r"^(?:اطلب|أطلب)\s*\(?(.*?)\)?\s*$", t)
    if m:
        raise DadError(vnext.AI_DISABLED)
    m = re.match(r"^(?:ضع|حط)\s+(.+?)\s+في\s+(.+?)\s*$", t)
    if m:
        target = prog.find(m.group(2))
        if not target:
            raise DadError(f"ما في شي اسمه «{_unq(m.group(2))}» في النافذة.", [f"أضف نص اسمه {_unq(m.group(2))}"])
        src = m.group(1).strip()
        if src[:1] in '"«':
            val = json.dumps(_unq(src), ensure_ascii=False)
        elif prog.find(src) or nk(src) in (nk("الناتج"), nk("الرد")):
            w = prog.find(src)
            val = f'V({json.dumps(w["name"] if w else ("الرد" if nk(src) == nk("الرد") else "الناتج"), ensure_ascii=False)})'
        else:
            items = vnext.items_of(src, names)
            me = vnext.math_expr(items)
            val = f"NUM({_js_expr(me[0], known)})" if me else json.dumps(src, ensure_ascii=False)
        return f'SET({json.dumps(target["name"], ensure_ascii=False)},{val});'
    m = re.match(r"^امسح\s*(.*)$", t)
    if m:
        what = _unq(m.group(1))
        if not what or nk(what) in (nk("الكل"), nk("كل شي"), nk("الجميع")):
            return "CLEAR();"
        w = prog.find(what)
        if not w:
            raise DadError(f"ما في شي اسمه «{what}» أمسحه.")
        return f'SET({json.dumps(w["name"], ensure_ascii=False)},"");'
    # أدوات IDE والملفات — تبقى تحت أوامر الضاد الطبيعية بدل زيادة أوامر النواة.
    m = re.match(r"^(?:اعرض|حدّث|حدث)\s+(?:ملفات|الملفات)(?:\s+المجلد)?\s+في\s+(.+?)\s*$", t)
    if m:
        target = prog.find(m.group(1))
        if not target or target["kind"] != "list":
            raise DadError(f"«{_unq(m.group(1))}» لازم تكون قائمة.", [f"أضف قائمة اسمها {_unq(m.group(1))}"])
        return f'{{const x=await BRIDGE("list",{{}});FILL({json.dumps(target["name"], ensure_ascii=False)},x.files||[]);SAY("تم تحديث الملفات");}}'

    m = re.match(r"^افتح\s+(?:المختار|الملف\s+المختار)\s+من\s+(.+?)\s+في\s+(.+?)\s*$", t)
    if m:
        src = prog.find(m.group(1)); target = prog.find(m.group(2))
        if not src or src["kind"] != "list":
            raise DadError(f"«{_unq(m.group(1))}» لازم تكون قائمة ملفات.")
        if not target or target["kind"] != "editor":
            raise DadError(f"«{_unq(m.group(2))}» لازم يكون محرر.")
        name_field = next((w for w in prog.widgets if nk(w["name"]) == nk("اسم الملف") and w["kind"] == "field"), None)
        set_name = f'SET({json.dumps(name_field["name"], ensure_ascii=False)},x.name||n);' if name_field else ''
        return (f'{{const n=V({json.dumps(src["name"], ensure_ascii=False)});if(!n)throw new Error("اختر ملف أول");'
                f'const x=await BRIDGE("open",{{name:n}});SET({json.dumps(target["name"], ensure_ascii=False)},x.code||"");'
                f'R["الملف"]=x.name||n;{set_name}SAY("انفتح: "+(x.name||n));}}')

    m = re.match(r"^احفظ\s+(.+?)\s+(?:باسم|في)\s+(.+?)\s*$", t)
    if m:
        srcw = prog.find(m.group(1))
        if srcw and srcw["kind"] == "editor":
            dst = _unq(m.group(2))
            if nk(dst) in (nk("الملف"), nk("الملف الحالي")):
                name_expr = '(R["الملف"]||V("اسم الملف")||"program.dad")'
            else:
                dstw = prog.find(dst)
                if dstw and dstw["kind"] == "field":
                    name_expr = f'V({json.dumps(dstw["name"], ensure_ascii=False)})'
                else:
                    name_expr = json.dumps(dst, ensure_ascii=False)
            listw = next((w for w in prog.widgets if w["kind"] == "list"), None)
            refill = (f'const q=await BRIDGE("list",{{}});FILL({json.dumps(listw["name"], ensure_ascii=False)},q.files||[]);' if listw else '')
            return (f'{{const n={name_expr};if(!n)throw new Error("اكتب اسم الملف أول");'
                    f'const x=await BRIDGE("save",{{name:n,code:String(V({json.dumps(srcw["name"], ensure_ascii=False)})||"")}});'
                    f'R["الملف"]=x.name||n;{refill}SAY("انحفظ: "+(x.name||n));}}')

    m = re.match(r"^(?:شغل|شغّل)\s+(.+?)(?:\s+في\s+(.+?))?\s*$", t)
    if m:
        srcw = prog.find(m.group(1)); outw = prog.find(m.group(2)) if m.group(2) else None
        if not srcw or srcw["kind"] != "editor":
            raise DadError(f"«{_unq(m.group(1))}» لازم يكون محرر كود.")
        if m.group(2) and (not outw or outw["kind"] not in ("box", "editor", "label")):
            raise DadError(f"«{_unq(m.group(2))}» لازم يكون صندوق أو نص للنتائج.")
        out_name = json.dumps(outw["name"], ensure_ascii=False) if outw else None
        setout = f'SET({out_name},txt);' if outw else 'SAY(txt);'
        return (f'{{SAY("⏳ يشغّل…");let x=await BRIDGE("run_start",{{code:String(V({json.dumps(srcw["name"], ensure_ascii=False)})||"")}});let txt="";'
                f'while(x.status==="ask"){{txt+=(txt&&x.out?"\\n":"")+(x.out||"");const a=window.prompt(x.prompt||"سؤال","");'
                f'if(a===null){{await BRIDGE("run_stop",{{id:x.id}});x={{ok:false,out:"",err:"⚠ وقفت التشغيل."}};break;}}'
                f'x=await BRIDGE("run_answer",{{id:x.id,answer:a}});}}'
                f'txt+=(txt&&x.out?"\\n":"")+(x.out||"")+(x.err?((txt||x.out?"\\n":"")+x.err):"");{setout}SAY(x.ok?"✓ اشتغل":"⚠ فيه مشكلة");}}')

    m = re.match(r"^(?:ابن|ابني|بناء)\s+(?:EXE\s+من\s+)?(.+?)(?:\s+(?:كـ|ك|الى|إلى)\s*EXE)?(?:\s+في\s+(.+?))?\s*$", t, re.I)
    if m and "EXE" in t.upper():
        srcw = prog.find(m.group(1)); outw = prog.find(m.group(2)) if m.group(2) else None
        if not srcw or srcw["kind"] != "editor":
            raise DadError(f"«{_unq(m.group(1))}» لازم يكون محرر كود.")
        setout = f'SET({json.dumps(outw["name"], ensure_ascii=False)},txt);' if outw else 'SAY(txt);'
        return (f'{{SAY("⏳ يبني EXE…");const x=await BRIDGE("build_exe",{{code:String(V({json.dumps(srcw["name"], ensure_ascii=False)})||""),name:(R["الملف"]||"program.dad")}});'
                f'const txt=x.ok?("✓ تم بناء EXE\\n"+(x.path||"")):("⚠ "+(x.error||"تعذر البناء"));{setout}SAY(x.ok?"✓ تم بناء EXE":"⚠ تعذر البناء");}}')

    if re.match(r"^(?:ملف\s+جديد|جديد)$", t):
        editor = next((w for w in prog.widgets if w["kind"] == "editor"), None)
        name_field = next((w for w in prog.widgets if nk(w["name"]) == nk("اسم الملف") and w["kind"] == "field"), None)
        bits = ['R["الملف"]="";']
        if editor: bits.append(f'SET({json.dumps(editor["name"], ensure_ascii=False)},"");')
        if name_field: bits.append(f'SET({json.dumps(name_field["name"], ensure_ascii=False)},"");')
        bits.append('SAY("ملف جديد");')
        return "".join(bits)

    m = re.match(r"^(?:قل|قول)(?:\s+(.+)|\((.*)\))\s*$", t)
    if m:
        src = m.group(1) if m.group(1) is not None else m.group(2)
        if vnext.one_group(src): src = src[1:-1]
        value = vnext.parse_output(src, names)
        if value['op'] != 'OUTPUT': raise DadError('السؤال داخل النافذة يحتاج حقلًا يكتبه المستخدم.')
        return f'SAY({_js_expr(value["expr"], known, "V")});'
    raise DadError(f"«{t}» مو مدعوم داخل «عند ضغط» في واجهات 1.9.",
                   ["احسب العدد ضرب السعر", "ضع الناتج في النتيجة", "اعرض الملفات في الملفات", "افتح المختار من الملفات في الكود", "شغل الكود في النتائج", "قل «تم»"])


def compile_ui(src: str) -> UIProgram:
    vnext.check_syntax(src)
    prog = UIProgram()
    lines = src.splitlines()
    i = 0
    cur_event, stack = None, []                               # stack: (indent, closer)
    def close_to(ind, js):
        while stack and ind <= stack[-1][0]:
            stack.pop(); js.append("}")
    while i < len(lines):
        raw = lines[i]; no = i + 1; i += 1
        body = raw.strip()
        if not body or body.startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip())
        try:
            if cur_event is not None and ind > 0:
                js = prog.events[cur_event]
                close_to(ind, js)
                m = re.match(r"^(?:إذا|اذا|لو)\s*\((.*)\)\s*(?:ثم\s+(.+))?:?\s*$", body)
                if m:
                    known = {w["name"] for w in prog.widgets} | {"الناتج"}
                    cond = _js_expr(vnext.parse_cond(m.group(1), prog.names())["cond"], known)
                    if m.group(2):
                        js.append(f"if({cond}){{{_action(m.group(2), prog, no)}}}")
                    else:
                        js.append(f"if({cond}){{"); stack.append((ind, "}"))
                    continue
                if re.match(r"^(وإلا|والا)\s*:?\s*$", body):
                    js.append("else{"); stack.append((ind, "}"))
                    continue
                for part in [p for p in vnext._split_then(body) if p]:
                    js.append(_action(part, prog, no))
                continue
            if cur_event is not None:
                close_to(-1, prog.events[cur_event]); cur_event = None
            m = re.match(r"^برنامج\s+اسمه\s+(.+)$", body)
            if m:
                prog.title = _unq(m.group(1)); continue
            m = re.match(r"^افتح\s+(نافذة|شاشة)(.*)$", body)
            if m:
                rest = m.group(2)
                if re.search(r"سوداء|سودا|مظلمة|داكنة|ليلية", rest): prog.dark = True
                if re.search(r"كاملة|كامله|ملء", rest) or m.group(1) == "شاشة": prog.full = True
                mt = re.search(r"(?:اسمها|اسمه|عنوانها)\s+(.+)$", rest)
                prog.window = _unq(mt.group(1)) if mt else (prog.window or prog.title)
                continue
            m = re.match(r"^شخصية\s+الذكاء\s+(.+)$", body)
            if m:
                raise DadError(vnext.AI_DISABLED)
            m = re.match(r"^(?:أضف|اضف)\s+(\S+)\s+(?:اسمه|اسمها|عنوانه)\s+(.+)$", body)
            if m and nk(m.group(1)) in WIDGETS:
                name = _unq(m.group(2))
                if WIDGETS[nk(m.group(1))] == "chat":
                    raise DadError(vnext.AI_DISABLED)
                if prog.find(name):
                    raise DadError(f"فيه شي اسمه «{name}» قبل — كل شي في النافذة له اسم مختلف.")
                prog.widgets.append({"kind": WIDGETS[nk(m.group(1))], "name": name}); continue
            m = re.match(r"^عند\s+ضغط\s+(.+?)\s*:?\s*$", body)
            if m:
                b = prog.find(m.group(1))
                if not b or b["kind"] != "button":
                    raise DadError(f"ما في زر اسمه «{_unq(m.group(1))}».", [f"أضف زر اسمه \"{_unq(m.group(1))}\""])
                cur_event = b["name"]; prog.events[cur_event] = []; stack = []
                continue
            m = re.match(r"^(?:قل|قول)\s*\(?(.*?)\)?\s*$", body)
            if m:
                prog.startup.append(f'SAY({json.dumps(_unq(m.group(1)), ensure_ascii=False)});'); continue
            raise DadError(f"ما فهمت «{body}» في برنامج الواجهة.",
                           ["أضف زر اسمه \"احسب\"", "أضف حقل اسمه العدد", "عند ضغط \"احسب\""])
        except DadError as e:
            e.line = e.line or no
            raise
    if cur_event is not None:
        close_to(-1, prog.events[cur_event])
    if not prog.widgets:
        raise DadError("البرنامج ما فيه ولا شي في النافذة.", ["أضف زر اسمه \"احسب\""])
    return prog


def to_html(prog: UIProgram, lm_base: str = "http://127.0.0.1:1234/v1", model: str = "") -> str:
    esc = lambda s: html.escape(str(s))
    parts = []
    for w in prog.widgets:
        n, k = w["name"], w["kind"]
        wid = json.dumps(n, ensure_ascii=False)
        if k == "field":
            parts.append(f'<label class="f"><span>{esc(n)}</span><input data-n="{esc(n)}" dir="auto" inputmode="decimal" autocomplete="off"></label>')
        elif k == "editor":
            parts.append(f'<label class="f"><span>{esc(n)}</span><textarea data-n="{esc(n)}" dir="auto" rows="6"></textarea></label>')
        elif k == "button":
            parts.append(f'<button class="b" data-b="{esc(n)}">{esc(n)}</button>')
        elif k == "chat":
            parts.append(f'<div class="chat" data-chat="{esc(n)}"><div class="msgs"><div class="m sys">{esc(n)} — اكتب رسالتك تحت واضغط Enter</div></div>'
                         f'<div class="compose"><textarea rows="2" dir="auto" placeholder="اكتب رسالتك…  (Enter للإرسال · Shift+Enter سطر جديد)"></textarea><button class="send">إرسال</button></div></div>')
        elif k == "box":
            parts.append(f'<div class="box"><div class="cap">{esc(n)}</div><pre data-n="{esc(n)}"></pre></div>')
        elif k == "list":
            parts.append(f'<label class="f"><span>{esc(n)}</span><select data-n="{esc(n)}" size="9"></select></label>')
        else:
            parts.append(f'<div class="lbl"><span class="cap">{esc(n)}</span><output data-n="{esc(n)}">—</output></div>')
    handlers = "\n".join(f'H[{json.dumps(b, ensure_ascii=False)}]=async function(){{try{{{"".join(js)}}}catch(e){{SAY("⚠ "+e.message)}}}};'
                         for b, js in prog.events.items())
    return f'''<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(prog.window or prog.title)}</title>
<style>
:root{{--bg:#f4f5f9;--card:#fff;--fg:#1d2230;--mut:#6b7285;--acc:#2f6fd6;--line:#e3e6ee}}
@media (prefers-color-scheme:dark){{:root{{--bg:#171923;--card:#20232f;--fg:#eceef4;--mut:#9aa1b5;--acc:#4a88ea;--line:#323646}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font-family:"Segoe UI","Dubai",Tahoma,sans-serif;display:flex;justify-content:center;padding:28px 14px}}
.win{{width:min(520px,100%);background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.08);overflow:hidden}}
.bar{{padding:12px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:8px}}
.bar h1{{font-size:17px;margin:0}}.bar small{{color:var(--mut);margin-inline-start:auto;font-size:12px}}
.body{{padding:18px;display:flex;flex-direction:column;gap:12px}}
.f{{display:flex;flex-direction:column;gap:5px}}.f span,.cap{{font-size:13px;color:var(--mut)}}
input,textarea,select{{font:inherit;font-size:17px;padding:9px 12px;border-radius:9px;border:1px solid var(--line);background:transparent;color:inherit}}
input:focus,textarea:focus,select:focus{{outline:2px solid var(--acc);border-color:transparent}}
.b{{font:inherit;font-size:16px;font-weight:600;padding:11px;border:0;border-radius:10px;background:var(--acc);color:#fff;cursor:pointer}}
.b:active{{transform:translateY(1px)}}
.lbl{{display:flex;align-items:baseline;gap:10px;padding:10px 12px;border-radius:10px;background:rgba(47,111,214,.08)}}
.lbl output{{font-size:24px;font-weight:700;margin-inline-start:auto}}
select{{min-height:150px}}
.box pre{{margin:4px 0 0;min-height:60px;padding:10px;border:1px solid var(--line);border-radius:9px;white-space:pre-wrap;font-family:inherit;unicode-bidi:plaintext}}
#say{{min-height:20px;font-size:14px;color:var(--mut);text-align:center}}
.chat{{display:flex;flex-direction:column;border:1px solid var(--line);border-radius:12px;overflow:hidden;min-height:420px;flex:1}}
.msgs{{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}}
.m{{max-width:85%;padding:10px 14px;border-radius:14px;white-space:pre-wrap;line-height:1.7;unicode-bidi:plaintext}}
.m.me{{align-self:flex-start;background:var(--acc);color:#fff;border-bottom-right-radius:4px}}
.m.ai{{align-self:flex-end;background:rgba(127,127,127,.14);border-bottom-left-radius:4px}}
.m.sys{{align-self:center;font-size:13px;color:var(--mut);background:none}} .m.err{{color:#e5534b}}
.compose{{display:flex;gap:8px;padding:10px;border-top:1px solid var(--line)}}
.compose textarea{{flex:1;resize:none}} .send{{font:inherit;font-weight:600;padding:0 18px;border:0;border-radius:10px;background:var(--acc);color:#fff;cursor:pointer}}
body.dark{{--bg:#0d0f14;--card:#12151c;--fg:#e8eaf0;--mut:#8a91a6;--acc:#3b82f6;--line:#232838}}
body.full{{padding:0}} body.full .win{{width:100%;min-height:100vh;border:0;border-radius:0;display:flex;flex-direction:column}}
body.full .body{{flex:1}}
</style></head><body class="{"dark" if prog.dark else ""} {"full" if prog.full else ""}"><div class="win">
<div class="bar"><h1>{esc(prog.window or prog.title)}</h1><small>{esc(prog.title)} · الضاد</small></div>
<div class="body">{"".join(parts)}<div id="say"></div></div></div>
<script>
const R={{}}, H={{}};
const AD="٠١٢٣٤٥٦٧٨٩";
function num(s){{ if(typeof s==="number") return s; s=String(s??"").trim().replace(/[٠-٩]/g,d=>AD.indexOf(d)).replace("٫",".").replace("،",".");
  const n=parseFloat(s); return (s!==""&&!isNaN(n)&&/^[-+]?\\d*\\.?\\d+$/.test(s))?n:s; }}
function el(n){{ return document.querySelector('[data-n="'+CSS.escape(n)+'"]'); }}
function V(n){{ if(n in R && !el(n)) return R[n]; const e=el(n); if(!e) return R[n];
  const v=("value" in e && e.tagName!=="OUTPUT")?e.value:e.textContent; return num(v===\"—\"?\"\":v); }}
function VN(n){{ const v=V(n); if(v===""||v===undefined) throw new Error("خانة «"+n+"» فاضية — اكتب فيها رقم"); if(typeof v!=="number") throw new Error("«"+v+"» في خانة «"+n+"» مو رقم"); return v; }}
function NUM(v){{ if(typeof v!=="number") throw new Error("الحساب يحتاج رقمًا؛ القيمة نص أو غير معرّفة"); if(!Number.isFinite(v)) throw new Error("نتيجة الحساب غير محدودة أو غير صالحة"); return Math.round(v*1e6)/1e6; }}
function ACTIVE(){{ if(!Object.prototype.hasOwnProperty.call(R,"_active")) throw new Error("كمل تحتاج قيمة قديمة؛ احسب أولًا"); return R["_active"]; }}
function BIN(op,a,b){{ NUM(a); NUM(b); if((op==="/"||op==="%")&&b===0) throw new Error("قسمة على صفر — ما ينفع"); switch(op){{case "+":return a+b;case "-":return a-b;case "*":return a*b;case "/":return a/b;case "**":return a**b;case "%":return a%b;}} }}
function SET(n,v){{ const e=el(n); if(!e){{R[n]=v;return;}} if("value" in e && e.tagName!=="OUTPUT") e.value=v; else e.textContent=(v===""?"—":v); R[n]=v; }}
function FILL(n,items){{ const e=el(n); if(!e||e.tagName!=="SELECT") return; const old=e.value; e.innerHTML=""; (items||[]).forEach(v=>{{const o=document.createElement("option");o.value=String(v);o.textContent=String(v);e.appendChild(o);}}); if(old&&[...e.options].some(o=>o.value===old))e.value=old; else if(e.options.length)e.selectedIndex=0; }}
let BRIDGE_ID=0; const BRIDGE_WAIT=new Map();
window.addEventListener("message",e=>{{const d=e.data||{{}}; if(d.dadBridgeReply!==1)return; const p=BRIDGE_WAIT.get(d.id); if(!p)return; BRIDGE_WAIT.delete(d.id); d.ok?p.resolve(d.data||{{}}):p.reject(new Error(d.error||"فشل الاتصال مع ضاد IDE"));}});
function BRIDGE(action,payload){{ return new Promise((resolve,reject)=>{{ const target=(window.parent!==window?window.parent:window.opener); if(!target) return reject(new Error("هذي العملية تحتاج تشغيل البرنامج من داخل ضاد IDE")); const id=++BRIDGE_ID; BRIDGE_WAIT.set(id,{{resolve,reject}}); target.postMessage({{dadBridge:1,id,action,payload:payload||{{}}}},"*"); setTimeout(()=>{{if(BRIDGE_WAIT.has(id)){{BRIDGE_WAIT.delete(id);reject(new Error("انتهت مهلة الاتصال مع ضاد IDE"));}}}},120000); }}); }}
function CLEAR(){{ document.querySelectorAll("[data-n]").forEach(e=>{{ if("value" in e && e.tagName!=="OUTPUT") e.value=""; else e.textContent=(e.tagName==="OUTPUT"?"—":""); }}); SAY(""); }}
function SAY(t){{ document.getElementById("say").textContent=String(t); }}
function CNT(x){{ return Array.isArray(x)?x.length:x; }} const SUM=a=>a.reduce((p,c)=>p+NUM(c),0), MAX=a=>Math.max(...a.map(NUM)), MIN=a=>Math.min(...a.map(NUM)), MEAN=a=>a.length?SUM(a)/a.length:0;
{handlers}
document.querySelectorAll("[data-b]").forEach(b=>b.addEventListener("click",()=>{{ const f=H[b.dataset.b]; if(f) f(); else SAY("الزر «"+b.dataset.b+"» ما له عمل — أضف: عند ضغط \\""+b.dataset.b+"\\""); }}));
document.querySelectorAll("input").forEach(i=>i.addEventListener("keydown",e=>{{ if(e.key==="Enter"){{ const b=document.querySelector("[data-b]"); if(b) b.click(); }} }}));
{"".join(prog.startup)}
</script></body></html>'''
