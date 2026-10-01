import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAD = ROOT / 'dad.py'


def run_program(tmp_path, source, answers=''):
    src = tmp_path / 'interactive.dad'
    src.write_text(source, encoding='utf-8')
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return subprocess.run([sys.executable, str(DAD), 'شغل', str(src)], input=answers,
                          text=True, capture_output=True, cwd=ROOT, env=env)


def test_calc_alone_uses_last_asked_value_for_subtract(tmp_path):
    r = run_program(tmp_path,
        'اسأل كم عدد البيض في السلة ثم احسب ثم قول الناتج',
        '10\nاطرح 4\n')
    assert r.returncode == 0, r.stderr
    assert '= 6' in r.stdout
    assert r.stdout.rstrip().endswith('6')


def test_relative_words_apply_to_active_value(tmp_path):
    cases = [('زائد 5', '15'), ('ناقص 4', '6'), ('ضرب 3', '30'), ('اقسم 2', '5')]
    for op, expected in cases:
        r = run_program(tmp_path, 'احسب 10 ثم احسب ثم قول الناتج', op + '\n')
        assert r.returncode == 0, (op, r.stderr)
        assert r.stdout.rstrip().endswith(expected), (op, r.stdout)


def test_full_expression_still_works_independently(tmp_path):
    r = run_program(tmp_path, 'احسب 10 ثم احسب ثم قول الناتج', '20 ناقص 4\n')
    assert r.returncode == 0, r.stderr
    assert r.stdout.rstrip().endswith('16')


def test_relative_operation_without_active_value_has_clear_error(tmp_path):
    r = run_program(tmp_path, 'احسب', 'اطرح 4\n')
    assert r.returncode != 0
    assert 'ما في قيمة سابقة' in r.stderr
