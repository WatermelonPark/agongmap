# -*- coding: utf-8 -*-
"""전국 시군구 지도 — 홈 sggMapSvg(home-app.js)와 /weekly/ 머리 지도(make_weekly_page.sgg_map_svg)가 같은 마크업을 굽는지,
지도 칸·TOP 10 지역명이 여는 그래프의 지역(home-stats.js trendTarget)이 맞는지 본다.

재현하는 상태(2026-10-02 대표 요청): 홈 주간 구역과 /weekly/ 머리의 시도 타일을 걷고 그 자리에 통계 탭과 같은 시군구 지도를
둔다. 칸(이름·값)을 누르면 홈 통계 시장동향의 그 지역 주간 그래프가 열린다(새 화면을 만들지 않는다). 지도는 홈(브라우저 JS)과
/weekly/(배치가 굽는 HTML) 두 곳에서 그려지므로, 같은 칸이 두 화면에서 다른 색·다른 끝자리로 보이지 않게 한 글자까지 대조한다
(같은 대상을 재는 코드는 같은 상수, 그 일치는 시험으로 — CLAUDE.md).

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - make_weekly_page._to_fixed3 를 '%.3f'(짝수 쪽 반올림)로 바꾸면 합성 픽스처의 한가운데 알파(0.3125·0.4375)에서 빨개진다.
  - 파이썬 tb 를 round(VH / 2) + 3(짝수 쪽 — 13/2=6.5 → 6)으로 바꾸면 값 글자 y 가 하나 어긋나 빨개진다.
  - sggMapSvg 의 3단 VH(12)를 13 으로 바꾸면 월간 합성 픽스처에서 빨개진다(파이썬은 12).
  - trendTarget 이 sggZoneOf 대신 sidoOf 를 쓰면 광주 칸(b3·b304)이 판정 단위(전남광주)에 못 닿아 빨개진다.
  - trendTarget 이 시군구 목록(sggOfSido) 확인을 빼면 값 없는 머리 칸(천안 c301)이 빈 시군구 그래프를 열어 빨개진다.
픽스처: ① 저장소 data.js 의 주간 시군구 최신 한 주(실데이터 — 값은 두 구현의 일치로만 본다, 날짜·값을 박지 않는다),
        ② 합성 3단(매매·전세·월세) 값 — 결측·0.00 으로 반올림되는 작은 음수·만색 기준을 넘는 값·알파가 정확히 한가운데(0.3125)인 값,
        ③ 판정 단위 목록에 '전남광주'가 있고 광주·전남 시군구 코드를 가진 합성 W.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_weekly_page as MW  # noqa: E402


def _func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, '홈 소스에서 %s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _node(js):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


def _js_map(vals, names, ref, href):
    """홈 sggMapSvg 를 실제 홈 함수(mapColor·pv2·pvSign)와 함께 node 로 돌린다. href: 코드 앞에 붙일 주소 또는 None."""
    h = HS.home_source()
    pre = [re.search(r'^const NATION_TILE=.*$', h, re.M).group(0)] + [_func(h, n) for n in ('pv2r', 'pv2', 'pvSign', 'mapColor', 'sggMapSvg')]
    return _node('\n'.join(pre + [
        'const vals=%s;' % json.dumps(vals),
        'const o={ref:%s,names:%s%s};' % (json.dumps(ref), json.dumps(names, ensure_ascii=False),
                                          (',href:c=>%s+c' % json.dumps(href)) if href else ''),
        'process.stdout.write(JSON.stringify(sggMapSvg(vals,o)));']))


def test_weekly_head_map_is_the_home_map():
    """/weekly/ 머리 지도 = 홈 주간 구역 지도(같은 값·같은 만색 기준 WK_MAP_REF·같은 링크 모양) — 주소 앞의 '/' 만 다르다."""
    W, _ = MW.load()
    py, _p = MW.week_map(W)
    S = W['sgg']
    row = S['rows'][-1]
    v = {c: row['ma'][i] for i, c in enumerate(S['codes']) if i < len(row['ma'])}
    ref = float(re.search(r'^var WK_MAP_REF=([\d.]+);', HS.home_source(), re.M).group(1))
    js = _js_map([v], ['매매'], ref, '/#stats-market-week~')
    same = py == js   # 긴 한 줄 문자열이라 pytest 의 == 차이 풀이(difflib)가 몇 분 걸린다 — 첫 차이만 적는다
    assert same, _first_diff(py, js)
    assert py.count('<a href="/#stats-market-week~') == len(MW.nation_tile()['t'])


def test_tile_names_are_unique_for_screen_readers():
    """칸 설명(aria-label)의 이름 부분이 모든 칸에서 다르다 — 짧은 이름('북'·'중'·'강서'·'광주')이 여러 시도에 겹쳐 보조기기에서
    같은 소리로 읽히지 않게 구는 소속 시, 그 밖은 소속 시도를 앞에 붙인다(2026-10-03 리뷰 지적).
    변이(실제로 확인): 앞말(pre)을 빈 문자열로 두면 '북'·'중' 등이 겹쳐 빨개진다. 픽스처: 실제 NATION_TILE 배치."""
    codes = [t[0] for t in MW.nation_tile()['t']]
    svg = MW.sgg_map_svg([{c: 0.01 for c in codes}], ['매매'], 0.4, href=lambda c: '#' + c)
    names = [re.sub(r' 매매 .*', '', x) for x in re.findall(r'data-code="[^"]+" aria-label="([^"]+)"', svg)]
    assert len(names) == len(codes)
    dup = sorted({n for n in names if names.count(n) > 1})
    assert not dup, '보조기기에서 겹쳐 읽히는 칸 이름: %s' % dup


def test_three_row_map_and_rounding_edges_match():
    """3단(월간 모양)·링크 없는 지도(풍선 도움말 <title>)와 반올림 가장자리도 같다."""
    codes = [t[0] for t in MW.nation_tile()['t']]
    ma, je, wo = {}, {}, {}
    # 0.0958…·-0.1652… 는 만색 기준 0.4 에서 알파가 정확히 0.3125·0.4375(셋째 자리 뒤가 딱 5 — 두 배수 한가운데)가 되는 값
    edge = [None, -0.001, 0.004, -0.005, 0.005, 1.7, -2.4, 0.09583333333333333, -0.16527777777777777, 0.0]
    for i, c in enumerate(codes):
        ma[c] = edge[i % len(edge)]
        je[c] = ((i * 37) % 120 - 60) / 100.0
        wo[c] = None if i % 7 == 0 else ((i * 11) % 50 - 25) / 1000.0
    names = ['매매', '전세', '월세']
    for ref in (0.4, 1.0):
        py = MW.sgg_map_svg([ma, je, wo], names, ref)
        js = _js_map([ma, je, wo], names, ref, None)
        same = py == js
        assert same, (ref, _first_diff(py, js))
        assert '<title>' in py and '<a ' not in py
    # 알파가 정확히 한가운데인 칸이 실제로 있어야 toFixed 반올림 방향(큰 쪽)을 가린다 — 없으면 이 픽스처가 그 변이를 못 잡는다
    assert 'rgba(224,86,74,0.313)' in MW.sgg_map_svg([ma], ['매매'], 0.4) and 0.14 + 0.72 * (0.09583333333333333 / 0.4) == 0.3125


def _first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return '첫 차이 %d: 파이썬 …%s… / 홈 …%s…' % (i, a[max(0, i - 80):i + 40], b[max(0, i - 80):i + 40])
    return '길이 다름 %d / %d' % (len(a), len(b))


def test_tile_codes_fit_the_region_hash():
    """지도의 모든 칸 코드가 홈 applyHash 의 '~코드' 모양([a-c] + 숫자 1~8자리)에 든다 — 안 들면 그 칸을 눌러도 통계가 안 열린다.
    변이: applyHash 정규식의 코드 자리를 {1,6} 으로 좁히면 8자리 서울 구 코드에서 빨개진다."""
    h = HS.home_source()
    pat = re.search(r"\(\?:~\((\[a-c\]\[0-9\]\{\d+,\d+\})\)\)\?\$/\);", h)
    assert pat, 'applyHash 의 ~코드 자리를 찾지 못했다'
    rx = re.compile('^' + pat.group(1) + '$')
    bad = [t[0] for t in MW.nation_tile()['t'] if not rx.match(t[0])]
    assert not bad, bad


def test_tile_opens_the_right_region():
    """칸·지역명 → 그래프 지역(trendTarget): 전국 칸은 전체, 시도 머리 칸은 그 시도(광주·전남은 판정 단위 전남광주), 시군구 칸은 그
    시군구, 시군구 목록에 없는 칸(값 없는 구를 가진 시의 머리 칸·모르는 코드)은 그 시도."""
    h = HS.home_source()
    js = '\n'.join([re.search(r'^const SGG_QNAME=.*$', h, re.M).group(0),
                    re.search(r'^const SIDO_PREFIX=\{.*?\};', h, re.M | re.S).group(0)]
                   + [_func(h, n) for n in ('sidoOf', 'sggZoneOf', 'sggOfSido', 'trendTarget')] + [
        'const codes=["a0","a7","a7020202","b3","b304","c5","c503","c3","c302","c301","b6"];',
        'const W={regions:["전국","수도권","지방","서울","전남광주","충남","세종"],',
        ' sgg:{codes:codes,rows:[{ma:codes.map((c,i)=>c==="c301"?null:0.01*i),je:codes.map(()=>null)}]}};',
        'process.stdout.write(JSON.stringify(Object.fromEntries(codes.concat(["c999"]).map(c=>[c,trendTarget(W,c)]))));'])
    got = _node(js)
    want = {'a0': ('', ''), 'a7': ('서울', ''), 'a7020202': ('서울', 'a7020202'), 'b3': ('전남광주', ''),
            'b304': ('전남광주', 'b304'), 'c5': ('전남광주', ''), 'c503': ('전남광주', 'c503'), 'c3': ('충남', ''),
            'c302': ('충남', 'c302'), 'c301': ('충남', ''), 'b6': ('세종', ''), 'c999': ('', '')}
    assert {k: (v['zone'], v['sgg']) for k, v in got.items()} == want, got


def test_every_map_and_rank_link_is_wired_to_the_graph():
    """지도 칸·TOP 10 지역명의 링크가 그래프로 이어지는 길이 끊기지 않았는지 — 링크 모양(sggMapSvg data-code·rankTables rk-go),
    누름 처리(onTrendLink — 같은 주소를 다시 누를 때), 대기열 입구(PARTS.stats.api 의 openTrendRegion)가 함께 있어야 한다.
    변이(각각 실제로 확인): PARTS 에서 openTrendRegion 을 빼면, rankTables 의 지역명 링크를 옛 맨 글자로 되돌리면, 홈 주간 구역이
    onTrendLink 를 붙이지 않으면 빨개진다."""
    h = HS.home_source()
    assert re.search(r"stats:\{src:'/home-stats\.js',api:\[[^\]]*'openTrendRegion'", h), 'PARTS.stats.api 에 openTrendRegion 이 없다'
    assert '<a class="rk-go" href="#stats-market-\'+k+\'~\'+c+\'" data-code="\'+c+\'">' in _func(h, 'rankTables')
    assert "onTrendLink(e,'home_map')" in _func(h, 'renderWeeklyGrid')
    assert "onTrendLink(e," in _func(h, 'drawNationMap')
    assert 'openTrendRegion(m[1],m[2])' in _func(h, 'onTrendLink')
