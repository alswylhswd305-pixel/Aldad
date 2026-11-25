"""t1018: lower static calc to Python, cheap _dad_tick, f-strings, 1-based slices.

Patched local engine only.
"""
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / "dad.py"
sys.path.insert(0, str(ROOT))
import vnext  # noqa: E402
from aldad_syntax import DadError  # noqa: E402


def run_program(tmp_path, source, answers="", env_extra=None, timeout=15):
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


def generated(source):
    py, _ = vnext.expand(source)
    return py


# ---------------------------------------------------------------------------
# P1: lower static احسب / يرجع to real Python; evaluate() only for typed text
# ---------------------------------------------------------------------------

def test_static_calc_is_lowered_not_evaluate():
    py = generated("احفظ 0 في المجموع\nاحسب المجموع زائد 3 ضرب 2\nقول الناتج")
    assert "_dad_evaluate(" not in py
    assert "المجموع + 3 * 2" in py or "المجموع+3*2" in py.replace(" ", "")


def test_return_expr_is_lowered_not_evaluate():
    py = generated("عرّف ضعف ياخذ س ويرجع س ضرب 2\nاحسب ضعف(5)\nقول الناتج")
    assert "_dad_evaluate(" not in py
    assert "س * 2" in py or "س*2" in py.replace(" ", "")


def test_interactive_calc_still_uses_evaluate():
    src = inspect.getsource(vnext._dad_calc_ask)
    assert "evaluate(" in src
    py = generated("احسب")
    assert "_dad_calc_ask(" in py
    assert "_dad_tmp =" not in py


