# -*- coding: utf-8 -*-
"""홈 차트·카카오 SDK와 /cycle/ 차트를 필요할 때 받는지 고정한다(점검후속 개발 ⑦ 2차).

2026-09-15 고객 점검: 홈 첫 로딩에서 통계 화면에만 쓰는 차트 라이브러리(약 70KB)와 공유할 때만 쓰는
카카오 SDK(약 29KB)를 받았고, /cycle/ 는 차트 라이브러리(약 205KB)를 본문 앞에서 막으며 받았다.

지연 로딩의 흔한 결함은 '받긴 받는데 그리는 쪽이 기다리지 않아 빈 차트'와 '여러 번 불려 스크립트가
여러 개 붙음'이다. 그래서 로더 코드를 꺼내 node 로 실제로 돌린다.
"""
import io
import json
import os
import re
import shutil
import subprocess

import pytest

import sys as _hs_sys  # noqa: E402
_hs_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _read(*p):
    if HS.is_home(*p):
        return HS.home_source()
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


def test_home_does_not_load_chart_or_kakao_upfront():
    s = _read('index.html')
    assert not re.search(r'<script[^>]*src="/chart-4\.4\.1', s), '홈이 차트 라이브러리를 첫 로딩에서 받는다'
    assert not re.search(r'<script[^>]*kakaocdn', s), '홈이 카카오 SDK를 첫 로딩에서 받는다'


def test_every_chart_drawer_waits_for_the_library():
    s = _read('index.html')
    for fn in ('drawStat\\(\\)', 'drawLeadtime\\(\\)', 'drawTrendChart\\(k\\)', 'drawPermitChart\\(\\)', 'drawOccChart\\(\\)'):
        assert re.search(r'function %s\{\s*if\(needChart\(' % fn, s), '%s 가 차트 라이브러리를 기다리지 않는다' % fn
    # new Chart 는 기다리는 함수 안에서만 — 새 그리기 함수가 가드 없이 생기면 빈 차트가 된다.
    # 주인은 **줄 첫머리의** 최상위 함수로 잡는다. 그냥 마지막 'function' 을 잡으면 그리기 함수 안의
    # 도우미(areaGrad 등)를 주인으로 오인해 멀쩡한 호출을 가드 없음으로 본다(처음 짰을 때 그랬다).
    guarded = ('drawStat', 'drawLeadtime', 'mkChart')
    for m in re.finditer(r'new Chart\(', s):
        head = s[:m.start()]
        owner = re.findall(r'^function (\w+)\(', head, re.M)[-1]
        assert owner in guarded, '가드 없는 함수 %s 에서 new Chart 를 부른다' % owner
    for m in re.finditer(r'(?<!function )mkChart\(', s):   # 정의 줄 자체는 호출이 아니다
        head = s[:m.start()]
        owner = re.findall(r'^function (\w+)\(', head, re.M)[-1]
        assert owner in ('mkChart', 'drawTrendChart', 'drawPermitChart', 'drawOccChart'), (
            '가드 없는 함수 %s 에서 mkChart 를 부른다' % owner)


def test_share_functions_wait_for_kakao():
    s = _read('index.html')
    for fn in ('shareTest', 'shareResult'):
        assert re.search(r'function %s\(\)\{\s*if\(needKakao\(%s\)\)return;' % (fn, fn), s), '%s 가 카카오 SDK를 기다리지 않는다' % fn


def _loader_src():
    s = _read('index.html')
    a = s.find('function loadScript(src){')
    b = s.find('\n', s.find('function needKakao(redo)'))
    assert a >= 0 and b > a, '로더 코드를 찾지 못했다'
    return s[a:b]


HARNESS = r"""
const appended = [];
const window = {};
const document = { createElement: () => ({ remove() {} }), head: { appendChild: (el) => appended.push(el) } };
let setups = 0;
function chartSetup() { setups++; }
%(src)s
(async () => {
  const out = {};
  let redraws = 0;
  out.first = needChart(() => redraws++);
  out.second = needChart(() => redraws++);
  out.scriptsAfterTwoCalls = appended.length;
  window.Chart = {}; appended[0].onload();
  await new Promise((r) => setTimeout(r, 10));
  out.redraws = redraws; out.setups = setups;
  out.thirdWithChart = needChart(() => redraws++);
  let shared = 0;
  out.kakaoFirst = needKakao(() => shared++);
  appended[appended.length - 1].onerror();
  await new Promise((r) => setTimeout(r, 10));
  out.sharedAfterFail = shared;
  out.kakaoAfterFail = needKakao(() => shared++);
  process.stdout.write(JSON.stringify(out));
})();
"""


def test_loader_appends_once_redraws_after_load_and_shares_even_when_kakao_fails():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    p = subprocess.run(['node', '-e', HARNESS % {'src': _loader_src()}], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    o = json.loads(p.stdout.decode('utf-8'))
    assert o['first'] is True and o['second'] is True
    assert o['scriptsAfterTwoCalls'] == 1, '동시에 두 번 불리자 스크립트가 %d개 붙었다' % o['scriptsAfterTwoCalls']
    assert o['redraws'] == 2 and o['setups'] == 1, '받은 뒤 다시 그리지 않았거나 설정을 여러 번 했다: %s' % o
    assert o['thirdWithChart'] is False, '라이브러리가 있는데도 기다렸다'
    assert o['sharedAfterFail'] == 1, '카카오 SDK를 못 받으면 공유가 멈춘다'
    assert o['kakaoAfterFail'] is False, '실패한 뒤에도 매번 SDK를 다시 기다린다'


def test_cycle_loads_chart_after_the_body_with_a_timer_fallback():
    s = _read('cycle', 'index.html')
    assert not re.search(r'<script[^>]*src="/chart-4\.4\.1', s), '/cycle/ 이 차트 라이브러리를 본문 앞에서 막으며 받는다'
    assert not re.search(r'^initReport\(\);', s, re.M), '/cycle/ 이 라이브러리 없이 차트를 바로 그린다'
    assert "el.src='/chart-4.4.1.umd.js'" in s and 'setTimeout(boot' in s, (
        '/cycle/ 지연 로딩에 타이머 폴백이 없다 — 화면을 그리지 않는 창에서 차트가 영영 안 뜬다')
    top = s[s.find('<script>', s.find('const D=') - 200):s.find('function initReport(){')]
    assert 'Chart.defaults' not in top, '/cycle/ 이 라이브러리를 받기 전에 Chart.defaults 를 건드린다'
