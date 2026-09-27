# -*- coding: utf-8 -*-
"""시도 리포트의 검색 요약 숫자(D3)와 시군구 주간 표·12개월 한 줄(D4) — 홈 마케팅 검수 요청서 D3·D4(2026-09-27).

재현하는 실제 상태(09-27):
  - D3: 네이버 스니펫은 <main> 첫 구역에서 나오는데, 시도 리포트의 첫 구역은 '숫자로 보면'이라는 칸 제목과 '누적 순부족'
    같은 칸 이름(<b>)뿐이라 색인된 14장 중 12장이 '숫자로 보면 ; 누적 순부족 ; …'처럼 숫자 없이 보였다. 세대수는 설명
    메타에만 있었다.
  - D4: 19장이 표를 뺀 본문을 크게 공유했다(요청서 실측 5-gram Jaccard 0.69~0.88. 이 시험의 잣대로는 <main> 에서 표를 뺀
    본문 글자의 80~82% 가 다른 장에도 똑같이 있는 문장이었다 — 09-27 생성분). 매주 바뀌는 그 지역만의 본문이 없었다.

원칙: 숫자는 한 곳에서 낸다. 설명 메타와 첫 문단은 make_sido_pages.summary_parts 한 목록, 시군구 순서·방향·연속은
weekly_moves(sgg_ranks·direction·streak — /weekly/ 표·홈 격자 표지와 같은 함수), 12개월 기준월은 /jeonse-ratio/ 의
jeonse_ref_index 와 SZ.month_back. 이 시험은 생성기 출력을 **따로 계산한 값**과 대조한다(같은 함수를 import 해 자기 자신과
비교하지 않는다 — 12주 누적·조사일 창·시도 접두는 여기서 다시 구현한다).

실데이터는 두 구현의 일치로만 본다(달·주·값을 박지 않는다 — 데이터가 앞으로 가도 초록. 한 주·한 분기 전진은
test_gate_survives_next_period 가 이 파일까지 돌려 본다).
"""
import copy
import datetime
import html as H
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_indicator_pages as I  # noqa: E402
import make_sido_pages as M  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_moves as WM  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _page(z):
    return io.open(os.path.join(ROOT, 'zone', z, 'index.html'), encoding='utf-8').read()


