# -*- coding: utf-8 -*-
"""허브 '지역으로 찾기' 칩은 글이 실제로 다루는 지역 단위에서 만든다(2026-11-19 대표 지시).

재현한 실제 상태(2026-11-14 발행 광역시 편 다섯, 2026-11-19 main): 대구 편 앞머리가 `city: [대구 수성구, 대구 달서구,
대구 북구]` 였다. 글은 대구 전체 편인데 허브에는 '대구 수성구·달서구·북구' 칩 셋이 섰고, 어느 것을 눌러도
/city/daegu-2027-moveins/ 한 편만 남았다(구별 글이 따로 있는 것처럼 읽혔다). 부산·대전·인천·울산 편도 같은 꼴이었다.
고친 방식: 광역시 전체 편의 앞머리를 `city: [대구]` 로 — 칩 하나('대구시')가 그 글을 가리키고, 구만 다룬 글
(`city: [대구 수성구]`)이 생기면 그 구 칩('수성구')이 저절로 시 칩 바로 뒤에 선다(city_groups 는 글의 city 에서 칩을 모은다).
도시 전체 편의 칩 글자는 '대구시'·'세종시'·'수원시'다(whole_city_names).

시험은 content/city/ 의 모든 원고를 돈다(특정 도시 하나를 박지 않는다 — 새 도시 편이 올라오면 그 글도 잰다).

변이(실제로 확인):
- content/city/daegu-2027-moveins.md 의 city 를 옛 구 셋으로 되돌리면 test_hub_city_chips_point_to_distinct_posts 와
  test_every_city_post_has_one_whole_city_chip_first 가 빨개진다(구 칩 셋이 같은 한 편을 가리키고, 구 칩이 시 전체 편을
  가리키고, 대구 편을 가리키는 칩이 '대구시' 하나가 아니다).
- make_content_pages._chip_label 의 도시 전체 분기(`return c + '시'`)를 지우면 test_every_city_post_has_one_whole_city_chip_first
  와 test_whole_city_chip_comes_first_and_reads_si 가 빨개진다.
- city_groups 정렬 열쇠의 구 표시(`' ' in c and not c.endswith(' 전체')`)를 뒤집으면 test_whole_city_chip_comes_first_and_reads_si
  와 test_every_city_post_has_one_whole_city_chip_first 가 빨개진다(구 칩이 시 칩 앞에 선다 — 실제 허브의 수원·용인·부천 줄).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import make_content_pages as MC    # noqa: E402

# 2026-11-14 발행 당시 대구 편 앞머리(region·city 그대로)
OLD_DAEGU = {'section': 'city', 'slug': 'daegu-2027-moveins', 'title': 't', 'region': '대구', 'topic': 'moveins',
             'city': ['대구 수성구', '대구 달서구', '대구 북구'], 'date': '2026-11-14', 'updated': '2026-11-14'}


def _post(slug, region, cities, section='city'):
    return {'section': section, 'slug': slug, 'title': 't', 'region': region, 'topic': 'moveins', 'city': cities,
            'date': '2026-11-19', 'updated': '2026-11-19'}


def _real():
    posts, _skipped = MC.collect()
    metas = [m for _sec, m, _body in posts]
    assert metas, '원고가 없다'
    return metas


def _selected(metas):
    """{칩 data-city: 그 칩이 남기는 글 slug 집합} — 허브 FILTER_JS 와 같은 규칙(이름 그대로이거나 앞말 + 빈칸)."""
    chips = re.findall(r'class="rchip" data-city="([^"]+)"', MC.city_chips(metas))
    return {c: frozenset(m['slug'] for m in metas if any(x == c or x.startswith(c + ' ') for x in MC.post_cities(m)))
            for c in chips}


def _rows(metas):
    """[(줄 이름, [(data-city, 칩 글자)…])] — 허브 칩 줄 그대로."""
    h = MC.city_chips(metas)
    return [(em, re.findall(r'data-city="([^"]+)">([^<]+)<', body))
            for em, body in re.findall(r'<div class="cf-g"(?: data-sido="[^"]*")?><em>([^<]*)</em><span class="cf-c">(.*?)</span></div>', h) if em]


def _whole_city(m):
    """시 전체 편 — 도시 입주물량 편(section city)으로, city 가 region 시 하나이거나 region 시의 구를 둘 이상 나열한 글
    (옛 광역시 편 꼴). 역세권·단지 글이 구 둘에 걸치는 것('고양 일산동구·일산서구' 킨텍스역)은 그 구들을 실제로 다루므로
    시 전체 편이 아니다."""
    if m.get('section') != 'city':
        return False
    cities = MC.post_cities(m)
    region = m.get('region')
    return cities == [region] or (len(cities) >= 2 and all(c.startswith('%s ' % region) for c in cities))


def _problems(metas):
    sel = _selected(metas)
    bad = []
    by_set = {}
    for c, s in sel.items():
        by_set.setdefault(s, []).append(c)
    for s, cs in by_set.items():
        if len(cs) > 1:
            bad.append('같은 글 %s 만 가리키는 칩이 %d개: %s' % (sorted(s), len(cs), cs))
    by_slug = {m['slug']: m for m in metas}
    for c, s in sel.items():
        if ' ' in c and not c.endswith(' 전체'):
            for slug in s:
                if _whole_city(by_slug[slug]):
                    bad.append('구 칩 %r 가 시 전체 글 %s 를 가리킨다' % (c, slug))
    return bad


def _order_problems(metas):
    """같은 시의 칩이 한 줄 안에서 붙어 있고, 도시 전체 칩이 그 시의 맨 앞인가."""
    whole = MC.whole_city_names(metas)
    bad = []
    for row, chips in _rows(metas):
        heads = [c.split(' ')[0] for c, _label in chips]
        for h in set(heads):
            at = [i for i, x in enumerate(heads) if x == h]
            if at != list(range(at[0], at[-1] + 1)):
                bad.append('%s 줄에서 %s 칩이 떨어져 있다: %s' % (row, h, [c for c, _ in chips]))
            if h in whole and chips[at[0]] != (h, h + '시'):
                bad.append('%s 줄에서 %s 의 첫 칩이 %r 다 — 도시 전체 칩(%s시)이 맨 앞이어야 한다' % (row, h, chips[at[0]], h))
    return bad


# ── 실제 원고 전체 ─────────────────────────────────────────────────────────
def test_hub_city_chips_point_to_distinct_posts():
    """실제 원고 전체로 만든 허브 칩: 같은 글 집합만 가리키는 칩이 둘 이상 없고, 구 칩이 시 전체 편을 가리키지 않는다."""
    assert _problems(_real()) == []


def test_every_city_post_has_one_whole_city_chip_first():
    """content/city/ 의 모든 글: 그 글을 가리키는 칩은 도시 전체 칩 하나('대구시'·'수원시')이고, 그 칩이 그 시의 맨 앞이며
    같은 시의 칩끼리 붙어 있다. 구 칩은 그 글을 가리키지 않는다."""
    metas = _real()
    city_posts = [m for m in metas if m['section'] == 'city']
    assert city_posts, 'content/city/ 원고가 없다'
    sel = _selected(metas)
    labels = {c: label for _row, chips in _rows(metas) for c, label in chips}
    for m in city_posts:
        assert MC.post_cities(m) == [m['region']], '%s: city 가 글이 다루는 시 하나(%s)가 아니다: %s' % (
            m['slug'], m['region'], MC.post_cities(m))
        hits = [c for c, got in sel.items() if m['slug'] in got and ' ' not in c]
        assert hits == [m['region']], '%s 를 가리키는 시 칩이 %s' % (m['slug'], hits)
        assert labels[m['region']] == m['region'] + '시', '%s 칩 글자가 %r' % (m['region'], labels[m['region']])
        gu = [c for c, got in sel.items() if m['slug'] in got and ' ' in c]
        assert gu == [], '%s 를 구 칩 %s 가 가리킨다' % (m['slug'], gu)
    assert _order_problems(metas) == []


# ── 픽스처 ─────────────────────────────────────────────────────────────────
def test_old_daegu_frontmatter_is_caught():
    """검사기가 결함을 잡는다 — 옛 대구 앞머리(구 셋)는 같은 한 편을 가리키는 구 칩 셋과 '구 칩 → 시 전체 편'으로 걸린다."""
    bad = _problems([OLD_DAEGU, _post('suwon-2027-moveins', '수원', ['수원'])])
    assert any('칩이 3개' in b for b in bad), bad
    assert any('구 칩' in b and 'daegu-2027-moveins' in b for b in bad), bad


def test_district_post_gets_its_own_chip_and_city_chip_shows_the_whole_post():
    """대구 전체 편(city: 대구)과 구만 다룬 글(city: 대구 수성구)이 함께 있으면: '대구' 칩이 서고 전체 편을 보여 주며,
    '대구 수성구' 칩은 그 구 글만 가리킨다. 구 글이 없으면 구 칩은 서지 않는다.
    옛 앞머리(구 셋) + 구 글이면 '대구 수성구' 칩이 시 전체 편까지 가리켜 실패로 잡힌다."""
    whole = _post('daegu-2027-moveins', '대구', ['대구'])
    gu = _post('daegu-suseong-2027-moveins', '대구', ['대구 수성구'])
    sel = _selected([whole, gu])
    assert set(sel) == {'대구', '대구 수성구'}, sel
    assert 'daegu-2027-moveins' in sel['대구']
    assert sel['대구 수성구'] == frozenset({'daegu-suseong-2027-moveins'})
    assert _problems([whole, gu]) == []
    assert set(_selected([whole])) == {'대구'}, '구 글이 없는데 구 칩이 섰다'
    bad = _problems([OLD_DAEGU, gu])
    assert any("구 칩 '대구 수성구'" in b and 'daegu-2027-moveins' in b for b in bad), bad


def test_whole_city_chip_comes_first_and_reads_si():
    """도시 전체 편 칩은 그 시의 맨 앞에 '대구시'·'세종시'·'수원시'로 서고, 같은 시의 구 칩('수성구')이 바로 뒤에 붙는다.
    도시 전체 편이 없는 시 칩(역세권 글의 '화성 동탄구', 구 칩이 둘 이상이라 세운 '고양')은 이름 그대로다.

    픽스처: 대구 전체 편에 구만 다룬 글 둘(수성구·달서구)이 생긴 앞날의 모습, 세종 편, 수원 편과 수원 영통구 단지 글,
    화성 동탄구 역세권 글, 고양 구 글 둘.
    """
    metas = [_post('daegu-2027-moveins', '대구', ['대구']),
             _post('daegu-suseong-2027-moveins', '대구', ['대구 수성구']),
             _post('daegu-dalseo-2027-moveins', '대구', ['대구 달서구']),
             _post('sejong-2027-moveins', '세종', ['세종']),
             _post('suwon-2027-moveins', '수원', ['수원']),
             _post('yeongtong-danji', '수원', ['수원 영통구'], 'danji'),
             _post('dongtan-gtx', '화성', ['화성 동탄구'], 'gtx'),
             _post('ilsan-a', '고양', ['고양 일산동구'], 'gtx'),
             _post('ilsan-b', '고양', ['고양 일산서구'], 'gtx')]
    rows = dict(_rows(metas))
    assert rows['대구'] == [('대구', '대구시'), ('대구 달서구', '달서구'), ('대구 수성구', '수성구')], rows['대구']
    assert rows['세종'] == [('세종', '세종시')]
    assert rows['경기'] == [('고양', '고양'), ('고양 일산동구', '일산동구'), ('고양 일산서구', '일산서구'),
                            ('수원', '수원시'), ('수원 영통구', '영통구'), ('화성 동탄구', '화성 동탄구')], rows['경기']
    assert _problems(metas) == [] and _order_problems(metas) == []