def test_arabic_calc_plus_mul_still_correct(tmp_path):
    r = run_program(tmp_path, "احفظ 10 في المجموع\nاحسب المجموع زائد 3 ضرب 2\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "16"


def test_calc_user_function_and_builtin(tmp_path):
    r = run_program(
        tmp_path,
        "عرّف ضعف ياخذ س ويرجع س ضرب 2\nاحسب ضعف(5)\nقول الناتج\nاحسب طول([1, 2, 3])\nقول الناتج",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-2:] == ["10", "3"]


def test_calc_full_precision_and_six_decimal_display(tmp_path):
    r = run_program(tmp_path, "احسب 1 قسمه 3\nقول الناتج\nقول الناتج * 3")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["0.333333", "1"]


def test_divzero_caught_and_arabic_message(tmp_path):
    r = run_program(
        tmp_path,
        "حاول:\n    احسب 10 قسمة 0\n    قول «ما انمسك»\nعند_خطأ باسم خ:\n    قول خ",
    )
    assert r.returncode == 0, r.stderr
    lines = out_lines(r)
    assert lines[0] != "ما انمسك"
    text = "\n".join(lines)
    assert "صفر" in text or "قسمة" in text or "صفر" in r.stdout
    # bilingual-ish: Arabic message preserved
    assert "صفر" in text or "division" in text.lower() or "قسمة" in text


def test_continue_uses_active_value_not_evaluate(tmp_path):
    py = generated("احسب 10\nأكمل ضرب 3\nقول الناتج")
    assert "_dad_evaluate(" not in py
    assert "_dad_active" in py
    r = run_program(tmp_path, "احسب 10\nأكمل ضرب 3\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "30"


def test_interactive_typed_calc_still_works(tmp_path):
    r = run_program(tmp_path, "احسب", answers="2 زائد 3\n")
    assert r.returncode == 0, r.stderr
    assert "5" in r.stdout


# ---------------------------------------------------------------------------
# P2: cheap _dad_tick, cached limits, clock every 1024, 8s/1M cap kept
# ---------------------------------------------------------------------------

def test_tick_source_has_no_reimport_or_environ():
    src = inspect.getsource(vnext._dad_tick)
    assert "__import__" not in src
    assert "environ" not in src
    assert "1024" in inspect.getsource(vnext) or vnext._TICK_CLOCK_EVERY == 1024


def test_reset_caches_limits():
    old_s, old_i = os.environ.get("DAD_MAX_SECONDS"), os.environ.get("DAD_MAX_ITERS")
    try:
        os.environ["DAD_MAX_SECONDS"] = "3"
        os.environ["DAD_MAX_ITERS"] = "50"
        vnext._dad_reset_limits()
        assert vnext._LIMIT["max_s"] == 3.0
        assert vnext._LIMIT["max_i"] == 50
        # later env change is ignored until reset
        os.environ["DAD_MAX_SECONDS"] = "9"
        os.environ["DAD_MAX_ITERS"] = "9"
        assert vnext._dad_limit_settings() == (3.0, 50)
        vnext._dad_reset_limits()
        assert vnext._dad_limit_settings() == (9.0, 9)
    finally:
        for k, v in (("DAD_MAX_SECONDS", old_s), ("DAD_MAX_ITERS", old_i)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        vnext._dad_reset_limits()


def test_iter_cap_still_fires(tmp_path):
    r = run_program(
        tmp_path,
        "طالما صح:\n    س = 1",
        env_extra={"DAD_MAX_SECONDS": "0", "DAD_MAX_ITERS": "100"},
    )
    assert r.returncode != 0
    assert "الحلقة دارت" in (r.stderr + r.stdout)


def test_time_cap_still_fires(tmp_path):
    r = run_program(
        tmp_path,
        "طالما صح:\n    س = 1",
        env_extra={"DAD_MAX_SECONDS": "1", "DAD_MAX_ITERS": "0"},
        timeout=8,
    )
    assert r.returncode != 0
    assert "وقت" in (r.stderr + r.stdout)


def test_caps_disabled_when_both_zero_finishes(tmp_path):
    # A 2000-iter loop would hit a stale 1M/8s cap if limits were not honored as 0.
    r = run_program(
        tmp_path,
        "احفظ 0 في س\nكرر 2000 مرات:\n    احسب س زائد 1\n    احفظ الناتج في س\nقول س",
        env_extra={"DAD_MAX_SECONDS": "0", "DAD_MAX_ITERS": "0"},
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "2000"


# ---------------------------------------------------------------------------
# Easy f-strings
# ---------------------------------------------------------------------------

def test_arabic_fstring_variable(tmp_path):
    r = run_program(tmp_path, "الاسم = «سعود»\nقول «مرحبا {الاسم}»")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "مرحبا سعود"


def test_english_fstring_variable(tmp_path):
    r = run_program(tmp_path, 'name = "Saud"\nsay "hello {name}"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "hello Saud"


def test_fstring_expression_and_arabic_ops(tmp_path):
    r = run_program(
        tmp_path,
        "س = 5\nقول «المجموع {س ضرب 2}»\nsay \"n={س + 1}\"",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-2:] == ["المجموع 10", "n=6"]


def test_fstring_escaped_braces(tmp_path):
    r = run_program(tmp_path, r'say "shown {{name}}"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "shown {name}"


def test_fstring_empty_brace_errors():
    with pytest.raises(DadError):
        generated('قول «هلا {}»')


# ---------------------------------------------------------------------------
# Easy slicing: 1-based inclusive (beginner-friendly). Index 1 is the first item.
# قطعة القائمة من 1 إلى 3  ==  first, second and third items  ==  Python list[0:3]
# 0 or negative is an error. Omitting the end runs to the end of the sequence.
# Mid-line Python slice() is left alone.
# ---------------------------------------------------------------------------

def test_arabic_slice_one_based_inclusive(tmp_path):
    r = run_program(
        tmp_path,
        "القائمة = [10, 20, 30, 40, 50]\nقول قطعة القائمة من 1 إلى 3",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "[10, 20, 30]"


def test_english_slice_one_based_inclusive(tmp_path):
    r = run_program(
        tmp_path,
        "items = [10, 20, 30, 40, 50]\nsay slice items from 1 to 3",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "[10, 20, 30]"


def test_slice_from_only_to_end(tmp_path):
    r = run_program(
        tmp_path,
        "القائمة = [10, 20, 30, 40]\nقول قطعة القائمة من 3",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "[30, 40]"


def test_slice_assignment_and_save(tmp_path):
    r = run_program(
        tmp_path,
        "القائمة = [10, 20, 30, 40, 50]\n"
        "الجزء = قطعة القائمة من 1 إلى 3\n"
        "احفظ قطعة القائمة من 2 إلى 2 في واحد\n"
        "قول الجزء\nقول واحد",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-2:] == ["[10, 20, 30]", "[20]"]


def test_slice_zero_and_negative_are_errors(tmp_path):
    r0 = run_program(tmp_path, "القائمة = [1, 2, 3]\nقول قطعة القائمة من 0 إلى 2")
    assert r0.returncode != 0
    msg = r0.stderr + r0.stdout
    assert "1" in msg and ("0" in msg or "1-based" in msg or "الأول" in msg)
    rneg = run_program(tmp_path, "القائمة = [1, 2, 3]\nsay slice القائمة from -1 to 2")
    assert rneg.returncode != 0


def test_python_slice_call_not_stolen(tmp_path):
    # Mid-line / assignment Python slice() stays the builtin (0-based, end exclusive).
    r = run_program(tmp_path, "س = slice(1, 3)\nقول س\nق = [10, 20, 30, 40]\nقول ق[س]")
    assert r.returncode == 0, r.stderr
    lines = out_lines(r)
    assert "slice(1, 3" in lines[0]
    assert lines[1] == "[20, 30]"


def test_standalone_slice_prints(tmp_path):
    r = run_program(tmp_path, "القائمة = [10, 20, 30]\nقطعة القائمة من 1 إلى 2")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "[10, 20]"
