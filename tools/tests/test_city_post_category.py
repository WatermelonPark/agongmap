# -*- coding: utf-8 -*-
"""도시 입주물량 편이 '지역별 아파트 공급' 카테고리를 같이 쓴다(2026-09-30 대표 결정). 두 시리즈를 제목의
'입주물량'으로 가르는지 고정한다.

가르지 않으면 도시 편이 지역 편 알림 이슈를 닫는다(발행 확인). 블로그 초안 도구 쪽 시험(지역 순번·글 끝 링크·제목·검색 순위
추적)은 2026-11-13 도구와 함께 지웠다. close_published_issues 는 살아 있는 blog_feed 가 RSS·카테고리 정본으로 쓰므로 남는다.

무엇을 깨뜨리면 빨개지나(실제로 확인):
  - close_published_issues.match 의 도시 편 제외 조건을 빼면 → test_city_post_does_not_close_zone_issue
픽스처: 실제 시범 초안(청주) 제목 형태, 이미 발행된 지역 편 제목 형태. 네트워크 없음.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import close_published_issues as C  # noqa: E402

ZONE = C.KIND_TO_CATEGORY['지역 공급']
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
