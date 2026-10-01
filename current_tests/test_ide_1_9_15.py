import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]


def exchange(p, request):
    p.stdin.write(json.dumps(request,ensure_ascii=False)+'\n');p.stdin.flush()
    line=p.stdout.readline()
    assert line, 'REPL closed before replying'
    return json.loads(line)


def test_live_repl_asks_for_each_iteration(tmp_path):
    p=subprocess.Popen([sys.executable,str(ROOT/'dad.py'),'repl'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       text=True,encoding='utf-8',cwd=tmp_path,env=dict(os.environ,DAD_OUT_DIR=str(tmp_path)))
    try:
        r=exchange(p,{'code':'اسأل كم العدد\nكرر العدد مرات\n    اسأل كم السعر\nكمل زائد 1\nقول الناتج','live':True})
        assert r == {'event':'question','prompt':'كم العدد؟'}
        for answer in ['3','4','8']:
            r=exchange(p,{'answer':answer})
            assert r == {'event':'question','prompt':'كم السعر؟'}
        r=exchange(p,{'answer':'12'})
        assert r['ok'] and r['out'].strip().endswith('13')
    finally:
        p.kill();p.communicate(timeout=5)


def test_live_repl_cancel_keeps_server_usable(tmp_path):
    p=subprocess.Popen([sys.executable,str(ROOT/'dad.py'),'repl'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       text=True,encoding='utf-8',cwd=tmp_path,env=dict(os.environ,DAD_OUT_DIR=str(tmp_path)))
    try:
        assert exchange(p,{'code':'اسأل كم العدد ثم قول وصلنا','live':True}).get('event')=='question'
        r=exchange(p,{'cancel':True})
        assert not r['ok'] and 'أوقف' in r['err'] and 'وصلنا' not in r['out']
        assert exchange(p,{'code':'احسب 8 ثم قول الناتج'})['ok']
    finally:
        p.kill();p.communicate(timeout=5)


@pytest.fixture
def ide(tmp_path,monkeypatch):
    monkeypatch.setenv('DAD_WORK_DIR',str(tmp_path))
    spec=importlib.util.spec_from_file_location('aldad_ide_under_test',ROOT/'aldad_ide.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    yield module
    if module.TERM.p:
        module.TERM.p.kill();module.TERM.p.communicate(timeout=5)


def test_ide_terminal_resumes_same_program(ide):
    r=ide.TERM.send({'code':'اسأل كم العدد ثم كمل زائد 2 ثم قول الناتج','live':True})
    assert r.get('event')=='question'
    r=ide.TERM.send({'answer':'7'})
    assert r['ok'] and r['out'].strip().endswith('9')


def test_windows_launcher_source_is_valid_and_runs(ide,tmp_path):
    source=ide._launcher_source('احسب 2 زائد 3\nقول الناتج')
    compile(source,'<windows-launcher-source>','exec')
    p=tmp_path/'launcher.py';p.write_text(source,encoding='utf-8')
    r=subprocess.run([sys.executable,str(p)],input='\n',text=True,capture_output=True,timeout=10,
                     env=dict(os.environ,PYTHONPATH=str(ROOT),DAD_SAFE='0'))
    assert r.returncode==0,r.stderr
    assert r.stdout.startswith('5\n')
