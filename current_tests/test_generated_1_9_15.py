"""Seeded behavioral programs with independent numeric expectations."""
import contextlib
import io
import math
import random
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dad
import vnext


def programs():
    r = random.Random(1915)
    cases = []
    for i in range(500):
        a, b, c, d = [r.randint(1, 25) for _ in range(4)]
        forms = [
            (f'{a} زائد {b} ضرب {c} ناقص {d}', a+b*c-d),
            (f'({a} زائد {b}) ضرب ({c} ناقص {d})', (a+b)*(c-d)),
            (f'-{a} زائد {b} قسمة {c} ضرب {d}', -a+b/c*d),
            (f'(({a} ناقص {b}) ضرب {c}) قسمة {d}', ((a-b)*c)/d),
            (f'{a} أس 2 ناقص ({b} زائد {c})', a**2-(b+c)),
        ]
        expr, value = forms[i % len(forms)]
        cases.append((f'احسب {expr}\nقول الناتج', [], value))
    for i in range(200):
        base, answer, delta = [r.randint(1, 30) for _ in range(3)]
        count = r.randint(0, 5)
        code = f'''احسب {base}
إذا 1 أصغر من 2
    اسأل كم العدد
وإلا
    اسأل كم السعر
العدد = 99
قول «مرحبا»
كرر {count} مرات
    إذا 1 أكبر من 0
        كمل زائد {delta}
قول الناتج'''
        if count == 0:
            # Asking activates its answer but does not overwrite the old result.
            expected = base
        else:
            expected = answer + delta*count
        cases.append((code, [str(answer)], expected))
    for i in range(200):
        answer, delta = r.randint(1, 30), r.randint(1, 15)
        prefix = ['احسب 9', 'اسأل كم العدد', 'قول «الطباعة لا تغير السياق»']
        count = r.randint(5, 35)
        code = ' ثم '.join(prefix + [f'كمل زائد {delta}'] * count + ['قول الناتج'])
        cases.append((code, [str(answer)], answer+delta*count))
    return cases


@pytest.mark.parametrize('code,answers,expected', programs(), ids=[f'program-{i:03}' for i in range(900)])
def test_reference_programs(code, answers, expected, monkeypatch):
    incoming = iter(answers)
    monkeypatch.setattr('builtins.input', lambda prompt='': next(incoming))
    env = {'__name__': '__main__', **vnext.RUNTIME}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(dad.to_python(code), '<generated-aldad>', 'exec'), env)
    assert math.isclose(env['الناتج'], expected, abs_tol=1e-6, rel_tol=1e-9)
    assert float(out.getvalue().splitlines()[-1]) == env['الناتج']


@pytest.mark.parametrize('i', range(100))
def test_incomplete_generated_programs(i):
    op = ['زائد', 'ناقص', 'ضرب', 'قسمة', 'أس'][i % 5]
    code = f'احسب ({i+1} زائد 2) {op} ثم قول «يجب ألا تصل هنا»'
    with pytest.raises(vnext.DadError, match='العملية ناقصة'):
        dad.to_python(code)
