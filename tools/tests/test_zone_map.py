# -*- coding: utf-8 -*-
"""시도 리포트 시세 구역의 잘라 낸 주간·월간 타일 지도(2026-10-10 대표 요청 — '주간·월간 타일 지도를 그 지역 부분만 잘라서').

재현하는 실제 상태: 10-09 까지 시도 리포트의 시세 구역은 시군구 주간 표뿐이었다. 이제 홈 시세 탭·/weekly/ 머리의 전국 시군구
지도를 그 지역 칸만 잘라 구역 머리에 두고, 주간·월간 두 장을 단추로 바꾼다(기본 주간). 잘라 낸 상자 안의 이웃 지역 칸은 값·링크
없이 흐리게 자리만 채운다(채우지 않으면 경기는 가운데 서울·인천 자리가 크게 비었다). 세종처럼 한 칸뿐인 곳은 지도 없이 예전 모양.
픽스처: 배치가 구운 zone/<지역>/index.html·weekly/index.html 과 data.js(ADV.weekly.sgg·ADV.monthly.sgg), 홈 NATION_TILE.
기대값은 따로 계산한다 — 소속은 홈 sidoOf 의 거울 sgg_sido 로(생성기는 sggZoneOf 거울 sgg_zone), 값 표기는 MW.pv2, 칸 크기는
/weekly/ 전국 지도의 viewBox·최대 폭에서. 지역·주·달을 박지 않는다(데이터가 앞으로 가도 초록).

변이(각각 실제로 확인):
  · zone_tile 에서 a0 거름을 빼면(수도권·경기·지방 상자에 '전국' 칸이 흐리게 낀다), 이웃 칸을 dim 에서 빼면, 한 칸 지역에도 지도를
    그리면 → 자르기 시험 빨강.
  · 월간 칸 주소를 주간 주소로 쓰면, 월세 줄을 빼면, 흐린 칸에 값을 적으면, sgg_map_svg 에 dim 을 넘기지 않으면(이웃 칸이 값·링크를
    단 채 그려진다) → 페이지 대조 시험 빨강.
  · 최대 폭을 늘 640 으로 두면 → 칸 크기 시험 빨강.
  · zone.js 전환이 묶음을 숨기지 않으면, 월간 묶음에서 hidden 을 빼면 → 전환 시험 빨강.
  · 월간 계열이 없을 때도 단추를 달면, 지도 상수를 못 읽었을 때 지도를 그리려 하면 → 물러서기 시험 빨강.
"""
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
import make_sido_pages as M  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_moves as WM  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HREF = {'week': '/#stats-market-week~%s', 'month': '/#stats-market-month~%s'}


def _page(z):
    return io.open(os.path.join(ROOT, 'zone', z, 'index.html'), encoding='utf-8').read()


def _zone_of(c):
    s = WM.sgg_sido(c)     # 홈 sidoOf 의 거울 — 광주·전남은 판정 단위 전남광주로 접는다
    return '전남광주' if s in ('광주', '전남') else s


def _in(z, c):
    if z == '전국':
        return True
    zz = _zone_of(c)
    return zz is not None and (zz == z or (z in SZ.AGG and SZ.REGION.get(zz) == z))


def _zones():
    adv, _ = M.load()
    return adv, [x['z'] for x in adv['sido']['zones']]


def _latest(S):
    row = S['rows'][-1]
    mets = ['ma', 'je'] + (['wo'] if isinstance(row.get('wo'), list) else [])
    return {c: [(row.get(m) or [None] * (i + 1))[i] if i < len(row.get(m) or []) else None for m in mets]
            for i, c in enumerate(S['codes'])}, mets


def test_crop_holds_the_zone_tiles_and_dims_the_rest_of_its_box():
    """잘라 낸 배치 = 그 지역 칸을 둘러싼 상자(왼쪽 위로 붙임). 상자 안 다른 지역 칸은 dim, '전국' 머리 칸(a0)은 전국 장에만.
    지역 칸이 하나뿐이면 None(지도 없음)."""
    N = MW.nation_tile()
    _, names = _zones()
    assert set(names) == set(SZ.ORDER)
    dims = {}
    for z in names:
        own = [t for t in N['t'] if _in(z, t[0])]
        got = M.zone_tile(N, z)
        if len(own) < 2:
            assert got is None, '%s: 칸이 %d개뿐인데 지도를 그린다' % (z, len(own))
            continue
        x0, y0 = min(t[2] for t in own), min(t[3] for t in own)
        x1, y1 = max(t[2] for t in own), max(t[3] for t in own)
        box = [t for t in N['t'] if x0 <= t[2] <= x1 and y0 <= t[3] <= y1 and (t[0] != 'a0' or z == '전국')]
        assert (got['cols'], got['rows']) == (x1 - x0 + 1, y1 - y0 + 1), z
        assert sorted(got['t']) == sorted([c, nm, x - x0, y - y0, h] for c, nm, x, y, h in box), z
        assert sorted(got['dim']) == sorted(t[0] for t in box if not _in(z, t[0])), z
        assert z == '전국' or 'a0' not in [t[0] for t in got['t']], z
        dims[z] = len(got['dim'])
    assert any(dims.values()), '상자 안 이웃 칸이 있는 지역이 하나도 없다 — 자르기 셈이 이웃을 놓친다'
    assert dims.get('전국') == 0


