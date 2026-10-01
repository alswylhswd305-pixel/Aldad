import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / 'dad.py'
sys.path.insert(0, str(ROOT))
import ui  # noqa: E402


def run_program(tmp_path, source, answers=''):
    src = tmp_path / 'case.dad'
    src.write_text(source, encoding='utf-8')
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run([sys.executable, str(DAD), 'شغل', str(src)], input=answers,
                          text=True, capture_output=True, cwd=ROOT, env=env)


def out_lines(r):
    return [x.strip() for x in r.stdout.splitlines() if x.strip()]


@pytest.mark.parametrize('answer,expected', [
    ('-4', '18'), ('- 4', '18'), ('−4', '18'),
    ('+5', '27'), ('+ 5', '27'),
    ('*2', '44'), ('* 2', '44'), ('×2', '44'),
    ('/2', '11'), ('/ 2', '11'), ('÷2', '11'),
])
def test_interactive_symbol_operation_uses_active_value(tmp_path, answer, expected):
    r = run_program(tmp_path, 'اسأل كم العدد ثم احسب ثم قول الناتج', f'22\n{answer}\n')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == expected


@pytest.mark.parametrize('answer', ['-4', '+5', '*2', '/2', '×2', '÷2'])
def test_interactive_symbol_operation_requires_active_value(tmp_path, answer):
    r = run_program(tmp_path, 'احسب', answer + '\n')
    assert r.returncode != 0
    assert 'قيمة سابقة' in r.stderr


@pytest.mark.parametrize('phrase,value,expected', [
    ('أكبر من أو يساوي', 10, 'نعم'),
    ('أكبر من أو يساوي', 9, 'لا'),
    ('أكثر من أو يساوي', 11, 'نعم'),
    ('أصغر من أو يساوي', 10, 'نعم'),
    ('أصغر من أو يساوي', 11, 'لا'),
    ('أقل من أو يساوي', 9, 'نعم'),
])
def test_long_arabic_comparators(tmp_path, phrase, value, expected):
    src = f'''احفظ {value} في العدد
إذا العدد {phrase} 10
    قول نعم
وإلا
    قول لا'''
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == expected


def test_long_comparator_inside_logical_expression(tmp_path):
    src = '''احفظ 10 في العدد
إذا العدد أكبر من أو يساوي 10 و العدد أصغر من 20
    قول نعم
وإلا
    قول لا'''
    r = run_program(tmp_path, src)
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == 'نعم'


def test_spaced_digit_names_work_in_core(tmp_path):
    r = run_program(tmp_path, 'احفظ 5 في سعر بيع 1\nاحسب سعر بيع 1 زائد 2\nقول الناتج')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == '7'


def test_spaced_digit_names_work_in_ui():
    src = '''برنامج اسمه تجربة
أضف حقل اسمه سعر بيع 1
أضف حقل اسمه كمية 1
أضف زر اسمه احسب
أضف نص اسمه المبلغ
عند ضغط احسب
    احسب سعر بيع 1 ضرب كمية 1
    ضع الناتج في المبلغ'''
    prog = ui.compile_ui(src)
    js = ''.join(prog.events['احسب'])
    assert 'سعر بيع 1' in js
    assert 'كمية 1' in js


def test_long_comparator_works_in_ui():
    src = '''برنامج اسمه تجربة
أضف حقل اسمه العدد
أضف زر اسمه افحص
أضف نص اسمه الحالة
عند ضغط افحص
    إذا(العدد أكبر من أو يساوي 10)
        ضع «نعم» في الحالة
    وإلا
        ضع «لا» في الحالة'''
    prog = ui.compile_ui(src)
    js = ''.join(prog.events['افحص'])
    assert '>=' in js


def test_contextual_question_has_natural_short_alias(tmp_path):
    r = run_program(tmp_path, 'اسأل كم سعر القطعة في المتجر\nقول سعر القطعة', '7\n')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == '7'


def test_contextual_alias_becomes_ambiguous_when_two_values_exist(tmp_path):
    src = '''اسأل كم عدد البيض في السلة
اسأل كم عدد البيض في الثلاجة
قول عدد البيض'''
    r = run_program(tmp_path, src, '6\n4\n')
    assert r.returncode != 0
    assert 'ملتبس' in r.stderr
    assert 'عدد البيض في السلة' in r.stderr
    assert 'عدد البيض في الثلاجة' in r.stderr


def test_full_contextual_names_remain_distinct(tmp_path):
    src = '''اسأل كم عدد البيض في السلة
اسأل كم عدد البيض في الثلاجة
احسب عدد البيض في السلة زائد عدد البيض في الثلاجة
قول الناتج'''
    r = run_program(tmp_path, src, '6\n4\n')
    assert r.returncode == 0, r.stderr
    assert out_lines(r)[-1] == '10'


def test_huge_power_rejected_before_output(tmp_path):
    r = run_program(tmp_path, 'احسب 10 أس 10000\nقول الناتج')
    assert r.returncode != 0
    assert 'كبيرة جدًا' in r.stderr
    assert 'قيمة غلط' not in r.stderr


def test_giant_literal_has_specific_error(tmp_path):
    huge = '9' * 5000
    r = run_program(tmp_path, f'احسب {huge}\nقول الناتج')
    assert r.returncode != 0
    assert 'الرقم كبير جدًا' in r.stderr

@pytest.mark.parametrize('expr', ['. زائد 2', '5 زائد . 2', '--4', '++4'])
def test_malformed_calculation_is_rejected(tmp_path, expr):
    r = run_program(tmp_path, f'احسب {expr}')
    assert r.returncode != 0
    assert '⚠' in r.stderr
