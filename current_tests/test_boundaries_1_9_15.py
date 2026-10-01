"""Additional discoveries: literals, diagnostics, offline paths and value types."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_stability_1_9_15 import run_program, output
import dad
import ui
from aldad_syntax import DadError


@pytest.mark.parametrize('code,want', [
    ('قول «٣، ثم ٤»', ['٣، ثم ٤']),
    ('قول "٣، ثم ٤"', ['٣، ثم ٤']),
    ("قول '٣، ثم ٤'", ['٣، ثم ٤']),
    ('قول (اكتب (نعم) هنا)', ['اكتب (نعم) هنا']),
    ('قول (أ (ب (ج)) د)', ['أ (ب (ج)) د']),
    ('قول «احسب 5 ضرب 2»', ['احسب 5 ضرب 2']),
    ('قول 22', ['22']),
    ('احفظ -3 في العدد\nكمل زائد 1', []),
])
def test_literal_and_command_boundaries(tmp_path, code, want):
    r = run_program(tmp_path, code)
    # Saving a variable is explicit assignment; it does not create active context.
    if code.startswith('احفظ -3'):
        assert r.returncode != 0 and 'قيمة قديمة' in r.stderr
    else:
        assert r.returncode == 0, r.stderr
        assert output(r) == want


@pytest.mark.parametrize('command', ['اطلب نصيحة', 'ارسم بطيخة', 'ارسم بطيخة في البحر'])
def test_rejected_program_cannot_contact_a_model(command, monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Language execution attempted a network call')
    import urllib.request
    monkeypatch.setattr(urllib.request, 'urlopen', blocked)
    with pytest.raises(DadError):
        dad.to_python(command)


@pytest.mark.parametrize('body', ['شخصية الذكاء «مساعد»', 'أضف محادثة اسمها المساعد', 'عند ضغط «نفذ»\n    اطلب نصيحة'])
def test_ui_has_no_model_execution(body):
    with pytest.raises(DadError, match='الذكاء'):
        ui.compile_ui('برنامج اسمه تجربة\nأضف زر اسمه «نفذ»\n'+body)


def test_generated_line_maps_back_to_source(tmp_path):
    r = run_program(tmp_path, 'قول هلا ثم كرر 3 مرات\nاحسب 1 قسمة 0')
    assert r.returncode != 0
    assert 'السطر 2:' in r.stderr
    assert '← احسب 1 قسمة 0' in r.stderr


@pytest.mark.parametrize('code,words', [
    ('احسب 5 ضرب 2 زائد المجهول', ['المجهول']),
    ('الاسم = "3"\nقول الاسم ضرب 2', ['رقم']),
    ('احسب 2 ثم كمل ضرب قسمة 4', ['عمليتين']),
    ('قول هلا ثم ثم قول وداع', ['ثم']),
    ('قول هلا ثم', ['ثم']),
    ('اسأل كم العدد ثم قول وصلنا', ['رقم']),
])
def test_additional_errors(tmp_path, code, words):
    r = run_program(tmp_path, code, '3oops\n')
    assert r.returncode != 0
    assert all(w in r.stderr for w in words)
    assert 'وصلنا' not in r.stdout