def test_page_maps_match_the_data():
    """구운 페이지의 지도 두 장: 링크 칸 = 그 지역 칸 가운데 머리 칸이거나 값이 있는 칸, 주소는 주기별 시세 탭 그래프, 칸 설명의
    값 = 데이터 최신 행의 발표 표기(MW.pv2), 월간은 원천에 월세가 있으면 세 줄. 흐린 칸은 링크·값 없이 이름만."""
    adv, names = _zones()
    N = MW.nation_tile()
    series = {'week': adv['weekly']['sgg'], 'month': adv['monthly']['sgg']}
    seen = 0
    for z in names:
        sec = re.search(r'<section class="zwk" id="weekly-sgg">(.*?)</section>', _page(z), re.S)
        if not sec:
            continue
        sec = sec.group(1)
        tile = M.zone_tile(N, z)
        if tile is None:
            assert '<svg' not in sec and 'zm-seg' not in sec, z
            continue
        for k, S in series.items():
            box = re.search(r'<div class="zm" data-zm="%s"[^>]*>(.*?)</svg>' % k, sec, re.S)
            assert box, '%s: %s 지도가 없다' % (z, k)
            svg = box.group(1)
            vals, mets = _latest(S)
            own = [t for t in tile['t'] if _in(z, t[0])]
            want = {c for c, _nm, _x, _y, h in own if h or any(v is not None for v in vals.get(c, []))}
            links = re.findall(r'<a href="([^"]+)" data-code="([^"]+)" aria-label="([^"]+)">', svg)
            assert {c for _, c, _ in links} == want, (z, k, sorted({c for _, c, _ in links} ^ want)[:5])
            for href, c, lab in links:
                assert href == HREF[k] % c, (z, k, href)
                got = re.findall(r'(매매|전세|월세) ([^%]+)%', H.unescape(lab))
                assert [g[0] for g in got] == ['매매', '전세', '월세'][:len(mets)], (z, k, lab)
                assert [g[1] for g in got] == [MW.pv2(v) for v in vals.get(c, [None] * len(mets))], (z, k, c, lab)
            faded = re.findall(r'<g transform="[^"]*" opacity="\.35" aria-hidden="true">(.*?)</g>', svg)
            dim_want = [t for t in tile['t'] if t[0] in tile['dim'] and (t[4] or any(v is not None for v in vals.get(t[0], [])))]
            assert len(faded) == len(dim_want), (z, k, len(faded), len(dim_want))
            for g in faded:
                assert '%' not in g and not re.search(r'>[+-]?\d+\.\d\d<', g), (z, k, g[:120])
            seen += 1
    assert seen, '지도가 실린 장이 하나도 없다'


def test_crop_max_width_keeps_the_national_tile_size():
    """잘라 낸 지도의 최대 폭은 칸 크기가 /weekly/ 전국 지도와 같게 줄인다 — 작은 시도(제주 3칸 등)가 넓은 화면에서 칸이 몇 배로
    부풀지 않게. 전국과 폭이 같은 상자(전국·수도권·경기·지방)는 전국 지도와 같은 최대 폭."""
    w = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
    nw, nmax = map(int, re.search(r'<svg viewBox="-2 -2 (\d+) \d+"[^>]*max-width:(\d+)px', w).groups())
    _, names = _zones()
    checked = 0
    for z in names:
        for vw, mx in re.findall(r'<svg viewBox="-2 -2 ([\d.]+) [\d.]+"[^>]*max-width:(\d+)px', _page(z)):
            assert abs(int(mx) - float(vw) * nmax / nw) <= 0.5, (z, vw, mx)
            checked += 1
    assert checked


