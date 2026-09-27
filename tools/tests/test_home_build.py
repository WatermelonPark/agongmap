# -*- coding: utf-8 -*-
"""홈 판 표식 — 새 HTML 과 옛 스크립트가 섞이면 한 번만 새로고침한다(홈 마케팅 검수 C11·MOB-9, 2026-09-27).

서비스워커는 HTML 과 home-app.js 를 따로 network-first(3.5초 한도)로 받는다. 재현: 서비스워커를 설치한 재방문자에게
'배포'(두 파일 모두 바뀜)를 흉내 내고 home-app.js 응답만 5초 늦추자(Chromium, 로컬 서버) 새 HTML 위에서 옛 스크립트가
돌았다. 2초로 늦추면 섞이지 않았다. 조치: index.html 의 <html data-build> 와 home-app.js 의 HOME_BUILD 를 견줘 다르면
한 번 새로고침한다. 판 값은 sw.js 의 VERSION 과 같다 — VERSION 을 올릴 때 셋을 같이 올린다.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _builds():
    sw = re.search(r"const VERSION = '([^']+)'", io.open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read())
    home = HS.home_source()   # index.html 마크업 + home-app.js
    html = re.search(r'<html\b[^>]*\bdata-build="([^"]*)"', home)
    js = re.search(r"const HOME_BUILD='([^']*)';", home)
    assert sw and html and js, '판 표식을 못 읽었다(sw %s · html %s · js %s) — 모양이 바뀌었으면 이 시험도 고칠 것' % (
        bool(sw), bool(html), bool(js))
    return sw.group(1), html.group(1), js.group(1)


def test_build_marker_is_the_same_in_html_script_and_sw():
    """index.html data-build = home-app.js HOME_BUILD = sw.js VERSION.

    둘(HTML·스크립트)이 다르면 모든 방문자가 매번(세션마다 한 번) 새로고침한다. sw.js VERSION 과 같게 둔 까닭: 배포마다
    VERSION 을 올리는 습관이 이미 있고(test_sw_version 이 단조 증가를 본다) 판 이름이 하나면 제보를 읽기 쉽다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): sw.js VERSION 만 올리거나, index.html data-build 만, home-app.js
    HOME_BUILD 만 바꾸면 빨개진다. 픽스처: 저장소의 세 파일 그대로.
    """
    sw, html, js = _builds()
    assert html == js == sw, (
        '판 표식이 갈렸다: sw.js VERSION %s · index.html data-build %s · home-app.js HOME_BUILD %s — '
        'VERSION 을 올렸으면 나머지 둘도 같은 값으로 바꿀 것' % (sw, html, js))


HARNESS = r"""
const SRC = %(snip)s, JB = %(jb)s, NEW = JB + 'next';
function load(htmlBuild, store, scriptBuild) {
  const events = []; let reloads = 0;
  const document = { documentElement: { getAttribute: (k) => (k === 'data-build' ? htmlBuild : null) } };
  const sessionStorage = store === null
    ? { getItem() { throw new Error('denied'); }, setItem() { throw new Error('denied'); } }   // 사생활 보호 모드 등
    : { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { store.set(k, String(v)); } };
  const location = { reload() { reloads++; } };
  const track = (ev, p) => events.push([ev, p]);
  const code = scriptBuild ? SRC.split("'" + JB + "'").join("'" + scriptBuild + "'") : SRC;
  const flag = new Function('document', 'sessionStorage', 'location', 'track', code + '\nreturn BUILD_RELOAD;')(
    document, sessionStorage, location, track);
  return { reloads, flag, events };
}
const seq = (n, htmlBuild, store) => Array.from({ length: n }, () => load(htmlBuild, store));
const out = {};
out.same = load(JB, new Map());
// 배포 직후 느린 망: 새 HTML(NEW) + 옛 스크립트(JB). 새로고침 뒤 새 스크립트가 오면 맞는다.
let st = new Map();
out.mixFirst = load(NEW, st);
out.mixFixed = load(NEW, st, NEW);
// 새로고침해도 계속 옛 스크립트가 오는 망: 다섯 번 들어와도 새로고침은 한 번뿐이어야 한다.
out.stuck = seq(5, NEW, new Map());
// 반대 조합(옛 HTML 캐시 + 새 스크립트)도 한 번 새로고침한다.
out.reverse = load('v0', new Map());
out.noStorage = load(NEW, null);
// 판 표식이 없는 HTML(표식 이전 판)은 비교하지 않는다 — 이 세션에 앞선 새로고침 기록이 남아 있어도.
st = new Map(); load(NEW, st);
out.noMarker = load(null, st);
process.stdout.write(JSON.stringify(out));
"""


def _run():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    src = HS.home_source()
    m = re.search(r"const HOME_BUILD='([^']*)';\s*let BUILD_RELOAD=false;\s*\(function\(\)\{.*?\n\}\)\(\);", src, re.S)
    assert m, 'home-app.js 에서 판 비교 코드를 못 찾았다 — 모양이 바뀌었으면 이 시험도 고칠 것'
    js = HARNESS % {'snip': json.dumps(m.group(0)), 'jb': json.dumps(m.group(1))}
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


def test_mismatch_reloads_exactly_once_and_measures_the_result():
    """판 비교 코드를 node 로 그대로 돌려 새로고침 횟수와 GA 이벤트를 센다.

    재현하는 실제 상태: 배포 직후 느린 망에서 새 HTML + 옛 스크립트(재현 조건), 새로고침해도 계속 옛 스크립트가 오는
    망(무한 새로고침 위험), 옛 HTML 캐시 + 새 스크립트, sessionStorage 를 못 쓰는 브라우저, 표식 이전 HTML.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 같은 판 재방문 가드(`||seen===html`)를 빼면 stuck 이 다섯 번
    새로고침해 빨개지고, 새로고침 앞의 sessionStorage.setItem 을 빼면 결과 이벤트가 사라져(mixFixed), `!html||` 를
    빼면 noMarker 가, `html===HOME_BUILD||` 를 빼면(판이 같아도 비교) same 이 빨개진다.
    """
    o = _run()
    assert o['same']['reloads'] == 0 and not o['same']['flag'], '판이 같은데 새로고침했다: %s' % o['same']
    assert o['mixFirst']['reloads'] == 1 and o['mixFirst']['flag'], '새 HTML + 옛 스크립트인데 새로고침하지 않았다'
    fx = o['mixFixed']
    assert fx['reloads'] == 0, '새로고침 뒤 판이 맞았는데 또 새로고침했다: %s' % fx
    assert [e[0] for e in fx['events']] == ['build_reload'] and fx['events'][0][1]['fixed'] is True, fx['events']
    stuck = o['stuck']
    assert sum(r['reloads'] for r in stuck) == 1, '판이 계속 어긋나는 망에서 새로고침이 한 번이 아니다: %s' % [
        r['reloads'] for r in stuck]
    evs = [e for r in stuck for e in r['events']]
    assert len(evs) == 1 and evs[0][1]['fixed'] is False, '결과 이벤트는 새로고침 뒤 한 번만 가야 한다: %s' % evs
    assert o['reverse']['reloads'] == 1, '옛 HTML + 새 스크립트도 한 번 새로고침해야 한다'
    assert o['noStorage']['reloads'] == 0, 'sessionStorage 를 못 쓰면 새로고침하지 않아야 한다(횟수를 셀 수 없다)'
    assert o['noMarker']['reloads'] == 0, '판 표식이 없는 HTML 에서 새로고침했다'


def test_boot_stops_while_reloading():
    """새로고침하는 동안 옛 스크립트가 새 마크업을 그리지 않게 boot() 첫 줄에서 멈추는지 본다.

    무엇을 깨뜨리면 빨개지나: boot() 의 `if(BUILD_RELOAD)return;` 줄을 지우면 빨개진다(실제로 확인).
    판 비교가 부르는 track 은 함수 선언이어야 맨 위에서 부를 수 있다(const 로 바꾸면 TDZ 오류를 try 가 삼켜 측정이
    조용히 사라진다) — 그것도 같이 본다. 픽스처: 저장소 home-app.js(home_source).
    """
    src = HS.home_source()
    assert re.search(r'function boot\(\)\{\s*if\(BUILD_RELOAD\)return;', src), 'boot() 가 새로고침 중에도 화면을 그린다'
    assert re.search(r'^function track\(', src, re.M), 'track 이 함수 선언이 아니다 — 맨 위 판 비교에서 부를 수 없다'
