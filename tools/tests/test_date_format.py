"""날짜 표기 두 단계(2026-10-06 대표 결정, 백로그 36-1) — 파이썬 정본과 홈 거울이 같은 글자를 내는가.

읽는 자리(기준 줄·문장·배너)는 '2026년 8월'·'9/28'·'2026년 2분기', 좁은 자리(표 칸·축 눈금·툴팁)는 '26.8'·'26.9.28'·'26Q2'.
파이썬 정본은 sido_zones.month_text·month_short·day_text·day_short·quarter_text, 홈 거울은 home-app.js 의 _ymT·_ymS·_md·_dS·_qT 다.
생성 페이지(지역 리포트·/jeonse-ratio/·/monthly/·/cycle/ 캡션)는 정본을, 홈 시세 탭은 거울을 쓴다. 둘이 갈리면 같은 달이 화면마다
다른 글자로 찍힌다.

변이(각각 실제로 확인): _ymS 의 연도 두 자리 자르기를 빼면('2026.8') 빨강. _ymT 가 달의 앞 0을 남기면('2026년 08월') 빨강.
_dS 가 달·일을 숫자로 바꾸지 않으면('26.09.28') 빨강. 파이썬 month_short 가 '%d' 로 연도를 찍으면('6.8' — 2006년) 빨강.
픽스처: 데이터에 실제로 나오는 꼴 — 월 계열 라벨('2026.08'), 잠정 표기('2026.08 p)'), 하이픈 달('2026-08'), 주간 조사일(ISO),
한 자리 연도 끝(2006년 — 짧은 꼴이 '06.1'), 달이 아닌 값(그대로 돌려준다).
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import sido_zones as SZ  # noqa: E402

MONTHS = ['2026.08', '2026.08 p)', '2026-08', '2006.01', '2025.12', '2026.10', '연', '']
DAYS = ['2026-09-28', '2026-10-01', '2006-01-02', '2025-12-31']
QUARTERS = ['2026Q2', '2006Q4', '2026H1', '']
UNITS = ['호 (월별)', '호 (연내 누계)', '호', '세대 (월별)', '%', '지수(2026.06=100)', '호수', '']
PAIRS = (('_ymT', SZ.month_text, MONTHS), ('_ymS', SZ.month_short, MONTHS),
         ('_md', SZ.day_text, DAYS), ('_dS', SZ.day_short, DAYS), ('_qT', SZ.quarter_text, QUARTERS),
         ('unitT', SZ.unit_text, UNITS))


def test_python_canon_examples():
    assert SZ.month_text('2026.08 p)') == '2026년 8월'
    assert SZ.month_short('2006.01') == '06.1'
    assert SZ.day_text('2026-10-01') == '10/1'
    assert SZ.day_short('2026-09-28') == '26.9.28'
    assert SZ.quarter_short('2026Q2') == '26Q2'
    assert SZ.unit_text('호 (연내 누계)') == '세대 (연내 누계)' and SZ.unit_text('호수') == '호수'   # 공급 단위 '세대'(백로그 36-2)
    assert SZ.basis_month('전세가율 · 2026년 8월 기준') == SZ.basis_month('2026.08 기준') == '2026.08'


def test_home_mirror_matches_the_python_canon():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    src = HS.home_source()
    fns = []
    for name in ('_md', '_ymP', '_ymT', '_ymS', '_dS', '_qT', 'unitT'):
        m = re.search(r'^function %s\(.*$' % name, src, re.M)
        assert m, '홈 스크립트에서 %s 를 찾지 못했다' % name
        fns.append(m.group(0))
    calls = [(n, v) for n, _, vals in PAIRS for v in vals]
    js = '\n'.join(fns) + '\nprocess.stdout.write(JSON.stringify(%s.map(([n,v])=>eval(n)(v))));' % json.dumps(calls)
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    got = json.loads(p.stdout.decode('utf-8'))
    want = [fn(v) for _, fn, vals in PAIRS for v in vals]
    bad = [(c, g, w) for c, g, w in zip(calls, got, want) if g != w]
    assert not bad, '홈 거울이 파이썬 정본과 다르다: %s' % bad
