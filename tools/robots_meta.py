# -*- coding: utf-8 -*-
"""검색 로봇 메타의 정본 — 모든 페이지 <head> 에 `<meta name="robots" content="max-image-preview:large">` 한 줄
(홈 마케팅 검수 D2·DIST-4①, 2026-09-27).

왜: 구글 디스커버·이미지 검색이 큰 미리보기(가로 전체 이미지)를 쓰는 조건이 이 지시다. 없으면 작은 썸네일만 쓴다.
2026-09-27 기준 robots 메타가 있는 페이지는 404(noindex)·개인정보(index, follow) 두 장뿐이었고 max-image-preview 는 0장이었다.

쓰는 곳
  - 전체를 굽는 생성기(make_sido_pages 템플릿·통합 안내, make_indicator_pages SHELL — /monthly/ 도 이 뼈대,
    make_quiz_share_pages)는 뼈대 문자열에 TAG 를 그대로 넣는다.
  - 손 뼈대의 표식만 채우는 생성기(make_weekly_page, refresh_cycle_data)는 ensure() 로 없으면 넣는다 — 뼈대가 배치
    산출물이라 PR 로 고치지 않는다(CLAUDE.md). 첫 배치가 한 줄을 넣고 그 뒤로는 그대로 둔다.
  - 손 페이지(index.html·소개·FAQ·개인정보·404·퀴즈 랜딩)는 손으로 적는다.
저장소의 모든 .html 에 robots 메타가 **정확히 하나** 있고 그 content 에 CONTENT 가 드는지는 test_robots_meta 가 본다
(생성기를 돌린 뒤 — 배치 게이트는 생성기 뒤에 돈다).

이미 robots 메타가 있는 페이지(404 의 noindex, 개인정보의 index, follow)는 기존 뜻을 깨지 않고 content 에 덧붙인다
('noindex, max-image-preview:large'). 두 줄로 나누지 않는다 — 한 페이지에 robots 메타가 둘이면 해석이 엔진마다 다르다.

표준 라이브러리만 쓴다(생성기가 설치 없이 돈다).
"""
import re

CONTENT = 'max-image-preview:large'
TAG = '<meta name="robots" content="%s">' % CONTENT

# name="robots" 메타(속성 순서·따옴표 모양이 달라도 잡는다). content 값은 group('c').
_ROBOTS = re.compile(r'<meta\s+name=["\']robots["\']\s+content=["\'](?P<c>[^"\']*)["\']\s*/?>', re.I)
_ANY_ROBOTS = re.compile(r'<meta\b[^>]*\bname=["\']robots["\'][^>]*>', re.I)
_VIEWPORT = re.compile(r'<meta\s+name=["\']viewport["\'][^>]*>', re.I)
_CHARSET = re.compile(r'<meta\s+charset=[^>]*>', re.I)


def robots_metas(html):
    """페이지의 robots 메타 태그 전부(모양이 달라도). 시험과 ensure() 가 같은 눈으로 센다."""
    return _ANY_ROBOTS.findall(html)


def has_directive(content):
    return CONTENT in [x.strip().lower() for x in (content or '').split(',')]


def ensure(html):
    """robots 메타가 하나도 없으면 viewport(없으면 charset) 메타 바로 뒤에 TAG 를 넣고, 하나 있으면 content 에 CONTENT 를
    덧붙인다(이미 있으면 그대로). 둘 이상이거나 넣을 자리를 못 찾으면 SystemExit — 조용히 넘기면 그 페이지만 빠진다."""
    tags = robots_metas(html)
    if len(tags) > 1:
        raise SystemExit('robots 메타가 %d개다 — 하나로 합칠 것' % len(tags))
    if tags:
        m = _ROBOTS.search(html)
        if not m:
            raise SystemExit('robots 메타 모양을 읽지 못했다: %s' % tags[0])
        if has_directive(m.group('c')):
            return html
        c = m.group('c').strip()
        new = (c + ', ' + CONTENT) if c else CONTENT
        return html[:m.start('c')] + new + html[m.end('c'):]
    m = _VIEWPORT.search(html) or _CHARSET.search(html)
    if not m:
        raise SystemExit('robots 메타를 넣을 자리(viewport·charset 메타)를 찾지 못했다')
    # 앞 태그가 제 줄에 있으면 줄을 바꿔 넣고(손 뼈대), 한 줄로 이어 쓴 페이지면 이어 붙인다(통합 안내 페이지 모양).
    after = html[m.end():m.end() + 2]
    nl = '\r\n' if after.startswith('\r\n') else ('\n' if after.startswith('\n') else '')
    return html[:m.end()] + nl + TAG + html[m.end():]
