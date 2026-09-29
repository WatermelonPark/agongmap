# -*- coding: utf-8 -*-
"""도시 입주물량 편이 '지역별 아파트 공급' 카테고리를 같이 쓴다(2026-09-30 대표 결정). 두 시리즈를 제목의
'입주물량'으로 가르는지 고정한다.

가르지 않으면 생기는 일: 도시 편이 지역 편 알림 이슈를 닫고(발행 확인), '2027년 서울 아파트 입주물량, …'이
서울 지역 편으로 세어져 지역 순번이 밀리고, 지역 편 글 끝 '같은 기준으로 본 다른 글'에 도시 편이 걸린다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - close_published_issues.match 의 도시 편 제외 조건을 빼면 → test_city_post_does_not_close_zone_issue
  - make_naver_post._zone_of_title 앞의 is_city_post 반환을 빼면 → test_city_post_is_not_counted_as_zone
  - series_links 의 도시 편 건너뛰기를 빼면 → test_series_links_skip_city_posts
  - zone_title 에 '입주물량'을 넣으면(두 안 어느 쪽이든) → test_zone_titles_never_carry_city_mark
  - naver_serp.track_keywords 가 도시 편도 '전망' 앞으로 자르면 → test_city_post_tracks_title_head
픽스처: 실제 시범 초안(청주) 제목 형태와 같은 형태의 서울 제목, 이미 발행된 지역 편 제목 형태(A안·B안). 네트워크 없음.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import close_published_issues as C  # noqa: E402
import make_naver_post as P  # noqa: E402
import naver_serp as NS  # noqa: E402
import sido_zones as SZ  # noqa: E402

ZONE = C.KIND_TO_CATEGORY['지역 공급']
NAMES = [z for z in SZ.ORDER if z not in SZ.AGG]
CITY_SEOUL = '2027년 서울 아파트 입주물량, 정점을 찍고 2029년엔 4분의 1로 줄어듭니다'
CITY_CJ = '2027년 청주 아파트 입주물량, 정점을 찍고 2029년엔 4분의 1로 줄어듭니다'
ZONE_SEOUL = '2027년 서울 아파트 공급물량 전망, 앞으로 3년 얼마나 부족할까'
D = datetime.date


def test_city_post_does_not_close_zone_issue():
    """월요일 지역 편이 밀린 주에 수요일 도시 편이 나가면, 예전 match 는 같은 카테고리라 그 이슈를 닫았다."""
    issues = [dict(n=1, kind='지역 공급', cat=ZONE, due=D(2026, 10, 5), title='지역 공급 (2026-10-05)')]
    posts = [dict(date=D(2026, 10, 7), cat=ZONE, title=CITY_CJ, url='city')]
    assert C.match(posts, issues) == [], '도시 편이 지역 편 알림 이슈를 닫는다'
    posts.append(dict(date=D(2026, 10, 8), cat=ZONE, title=ZONE_SEOUL, url='zone'))
    assert [(i['n'], p['url']) for i, p in C.match(posts, issues)] == [(1, 'zone')]


def test_city_post_is_not_counted_as_zone():
    assert P._zone_of_title(CITY_SEOUL, NAMES) is None, '서울 도시 편이 서울 지역 편으로 세어진다'
    assert P._zone_of_title(ZONE_SEOUL, NAMES) == '서울'


def test_series_links_skip_city_posts(monkeypatch):
    posts = [dict(date=D(2026, 9, 27), cat=ZONE, title='2027년 세종시 부동산 전망, 앞으로 3년', url='zone-sejong'),
             dict(date=D(2026, 10, 7), cat=ZONE, title=CITY_CJ, url='city-cj'),
             dict(date=D(2026, 10, 2), cat=C.KIND_TO_CATEGORY['주간 시세'], title='주간 아파트가격 동향', url='week')]
    monkeypatch.setattr(C, 'fetch_posts', lambda: posts)
    html = P.series_links('부산', 1)
    assert 'zone-sejong' in html and 'city-cj' not in html, html


def test_zone_titles_never_carry_city_mark():
    """두 시리즈를 가르는 표지다. 지역 편 제목에 이 말이 들어가면 발행한 지역 편을 못 세고 같은 지역을 또 고른다."""
    for seq in range(1, P.TITLE_ARM_FROM + 4):
        for ask in ('부족할까', '남을까'):
            t = P.zone_title('서울', '2027', 3, ask, seq)
            assert not C.is_city_post(t), t


def test_city_post_tracks_title_head():
    kws = NS.track_keywords([dict(date='2026-10-07', cat=ZONE, title=CITY_CJ)])
    assert '2027년 청주 아파트 입주물량' in kws, kws
    assert not any('정점' in k for k in kws), '제목 통째가 질의가 된다'
