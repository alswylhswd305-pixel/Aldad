"""t1037: natural ask sentences, beginner shapes, IDE examples and EXE button."""
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


def out_lines(r):
    return [x.strip() for x in r.stdout.splitlines() if x.strip() and not x.startswith("@@")]


def test_ask_eggs_in_basket_without_quotes(tmp_path):
    r = run_program(tmp_path, "اسأل كم عدد البيض في السلة\nقول عدد البيض في السلة", "6\n")
    assert r.returncode == 0, r.stderr
    assert out_lines(r) == ["كم عدد البيض في السلة؟ 6", "6"]


def test_ask_eggs_then_continue_calc_words_are_softened(tmp_path):
    """The line from Saud's screenshot: question + trailing اكمل احسب."""
    r = run_program(
        tmp_path,
        "اسأل كم عدد البيض في السلة اكمل احسب\nقول عدد البيض في السلة",
        "8\n",
    )
    assert r.returncode == 0, r.stderr
    assert "كم عدد البيض في السلة؟ 8" in r.stdout
    assert out_lines(r)[-1] == "8"
    assert "فهمت السؤال كـ: اسأل كم عدد البيض في السلة" in r.stderr
    assert "أمرين" not in r.stderr


def test_english_ask_eggs_in_basket(tmp_path):
    r = run_program(tmp_path, "ask how many eggs in the basket\nsay how many eggs in the basket", "4\n")
    assert r.returncode == 0, r.stderr
    assert "4" in r.stdout


def test_ambiguous_say_calc_still_fails_with_copyable_fix(tmp_path):
    r = run_program(tmp_path, "قول كم عدد بيض احسب ثم قول «وصلنا»", "7\n")
    assert r.returncode != 0
    assert "أمرين" in r.stderr and "ثم" in r.stderr
    assert "وصلنا" not in r.stdout
    assert "هل تقصد:" in r.stderr
    assert "قول «كم عدد بيض احسب»" in r.stderr
    assert "قول كم عدد بيض ثم احسب" in r.stderr


def test_ask_with_real_second_command_suggests_then(tmp_path):
    # احسب at the end with an operand is a second command, not filler.
    r = run_program(tmp_path, "اسأل كم العدد اكمل زائد 1", "5\n")
    assert r.returncode != 0, r.stdout + r.stderr
    assert "أمرين" in r.stderr
    assert "اسأل كم العدد" in r.stderr
    assert "ثم" in r.stderr
    assert "اكمل زائد 1" in r.stderr


def _svg(tmp_path, source):
    r = run_program(tmp_path, source)
    assert r.returncode == 0, r.stderr
    svgs = list(tmp_path.glob("*.svg"))
    assert svgs, r.stdout + r.stderr
    return svgs[0].read_text(encoding="utf-8")


def test_draw_red_circle_arabic(tmp_path):
    svg = _svg(tmp_path, "ارسم دائرة حمراء")
    assert "<circle" in svg
    assert "#D84A3A" in svg


def test_draw_blue_square_english(tmp_path):
    svg = _svg(tmp_path, "draw a blue square")
    assert "<rect" in svg
    assert "#2F6FD0" in svg


def test_draw_circle_and_square_together(tmp_path):
    svg = _svg(tmp_path, "ارسم دائرة حمراء ومربع أزرق")
    assert "<circle" in svg and "<rect" in svg
    assert "#D84A3A" in svg and "#2F6FD0" in svg


def test_draw_with_color_word_blon(tmp_path):
    svg = _svg(tmp_path, "ارسم دائرة بلون أخضر")
    assert "<circle" in svg
    assert "#3A9D5D" in svg


def test_unknown_draw_still_rejected(tmp_path):
    r = run_program(tmp_path, "ارسم بطيخة")
    assert r.returncode != 0
    assert "ما أعرف أرسم" in r.stderr


@pytest.fixture
def ide(tmp_path, monkeypatch):
    monkeypatch.setenv("DAD_WORK_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("aldad_ide_t1037", ROOT / "aldad_ide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ide_examples_ready(ide):
    assert 5 <= len(ide.IDE_EXAMPLES) <= 8
    ids = {e["id"] for e in ide.IDE_EXAMPLES}
    assert "hello_ar" in ids and "hello_en" in ids
    assert "shapes_ar" in ids
    # Every example is valid Novaq (draw/say may need no stdin).
    for ex in ide.IDE_EXAMPLES:
        assert "قول" in ex["code"] or "say" in ex["code"] or "ارسم" in ex["code"] or "draw" in ex["code"] or "اسأل" in ex["code"] or "ask" in ex["code"]


def test_ide_build_exe_does_not_auto_install(ide):
    src = Path(ide.__file__).read_text(encoding="utf-8") if getattr(ide, "__file__", None) else (ROOT / "aldad_ide.py").read_text(encoding="utf-8")
    # The installer is never invoked; the string may appear only in the help message.
    assert 'subprocess.run([sys.executable, "-m", "pip"' not in src
    assert "ما ثبّتّها تلقائياً" in src
    r = ide.build_exe_program("قول هلا", "hello")
    assert r["ok"] is False
    assert "PyInstaller" in r["error"] or "Windows" in r["error"]


def test_ide_page_has_exe_button_and_examples_menu(ide):
    page = ide.PAGE
    assert "bExe" in page and "📦 EXE" in page
    assert "أمثلة" in page
    assert "/examples" in page or "fillExamples" in page
    assert "نوفاك" in page
