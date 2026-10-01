import json
from math import ceil
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_stability_1_9_15 import run_program,output
import ui

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'examples/expected.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('name',CASES)
def test_delivered_examples(tmp_path,name):
    case=CASES[name]
    r=run_program(tmp_path,(ROOT/'examples'/name).read_text(encoding='utf-8'),case['answers'])
    assert r.returncode==0,r.stderr
    assert [l for l in output(r) if not l.startswith('@@DAD_IMAGE@@')]==case['out']
    for path,value in case.get('files',{}).items():
        assert (tmp_path/path).read_text(encoding='utf-8')==value
    if case.get('svg'): ET.parse(tmp_path/case['svg'])


def test_delivered_invoice_ui():
    pr=ui.compile_ui((ROOT/'examples/interactive_invoice.dad').read_text(encoding='utf-8'))
    assert pr.title=='فاتورتي' and len(pr.widgets)==4
    html=ui.to_html(pr)
    assert 'fetch(' not in html and 'BIN(' in html


@pytest.mark.parametrize('name',['calculator.dad','grocery.dad','aldad_ide_pro.dad'])
def test_existing_ui_examples_still_compile(name):
    pr=ui.compile_ui((ROOT/name).read_text(encoding='utf-8'))
    assert pr.widgets and 'fetch(' not in ui.to_html(pr)


@pytest.mark.parametrize('name,answers,expected',[
    ('example.dad','سعود\n22\n','الضاد لغتي'),
    ('functions_example.dad','','10'),
    ('money_manager.dad','سعود\n1200\n','الباقي معك: 725 دينار'),
    # Independent geometry and prices: 37 tiles * 1.5 + 9 litres * 2.25.
    ('materials_calculator.dad','4\n3\n3\n',str(ceil(4*3/.36*1.1)*1.5 + ceil((4+3)*2*3*2/10)*2.25)),
])
def test_existing_console_examples_still_run(tmp_path,name,answers,expected):
    r=run_program(tmp_path,(ROOT/name).read_text(encoding='utf-8'),answers)
    assert r.returncode==0,r.stderr
    assert expected in r.stdout
