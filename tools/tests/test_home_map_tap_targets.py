# -*- coding: utf-8 -*-
"""홈 지도의 광역시·세종 탭 표적이 서로 겹치지 않는다(A8·MOB-6, 2026-09-27 홈 마케팅 검수).

실제 상태(픽스처가 재현하는 것): 광역시·세종 8곳은 도형이 작아 투명 원(r=22)을 덧대 탭 표적을 넓혔다. 그런데
세종·대전(중심 거리 25.7), 서울·인천(27.5), 부산·울산(39.9)은 반지름 합 44보다 가까워 원이 겹쳤고, 나중에 그린
원이 위에 놓여 세종 원의 30%·인천 원의 25%·인천 라벨의 29%가 대전·서울 리포트로 열렸다(375px 브라우저 실측,
원·라벨 안을 격자로 눌러 본 결과). 픽스처는 저장소의 실제 sido-geo.js 좌표와 판정 단위 전부다.

고친 방식: 원을 그대로 두고 가까운 작은 지역 쪽만 두 중심의 수직이등분선 안쪽에서 잘라 낸 다각형을 표적으로
쓴다. 원을 통째로 줄이는 안은 겹침은 풀지만 라벨 가장자리가 옆 도로 새고(세종 라벨 45점 중 5점이 충남·충북),
라벨 중심 둘레 σ=7px 탭 모형에서 세종 61%·대전 62%로 옛 원(76%·94%)보다 나빴다. 자르는 안은 세종 88%·대전 83%,
인천 71%→82%(375px 실측) — 그래서 아래 세 번째 시험이 '필요 이상으로 줄이지 않았는지'를 따로 본다.

방법: 홈 지도 루프(home-app.js renderSidoMap 의 `var SMALL=` 부터 SVG 를 닫기 전까지, tools/home_src 로 읽는다)를
node 로 실제로 돌려 나온 표적(<polygon> 또는 옛 모양 <circle>)의 좌표로 잰다 — 자르는 식을 시험에 다시 쓰면
코드가 틀려도 시험이 같이 틀린다. 겹침은 볼록 다각형 분리축 판정(SAT)으로, 원은 바깥에 접하는 64각형으로 본다.
CI 에서는 건너뜀도 실패다(conftest).

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인했다):
  - 표적을 옛 `<circle cx cy r="22">` 로 되돌리면 → 겹침 시험(세종·대전, 서울·인천, 부산·울산)
  - tapShape 의 반평면 자르기(SIDO_GEO.p.forEach 블록)를 지우면 → 겹침 시험
  - TAP_GAP 을 음수로(이등분선 너머까지) 두면 → 겹침 시험
  - 원을 통째로 줄이는 안(r=min(22, 이웃 거리/2−1))으로 바꾸면 → '필요 이상으로 줄이지 않는다' 시험
  - 표적을 그리는 조건에서 한 곳을 빼면(예: `SMALL[a.n]&&a.n!=='세종'`) → 표적 목록 시험
"""
import io
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402
import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _loop_src():
    s = HS.home_source()
    a = s.find('var SMALL=')
    b = s.find("h+='</svg></div>';", a)
    assert a >= 0 and b > a, '홈 지도 루프를 찾지 못했다 — 구조가 바뀌었으면 이 시험도 고칠 것'
    return s[a:b]


def _small_names():
    m = re.search(r"var SMALL=\{([^}]*)\}", _loop_src())
    assert m, 'SMALL(표적을 덧대는 작은 지역) 목록을 찾지 못했다'
    return re.findall(r"'([^']+)'\s*:", m.group(1))


def _tap_r():
    m = re.search(r'\bTAP_R=(\d+(?:\.\d+)?)', _loop_src())
    assert m, 'TAP_R(표적 원의 반지름)을 찾지 못했다'
    return float(m.group(1))


def _geo():
    s = io.open(os.path.join(ROOT, 'sido-geo.js'), encoding='utf-8').read()
    return json.loads(re.search(r'SIDO_GEO\s*=\s*(\{.*\})\s*;?\s*$', s, re.S).group(1))


