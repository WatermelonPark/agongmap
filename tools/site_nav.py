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

_I_CONTENT = ('<path d="M6 3h9l4 4v14H6z" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linejoin="round"/><path d="M15 3v4h4M9.5 12h6M9.5 16h6" fill="none" '
             'stroke="currentColor" stroke-width="2" stroke-linecap="round"/>')

# (식별자, 주소, 라벨, 아이콘). 칸 수를 바꾸면 칸 폭이 바뀌므로 대표 결정 사항이다(IA-6 2단계).
# 2026-10-29 대표 결정으로 '콘텐츠'가 들어와 다섯 칸이 됐다 — 콘텐츠 글(도시 입주물량·GTX·단지·해설)이
# 홈의 '최근 리포트'와 섹션 목록으로만 닿아 어디에도 입구가 없었다. 주소가 /content/ 가 아닌 까닭:
# 저장소 루트의 content/ 는 원고 소스라 같은 이름이면 서빙이 겹친다.
#
# 2026-10-30 대표 승인으로 '사이클'이 빠져 다시 네 칸이다. /cycle/ 은 주소도 내부 링크(홈 CTA·FAQ·주간
# 시세·퀴즈·입주물량·전세가율 등 스무 곳 남짓)도 그대로 두고, 입구만 /reports/ 허브의 '기본 개념' 줄로
# 옮겼다(make_content_pages.BASIC_CARDS). 근거는 GA 10/2~10/29: /cycle/ 세션 26 중 19가 사이트 안 이동이고
# 검색 랜딩은 7이라 탭을 빼도 검색 손실이 작다. ⚠️ 사이클 페이지는 탭바에서 'reports' 를 켠다 —
# 제 탭이 없어졌다고 아무 탭도 안 켜면 어디에 있는지 알 수 없다.
TABS = (
    ('home', '/', '홈', _I_HOME),
    ('zone', '/zone/', '지역', _I_ZONE),
    ('stats', '/#stats', '시세', _I_STATS),
    # 식별자는 주소의 영문 경로와 같게 둔다 — 홈의 탭 클릭 측정이 링크 탭의 주소에서 식별자를 뽑는다
    # (home-app.js: dataset.view || href 의 영문자). 라벨만 '콘텐츠' 다.
    ('reports', '/reports/', '콘텐츠', _I_CONTENT),
)
# 손 페이지가 켜는 탭(2026-10-30 디자인 리뷰 — 퀴즈 3종은 '홈', FAQ 는 아무것도 켜지 않았는데 푸터 사이트맵에서는 둘 다
# '읽을거리'였다). 읽을거리는 콘텐츠 탭('reports')이 맡으므로 그 탭을 켠다. 소개·개인정보·404 는 어느 탭에도 속하지 않아
# 켜지 않는다. test_site_nav 가 각 손 페이지 탭바의 켜진 탭을 이 표와 대조한다.
# 퀴즈 랜딩 3종은 2026-11-14 퀴즈 제거로 빠졌다(그 주소는 홈으로 넘기는 최소 페이지라 탭바·푸터가 없다).
HAND_TAB_ON = {'faq/index.html': 'reports',
               'about/index.html': None, 'privacy/index.html': None, '404.html': None}
# 탭 라벨 글자 크기(px) — 라벨 글자 하한 13px(2026-09-28 대표 결정 — 홈 작은 글씨 정리, 예전 11.5px). 탭바는 모든 페이지
# 공용이라 app.css·손 페이지 <style>·생성기(make_indicator_pages SHELL, make_weekly_page put_nav)가 이 값을 쓴다 —
# test_site_nav 가 저장소의 모든 탭바 규칙과 대조한다. 320px 네 칸(80px)에 '사이클' 13px(약 40px)이 들고, 탭바 높이(62px)는
# 고정이라 본문 아래 여백(padding-bottom 66px)은 그대로다.
# 브라우저 머리(주소창) 색 — 모든 페이지의 <meta name="theme-color"> 와 manifest theme_color 의 정본. 탭바 배경과 같은 먹색 토큰
# (app.css --ink)이다. 예전엔 소개·FAQ·/weekly/ 는 먹색, 나머지 29장과 manifest 는 옛 남색 #16203a 로 갈렸다(전수리뷰 P 묶음 overflow).
THEME_COLOR = '#131e24'

