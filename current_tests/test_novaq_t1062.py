"""t1062: beginner guide examples and no user-facing الضاد in the IDE UI."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / "dad.py"
IDE = ROOT / "aldad_ide.py"


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


def _load_ide(tmp_path):
    os.environ["DAD_WORK_DIR"] = str(tmp_path)
    # A fresh load is safer than reusing a module imported under another work dir.
    sys.modules.pop("aldad_ide_t1062", None)
    spec = importlib.util.spec_from_file_location("aldad_ide_t1062", IDE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_guide_has_eight_ordered_lessons(tmp_path):
    ide = _load_ide(tmp_path)
    ids = [e["id"] for e in ide.IDE_GUIDE]
    assert ids == [
        "g_say",
        "g_ask",
        "g_save_greet",
        "g_calc",
        "g_then",
        "g_if",
        "g_rep",
        "g_draw",
    ]
    for e in ide.IDE_GUIDE:
        assert e["title"].strip()
        assert e["explain"].strip()
        assert e["code"].strip()
        assert "شغّل المثال" in ide.PAGE
        assert "دليل المبتدئ" in ide.PAGE
        assert "bGuide" in ide.PAGE


@pytest.mark.parametrize("lesson_id", [
    "g_say", "g_ask", "g_save_greet", "g_calc",
    "g_then", "g_if", "g_rep", "g_draw",
])
def test_guide_lesson_runs(tmp_path, lesson_id):
    ide = _load_ide(tmp_path)
    les = next(e for e in ide.IDE_GUIDE if e["id"] == lesson_id)
    r = run_program(tmp_path, les["code"], les.get("answers") or "")
    assert r.returncode == 0, r.stderr
    out = out_text(r)
    if lesson_id == "g_say":
        assert out == "هلا يا سعود"
    elif lesson_id == "g_ask":
        assert "شنو اسمك؟" in r.stdout
        assert out.splitlines()[-1] == "سعود"
    elif lesson_id == "g_save_greet":
        assert "شنو اسمك؟" in r.stdout
        assert "اهلا نورة" in out
        assert "أهلا نورة" in out
    elif lesson_id == "g_calc":
        assert out.strip() == "11"
    elif lesson_id == "g_then":
        assert out.strip() == "8"
    elif lesson_id == "g_if":
        assert "كم العمر؟" in r.stdout
        assert "إنت بالغ" in out
    elif lesson_id == "g_rep":
        assert out.splitlines() == ["هلا", "هلا", "هلا"]
    elif lesson_id == "g_draw":
        assert "@@DAD_IMAGE@@" in r.stdout
        paths = [ln.split("@@DAD_IMAGE@@", 1)[1].strip() for ln in r.stdout.splitlines() if "@@DAD_IMAGE@@" in ln]
        assert paths
        svg = Path(paths[0])
        assert svg.is_file()
        text = svg.read_text(encoding="utf-8")
        assert "<svg" in text.lower() or "<circle" in text.lower() or "دائرة" in text
        # red circle + blue square should appear as shapes
        low = text.lower()
        assert "circle" in low or "ellipse" in low
        assert "rect" in low or "polygon" in low or "square" in low


def test_ide_ui_has_no_user_facing_aldad(tmp_path):
    ide = _load_ide(tmp_path)
    page = ide.PAGE
    # The only allowed user-facing occurrence is the historic .ضاد extension.
    cleaned = page.replace(".ضاد", "")
    assert "الضاد" not in cleaned
    assert "ضاد" not in cleaned
    assert "Aldad" not in cleaned
    assert "ALDAD" not in cleaned
    assert "نوفاك" in page
    assert "نوفاك›" in page
    assert "طرفية نوفاك" in page

    # Startup / error messages shown to the user (not filesystem fallbacks).
    src = IDE.read_text(encoding="utf-8")
    forbidden = [
        "ضاد IDE",
        "طرفية الضاد",
        "ضاد›",
        "ملفات محرك الضاد",
        "ما اشتغل ضاد IDE",
        "تشغّل الضاد",
        "جسر ضاد IDE",
        "مكتوب بالضاد",
        "لغة الضاد",
        "Starting Aldad",
    ]
    for phrase in forbidden:
        assert phrase not in src, phrase


def test_rules_document_today_natural_patterns():
    rules = (ROOT / "rules_ar.md").read_text(encoding="utf-8")
    for needle in [
        "نوفاك",
        "واحفظه في",
        "(الاسم)",
        "{اسمك}",
        "بعدين",
        "قول «أهلا {اسمك}»",
        "قطعة القائمة من 1 إلى 3",
        "ارسم",
        "ask",
        "say",
    ]:
        assert needle in rules, needle
