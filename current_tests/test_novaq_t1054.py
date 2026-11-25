"""t1054: beginner natural ask/save/greet, و/بعدين chaining, parentheses, English names."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / "dad.py"


def run_program(tmp_path, source, answers="", timeout=10):
    src = tmp_path / "case.dad"
    src.write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["DAD_OUT_DIR"] = str(tmp_path)
    return subprocess.run(
        [sys.executable, str(DAD), "شغل", str(src)],
        input=answers,
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        env=env,
        timeout=timeout,
    )


def out_text(r):
    return "\n".join(
        x for x in r.stdout.splitlines() if x.strip() and not x.startswith("@@")
    )


def test_saud_hello(tmp_path):
    r = run_program(tmp_path, "قول هلا سعود")
    assert r.returncode == 0, r.stderr
    assert "هلا سعود" in r.stdout


def test_ask_sheno_esmak_then_greet_aliases(tmp_path):
    r = run_program(tmp_path, "اسأل شنو اسمك\nقول اهلا اسمك", "سعود\n")
    assert r.returncode == 0, r.stderr
    assert "اهلا سعود" in out_text(r)


def test_ask_then_greet_fstring_alias(tmp_path):
    r = run_program(tmp_path, "اسأل شنو اسمك\nقول «أهلا {اسمك}»", "نورة\n")
    assert r.returncode == 0, r.stderr
    assert "أهلا نورة" in out_text(r)


def test_ask_then_greet_parentheses(tmp_path):
    r = run_program(tmp_path, "اسأل شنو اسمك\nقول اهلا (الاسم)", "خالد\n")
    assert r.returncode == 0, r.stderr
    assert "اهلا خالد" in out_text(r)


def test_saud_incomplete_save_is_friendly(tmp_path):
    r = run_program(tmp_path, "اسأل شنو اسمك و احفظه في", "سعود\n")
    assert r.returncode != 0
    assert "احفظه في" in r.stderr
    assert "هل تقصد:" in r.stderr
    assert "اسأل شنو اسمك واحفظه في الاسم" in r.stderr
    assert "احفظه في؟" not in r.stdout  # not swallowed as the question


def test_ask_and_save_in_named_var(tmp_path):
    r = run_program(tmp_path, "اسأل شنو اسمك و احفظه في الاسم\nقول اهلا (الاسم)", "منى\n")
    assert r.returncode == 0, r.stderr
    assert "شنو اسمك؟" in r.stdout
    assert "احفظه" not in r.stdout
    assert "اهلا منى" in out_text(r)


def test_wa_chains_two_commands(tmp_path):
    r = run_program(tmp_path, "قول هلا و قول مرحبا")
    assert r.returncode == 0, r.stderr
    assert out_text(r).splitlines() == ["هلا", "مرحبا"]


def test_ba3deen_chains_like_then(tmp_path):
    r = run_program(tmp_path, "احسب 5 زائد 3 بعدين قول الناتج")
    assert r.returncode == 0, r.stderr
    assert "8" in out_text(r)


def test_wa_in_plain_text_is_not_split(tmp_path):
    r = run_program(tmp_path, "قول تفاح و موز")
    assert r.returncode == 0, r.stderr
    assert "تفاح و موز" in r.stdout


def test_wa_in_if_condition_still_and(tmp_path):
    r = run_program(tmp_path, "إذا 5 أكبر من 3 و 2 أصغر من 9\n    قول نعم")
    assert r.returncode == 0, r.stderr
    assert "نعم" in r.stdout


def test_english_ask_name_fstring_and_paren(tmp_path):
    r = run_program(tmp_path, 'ask what is your name\nsay "hello {name}"\nsay hello (name)', "Saud\n")
    assert r.returncode == 0, r.stderr
    assert r.stdout.count("hello Saud") == 2


def test_english_whats_contraction(tmp_path):
    r = run_program(tmp_path, "ask what's your name\nsay name", "Bill\n")
    assert r.returncode == 0, r.stderr
    assert "Bill" in out_text(r)


def test_english_save_it_in(tmp_path):
    r = run_program(tmp_path, "ask what is your name and save it in name\nsay name", "Sara\n")
    assert r.returncode == 0, r.stderr
    assert "save" not in r.stdout.lower()
    assert "Sara" in out_text(r)


def test_paren_unknown_name_is_friendly(tmp_path):
    r = run_program(tmp_path, "قول اهلا (الاسم)")
    assert r.returncode != 0
    assert "الاسم" in r.stderr
    assert "هل تقصد:" in r.stderr
    assert "Traceback" not in r.stderr


def test_draw_pink_rect(tmp_path):
    r = run_program(tmp_path, "ارسم مستطيل وردي")
    assert r.returncode == 0, r.stderr
    svgs = list(tmp_path.glob("*.svg"))
    assert svgs
    assert "<rect" in svgs[0].read_text(encoding="utf-8")


def test_eggs_line_still_softened(tmp_path):
    r = run_program(tmp_path, "اسأل كم عدد البيض في السلة اكمل احسب\nقول عدد البيض في السلة", "6\n")
    assert r.returncode == 0, r.stderr
    assert "6" in out_text(r)


@pytest.fixture
def ide(tmp_path, monkeypatch):
    monkeypatch.setenv("DAD_WORK_DIR", str(tmp_path))
    monkeypatch.setenv("DAD_OUT_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("aldad_ide_t1054", ROOT / "aldad_ide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ide_path_ask_save_greet(ide):
    r = ide.run_program("اسأل شنو اسمك واحفظه في الاسم\nقول اهلا (الاسم)\nقول «أهلا {اسمك}»", "سعود\n")
    assert r["ok"], r["err"]
    out = r["out"]
    assert "اهلا سعود" in out
    assert "أهلا سعود" in out
    assert "احفظه" not in out


def test_atba_is_say_compatible(tmp_path):
    r = run_program(tmp_path, "اطبع «هلا»")
    assert r.returncode == 0, r.stderr
    assert "هلا" in r.stdout


def test_say_then_calc_without_separator_is_friendly(tmp_path):
    r = run_program(tmp_path, "قول هلا احسب 1")
    assert r.returncode != 0
    assert "أمرين" in r.stderr and "ثم" in r.stderr
    assert "قول «هلا احسب 1»" in r.stderr
    assert "قول هلا ثم احسب 1" in r.stderr
    assert "هلا احسب 1" not in r.stdout
