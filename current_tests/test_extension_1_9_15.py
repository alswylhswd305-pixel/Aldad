"""Run VS Code's transport with real Python children, without VS Code mocks."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def execute(tmp_path, code, answers):
    p=tmp_path/'extension.dad'
    p.write_text(code,encoding='utf-8')
    script='''const {runProcess}=require(process.argv[1]);
const p=JSON.parse(require('fs').readFileSync(0,'utf8')); const asked=[];
runProcess({candidates:[[p.python,[]]],args:[p.engine,'run',p.file],cwd:p.cwd,
env:{...process.env,PYTHONIOENCODING:'utf-8',DAD_INTERACTIVE:'1'},
onPrompt:async q=>{asked.push(q);return p.answers.shift();},timeoutMs:5000})
.then(r=>console.log(JSON.stringify({...r,asked})));'''
    payload={'python':sys.executable,'engine':str(ROOT/'dad.py'),'file':str(p),'cwd':str(tmp_path),'answers':answers}
    r=subprocess.run(['node','-e',script,str(ROOT/'vscode/extension/runner.js')],input=json.dumps(payload,ensure_ascii=False),
                     text=True,capture_output=True,timeout=10)
    assert r.returncode == 0,r.stderr
    return json.loads(r.stdout)


def test_extension_asks_only_executed_questions(tmp_path):
    r=execute(tmp_path,'''اسأل كم العدد
إذا العدد أكبر من 0
    كرر العدد مرات
        اسأل كم السعر
وإلا
    اسأل كم المجهول
كمل زائد 1
قول الناتج''',['3','4','8','12'])
    assert r['code']==0,r
    assert r['asked']==['كم العدد؟','كم السعر؟','كم السعر؟','كم السعر؟']
    assert r['out'].strip().endswith('13')


def test_extension_stops_questions_after_error(tmp_path):
    r=execute(tmp_path,'احسب 1 قسمة 0 ثم اسأل كم العدد',[])
    assert r['code']!=0 and r['asked']==[] and 'قسمة على صفر' in r['err']


def test_extension_cancel_stops_program(tmp_path):
    r=execute(tmp_path,'اسأل كم العدد ثم قول وصلنا',[])
    assert r['code']!=0 and 'أوقف' in r['err'] and 'وصلنا' not in r['out']


def test_marker_in_literal_text_is_not_a_question(tmp_path):
    r=execute(tmp_path,'قول \'@@DAD_ASK@@"هذا نص"\'\nقول «٣٫٥، سعود»',[])
    assert r['code']==0 and not r['asked']
    assert r['out'].splitlines()==['@@DAD_ASK@@"هذا نص"','٣٫٥، سعود']
