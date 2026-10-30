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
  · main 이 merge_city 대신 city_posts(posts)만 쓰면(RSS 창 밖 글을 버림), merge_city 가 창 안의 지워진 글을 남기면 → 이어 두기 시험 빨강.
  · city_head 가 첫 쉼표에서 자르면('1,234세대' 제목) → 머리 시험 빨강.
  · city_html 날짜를 SZ.day_text(연도 없음)로 되돌리면 → 칸 시험 빨강.
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


def test_the_section_points_at_our_own_city_posts_not_the_blog():
    """/moveins/ 도시 칸은 **사이트의 /city/ 글**을 가리킨다 — 네이버 글이 아니다(총괄 결정 2026-10-30).

    왜: 네이버 발행이 끝나(10-26·10-29 대표 결정) 그 칸은 묵은 글만 가리켰다. 같은 주제의 글이 사이트에
    생겨(/city/ 도시 입주물량 편) 그쪽으로 돌렸다. 자리는 지표 생성기가 내고 내용은 콘텐츠 생성기가 채운다.

    무엇을 바꾸면 빨개지나: city_html 이 다시 블로그 링크를 구우면, 콘텐츠 생성기가 /city/ 아닌 섹션을
      싣거나 최신 글이 아닌 것을 고르면, 글이 없는데도 칸을 채우면.
    픽스처: 손으로 지은 글 메타 셋(도시 편 둘·다른 섹션 하나)과 지표 생성기가 낸 빈 자리.
    """
    import make_content_pages as MC
    slot = I.city_html()
    assert MC.MOVEINS_START in slot and MC.MOVEINS_END in slot, '지표 생성기가 낸 자리에 표식이 없다'
    assert 'blog.naver' not in slot and '<a href=' not in slot, '자리에 내용이 들어 있다 — 안쪽은 콘텐츠 생성기 몫이다'

    def meta(slug, updated, sec='city'):
        return {'section': sec, 'slug': slug, 'updated': updated, 'date': updated,
                'title': '%s 입주물량' % slug}

    body = MC.moveins_cities_html([meta('old-city', '2026-10-01'), meta('new-city', '2026-10-29'),
                                   meta('danji-one', '2026-10-30', sec='danji')])
    assert 'blog.naver' not in body, '칸에 네이버 링크가 되살아났다'
    assert body.index('/city/new-city/') < body.index('/city/old-city/'), '최신 글이 위가 아니다'
    assert '/danji/' not in body, '도시 칸에 다른 섹션 글이 실렸다'
    assert MC.MOVEINS_H2 in body
    assert MC.moveins_cities_html([meta('danji-one', '2026-10-30', sec='danji')]) == ''   # 빈 약속 금지


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


def test_head_keeps_thousands_separators():
    assert BF.city_head('1,234세대 몰리는 2027년 청주 아파트 입주물량, 정리') == '1,234세대 몰리는 2027년 청주 아파트 입주물량'
    assert BF.city_head('2027년 청주 아파트 입주물량,20개 단지') == '2027년 청주 아파트 입주물량,20개 단지'


def test_older_city_posts_survive_the_rss_window_and_deleted_ones_do_not(tmp_path):
    """재현하는 실제 상태: 네이버 RSS 는 최근 글 몇십 개만 준다. 주간·지역·이론 글이 쌓이면 지난 도시 편이 RSS 창 밖으로 밀린다.
    픽스처: 저장 목록에 창보다 오래된 도시 편(9/1)과 창 안인데 RSS 에 없는(지워진) 도시 편(10/2), RSS 에는 10/1~10/8 글."""
    path = str(tmp_path / 'blog.json')
    assert BF.main(path=path, fetch=_posts) == 0
    doc = json.loads(open(path, encoding='utf-8').read())
    doc['city'] += [{'date': '2026-09-01', 'title': '2027년 청주 아파트 입주물량, 지난 글', 'url': HOME + '/1900'},
                    {'date': '2026-10-02', 'title': '2027년 아산 아파트 입주물량, 지운 글', 'url': HOME + '/1997'}]
    open(path, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False))
    assert BF.main(path=path, fetch=_posts) == 0
    got = [p['url'] for p in BF.read_city(path)]
    assert got == [HOME + '/2001', HOME + '/1998', HOME + '/1900'], got
