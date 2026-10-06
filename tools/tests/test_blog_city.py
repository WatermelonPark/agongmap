# -*- coding: utf-8 -*-
"""/moveins/ 의 '도시별 입주 예정 단지' 칸 — 블로그 도시 입주물량 편만, 새 글부터, 없으면 칸째 빠진다(백로그 37, 2026-10-07).

재현하는 실제 상태: GA 지난 28일 /moveins/ 는 홈 다음으로 유입이 많지만(43명) 참여 22초로 짧다. 마케팅 세션이 10월부터 블로그에
도시 입주물량 편을 낸다(시범 청주). 도시 편은 지역 편과 같은 카테고리 '지역별 아파트 공급'에 실리고 제목 표지 '입주물량'으로만
가른다(close_published_issues.is_city_post — 발행 확인·순번과 같은 판정).
픽스처: 실제 발행 제목 모양 셋을 섞은 RSS 글 목록 — 지역 편('2027년 서울 아파트 공급물량 전망, …'), 도시 편('2027년 청주 아파트
입주물량, …'), 주간 글('[한국부동산원] 주간 아파트가격 동향(…) | …'), 그리고 남의 주소를 가진 도시 편 하나.

변이(각각 실제로 확인):
  · blog_feed.city_posts 가 is_city_post 대신 카테고리만 보면 → 지역 편이 실려 ③ 빨강.
  · city_posts 가 주소 검사(ours)를 빼면 → 남의 주소가 실려 ① 빨강.
  · make_indicator_pages.city_html 이 글이 없을 때도 머리를 구우면 → ② 빨강.
  · blog_feed.main 이 도시 목록을 쓰지 않으면(write(new, path)) → 배치 시험 빨강.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import blog_feed as BF  # noqa: E402
import close_published_issues as CP  # noqa: E402
import make_indicator_pages as I  # noqa: E402

HOME = BF.BLOG_HOME
REGION = CP.KIND_TO_CATEGORY['지역 공급']
WEEKLY = CP.KIND_TO_CATEGORY['주간 시세']


def _posts():
    d = datetime.date
    return [
        {'date': d(2026, 10, 7), 'cat': REGION, 'title': '2027년 청주 아파트 입주물량, 20개 단지 19,613세대가 몰린다',
         'url': HOME + '/2001'},
        {'date': d(2026, 10, 6), 'cat': REGION, 'title': '2027년 서울 아파트 공급물량 전망, 착공이 적정물량의 32%',
         'url': HOME + '/2000'},
        {'date': d(2026, 10, 3), 'cat': WEEKLY,
         'title': '[한국부동산원] 주간 아파트가격 동향(9월 넷째 주) | 경기가 가장 크게 올랐습니다', 'url': HOME + '/1999'},
        {'date': d(2026, 10, 1), 'cat': '지역별\xa0아파트 공급', 'title': '2027년 천안 아파트 입주물량, 아산과 함께 보면',
         'url': HOME + '/1998'},
        {'date': d(2026, 10, 8), 'cat': REGION, 'title': '2027년 대전 아파트 입주물량, 남의 글', 'url': 'https://example.com/x'},
    ]


def test_only_city_posts_newest_first():
    got = BF.city_posts(_posts())
    assert [p['url'] for p in got] == [HOME + '/2001', HOME + '/1998'], got           # ① 남의 주소·주간 글 빠짐
    assert all('공급물량 전망' not in p['title'] for p in got)                         # ③ 지역 편이 실리지 않는다
    assert got[0]['date'] == '2026-10-07' and BF.city_head(got[0]['title']) == '2027년 청주 아파트 입주물량'
    many = [dict(_posts()[0], date=datetime.date(2026, 1, k + 1), url=HOME + '/%d' % k) for k in range(10)]
    assert len(BF.city_posts(many)) == BF.CITY_MAX


def test_section_is_baked_only_when_there_are_posts():
    html = I.city_html(BF.city_posts(_posts()))
    assert html.count('<a href=') == 2 and I.CITY_H2 in html and "to:'city_post'" in html
    assert '네이버 블로그 10/7' in html and '2027년 청주 아파트 입주물량<span>' in html
    assert I.city_html([]) == ''                                                      # ② 빈 약속 금지


def test_batch_writes_the_city_list_and_pages_read_it_back(tmp_path):
    path = str(tmp_path / 'blog.json')
    assert BF.main(path=path, fetch=_posts) == 0
    doc = json.loads(open(path, encoding='utf-8').read())
    assert [p['url'] for p in doc['city']] == [HOME + '/2001', HOME + '/1998']
    assert [p['url'] for p in BF.read_city(path)] == [HOME + '/2001', HOME + '/1998']
    # 저장 파일이 손상돼 남의 주소·지역 편이 들어 있어도 페이지에 닿기 전에 걸러진다
    doc['city'].append({'date': '2026-10-09', 'title': '2027년 서울 아파트 공급물량 전망, x', 'url': HOME + '/1'})
    doc['city'].append({'date': '2026-10-09', 'title': '2027년 대전 아파트 입주물량, x', 'url': 'https://example.com/y'})
    open(path, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False))
    assert len(BF.read_city(path)) == 2
