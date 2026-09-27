# -*- coding: utf-8 -*-
"""홈 공급 지도의 두 모드 '3년 공급 / 이번 주 시세'(홈 마케팅 검수 C3·IA-1 안 B, 2026-09-27).

재현하는 실제 상태: 09-26 까지 홈 지도는 분기 공급 판정 하나만 칠했고, 매주 바뀌는 값은 두 화면 아래 주간 격자에만
있었다(IA-1). 한 지도에 주간 시세를 함께 싣되, 같은 빨강·파랑이 모드마다 다른 뜻(공급 부족·여유 ↔ 매매 상승·하락)이
되므로 범례의 끝말·가운데 칸·뜻 한 줄(제목과 단위)과 지도 이름을 모드마다 바꾸고, 주간 모드는 발표일을 지도 위에 박는다.
원칙: 발표일·지연·연휴 문장은 weekly_release(파이썬 정본)와 같은 답을 내는 홈 weeklyRelease/wkWhenText/wkPubLead 를
그대로 쓰고, 주간 값의 표시는 pv2(반올림 정본), 색은 통계 탭 시군구 주간 지도와 같은 mapColor·WK_MAP_REF 를 쓴다.
지역을 누르면 두 모드 모두 시도 공급 리포트가 열리고 탭 표적(A8 다각형)·라벨은 모드와 무관하다.

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
                    'ctxt': '1,000세대 부족 · 3년 필요량의 60%만큼'})
    return out


def _fns(src, names):
    return '\n'.join(_js_func(src, n) for n in names)


def _base_js(src):
    """주간 모드에 쓰는 홈 함수 전부(색·서식·발표 문장·범례·카드) — 실제 소스 그대로."""
    return '\n'.join([
        _wk_block(src), _var(src, 'TB_MIN'), _var(src, 'TB_UP'), _var(src, 'TB_BAL'), _var(src, 'TB_GRADE'),
        _var(src, 'WK_MAP_REF'), _var(src, 'MAP_MODE'),
        _fns(src, ('pv2r', 'pv2', 'pvSign', 'mapColor', 'tintA', 'mapFill', 'supplyFill', 'opaqueOnPaper', 'wkFill',
                   'wkPct', 'wkMapModel', 'mapKeyHtml', 'mapAria', 'wkAggCard', 'aggCard', 'distLinks', 'tbSigned',
                   'renderSidoMap')),
    ])


def _render(src, p, now_ms, mode):
    """renderSidoMap 을 실제 좌표·합성 데이터로 한 번 그려 map-wrap 의 HTML 과 모델을 돌려준다."""
    ADV = {'sido': {'L': '2026Q2', 'Ltxt': '2026년 2분기', 'ktxt': '뜻 한 줄', 'zones': _zones(), 'dist': '분포'},
           'weekly': _week(p), 'holidays': H2026}
    js = ('var ADV=%s, SIDO_GEO=%s;\n%s\n'
          'function weeklyReleaseNow(){ _HOLIDAYS=new Set(ADV.holidays); return weeklyRelease(ADV.weekly.rows[0].p,new Date(%d),ADV.weekly.grace); }\n'
          'var EL={dataset:{},innerHTML:""}, WB={disabled:false};\n'
          'var document={getElementById:function(id){return id==="map-wrap"?EL:null},'
          'querySelector:function(s){return s.indexOf("weekly")>=0?WB:null}};\n'
          'MAP_MODE=%s; renderSidoMap();\n'
          'process.stdout.write(JSON.stringify({h:EL.innerHTML,M:wkMapModel(ADV.weekly,weeklyReleaseNow()),'
          'r:weeklyReleaseNow(),wb:WB.disabled}));'
          % (json.dumps(ADV, ensure_ascii=False), json.dumps(_geo(), ensure_ascii=False), _base_js(src), now_ms,
             json.dumps(mode)))
    return _node(js)


def _shapes(h):
    """지도 도형마다 (href, 채움, 표적 다각형 또는 None, 라벨 또는 None)."""
    svg = h[h.index('<svg'):]
    return re.findall(r'<a href="([^"]*)" aria-label="[^"]*"><path d="[^"]*" fill="([^"]*)"></path>'
                      r'(?:<polygon class="tap" points="([^"]*)"[^>]*></polygon>)?'
                      r'(?:<text[^>]*>([^<]*)</text>)?', svg)


def _pct(v):
    return '자료 없음' if v is None else MW.pv2(v).replace('-', '−') + '%'


@pytest.mark.parametrize('name,p,today', STATES, ids=[s[0] for s in STATES])
def test_weekly_mode_texts_come_from_data_and_the_release_functions(name, p, today):
    """주간 모드의 발표 줄·범례·카드·지도 이름은 데이터와 공용 함수에서 온다(모드마다 범례 제목·단위가 바뀐다).

    - 지도 위 발표 줄 = 주간 구역 머리줄과 같은 문장(파이썬 WR.when_text 와 글자까지 같다), 범례 뜻 한 줄 끝 = WR.pub_lead
      (늦은 주 '9/10 발표 기준'), 범례 끝말은 하락·보합·상승, 단위 '(%)'. 공급 범례의 말(공급 여유·균형·부족)은 없다.
    - 카드 셋(전국·수도권·지방)의 값은 pv2 표시값(MW.pv2 와 같다) + '%', 배지는 표시값의 부호로 상승·보합·하락.
    - 공급 모드는 예전 범례·카드 그대로(공급 여유·균형·공급 부족, 판정 카드 → /zone/), 발표 줄 없음.
    변이(각각 실제로 넣어 빨간 것을 확인): wkMapModel 의 when 을 발표일만(_md(r.pub)) 으로 바꾸면 발표 줄 단정, mapKeyHtml 주간
          갈래의 '(%)' 를 빼면 단위 단정, 주간 범례가 공급 끝말('공급 여유')을 쓰면 끝말 단정, wkPct 가 pv2 대신 toFixed(2)
          (−0.085 → '−0.08', −0.0012 → '−0.00')를 쓰면 카드·지역 이름표 값 단정, renderSidoMap 주간 갈래가 발표 줄을 안 그리면 발표 줄 단정.
    픽스처: 2026 추석 공휴일 표, 세 상태(평상·연휴·늦은 주), 반올림 경계 값(−0.0012·−0.085·0.005)과 자료 없음(제주).
    """
    src = _src()
    st = WR.status(p, today=datetime.date(*today), holidays=H2026)
    ms = _kst_ms(*today)
    wk = _render(src, p, ms, 'weekly')
    M, h = wk['M'], wk['h']
    assert M['when'] == WR.when_text(st) and M['lead'] == WR.pub_lead(st), (M, st)
    assert M['stale'] == st['stale'] and (name == 'stale') == st['stale'] and (name == 'hedge') == st['hedge']
    assert '<p class="agg-dist wk-when">%s</p>' % WR.when_text(st) in h, '지도 위 발표 줄이 없다'
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
            assert re.search(r'aria-label="%s — 이번 주 매매 %s · ' % (re.escape(n), re.escape(_pct(v))), h), (n, v)

    sup = _render(src, p, ms, 'supply')['h']
    assert '<i class="mk-b">균형</i>' in sup and '공급 여유' in sup and '공급 부족' in sup
    assert '뜻 한 줄 · 2026년 2분기 기준' in sup and 'wk-when' not in sup and '/weekly/' not in sup
    assert 'aria-label="시도별 아파트 공급 부족 지도 — 붉을수록 부족, 푸를수록 여유, 회색은 균형"' in sup
    assert re.findall(r'<a class="agg-a" href="/zone/', sup) and '<p class="agg-dist">분포' in sup


def test_mode_switch_keeps_links_targets_and_labels_and_recolors_only():
    """모드를 바꿔도 지역을 누르면 여는 곳(/zone/<시도>/)·탭 표적 다각형(A8)·라벨은 도형마다 같고, 채움만 바뀐다.

    공급 모드의 채움은 supplyFill(균형 g1 → --bal 중립색, C4②), 주간 모드의 채움은 wkFill = mapColor(v, WK_MAP_REF)를
    지면색 위에 합성한 불투명색이다 — 균형 판정 지역(경기)도 주간 모드에서는 그 주 값의 색이고 --bal 이 아니다. 표시값이
    0.00(인천 −0.0012)이면 보합 회색, 자료 없음(제주)은 --paper2.
    변이(각각 실제로 확인): 주간 갈래에서 링크를 '/weekly/' 로 바꾸면 링크 단정, 표적을 주간 모드에서만 빼면 표적 단정,
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
    assert [x[0] for x in a] == [x[0] for x in b] and all(x[0].startswith('/zone/') for x in b)
    assert [x[2] for x in a] == [x[2] for x in b] and sum(1 for x in b if x[2]) >= 8, '탭 표적이 모드에 따라 달라졌다'
    assert [x[3] for x in a] == [x[3] for x in b]
    # 채움 — 기대값을 JS 함수(mapColor·opaqueOnPaper)가 아니라 여기서 따로 합성해 대조한다
    paper = [int(x) for x in re.search(r'PAPER_RGB=\[(\d+),(\d+),(\d+)\]', src).groups()]
    ref = float(re.search(r'^var WK_MAP_REF=([\d.]+);', src, re.M).group(1))
    zone_of = {}
    for g, (href, _, _, _) in zip(geo, b):
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
var MAP_MODE='supply', sent=[], drawn=0, HAS=%(has)s;
function track(e,p){ sent.push([e,p]); }
function renderSidoMap(){ drawn++; }
function weeklyReleaseNow(){ return HAS?{survey:"2026-09-07",pub:"2026-09-10",next:"2026-09-17",hedge:false,stale:false}:null; }
function wkWhenText(){ return "w"; } function wkPubLead(){ return "l"; }
var ADV={weekly:HAS?{regions:["전국"],rows:[{p:"2026-09-07",ma:[0.1]}]}:{}};
function mk(m,on){ var a={"aria-pressed":on?"true":"false"}; return {dataset:{m:m},cls:on?["on"]:[],
  classList:{toggle:function(c,v){ this.o.cls=v?["on"]:[]; }},getAttribute:function(k){return a[k]},setAttribute:function(k,v){a[k]=v}}; }
