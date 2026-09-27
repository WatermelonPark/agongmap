# -*- coding: utf-8 -*-
"""앱 바로가기·설치 사용자 측정·'통계' 탭 위치 표시(홈 마케팅 검수 A5 — RET-8, IA-6 1단계, PWA-1 일부, 2026-09-27).

재현하는 실제 상태(2026-09-26 검수):
  - 홈 화면 아이콘을 길게 누르면 부린이·투자자 테스트가 먼저 나왔고, 가장 자주 바뀌는 주간 시세는 없었다.
  - start_url 이 '/' 라 설치 앱으로 들어온 방문이 GA 에서 직접 유입과 섞였다.
  - 블로그 주간 글 독자가 착지하는 /weekly/ 와 /monthly/·/moveins/·/jeonse-ratio/ 의 하단 탭바에 켜진 탭이 없어
    (각 HTML 에서 'nav-btn on' 0건) 사이트의 어느 메뉴인지 보이지 않았다.
"""
import io
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_weekly_page as MW  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _manifest():
    return json.load(io.open(os.path.join(ROOT, 'manifest.webmanifest'), encoding='utf-8'))


def _page_file(path):
    """사이트 주소 → 저장소 파일('/' 는 index.html, '/x/' 는 x/index.html)."""
    rel = path.lstrip('/')
    if not rel or rel.endswith('/'):
        rel += 'index.html'
    return os.path.join(ROOT, *rel.split('/'))


def test_install_id_is_pinned_and_start_url_is_measured():
    """start_url 에 pwa UTM 을 붙이되 id 는 '/' 로 고정한다.

    id 가 없으면 브라우저는 start_url 을 앱 식별자로 쓴다 — start_url 을 바꾸는 순간 이미 설치한 사람의 앱이 다른
    앱이 된다. id 를 옛 start_url('/')로 박아 두었으므로 UTM 을 붙여도 기존 설치에는 영향이 없다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): id 를 지우거나 start_url 과 같게 바꾸면, start_url 에서 utm_source=pwa
    를 빼면, '?utm…' 을 '#' 뒤로 보내면(A1 과 같은 결함) 빨개진다. 픽스처: 저장소 manifest.webmanifest.
    """
    m = _manifest()
    assert m.get('id') == '/', "manifest id 는 '/'(옛 start_url)로 고정한다 — 바꾸면 기존 설치 앱이 다른 앱이 된다: %r" % m.get('id')
    u = urllib.parse.urlsplit(m['start_url'])
    q = urllib.parse.parse_qs(u.query)
    assert u.path == '/' and not u.fragment, 'start_url 은 홈이어야 한다: %s' % m['start_url']
    assert q.get('utm_source') == ['pwa'] and q.get('utm_medium'), '설치 앱 방문을 가를 UTM 이 없다: %s' % m['start_url']
    assert m['start_url'].startswith(m['scope']), 'start_url 이 scope 밖이다'


def test_first_shortcut_is_this_weeks_prices_and_all_shortcuts_land():
    """바로가기 첫 칸은 '이번 주 아파트 시세'(/weekly/), 투자자 테스트 칸은 '이달의 통계'(/monthly/)다(IA-6 1단계).

    모든 바로가기는 ① 저장소에 실제로 있는 페이지로 가고 ② pwa UTM 을 '#' 앞 쿼리로 싣는다(설치 사용자 측정).
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 옛 순서(부린이 테스트 첫 칸)로 되돌리면, /monthly/ 바로가기를 빼면,
    바로가기 주소를 없는 '/weekly2/' 로 바꾸면, 바로가기 UTM 을 '#' 뒤로 보내면 빨개진다.
    """
    sc = _manifest()['shortcuts']
    first = urllib.parse.urlsplit(sc[0]['url'])
    assert first.path == '/weekly/' and sc[0]['name'] == '이번 주 아파트 시세', '바로가기 첫 칸이 주간 시세가 아니다: %s' % sc[0]
    paths = [urllib.parse.urlsplit(s['url']).path for s in sc]
    assert '/monthly/' in paths, "'이달의 통계'(/monthly/) 바로가기가 없다: %s" % paths
    for s in sc:
        u = urllib.parse.urlsplit(s['url'])
        assert os.path.isfile(_page_file(u.path)), '바로가기가 없는 페이지로 간다: %s' % s['url']
        assert urllib.parse.parse_qs(u.query).get('utm_source') == ['pwa'], '바로가기에 pwa UTM 이 없다: %s' % s['url']
        assert '?' not in u.fragment, "UTM 이 '#' 뒤에 있다 — 쿼리가 아니라 해시라 GA 가 못 읽는다: %s" % s['url']


