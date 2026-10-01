from test_stability_1_9_15 import run_program, output
import pytest


def test_full_question_names_override_ambiguous_short_names(tmp_path):
    r = run_program(tmp_path, '''اسأل كم عدد البيض في السلة
اسأل كم عدد البيض في الثلاجة
احسب عدد البيض في السلة زائد عدد البيض في الثلاجة
قول الناتج''', '6\n4\n')
    assert r.returncode == 0, r.stderr
    assert output(r) == ['كم عدد البيض في السلة؟ 6', 'كم عدد البيض في الثلاجة؟ 4', '10']


@pytest.mark.parametrize('source', ['قول كم عدد بيض احسب', 'قول(كم عدد بيض احسب)'])
def test_ambiguous_commands_fail_before_question_or_execution(tmp_path, source):
    r = run_program(tmp_path, source + ' ثم قول «وصلنا»', '7\n')
    assert r.returncode != 0
    assert 'أمرين' in r.stderr and 'ثم' in r.stderr
    assert not r.stdout and 'وصلنا' not in r.stdout