LABEL_PX = 13
# 사이트 글자 하한 두 단계의 정본(2026-11-06 대표 결정 '읽는 글 14px 하한 채택'). 읽는 문장 — 마침표로 끝나는 설명·주석·단락·카드
# 결론 줄·보기 줄·링크 카드 설명·푸터 면책 — 은 READ_PX 이상, 라벨·축 눈금·표 칸·칩·날짜·캡션 한 줄은 LABEL_PX(위 탭 라벨과 같은 값)
# 이상이다. SVG 지도 라벨·그래프 축·사이클 도식은 예외다. 손 페이지(소개·FAQ·개인정보·퀴즈 랜딩 3종·404)와 공용 푸터 면책은
# test_hand_reading_font 가 이 두 값으로 본다(홈·시세 탭·생성 페이지의 하한 시험은 아직 LABEL_PX 하나로 본다).
READ_PX = 14
# 탭바 키보드 초점(백로그 36-8, 2026-10-06) — 손 페이지 탭바엔 초점 표시가 없어 Tab 으로 어디 있는지 보이지 않았다. 먹색 바탕 위라
# 흰 테두리를 안쪽으로 그린다. app.css 와 각 페이지 <style> 이 이 글자를 그대로 싣고 test_site_nav 가 모든 탭바 페이지를 본다.
NAV_FOCUS_CSS = '.nav-btn:focus-visible{outline:2px solid #fff;outline-offset:-4px}'
# 키보드 초점이 하단 탭바(62px) 밑에 숨지 않게 — 초점을 옮길 때 브라우저가 이만큼 띄워 스크롤한다(WCAG 2.4.11, 2026-11-12 접근성
# 점검: 375px 에서 FAQ 질문·지도 칸·푸터 링크 등이 탭바 뒤에 통째로 가렸다). 탭바가 아래에 있는 폭(1023px 이하)만. 탭바를 싣는
# 모든 스타일 원본(app.css·지표 뼈대·주간 뼈대 생성기·손 페이지)이 이 글자를 싣고 test_site_nav 가 본다.
NAV_SCROLL_PAD_CSS = '@media(max-width:1023px){html{scroll-padding-bottom:72px}}'
# 웹 글꼴(Pretendard)이 늦게 와 글이 다시 줄바꿈되며 화면이 밀리는 것(CLS)을 줄이는 대체 글꼴 — 안드로이드 기본 한글 글꼴(Noto Sans
# CJK KR)을 Pretendard 한글 폭에 맞춰 94% 로 그린다(Pretendard 한글 폭은 Noto 의 0.939배 — 2026-11-12 브라우저 실측). 세로 치수도
# Pretendard(위 0.952·아래 0.248)를 size-adjust 로 나눈 값. 같은 조건 재현에서 /cycle/ 0.214 → 0, /column/ 0.113 → 0, /monthly/
# 0.035 → 0.002(375px), 서울 리포트 1280px 0.088 → 0.038. 그 글꼴이 없는 기기(iOS·Windows 기본)는 이 칸을 건너뛰어 예전과 같다.
# 글꼴 목록에서는 'Pretendard' 바로 뒤에 둔다(FONT_STACK_HEAD). 글꼴 목록을 싣는 모든 스타일 원본이 두 글자를 싣고 test_site_nav 가 본다.
FONT_FALLBACK_CSS = "@font-face{font-family:'Agong Fallback';src:local('Noto Sans CJK KR'),local('NotoSansCJKkr-Regular'),local('Noto Sans KR'),local('NotoSansKR-Regular');size-adjust:94%;ascent-override:101%;descent-override:26.4%;line-gap-override:0%;unicode-range:U+1100-11FF,U+3130-318F,U+AC00-D7A3}"
FONT_STACK_HEAD = "'Pretendard Variable','Pretendard','Agong Fallback',"
# 켜진 탭 색(2026-10-31 디자인 리뷰 2차 — FAQ 가 '콘텐츠' 탭을 켜도록 class="nav-btn on" 을 달았는데 이 규칙이 없어 네 탭이
# 모두 회색이었다). 탭을 켜는 페이지는 자기 <style> 이나 읽는 시트(app.css)에 이 글자를 싣고, test_site_nav 가 본다.
NAV_ON_CSS = '.nav-btn.on{color:#fff}'
# 틀 강조색(2026-11-11 대표 결정 B안 '남색 + 형광 표시'). 사이트 틀이 먹색·회색뿐이라(색 감사: 18개 페이지 종류 중 9개가
# 틀에 유채색 0%) 내비·선택된 단추·주요 단추·링크·요약 표지는 남색(--brand), 결론 숫자에는 노랑 형광 표시(--mark), 콘텐츠 분류
# 태그는 연노랑(--mark-bg·--mark-ink)으로 칠한다. 데이터(지도·표·그래프)는 의미색만 쓰고 이 색을 쓰지 않는다 — 남색은 하락 파랑
# (#2a62a3)보다 훨씬 어둡게 두어 갈린다. 모든 페이지의 :root 가 이 글자를 그대로 싣고 test_brand_color 가 대조한다.
BRAND_TOKENS = '--brand:#16325c;--brand-bg:#e8eef7;--mark:#ffe066;--mark-bg:#fff3b8;--mark-soft:#fff6cc;--mark-ink:#5a4300'
# 하단 탭바(데스크톱 위 내비) 바탕 — 모든 탭바 페이지가 같은 남색이다(test_brand_color).
NAV_BG_CSS = 'background:var(--brand)'
# 데이터 의미색 — 흰 바탕 위 등락 글자(2026-11-11 색 감사: '상승' 글자 빨강이 #c0392b·#a93226·#8f2318·#b23b2e 네 벌,
# '하락' 파랑이 #1a5276·#123c5c·#2a62a3 세 벌이었다). 흰 바탕 표·순위의 등락 글자는 이 둘만 쓴다(대비 6:1 이상).
# 지도 칸 채움과 칠한 칸 위 글자(make_weekly_page.tile_ink ↔ 홈 tcol)는 바탕이 달라 따로 둔다. test_brand_color 가 대조한다.
UP_INK = '#a93226'
DN_INK = '#1a5276'
# 그래프 계열색(2026-11-11 대표 결정 '사이클 색으로 통일') — 매매 빨강·전세 보라·공급(착공·준공·입주물량, 월세 선) 초록.
# /cycle/ 와 app.css --maemae·--jeonse·--stock 이 원래 쓰던 값이다. 시세 탭 시장동향(TR_COL)·기본통계(DS_COLOR)·콘텐츠 글 그림이
# 같은 값을 쓴다(test_brand_color). 지도·표의 상승·하락은 칸 채움·글자색(UP_INK·DN_INK)이라 선 그래프와 범례로 갈린다.
SERIES_COL = {'ma': '#c0392b', 'je': '#6c4ab6', 'sup': '#1f8a70'}
SERIES_TOKENS = '--maemae:#c0392b;--jeonse:#6c4ab6;--stock:#1f8a70'
# 뒤 단계가 채우는 표식 구간(자리는 그 페이지의 생성기가 빈 쌍으로 내고, 안쪽은 make_content_pages 가 채운다). 페이지를 다시 굽는
# 생성기는 늘 빈 쌍을 내므로, 커밋된 옛 판(채워진 구간)과 견주면 데이터가 그대로인 날에도 '내용 바뀜'이 된다 — 2026-11-13 전수
# 리뷰: 시도 리포트 전부와 /moveins/ 의 dateModified·'페이지 수정'·sitemap lastmod 가 매일 오늘로 올랐다. 그래서
# make_sido_pages.keep_dates 는 이 구간들을 양쪽에서 비우고 견준다. **keep_dates 를 거치는 페이지에 새 표식 구간을 두면 여기에 올린다**
# (test_late_slots). /weekly/ 해설 칸(WK:COLUMN)과 홈 CONTENT_RECENT 는 keep_dates 를 거치지 않는 페이지라 여기 없다.
SLOT_ZONE_POSTS = ('<!--ZONE_POSTS_START-->', '<!--ZONE_POSTS_END-->')
SLOT_MOVEINS_CITY = ('<!--MV:CITY-->', '<!--/MV:CITY-->')
LATE_SLOTS = (SLOT_ZONE_POSTS, SLOT_MOVEINS_CITY)
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
# 글자 크기: 푸터 바탕(브랜드·링크 줄·문의·자료 줄 — 한 줄 라벨)은 FOOTER_PX(= LABEL_PX 13px) 이상, 면책 문장은 읽는 글이라
# READ_PX(14px) 이상이다(2026-11-06). 면책의 크기는 FOOTER_DISC 의 인라인 style 이 싣는다 — 손 페이지 <style>·app.css·생성기
# 뼈대(make_indicator_pages SHELL·/weekly/ 뼈대)의 .disc·footer 규칙이 13px 이어도 이 한 줄이 이긴다. 그래서 면책 크기를 바꿀
# 곳은 여기 하나다(test_hand_reading_font 가 손 페이지·site_footer·퀴즈 점수 페이지를 본다).
# 연락처 agongmap@gmail.com 은 서비스 대표 주소(공개 연락처, 2026-09-18 대표 결정)다.
HAND_FOOTER_PAGES = ('about/index.html', 'faq/index.html', 'privacy/index.html', '404.html')
# 모든 페이지 푸터가 싣는 링크 줄의 정본(2026-10-30 디자인 리뷰 — 생성 페이지·콘텐츠 페이지 대부분에 개인정보처리방침 링크가
# 없었다). 손 페이지 HAND_FOOTER 와 생성기 푸터(site_footer)가 같은 글자를 쓰고, test_site_nav 가 저장소의 모든 <footer> 에
# 이 줄이 있는지 본다(홈 세 벌은 갱신 주기로 묶은 사이트맵 푸터라 test_home_summary 가 따로 본다).
# 메일은 링크 줄에서 뺐다(2026-11-07 디자인 검수 hand-10 — 한 줄에 중점 넷이라 메일 주소가 내비 링크처럼 읽혔고 375px 폭을 거의
# 다 채웠다). 메일은 FOOTER_CONTACT 한 줄로 링크 줄 아래에 둔다.
FOOTER_LINKS = ('<a href="/">홈</a> · <a href="/about/">소개</a> · <a href="/faq/">FAQ</a> · '
                '<a href="/privacy/">개인정보처리방침</a>')
