"""Shared lexical rules and Arabic diagnostics; no execution or guessing."""


class DadError(Exception):
    def __init__(self, message, options=None):
        super().__init__(message)
        self.options = options or []
        self.line = None

    def arabic(self):
        text = (f"السطر {self.line}: " if self.line else "") + str(self)
        if self.options:
            text += "\nهل تقصد:\n" + "\n".join(f"  {i}. {o}" for i, o in enumerate(self.options, 1))
        return text


def spans(text):
    """Yield (position, char, depth) only outside quotes and comments."""
    stack = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "#":
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if ch in "\"'«":
            quote = "»" if ch == "«" else ch * (3 if text.startswith(ch * 3, i) else 1)
            i += 1 if ch == "«" else len(quote)
            while i < len(text) and not text.startswith(quote, i):
                i += 2 if text[i] == "\\" and ch != "«" else 1
            i += len(quote)
            continue
        yield i, ch, len(stack)
        if ch in "([{": stack.append(ch)
        elif ch in ")]}":
            if stack: stack.pop()
        i += 1


def strip_comment(text):
    # A comment is discarded only outside a quoted string.
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "#": return text[:i].rstrip()
        if ch in "\"'«":
            quote = "»" if ch == "«" else ch * (3 if text.startswith(ch * 3, i) else 1)
            i += 1 if ch == "«" else len(quote)
            while i < len(text) and not text.startswith(quote, i):
                i += 2 if text[i] == "\\" and ch != "«" else 1
            i += len(quote)
        else: i += 1
    return text


def split_then(text):
    positions = [i for i, ch, depth in spans(text)
                 if depth == 0 and text.startswith("ثم", i)
                 and (i == 0 or text[i-1].isspace())
                 and (i+2 == len(text) or text[i+2].isspace() or text[i+2] == "(")]
    parts, start = [], 0
    for i in positions:
        parts.append(text[start:i].strip()); start = i + 2
    parts.append(text[start:].strip())
    return parts


def one_group(text):
    if not (text.startswith("(") and text.endswith(")")): return False
    return not any(ch == ")" and depth == 1 and i != len(text)-1
                   for i, ch, depth in spans(text))


def check_syntax(text):
    pairs = {")": "(", "]": "[", "}": "{"}
    closing = {"(": ")", "[": "]", "{": "}"}
    stack, i, line = [], 0, 1
    while i < len(text):
        ch = text[i]
        if ch == "\n": line += 1
        elif ch == "#":
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif ch in "\"'«":
            begin = line
            quote = "»" if ch == "«" else ch * (3 if text.startswith(ch * 3, i) else 1)
            i += 1 if ch == "«" else len(quote)
            while i < len(text) and not text.startswith(quote, i):
                if text[i] == "\n":
                    if len(quote) < 3: break
                    line += 1
                i += 2 if text[i] == "\\" and ch != "«" else 1
            if i >= len(text) or not text.startswith(quote, i):
                e = DadError(f"علامة {ch} ما انقفلت بـ {quote} — أغلق النص."); e.line = begin; raise e
            i += len(quote); continue
        elif ch in closing: stack.append((ch, line))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                e = DadError(f"قوس «{ch}» زائد أو لا يطابق القوس المفتوح."); e.line = line; raise e
            stack.pop()
        i += 1
    if stack:
        ch, line = stack[0]
        suffix = "".join(closing[c] for c, _ in reversed(stack))
        opts = [text.splitlines()[line-1].strip()+suffix] if all(ln == line for _, ln in stack) else []
        e = DadError(f"القوس {ch} في هذا السطر ما انقفل — لازم يقابله {closing[ch]}.", opts)
        e.line = line; raise e


AI_DISABLED = "الذكاء الاصطناعي غير مسموح داخل تنفيذ الضاد. اكتب أوامر ثابتة تعمل بدون إنترنت."
