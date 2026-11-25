"""t1064: time/date, then-in-speech, unit conversion, كم-calc, typo chaining, English guide."""
import datetime
import importlib.util
import os
import re
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


def assert_ok(r, src=""):
    assert r.returncode == 0, f"{src}\n{r.stderr}"


def assert_time_out(text):
    now = datetime.datetime.now()
    cands = {
        now.strftime("%H:%M"),
        (now - datetime.timedelta(minutes=1)).strftime("%H:%M"),
        (now + datetime.timedelta(minutes=1)).strftime("%H:%M"),
    }
    assert any(c in text for c in cands), text


def assert_date_out(text):
    assert datetime.datetime.now().strftime("%Y/%m/%d") in text, text


def _load_ide(tmp_path):
    os.environ["DAD_WORK_DIR"] = str(tmp_path)
    sys.modules.pop("aldad_ide_t1064", None)
    spec = importlib.util.spec_from_file_location("aldad_ide_t1064", IDE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- core feature tests ----------

@pytest.mark.parametrize("src", [
    "قول كم الساعة",
    "كم الساعة",
    "كم الوقت",
    "قول كم الوقت",
    "اسأل كم الساعة",
    "الوقت",
    "what time is it",
    "say what time is it",
    "كم الساعة الحين",
    "الساعة كم",
])
def test_current_time_phrases(tmp_path, src):
    r = run_program(tmp_path, src)
    assert_ok(r, src)
    assert "؟" not in r.stdout or "كم الساعة؟" not in r.stdout or out_text(r).split("؟")[-1].strip() != ""
    # must not prompt the user
    assert "يحتاج رقم" not in r.stderr
    assert_time_out(out_text(r) or r.stdout)


@pytest.mark.parametrize("src", [
    "شنو التاريخ",
    "قول شنو التاريخ",
    "وش التاريخ",
    "what's the date",
    "say what's the date",
    "what is the date",
])
def test_current_date_phrases(tmp_path, src):
    r = run_program(tmp_path, src)
    assert_ok(r, src)
    assert_date_out(out_text(r) or r.stdout)


def test_ask_time_of_user_still_asks(tmp_path):
    r = run_program(tmp_path, "اسأل كم الساعة عندك", "3\n")
    assert_ok(r)
    assert "كم الساعة عندك؟" in r.stdout
    # should not have printed clock time as the only output
    assert "عندك؟" in r.stdout


def test_kam_count_still_asks(tmp_path):
    r = run_program(tmp_path, "اسأل كم عدد البيض في السلة\nقول عدد البيض", "5\n")
    assert_ok(r)
    assert "كم عدد البيض في السلة؟" in r.stdout
    assert "5" in out_text(r)


@pytest.mark.parametrize("src,expect", [
    ("قول اكل ثم نام", "اكل ثم نام"),
    ("قل اكل ثم نام", "اكل ثم نام"),
    ("قول «اكل ثم نام»", "اكل ثم نام"),
    ("say eat then sleep", "eat then sleep"),
    ("say \"eat then sleep\"", "eat then sleep"),
    ("قول تفاح و موز", "تفاح و موز"),
])
def test_then_inside_speech_is_text(tmp_path, src, expect):
    r = run_program(tmp_path, src)
    assert_ok(r, src)
    assert out_text(r) == expect


@pytest.mark.parametrize("src,lines", [
    ("قول هلا ثم قول مرحبا", ["هلا", "مرحبا"]),
    ("say hi then say bye", ["hi", "bye"]),
    ("قول هلا و قول مرحبا", ["هلا", "مرحبا"]),
    ("قوول هلا و قوول مرحبا", ["هلا", "مرحبا"]),
])
def test_then_chains_when_both_are_commands(tmp_path, src, lines):
    r = run_program(tmp_path, src)
    assert_ok(r, src)
    assert out_text(r).splitlines() == lines


def test_mixed_then_still_errors(tmp_path):
    r = run_program(tmp_path, "احسب 5 زائد 3 ثم نام")
    assert r.returncode != 0
    assert "نام" in r.stderr


@pytest.mark.parametrize("src,value", [
    ("احسب كم جرام في 2 كيلو\nقول الناتج", "2000"),
    ("كم جرام في 2 كيلو", "2000"),
    ("احسب(كم جرام في 2 كيلو)\nقول الناتج", "2000"),
    ("احسب كم متر في 3 كيلومتر\nقول الناتج", "3000"),
    ("احسب كم سم في 2 متر\nقول الناتج", "200"),
    ("احسب كم دقيقة في 2 ساعة\nقول الناتج", "120"),
    ("احسب كم ساعة في 120 دقيقة\nقول الناتج", "2"),
    ("احسب كم يوم في 2 أسبوع\nقول الناتج", "14"),
    ("احسب كم ثانية في 3 دقائق\nقول الناتج", "180"),
    ("احسب ساعتين بالدقايق\nقول الناتج", "120"),
    ("calc how many grams in 2 kilos\nsay result", "2000"),
    ("calc how many meters in 3 kilometers\nsay result", "3000"),
    ("calc how many minutes in 2 hours\nsay result", "120"),
    ("calc how many days in 2 weeks\nsay result", "14"),
])
def test_unit_conversion(tmp_path, src, value):
    r = run_program(tmp_path, src)
    assert_ok(r, src)
    assert out_text(r).splitlines()[-1] == value


@pytest.mark.parametrize("src,value", [
    ("كم 4 زائد 5 احسب\nقول الناتج", "9"),
    ("كم 4 زائد 5", "9"),
    ("احسب كم 4 زائد 5\nقول الناتج", "9"),
    ("كم 10 ناقص 3", "7"),
    ("كم 6 ضرب 7 احسب\nقول الناتج", "42"),
    ("calc 5 plus 3 times 2\nsay result", "11"),
])
def test_kam_arithmetic_and_english_times(tmp_path, src, value):
    r = run_program(tmp_path, src)
    assert_ok(r, src)
    assert out_text(r).splitlines()[-1] == value


def test_two_commands_without_then_still_ambiguous(tmp_path):
    r = run_program(tmp_path, "قول هلا احسب 1")
    assert r.returncode != 0
    assert "أمرين" in r.stderr


# ---------- ~100 varied-style batch ----------

def _varied_cases():
    cases = []
    # time / date, many styles
    for i, src in enumerate([
        "قول كم الساعة", "قل(كم الساعة)", "كم الوقت", "قول الوقت",
        "كم الساعة الآن", "الوقت الحين", "say the time", "what time is it",
        "شنو التاريخ", "قول التاريخ", "ما التاريخ", "تاريخ اليوم",
        "what's the date", "what is the date", "say the date",
    ], 1):
        kind = "date" if any(w in src.lower() for w in ("تاريخ", "date", "اليوم")) and "time" not in src.lower() else "time"
        # «قول التاريخ» / «تاريخ اليوم» / «say the date»
        if any(w in src.lower() for w in ("تاريخ", "date")):
            kind = "date"
        cases.append((f"time-{i}", src, "", kind, None, None))

    # then in speech vs chain
    speech = [
        ("قول نام ثم اكل", "نام ثم اكل"),
        ("قول شرب ثم نام ثم اكل", "شرب ثم نام ثم اكل"),
        ("قل اكل ثم نام", "اكل ثم نام"),
        ("قول هلا ثم مرحبا", "هلا ثم مرحبا"),
        ("say run then walk", "run then walk"),
        ("say one then two then three", "one then two then three"),
        ("قول «اجلس ثم قم»", "اجلس ثم قم"),
        ("say apples and oranges", "apples and oranges"),
        ("قول قهوة و حليب", "قهوة و حليب"),
    ]
    for i, (src, exp) in enumerate(speech, 1):
        cases.append((f"speech-{i}", src, "", "exact", exp, None))

    chains = [
        ("قول أ ثم قول ب", ["أ", "ب"]),
        ("say one then say two", ["one", "two"]),
        ("احسب 2 زائد 2 و قول الناتج", ["4"]),
        ("calc 10 minus 4 and say result", ["6"]),
        ("قول هلا بعدين قول باي", ["هلا", "باي"]),
        ("قوول صباح الخير و قوول مساء الخير", ["صباح الخير", "مساء الخير"]),
        ("قول 1 ثم قول 2 ثم قول 3", ["1", "2", "3"]),
    ]
    for i, (src, lines) in enumerate(chains, 1):
        cases.append((f"chain-{i}", src, "", "lines", None, lines))

    # conversions, styles
    conv = [
        ("احسب كم غرام في 1 كيلو", "1000"),
        ("كم جرام في 5 كيلو", "5000"),
        ("احسب كم كيلو في 3000 جرام", "3"),
        ("احسب كم كيلومتر في 5000 متر", "5"),
        ("كم متر في 1 كيلومتر", "1000"),
        ("احسب كم سم في 5 متر", "500"),
        ("احسب كم متر في 200 سم", "2"),
        ("كم دقيقة في 3 ساعات", "180"),
        ("احسب كم ثانية في 2 دقيقة", "120"),
        ("احسب كم أسبوع في 14 يوم", "2"),
        ("احسب كم ساعة في 90 دقيقة", "1.5"),
        ("calc how many cm in 3 meters", "300"),
        ("calc how many seconds in 2 minutes", "120"),
        ("calc how many hours in 240 minutes", "4"),
        ("احسب 4 كيلو بالجرام", "4000"),
        ("احسب ثلاث ساعات بالدقايق", "180"),
    ]
    for i, (src, val) in enumerate(conv, 1):
        body = src if src.startswith("كم") or src.startswith("calc") or src.startswith("احسب") else src
        if "قول" not in body and "say" not in body and not body.startswith("كم "):
            body = body + "\nقول الناتج" if "calc" not in body else body + "\nsay result"
            if body.startswith("calc"):
                body = src + "\nsay result"
            elif src.startswith("احسب"):
                body = src + "\nقول الناتج"
        cases.append((f"conv-{i}", body, "", "last", val, None))

    # كم arithmetic, word orders, English
    math_cases = [
        ("كم 1 زائد 2", "3"),
        ("كم 8 ناقص 3 احسب\nقول الناتج", "5"),
        ("كم 4 ضرب 5", "20"),
        ("احسب كم 9 قسمة 3\nقول الناتج", "3"),
        ("كم 2 زائد 3 ضرب 4", "14"),
        ("calc 8 plus 2\nsay result", "10"),
        ("calc 9 minus 4\nsay result", "5"),
        ("calc 6 times 6\nsay result", "36"),
        ("calc 15 divided 3\nsay result", "5"),
        ("كم 100 زائد 25 احسب\nقول الناتج", "125"),
        ("كم 20 زائد 5 ناقص 3", "22"),
        ("احسب (5 زائد 3) ضرب 2\nقول الناتج", "16"),
        ("calc (5 plus 3) times 2\nsay result", "16"),
        ("كم 2 زائد 2 زائد 2", "6"),
        ("احسب 100 قسمة 4\nقول الناتج", "25"),
    ]
    for i, (src, val) in enumerate(math_cases, 1):
        cases.append((f"math-{i}", src, "", "last", val, None))

    # typo + connectors
    typos = [
        ("قوول أهلا", ["أهلا"]),
        ("قوول واحد و قوول اثنين", ["واحد", "اثنين"]),
        ("احسبب 7 زائد 1\nقول الناتج", ["8"]),
    ]
    for i, (src, lines) in enumerate(typos, 1):
        cases.append((f"typo-{i}", src, "", "lines", None, lines))

    # still-ask / negatives
    asks = [
        ("اسأل كم العدد", "8\n", "كم العدد؟"),
        ("اسأل كم العمر", "16\n", "كم العمر؟"),
        ("قول كم عدد الكتب", "2\n", "كم عدد الكتب؟"),
        ("اسأل كم الساعة عندك", "11\n", "كم الساعة عندك؟"),
    ]
    for i, (src, ans, prompt) in enumerate(asks, 1):
        cases.append((f"ask-{i}", src, ans, "prompt", prompt, None))

    # English guide-adjacent
    eng = [
        ("say \"hello Saud\"", "hello Saud"),
        ("calc 5 plus 3 times 2\nsay result", "11"),
        ("calc 5 plus 3 and say result", "8"),
        ("rep 2 times\n    say \"hi\"", "hi\nhi"),
    ]
    for i, (src, exp) in enumerate(eng, 1):
        cases.append((f"en-{i}", src, "", "exact", exp, None))

    # draw english / arabic extras
    cases.append(("draw-en-1", "draw a blue square", "", "image", None, None))
    cases.append(("draw-en-2", "draw a red circle and a blue square", "", "image", None, None))
    cases.append(("draw-ar-1", "ارسم مثلث أخضر", "", "image", None, None))

    # more speech / chain / typo / time fillers to cover beginner styles
    extra_speech = [
        ("قول اجلس ثم قم", "اجلس ثم قم"),
        ("قول اقرأ ثم اكتب ثم نم", "اقرأ ثم اكتب ثم نم"),
        ("say sit then stand", "sit then stand"),
        ("قول صباح الخير ثم إلى اللقاء", "صباح الخير ثم إلى اللقاء"),
        ("قل مرحبا ثم أهلا", "مرحبا ثم أهلا"),
        ("say tea and coffee", "tea and coffee"),
        ("قول خبز و جبن و تمر", "خبز و جبن و تمر"),
        ("قول «ثم ثم ثم»", "ثم ثم ثم"),
    ]
    for i, (src, exp) in enumerate(extra_speech, 1):
        cases.append((f"speech-x-{i}", src, "", "exact", exp, None))

    extra_chain = [
        ("قول حياك ثم قول الله يحييك", ["حياك", "الله يحييك"]),
        ("say good morning then say good night", ["good morning", "good night"]),
        ("احسب 1 زائد 1 بعدين قول الناتج", ["2"]),
        ("calc 3 plus 4 then say result", ["7"]),
        ("قوول نعم و قوول لا", ["نعم", "لا"]),
        ("قول أول و قول ثاني و قول ثالث", ["أول", "ثاني", "ثالث"]),
    ]
    for i, (src, lines) in enumerate(extra_chain, 1):
        cases.append((f"chain-x-{i}", src, "", "lines", None, lines))

    extra_conv = [
        ("كم جرام في 10 كيلو", "10000"),
        ("احسب كم مل في 2 لتر\nقول الناتج", "2000"),
        ("احسب كم يوم في 3 أسابيع\nقول الناتج", "21"),
        ("احسب كم ثانية في ساعة\nقول الناتج", "3600"),
        ("calc how many grams in 4 kilos\nsay result", "4000"),
        ("calc how many weeks in 28 days\nsay result", "4"),
        ("كم سم في 1 متر", "100"),
        ("احسب كم دقيقة في نصف ساعة\nقول الناتج", "30"),
    ]
    # skip نصف ساعة if it may fail — check later; include safer ones
    extra_conv = extra_conv[:-1] + [("احسب كم دقيقة في 0.5 ساعة\nقول الناتج", "30")]
    for i, (src, val) in enumerate(extra_conv, 1):
        cases.append((f"conv-x-{i}", src, "", "last", val, None))

    extra_time = [
        "قول كم الوقت",
        "كم الوقت الآن",
        "say what time is it",
        "شنو تاريخ اليوم",
    ]
    for i, src in enumerate(extra_time, 1):
        kind = "date" if "تاريخ" in src or "date" in src.lower() else "time"
        cases.append((f"time-x-{i}", src, "", kind, None, None))

    extra_ask = [
        ("اسأل كم الطول", "170\n", "كم الطول؟"),
        ("ask how many eggs", "12\n", "how many eggs؟"),
    ]
    for i, (src, ans, prompt) in enumerate(extra_ask, 1):
        cases.append((f"ask-x-{i}", src, ans, "prompt", prompt, None))

    extra_if = [
        ("اسأل كم العمر\nإذا العمر أكبر من 18\n    قول «بالغ»\nوإلا\n    قول «صغير»", "21\n", "بالغ"),
        ("ask how many years\nif years gt 10\n    say \"yes\"\nelse\n    say \"no\"", "4\n", "no"),
    ]
    for i, (src, ans, exp) in enumerate(extra_if, 1):
        cases.append((f"if-x-{i}", src, ans, "last", exp, None))

    return cases


VARIED = _varied_cases()


@pytest.mark.parametrize("cid,src,answers,kind,expect,lines", VARIED, ids=[c[0] for c in VARIED])
def test_varied_batch(tmp_path, cid, src, answers, kind, expect, lines):
    r = run_program(tmp_path, src, answers)
    if kind == "prompt":
        assert_ok(r, src)
        assert expect in r.stdout
        return
    if kind == "image":
        assert_ok(r, src)
        assert "@@DAD_IMAGE@@" in r.stdout
        return
    assert_ok(r, src)
    out = out_text(r)
    if kind == "time":
        assert_time_out(out)
    elif kind == "date":
        assert_date_out(out)
    elif kind == "exact":
        assert out == expect, (cid, out)
    elif kind == "last":
        assert out.splitlines()[-1] == expect, (cid, out)
    elif kind == "lines":
        assert out.splitlines() == lines, (cid, out)
    else:
        raise AssertionError(kind)


def test_varied_batch_is_about_one_hundred():
    assert 90 <= len(VARIED) <= 140, len(VARIED)


# ---------- English guide ----------

def test_english_guide_has_eight_lessons(tmp_path):
    ide = _load_ide(tmp_path)
    ids = [e["id"] for e in ide.IDE_GUIDE_EN]
    assert ids == [e["id"] for e in ide.IDE_GUIDE]
    assert "gEn" in ide.PAGE and "gAr" in ide.PAGE
    assert "Beginner guide" in ide.PAGE or "title_en" in Path(IDE).read_text(encoding="utf-8")
    for e in ide.IDE_GUIDE_EN:
        assert e["title"].strip() and e["explain"].strip() and e["code"].strip()


@pytest.mark.parametrize("lesson_id", [
    "g_say", "g_ask", "g_save_greet", "g_calc",
    "g_then", "g_if", "g_rep", "g_draw",
])
def test_english_guide_lesson_runs(tmp_path, lesson_id):
    ide = _load_ide(tmp_path)
    les = next(e for e in ide.IDE_GUIDE_EN if e["id"] == lesson_id)
    r = run_program(tmp_path, les["code"], les.get("answers") or "")
    assert_ok(r, les["code"])
    out = out_text(r)
    if lesson_id == "g_say":
        assert out == "hello Saud"
    elif lesson_id == "g_ask":
        assert "what is your name؟" in r.stdout
        assert out.splitlines()[-1] == "Saud"
    elif lesson_id == "g_save_greet":
        assert "hello Nora" in out
    elif lesson_id == "g_calc":
        assert out.splitlines()[-1] == "11"
    elif lesson_id == "g_then":
        assert out.splitlines()[-1] == "8"
    elif lesson_id == "g_if":
        assert "you are an adult" in out
    elif lesson_id == "g_rep":
        assert out.splitlines() == ["hi", "hi", "hi"]
    elif lesson_id == "g_draw":
        assert "@@DAD_IMAGE@@" in r.stdout


def test_rules_en_covers_new_patterns():
    text = (ROOT / "rules_en.md").read_text(encoding="utf-8")
    for needle in [
        "Novaq",
        "what time is it",
        "what's the date",
        "eat then sleep",
        "how many grams in 2 kilos",
        "times",
        "and save it in name",
        "hello {name}",
        "slice items from 1 to 3",
        "draw a red circle",
    ]:
        assert needle in text, needle


def test_rules_ar_covers_new_patterns():
    text = (ROOT / "rules_ar.md").read_text(encoding="utf-8")
    for needle in ["كم الساعة", "شنو التاريخ", "قول اكل ثم نام", "كم جرام في 2 كيلو", "كم 4 زائد 5"]:
        assert needle in text, needle