FOOTER_CONTACT = '문의 <a href="mailto:agongmap@gmail.com">agongmap@gmail.com</a>'
FOOTER_BRAND = '<b>아공맵</b> — 아파트 공급 지도'
DISCLAIMER = '공공 데이터를 가공한 참고 자료이며 투자자문이 아닙니다. 투자 판단과 책임은 이용자에게 있습니다.'
FOOTER_PX = LABEL_PX
FOOTER_DISC = '<div class="disc" style="font-size:%gpx">%s</div>' % (READ_PX, DISCLAIMER)
HAND_FOOTER = ('<footer class="sfoot"><div class="wrap">\n'
               '  ' + FOOTER_BRAND + '<br>\n'
               '  ' + FOOTER_LINKS + '<br>\n'
               '  ' + FOOTER_CONTACT + '<br>\n'
               '  자료: KOSIS·한국부동산원·국토교통부·한국은행\n'
               '  ' + FOOTER_DISC + '\n'
               '</div></footer>')


def site_footer(src):
    """생성 페이지·콘텐츠 페이지 푸터 — 브랜드 · 링크 줄(FOOTER_LINKS) · 문의 · 그 페이지의 자료 기관 · 면책.
    src 는 기관명이다(공개 저장소 규칙 — '자료: 아공맵' 처럼 우리 이름을 출처로 쓰지 않는다). 없으면 자료 줄을 뺀다."""
    srcl = ('  자료: %s\n' % src) if src else ''
    return ('<footer class="sitefoot"><div class="wrap">\n'
            '  ' + FOOTER_BRAND + '<br>\n'
            '  ' + FOOTER_LINKS + '<br>\n'
            '  ' + FOOTER_CONTACT + (('<br>\n') if src else '\n')
            + srcl +
            '  ' + FOOTER_DISC + '\n'
            '</div></footer>')


