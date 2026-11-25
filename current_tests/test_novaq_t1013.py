"""t1013: calc functions/precision/divzero, booleans, name clashes, dicts, files, try/catch.

Arabic and English for each behavior. Patched local engine only.
"""
import os
import subprocess
import sys
from pathlib import Path

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


def test_arabic_calc_user_function(tmp_path):
    r = run_program(tmp_path, "عرّف ضعف ياخذ س ويرجع س ضرب 2\nاحسب ضعف(5)\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "10"


def test_english_calc_user_function(tmp_path):
    r = run_program(tmp_path, "def double takes x return x mul 2\ncalc double(5)\nsay result")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "10"


def test_arabic_calc_builtin_len(tmp_path):
    r = run_program(tmp_path, "احسب طول([1, 2, 3])\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "3"


def test_english_calc_builtin_abs(tmp_path):
    r = run_program(tmp_path, "calc abs(-7)\nsay result")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "7"


def test_calc_stores_full_precision(tmp_path):
    r = run_program(tmp_path, "احسب 1 قسمه 3\nقول الناتج\nقول الناتج * 3")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["0.333333", "1"]


def test_calc_display_trims_zeros(tmp_path):
    r = run_program(tmp_path, "calc 0.1 plus 0.2\nsay result")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "0.3"


def test_arabic_divzero_caught_by_try(tmp_path):
    r = run_program(
        tmp_path,
        "حاول:\n    احسب 10 قسمة 0\n    قول «ما انمسك»\nعند_خطأ:\n    قول «انمسك»",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "انمسك"


def test_english_divzero_caught_by_catch(tmp_path):
    r = run_program(
        tmp_path,
        'try:\n    calc 10 div 0\n    say "not caught"\ncatch:\n    say "caught"',
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "caught"


def test_divzero_message_is_bilingual_and_printable(tmp_path):
    r = run_program(
        tmp_path,
        "حاول:\n    احسب 10 قسمة 0\nعند_خطأ باسم خ:\n    قول خ",
    )
    assert r.returncode == 0, r.stderr
    msg = out_lines(r)[-1]
    assert "قسمة على صفر" in msg
    assert "Division by zero" in msg


def test_uncaught_divzero_still_clear(tmp_path):
    r = run_program(tmp_path, "احسب 10 قسمة 0")
    assert r.returncode != 0
    assert "قسمة على صفر" in (r.stderr or "")
    assert "Division by zero" in (r.stderr or "")


def test_try_else_and_finally(tmp_path):
    r = run_program(
        tmp_path,
        "حاول:\n    احسب 1 زائد 1\nعند_خطأ:\n    قول «لا»\nعند_نجاح:\n    قول «نعم»\nأخيرا:\n    قول «تم»",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["نعم", "تم"]


def test_save_function_call_stores_result(tmp_path):
    r = run_program(tmp_path, "عرّف ضعف ياخذ س ويرجع س ضرب 2\nاحفظ ضعف(5) في القيمة\nقول القيمة")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "10"


def test_true_false_saved_as_booleans(tmp_path):
    r = run_program(
        tmp_path,
        "احفظ صح في العلم\nقول العلم\nقول نوع(العلم)\nاحفظ خطأ في العلم2\nقول العلم2\nقول نوع(العلم2)",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["صح", "<class 'bool'>", "خطأ", "<class 'bool'>"]


def test_nisef_as_variable_not_fraction(tmp_path):
    r = run_program(tmp_path, "احفظ 10 في نصف\nاحسب نصف\nقول الناتج\nاحسب نصف زائد 1\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["10", "11"]


def test_fraction_word_still_works_when_undefined(tmp_path):
    r = run_program(tmp_path, "احسب نصف 90\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "45"


def test_al_ard_is_not_show_command(tmp_path):
    r = run_program(tmp_path, "العرض = 7\nقول العرض")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "7"


def test_arabic_dict_put_and_get(tmp_path):
    r = run_program(
        tmp_path,
        "قاموس بيانات\nضع «اسم» في بيانات بقيمة «علي»\nقول بيانات['اسم']",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "علي"


def test_english_dict_put_and_get(tmp_path):
    r = run_program(
        tmp_path,
        'dict box\nput "name" in box as "Ali"\nsay box["name"]',
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "Ali"


def test_english_write_read_append(tmp_path):
    r = run_program(
        tmp_path,
        'write "hello" in note.txt\nread "note.txt"\nsay المحتوى\nappend "!" in "note.txt"\nread "note.txt"\nsay المحتوى',
    )
    assert r.returncode == 0, r.stderr
    assert "hello" in out_lines(r)
    assert "hello!" in out_lines(r)
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "hello!"


def test_arabic_write_read_append(tmp_path):
    r = run_program(
        tmp_path,
        "احفظ «hello» في note.txt\nافتح note.txt\nقول المحتوى\nألحق «!» في note.txt\nافتح note.txt\nقول المحتوى",
    )
    assert r.returncode == 0, r.stderr
    assert "hello" in out_lines(r)
    assert "hello!" in out_lines(r)
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "hello!"
