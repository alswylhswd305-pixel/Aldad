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
                if isinstance(b, float) and b.is_integer(): b = int(b)
                if isinstance(b, int) and b >= 0 and isinstance(a, int) and abs(a) > 1:
                    estimated_bits = int(math.log2(abs(a)) * b) + 1
                    if estimated_bits > MAX_INT_BITS: _too_large()
                elif isinstance(b, (int, float)) and b > 4096 and abs(a) > 1:
                    _too_large()
            try: val = OPS[type(node.op)](a, b)
            except ZeroDivisionError: raise DadError("قسمة على صفر — ما ينفع تقسم على صفر.") from None
            except (OverflowError, ValueError): raise DadError("قيمة الحساب كبيرة أو غير صالحة لهذه العملية.") from None
            if isinstance(val, complex): raise DadError("الحساب يعطي عددًا مركبًا؛ الجذر لعدد سالب غير مدعوم.")
            return number(val)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1 and not node.keywords:
            fname = node.func.id
            if fname not in ("sum", "max", "min", "_dad_mean", "_dad_count"):
                raise DadError("هذا الحساب يحتوي دالة غير مدعومة.")
            value = walk(node.args[0])
            if fname == "_dad_count":
                return len(value) if isinstance(value, (list, tuple, dict, set)) else number(value)
            if not isinstance(value, (list, tuple)):
                raise DadError("حساب المجموع أو المتوسط أو أكبر/أصغر قيمة يحتاج قائمة أرقام.")
            nums = [number(x) for x in value]
            if fname in ("max", "min") and not nums:
                raise DadError("القائمة فارغة — لا توجد قيمة أكبر أو أصغر.")
            return {"sum": lambda: sum(nums), "max": lambda: max(nums), "min": lambda: min(nums),
                    "_dad_mean": lambda: sum(nums)/len(nums) if nums else 0}[fname]()
        raise DadError("هذا التعبير غير مدعوم في الحساب.")

    return number(walk(tree.body))
