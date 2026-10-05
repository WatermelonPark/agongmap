# -*- coding: utf-8 -*-
"""홈 구역 입구마다 home_cta 의 to 값이 붙어 있다(홈 마케팅 검수 A3·IA-7·RET-9, 2026-09-27).

재현하는 실제 상태: 09-26 까지 track('home_cta', …) 는 사이클 버튼 하나뿐이었다. 주간 격자·주간 버튼·
'시도별로 자세히 보기'·퀴즈 버튼 셋에는 없어, 첫 화면을 바꾼 뒤 홈에서 어디로 몇 명이 갔는지 비교할 기준선이
없었다(08-17 요청서의 '기존 to 측정기준을 태워 홈→주간 이동이 잡히게' 요구도 이행되지 않았다). /weekly/ 로 가는
입구 셋(격자·버튼·푸터)도 구별할 수 없었다.

무엇을 깨뜨리면 빨개지나: 퀴즈 버튼 하나의 onclick 을 지우거나, 격자 링크의 to 를 'weekly_map' 으로 바꿔 버튼과
겹치게 하거나, 값을 'WeeklyGrid' 처럼 snake_case 밖으로 쓰면 빨개진다(셋 다 실제로 바꿔 확인).
픽스처: 손으로 쓴 index.html 홈 뷰와 home-app.js 가 굽는 주간 격자 링크(home_src 로 읽는다).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import blog_feed as BF  # noqa: E402  (블로그 첫 화면 주소의 정본 — 푸터 링크, 홈 마케팅 검수 B5)

# 입구(목적지) → to 값. 목적지가 같은 입구도 값이 달라야 한다(/weekly/ 격자·푸터).
WANT = {
    ('/zone/', '시도별로 자세히 보기'): 'zone_hub',
    ('#stats-market', '시군구 상승·하락 TOP 10 보기'): 'weekly_map',
    ('/burini-test/', '부린이 테스트 · 난이도'): 'quiz_burini',
    ('/investor-test/', '투자자 테스트 · 난이도'): 'quiz_investor',
    ('/redev-test/', '재건축·재개발 테스트 · 난이도'): 'quiz_redev',
    ('/cycle/', '사이클 리포트 읽기'): 'cycle',
    ('/weekly/', '이번 주 시세 지도'): 'weekly_footer',
    # 푸터 '매주' 묶음의 블로그 링크(홈 마케팅 검수 B5·IA-9, 2026-09-27). 주간 구역의 해석 글 한 줄(blog_weekly)은 스크립트가
    # 그린다 — test_home_summary 가 본다.
    (BF.BLOG_HOME, '매주 해설 글'): 'blog_footer',
    # 3차(2026-09-27): 이달의 통계 입구(B6·IA-8 — 푸터 '이달의 통계'와 가르려고 입구 이름 전체로 찾는다).
    # 첫 화면 '이번 주' 띠(weekly_hero)·'내 지역' 줄(my_zone)은 2026-10-05 대표 요청으로 뺐다.
    ('/monthly/', '이달의 통계 한 화면으로 보기'): 'monthly',
}
TO = re.compile(r"""onclick="track\('home_cta',\{to:'([^']*)'\}\)\"""")


def _home_view():
    s = HS.home_source()   # index.html 이 앞에 온다 — 홈 뷰 마크업만 잘라 쓴다
    return s[s.index('<div id="view-home">'):s.index('<!-- ===== 통계보기 대시보드 ===== -->')]


def test_every_home_entrance_carries_its_own_to_value():
    home = _home_view()
    got = {}
    for m in re.finditer(r'<a ([^>]*)>(.*?)</a>', home, re.S):
        attrs, text = m.group(1), re.sub(r'<[^>]+>', '', m.group(2))
        href = re.search(r'href="([^"]+)"', attrs)
        for (h, label), _ in WANT.items():
            if href and href.group(1) == h and label in text:
                t = TO.search(attrs)
                got.setdefault((h, label), []).append(t.group(1) if t else None)
    missing = [k for k in WANT if k not in got]
    assert not missing, '홈 뷰에서 입구를 찾지 못했다: %s' % missing
    bad = {k: (v, WANT[k]) for k, v in got.items() if any(x != WANT[k] for x in v)}
    assert not bad, 'home_cta to 값이 없거나 다르다(입구: (있음, 기대)): %s' % bad


def test_weekly_grid_link_is_tagged_and_values_are_distinct_snake_case():
    src = HS.home_source()
    m = re.search(r'<a class="wg-link" href="/weekly/" onclick="track\(\\\'home_cta\\\',\{to:\\\'([^\\]*)\\\'\}\)">', src)
    assert m, '주간 격자 링크(renderWeeklyGrid)에 home_cta to 값이 없다'
    vals = list(WANT.values()) + [m.group(1)]
    assert m.group(1) == 'weekly_grid'
    assert len(set(vals)) == len(vals), '입구끼리 to 값이 겹친다: %s' % vals
    assert all(re.match(r'^[a-z][a-z0-9_]*$', v) for v in vals), vals
    # 홈 뷰의 home_cta 가 모두 이 표 안에 있다 — 표에 없는 값이 생기면 여기서 표를 늘린다
    assert set(TO.findall(_home_view())) == set(WANT.values())


def test_in_page_entrances_keep_the_landing_query():
    """홈 안에서 화면만 바꾸는 입구는 쿼리를 버리지 않는다 — 쿼리 착지에서 문서를 다시 불러오거나 뒤로 가기가 어긋나지 않게.

    재현하는 실제 상태(1차 배포 검증, 2026-09-27): 설치 앱 start_url 이 '/?utm_source=pwa…', 블로그 주간 링크가
    '/?utm…#stats-market' 로 바뀌어 쿼리 착지가 가장 흔한 진입이 됐다. 그때 ① 주간 버튼이 '/#stats-market'(절대
    경로)이면 '/?q' 에서 눌렀을 때 쿼리가 달라 해시 이동이 아니라 문서 전체를 다시 불러왔고(GA 착지 hit 도 다시
    나감), ② showView('home') 이 location.pathname 만 pushState 하면 홈 → 뒤로 가기에서 쿼리까지 바뀌어 hashchange
    가 오지 않아 주소는 통계, 화면은 홈에 머물렀다(Chromium 375px 재현).
    변이: 버튼 href 를 '/#stats-market' 으로, showView 의 홈 tgtUrl 을 location.pathname 으로 되돌리면 각각
    빨개진다(실제로 확인).
    """
    home = _home_view()
    bad = re.findall(r'<a class="home-cta" href="(/#[^"]*)"', home)
    assert not bad, '같은 문서 안 화면 전환 입구가 절대 경로(%s)다 — 쿼리 착지에서 문서를 다시 불러온다' % bad
    src = HS.home_source()
    # 홈 주소의 쿼리는 q — 퀴즈가 아니면 대결 쿼리(c·s·q)만 걷은 location.search(chalSearch, 전수리뷰 #44)
    m = re.search(r"tgtUrl=v==='home'\?([^:]+):", src)
    assert m and m.group(1) == 'location.pathname+q', "홈으로 갈 때 pushState 주소가 쿼리를 버린다: %s" % (m and m.group(1))
    assert "const q=v==='test'?location.search:chalSearch();" in src
    assert re.search(r"function chalSearch\(\)\{\s*if\(!chalInURL\(location\.search\)\)return location\.search;", src)
