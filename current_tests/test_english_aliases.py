"""Natural English aliases for Novaq (proposed keyword table), patched local engine only.

`rep` is the short English for كرر. Dictionary كرر still means Python iter, so
`iter` is not used as the repeat command.
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


def test_english_say_prints(tmp_path):
    r = run_program(tmp_path, 'say "hello"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "hello"


def test_arabic_say_twin_still_works(tmp_path):
    r = run_program(tmp_path, "قول «هلا»")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "هلا"


def test_english_calc_plus_and_result(tmp_path):
    r = run_program(tmp_path, "calc 5 plus 3\nsay result")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "8"


def test_arabic_calc_zayd_and_natej(tmp_path):
    r = run_program(tmp_path, "احسب 5 زائد 3\nقول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "8"


def test_english_then_chain(tmp_path):
    r = run_program(tmp_path, 'say "hi" then calc 2 mul 4 then say result')
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["hi", "8"]


def test_arabic_then_chain(tmp_path):
    r = run_program(tmp_path, "قول «هلا» ثم احسب 2 ضرب 4 ثم قول الناتج")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["هلا", "8"]


def test_english_rep_times(tmp_path):
    r = run_program(tmp_path, 'rep 3 times\n    say "tick"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["tick", "tick", "tick"]


def test_english_rep_twice(tmp_path):
    r = run_program(tmp_path, 'rep twice\n    say "tick"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["tick", "tick"]


def test_arabic_repeat_still_works(tmp_path):
    r = run_program(tmp_path, "كرر 3 مرات\n    قول «tick»")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["tick", "tick", "tick"]


def test_english_ask_assignment(tmp_path):
    r = run_program(tmp_path, 'name = ask "Name?"\nsay name', "Saud\n")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "Saud"


def test_english_nested_ask(tmp_path):
    r = run_program(
        tmp_path,
        'دالة نظف(س):\n    أرجع نص(س).قص()\nقول نظف(ask "command?")',
        "  yes  \n",
    )
    assert r.returncode == 0, r.stderr
    assert "yes" in out_lines(r)[-1]


def test_arabic_nested_ask_still_works(tmp_path):
    r = run_program(
        tmp_path,
        'دالة نظف(س):\n    أرجع نص(س).قص()\nقول نظف(اسأل «أمر؟»)',
        "  نعم  \n",
    )
    assert r.returncode == 0, r.stderr
    assert "نعم" in out_lines(r)[-1]


def test_english_def_takes_return(tmp_path):
    r = run_program(tmp_path, "def double takes x return x mul 2\nsay double(5)")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "10"


def test_english_def_takes_and(tmp_path):
    r = run_program(tmp_path, "def add2 takes a and b return a plus b\nsay add2(4, 6)")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "10"


def test_python_def_still_works(tmp_path):
    r = run_program(tmp_path, "def triple(x):\n    return x * 3\nprint(triple(3))")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "9"


def test_english_if_gt_then(tmp_path):
    r = run_program(tmp_path, 'if 10 gt 3 then say "yes"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "yes"


def test_english_if_and_comparators(tmp_path):
    r = run_program(tmp_path, 'x = 8\nif x gt 5 and 2 lt 9 then say "both"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "both"


def test_python_if_colon_still_works(tmp_path):
    r = run_program(tmp_path, 'if 10 > 3:\n    say "pyif"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "pyif"


def test_english_more_continues_calc(tmp_path):
    r = run_program(tmp_path, "calc 10\nmore minus 3\nsay result")
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "7"


def test_english_add_to_list(tmp_path):
    r = run_program(tmp_path, 'box = []\nadd "a" to box\nadd 5 to box\nsay box')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "['a', 5]"


def test_english_show_alias(tmp_path):
    r = run_program(tmp_path, 'show "ready"')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "ready"


def test_iter_is_not_the_repeat_command(tmp_path):
    """كرر in the dictionary layer is Python iter; natural repeat is `rep`."""
    r = run_program(
        tmp_path,
        "xs = [1, 2, 3]\nit = iter(xs)\nsay next(it)\nsay next(it)",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["1", "2"]


def test_call_is_not_typo_corrected_to_calc(tmp_path):
    r = run_program(
        tmp_path,
        "def greet(n):\n    return n\nprint(greet('ok'))",
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "ok"
    r2 = run_program(tmp_path, "call 1 plus 1")
    # `call` must not be silently rewritten to calc
    assert r2.returncode != 0 or "2" not in out_lines(r2)


def test_english_word_ops_minus_div(tmp_path):
    r = run_program(tmp_path, "calc 20 minus 8\nsay result\ncalc 15 div 3\nsay result")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["12", "5"]


def test_english_say_concat_function_params(tmp_path):
    r = run_program(
        tmp_path,
        'def emit(kind, text):\n    say("RESULT " + kind + " " + text)\nemit("HELP", "P|Q")\n',
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "RESULT HELP P|Q"


def test_arabic_say_concat_function_params(tmp_path):
    r = run_program(
        tmp_path,
        'دالة أظهر(نوع, كلام):\n    قول("RESULT " + نوع + " " + كلام)\nأظهر("HELP", "P|Q")\n',
    )
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "RESULT HELP P|Q"
