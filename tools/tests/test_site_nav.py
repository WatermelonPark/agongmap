# -*- coding: utf-8 -*-
"""하단 탭바 라벨이 모든 페이지에서 정본(site_nav.TABS)과 같다 — 홈 마케팅 검수 C2(HERO-7·RET-8·IA-6 2단계·MOB-3).

재현하는 실제 상태(2026-09-26 검수): 탭바는 홈·지역·통계·사이클이었고, 같은 마크업이 홈 index.html·손 페이지
(소개·FAQ·개인정보·404·퀴즈 랜딩 3종·/cycle/)·생성기 두 곳(make_sido_pages FOOT, make_indicator_pages SHELL)과
/weekly/ 뼈대에 복제되어 저장소 HTML 33개에 '<span>통계</span>'가 있었다. 탭 이름을 '시세'로 바꾸는 결정 하나가
서른 곳 넘게 흩어져 있어, 한 곳만 빠져도(예: 배치가 다시 굽지 않는 손 페이지) 아무것도 빨개지지 않았다.

이 파일의 시험은 배치·CI 처럼 생성기를 먼저 돌린 저장소에서 돈다 — 생성 페이지(zone/·weekly/·monthly/·moveins/·
jeonse-ratio/)는 새 생성기가 구운 것을 본다. 생성기를 안 돌린 로컬 작업 트리에서는 옛 산출물이 빨개질 수 있다.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_indicator_pages as I  # noqa: E402
import make_sido_pages as M  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import site_nav as N  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SKIP_DIRS = ('drafts', 'logs', 'node_modules')   # 로컬 전용·외부물. 점으로 시작하는 폴더(.git·.claude)도 건너뛴다.
NAV = re.compile(r'<nav class="bottomnav">(.*?)</nav>', re.S)
BTN = re.compile(r'<(a|button) class="nav-btn[^"]*"([^>]*)>(.*?)</\1>', re.S)
BY_HREF = {h: t for t, h in N.HREF.items()}


def _tabs(nav_inner):
    """탭바 안쪽 → [(식별자, 라벨, 켜짐)]. 홈은 <button data-view>, 나머지는 <a href> 다."""
    out = []
    for m in BTN.finditer(nav_inner):
        attrs, body = m.group(2), m.group(3)
        view = re.search(r'data-view="([^"]*)"', attrs)
        href = re.search(r'href="([^"]*)"', attrs)
        tid = view.group(1) if view else BY_HREF.get(href.group(1) if href else None, href and href.group(1))
        label = re.findall(r'<span>([^<]*)</span>', body)
        out.append((tid, label[0].strip() if len(label) == 1 else label, ' on' in m.group(0).split('>', 1)[0]))
    return out


def _html_pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in SKIP_DIRS]
        for f in files:
            if f.endswith('.html'):
                yield os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')


def test_every_page_tabbar_matches_the_canon():
    """저장소의 모든 HTML 탭바가 정본과 같은 순서·식별자·라벨이다(홈·지역·시세·사이클). 켜진 탭은 많아야 하나.

    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 손 페이지 하나(about/index.html)의 '시세' 를 '통계' 로 되돌리면,
    홈 index.html 탭바의 라벨을 되돌리면, site_nav.TABS 의 라벨을 '시세·통계' 로 바꾸면(손 페이지가 안 따라와서)
    빨개진다. 픽스처: 생성기를 돌린 뒤의 저장소 HTML 전부(모듈 독스트링).
    """
    pages, bad = [], {}
    for rel in _html_pages():
        html = io.open(os.path.join(ROOT, rel), encoding='utf-8').read()
        navs = NAV.findall(html)
        if not navs:
            continue
        pages.append(rel)
        tabs = [_tabs(n) for n in navs]
        want = [(t, l) for t, l in zip(N.IDS, N.LABELS)]
        got = [[(t, l) for t, l, _ in x] for x in tabs]
        if len(navs) != 1 or got[0] != want or sum(on for _, _, on in tabs[0]) > 1:
            bad[rel] = got
    assert 'index.html' in pages and len(pages) > 1, '탭바가 있는 페이지를 못 찾았다: %s' % pages
    assert not bad, '탭바가 정본(%s)과 다르다: %s' % (list(zip(N.IDS, N.LABELS)), bad)


def test_generators_bake_the_canonical_tabbar():
    """생성기 템플릿 자체가 정본 탭바를 굽는다 — 이미 구운 페이지가 우연히 맞는 것에 기대지 않는다.

    /weekly/ 는 페이지 파일이 곧 뼈대라, 픽스처로 옛 '통계' 라벨 뼈대(2026-09-27 1차 배포 직후 모양)를 만들어 굽는다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): make_weekly_page.put_nav 를 옛 방식(켜짐 표시만 바꾸기)으로 되돌리면,
    make_sido_pages FOOT 이나 make_indicator_pages SHELL 에 옛 손 탭바 문자열('<span>통계</span>')을 되살리면 빨개진다.
    """
    want = list(zip(N.IDS, N.LABELS))
    for name, tpl, on in (('make_indicator_pages.SHELL', I.SHELL, 'stats'), ('make_sido_pages.FOOT', M.FOOT, 'zone')):
        navs = NAV.findall(tpl)
        assert len(navs) == 1, '%s 에 탭바가 %d개' % (name, len(navs))
        tabs = _tabs(navs[0])
        assert [(t, l) for t, l, _ in tabs] == want, '%s 탭바가 정본과 다르다: %s' % (name, tabs)
        assert [t for t, _, o in tabs if o] == [on], '%s 에서 켜진 탭: %s' % (name, tabs)

    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    old = NAV.sub(lambda m: m.group(0).replace('<span>%s</span>' % N.LABEL['stats'], '<span>통계</span>'), page)
    assert '<span>통계</span>' in NAV.search(old).group(0), '픽스처가 옛 라벨 뼈대가 아니다'
    W, Q = MW.load()
    got = MW.render(old, W, Q)
    tabs = _tabs(NAV.search(got).group(1))
    assert [(t, l) for t, l, _ in tabs] == want, '/weekly/ 생성기가 옛 라벨을 남긴다: %s' % tabs
    assert "활성 탭은 '통계'" not in got, '/weekly/ CSS 주석에 옛 탭 이름이 남았다'


NAV_BTN_RULE = re.compile(r'(?:^|[}\s])\.nav-btn\{([^}]*)\}')


def _label_sizes(css):
    """CSS 안 `.nav-btn{…}` 규칙들의 font-size(px). 주석은 벗긴다."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    return [float(m.group(1)) for r in NAV_BTN_RULE.findall(css) for m in [re.search(r'font-size:\s*([\d.]+)px', r)] if m]