# ── 데스크톱 틀(2026-10-06 대표 결정 '데스크톱 전체 개편') ─────────────────────────────────────────────────────
# 1024px 이상에서 하단 탭바를 위로 옮기고 화면마다 넓은 배치를 쓰는 규칙은 루트 desk.css 하나에 있다. 모든 탭바 페이지가
# desk_link() 를 <head> 에 싣고 <body data-desk="종류"> 로 배치를 고른다(종류는 desk.css 머리 주석). media 조건이라 1023px 이하
# 화면은 이 파일을 그리기에 쓰지 않는다 — 모바일은 예전과 같다. 주소의 v 는 desk.css 내용의 해시다: 서비스워커가 정적 파일을
# 캐시에서 먼저 주므로(sw.js) 파일을 고치면 주소가 바뀌어야 새 규칙이 닿는다. 손 페이지는 이 글자를 손으로 싣고
# test_site_nav 가 저장소의 모든 탭바 페이지를 대조한다(해시가 바뀌면 거기서 빨개져 고칠 곳을 알려 준다).
import hashlib as _hashlib
import os as _os

DESK_CSS = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'desk.css')
DESK_KINDS = ('read', 'wide', 'doc', 'report', 'weekly', 'home')


def desk_version():
    with open(DESK_CSS, 'rb') as f:
        return _hashlib.sha1(f.read().replace(b'\r\n', b'\n')).hexdigest()[:8]


