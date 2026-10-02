import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / "dad.py"


def run_program(tmp_path, source, answers=""):
    src = tmp_path / "case.dad"
    src.write_text(source, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(DAD), "شغل", str(src)],
        input=answers,
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=env,
    )


def out_lines(r):
    return [x.strip() for x in r.stdout.splitlines() if x.strip()]


def test_multiword_function_name_and_return_line(tmp_path):
    src = """عرّف حساب درجة الخطر ياخذ الصحة و الأعداء
    احفظ (100 - الصحة) * 0.6 في عامل الضعف
    احفظ عامل الضعف + (الأعداء * 12) في الخطر الإجمالي
    أرجع الخطر الإجمالي

احفظ حساب درجة الخطر(42, 3) في النتيجة
قول النتيجة"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == "70.8"


def test_boolean_literals_are_real_values(tmp_path):
    src = """احفظ صحيح في الدرع
إذا الدرع يساوي صحيح
    قول «مفعل»
وإلا
    قول «متوقف»
قول الدرع"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert "مفعل" in out_lines(r)
    assert out_lines(r)[-1] == "صح"


def test_function_scope_shadowing_does_not_leak(tmp_path):
    src = """احفظ 50 في النقاط

عرّف تعديل ياخذ النقاط
    احفظ النقاط + 10 في النقاط
    قول النقاط
    أرجع النقاط

تعديل(100)
قول النقاط"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    lines = out_lines(r)
    assert "110" in lines
    assert lines[-1] == "50"


def test_return_outside_function_is_rejected(tmp_path):
    r = run_program(tmp_path, "أرجع 5")
    assert r.returncode != 0
    assert "داخل الدالة فقط" in r.stderr


def test_tactical_utility_example_runs(tmp_path):
    src = """احفظ 42 في صحة الكائن
احفظ 3 في عدد الأعداء المجاورين
احفظ 15 في مستوى الطاقة المتبقية
احفظ صحيح في درع الحماية جاهز

عرّف حساب درجة الخطر ياخذ الصحة و الأعداء
    احفظ (100 - الصحة) * 0.6 في عامل الضعف
    احفظ عامل الضعف + (الأعداء * 12) في الخطر الإجمالي
    أرجع الخطر الإجمالي

عرّف اتخاذ القرار التكتيكي ياخذ الصحة و الأعداء و الطاقة و الدرع
    احفظ حساب درجة الخطر(الصحة, الأعداء) في نسبة الخطر
    قول «--- تقييم حالة الميدان ---»
    قول «درجة الخطر المحسوبة:»
    قول نسبة الخطر

    إذا نسبة الخطر أكبر من 65
        إذا الدرع يساوي صحيح
            قول «قرار الذكاء الاصطناعي: تفعيل درع الحماية التكتيكي فوراً»
        وإلا
            قول «قرار الذكاء الاصطناعي: الانسحاب والتراجع للتحصين»
    وإلا إذا نسبة الخطر أكبر من 30
        إذا الطاقة أكبر من 10
            قول «قرار الذكاء الاصطناعي: شن هجوم مضاد خاطف»
        وإلا
            قول «قرار الذكاء الاصطناعي: التموضع الدفاعي واستعادة الطاقة»
    وإلا
        قول «قرار الذكاء الاصطناعي: الهجوم الشامل وإغلاق المساحات»

اتخاذ القرار التكتيكي(صحة الكائن, عدد الأعداء المجاورين, مستوى الطاقة المتبقية, درع الحماية جاهز)"""
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    lines = out_lines(r)
    assert "70.8" in lines
    assert lines[-1] == "قرار الذكاء الاصطناعي: تفعيل درع الحماية التكتيكي فوراً"
