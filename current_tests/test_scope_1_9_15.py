from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_stability_1_9_15 import run_program,output


@pytest.mark.parametrize('code,answers,want',[
    ('اسأل كم سعر القطعة\nعرّف تجربة بدون مدخلات\n    اسأل كم سعر الكرتون\n    أرجع 0\nاحسب السعر زائد 1\nقول الناتج','5\n',['كم سعر القطعة؟ 5','6']),
    ('استورد نظام\nقول نظام.path.exists(".")','',['صح']),
    ('س = صح\nقول س\nس = خطأ\nقول س','',['صح','خطأ']),
    ('عرّف خارج ياخذ س\n    عرّف داخل بدون مدخلات\n        احسب س ضرب 2\n        أرجع الناتج\n    أرجع داخل()\nقول خارج(4)','',['8']),
    ('احسب 20\nعرّف حساب ياخذ س\n    احفظ 5 في قيمة محلية\n    احسب س زائد قيمة محلية\n    أرجع الناتج\nقول حساب(2)\nكمل زائد 1\nقول الناتج','',['7','21']),
])
def test_scoped_names_and_legacy_calls(tmp_path,code,answers,want):
    r=run_program(tmp_path,code,answers)
    assert r.returncode==0,r.stderr
    assert output(r)==want