def test_every_tabbar_label_is_the_canonical_size():
    """탭 라벨 글자가 모든 페이지에서 정본 크기(site_nav.LABEL_PX = 13px — 홈 화면 글자 하한, 2026-09-28 대표 결정)다.
    탭바는 모든 페이지 공용이라 app.css 를 읽는 페이지(홈·시도 리포트·/cycle/·퀴즈 점수 페이지)는 공용 규칙이, 자기 <style> 을
    쓰는 페이지(손 페이지·/weekly/·/monthly/·/moveins/·/jeonse-ratio/)는 그 규칙이 칠한다. 생성기도 같은 값을 굽는다 —
    make_indicator_pages SHELL 은 상수를 넣고, /weekly/ 는 뼈대가 산출물이라 put_nav 가 옛 11.5px 를 고쳐 쓴다(픽스처로 확인).
    데스크톱 홈 상단 내비(body.home-app .nav-btn, 1024px 이상)는 이보다 작지 않다.

    재현하는 실제 상태(2026-09-28 검토): 홈 작은 글씨를 13px 이상으로 올린 뒤에도 하단 탭바 라벨(홈·지역·시세·사이클)만
    11.5px 였다 — app.css·손 페이지 7곳·생성기 두 곳·/weekly/ 뼈대에 같은 값이 흩어져 있었다.
    변이(각각 확인): app.css `.nav-btn` 을 11.5px 로 되돌리면 홈·시도 리포트가, 손 페이지 하나(about)의 규칙을 되돌리면 그
    페이지가, SHELL 의 상수를 11.5px 로 박으면 SHELL 단정이, put_nav 의 글자 크기 고쳐 쓰기를 지우면 /weekly/ 픽스처 단정이
    빨개진다. 픽스처: 생성기를 돌린 뒤의 저장소 HTML 전부 + 옛 11.5px 뼈대로 되돌린 /weekly/ 사본.
    """
    want = float(N.LABEL_PX)
    assert want >= 13, '탭 라벨이 홈 글자 하한(13px)보다 작다'
    app = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    app_sizes = _label_sizes(re.sub(r'@media[^{]*\{(?:[^{}]*\{[^}]*\})*[^{}]*\}', '', app))
    assert app_sizes == [want], 'app.css .nav-btn 글자 %s ≠ 정본 %s' % (app_sizes, want)
    desk = re.search(r'body\.home-app \.nav-btn\{[^}]*font-size:([\d.]+)px', app)
    assert desk and float(desk.group(1)) >= want, '데스크톱 상단 내비 라벨이 정본보다 작다'
    bad, seen = {}, 0
    for rel in _html_pages():
        html = io.open(os.path.join(ROOT, rel), encoding='utf-8').read()
        if not NAV.search(html):
            continue
        seen += 1
        own = _label_sizes(''.join(re.findall(r'<style[^>]*>(.*?)</style>', html, re.S)))
        if own:
            if any(s != want for s in own):
                bad[rel] = own
        elif 'href="/app.css"' not in html:
            bad[rel] = '탭 라벨 규칙이 없다'
    assert seen > 10 and not bad, '탭 라벨 글자가 정본(%spx)과 다르다: %s' % (want, bad)
    assert _label_sizes(I.SHELL) == [want], 'make_indicator_pages SHELL 탭 라벨: %s' % _label_sizes(I.SHELL)
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    old = NAV_BTN_RULE.sub(lambda m: m.group(0).replace('font-size:%gpx' % want, 'font-size:11.5px'), page)
    assert _label_sizes(old) == [11.5], '픽스처가 옛 11.5px 뼈대가 아니다'
    W, Q = MW.load()
    assert _label_sizes(MW.render(old, W, Q)) == [want], '/weekly/ 생성기가 옛 탭 라벨 크기를 남긴다'


