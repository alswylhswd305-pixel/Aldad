from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_stability_1_9_15 import run_program, output


@pytest.mark.parametrize('code,want', [
    ('\ufeffاحسب 2 زائد 3\nقول الناتج', ['5']),
    ('قول «٣٫٥، ثم ٤»', ['٣٫٥، ثم ٤']),
    ('احفظ [«٣،٤»، 2] في السلة\nقول السلة', ["['٣،٤', 2]"]),
    ('احفظ «في البيت» في الرسالة\nقول الرسالة', ['في البيت']),
    ('السلة = []\nأضف «اذهب إلى البيت» إلى السلة\nقول السلة', ["['اذهب إلى البيت']"]),
    ('السلة = [1، 2]\nإذا (1 أكبر من 0 و 2 أصغر من 3) أو 4 يساوي 5\n    قول هلا\nوإلا\n    قول وداع', ['هلا']),
    ('احفظ [1، 2، 3] في قائمة الطلب\nاحسب مجموع قائمة الطلب\nقول الناتج\nلكل عنصر في قائمة الطلب\n    قول عنصر', ['6','1','2','3']),
    ('احسب 1\nإذا 1 أكبر من 0\n\tكرر 2 مرات\n\t\tكمل زائد 1\nقول الناتج', ['3']),
])
def test_final_valid_edges(tmp_path, code, want):
    r = run_program(tmp_path,code)
    assert r.returncode == 0,r.stderr
    assert output(r)==want


@pytest.mark.parametrize('code', ['كم += 1', 'دالة تجربة(الناتج):\n    أرجع 2', 'س، ثم = [1، 2]', 'دالة الناتج():\n    أرجع 2'])
def test_reserved_legacy_bindings_are_also_rejected(tmp_path,code):
    r=run_program(tmp_path,code)
    assert r.returncode != 0 and 'محجوز' in r.stderr


def test_story_with_missing_final_value(tmp_path):
    r=run_program(tmp_path,'احسب عندي 10 وصرفت 2 وزادت')
    assert r.returncode != 0 and 'ناقصة' in r.stderr


def test_adjacent_commands_need_then(tmp_path):
    r=run_program(tmp_path,'قول(هلا) قول(وداع)')
    assert r.returncode != 0 and 'حط بينهم «ثم»' in r.stderr