def _text(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def _zones():
    adv, _ = M.load()
    return adv, [z['z'] for z in adv['sido']['zones']]


# ── D3: <main> 첫 문단 = 설명 메타 ────────────────────────────────────────────────────────────

def test_first_block_of_main_says_the_description_numbers():
    """19장(집계 3장 포함) 모두 <main> 의 첫 요소가 숫자 문단이고, 그 글이 설명 메타와 같다(세대수·호수가 같다).
    '숫자로 보면' 칸 제목(<b>) 안에도 그 칸의 숫자가 있다 — 누적 순부족 칸의 <b> 는 설명 메타의 첫 세대수를 담는다.

    변이(각각 실제로 확인): build_page 에서 summary_html 을 </header> 앞으로 옮기면(문단을 헤더로 되돌리면) 첫 요소가
    '숫자로 보면' 구역이 되어 빨개진다. 설명 메타만 옛 문장으로 따로 만들어도(세대수 조각을 빼면) 빨개진다. zcell 의
    값 <span> 을 </b> 뒤로 되돌리면 칸 제목 단정이 빨개진다.
    픽스처: 배치가 방금 구운 zone/<지역>/index.html 19장(허브·통합 안내 페이지는 뺀다).
    """
    _, names = _zones()
    assert len(names) == len(SZ.ORDER)
    for z in names:
        s = _page(z)
        desc = H.unescape(re.search(r'<meta name="description" content="([^"]*)"', s).group(1))
        m = re.search(r'<main id="main">\s*<(\w+)\b[^>]*>(.*?)</\1>', s, re.S)
        assert m, z
        first = _text(m.group(2))
        assert first == desc, '%s: <main> 첫 요소가 설명 메타와 다르다\n  첫 요소: %s\n  메타   : %s' % (z, first[:120], desc[:120])
        nums = lambda t: re.findall(r'[\d,]+(?=세대|호)', t)
        assert nums(first) and nums(first) == nums(desc), z
        head = s[s.index('<header'):s.index('</header>')]
        assert first not in _text(head), '%s: 숫자 문단이 헤더에도 있다' % z
        cells = re.findall(r'<div class="zcell"><b>(.*?)</b><i>', s, re.S)
        assert len(cells) >= 4, z
        assert all(re.search(r'\d', _text(c)) for c in cells), '%s: 숫자 없는 칸 제목이 있다 %s' % (z, cells)
        assert nums(desc)[0] in _text(cells[0]), '%s: 누적 순부족 칸 제목에 세대수가 없다' % z


def test_description_and_paragraph_share_one_fragment_list():
    """설명 메타(summary_text)와 첫 문단(summary_html)이 같은 조각에서 나온다 — 조각을 하나 바꾸면 둘이 같이 바뀐다.

    변이: summary_html 이 조각 목록 대신 자기 문장을 새로 만들면(예: 세대수 조각을 빼면) 빨개진다(확인).
    픽스처: 합성 행(부족 1,234세대·균형 둘 다) — 실데이터와 무관한 갈래까지 본다.
    """
    calc = {'H': 12, 'L': '2030Q1', 'Ltxt': '2030년 1분기'}
    for row, lab in (({'ctxt': '1,234세대 부족 · 3년 필요량의 40%만큼', 'fut': 5000.4, 'ref': 700, 'dtot': 1234}, '부족'),
                     ({'fut': 10.6, 'ref': 3, 'dtot': -50, 'inow': 1}, '공급 여유')):
        parts = M.summary_parts('가나', row, calc, lab)
        assert _text(M.summary_html(parts)) == M.summary_text(parts)
        assert '%s세대' % M.num(row['fut']) in M.summary_text(parts)


# ── D4: 시군구 → 시도 ────────────────────────────────────────────────────────────────────────

def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _js_block(src, head, end):
    a = src.find(head)
    assert a >= 0, 'home-app.js 에서 %s 를 찾지 못했다' % head
    return src[a:src.index(end, a) + len(end)]


def test_sgg_sido_matches_home_sidoOf():
    """시도 리포트 표가 시군구를 두는 시도(weekly_moves.sgg_sido)가 홈 통계 탭 '시도 → 시군구' 선택(home-app.js sidoOf)과 같다.
    저장소 data.js 의 시군구 코드 전부 + 접두 경계(a0·a7·a8·a9·모르는 접두)로 node 대조한다.

    변이: SGG_PREFIX 의 'b3' 을 '전남'으로 바꾸거나, sgg_sido 가 a9 이외의 a 접두를 None 으로 돌려주면 빨개진다(확인).
    픽스처: 저장소 data.js ADV.weekly.sgg.codes(212곳 안팎 — 개수는 박지 않는다) + 합성 코드 여섯.
    """
    W, _ = MW.load()
    codes = list(W['sgg']['codes']) + ['a0', 'a7', 'a8', 'a9', 'a901', 'a6', 'z9', 'c9']
    src = HS.home_source()
    js = '\n'.join([_js_block(src, 'const SIDO_PREFIX=', '};'), _js_block(src, 'function sidoOf(', '\n}'),
                    'const cs=%s;' % json.dumps(codes),
                    'process.stdout.write(JSON.stringify(cs.map(c=>sidoOf(c))));'])
    site = _node(js)
    ours = [WM.sgg_sido(c) for c in codes]
    assert ours == site, [(c, a, b) for c, a, b in zip(codes, ours, site) if a != b][:10]


# ── D4: 표 숫자 = 따로 계산한 값 ─────────────────────────────────────────────────────────────

def _d(p):
    return datetime.date(*(int(x) for x in p.split('-')))


def _cum12(rows, i, met):
    """12주 누적을 여기서 다시 계산한다 — 조사일로 창을 고르고(최신 − 84일 < p ≤ 최신) 지수처럼 이어 곱한다."""
    last = _d(rows[-1]['p'])
    base = last - datetime.timedelta(days=7 * WM.CUM_WEEKS)
    if not any(_d(r['p']) <= base for r in rows):
        return None
    acc = 1.0
    for r in rows:
        if base < _d(r['p']) <= last:
            v = (r.get(met) or [None] * (i + 1))[i]
            if v is None:
                return None
            acc *= 1 + v / 100.0
    return (acc - 1) * 100


def _zone_of(code):
    s = WM.sgg_sido(code)      # 홈 sidoOf 와 같은지는 위 시험이 본다
    return '전남광주' if s in ('광주', '전남') else s


def _expected(W, Q, z):
    """/weekly/ 시군구 전체 표 순서(rank_moves) 가운데 z 에 드는 곳 — 순서는 /weekly/ 표의 부분열이어야 한다."""
    S = W['sgg']
    order = [c for c, _, _, _ in WM.rank_moves(S, Q)]
    idx = {c: k for k, c in enumerate(S['codes'])}
    if z == '전국':
        pick = order
    elif z in SZ.AGG:
        pick = [c for c in order if SZ.REGION.get(_zone_of(c)) == z]
    else:
        pick = [c for c in order if _zone_of(c) == z]
    out = []
    for c in pick:
        i = idx[c]
        r = [M.short_name(z, Q[c])]
        for met in ('ma', 'je'):
            vals = [(row.get(met) or [None] * (i + 1))[i] for row in S['rows']]
            s = WM.streak(vals)
            r += [MW.pv2(vals[-1]), MW.pv2(_cum12(S['rows'], i, met)), WM.streak_text(s, abs(s) == len(vals) if s else 0)]
        out.append(r)
    return out


def _tables(s):
    sec = re.search(r'<section class="zwk" id="weekly-sgg">(.*?)</section>', s, re.S)
    if not sec:
        return None, []
    tabs = []
    for t in re.findall(r'<tbody>(.*?)</tbody>', sec.group(1), re.S):
        tabs.append([[_text(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
                     for tr in re.findall(r'<tr>(.*?)</tr>', t, re.S)])
    return sec.group(1), tabs


def test_zone_tables_match_weekly_moves_and_the_weekly_page_order():
    """시도 리포트 19장의 시군구 주간 표 = 따로 계산한 값. 시도는 그 시도 시군구 전부(/weekly/ 표 순서의 부분열), 집계 3장은
    많이 오른 AGG_TOP 곳 + 많이 내린 AGG_TOP 곳(5+5). 매매·전세 주간 = MW.pv2, 연속 = weekly_moves.streak(표지와 같은 함수),
    12주 = 조사일 창으로 다시 이어 곱한 값.

    변이(각각 실제로 확인): zone_table 이 원값 대신 계열 순서(codes)로 줄을 세우면 순서 단정, cum_window 가 rows[-12:] 같은 행 번호
    창을 쓰면 12주 단정(실데이터에 발표를 거른 주가 있으면 — 아래 합성 시험이 늘 본다), streak 대신 원값 부호로 연속을 세면
    연속 단정, AGG_TOP 을 3으로 줄이면 5+5 단정이 빨개진다.
    픽스처: 배치가 구운 zone/<지역>/index.html 19장과 저장소 data.js ADV.weekly.sgg(156주 — 길이는 박지 않는다).
    """
    adv, names = _zones()
    W, Q = MW.load()
    for z in names:
        sec, tabs = _tables(_page(z))
        want = _expected(W, Q, z)
        assert sec is not None and want, '%s: 시군구 주간 표가 없다' % z
        if z in SZ.AGG:
            # 요청서 D4: 집계 3장은 상위·하위 5곳만(생성기 상수를 읽지 않는다 — 상수를 바꾸면 빨개져야 한다)
            assert len(tabs) == 2 and [len(t) for t in tabs] == [5, 5], (z, [len(t) for t in tabs])
            assert tabs[0] == want[:5], (z, tabs[0][:2], want[:2])
            assert tabs[1] == want[::-1][:5], (z, tabs[1][:2], want[-2:])
        else:
            assert len(tabs) == 1 and tabs[0] == want, (z, [a for a, b in zip(tabs[0], want) if a != b][:3] if tabs else None)
    # 세종은 원천이 시 전체 한 줄만 낸다 — 표는 한 줄, 제목에 '시군구'가 없다
    s = _page('세종')
    assert '<h2>세종 주간 아파트 시세</h2>' in s and len(_tables(s)[1][0]) == 1
    # 전남광주는 광주 구와 전남 시군을 한 표에 모은다
    got = {r[0] for r in _tables(_page('전남광주'))[1][0]}
    assert any(n.startswith('광주 ') for n in got) and any(not n.startswith('광주 ') for n in got), got


def test_lead_counts_come_from_the_table_rows():
    """표 위 요약의 오른 곳·내린 곳·보합·연속 N주 이상 곳 수 = 표 행에서 센 값(방향은 표시값 부호).

    변이: _wk_lead 가 방향을 원값 부호로 세면(0.00 을 상승·하락으로) 또는 STREAK_MIN 대신 2를 쓰면 빨개진다(확인 — 실데이터에
    표시 0.00 칸이 있는 주와 2주 연속인 곳이 있어야 드러나므로 합성 표로도 본다).
    픽스처: 배치가 구운 시도 16장(집계 3장은 표가 5+5 라 행으로 셀 수 없어 뺀다) + 합성 네 주.
    """
    _, names = _zones()
    for z in [n for n in names if n not in SZ.AGG and n not in M.NO_INNER_UNITS]:
        sec, tabs = _tables(_page(z))
        rows = tabs[0]
        sign = lambda t: 1 if t.startswith('+') else (-1 if t.startswith('-') else 0)
        up, dn = sum(sign(r[1]) > 0 for r in rows), sum(sign(r[1]) < 0 for r in rows)
        lead = _text(re.search(r'<p class="zwk-lead">(.*?)</p>', sec, re.S).group(1))
        assert '오른 곳은 %d곳, 내린 곳은 %d곳, 보합은 %d곳' % (up, dn, len(rows) - up - dn) in lead, (z, lead)
        k = lambda r, d: r[3] != '–' and r[3][0] == d and int(re.match(r'.(\d+)', r[3]).group(1)) >= WM.STREAK_MIN
        assert '연속 오른 곳은 %d곳, 연속 내린 곳은 %d곳' % (sum(k(r, '▲') for r in rows), sum(k(r, '▼') for r in rows)) in lead, z
    # 합성: 이번 주 0.004(표시 0.00 → 보합), 2주 연속 상승, 3주 연속 상승
    S = {'codes': ['b101', 'b102', 'b103'], 'rows': [
        {'p': '2031-01-06', 'ma': [0.1, -0.1, 0.1], 'je': [0.1, 0.1, 0.1]},
        {'p': '2031-01-13', 'ma': [0.1, 0.1, 0.1], 'je': [0.1, 0.1, 0.1]},
        {'p': '2031-01-20', 'ma': [0.004, 0.2, 0.3], 'je': [0.1, 0.1, 0.1]}]}
    Q = {'b101': '부산 가구', 'b102': '부산 나구', 'b103': '부산 다구'}
    sec = M.weekly_section('부산', {'sgg': S}, Q)
    assert '오른 곳은 2곳, 내린 곳은 0곳, 보합은 1곳' in sec and '연속 오른 곳은 1곳' in sec, _text(sec)


# ── D4: 12주 창·빈 자료·날짜 전진 ─────────────────────────────────────────────────────────────

def _weeks(start, n, skip=()):
    d = _d(start)
    out = []
    for k in range(n):
        p = (d + datetime.timedelta(days=7 * k)).isoformat()
        if p not in skip:
            out.append(p)
    return out


def test_cum_window_is_by_survey_date_not_row_count():
    """12주 누적 창은 조사일로 고른다 — 발표를 한 주 거른 이력에서 행 12개(rows[-12:])는 13주다.

    변이: cum_window 를 list(range(len(rows) - 12, len(rows))) 로 바꾸면 빨개진다(확인). 이력이 창보다 짧으면 None.
    픽스처: 2031년(실데이터와 겹치지 않는 먼 미래 — 날짜가 앞으로 가도 같은 답) 20주 가운데 한 주를 거른 이력, 값은 주마다 +1%.
    """
    ps = _weeks('2031-03-03', 20, skip={'2031-05-12'})
    rows = [{'p': p, 'ma': [1.0], 'je': [None]} for p in ps]
    win = WM.cum_window(rows)
    assert len(win) == WM.CUM_WEEKS - 1 and rows[win[0]]['p'] > (_d(ps[-1]) - datetime.timedelta(days=84)).isoformat()
    assert abs(WM.cum_change(rows, win, 0, 'ma') - (1.01 ** (WM.CUM_WEEKS - 1) - 1) * 100) < 1e-9
    assert WM.cum_change(rows, win, 0, 'je') is None                       # 창 안 결측 → None(0 으로 세지 않는다)
    assert WM.cum_window(rows[-(WM.CUM_WEEKS - 1):]) is None                # 기준 주가 없다(이력이 창보다 짧다)
    assert WM.cum_window(rows[-WM.CUM_WEEKS:]) == list(range(1, WM.CUM_WEEKS))   # 거른 주 덕에 12행째가 기준 주다
    assert WM.cum_window([]) is None and WM.cum_window([{'p': None}]) is None


@pytest.mark.parametrize('S', [
    None, {}, {'codes': [], 'rows': []},
    {'codes': ['a7010101'], 'rows': [{'p': '2031-01-06', 'ma': [0.1], 'je': [0.1]}]},          # 한 주뿐
    {'codes': ['a7010101'], 'rows': [{'p': '2031-01-06'}, {'p': 'x'}]},                          # 값·날짜가 깨졌다
    {'codes': ['a7010101', 'a7010102'], 'rows': [{'p': '2031-01-06', 'ma': [0.1, 0.1], 'je': [0.1, 0.1]},
                                                 {'p': '2031-01-13', 'ma': ['0.1', 0.2], 'je': [0.1, 0.1]}]},   # 값이 글자
])
def test_empty_or_single_week_drops_the_table_without_dying(S):
    """시군구 계열이 없거나 한 주뿐이거나 깨져 있으면 표만 빠지고 생성기는 죽지 않는다(배치 중단 금지 — 2026-09-26 감사 15번 유형).
    build_page 전체도 그 상태로 굽힌다(다른 칸은 그대로).

    변이(각각 실제로 확인): weekly_section 의 try/except 를 지우면 '값이 글자' 계열에서, zone_table 의 '행이 둘 미만이면 []' 가드를
    지우면 한 주 계열에서(표가 구워진다) 빨개진다.
    픽스처: 합성 계열 여섯 모양 + 저장소 data.js 의 판정·STATS(표 밖의 칸은 실데이터).
    """
    Q = {'a7010101': '서울 종로구'}
    assert M.weekly_section('서울', {'sgg': S} if S is not None else None, Q) == ''
    adv, stats = M.load()
    calc = adv['sido']
    w = dict(adv['weekly'], sgg=S) if S is not None else None
    page = M.build_page('서울', calc, stats, M.price_quarters(adv), calc['zones'], w, names=Q)
    assert 'id="weekly-sgg"' not in page and '<section class="zsum">' in page and '<h2>다른 지역</h2>' in page


def test_table_survives_dates_moving_forward():
    """조사일이 먼 미래로 가도(2031년) 표·12주·연속이 그대로 나온다 — 날짜를 박지 않았다.
    변이: cum_window 가 오늘(kst)을 기준으로 창을 잡으면 12주 칸이 비어 빨개진다(확인).
    픽스처: 2031년 14주, 시군구 두 곳(서울 두 구), 매주 +0.1·−0.1.
    """
    ps = _weeks('2031-01-06', 14)
    S = {'codes': ['a7010101', 'a7010102'],
         'rows': [{'p': p, 'ma': [0.1, -0.1], 'je': [0.1, -0.1]} for p in ps]}
    Q = {'a7010101': '서울 가구', 'a7010102': '서울 나구'}
    sec, tabs = _tables(M.weekly_section('서울', {'sgg': S}, Q))
    up = ['+0.10', MW.pv2((1.001 ** WM.CUM_WEEKS - 1) * 100), '▲14 이상']      # 14주 전부 상승 = 보관 이력 첫 주까지
    dn = ['-0.10', MW.pv2((0.999 ** WM.CUM_WEEKS - 1) * 100), '▼14 이상']
    assert tabs == [[['가구'] + up + up, ['나구'] + dn + dn]], tabs


# ── D4: 12개월 한 줄 ─────────────────────────────────────────────────────────────────────────

def _months(a, b, skip=()):
    y, m = (int(x) for x in a.split('.'))
    out = []
    while '%d.%02d' % (y, m) <= b:
        lab = '%d.%02d' % (y, m)
        if lab not in skip:
            out.append(lab)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_year_line_uses_the_card_months_and_labels_not_row_offsets():
    """'최근 12개월' 한 줄: 미분양은 '숫자로 보면' 카드와 같은 달(SZ.unsold_latest), 전세가율은 /jeonse-ratio/ 와 같은 달
    (make_indicator_pages.jeonse_ref_index — 최신 달에 필요 지역이 비면 앞 달로 보류), 12개월 전 칸은 라벨(SZ.month_back)로.
    같은 페이지 위 카드(next_links)도 같은 전세가율 달을 말한다.

    변이(각각 실제로 확인): year_line 이 12개월 전을 인덱스 차(i-12)로 잡으면(한 달 빠진 계열에서 13달 전) 빨개지고, 전세가율
    기준을 dates[-1] 로 되돌리면(보류 달) 빨개진다. next_links 만 dates[-1] 로 되돌려도 카드 단정이 빨개진다.
    픽스처: 2030.01~2031.06 합성 계열 — 미분양은 2030.09 가 빠졌고, 전세가율은 최신 2031.06 에 한 지역(제주)이 비었다.
    """
    ud = _months('2030.01', '2031.06', skip={'2030.09'})
    jd = _months('2030.01', '2031.06')
    regs = list(dict.fromkeys(list(SZ.ORDER) + list(I.JEONSE_NEED)))
    un = {'dates': ud, 'series': {r: [1000 + 10 * k for k in range(len(ud))] for r in regs}}
    un['series']['서울'][ud.index('2030.12')] = 5000          # 창 안의 최고 달
    jr = {'dates': jd, 'series': {r: [60.0 + 0.1 * k for k in range(len(jd))] for r in regs}}
    jr['series']['제주'][-1] = None                          # 최신 달 보류 → 2031.05 기준
    stats = {'미분양': un, '전세가율': jr}
    line = _text(M.year_line('서울', stats))
    v = lambda d, lab: d['series']['서울'][d['dates'].index(lab)]
    assert '미분양 %s호(2030.06) → %s호(2031.06)' % (M.num(v(un, '2030.06')), M.num(v(un, '2031.06'))) in line, line
    assert '가장 많던 달 5,000호(2030.12)' in line, line
    assert '전세가율 %.1f%%(2030.05) → %.1f%%(2031.05)' % (v(jr, '2030.05'), v(jr, '2031.05')) in line, line
    assert I.jeonse_ref_index(jr, I.JEONSE_NEED) == jd.index('2031.05')
    card = M.next_links('서울', None, stats)
    assert '2031.05 기준' in card and '2031.06' not in re.search(r'<b>전세가율</b><i>(.*?)</i>', card).group(1), card
    # 양 끝 값이 없으면 그 항목만 빠지고, 둘 다 없으면 줄이 없다
    assert M.year_line('서울', {'미분양': un}).count('전세가율') == 0
    assert M.year_line('서울', {}) == '' and M.year_line('없는곳', stats) == ''


def test_every_report_has_the_year_line_from_saved_data():
    """배치가 구운 19장 모두 '최근 12개월' 줄이 있고, 그 줄의 기준월이 같은 페이지 '숫자로 보면' 미분양 카드의 기준월과 같다.
    변이: year_line 이 미분양을 dates[-1](다른 지역이 먼저 채운 달)로 읽게 바꾸면, 지역 최신 달이 늦은 날 빨개진다.
    픽스처: 배치가 구운 zone/<지역>/index.html 19장.
    """
    _, names = _zones()
    for z in names:
        s = _page(z)
        m = re.search(r'<p class="zyear">(.*?)</p>', s, re.S)
        assert m, '%s: 12개월 줄이 없다' % z
        card = re.search(r'([\d.]+) 기준 · 분기 적정물량', s)
        if card and '미분양' in m.group(1):
            assert '호(%s)' % card.group(1) in m.group(1), (z, card.group(1), _text(m.group(1)))


# ── D4: 표를 뺀 본문의 공통 문장 비율 상한 ─────────────────────────────────────────────────────

SHARED_CAP = 0.75


def _sentences(s):
    """<main> 에서 표·스크립트·스타일을 뺀 본문을 문장으로 나눈다(블록 태그에서 끊고, '.'+공백에서 끊는다)."""
    m = re.search(r'<main[^>]*>(.*)</main>', s, re.S).group(1)
    m = re.sub(r'<(script|style|table)\b.*?</\1>', ' ', m, flags=re.S)
    m = re.sub(r'<(p|h1|h2|h3|div|section|li|a|i|b|span|br)\b[^>]*>', '\n', m)
    t = H.unescape(re.sub(r'<[^>]+>', ' ', m))
    out = []
    for line in t.split('\n'):
        for x in re.split(r'(?<=[.!?])\s+', line):
            x = re.sub(r'\s+', ' ', x).strip()
            if len(x) >= 2:
                out.append(x)
    return out


def shared_ratio(pages):
    """{지역: html} → {지역: 그 장의 본문 글자 가운데 다른 장에도 똑같이 있는 문장의 글자 비율}."""
    S = {z: _sentences(s) for z, s in pages.items()}
    cnt = {}
    for ss in S.values():
        for x in set(ss):
            cnt[x] = cnt.get(x, 0) + 1
    return {z: sum(len(x) for x in ss if cnt[x] >= 2) / float(sum(len(x) for x in ss)) for z, ss in S.items()}


def test_report_body_outside_tables_is_mostly_its_own():
    """19장의 <main> 에서 표를 뺀 본문 가운데 **다른 장에도 똑같이 있는 문장**의 글자 비율이 SHARED_CAP 이하다.

    값(09-27 생성분, 이 잣대): D4 전 0.80~0.82 → D4 뒤 0.63~0.70. 상한은 구조로 정했다 — 공통 문장은 방법론 블록(이번에 건드리지
    않는다)·칸 이름·안내 문구처럼 틀에서 오는 글이라 데이터가 바뀌어도 거의 그대로이고, 지역마다 다른 글(첫 숫자 문단·주간 요약·
    12개월 줄)은 지역 이름과 숫자가 들어 있어 다른 장과 문장 단위로 겹치지 않는다. 그래서 주·분기가 바뀌어도 비율은 틀과 고유 글의
    길이 비로 정해지고, 틀을 늘리거나 고유 글을 빼는 변경만 이 선을 넘는다.
    변이(각각 실제로 확인): build_page 에서 weekly_section 과 year_line 을 빼면(D4 이전 모양) 0.77~0.80 으로 빨개지고, 주간 요약
    문단(_wk_lead)만 비워도 빨개진다.
    픽스처: 배치가 구운 zone/<지역>/index.html 19장(허브·통합 안내 페이지는 뺀다).
    """
    _, names = _zones()
    r = shared_ratio({z: _page(z) for z in names})
    assert len(r) == len(SZ.ORDER)
    over = {z: round(v, 3) for z, v in r.items() if v > SHARED_CAP}
    assert not over, '표를 뺀 본문의 공통 문장 비율이 %.2f 를 넘는다: %s' % (SHARED_CAP, over)


def test_shared_ratio_measure_sees_boilerplate():
    """잣대 자기 확인 — 같은 틀에 지역 이름만 바꾼 두 장은 공통 비율이 높고, 고유 문단을 더하면 낮아진다.
    변이: shared_ratio 가 cnt>=2 대신 cnt>=len(pages)+1 을 쓰면(아무것도 공통으로 안 세면) 빨개진다(확인).
    픽스처: 합성 두 장.
    """
    tpl = '<main><p>같은 틀 문장입니다. 두 번째 틀 문장입니다.</p><p>%s</p><table><tr><td>%s</td></tr></table></main>'
    a = {'가': tpl % ('가 지역.', '표 가'), '나': tpl % ('나 지역.', '표 나')}
    base = shared_ratio(a)
    assert min(base.values()) > 0.8
    b = {k: v.replace('</main>', '<p>%s만의 긴 고유 문단이 여기에 있고 숫자 1,234 도 있습니다.</p></main>' % k) for k, v in a.items()}
    assert max(shared_ratio(b).values()) < min(base.values())
