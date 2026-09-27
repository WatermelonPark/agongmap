# -*- coding: utf-8 -*-
"""지역 편 캡처는 리포트의 칸을 화면 덩어리 순번이 아니라 섹션 제목으로 고른다(2026-09-27).

순번 방식(카드=1, 표=2, 다른 지역=4)은 리포트에 '시세도 함께' 칸이 들어오자 한 칸 밀려, 세종 편 초안의
'16개 시도 판정표' 자리에 시세 카드 두 칸이 찍혔다(대표 발견). 지금은 저장소의 zone/<지역>/index.html 에서
제목(h2)에 '분기별 공급'·'다른 지역'이 든 섹션을 떼어 캡처용 페이지를 만들고 그 페이지를 찍는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - ZONE_SECTIONS 의 판정표 제목을 다른 칸('시세도 함께')으로 바꾸면 → 판정표 시험
  - GA 스크립트 빼기를 지우면 → 판정표 시험(캡처가 방문으로 잡힌다)
  - 루트 기준 주소('/app.css') 바꾸기를 지우면 → 판정표 시험(스타일 없는 맨 글자가 찍힌다 — 실제로 한 번 그렇게 찍혔다)
  - 표 동작 스크립트까지 빼면 → 분기표 시험(스크롤 상자가 2017년 행부터 찍힌다 — 실제로 한 번 그렇게 찍혔다)
  - capture_zone 이 다시 _blocks 순번으로 자르면 → 연결 시험
픽스처: 저장소의 실제 zone/세종/index.html(생성기 산출물). 크롬은 부르지 않는다.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402


def test_judgment_grid_page_is_that_section_only():
    h = P._section_page('세종', P.ZONE_SECTIONS['판정표'])
    assert h and 'sc-tier' in h and '제주' in h
    assert '이번 주 시세' not in h and 'zback' not in h            # 옆 칸·돌아가기 링크 없음
    assert 'googletagmanager' not in h and "gtag('config'" not in h
    assert 'href="app.css"' in h and 'href="/app.css"' not in h


def test_quarterly_table_page_keeps_table_script():
    h = P._section_page('세종', P.ZONE_SECTIONS['표'])
    assert h and '<table class="ztb"' in h
    assert 'src="zone/zone.js' in h                                  # 최근 분기로 스크롤하는 스크립트


def test_missing_section_is_none():
    assert P._section_page('세종', '없는 칸 제목') is None


def test_capture_zone_uses_sections_not_block_order():
    src = inspect.getsource(P.capture_zone)
    assert '_shoot_section(' in src and '_blocks(' not in src
