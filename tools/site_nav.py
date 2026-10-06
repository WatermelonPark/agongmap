# -*- coding: utf-8 -*-
"""하단 탭바의 정본 — 탭 순서·주소·라벨·아이콘을 여기 하나에 둔다(홈 마케팅 검수 C2, 2026-09-27).

탭바는 홈(index.html)과 손 페이지(소개·FAQ·개인정보·404·퀴즈 랜딩 3종·/cycle/)에 손으로, 생성기
(make_sido_pages FOOT, make_indicator_pages SHELL — /monthly/ 도 이 뼈대, make_weekly_page put_nav)에 문자열로
복제돼 있었다. '통계' 탭 이름을 '시세'로 바꾸는 한 번의 결정이 서른 곳 넘게 흩어져 있어, 한 곳만 빠져도 아무것도
빨개지지 않았다(CLAUDE.md 데이터 원칙: 같은 대상을 재는 코드는 같은 상수를 쓴다). 생성기는 bottomnav() 로 굽고,
손 페이지는 라벨을 손으로 맞추되 test_site_nav 가 저장소의 모든 HTML 탭바를 TABS 와 대조한다.

탭 식별자(id)는 표시 이름과 따로 간다 — 홈의 data-view="stats", 해시 '#stats', GA page_title 'view_stats',
탭 클릭 이벤트 nav_tab 의 tab 값이 모두 'stats' 그대로라 이름을 바꿔도 GA 에서 전후가 한 줄로 이어진다.
'시세'로 바꾼 까닭: 이 탭의 기본 화면이 시장동향·주간 시세 지도라 이름과 내용이 맞는다. 투자지표·기본통계는
그 안의 탭으로 남는다(요청서 C2, HERO-7·RET-8·IA-6 2단계·MOB-3).

표준 라이브러리만 쓴다(생성기가 설치 없이 돈다).
"""

_SVG = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">%s</svg>'
_I_HOME = ('<path d="M3 11l9-8 9 8M5 10v10h14V10" fill="none" stroke="currentColor" stroke-width="2" '
           'stroke-linecap="round" stroke-linejoin="round"/>')
_I_ZONE = ('<path d="M12 21s-7-5.8-7-11a7 7 0 0 1 14 0c0 5.2-7 11-7 11z" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="10" r="2.5" fill="none" '
           'stroke="currentColor" stroke-width="2"/>')
_I_STATS = ('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round"/>')
_I_CYCLE = ('<path d="M20 12a8 8 0 1 1-2.34-5.66" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round"/><path d="M20.3 3.7v5h-5" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"/>')

# (식별자, 주소, 라벨, 아이콘). 네 칸 — 칸 수를 바꾸면 375px 칸 폭(약 94px)이 바뀌므로 대표 결정 사항이다(IA-6 2단계).
TABS = (
    ('home', '/', '홈', _I_HOME),
    ('zone', '/zone/', '지역', _I_ZONE),
    ('stats', '/#stats', '시세', _I_STATS),
    ('cycle', '/cycle/', '사이클', _I_CYCLE),
)
# 탭 라벨 글자 크기(px) — 홈 화면 글자 하한 13px(2026-09-28 대표 결정 — 홈 작은 글씨 정리, 예전 11.5px). 탭바는 모든 페이지
# 공용이라 app.css·손 페이지 <style>·생성기(make_indicator_pages SHELL, make_weekly_page put_nav)가 이 값을 쓴다 —
# test_site_nav 가 저장소의 모든 탭바 규칙과 대조한다. 320px 네 칸(80px)에 '사이클' 13px(약 40px)이 들고, 탭바 높이(62px)는
# 고정이라 본문 아래 여백(padding-bottom 66px)은 그대로다.
LABEL_PX = 13
# 탭바 키보드 초점(백로그 36-8, 2026-10-06) — 손 페이지 탭바엔 초점 표시가 없어 Tab 으로 어디 있는지 보이지 않았다. 먹색 바탕 위라
# 흰 테두리를 안쪽으로 그린다. app.css 와 각 페이지 <style> 이 이 글자를 그대로 싣고 test_site_nav 가 모든 탭바 페이지를 본다.
NAV_FOCUS_CSS = '.nav-btn:focus-visible{outline:2px solid #fff;outline-offset:-4px}'
IDS = tuple(t[0] for t in TABS)
LABELS = tuple(t[2] for t in TABS)
HREF = {t[0]: t[1] for t in TABS}
LABEL = {t[0]: t[2] for t in TABS}


def bottomnav(on=None):
    """하단 탭바 <nav> 한 덩어리. on 은 켤 탭의 식별자(없으면 켜진 탭 없음)."""
    if on is not None and on not in IDS:
        raise ValueError('없는 탭: %r' % (on,))
    rows = []
    for tid, href, label, icon in TABS:
        cls = ' on" aria-current="page' if tid == on else ''
        rows.append('  <a class="nav-btn%s" href="%s">%s<span>%s</span></a>' % (cls, href, _SVG % icon, label))
    return '<nav class="bottomnav">\n' + '\n'.join(rows) + '\n</nav>'


# ── 손 페이지 푸터(백로그 36-4, 2026-10-06) ─────────────────────────────────────────────────────────────
# 소개·FAQ·개인정보·퀴즈 랜딩 3종·404 의 푸터가 제각각이었다 — 어떤 곳은 면책이 없고(개인정보·퀴즈), 어떤 곳은 소개·개인정보
# 링크가 없었다(FAQ·퀴즈). 이 한 덩어리를 그대로 붙이고 test_site_nav 가 각 페이지의 <footer> 를 이 값과 대조한다.
# 글자 크기는 13px 이상(시세 탭·퀴즈·푸터 하한 — test_view_min_font, 손 페이지 쪽은 test_site_nav 가 본다).
# 연락처 agongmap@gmail.com 은 서비스 대표 주소(공개 연락처, 2026-09-18 대표 결정)다.
HAND_FOOTER_PAGES = ('about/index.html', 'faq/index.html', 'privacy/index.html', 'burini-test/index.html',
                     'investor-test/index.html', 'redev-test/index.html', '404.html')
HAND_FOOTER = ('<footer class="sfoot"><div class="wrap">\n'
               '  <b>아공맵</b> — 아파트 · 공급량 · 투자지도<br>\n'
               '  <a href="/">홈</a> · <a href="/about/">소개</a> · <a href="/faq/">FAQ</a> · '
               '<a href="/privacy/">개인정보처리방침</a> · <a href="mailto:agongmap@gmail.com">agongmap@gmail.com</a><br>\n'
               '  자료: KOSIS·한국부동산원·국토교통부·한국은행 · 공공 데이터를 가공한 참고 자료이며 투자자문이 아닙니다. '
               '투자 판단과 책임은 이용자에게 있습니다.\n'
               '</div></footer>')
FOOTER_PX = 13
