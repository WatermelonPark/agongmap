# -*- coding: utf-8 -*-
"""시도 리포트의 연수·출처·인허가 배율 문구가 모델 상수·데이터에서 나온다(전수 리뷰 #19·#21·#112).

재현하는 실제 상태:
  - #19: '숫자로 보면' 카드 제목 '지난 4년 쌓인 부족'·부제 '3년 뒤로 밀어 추정'·방법론 '착공 실적을 3년 뒤로 밀어'·"'3년 너머' 줄"이
    박혀 있었다. 검증자가 LEAD_Q 16·창 20 으로 바꾸자 한 페이지에 '지난 5년 쌓인 부족'(식)과 '지난 4년 쌓인 부족'(카드 제목)이
    함께 나왔다.
  - #21: 같은 페이지가 미분양 출처를 참고 행 안내에서는 '국토교통부', 방법론에서는 '한국부동산원'으로 말했다.
  - #112: '인허가는 같은 해 착공보다 15%쯤 많고'가 리터럴이었다(매 배치 데이터로 재는 착공÷인허가 0.867 → 1.153배).
무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 카드 제목을 '지난 4년 …' 리터럴로 되돌리면 정적·동작 단정이 모두, 방법론 미분양
출처를 '(한국부동산원)' 으로 되돌리면 출처 단정이, '15%%쯤' 을 되돌리면 정적 단정과 데이터 대조가 빨개진다.
픽스처: 저장소 data.js(실데이터) — 상수만 monkeypatch 로 바꾼 상태를 메모리에서 굽는다. 기대값은 상수·데이터에서 유도한다.
"""
import ast
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as P  # noqa: E402
import sido_zones as SZ  # noqa: E402

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'make_sido_pages.py')
BANNED = re.compile(r"지난 \d년|\d년 뒤|\d년 너머|착공보다 \d+%")


def _literals():
    tree = ast.parse(io.open(SRC, encoding='utf-8').read())
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef)) and n.body and isinstance(n.body[0], ast.Expr)}
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


def test_generator_has_no_hardcoded_years_or_permit_ratio():
    bad = [v for v in _literals() if BANNED.search(v)]
    assert not bad, '생성기 문자열에 연수·배율이 박혀 있다: %s' % [BANNED.search(v).group(0) for v in bad]


def _page(z='서울', stats=None):
    adv, st = P.load()
    st = stats if stats is not None else st
    calc = SZ.calc(st)
    return P.build_page(z, calc, st, P.price_quarters(adv), calc['zones']), calc, st


def test_page_years_follow_window_and_lead(monkeypatch):
    monkeypatch.setattr(SZ, 'LEAD_Q', 16)
    monkeypatch.setattr(SZ, 'BACKLOG_WINDOW', 20)
    html, calc, _ = _page()
    assert calc['H'] == 16
    text = re.sub(r'<[^>]+>', ' ', html)
    past = set(re.findall(r'지난 (\d+)년', text))
    after = set(re.findall(r'(\d+)년 뒤', text))
    beyond = set(re.findall(r"'?(\d+)년 너머", text))
    assert past == {'5'}, '지난 창 연수가 갈렸다: %s' % past
    assert after == {'4'}, '리드 연수가 갈렸다: %s' % after
    assert beyond == {'4'}, "'… 너머' 줄 연수가 갈렸다: %s" % beyond


def test_unsold_source_is_one_agency():
    html, _, _ = _page()
    assert P.UN_SOURCE in P.REFNOTE['un']
    m = re.search(r'<b>미분양</b>은 지금 안 팔리고 남은 집입니다\(([^)]+)\)', html)
    assert m and m.group(1) == P.UN_SOURCE, m and m.group(1)
    other = {'국토교통부', '한국부동산원'} - {P.UN_SOURCE}
    assert not any('(%s' % o in P.REFNOTE['un'] for o in other)


def test_permit_ratio_is_measured():
    html, _, st = _page()
    n = SZ.permit_over_start_pct(st)
    c = SZ.permit_start_conv(st, '전국')
    assert n is not None and abs(n - (1 / c - 1) * 100) <= 2.5, (n, c)
    assert '같은 해 착공보다 %d%%쯤 많고' % n in html
    # 인허가를 잴 수 없으면 그 구절만 빠진다(생성기는 죽지 않는다)
    no_permit = {k: v for k, v in st.items() if k != '인허가'}
    html2, _, _ = _page(stats=no_permit)
    assert '착공보다' not in html2 and '해마다 크게 흔들리기 때문입니다' in html2