def desk_link():
    return '<link rel="stylesheet" href="/desk.css?v=%s" media="(min-width:1024px)">' % desk_version()


def desk_body(kind, cls=None):
    """<body …> 여는 태그. kind 는 DESK_KINDS 가운데 하나."""
    if kind not in DESK_KINDS:
        raise ValueError('없는 데스크톱 배치: %r' % (kind,))
    return '<body%s data-desk="%s">' % (' class="%s"' % cls if cls else '', kind)


def dtoc(items, title='이 페이지'):
    """왼쪽 목차(doc 배치). items = [(앵커 id, 라벨)]. hidden 이라 desk.css 가 없는 좁은 화면에서는 보이지 않는다."""
    lis = ''.join('<li><a href="#%s">%s</a></li>' % (i, t) for i, t in items)
    return '<nav class="dtoc" hidden aria-label="목차"><b>%s</b><ol>%s</ol></nav>' % (title, lis)


# 목차에서 지금 읽는 절을 표시하고(aria-current), 접힌 <details> 로 가는 목차 링크는 펼친다(FAQ). 목차가 없거나 오래된
# 브라우저면 아무것도 하지 않는다 — 링크는 그대로 앵커로 동작한다.
DTOC_JS = ("<script>(function(){var t=document.querySelector('.dtoc');if(!t)return;"
           "var a=[].slice.call(t.querySelectorAll('a[href^=\"#\"]')),m={};"
           "a.forEach(function(x){var s=document.getElementById(x.getAttribute('href').slice(1));if(s)m[s.id]=x});"
           "t.addEventListener('click',function(e){var x=e.target.closest&&e.target.closest('a');if(!x)return;"
           "var d=document.getElementById(x.getAttribute('href').slice(1));if(d&&d.tagName==='DETAILS')d.open=true});"
           "if(!('IntersectionObserver' in window))return;"
           "var o=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting)return;"
           "a.forEach(function(x){x.removeAttribute('aria-current')});var x=m[e.target.id];"
           "if(x)x.setAttribute('aria-current','true')})},{rootMargin:'-15% 0px -75% 0px'});"
           "Object.keys(m).forEach(function(k){o.observe(document.getElementById(k))})})();</script>")
