# -*- coding: utf-8 -*-
"""홈·시세 탭 첫 화면 정리(2026-10-30 디자인 리뷰 2차)가 되돌아가지 않는다.

재현하는 실제 상태(리뷰 캡처, 375px·1280px):
  ① 시군구 타일 지도가 375px 에서 오른쪽이 잘려 보이는데 밀 수 있다는 단서가 맨 아래 문장뿐이었다(홈 시세 모드·시세 탭).
  ② 시세 탭 시장동향 지도 위에 가운데 검은 띠('10/26 기준 · 한국부동산원 · 매매·전세 · 전주 대비')가 있어, 머리 발표 줄·아래 자료
     줄과 함께 출처가 세 번 나왔고 홈의 옅은 기준 줄과 모양이 달랐다. 지도 아래에는 색 범례가 없었다.
  ③ TOP 10 의 마지막 열 머리 '전주 대비'가 옆 값 열과 같은 말인데 실제로는 순위 변화였고, 화살표가 시세 빨강·파랑이라 하락 표의
     '▲1위'(더 내린 쪽으로 오름)가 상승처럼 읽혔다.
  ④ 같은 낱말 '적음·보통·많음'에 홈 신호등은 빨강·노랑·초록, 시세 탭 입주물량 그래프·범례는 빨강·회색·파랑이었다.
  ⑤ 1280px 에서 시세 탭 상단 탭만 가운데 정렬이고, 홈 '최근 리포트' 묶음은 620px 가운데라 위 카드·지도 단과 왼쪽 끝이 어긋났으며
     375px 에서는 좌우 여백 0 으로 화면 끝에 붙었다. 주간 구역 링크 둘은 아래 큰 단추(400px) 밖으로 벌어졌다.
  ⑥ 375px 시세 카드에서 '매매 전주 대비'가 감춰져 '+0.07%'가 매매인지 전세인지 알 수 없었다.

변이(각각 실제로 넣어 빨간 것을 확인): scrollCue 의 cue-r 판정을 뒤집으면 흐림 단정이, mapDateChip 에 검은 띠(<div><span>)를
되살리면 기준 줄 단정이, rankTables 의 열 머리를 unit 으로 되돌리면 순위 변화 단정이, .rk-up 을 #c0392b 로 되돌리면 무채색
단정이, OCC_COL 을 옛 #3a7bd5 로 되돌리면 팔레트 단정이, .smode 넓은 화면 규칙을 지우면 정렬 단정이, .crecent 를 620px·좌우 0
으로 되돌리면 정렬 단정이, .agg-wk .agg-p 규칙을 지우면 카드 단정이 빨개진다.
픽스처: 저장소 home-app.js·home-stats.js(home_src)·app.css·index.html 원문과, 폭·스크롤 값을 넣은 가짜 상자(node).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _css():
    return io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()


def _rule(css, sel):
    m = re.search(r'(?:^|[}\s])' + re.escape(sel) + r'\{([^}]*)\}', css)
    assert m, '%s 규칙을 찾지 못했다' % sel
    return m.group(1)


def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, '%s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8'))


def test_scroll_cue_marks_the_side_with_more_to_scroll():
    fn = _js_func(HS.home_source(), 'scrollCue')
    js = fn + r'''
function mk(sw,cw,sl){
  var cls={cue:1};
  var w={classList:{contains:function(c){return !!cls[c];},toggle:function(c,on){if(on)cls[c]=1;else delete cls[c];}}};
  var box={parentNode:w,scrollWidth:sw,clientWidth:cw,scrollLeft:sl,addEventListener:function(){}};
  return [box,cls];
}
var out=[];
[[600,320,0],[600,320,280],[600,320,140],[300,320,0],[600,0,0]].forEach(function(a){
  var b=mk(a[0],a[1],a[2]); scrollCue(b[0]); out.push(Object.keys(b[1]).sort().join(' '));
});
process.stdout.write(JSON.stringify(out));
'''
    got = _node(js)
    # 처음(오른쪽만) · 끝(왼쪽만) · 가운데(둘 다) · 안 넘침(없음) · 숨은 상자(판정 안 함)
    assert got == ['cue cue-r', 'cue cue-l', 'cue cue-l cue-r', 'cue', 'cue'], got
    css = _css()
    assert 'opacity:1' in _rule(css, '.cue.cue-l::before,.cue.cue-r::after')
    stats = HS.home_source()
    assert '<div class="cue"><div class="map-scroll">' in _js_func(stats, 'drawNationMap'), '시세 탭 지도 상자에 흐림 덮개가 없다'
    assert 'scrollCue(box)' in _js_func(stats, 'syncSwipe'), '보일 때(syncSwipe) 흐림을 다시 재지 않는다'


def test_stats_map_has_a_light_basis_line_and_a_legend_under_the_map():
    src = HS.home_source()
    chip = _js_func(src, 'mapDateChip')
    assert "'<p class=\"map-datechip\">'" in chip and '<span>' not in chip, chip
    assert "' 기준 · 한국부동산원</p>'" in chip, '기준 줄이 홈 #tb-when 과 같은 \'시점 기준 · 출처\' 양식이 아니다'
    rule = _rule(_css(), '.map-datechip')
    assert 'background' not in rule and 'text-align:left' in rule, rule
    draw = _js_func(src, 'drawNationMap')
    leg = draw[draw.index('map-suplegend'):]
    assert 'tb-key wg-key' in leg and '하락' in leg and '상승' in leg and leg.index('하락') < leg.index('상승'), \
        '지도 아래 범례가 없거나 왼쪽 하락 → 오른쪽 상승이 아니다'


def test_rank_change_column_is_named_and_neutral():
    src = HS.home_source()
    tbl = _js_func(src, 'rankTables')
    assert "<th>순위 변화</th>" in tbl and "'<th>'+unit+'</th>'" not in tbl
    css = _css()
    for sel in ('.rk-up', '.rk-dn'):
        body = _rule(css, sel)
        assert 'color:var(--ink2)' in body and '#c0392b' not in body and '#1a5276' not in body, (sel, body)


def test_occupancy_colors_are_the_traffic_light_colors():
    css = _css()
    light = {k: re.search(r'\.zl-d\.%s\{background:(#[0-9a-f]{6})\}' % k, css).group(1) for k in ('lo', 'ok', 'hi')}
    src = HS.home_source()
    occ = re.search(r"const OCC_COL=\{lo:'(#[0-9a-f]{6})',hi:'(#[0-9a-f]{6})','':'(#[0-9a-f]{6})'\};", src)
    assert occ and occ.groups() == (light['lo'], light['hi'], light['ok']), (occ and occ.groups(), light)
    idx = dict(HS.home_files())[HS.HOME]
    leg = re.search(r'<div class="adv-legend">(<span><i style="background:#[0-9a-f]{6}"></i>적음.*?)</div>', idx).group(1)
    got = re.findall(r'background:(#[0-9a-f]{6})"></i>(적음|보통|많음)', leg)
    assert got == [(light['lo'], '적음'), (light['ok'], '보통'), (light['hi'], '많음')], got


def test_columns_line_up_and_price_cards_keep_their_series():
    css = _css()
    smode = re.search(r'@media\(min-width:600px\)\{\.smode\{([^}]*)\}', css)
    assert smode and 'justify-content:flex-start' in smode.group(1) and 'var(--col-wide)' in smode.group(1), \
        '넓은 화면 시세 탭 상단 탭이 아래 하위 탭·제목과 같은 왼쪽 끝이 아니다'
    rec = _rule(css, '.crecent')
    assert 'max-width:var(--col-wide)' in rec and 'padding:4px 24px 18px' in rec, rec
    assert _rule(css, '.wgrid').startswith('max-width:400px'), '주간 구역 링크 줄이 아래 큰 단추(400px) 폭이 아니다'
    assert re.search(r'\.agg-wk \.agg-p\{position:static', css), "375px 시세 카드가 '매매 전주 대비'를 감춘다"
    assert "class=\"agg-c agg-wk\"" in _js_func(HS.home_source(), 'wkAggCard')
