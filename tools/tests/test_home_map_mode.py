# -*- coding: utf-8 -*-
"""홈 공급 지도의 모드 '공급 현황 / 주간 시세 / 월간 시세'(홈 마케팅 검수 C3·IA-1 안 B, 2026-09-27 → 2026-10-04 월간 추가).

재현하는 실제 상태: 09-26 까지 홈 지도는 분기 공급 판정 하나만 칠했고, 매주 바뀌는 값은 두 화면 아래 주간 격자에만
있었다(IA-1). 한 지도에 주간 시세를 함께 싣되, 같은 빨강·파랑이 모드마다 다른 뜻(공급 부족·여유 ↔ 매매 상승·하락)이
되므로 범례의 끝말·가운데 칸·뜻 한 줄(제목과 단위)과 지도 이름을 모드마다 바꾸고, 주간 모드는 발표일을 지도 위에 박는다.
원칙: 발표일·지연·연휴 문장은 weekly_release(파이썬 정본)와 같은 답을 내는 홈 weeklyRelease/wkWhenText/wkPubLead 를
그대로 쓰고, 주간 값의 표시는 pv2(반올림 정본), 색은 통계 탭 시군구 주간 지도와 같은 mapColor·WK_MAP_REF 를 쓴다.
지역을 누르면 공급 모드는 시도 공급 리포트, 시세 모드는 그 시도의 주간·월간 그래프(시세 탭 '#stats-market-<주기>~코드',
2026-10-04 대표 요청)가 열리고, 탭 표적(A8 다각형)·라벨은 모드와 무관하다. 카드 셋은 2026-10-04 에 지도 상자 밖(#agg-wrap —
모드 단추 아래, 지도/그래프/표 단추 위)으로 나갔다.

방법: 홈 스크립트(tools/home_src 로 읽는다)의 함수들을 node 로 실제로 돌린다 — 지도는 renderSidoMap 전체를 저장소의 실제
sido-geo.js 좌표로 그려 나온 HTML 을 읽는다. 날짜는 고정 합성 주(2026 공휴일 표, 추석 9/24~26)로만 단정하고 기대값은
파이썬 weekly_release·make_weekly_page.pv2 에서 유도한다(데이터·날짜가 앞으로 가도 초록). CI 에서는 건너뜀도 실패다.
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import kst  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 2026 법정공휴일(대체공휴일 포함) — test_weekly_release·test_home_first_screen 과 같은 표. 추석 09-24(목)~26.
H2026 = ['2026-01-01', '2026-02-16', '2026-02-17', '2026-02-18', '2026-03-01', '2026-03-02', '2026-05-05',
         '2026-05-25', '2026-06-03', '2026-06-06', '2026-08-15', '2026-08-17', '2026-09-24', '2026-09-25',
         '2026-09-26', '2026-10-03', '2026-10-05', '2026-10-09', '2026-12-25']

# 세 상태: 평상 주(9/7 조사 → 9/10 발표, 다음 9/17), 연휴 주(9/14 조사 → 다음 발표 주에 추석), 늦은 주(9/7 조사분이 10/1 에도 최신).
STATES = (('normal', '2026-09-07', (2026, 9, 11)), ('hedge', '2026-09-14', (2026, 9, 18)),
          ('stale', '2026-09-07', (2026, 10, 1)))

# 집계·시도 값: 표시 반올림 경계(−0.0012 → 0.00 보합, −0.085 → −0.09 대칭 반올림, 0.005 → +0.01), 큰 오름·내림, 자료 없음(None).
# 카드 셋(전국·수도권·지방)이 하락·상승·보합을 하나씩 갖게 둔다.
VALS = {'전국': -0.085, '수도권': 0.2299, '지방': -0.0012,
        '서울': 0.40, '경기': 0.2299, '인천': -0.0012, '부산': -0.085, '대구': -0.31, '세종': 0.005, '제주': None}


def _src():
    return HS.home_source()


def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError('%s 의 끝을 찾지 못했다' % name)


def _var(src, name):
    m = re.search(r'^var %s=.*$' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 var %s 를 찾지 못했다' % name
    return m.group(0)


def _wk_block(src):
    m = re.search(r'// <wk-release>[^\n]*\n(.*?)// </wk-release>', src, re.S)
    assert m, 'home-app.js 에서 <wk-release> 구간을 찾지 못했다'
    return m.group(1)


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8'))


def _geo():
    s = io.open(os.path.join(ROOT, 'sido-geo.js'), encoding='utf-8').read()
    return json.loads(re.search(r'SIDO_GEO\s*=\s*(\{.*\})\s*;?\s*$', s, re.S).group(1))


def _kst_ms(y, m, d, hh=12):
    return int(datetime.datetime(y, m, d, hh, 0, tzinfo=kst.KST).timestamp() * 1000)


def _week(p):
    regs = list(SZ.DISPLAY_ORDER)
    return {'regions': regs, 'grace': WR.GRACE_WEEKLY,
            'rows': [{'p': p, 'ma': [VALS.get(z, 0.01) for z in regs], 'je': [0.01] * len(regs)}]}


def _zones():
    """판정 단위 전부. 경기는 균형(g1)으로 둔다 — 주간 모드에 균형 중립색이 새지 않는지 보려고."""
    out = []
    for z in SZ.ORDER:
        g = 'g1' if z == '경기' else ('g0' if z == '인천' else 'g2')
        out.append({'z': z, 'grade': g, 'ratio': {'g1': 0.17, 'g0': -0.2}.get(g, 0.6), 'tot': 1000,
                    'ctxt': '1,000세대 부족(3년 적정물량의 60%)'})
    return out


def _fns(src, names):
    return '\n'.join(_js_func(src, n) for n in names)


def _base_js(src):
    """주간 모드에 쓰는 홈 함수 전부(색·서식·발표 문장·범례·카드) — 실제 소스 그대로."""
    return '\n'.join([
        _wk_block(src), _var(src, 'TB_MIN'), _var(src, 'TB_UP'), _var(src, 'TB_BAL'), _var(src, 'TB_GRADE'),
        _var(src, 'WK_MAP_REF'), _var(src, 'MO_MAP_REF'), _var(src, 'MAP_MODE'),
        re.search(r'^const NATION_TILE=.*$', src, re.M).group(0),
        _fns(src, ('pv2r', 'pv2', 'pvSign', 'mapColor', 'tintA', 'mapFill', 'supplyFill', 'opaqueOnPaper', 'wkFill',
                   'wkPct', 'wkMapModel', 'moMapModel', 'priceModel', 'mapKeyHtml', 'mapAria', 'wkAggCard', 'aggLights', 'aggLightKey', 'aggCard',
                   'tbSigned', 'sidoCode', 'priceOk', 'renderAggCards', 'renderSidoMap')),
    ])


MONTH = '2026-08'


def _month():
    regs = list(SZ.DISPLAY_ORDER)
    return {'regions': regs, 'rows': [{'p': MONTH, 'ma': [VALS.get(z, 0.01) for z in regs], 'je': [0.01] * len(regs)}]}


def _render(src, p, now_ms, mode):
    """renderAggCards·renderSidoMap 을 실제 좌표·합성 데이터로 한 번 그려 카드 상자 + 지도 상자의 HTML 과 모델을 돌려준다."""
    # ktxt·dist 는 옛 data.js 모양(2026-09-28 에 홈에서 뺀 공급 범례 뜻 한 줄·분포 한 줄의 재료) — 그리지 않는지 본다
    ADV = {'sido': {'L': '2026Q2', 'Ltxt': '2026년 2분기', 'ktxt': '뜻 한 줄', 'zones': _zones(), 'dist': '분포'},
           'weekly': _week(p), 'monthly': _month(), 'holidays': H2026}
    js = ('var ADV=%s, SIDO_GEO=%s;\n%s\n'
          'function weeklyReleaseNow(){ _HOLIDAYS=new Set(ADV.holidays); return weeklyRelease(ADV.weekly.rows[0].p,new Date(%d),ADV.weekly.grace); }\n'
          'var EL={dataset:{},innerHTML:"",addEventListener:function(){}}, AG={innerHTML:""}, WB={disabled:false}, TW={textContent:"?"};\n'
          'var document={getElementById:function(id){return id==="map-wrap"?EL:(id==="agg-wrap"?AG:(id==="tb-when"?TW:null))},'
          'querySelector:function(s){return s.indexOf("weekly")>=0?WB:null}};\n'
          'MAP_MODE=%s; renderAggCards(); renderSidoMap();\n'
          'process.stdout.write(JSON.stringify({h:AG.innerHTML+EL.innerHTML,M:wkMapModel(ADV.weekly,weeklyReleaseNow()),'
          'MM:moMapModel(ADV.monthly),r:weeklyReleaseNow(),wb:WB.disabled,tw:TW.textContent}));'
          % (json.dumps(ADV, ensure_ascii=False), json.dumps(_geo(), ensure_ascii=False), _base_js(src), now_ms,
             json.dumps(mode)))
    return _node(js)


def _shapes(h):
    """지도 도형마다 (href, 채움, 표적 다각형 또는 None, 라벨 또는 None)."""
    svg = h[h.index('<svg'):]
    return re.findall(r'<a href="([^"]*)"(?: data-code="[^"]*")?(?: tabindex="-1" aria-hidden="true")? aria-label="[^"]*">'
                      r'<path d="[^"]*" fill="([^"]*)"></path>'
                      r'(?:<polygon class="tap" points="([^"]*)"[^>]*></polygon>)?'
                      r'(?:<text[^>]*>([^<]*)</text>)?', svg)


def _pct(v):
    return '자료 없음' if v is None else MW.pv2(v).replace('-', '−') + '%'


@pytest.mark.parametrize('name,p,today', STATES, ids=[s[0] for s in STATES])
def test_weekly_mode_texts_come_from_data_and_the_release_functions(name, p, today):
    """주간 모드의 발표 줄·범례·카드·지도 이름은 데이터와 공용 함수에서 온다(모드마다 범례 제목·단위가 바뀐다).

    - 기준 줄(지도/그래프/표 단추 왼쪽 #tb-when) = '9/7 기준 · 한국부동산원'(조사일 — 월간 '2026년 8월 기준 · 한국부동산원'과 한
      양식, 2026-10-05 대표 요청. 늦은 주·연휴 주도 같은 양식), 범례 뜻 한 줄 끝 = WR.pub_lead
      (늦은 주 '9/10 발표 기준'), 범례 끝말은 하락·보합·상승, 단위 '(%)'. 공급 범례의 말(공급 여유·균형·부족)은 없다.
    - 카드 셋(전국·수도권·지방)의 값은 pv2 표시값(MW.pv2 와 같다) + '%', 배지는 표시값의 부호로 상승·보합·하락.
    - 공급 모드는 범례 끝말(공급 여유·균형·공급 부족)과 판정 카드(→ /zone/)뿐이다 — 발표 줄 없음, 범례 뜻 한 줄('… · 2026년
      2분기 기준')과 카드 아래 분포 한 줄은 없다(2026-09-28 대표 결정 — 작은 글씨 정리. 옛 data.js 의 ktxt·dist 가 있어도 안 그린다).
    변이(각각 실제로 넣어 빨간 것을 확인): wkMapModel 의 when 을 발표일(_md(r.pub))로 바꾸면 기준 줄 단정, renderAggCards 가
          공급 모드에서 #tb-when 을 비우지 않으면 공급 단정, mapKeyHtml 주간
          갈래의 '(%)' 를 빼면 단위 단정, 주간 범례가 공급 끝말('공급 여유')을 쓰면 끝말 단정, wkPct 가 pv2 대신 toFixed(2)
          (−0.085 → '−0.08', −0.0012 → '−0.00')를 쓰면 카드·지역 이름표 값 단정,
          공급 범례에 뜻 한 줄(ADV.sido.ktxt · Ltxt 기준)을 되살리면 공급 단정.
    픽스처: 2026 추석 공휴일 표, 세 상태(평상·연휴·늦은 주), 반올림 경계 값(−0.0012·−0.085·0.005)과 자료 없음(제주).
    """
    src = _src()
    st = WR.status(p, today=datetime.date(*today), holidays=H2026)
    ms = _kst_ms(*today)
    wk = _render(src, p, ms, 'weekly')
    M, h = wk['M'], wk['h']
    basis = '%s 기준 · 한국부동산원' % WR.md(st['survey'])   # 조사일 기준(2026-10-05 대표 요청 — 주간·월간 양식 통일)
    assert M['when'] == basis and M['lead'] == WR.pub_lead(st), (M, st)
    assert M['stale'] == st['stale'] and (name == 'stale') == st['stale'] and (name == 'hedge') == st['hedge']
    assert wk['tw'] == basis and 'wk-when' not in h, '단추 왼쪽 기준 줄(#tb-when)이 아니다'
    key = re.search(r'<div class="tb-key map-key mk-wk">(.*?)</div>', h).group(1)
    words = re.findall(r'</i>([^<]+)</span>', key)
    assert words == ['하락', '상승'] and '>보합</i>' in key, key
    note = re.search(r'<span class="tk-n">([^<]*)</span>', key).group(1)
    assert note == '아파트 매매가격 전주 대비 변동률(%%) · %s' % WR.pub_lead(st), note
    assert '공급 여유' not in key and '균형' not in key
    assert 'aria-label="시도별 아파트 매매가격 주간 변동 지도 — 붉을수록 상승, 푸를수록 하락, 회색은 보합 · %s"' \
        % WR.pub_lead(st) in h
    cards = re.findall(r'<a class="agg-a" href="([^"]*)"[^>]*><span class="agg-l1"><b>([^<]*)</b>'
                       r'<span class="sc-tier ([^"]*)">([^<]*)</span></span><span class="agg-l2"><i class="agg-n">([^<]*)<', h)
    regs = _week(p)['regions']
    want = []
    for n in SZ.AGG:
        v = VALS.get(n, 0.01)
        r = MW.pv2r(v)
        want.append(('/weekly/', n, 'wk-u' if r > 0 else 'wk-d' if r < 0 else 'wk-0',
                     '상승' if r > 0 else '하락' if r < 0 else '보합', _pct(v)))
    assert cards == want, cards
    assert 'agg-how' not in h and 'class="agg-i"' not in h, '주간 모드에 공급 판정 ⓘ 식이 남았다'
    # 지역 값 서식(카드 밖 — 지도 이름표)도 pv2 정본과 같다
    for n, v in VALS.items():
        if n in regs and n not in SZ.AGG:
            assert re.search(r'aria-label="%s — %s 매매 %s · 누르면 주간 그래프"'
                             % (re.escape(n), re.escape(WR.pub_lead(st)), re.escape(_pct(v))), h), (n, v)

    sup_r = _render(src, p, ms, 'supply')
    sup = sup_r['h']
    assert sup_r['tw'] == '', '공급 모드에 시세 기준 줄이 남았다'
    assert '<i class="mk-b">균형</i>' in sup and '공급 여유' in sup and '공급 부족' in sup
    assert '뜻 한 줄' not in sup and '2026년 2분기 기준' not in sup and 'tk-n' not in sup
    assert 'wk-when' not in sup and '/weekly/' not in sup
    assert 'aria-label="시도별 아파트 공급 부족 지도 — 붉을수록 부족, 푸를수록 여유, 회색은 균형"' in sup
    assert re.findall(r'<a class="agg-a" href="/zone/', sup) and 'agg-dist' not in sup and '분포' not in sup


def test_mode_switch_keeps_targets_and_labels_and_recolors_and_relinks():
    """모드를 바꿔도 탭 표적 다각형(A8)·라벨은 도형마다 같고, 채움과 여는 곳이 바뀐다 — 공급 모드는 시도 공급 리포트
    (/zone/<시도>/), 주간 모드는 그 시도의 주간 그래프('#stats-market-week~<시도 머리 칸 코드>' — NATION_TILE, 광주 b3·전남 c5 는
    통계 탭에서 전남광주로 접힌다, 2026-10-04 대표 요청).

    공급 모드의 채움은 supplyFill(균형 g1 → --bal 중립색, C4②), 주간 모드의 채움은 wkFill = mapColor(v, WK_MAP_REF)를
    지면색 위에 합성한 불투명색이다 — 균형 판정 지역(경기)도 주간 모드에서는 그 주 값의 색이고 --bal 이 아니다. 표시값이
    0.00(인천 −0.0012)이면 보합 회색, 자료 없음(제주)은 --paper2.
    변이(각각 실제로 확인): 주간 갈래의 링크를 공급 리포트로 되돌리면 링크 단정, 표적을 주간 모드에서만 빼면 표적 단정,
          채움을 supplyFill 로 두면(모드가 색을 안 바꿈) 채움 단정, wkFill 이 합성 없이 mapColor 의 rgba 를 그대로 쓰면
          불투명 단정, wkFill 이 WK_MAP_REF 대신 다른 기준(1.0)을 쓰면 채움 단정이 빨개진다.
    픽스처: 저장소 sido-geo.js 좌표 전부, 판정 단위 전부(경기 g1·인천 g0·나머지 g2), 반올림 경계 값이 든 합성 주.
    """
    src = _src()
    p, today = '2026-09-07', (2026, 9, 11)
    sup = _render(src, p, _kst_ms(*today), 'supply')['h']
    wk = _render(src, p, _kst_ms(*today), 'weekly')['h']
    a, b = _shapes(sup), _shapes(wk)
    geo = _geo()['p']
    assert len(a) == len(b) == len(geo), (len(a), len(b), len(geo))
    # 한 판정 단위의 둘째 도형(라벨 없는 도형 — 전남광주의 광주 쪽)은 키보드 순서·읽기에서 뺀다(백로그 36-8 — 같은 곳으로 가는 초점이
    # 두 번 섰다). 변이: home-app.js 의 dup 을 늘 '' 로 두면 빨강(확인).
    for h, shapes in ((sup, a), (wk, b)):
        assert h.count('tabindex="-1" aria-hidden="true"') == sum(1 for x in shapes if not x[3]) >= 1
    assert 'role="group"' in sup and 'role="img" aria-label="시도별' not in sup
    heads = {t[1]: t[0] for t in MW.nation_tile(src)['t'] if t[4] and len(t[0]) == 2}
    assert all(x[0].startswith('/zone/') for x in a)
    assert [x[0] for x in b] == ['#stats-market-week~%s' % heads[g['n']] for g in geo], '주간 모드 지역 링크가 그 시도 그래프가 아니다'
    assert [x[2] for x in a] == [x[2] for x in b] and sum(1 for x in b if x[2]) >= 8, '탭 표적이 모드에 따라 달라졌다'
    assert [x[3] for x in a] == [x[3] for x in b]
    # 채움 — 기대값을 JS 함수(mapColor·opaqueOnPaper)가 아니라 여기서 따로 합성해 대조한다
    paper = [int(x) for x in re.search(r'PAPER_RGB=\[(\d+),(\d+),(\d+)\]', src).groups()]
    ref = float(re.search(r'^var WK_MAP_REF=([\d.]+);', src, re.M).group(1))
    zone_of = {}
    for g, (href, _, _, _) in zip(geo, a):
        zone_of[g['n']] = unquote(href.split('/')[2])
    for (href, fill_s, _, _), (_, fill_w, _, _), g in zip(a, b, geo):
        z = zone_of[g['n']]
        v = VALS.get(z, 0.01)
        if z == '경기':
            assert fill_s == 'var(--bal)', '균형 지역의 공급 채움이 중립색이 아니다: %s' % fill_s
        if v is None:
            assert fill_w == 'var(--paper2)', (z, fill_w)
            continue
        r = MW.pv2r(v)
        if r == 0:
            assert fill_w == '#e8ecea', (z, fill_w)
            continue
        al = 0.14 + 0.72 * min(abs(v) / ref, 1)
        c = (224, 86, 74) if r > 0 else (58, 123, 213)
        want = 'rgb(%s)' % ','.join(str(int(round(P + (C - P) * float('%.3f' % al) + 1e-9)))
                                    for P, C in zip(paper, c))
        got = [int(x) for x in re.findall(r'\d+', fill_w)]
        assert fill_w.startswith('rgb(') and all(abs(x - y) <= 1 for x, y in zip(got, [int(x) for x in re.findall(r'\d+', want)])), \
            (z, v, fill_w, want)
        assert fill_w != fill_s and fill_w != 'var(--bal)'


MODE_HARNESS = r'''
%(fns)s
var MAP_MODE='supply', TB_VIEW=%(view)s, sent=[], drawn=0, cards=0, views=[], HAS=%(has)s;
function track(e,p){ sent.push([e,p]); }
function renderSidoMap(){ drawn++; } function renderAggCards(){ cards++; }
function tbView(v,quiet){ views.push([v,!!quiet]); TB_VIEW=v; }
var WK_MAP_REF=0.4, MO_MAP_REF=1.0, SIDO_GEO={};
function weeklyReleaseNow(){ return HAS?{survey:"2026-09-07",pub:"2026-09-10",next:"2026-09-17",hedge:false,stale:false}:null; }
function wkWhenText(){ return "w"; } function wkPubLead(){ return "l"; }
var ADV={weekly:HAS?{regions:["전국"],rows:[{p:"2026-09-07",ma:[0.1]}]}:{},monthly:HAS?{regions:["전국"],rows:[{p:"2026-08",ma:[0.3]}]}:{}};
function mk(m,on){ var a={"aria-pressed":on?"true":"false"}; return {dataset:{m:m},cls:on?["on"]:[],
  classList:{toggle:function(c,v){ this.o.cls=v?["on"]:[]; }},getAttribute:function(k){return a[k]},setAttribute:function(k,v){a[k]=v}}; }
var B=[mk("supply",true),mk("weekly",false),mk("monthly",false)]; B.forEach(function(b){ b.classList.o=b; });
var EL={dataset:{done:"1"}};
var SEC={price:false,classList:{toggle:function(c,v){ if(c==="mm-price") SEC.price=v; }}};
var document={getElementById:function(id){ return id==="map-wrap"?EL:(id==="sec-score"?SEC:(id==="map-mode"?{querySelectorAll:function(){return B}}:null)); }};
var st=[];
function snap(){ st.push([MAP_MODE,B.map(function(b){return b.getAttribute("aria-pressed")+(b.cls.length?"+on":"")}).join(),drawn,cards,EL.dataset.done,SEC.price]); }
mapMode("weekly"); snap(); mapMode("weekly"); snap(); mapMode("monthly"); snap(); mapMode("nonsense"); snap(); mapMode("supply"); snap();
process.stdout.write(JSON.stringify({st:st,sent:sent,views:views}));
'''


def test_mode_toggle_markup_state_and_measurement():
    """모드 단추 셋(2026-10-04 대표 요청 — 월간 추가, 10-05 이름 바꿈): 홈 마크업은 group + aria-pressed 세 단추(기본 '공급 현황' 눌림)이고
    판정 카드 상자(#agg-wrap) 위, 지도/그래프/표 줄(.tb-bar) 밖에 있다 — 지도/그래프/표 단추는 카드 아래다. 보기와 무관하게 늘
    보인다. mapMode 는 누른 단추의 aria-pressed·on 을 맞추고 카드·지도를 다시 그리며(done 초기화), 모드가 바뀔 때만 map_mode 를
    한 번 잰다(값은 snake_case supply·weekly·monthly — 모르는 값은 supply). 시세 데이터가 없으면 전환하지 않고 재지도 않는다.
    공급 그래프·표를 보던 중에 시세 모드를 누르면 지도로 돌린다(시세 그래프·표는 시세 탭이 맡는다).
    변이(각각 실제로 확인): mapMode 에서 aria-pressed 갱신이나 on 클래스 갱신을 빼면 상태 단정, tbView('map',true) 의 quiet 를
          빼면 보기 단정(supply_view 가 덤으로 나간다 — 2026-10-05 리뷰), mm-price 토글을 빼면 상태 단정, 같은 모드 재클릭에도 track 을 부르면 측정 횟수
          단정, 데이터 없음 가드를 빼면 마지막 단정, renderAggCards 호출을 빼면 카드 단정, 모드 단추를 .tb-bar 안으로 되돌리면
          자리 단정, 그래프 보기에서 시세 모드를 누를 때 tbView('map') 을 빼면 보기 단정이 빨개진다.
    픽스처: 저장소 index.html·home-app.js 의 mapMode·wkMapModel·moMapModel·priceModel 과 합성 DOM(단추 셋·지도 상자).
    """
    src = _src()
    m = re.search(r'<div class="tb-seg map-mode" id="map-mode" role="group" aria-label="[^"]+">(.*?)</div>', src, re.S)
    assert m, '지도 모드 전환 묶음(#map-mode)이 홈 마크업에 없다'
    btns = re.findall(r'<button type="button" data-m="([a-z_]+)"( class="on")? aria-pressed="(true|false)" '
                      r'onclick="mapMode\(\'([a-z_]+)\'\)">(.*?)</button>', m.group(1))
    assert [(b[0], bool(b[1]), b[2], b[3], b[4]) for b in btns] == [
        ('supply', True, 'true', 'supply', '공급 현황'), ('weekly', False, 'false', 'weekly', '주간 시세'),
        ('monthly', False, 'false', 'monthly', '월간 시세')], btns   # 이름은 2026-10-05 대표 요청('공급 현황·주간 시세·월간 시세')
    assert m.start() < src.index('<div id="agg-wrap">') < src.index('<div class="tb-bar">') < src.index('id="tb-view"'), \
        '모드 단추 → 카드 → 지도/그래프/표 순서가 아니다'
    bar = src[src.index('<div class="tb-bar">'):src.index('id="tb-view"')]
    assert bar.rstrip().endswith('<p class="tb-when" id="tb-when"></p>\n      <div class="tb-seg tb-view"'), \
        '시세 기준 줄(#tb-when)이 지도/그래프/표 단추 바로 왼쪽에 없다(2026-10-05 대표 요청)'
    css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    assert not re.search(r':not\(\.vm-map\) \.map-mode\{display:none\}', css), '모드 단추가 그래프·표 보기에서 숨는다'

    fns = '\n'.join(_js_func(src, n) for n in ('mapMode', 'wkMapModel', 'moMapModel', 'priceModel', 'priceOk', '_md'))
    got = _node(MODE_HARNESS % {'fns': fns, 'has': 'true', 'view': '"map"'})
    assert got['st'] == [['weekly', 'false,true+on,false', 1, 1, '', True],
                         ['weekly', 'false,true+on,false', 1, 1, '', True],
                         ['monthly', 'false,false,true+on', 2, 2, '', True],
                         ['supply', 'true+on,false,false', 3, 3, '', False],
                         ['supply', 'true+on,false,false', 3, 3, '', False]], got['st']
    # 공급 출처 줄은 시세 모드에서 숨는다(#sec-score.mm-price — 시세 지도의 출처가 아니다, 2026-10-05 리뷰)
    assert '#sec-score.mm-price .map-src{display:none}' in css
    assert got['sent'] == [['map_mode', {'mode': 'weekly'}], ['map_mode', {'mode': 'monthly'}],
                           ['map_mode', {'mode': 'supply'}]], got['sent']
    assert all(re.match(r'^[a-z][a-z0-9_]*$', x) for e, p in got['sent'] for x in (e, p['mode']))
    assert got['views'] == []
    g2 = _node(MODE_HARNESS % {'fns': fns, 'has': 'true', 'view': '"graph"'})
    assert g2['views'] == [['map', True]], '공급 그래프를 보던 중 시세 모드를 눌렀는데 지도로 조용히(quiet) 돌리지 않았다'
    none = _node(MODE_HARNESS % {'fns': fns, 'has': 'false', 'view': '"map"'})
    assert none['st'][0][:1] == ['supply'] and none['sent'] == [], none


TBVIEW_HARNESS = r'''
%(fns)s
var MAP_MODE=%(mode)s, TB_VIEW='map', sent=[];
function track(e,p){ sent.push([e,p]); }
var location={hash:''};
var document={getElementById:function(){ return null; }};
tbView(%(v)s);
process.stdout.write(JSON.stringify({hash:location.hash,view:TB_VIEW,sent:sent}));
'''


@pytest.mark.parametrize('mode,v,want', [
    ('weekly', 'graph', '#stats-market-week~a0'), ('weekly', 'table', '#stats-market-week~a0-t'),
    ('monthly', 'graph', '#stats-market-month~a0'), ('monthly', 'table', '#stats-market-month~a0-t')])
def test_price_mode_graph_and_table_open_the_stats_tab(mode, v, want):
    """시세 모드(주간·월간)의 '그래프'·'표' 단추는 홈에 새로 그리지 않고 시세 탭의 그 화면(전국)을 연다(2026-10-04 대표 요청).
    주소 '#stats-market-<주기>~a0'(그래프)·'~a0-t'(표)는 applyHash → openTrendRegion 이 받는다(test_home_entry). 홈 보기(TB_VIEW)는
    지도 그대로라 뒤로 오면 시세 지도가 남아 있다.
    변이(각각 실제로 확인): 표 단추에 '-t' 를 빼면 표 단정, 월간을 주간 주소로 보내면 주기 단정, 시세 모드 갈래를 빼면(공급
          그래프로 바뀜) 주소 단정이 빨개진다. 픽스처: 저장소 tbView 와 합성 DOM.
    """
    src = _src()
    got = _node(TBVIEW_HARNESS % {'fns': _js_func(src, 'tbView'), 'mode': json.dumps(mode), 'v': json.dumps(v)})
    assert got['hash'] == want and got['view'] == 'map', got
    assert got['sent'] == [['trend_pick', {'period': want.split('-')[2].split('~')[0], 'region': 'a0', 'from': 'score_' + v}]], got


def test_monthly_mode_cards_legend_links_and_colors():
    """월간 모드(2026-10-04 대표 요청 — 홈에서 월간도 쉽게): 카드 셋은 최신 달 전국·수도권·지방 매매 변동률(→ /monthly/, '매매
    전월 대비'), 카드 아래 기준 달 줄, 범례 뜻 한 줄 '아파트 매매가격 전월 대비 변동률(%) · 8월 기준', 지역은 그 시도 월간 그래프
    ('#stats-market-month~코드'), 색은 통계 탭 시군구 월간 지도와 같은 MO_MAP_REF 만색 기준이다.
    변이(각각 실제로 확인): moMapModel 이 WK_MAP_REF 를 쓰면 색 단정, 카드 링크를 /weekly/ 로 두면 카드 단정, 월간 지도 링크를
          주간 주소로 두면 링크 단정이 빨개진다.
    픽스처: 반올림 경계 값이 든 합성 달 2026-08(주간과 같은 VALS), 저장소 sido-geo.js 좌표.
    """
    src = _src()
    out = _render(src, '2026-09-07', _kst_ms(2026, 9, 11), 'monthly')
    h, MM = out['h'], out['MM']
    assert MM['when'] == '2026년 8월 기준 · 한국부동산원' and MM['lead'] == '8월 기준', MM
    assert out['tw'] == MM['when'] and 'wk-when' not in h
    note = re.search(r'<span class="tk-n">([^<]*)</span>', h).group(1)
    assert note == '아파트 매매가격 전월 대비 변동률(%) · 8월 기준', note
    cards = re.findall(r'<a class="agg-a" href="([^"]*)"[^>]*>.*?<i class="agg-n">([^<]*)<.*?<i class="agg-p">([^<]*)</i>', h)
    assert cards == [('/monthly/', _pct(VALS[n]), '매매 전월 대비') for n in SZ.AGG], cards
    heads = {t[1]: t[0] for t in MW.nation_tile(src)['t'] if t[4] and len(t[0]) == 2}
    links = [x[0] for x in _shapes(h)]
    assert links == ['#stats-market-month~%s' % heads[g['n']] for g in _geo()['p']], links[:3]
    ref = float(re.search(r'^var MO_MAP_REF=([\d.]+);', src, re.M).group(1))
    seoul = [x[1] for x, g in zip(_shapes(h), _geo()['p']) if g['n'] == '서울'][0]
    paper = [int(x) for x in re.search(r'PAPER_RGB=\[(\d+),(\d+),(\d+)\]', src).groups()]
    al = float('%.3f' % (0.14 + 0.72 * min(abs(VALS['서울']) / ref, 1)))
    want = [int(round(P + (C - P) * al + 1e-9)) for P, C in zip(paper, (224, 86, 74))]
    got = [int(x) for x in re.findall(r'\d+', seoul)]
    assert all(abs(x - y) <= 1 for x, y in zip(got, want)), (seoul, want)


def test_weekly_color_scale_is_one_constant():
    """주간 변동 색의 만색 기준은 한 상수(WK_MAP_REF) — 홈 지도 주간 모드·통계 탭 시군구 주간 지도·히어로 배경이 같이 쓴다.
    예전엔 뒤의 둘이 각자 0.4 를 적었다(같은 대상을 재는 코드는 같은 상수, CLAUDE.md).
    변이(실제로 확인): drawNationMap 이나 renderHeroMap 에 0.4 를 다시 적으면, wkFill 이 다른 기준을 쓰면 빨개진다.
    픽스처: 저장소 home-app.js.
    """
    src = _src()
    assert len(re.findall(r'^var WK_MAP_REF=', src, re.M)) == 1
    assert "k==='week'?WK_MAP_REF:" in _js_func(src, 'drawNationMap')
    assert 'mapColor(v[a[0]],WK_MAP_REF)' in _js_func(src, 'renderHeroMap')
    assert 'mapColor(v,ref||WK_MAP_REF)' in _js_func(src, 'wkFill')
    # 월간도 한 상수(MO_MAP_REF) — 홈 지도 월간 모드와 통계 탭 시군구 월간 지도가 같이 쓴다(2026-10-04)
    assert len(re.findall(r'^var MO_MAP_REF=', src, re.M)) == 1
    assert "k==='week'?WK_MAP_REF:MO_MAP_REF" in _js_func(src, 'drawNationMap')
    assert 'ref:MO_MAP_REF' in _js_func(src, 'moMapModel')
    for fn in ('drawNationMap', 'renderHeroMap', 'wkFill', 'mapKeyHtml'):
        assert not re.search(r'mapColor\([^)]*,\s*0\.\d', _js_func(src, fn)), '%s 가 기준을 숫자로 적었다' % fn


LOCK_HARNESS = r'''
%(base)s
function weeklyReleaseNow(){ _HOLIDAYS=new Set(ADV.holidays); return weeklyRelease(ADV.weekly.rows[0].p,new Date(%(ms)d),ADV.weekly.grace); }
var BT={weekly:{disabled:false},monthly:{disabled:false},map:{disabled:false}}, AG={innerHTML:""}, sent=[], picked=[], views=[], TB_VIEW="map";
var EL={dataset:{},innerHTML:"",ls:[],addEventListener:function(t,f){ this.ls.push([t,f]); }};
function track(e,p){ sent.push([e,p]); }
function tbView(v){ views.push(v); }
function onTrendLink(e,from){ picked.push(from); }
var document={getElementById:function(id){return id==="map-wrap"?EL:(id==="agg-wrap"?AG:null)},
  querySelector:function(s){ var m=/data-[mv]="([a-z]+)"/.exec(s); return m?BT[m[1]]:null; }};
renderAggCards(); renderSidoMap();
EL.ls.forEach(function(x){ if(x[0]==="click") x[1]({}); });
process.stdout.write(JSON.stringify({w:BT.weekly.disabled,m:BT.monthly.disabled,map:BT.map.disabled,views:views,picked:picked}));
'''


@pytest.mark.parametrize('case', ['all', 'no_month', 'no_week', 'no_geo'])
def test_price_buttons_lock_when_their_data_or_the_map_is_missing(case):
    """시세 단추는 그 재료가 없으면 잠긴다(월간 행이 없으면 월간만, 주간 행이 없으면 주간만). 지도 좌표(sido-geo.js)가 안 오면
    시세 모드는 지도 전용이라 둘 다 잠근다 — 잠그지 않으면 지도 폴백(표)과 시세 갈래(시세 탭으로 보내기)가 서로 불러 누르는
    순간 시세 탭으로 튄다(2026-10-05 리뷰). 지도가 그려지면 지도 누름 처리(onTrendLink, from 'score_map')가 한 번 붙는다.
    변이(각각 실제로 확인): renderAggCards 의 잠금을 빼면 no_month·no_week 가, priceOk 의 SIDO_GEO 검사를 빼면 no_geo 가,
          renderSidoMap 의 click 처리 붙이기를 빼면 all 의 picked 단정이 빨개진다.
    픽스처: 합성 주(2026-09-07)·달(2026-08), 저장소 sido-geo.js 좌표 — 재료를 하나씩 비운 네 상태.
    """
    src = _src()
    ADV = {'sido': {'L': '2026Q2', 'Ltxt': '2026년 2분기', 'zones': _zones()},
           'weekly': _week('2026-09-07'), 'monthly': _month(), 'holidays': H2026}
    if case == 'no_month':
        ADV['monthly'] = {'regions': [], 'rows': []}
    if case == 'no_week':
        ADV['weekly'] = dict(ADV['weekly'], regions=[])
    geo = '' if case == 'no_geo' else 'var SIDO_GEO=%s;' % json.dumps(_geo(), ensure_ascii=False)
    base = 'var ADV=%s; %s\n%s' % (json.dumps(ADV, ensure_ascii=False), geo, _base_js(src))
    got = _node(LOCK_HARNESS % {'base': base, 'ms': _kst_ms(2026, 9, 11)})
    want = {'all': (False, False), 'no_month': (False, True), 'no_week': (True, False), 'no_geo': (True, True)}[case]
    assert (got['w'], got['m']) == want, got
    if case == 'no_geo':
        assert got['map'] and got['views'] == ['table'], got   # 공급 모드의 표 폴백은 그대로
    else:
        assert got['picked'] == ['score_map'], got


OPEN_HARNESS = r'''
%(fn)s
var TREND={week:{sel:"s"}}, TREND_P=Promise.resolve(), TR_OPEN={week:null}, TRSHOW={}, SGG_HIST_READY=true, calls=[];
function trendData(){ return {regions:["전국"]}; } function trendTarget(W,c){ return {zone:"전국",sgg:""}; }
function fillTrendReg(){} function fillSggSel(){} function renderWeekSec(){} function afterLayout(){}
function gtSet(k,v,silent){ calls.push([k,v,silent]); }
var document={getElementById:function(){ return {value:""}; }};
openTrendRegion("week","a0","t").then(function(){ return openTrendRegion("week","a0"); })
  .then(function(){ process.stdout.write(JSON.stringify(calls)); });
'''


def test_open_trend_region_opens_the_table_for_the_t_route():
    """'#stats-market-<주기>~코드-t'(홈 시세 모드의 '표' 단추)는 그 지역을 표로, '-t' 없는 주소(지도 칸·'그래프' 단추)는 그래프로
    연다 — openTrendRegion 의 셋째 인자. 열 때 바꾼 보기는 사람이 누른 전환이 아니라 재지 않는다(silent).
    변이(실제로 확인): gtSet(k,view==='t'?'t':'g',true) 를 늘 'g' 로 두면 첫 단정이 빨개진다(2026-10-05 리뷰 — 그전엔 시험이 없었다).
    픽스처: 저장소 openTrendRegion 과 합성 통계 탭(데이터 받기는 끝난 상태).
    """
    got = _node(OPEN_HARNESS % {'fn': _js_func(_src(), 'openTrendRegion')})
    assert got == [['week', 't', True], ['week', 'g', True]], got
