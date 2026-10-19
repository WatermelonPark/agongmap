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


def _pm_row(html):
    m = re.search(r'<tr class="zref" data-ref="pm">(.*?)</tr>', html, re.S)
    assert m, "'인허가 1년' 참고 행을 못 찾았다"
    return [re.sub(r'<[^>]+>', '', c) for c in re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.S)]


def test_permit_year_row_names_its_month_and_rounds_half_up():
    """표 아래 '인허가 1년' 참고 행이 미분양 행처럼 기준 달('2026년 8월 기준 · …', 날짜 두 단계의 읽는 꼴)을 적고, 퍼센트는 화면 정수
    정본 rnd(half_up)로 찍는다(전수리뷰 Z1 overflow — 창의 끝 달을 버리고 '%.0f' 로 짝수 쪽 반올림했다).
    기준 달은 판정(calc)이 실은 permit_prd(= SZ.permit_ref_month, '3년 너머' 창과 같은 달)이고, 그 칸이 없는 옛 판정(다음 배치 전)은
    달 없이 굽는다.
    변이(실제로 확인): 행에서 기준 달 조각을 빼면 첫 단정이, 퍼센트를 '%.0f%%' 로 되돌리면 0.925(=92.5%) 단정이 빨개진다.
    픽스처: 저장소 STATS 로 새로 돌린 판정(지금 코드). 서울 행에 인허가 1년 값(실데이터 값, 비면 합성 12,345)과 pmr 0.925(100배가 이진수로
    정확히 92.5)를 실은 사본 — 실데이터에 그 지역 값이 비는 회차에도 행이 선다 —, 그 사본에서 permit_prd 를 뺀 사본. 실데이터 행은 값이
    있으면 퍼센트를, 없으면 행이 서지 않음을 본다.
    """
    html, calc, st = _page()
    assert calc['permit_prd'] == SZ.permit_ref_month(st), calc.get('permit_prd')
    adv, _ = P.load()
    pq = P.price_quarters(adv)
    prd = calc['permit_prd'] or '2026.08'
    zs = [dict(z, pm12=z.get('pm12') or 12345, pmr=0.925) if z['z'] == '서울' else z for z in calc['zones']]
    c2 = dict(calc, permit_prd=prd, zones=zs)
    cells = _pm_row(P.build_page('서울', c2, st, pq, zs))
    assert cells[3] == '%s 기준 · 착공 전 단계의 선행 물량' % SZ.month_text(prd), cells
    assert cells[2] == '93%', cells
    c3 = {k: v for k, v in c2.items() if k != 'permit_prd'}
    assert _pm_row(P.build_page('서울', c3, st, pq, zs))[3] == '착공 전 단계의 선행 물량'
    row = [z for z in calc['zones'] if z['z'] == '서울'][0]
    if row.get('pm12') is not None and row.get('pmr') is not None:
        assert _pm_row(html)[2] == '%d%%' % SZ.half_up(row['pmr'] * 100)
    else:
        assert 'data-ref="pm"' not in html, '인허가 1년 값이 없는데 행이 섰다'


def test_table_start_is_one_constant():
    """시도 리포트 분기 표·홈 통합표(split_data)·통계 탭 입주물량(supply_rows)이 같은 첫 분기·첫 달에서 시작한다 — 정본
    SZ.TABLE_FROM_YEAR(전수리뷰 X1 overflow — '2017'이 make_sido_pages·sido_zones·split_data 세 곳에 따로 박혀 있었고 일치 시험이 없었다).
    홈 통합표는 split_data.TABLE_FROM 을 읽지 않고 자기 거울 TB_FROM(home-app.js 'var TB_FROM=<해>*12')을 쓰므로 그 해도 같은지 본다(검토 보강 —
    거울 대조가 어디에도 없었다).
    변이(실제로 확인): supply_rows 의 시작을 qidx(2018, 1) 로, split_data.TABLE_FROM 을 '2018.01' 로, 홈 TB_FROM 을 2018*12 로 박으면 각각 빨개진다.
    픽스처: 저장소 STATS(실데이터) — 표의 첫 행만 본다(데이터가 앞으로 가도 첫 행은 그대로다) — 와 홈 스크립트(home_src 입구)."""
    import split_data as S
    import home_src as HS
    y = SZ.TABLE_FROM_YEAR
    assert P.TABLE_FROM == SZ.qidx(y, 1) and S.TABLE_FROM == '%d.01' % y, (P.TABLE_FROM, S.TABLE_FROM)
    tb = re.findall(r'var TB_FROM\s*=\s*(\d+)\s*\*\s*12\b', HS.home_source())
    assert tb == [str(y)], '홈 TB_FROM 거울이 정본 TABLE_FROM_YEAR(%d)와 다르다: %s' % (y, tb)
    _, calc, st = _page()
    assert SZ.supply_rows(st)['rows'][0]['p'] == '%dQ1' % y
    assert P.series(st, '서울', calc)[0][0] == SZ.qidx(y, 1)


def test_report_head_basis_line_names_its_source():
    """리포트 머리 기준 줄은 '시점 기준 · 출처' 한 양식이다(2026-10-06 대표 결정 — 날짜 두 단계·기준 줄 양식). 재현한 실제 상태: 머리 줄이
    '2026년 2분기 기준 · 분기마다 갱신'이라 출처가 없었다(전수리뷰 Z1 overflow). 갱신 주기는 <main> 첫 문단이 말한다.
    변이(실제로 확인): 기준 줄을 옛 '… 기준 · 분기마다 갱신'으로 되돌리면 빨개진다.
    픽스처: 저장소 STATS 로 새로 돌린 판정으로 서울 리포트를 메모리에서 굽는다."""
    html, calc, _ = _page()
    m = re.search(r'<span class="zbasis">([^<]*)</span>', html)
    assert m and m.group(1) == '%s 기준 · %s' % (calc['Ltxt'], P.BASIS_SRC), m and m.group(1)
    row = [z for z in calc['zones'] if z['z'] == '서울'][0]
    assert '국토교통부' in P.BASIS_SRC and '분기마다 갱신' in P.summary_text(P.summary_parts('서울', row, calc, '부족'))
