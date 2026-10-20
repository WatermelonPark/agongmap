# -*- coding: utf-8 -*-
"""블로그 초안 도구의 작은 결함(2026-10-18 전수리뷰 BL1 overflow).

- 전세가율 절의 방향(올랐/내렸/보합)은 찍는 값(소수 한 자리)으로 가른다 — 원값으로 가르면 '전월 69.1%에서 올랐습니다'가 된다.
- '더 보기' 공급 칸의 '앞으로 N년간'은 판정 창 정본(SZ.LEAD_Q)에서 센다.
- 시리즈 링크의 RSS 주소(guid)는 이스케이프해 href 에 넣는다.

픽스처: 합성 두 달 전세가율 계열(69.06 → 69.14, 둘 다 69.1 로 찍힌다), 합성 RSS 글 목록(주소에 '&'·'"').
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import close_published_issues as CP  # noqa: E402
import make_indicator_pages as I  # noqa: E402
import make_naver_post as P  # noqa: E402
import sido_zones as SZ  # noqa: E402


def test_jeonse_direction_follows_the_printed_values(monkeypatch):
    """변이(확인): 방향을 원값(cur > prv)으로 되돌리면 '올랐습니다'가 나와 빨개진다."""
    monkeypatch.setattr(I, 'jeonse_ref_index', lambda j, need: len(j['dates']) - 1)
    sts = {'전세가율': {'dates': ['2026.07', '2026.08'], 'series': {'전국': [69.06, 69.14]}}}
    h = P.extra_section({}, sts, 0)
    assert '전월 69.1%에서 보합입니다' in h, h
    sts['전세가율']['series']['전국'] = [68.9, 69.14]
    assert '올랐습니다' in P.extra_section({}, sts, 0)


def test_more_rotation_years_come_from_the_window():
    """공급 칸 문구가 정본 식(SZ.LEAD_Q // 4)으로 만든 연수를 쓰고, 소스에 연수가 박혀 있지 않다.
    변이(확인): 문구를 옛 '앞으로 3년간 …'(박힌 연수)으로 되돌리면 소스 단정이 빨개진다."""
    import inspect
    desc = next(m['desc'] for m in P.MORE_ROTATION if m.get('path') == '/zone/')
    assert ('앞으로 %d년간' % (SZ.LEAD_Q // 4)) in desc
    assert "앞으로 3년간" not in inspect.getsource(P)


def test_series_link_href_is_escaped(monkeypatch):
    """변이(확인): series_links 의 href 를 p['url'] 그대로 두면 빨개진다."""
    import datetime
    posts = [dict(date=datetime.date(2026, 10, 16), cat=CP.KIND_TO_CATEGORY['주간 시세'], title='주간 "따옴표" 글',
                  url='https://blog.naver.com/startupbd/1?a=1&b="x"')]
    monkeypatch.setattr(CP, 'fetch_posts', lambda: posts)
    h = P.series_links('부산', 1, 16)
    assert 'href="https://blog.naver.com/startupbd/1?a=1&amp;b=&quot;x&quot;"' in h, h
