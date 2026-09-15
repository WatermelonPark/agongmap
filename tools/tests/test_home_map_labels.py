# -*- coding: utf-8 -*-
"""홈 지도 라벨이 판정 단위를 따르는지 고정한다.

2026-09-15 고객 점검: 광주·전남이 2026-09-10 에 '전남광주' 한 판정 단위로 합쳐졌는데 홈 지도는
도형마다 원래 이름을 그려 '광주'·'전남' 두 라벨이 따로 떠 있었다. 색과 링크는 통합 지역을
가리키면서 라벨만 옛 모델이었다.

지도 루프는 브라우저 JS 라서, index.html 에서 그 루프를 꺼내 node 로 실제로 돌린다. 문자열만
검사하면 라벨 식을 다르게 써서 같은 결함을 되살려도 통과한다.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _loop_src():
    s = HS.home_source()
    a = s.find('var SMALL=')
    b = s.find("h+='</svg></div>';", a)
    assert a >= 0 and b > a, '홈 지도 루프를 찾지 못했다 — 구조가 바뀌었으면 이 시험도 고칠 것'
    return s[a:b]


def _geo():
    s = io.open(os.path.join(ROOT, 'sido-geo.js'), encoding='utf-8').read()
    return json.loads(re.search(r'SIDO_GEO\s*=\s*(\{.*\})\s*;?\s*$', s, re.S).group(1))


def _labels():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    zones = {z: {'grade': 0, 'tot': 0, 'ratio': 0} for z in SZ.ORDER}
    js = ('var ADV={sido:{L:""}},Z=%s,SIDO_GEO=%s,TB_GRADE={},h="";'
          'function tbSigned(v){return String(v)}function mapFill(){return "#ccc"}\n%s\n'
          'var out=[],re=/<text[^>]*>([^<]*)<\\/text>/g,m;while((m=re.exec(h)))out.push(m[1]);'
          'var links=[],r2=/href="\\/zone\\/([^\\/]*)\\//g;while((m=r2.exec(h)))links.push(decodeURIComponent(m[1]));'
          'process.stdout.write(JSON.stringify({labels:out,links:links}));'
          % (json.dumps(zones, ensure_ascii=False), json.dumps(_geo(), ensure_ascii=False), _loop_src()))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def test_every_label_is_a_zone_and_appears_once():
    got = _labels()
    labels = got['labels']
    bad = [x for x in labels if x not in SZ.ORDER]
    assert not bad, '판정 단위에 없는 지도 라벨: %s' % bad
    dup = sorted({x for x in labels if labels.count(x) > 1})
    assert not dup, '한 판정 단위에 라벨이 여러 개다: %s' % dup


def test_every_sido_on_the_map_is_labelled():
    got = _labels()
    want = sorted(set(got['links']))
    assert sorted(got['labels']) == want, '라벨과 링크 대상이 다르다: %s' % sorted(set(got['labels']) ^ set(want))
    for z in SZ.ORDER:
        if z not in SZ.AGG:
            assert z in got['labels'], '%s 라벨이 지도에 없다' % z


def test_merged_name_is_not_hardcoded_in_the_loop():
    code = re.sub(r'/\*.*?\*/', '', _loop_src(), flags=re.S)  # 주석의 설명문은 제외
    assert '전남광주' not in code, '지도 루프에 통합 이름을 박았다 — 판정 단위에서 파생할 것'