def _dom_harness(js):
    """zone.js 를 합성 DOM 에 올린다 — 단추 둘(주간 눌림), 묶음 둘(월간 hidden), 지도 상자 둘과 그 아래 '옆으로 밀어' 안내."""
    return r'''
var reg={}, win={};
function El(attrs){ this.a=attrs||{}; this.hidden=!!this.a.hidden; this.cls={}; var self=this;
  (this.a.cls||'').split(' ').forEach(function(c){ if(c)self.cls[c]=1; });
  this.classList={toggle:function(c,on){ if(on)self.cls[c]=1; else delete self.cls[c]; },contains:function(c){return !!self.cls[c];}};
  this.scrollWidth=this.a.sw||0; this.clientWidth=this.a.cw||0; this.ls={}; }
El.prototype.getAttribute=function(k){ return this.a[k]===undefined?null:this.a[k]; };
El.prototype.setAttribute=function(k,v){ this.a[k]=v; };
El.prototype.addEventListener=function(t,f){ this.ls[t]=f; };
El.prototype.querySelector=function(s){ return this.kids&&this.kids[s]||null; };
var bw=new El({'data-zm':'week',cls:'on','aria-pressed':'true'}), bm=new El({'data-zm':'month','aria-pressed':'false'});
var hw=new El({hidden:true}), hm=new El({hidden:true});
var cw=new El({}), cm=new El({}); cw.kids={'.zm-swipe':hw}; cm.kids={'.zm-swipe':hm};
var sw=new El({sw:300,cw:320}), sm=new El({sw:0,cw:0}); sw.nextElementSibling=cw; sm.nextElementSibling=cm;
var zw=new El({'data-zm':'week'}), zm=new El({'data-zm':'month',hidden:true});
var Q={'.zm-seg button[data-zm]':[bw,bm],'.zm[data-zm]':[zw,zm],'.zwk .mm-scroll':[sw,sm]};
var document={querySelectorAll:function(s){ return Q[s]||[]; },getElementById:function(){ return null; }};
var window={addEventListener:function(t,f){ win[t]=f; }};
%s
var out={start:[zw.hidden,zm.hidden,hw.hidden]};
sm.scrollWidth=472; sm.clientWidth=327;            // 월간 묶음이 보이면 넓이가 생긴다(수도권 같은 넓은 지도)
bm.ls.click();
out.month=[zw.hidden,zm.hidden,bw.getAttribute('aria-pressed'),bm.getAttribute('aria-pressed'),bw.classList.contains('on'),bm.classList.contains('on'),hm.hidden];
bw.ls.click();
out.week=[zw.hidden,zm.hidden,bw.getAttribute('aria-pressed'),bm.getAttribute('aria-pressed')];
out.resize=typeof win.resize;
process.stdout.write(JSON.stringify(out));
''' % js


def test_toggle_switches_between_week_and_month():
    """구운 장은 주간 묶음이 보이고 월간 묶음은 hidden, 단추는 주간이 눌린 채다. zone.js 는 단추를 누르면 그 주기 묶음만 보이고
    눌림 표시(aria-pressed·on)를 옮기며, 지도가 상자보다 넓을 때만 '옆으로 밀어' 안내를 켠다."""
    _, names = _zones()
    pages = 0
    for z in names:
        sec = re.search(r'<section class="zwk" id="weekly-sgg">(.*?)</section>', _page(z), re.S)
        if not sec or 'zm-seg' not in sec.group(1):
            continue
        s = sec.group(1)
        assert s.count(M.ZM_SEG) == 1, z
        assert re.search(r'<div class="zm" data-zm="week">', s) and re.search(r'<div class="zm" data-zm="month" hidden>', s), z
        pages += 1
    assert pages, '주간·월간 단추가 달린 장이 하나도 없다'
    assert 'aria-pressed="true" data-zm="week"' in M.ZM_SEG and 'aria-pressed="false" data-zm="month"' in M.ZM_SEG
    if not shutil.which('node'):
        pytest.skip('node 없음')
    p = subprocess.run(['node', '-e', _dom_harness(M.zone_js())], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    got = json.loads(p.stdout.decode('utf-8'))
    assert got['start'] == [False, True, True], got            # 주간 지도 300 < 상자 320 — 안내 없음
    assert got['month'] == [True, False, 'false', 'true', False, True, False], got   # 월간 472 > 327 — 안내를 켠다
    assert got['week'] == [False, True, 'true', 'false'], got
    assert got['resize'] == 'function'


def test_single_tile_zone_and_missing_pieces_fall_back_to_the_old_section():
    """세종(한 칸)은 지도 없이 예전 제목·표. 월간 계열이 없으면 주간 지도만 두고 단추·월간 묶음 없이 제목도 '주간'.
    지도 상수를 못 읽으면(maps=None) 지도 없는 예전 구역."""
    adv, _ = _zones()
    W, Q = MW.load()
    ctx = M.zone_map_ctx()
    assert ctx and ctx['ref']['week'] > 0 and ctx['ref']['month'] > 0
    one = [z for z in SZ.ORDER if M.zone_tile(ctx['tile'], z) is None]
    for z in one:
        sec = M.weekly_section(z, W, Q, adv['monthly'], ctx)
        if sec:
            assert 'zm-seg' not in sec and '<svg' not in sec and '<h2>%s 주간 아파트 시세</h2>' % z in sec, z
    many = [z for z in SZ.ORDER if z not in SZ.AGG and z not in one]
    z = max(many, key=lambda x: len(M.zone_tile(ctx['tile'], x)['t']))
    full = M.weekly_section(z, W, Q, adv['monthly'], ctx)
    assert '<h2>%s 시군구 주간·월간 아파트 시세</h2>' % z in full and M.ZM_SEG in full and full.count('<svg') == 2
    wk = M.weekly_section(z, W, Q, None, ctx)
    assert '<h2>%s 시군구 주간 아파트 시세</h2>' % z in wk and 'zm-seg' not in wk and 'data-zm="month"' not in wk
    assert wk.count('<svg') == 1 and 'stats-market-week~' in wk
    old = M.weekly_section(z, W, Q, adv['monthly'], None)
    assert '<svg' not in old and 'zm-seg' not in old and '<h2>%s 시군구 주간 아파트 시세</h2>' % z in old