var B=[mk("supply",true),mk("weekly",false)]; B.forEach(function(b){ b.classList.o=b; });
var EL={dataset:{done:"1"}};
var document={getElementById:function(id){ return id==="map-wrap"?EL:(id==="map-mode"?{querySelectorAll:function(){return B}}:null); }};
var st=[];
function snap(){ st.push([MAP_MODE,B.map(function(b){return b.getAttribute("aria-pressed")}),B.map(function(b){return b.cls.join()}),drawn,EL.dataset.done]); }
mapMode("weekly"); snap(); mapMode("weekly"); snap(); mapMode("nonsense"); snap(); mapMode("supply"); snap();
process.stdout.write(JSON.stringify({st:st,sent:sent}));
'''


def test_mode_toggle_markup_state_and_measurement():
    """전환 버튼: 홈 마크업은 group + aria-pressed 두 버튼(기본 '3년 공급' 눌림), 지도 보기에서만 보인다. mapMode 는
    누른 버튼의 aria-pressed·on 을 맞추고 지도를 다시 그리며(done 초기화), 모드가 바뀔 때만 map_mode 를 한 번 잰다(값은
    snake_case supply·weekly — 모르는 값은 supply). 주간 데이터가 없으면 전환하지 않고 재지도 않는다.
    변이(각각 실제로 확인): mapMode 에서 aria-pressed 갱신을 빼면 상태 단정, 같은 모드 재클릭에도 track 을 부르면 측정 횟수
          단정, 데이터 없음 가드를 빼면 마지막 단정, 기본 버튼의 aria-pressed 를 false 로 두면 마크업 단정, CSS 의 '지도 보기에서만'
          규칙을 지우면 규칙 단정이 빨개진다.
    픽스처: 저장소 index.html·app.css·home-app.js 의 mapMode 와 합성 DOM(버튼 둘·지도 상자).
    """
    src = _src()
    m = re.search(r'<div class="tb-seg map-mode" id="map-mode" role="group" aria-label="[^"]+">(.*?)</div>', src, re.S)
    assert m, '지도 모드 전환 묶음(#map-mode)이 홈 마크업에 없다'
    btns = re.findall(r'<button type="button" data-m="([a-z_]+)"( class="on")? aria-pressed="(true|false)" '
                      r'onclick="mapMode\(\'([a-z_]+)\'\)">(.*?)</button>', m.group(1))
    assert [(b[0], bool(b[1]), b[2], b[3]) for b in btns] == [('supply', True, 'true', 'supply'),
                                                             ('weekly', False, 'false', 'weekly')], btns
    assert re.sub(r'<[^>]+>', '', btns[0][4]) == '3년 공급' and re.sub(r'<[^>]+>', '', btns[1][4]) == '이번 주 시세'
    assert m.start() < src.index('id="tb-view"') and m.start() > src.index('<div class="tb-bar">'), \
        '전환 버튼이 지도/그래프/표 줄 안에 있지 않다 — 줄을 새로 만들면 기본 모드의 첫 화면이 밀린다'
    css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    assert re.search(r'#sec-score:not\(\.vm-map\) \.map-mode\{display:none\}', css), '전환 버튼이 그래프·표에서도 보인다'

    fns = _js_func(src, 'mapMode') + '\n' + _js_func(src, 'wkMapModel')
    got = _node(MODE_HARNESS % {'fns': fns, 'has': 'true'})
    assert got['st'] == [['weekly', ['false', 'true'], ['', 'on'], 1, ''],
                         ['weekly', ['false', 'true'], ['', 'on'], 1, ''],
                         ['supply', ['true', 'false'], ['on', ''], 2, ''],
                         ['supply', ['true', 'false'], ['on', ''], 2, '']], got['st']
    assert got['sent'] == [['map_mode', {'mode': 'weekly'}], ['map_mode', {'mode': 'supply'}]], got['sent']
    assert all(re.match(r'^[a-z][a-z0-9_]*$', x) for e, p in got['sent'] for x in (e, p['mode']))
    none = _node(MODE_HARNESS % {'fns': fns, 'has': 'false'})
    assert none['st'][0][:1] == ['supply'] and none['sent'] == [], none


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
    assert 'mapColor(v,WK_MAP_REF)' in _js_func(src, 'wkFill')
    for fn in ('drawNationMap', 'renderHeroMap', 'wkFill', 'mapKeyHtml'):
        assert not re.search(r'mapColor\([^)]*,\s*0\.\d', _js_func(src, fn)), '%s 가 기준을 숫자로 적었다' % fn
