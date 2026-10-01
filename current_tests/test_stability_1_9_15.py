"""Behavior tests written before the engine fixes; all cases run real programs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get("ALDAD_TEST_ENGINE", ROOT / "dad.py"))


def run_program(tmp_path, code, answers="", args="run"):
    path = tmp_path / "program.dad"
    path.write_text(code + "\n", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               DAD_OUT_DIR=str(tmp_path), DAD_LM_BASE="http://127.0.0.1:9/v1")
    result = subprocess.run([sys.executable, str(ENGINE), args, str(path)],
                            input=answers, text=True, encoding="utf-8",
                            capture_output=True, timeout=10, cwd=tmp_path, env=env)
    assert "Traceback" not in result.stdout + result.stderr
    return result


def output(result):
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


VALID = [
    ("احسب 20\nإذا 1 أكبر من 2\n    اسأل كم العدد\nكمل زائد 3\nقول الناتج", "", ["23"]),
    ("احسب 20\nكرر 0 مرات\n    اسأل كم العدد\nكمل زائد 3\nقول الناتج", "", ["23"]),
    ("احسب 20\nالسلة = []\nلكل عنصر في السلة\n    اسأل كم العدد\nكمل زائد 3\nقول الناتج", "", ["23"]),
    ("احسب 20\nإذا 1 أكبر من 0\n    اسأل كم العدد\nوإلا\n    اسأل كم السعر\nكمل زائد 3\nقول الناتج", "7\n", ["كم العدد؟ 7", "10"]),
    ("احسب 20\nعرّف ضعف ياخذ س\n    اسأل كم العدد\n    أرجع س ضرب 2\nكمل زائد 3\nقول الناتج", "", ["23"]),
    ("اسأل كم العدد\nالعدد = 99\nكمل زائد 3\nقول الناتج\nقول العدد", "7\n", ["كم العدد؟ 7", "10", "99"]),
    ("اسأل كم العدد\nقول هلا\nقول العدد\nكمل ناقص 4\nقول الناتج\nقول العدد", "22\n", ["كم العدد؟ 22", "هلا", "22", "18", "22"]),
    ("احسب 10\nقول 2 زائد 3\nكمل زائد 1\nقول الناتج", "", ["5", "11"]),
    ("اسأل كم العدد ثم اسأل كم العدد ثم اسأل كم العدد ثم كمل زائد 1 ثم قول الناتج", "1\n5\n9\n", ["كم العدد؟ 1", "كم العدد؟ 5", "كم العدد؟ 9", "10"]),
    ("كرر مرتين\n    اسأل كم العدد\n    كمل ضرب 2\n    قول الناتج", "3\n7\n", ["كم العدد؟ 3", "6", "كم العدد؟ 7", "14"]),
    ("احسب 1\nكرر 2 مرات\n    كرر 3 مرات\n        كمل زائد 1\nقول الناتج", "", ["7"]),
    ("العدد = 7\nقول كم العدد\nكمل زائد 1\nقول الناتج", "9\n", ["كم العدد؟ 9", "9", "10"]),
    ("اسأل كم عدد البيض ثم احسب عدد البيض ناقص 4 ثم قول الناتج ثم قول عدد البيض", "22\n", ["كم عدد البيض؟ 22", "18", "22"]),
    ("السلة = [1، 2]\nاسأل كم عدد البيض في السلة\nقول السلة\nقول عدد البيض في السلة", "7\n", ["كم عدد البيض في السلة؟ 7", "[1, 2]", "7"]),
    ("اسأل كم سعر القطعة\nاسأل كم سعر الكرتون\nقول سعر القطعة\nقول سعر الكرتون", "5\n20\n", ["كم سعر القطعة؟ 5", "كم سعر الكرتون؟ 20", "5", "20"]),
    ("احفظ 22 في البيض\nاحسب البيض ناقص 4\nقول الناتج\nقول البيض", "", ["18", "22"]),
    ("احسب 8 ثم احفظ الناتج في مجموع الطلب ثم كمل زائد 2 ثم قول مجموع الطلب ثم قول الناتج", "", ["8", "10"]),
    ("احفظ «سعود» في الاسم\nقول الاسم\nاسأل وش الاسم\nقول الاسم", "علي\n", ["سعود", "وش الاسم؟ علي", "علي"]),
    ("احفظ «قول ثم احسب» في الرسالة\nقول الرسالة", "", ["قول ثم احسب"]),
    ("احفظ [1، 2] في السلة\nأضف 3 إلى السلة\nلكل عنصر في السلة\n    قول عنصر", "", ["1", "2", "3"]),
    ("احسب (2 زائد 3) ضرب (4 ناقص 1)\nقول الناتج", "", ["15"]),
    ("احسب ((2 زائد 3) ضرب 4) قسمة 2\nقول الناتج", "", ["10"]),
    ("احسب -5 زائد 2 ضرب 3\nقول الناتج", "", ["1"]),
    ("احسب 2 أس 3 أس 2\nقول الناتج", "", ["512"]),
    ("احسب 8 قسمة 4 ضرب 2\nقول الناتج", "", ["4"]),
    ("احسب ٠٫٥ زائد ١٫٢٥\nقول الناتج", "", ["1.75"]),
    ("احسب 5 ثم كمل ضرب (2 زائد 3) ثم قول الناتج", "", ["25"]),
    ("احسب 5\nإذا (الناتج زائد 1) أكبر من 5\n    كمل زائد 2\nقول الناتج", "", ["7"]),
    ("احسب 2\nإذا الناتج يساوي 1\n    قول واحد\nوإلا إذا الناتج يساوي 2\n    قول اثنين\nوإلا\n    قول غيره", "", ["اثنين"]),
    ("قول «اسأل ثم احسب ثم كمل» ثم قول 'هلا ثم وداع'", "", ["اسأل ثم احسب ثم كمل", "هلا ثم وداع"]),
    ("قول «قال: \\\"ثم\\\"» ثم قول نعم", "", ['قال: \\"ثم\\"', "نعم"]),
    ("احسب 2 زائد 3 # ثم اسأل كم العدد\nقول الناتج", "", ["5"]),
    ("قول هلا # احسب ثم اسأل", "", ["هلا"]),
    ("احسب 1\nكمل زائد 1 ثم كرر 3 مرات\nقول الناتج", "", ["4"]),
    ("عرّف عداد بدون مدخلات\n    احسب 1\n    كمل زائد 1 ثم كرر 3 مرات\n    أرجع الناتج\nقول عداد()", "", ["4"]),
    ("احسب 20\nعرّف عداد بدون مدخلات\n    احسب 1\n    كمل زائد 2\n    أرجع الناتج\nقول عداد()\nكمل زائد 3\nقول الناتج", "", ["3", "23"]),
    ("احسب 10\nلكل عنصر في السلة\n    كمل زائد عنصر\nقول الناتج", "", ["16"]),
]
# Collection setup is part of the program, rather than a hidden fixture.
VALID[-1] = ("السلة = [1، 2، 3]\n" + VALID[-1][0], "", ["16"])


@pytest.mark.parametrize("code,answers,want", VALID)
def test_valid_programs(tmp_path, code, answers, want):
    result = run_program(tmp_path, code, answers)
    assert result.returncode == 0, result.stdout + result.stderr
    assert output(result) == want


@pytest.mark.parametrize("space", ["", " ", "  ", "\t", "\u00a0"])
@pytest.mark.parametrize("body,want", [("هلا", "هلا"), ("الناتج", "8"), ("5 زائد 3", "8")])
def test_space_before_parenthesis_has_one_meaning(tmp_path, space, body, want):
    r = run_program(tmp_path, f"احسب 8\nقول{space}({body})")
    assert r.returncode == 0, r.stderr
    assert output(r) == [want]


@pytest.mark.parametrize("sep", [" ثم ", "  ثم  ", "\tثم\t", "\u00a0ثم\u00a0"])
def test_long_chains_and_whitespace(tmp_path, sep):
    code = sep.join(["احسب 0"] + ["كمل زائد 1"] * 80 + ["قول الناتج"])
    r = run_program(tmp_path, code)
    assert r.returncode == 0, r.stderr
    assert output(r) == ["80"]


ERRORS = [
    ("احسب 5 ضرب", "", "العملية ناقصة", "بعد «ضرب»"),
    ("احسب 5 زائد", "", "العملية ناقصة", "بعد «زائد»"),
    ("احسب 5 قسمة", "", "العملية ناقصة", "بعد «قسمة»"),
    ("احسب 5 ضرب قسمة 2", "", "عمليتين", ""),
    ("احسب 5 2", "", "عملية", ""),
    ("احسب (5 زائد 3", "", "القوس", ""),
    ("احسب 5 زائد 3)", "", "قوس", ""),
    ("قول «هلا", "", "ما انقفلت", ""),
    ("قول 'هلا", "", "ما انقفلت", ""),
    ("افتح", "", "اسم الملف", ""),
    ("احفظ", "", "وش أحفظ ووين", ""),
    ("أضف 5", "", "وش أضيف ووين", ""),
    ("كم العدد", "", "ليست أمراً", ""),
    ("اسأل", "", "السؤال", ""),
    ("كمل زائد 1", "", "قيمة قديمة", ""),
    ("قول هلا\nكمل زائد 1", "", "قيمة قديمة", ""),
    ("احسب 10\nإذا 1 أكبر من 2\n    اسأل كم العدد\nقول العدد", "", "غير", ""),
    ("اسأل وش الاسم\nكمل ضرب 2", "سعود\n", "رقم", ""),
    ("الاسم = \"3\"\nاحسب الاسم زائد 2", "", "رقم", ""),
    ("الاسم = \"3\"\nاحسب الاسم تربيع", "", "رقم", ""),
    ("اسأل كم العدد", "سعود\n", "رقم", ""),
    ("اسأل كم العدد", "5abc\n", "رقم", ""),
    ("اسأل كم العدد", "10 قسمة 0\n", "قسمة على صفر", ""),
    ("احسب 20\nكمل 7", "", "عملية", ""),
    ("كرر 2.5 مرات\n    قول هلا", "", "صحيح", ""),
    ("كرر -2 مرات\n    قول هلا", "", "سالب", ""),
    ("العدد = \"2junk\"\nكرر العدد مرات\n    قول هلا", "", "رقم", ""),
    ("إذا 1 أكبر من\n    قول هلا", "", "الشرط ناقص", ""),
    ("وإلا\n    قول هلا", "", "إذا", ""),
    ("احسب 8\nعرّف عداد بدون مدخلات\n    كمل زائد 1\n    أرجع الناتج\nقول عداد()", "", "قيمة قديمة", ""),
    ("احسب 10\nإذا 1 أكبر من 2\n    اسأل كم العدد\nوإلا\n    قول هلا\nكمل ضرب المجهول", "", "المجهول", ""),
    ("اسأل كم سعر القطعة\nاسأل كم سعر الكرتون\nاحسب السعر زائد 1", "5\n20\n", "ملتبس", ""),
    ("اطلب نصيحة", "", "الذكاء", ""),
    ("ارسم بطيخة في البحر", "", "ما أعرف أرسم", ""),
    ("ارسم", "", "الرسم", ""),
]


@pytest.mark.parametrize("code,answers,first,second", ERRORS)
def test_clear_errors(tmp_path, code, answers, first, second):
    result = run_program(tmp_path, code, answers)
    assert result.returncode != 0
    assert "⚠" in result.stderr
    assert first in result.stderr and second in result.stderr
    assert "AttributeError" not in result.stderr
    assert "SyntaxError" not in result.stderr


@pytest.mark.parametrize("name", ["الناتج", "ثم", "كم", "كمل", "قول", "احسب", "ارسم", "افتح", "أضف", "لكل", "وإلا", "اسأل", "ناتج", "احفظ"])
@pytest.mark.parametrize("template", ["{name} = 5", "اسأل كم {name}", "احفظ 5 في {name}", "السلة = [1]\nلكل {name} في السلة\n    قول هلا", "عرّف تجربة ياخذ {name} ويرجع 5"])
def test_reserved_names_in_all_bindings(tmp_path, name, template):
    r = run_program(tmp_path, template.format(name=name), "8\n")
    assert r.returncode != 0
    assert "محجوز" in r.stderr, r.stderr


@pytest.mark.parametrize("bad", ["احسب 10 قسمة 0", "احسب 5 ضرب", "كمل قسمة 0", "افتح مو_موجود.txt"])
def test_chain_failure_stops_following_side_effects(tmp_path, bad):
    r = run_program(tmp_path, f"احسب 8 ثم {bad} ثم احفظ هلا في ملف after.txt ثم قول وصلنا")
    assert r.returncode != 0
    assert "وصلنا" not in r.stdout
    assert not (tmp_path / "after.txt").exists()


@pytest.mark.parametrize("command", ["احفط 5 في ملف test.txt", "اسال كم العدد", "فول هلا", "احس 5 زائد 3"])
def test_typo_or_explicit_arabic_rejection(tmp_path, command):
    r = run_program(tmp_path, command, "8\n")
    assert r.returncode == 0 or "⚠" in r.stderr


def test_file_roundtrip(tmp_path):
    r = run_program(tmp_path, "احسب 5 زائد 3 ثم احفظ الناتج في ملف result.txt ثم افتح result.txt ثم قول المحتوى ثم كمل زائد 2 ثم قول الناتج")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "result.txt").read_text(encoding="utf-8") == "8"
    assert output(r)[-2:] == ["8", "10"]


def test_repl_keeps_last_successful_context_after_error(tmp_path):
    reqs = [{"code": "احسب 8"}, {"code": "اسأل كم العدد ثم احسب العدد قسمة 0", "answers": ["7"]}, {"code": "كمل زائد 1"}, {"code": "قول الناتج"}]
    p = subprocess.run([sys.executable, str(ENGINE), "repl"], input="".join(json.dumps(x, ensure_ascii=False)+"\n" for x in reqs),
                       text=True, encoding="utf-8", capture_output=True, timeout=10, cwd=tmp_path,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8", DAD_OUT_DIR=str(tmp_path)))
    records = [json.loads(x) for x in p.stdout.splitlines()]
    assert len(records) == 4, p.stderr
    assert records[0]["ok"] and not records[1]["ok"] and records[2]["ok"] and records[3]["ok"]
    assert records[3]["out"].strip() == "8"


def test_drawing_is_repeatable_and_offline(tmp_path):
    code = "ارسم سفينة حمراء في البحر واسمها سعود"
    for _ in range(2):
        r = run_program(tmp_path, code)
        assert r.returncode == 0, r.stderr
        svg = (tmp_path / "رسمة_1.svg").read_bytes()
        if _ == 0: first = svg
        else: assert svg == first


def test_invalid_cli_file_has_arabic_error(tmp_path):
    p = subprocess.run([sys.executable, str(ENGINE), "run", str(tmp_path/"missing.dad")], text=True, encoding="utf-8", capture_output=True, timeout=10)
    assert p.returncode != 0
    assert "Traceback" not in p.stderr
    assert "مو موجود" in p.stderr