# 통계 탭 아래 읽을거리 — 이 페이지들의 하단 탭바는 '통계'(/#stats)를 켠다.
STATS_PAGES = ('weekly', 'monthly', 'moveins', 'jeonse-ratio')


def _nav(html):
    m = re.search(r'<nav class="bottomnav">(.*?)</nav>', html, re.S)
    assert m, '하단 탭바를 못 찾았다'
    return re.findall(r'<a class="nav-btn( on)?"[^>]*href="([^"]*)"', m.group(1))


def test_stats_pages_light_the_stats_tab():
    """/weekly/·/monthly/·/moveins/·/jeonse-ratio/ 의 탭바에서 '통계'(/#stats) 하나만 켜지고, 켜진 색 규칙이 있다.

    이 페이지들은 공용 시트를 안 읽으므로 .nav-btn.on 규칙이 페이지 안에 있어야 켜진 것이 보인다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 지표 생성기 SHELL 의 '통계' 링크에서 on 을 빼거나 .nav-btn.on 규칙을
    지우면(생성기를 돌린 뒤) 빨개진다. /weekly/ 는 뼈대를 페이지 파일에 두고 표식 자리만 다시 쓰므로, 한 번 켜진 뒤에는
    생성기에서 put_nav 를 빼도 이 시험은 초록이다(실제로 확인) — 그 변이는 아래 시험이 잡는다.
    픽스처: 생성기가 구운 저장소의 네 페이지(배치·CI 는 생성기를 먼저 돌린다).
    """
    for d in STATS_PAGES:
        html = io.open(os.path.join(ROOT, d, 'index.html'), encoding='utf-8').read()
        on = [href for flag, href in _nav(html) if flag]
        assert on == ['/#stats'], '/%s/ 탭바에서 켜진 탭이 통계 하나가 아니다: %s' % (d, on)
        assert re.search(r'\.nav-btn\.on\{[^}]*color:#fff', html), '/%s/ 에 켜진 탭 색 규칙이 없다' % d


def test_generators_light_the_stats_tab_on_any_page():
    """생성기 자체가 탭을 켠다 — 손으로 켠 페이지가 우연히 초록이 되지 않게, 탭이 꺼진 뼈대에서 굽는다.

    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): make_weekly_page.render 에서 put_nav 를 빼면, NAV_ON 을 '/zone/' 로
    바꾸면, 뼈대에 .nav-btn.on 규칙이 없을 때 넣는 분기를 지우면, SHELL 의 '통계' 링크에서 on 을 빼면 빨개진다.
    픽스처: 켜진 탭·규칙이 없던 2026-09-26 /weekly/ 뼈대 모양과 저장소 data.js 의 주간 계열.
    """
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    off = re.sub(r'<a class="nav-btn on" aria-current="page"', '<a class="nav-btn"', page)
    off = re.sub(r'\r?\n' + re.escape(MW.NAV_ON_CSS), '', off)
    assert not [f for f, _ in _nav(off) if f] and MW.NAV_ON_CSS not in off, '픽스처가 꺼진 뼈대가 아니다'
    W, Q = MW.load()
    got = MW.render(off, W, Q)
    assert [h for f, h in _nav(got) if f] == ['/#stats'] and MW.NAV_ON_CSS in got, '/weekly/ 생성기가 통계 탭을 켜지 않는다'
    assert MW.render(got, W, Q) == got, '생성기가 멱등이 아니다 — 배치마다 페이지가 바뀐다'
    assert [h for f, h in _nav(I.SHELL) if f] == ['/#stats'], '지표 생성기 뼈대가 통계 탭을 켜지 않는다'
