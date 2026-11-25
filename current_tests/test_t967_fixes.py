"""Fixes approved for local 1.9.17 patch: diacritics, loop cap, صنف, conditions, dotted قول, nested اسأل.

Each behavior is tested in Arabic and in the English/Python-style layer.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / "dad.py"


def run_program(tmp_path, source, answers="", env_extra=None, timeout=10):
    src = tmp_path / "case.dad"
    src.write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["DAD_OUT_DIR"] = str(tmp_path)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(DAD), "شغل", str(src)],
        input=answers,
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        env=env,
        timeout=timeout,
    )


def out_lines(r):
    return [x.strip() for x in r.stdout.splitlines() if x.strip()]


def test_arabic_diacritics_on_command(tmp_path):
    r = run_program(tmp_path, "قُول «هلا»")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "هلا"


def test_english_rtl_mark_before_print(tmp_path):
    r = run_program(tmp_path, "\u200fprint('hi')")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "hi"


def test_arabic_rtl_mark_before_command(tmp_path):
    r = run_program(tmp_path, "\u200fقول «هلا»")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "هلا"


def test_arabic_shadda_in_identifier(tmp_path):
    r = run_program(tmp_path, "غيّر_السعر = 3\nقول غيّر_السعر")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "3"


def test_english_program_can_use_shadda_name(tmp_path):
    r = run_program(tmp_path, "غيّر_السعر = 3\nprint(غيّر_السعر)")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "3"


def test_arabic_infinite_loop_has_clear_error_instead_of_hang(tmp_path):
    t0 = time.monotonic()
    r = run_program(
        tmp_path,
        "طالما صح:\n    تجاوز",
        env_extra={"DAD_MAX_SECONDS": "1", "DAD_MAX_ITERS": "0"},
        timeout=6,
    )
    elapsed = time.monotonic() - t0
    assert r.returncode != 0
    assert "أخذ وقتًا أطول من المسموح" in r.stderr or "دارت مرات أكثر" in r.stderr
    assert elapsed < 5


def test_english_infinite_loop_has_clear_arabic_error(tmp_path):
    t0 = time.monotonic()
    r = run_program(
        tmp_path,
        "while True:\n    pass",
        env_extra={"DAD_MAX_SECONDS": "1", "DAD_MAX_ITERS": "0"},
        timeout=6,
    )
    elapsed = time.monotonic() - t0
    assert r.returncode != 0
    assert "أخذ وقتًا أطول من المسموح" in r.stderr or "دارت مرات أكثر" in r.stderr
    assert elapsed < 5


def test_arabic_class_is_not_typo_corrected_to_add(tmp_path):
    src = """صنف نقطة:
    دالة __init__(نفسه, س, ص):
        نفسه.س = س
        نفسه.ص = ص
ن = نقطة(3, 4)
قول(ن.س)
قول(ن.ص)
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert "صححت «صنف»" not in r.stderr
    assert out_lines(r)[-2:] == ["3", "4"]


def test_english_class_still_works(tmp_path):
    src = """class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
p = Point(3, 4)
print(p.x)
print(p.y)
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-2:] == ["3", "4"]


def test_arabic_if_with_function_call_condition(tmp_path):
    src = """الاسم = «»
إذا طول(الاسم) أصغر من 1
    قول «فارغ»
وإلا
    قول «مو فارغ»
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "فارغ"


def test_arabic_while_with_function_call_condition(tmp_path):
    src = """السجل = [1]
طالما طول(السجل) أصغر من 3:
    السجل.أضف(طول(السجل))
قول طول(السجل)
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "3"


def test_english_if_and_while_with_len(tmp_path):
    src = """name = ""
if len(name) < 1:
    print("empty")
items = [1]
while len(items) < 3:
    items.append(len(items))
print(len(items))
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["empty", "3"]


def test_arabic_say_dotted_attribute(tmp_path):
    src = """صنف سلعة:
    دالة __init__(نفسه, اسم):
        نفسه.اسم = اسم
س = سلعة(«تمر»)
قول(س.اسم)
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "تمر"


def test_english_print_dotted_attribute(tmp_path):
    src = """class Item:
    def __init__(self, name):
        self.name = name
item = Item("dates")
print(item.name)
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "dates"


def test_arabic_nested_ask_inside_call(tmp_path):
    src = """عرّف نظف ياخذ س ويرجع س
الأمر = نظف(اسأل «الأمر؟»)
قول الأمر
"""
    r = run_program(tmp_path, src, "خروج\n")
    assert r.returncode == 0, r.stderr
    assert "خروج" in out_lines(r)


def test_english_nested_input_inside_call(tmp_path):
    src = """def clean(s):
    return s.strip()
command = clean(input("command? "))
print(command)
"""
    r = run_program(tmp_path, src, "quit\n")
    assert r.returncode == 0, r.stderr
    assert any("quit" in x for x in out_lines(r))


def test_arabic_function_return_is_not_auto_printed(tmp_path):
    """Leftover list/help numbers were from the demo printing the return value, not the engine."""
    src = """عرّف مساعدة بدون مدخلات
    قول «قائمة الأوامر»
    أرجع 3
مساعدة()
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["قائمة الأوامر"]


def test_english_function_return_is_not_auto_printed(tmp_path):
    src = """def help():
    print("menu")
    return 3
help()
"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["menu"]
