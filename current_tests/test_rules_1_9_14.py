from __future__ import annotations
import os, subprocess, sys, tempfile
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / "dad.py"

def run(code: str, answers: str = ""):
    with tempfile.NamedTemporaryFile("w", suffix=".dad", encoding="utf-8", delete=False) as f:
        f.write(code + ("\n" if not code.endswith("\n") else "")); path=f.name
    try:
        env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", DAD_LM_BASE="http://127.0.0.1:9/v1")
        p=subprocess.run([sys.executable, str(DAD), "run", path], input=answers, text=True,
                         capture_output=True, encoding="utf-8", timeout=10, cwd=str(ROOT), env=env)
        return p.returncode, p.stdout.replace("\r\n","\n"), p.stderr.replace("\r\n","\n")
    finally:
        try: os.unlink(path)
        except OSError: pass

def lines(out): return [x.strip() for x in out.splitlines() if x.strip()]

OK_CASES = [
    ("اسأل كم العدد\nكمل ناقص 4\nقول الناتج", "22\n", ["كم العدد؟ 22", "18"]),
    ("احسب 10 ضرب 2\nاسأل كم العدد\nكمل زائد 5\nقول الناتج", "7\n", ["كم العدد؟ 7", "12"]),
    ("احسب 10 ضرب 2\nقول (هلا)\nكمل زائد 5\nقول الناتج", "", ["هلا", "25"]),
    ("قول كم عدد البيض\nكمل ناقص 3\nقول الناتج", "8\n", ["كم عدد البيض؟ 8", "8", "5"]),
    ("اسأل كم العدد\nأكمل زائد 1\nقول الناتج", "5\n", ["كم العدد؟ 5", "6"]),
    ("اسأل كم العدد\nاكمل زائد 1\nقول الناتج", "5\n", ["كم العدد؟ 5", "6"]),
    ("اسأل كم العدد\nاسأل كم العدد\nقول العدد", "4\n9\n", ["كم العدد؟ 4", "كم العدد؟ 9", "9"]),
    ("احسب 2 زائد 3 ضرب 4\nقول الناتج", "", ["14"]),
    ("احسب (2 زائد 3) ضرب 4\nقول الناتج", "", ["20"]),
    ("اسأل كم العدد ثم احسب العدد ضرب 2 ثم قول الناتج", "6\n", ["كم العدد؟ 6", "12"]),
    ("احسب 10 زائد 5\nكرر 2 مرات\n    كمل زائد 1\nقول الناتج", "", ["17"]),
    ("احسب 10 زائد 5\nإذا الناتج أكبر من 10\n    كمل زائد 2\nقول الناتج", "", ["17"]),
]
ERR_CASES = [
    ("كم العدد", "", "«كم» كلمة سؤال وليست أمراً لوحدها"),
    ("كمل ناقص 3", "", "«كمل» تحتاج قيمة قديمة تكمل عليها"),
    ("الناتج = 5", "", "«الناتج» اسم محجوز"),
    ("كم = 5", "", "«كم» اسم محجوز"),
    ("اسأل كم الناتج", "", "«الناتج» اسم محجوز"),
    ("اسأل وش الاسم\nاحسب الاسم ضرب 2", "سعود\n", "«احسب» لقت كلام مو رقم"),
    ("احسب 5 ضرب ثم قول الناتج", "", "ما فهمت الحساب"),
]

@pytest.mark.parametrize("code,answers,want", OK_CASES)
def test_valid_rules(code, answers, want):
    rc,out,err=run(code,answers)
    assert rc == 0, out+err
    assert lines(out) == want
    assert "Traceback" not in out+err

@pytest.mark.parametrize("code,answers,msg", ERR_CASES)
def test_rule_errors(code, answers, msg):
    rc,out,err=run(code,answers)
    text=out+err
    assert rc != 0
    assert msg in text
    assert "Traceback" not in text
