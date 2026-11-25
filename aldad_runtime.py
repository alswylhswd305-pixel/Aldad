"""Runtime context and checked arithmetic, independent of sentence parsing."""
import ast
import math
import operator

from aldad_syntax import DadError


# نبقي الأعداد الصحيحة ضمن حجم يمكن عرضه وحفظه بأمان في الواجهة والطرفية.
# 13000 bit ≈ 3914 أرقام عشرية؛ أقل من حد تحويل int إلى نص في Python الحديثة.
MAX_INT_BITS = 13000


def _too_large():
    raise DadError("النتيجة كبيرة جدًا — استخدم أرقامًا أصغر أو قسّم الحساب إلى خطوات.")


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DadError(f"«احسب» لقت كلام مو رقم («{str(value)[:30]}») — الحساب يحتاج رقمًا.")
    if isinstance(value, int) and value.bit_length() > MAX_INT_BITS:
        _too_large()
    if isinstance(value, float) and not math.isfinite(value):
        raise DadError("نتيجة الحساب غير محدودة — استخدم أرقامًا أصغر.")
    return value


def active(scope):
    if "_dad_active" not in scope:
        raise DadError("«كمل» تحتاج قيمة قديمة تكمل عليها. اسأل أو احسب أولًا.")
    return scope["_dad_active"]


OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}



DIVZERO_MSG = "قسمة على صفر — ما ينفع تقسم على صفر. / Division by zero."


class DadZeroDivisionError(DadError, ZeroDivisionError):
    """Catchable by حاول/try/except/catch and still printed as a DadError."""


def dad_divzero():
    return DadZeroDivisionError(DIVZERO_MSG)


# Built-ins and their Arabic twins, for احسب/calc function calls.
CALC_BUILTINS = {
    "abs": abs, "len": len, "int": int, "float": float, "round": round,
    "sum": sum, "max": max, "min": min, "pow": pow, "divmod": divmod,
    "طول": len, "صحيح": int, "عشري": float, "مطلق": abs, "قرب": round,
    "مجموع": sum, "أكبر": max, "أصغر": min, "قوة": pow,
}
_CALC_DENY = {
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint",
    "exit", "quit", "globals", "locals", "vars", "dir", "getattr", "setattr",
    "delattr", "memoryview", "print", "classmethod", "staticmethod",
}


def _resolve_calc_func(node, walk, local_scope, global_scope):
    if isinstance(node.func, ast.Name):
        fname = node.func.id
        if fname in _CALC_DENY or (fname.startswith("_") and fname not in ("_dad_mean", "_dad_count")):
            raise DadError("هذا الحساب يحتوي دالة غير مدعومة.")
        if fname == "_dad_count":
            return "_dad_count"
        if fname in local_scope and callable(local_scope[fname]):
            return local_scope[fname]
        if fname in global_scope and callable(global_scope[fname]):
            return global_scope[fname]
        if fname in CALC_BUILTINS:
            return CALC_BUILTINS[fname]
        raise DadError(f"هذا الحساب يحتوي دالة غير مدعومة («{fname}»).")
    if isinstance(node.func, ast.Attribute):
        obj = walk(node.func.value)
        attr = node.func.attr
        if attr.startswith("_") or attr in _CALC_DENY:
            raise DadError("هذا الحساب يحتوي دالة غير مدعومة.")
        fn = getattr(obj, attr, None)
        if not callable(fn):
            raise DadError("هذا الحساب يحتوي دالة غير مدعومة.")
        return fn
    raise DadError("هذا الحساب يحتوي دالة غير مدعومة.")


def _call_calc_function(node, walk, local_scope, global_scope):
    fn = _resolve_calc_func(node, walk, local_scope, global_scope)
    if fn == "_dad_count":
        if len(node.args) != 1 or node.keywords:
            raise DadError("حساب العدد يحتاج قيمة واحدة.")
        value = walk(node.args[0])
        return len(value) if isinstance(value, (list, tuple, dict, set)) else number(value)
    args = [walk(a) for a in node.args]
    kwargs = {kw.arg: walk(kw.value) for kw in node.keywords if kw.arg}
    # Keep the old checked path for sum/max/min on a single list argument.
    if fn in (sum, max, min) and len(args) == 1 and not kwargs and isinstance(args[0], (list, tuple)):
        nums = [number(x) for x in args[0]]
        if fn in (max, min) and not nums:
            raise DadError("القائمة فارغة — لا توجد قيمة أكبر أو أصغر.")
        return fn(nums)
    try:
        return fn(*args, **kwargs)
    except ZeroDivisionError:
        raise dad_divzero() from None
    except DadError:
        raise
    except Exception as e:
        raise DadError(f"فشل نداء الدالة في الحساب ({type(e).__name__}).") from e


def evaluate(expr, global_scope, local_scope, continuing=False):
    """Evaluate the parser's numeric AST; operands are checked before operators.

    Context belongs to the executed scope. A skipped branch or an uncalled
    function cannot change it. No model, network, or Python eval is involved.
    """
    try: tree = ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError): raise DadError("العملية ناقصة أو مكتوبة بشكل غير صحيح.") from None

    def walk(node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.Name):
            if node.id == "القيمة_الفعالة" and continuing: return active(local_scope)
            if node.id in local_scope: return local_scope[node.id]
            if node.id in global_scope: return global_scope[node.id]
            raise DadError(f"«{node.id.replace('_', ' ')}» غير معروف — عرّفه أو اسأل عنه أولًا.")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            v = number(walk(node.operand))
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            a, b = number(walk(node.left)), number(walk(node.right))
            if isinstance(node.op, ast.Pow) and isinstance(b, (int, float)):
                # نرفض الأس الذي سيولد عددًا عملاقًا قبل بنائه في الذاكرة.
                if isinstance(b, float) and b.is_integer():
                    b = int(b)
                if isinstance(b, int) and b >= 0 and isinstance(a, int) and abs(a) > 1:
                    estimated_bits = int(math.log2(abs(a)) * b) + 1
                    if estimated_bits > MAX_INT_BITS:
                        _too_large()
                elif isinstance(b, (int, float)) and b > 4096 and abs(a) > 1:
                    _too_large()
            try: val = OPS[type(node.op)](a, b)
            except ZeroDivisionError: raise dad_divzero() from None
            except (OverflowError, ValueError): raise DadError("قيمة الحساب كبيرة أو غير صالحة لهذه العملية.") from None
            if isinstance(val, complex): raise DadError("الحساب يعطي عددًا مركبًا؛ الجذر لعدد سالب غير مدعوم.")
            return number(val)
        if isinstance(node, (ast.List, ast.Tuple)):
            return [walk(elt) for elt in node.elts]
        if isinstance(node, ast.Call):
            return _call_calc_function(node, walk, local_scope, global_scope)
        raise DadError("هذا التعبير غير مدعوم في الحساب.")

    return number(walk(tree.body))