def _circle_poly(cx, cy, r, n=64):
    """원을 바깥에 접하는 n각형으로 — 겹침을 놓치지 않는 쪽(보수적)으로 근사한다."""
    R = r / math.cos(math.pi / n)
    return [(cx + R * math.cos(2 * math.pi * k / n), cy + R * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _targets():
    """지도 루프를 node 로 돌려 작은 지역마다 표적 다각형을 돌려준다. {이름: (앵커 x, y, [(x, y), …])}"""
    if not shutil.which('node'):
        pytest.skip('node 없음')
    zones = {z: {'grade': 0, 'tot': 0, 'ratio': 0} for z in SZ.ORDER}
    js = ('var ADV={sido:{L:""}},Z=%s,SIDO_GEO=%s,TB_GRADE={},h="";'
          'function tbSigned(v){return String(v)}function mapFill(){return "#ccc"}function supplyFill(){return "#ccc"}'
          # 지도 모드(C3): M 은 주간 모드 재료(null = 공급 모드). 주간 모드에서도 같은 표적·라벨인지는 test_home_map_mode 가 본다.
          'var M=null;function wkFill(){return "#ccc"}function wkPct(){return ""}function mapKeyHtml(){return ""}'
          'function mapAria(){return ""}\n%s\n'
          'var out=[],m,names=SIDO_GEO.p.map(function(a){return a.n}),i=0,'
          're2=/<a href="[^"]*"[^>]*><path[^>]*><\\/path>(<(?:circle|polygon)[^>]*>)?/g;'
          'while((m=re2.exec(h))){if(m[1])out.push({n:names[i],el:m[1]});i++;}'
          'process.stdout.write(JSON.stringify({out:out,count:i}));'
          % (json.dumps(zones, ensure_ascii=False), json.dumps(_geo(), ensure_ascii=False), _loop_src()))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    got = json.loads(p.stdout.decode('utf-8'))
    geo = _geo()['p']
    assert got['count'] == len(geo), '지도 도형 수가 SIDO_GEO 와 다르다 — 순서 대응이 깨졌다'
    geo = {a['n']: a for a in geo}
    res = {}
    for t in got['out']:
        a = geo[t['n']]
        c = re.search(r'cx="([^"]*)" cy="([^"]*)" r="([^"]*)"', t['el'])
        if c:
            poly = _circle_poly(float(c.group(1)), float(c.group(2)), float(c.group(3)))
        else:
            pts = re.search(r'points="([^"]*)"', t['el'])
            assert pts, '표적 모양을 읽지 못했다: %s' % t['el'][:80]
            poly = [tuple(float(v) for v in xy.split(',')) for xy in pts.group(1).split()]
        res[t['n']] = (a['x'], a['y'], poly)
    return res


def _axes(poly):
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        nx, ny = y2 - y1, x1 - x2
        L = math.hypot(nx, ny)
        if L > 1e-9:
            yield nx / L, ny / L


def _gap(pa, pb):
    """볼록 다각형 둘의 분리축 간격(양수면 떨어져 있다, 0 이하면 겹치거나 닿는다)."""
    best = -float('inf')
    for ax, ay in itertools.chain(_axes(pa), _axes(pb)):
        a = [x * ax + y * ay for x, y in pa]
        b = [x * ax + y * ay for x, y in pb]
        best = max(best, min(b) - max(a), min(a) - max(b))
    return best


def _inside(poly, x, y):
    """볼록 다각형 안(경계 포함)인가 — 변마다 같은 쪽에 있는지로 본다."""
    sgn = 0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        c = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if abs(c) < 1e-9:
            continue
        s = 1 if c > 0 else -1
        if sgn and s != sgn:
            return False
        sgn = s
    return True


def test_every_small_region_keeps_a_tap_target():
    got = _targets()
    geo_names = {a['n'] for a in _geo()['p']}
    want = sorted(n for n in _small_names() if n in geo_names)
    assert len(want) >= 2, '작은 지역 목록이 비었다 — 검사가 헛돈다'
    assert sorted(got) == want
    for n, (x, y, poly) in got.items():
        assert len(poly) >= 3 and _inside(poly, x, y), '%s 표적이 자기 라벨 자리를 덮지 않는다' % n


def test_small_tap_targets_do_not_overlap():
    got = _targets()
    bad = []
    for (na, (_, _, pa)), (nb, (_, _, pb)) in itertools.combinations(sorted(got.items()), 2):
        g = _gap(pa, pb)
        if g <= 0:
            bad.append('%s·%s(간격 %.2f)' % (na, nb, g))
    assert not bad, '탭 표적이 겹친다 — 겹친 쪽을 누르면 나중에 그린 이웃 리포트가 열린다: %s' % bad


def test_targets_are_cut_only_toward_close_neighbours():
    """필요한 만큼만 줄인다: 옛 원(반지름 TAP_R) 안에서 이웃 작은 지역과의 수직이등분선보다 내 쪽(여유 1.5)에 있는
    점은 전부 내 표적이어야 한다 — 겹치지 않는 가장 큰 공정한 표적(보로노이 칸 ∩ 원)을 기준으로 삼는다.

    원을 통째로 줄이면 라벨 가장자리가 옆 도로 샌다(모듈 설명의 실측) — 그 회귀를 막는다. 원 둘레의 다각형 근사
    오차(32각형이면 0.1 남짓)를 넘지 않게 반지름에서 1.5 를 뺀 원 안만 본다.
    """
    got = _targets()
    R = _tap_r()
    bad = []
    for n, (x, y, poly) in got.items():
        cut = []
        for m, (x2, y2, _) in got.items():
            d = math.hypot(x2 - x, y2 - y)
            if m != n and d < 2 * R:
                cut.append(((x2 - x) / d, (y2 - y) / d, d / 2 - 1.5))
        miss = 0
        for i in range(-int(R), int(R) + 1):
            for j in range(-int(R), int(R) + 1):
                if math.hypot(i, j) > R - 1.5:
                    continue
                if all(i * ux + j * uy <= lim for ux, uy, lim in cut) and not _inside(poly, x + i, y + j):
                    miss += 1
        if miss:
            bad.append('%s: 내 쪽인데 표적 밖인 점 %d개' % (n, miss))
    assert not bad, '탭 표적을 필요 이상으로 줄였다: %s' % bad
