import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui


def execute_ui(source, values):
    html = ui.to_html(ui.compile_ui(source))
    assert 'fetch(' not in html and '/chat/completions' not in html
    script = re.search(r'<script>(.*?)</script>', html, re.S).group(1)
    runner = '''const vm=require('vm');
const payload=JSON.parse(require('fs').readFileSync(0,'utf8'));
const elements={say:{textContent:''}};
for(const [k,v] of Object.entries(payload.values)) elements[k]={value:v,tagName:'INPUT'};
const document={querySelector:q=>elements[q.match(/data-n="(.*?)"/)[1]]||null,
querySelectorAll:()=>[],getElementById:n=>elements[n]};
const window={addEventListener:()=>{}};
const ctx=vm.createContext({document,window,CSS:{escape:x=>x},console,setTimeout,clearTimeout});
vm.runInContext(payload.script,ctx);
(async()=>{await vm.runInContext('H["نفذ"]()',ctx);console.log(JSON.stringify({say:elements.say.textContent,result:vm.runInContext('R["الناتج"]',ctx)}));})();'''
    r = subprocess.run(['node', '-e', runner], input=json.dumps({'script':script,'values':values},ensure_ascii=False),
                       text=True, capture_output=True, timeout=10)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.parametrize('expr,want', [('(2 زائد 3) ضرب (4 ناقص 1)',15), ('((2 زائد 3) ضرب 4)',20), ('2 أس 3 أس 2',512)])
def test_ui_parentheses_and_precedence(expr, want):
    source = f'برنامج اسمه تجربة\nأضف زر اسمه «نفذ»\nعند ضغط «نفذ»\n    احسب {expr}\n    قول الناتج'
    r=execute_ui(source,{})
    assert r == {'say':str(want),'result':want}


def test_compound_field_names_and_continue():
    source='''برنامج اسمه فاتورة
أضف حقل اسمه «سعر القطعة»
أضف حقل اسمه «الكمية»
أضف زر اسمه «نفذ»
عند ضغط «نفذ»
    احسب سعر القطعة ضرب الكمية
    قول «حساب»
    كمل زائد 2
    قول الناتج'''
    assert execute_ui(source,{'سعر القطعة':'5','الكمية':'3'}) == {'say':'17','result':17}


@pytest.mark.parametrize('value', ['3oops', 'سعود', ''])
def test_ui_rejects_text_as_number(value):
    source='برنامج اسمه تجربة\nأضف حقل اسمه العدد\nأضف زر اسمه «نفذ»\nعند ضغط «نفذ»\n    احسب العدد ضرب 2\n    قول «وصلنا»'
    r=execute_ui(source,{'العدد':value})
    assert r['say'].startswith('⚠') and 'وصلنا' not in r['say']


def test_ui_zero_division_stops_chain():
    source='برنامج اسمه تجربة\nأضف زر اسمه «نفذ»\nعند ضغط «نفذ»\n    احسب 1 قسمة 0 ثم قول «وصلنا»'
    r=execute_ui(source,{})
    assert 'قسمة على صفر' in r['say'] and 'وصلنا' not in r['say']