def test_manifest_shortcut_to_the_tab_uses_the_tab_label():
    """설치 앱 바로가기 중 이 탭(/#stats)으로 가는 칸은 탭과 같은 이름을 쓴다(짧은 이름에 탭 라벨).

    무엇을 깨뜨리면 빨개지나(실제로 확인): 바로가기를 옛 '부동산 데이터 통계'/'통계 보기' 로 되돌리면 빨개진다.
    픽스처: 저장소 manifest.webmanifest. '이달의 통계'(/monthly/)는 탭이 아니라 페이지 이름이라 대상이 아니다.
    """
    m = json.load(io.open(os.path.join(ROOT, 'manifest.webmanifest'), encoding='utf-8'))
    frag = urllib.parse.urlsplit(N.HREF['stats']).fragment
    hits = [s for s in m['shortcuts'] if urllib.parse.urlsplit(s['url']).path == '/'
            and urllib.parse.urlsplit(s['url']).fragment == frag]
    assert len(hits) == 1, '탭(%s)으로 가는 바로가기가 하나가 아니다: %s' % (N.HREF['stats'], m['shortcuts'])
    s = hits[0]
    assert N.LABEL['stats'] in s['short_name'] and N.LABEL['stats'] in s['name'], s


HARNESS = r'''
const cfg = %(cfg)s;
const sent = [];
function track(ev, p) { sent.push([ev, p]); }
function mk(t) {
  const h = {}; const el = {
    dataset: t.view ? {view: t.view} : {}, textContent: t.label, innerText: t.label,
    classList: {contains: c => (t.cls || '').split(' ').includes(c)},
    getAttribute: k => (k === 'href' ? (t.href === undefined ? null : t.href) : null),
    addEventListener: (ty, fn) => { (h[ty] = h[ty] || []).push(fn); },
    click: () => (h.click || []).forEach(f => f({})),
  }; return el;
}
const els = cfg.tabs.map(mk);
const document = {querySelectorAll: sel => (sel === '.bottomnav .nav-btn' ? els : [])};
eval(cfg.code);
els.forEach(e => e.click());
process.stdout.write(JSON.stringify(sent));
'''


def test_home_tab_click_is_measured_by_identifier_not_label():
    """홈 탭바 클릭이 GA nav_tab 이벤트로 가고, 값은 표시 문자열이 아니라 식별자(home·zone·stats·cycle)다.

    이름을 '통계' → '시세' 로 바꿔도 이벤트 값이 그대로여야 GA 에서 전후 탭 클릭 수를 한 줄로 비교한다(요청서 C2).
    홈 index.html 의 실제 탭바 마크업(data-view·href·라벨)을 읽어 모의 요소로 만들고, home-app.js 의 탭 클릭
    구문을 node 에서 돌려 네 탭을 차례로 누른다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 구문을 지우면, 값을 b.textContent(표시 문자열)로 바꾸면, 링크 탭의
    주소 가공을 빼서 '/zone/' 이 그대로 가면 빨개진다. 픽스처: 저장소 index.html 탭바와 home-app.js(home_source).
    """
    if not shutil.which('node'):
        pytest.skip('node 없음')
    src = HS.home_source()
    nav = NAV.search(src[src.index('<!-- ===== 하단 내비 ===== -->'):])
    assert nav, '홈 탭바를 못 찾았다'
    tabs = []
    for m in BTN.finditer(nav.group(1)):
        attrs = m.group(2)
        view = re.search(r'data-view="([^"]*)"', attrs)
        href = re.search(r'href="([^"]*)"', attrs)
        tabs.append({'view': view and view.group(1), 'href': href.group(1) if href else None,
                     'label': re.search(r'<span>([^<]*)</span>', m.group(3)).group(1),
                     'cls': re.search(r'class="([^"]*)"', m.group(0)).group(1)})
    m = re.search(r"document\.querySelectorAll\('\.bottomnav \.nav-btn'\)\.forEach\(.*?\)\)\);", src, re.S)
    assert m, "home-app.js 에 하단 탭 클릭 측정(nav_tab) 구문이 없다"
    p = subprocess.run(['node', '-e', HARNESS % {'cfg': json.dumps({'tabs': tabs, 'code': m.group(0)},
                                                                  ensure_ascii=False)}],
                       capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    sent = json.loads(p.stdout.decode('utf-8'))
    assert [e for e, _ in sent] == ['nav_tab'] * len(N.IDS), sent
    assert [x.get('tab') for _, x in sent] == list(N.IDS), '탭 클릭 값이 식별자가 아니다: %s' % sent
