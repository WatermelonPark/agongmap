# -*- coding: utf-8 -*-
"""발행 글의 값과 기준 시점은 **같은 원소**에서 나와야 한다.

2026-09-12 리뷰. `_series_last`가 값은 결측을 걸러낸 목록의 끝에서, 날짜는 원본
목록의 끝에서 뽑고 있었다. 꼬리가 None이면 지난달 값에 이번 달 날짜가 붙어
"전국 미분양은 6만 7천 호입니다(2026.07 기준)"처럼 **발행 글이 틀린 시점을 말한다.**

터지는 조건이 실재한다: merge_basic은 새 달 열을 전 지역 None으로 먼저 만들고
받아온 지역만 채운다. 전국이 아직 안 온 달에 정확히 이 모양이 된다. 발견 시점에는
네 계열 모두 꼬리 None이 0이라 겉으로는 멀쩡했다 — 그래서 주입해서 본다.

블로그가 사이트와 다른 숫자·시점을 말하면 '계산법을 공개한다'는 근거가 무너진다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402


def _st(tail):
    return {'미분양': {'dates': ['2026.05', '2026.06', '2026.07'],
                       'series': {'전국': [65000, 67464, tail]}}}


def test_point_matches_the_value_when_tail_is_missing():
    cur, prv, when = P._series_last(_st(None), '미분양')
    assert (cur, prv, when) == (67464, 65000, '2026.06'), \
        '꼬리가 비었는데 이번 달 날짜를 붙였다 — 발행 글이 틀린 시점을 말한다'


def test_normal_tail_still_reports_the_latest():
    cur, prv, when = P._series_last(_st(70000), '미분양')
    assert (cur, prv, when) == (70000, 67464, '2026.07')


def test_too_few_points_returns_nothing():
    """값이 하나뿐이면 '전월 대비'를 쓸 수 없다 — 섹션째 생략되어야 한다."""
    st = {'미분양': {'dates': ['2026.07'], 'series': {'전국': [70000]}}}
    assert P._series_last(st, '미분양') == (None, None, None)


def test_both_publishing_tools_say_the_same_region_count():
    """사이클 곳 수를 두 도구가 다르게 말하면 안 된다. 둘 다 정본을 읽는다."""
    from make_naver_post import CYCLE_SYNC_N as A
    assert A == T.CYCLE_SYNC_N
    descs = [m['desc'] for m in P.MORE_ROTATION if '개 시도' in m['desc']]
    assert descs, 'MORE_ROTATION 에서 곳 수 문장을 찾지 못했다'
    for s in descs:
        assert '%d개 시도' % T.CYCLE_SYNC_N in s, \
            '블로그 문구의 곳 수가 사이트와 다르다: %s' % s


def test_tile_counts_match_what_the_map_draws():
    """발행 문구의 시군구 수가 홈 지도의 실제 타일 수와 같아야 한다.

    2026-09-12: '187개 시군구'라고 적혀 있었으나 실제 타일은 182개(서울 25 + 157)였다.
    사이트에 187이라는 수가 어디에도 없어 대조할 데가 없었고 4주마다 발행됐다.

    기대값은 지도 재료(NATION_TILE.t — 시군구 지도 drawNationMap 이 그리는 칸)에서 따로 센다: 칸 가운데 SGG_QNAME 에 이름이
    있는 것이 시군구 타일이다(시도·부모 시 칸은 이름표에 없다). 예전 시험은 도구(_tile_counts)와 같은 SGG_QNAME 셈을 되풀이해
    지도에 없는 코드가 이름표에 들어와도 초록이었다(전수리뷰 #97).
    변이(실제로 확인): home-stats.js 의 SGG_QNAME 맨 앞에 지도에 없는 코드 "zz999":"가상시" 를 넣으면 빨개진다.
    픽스처: 실제 홈 소스(home_source) — NATION_TILE 212칸, SGG_QNAME 182곳(2026-09).
    """
    import json
    import re
    h = HS.home_source()
    q = json.loads(re.search(r'SGG_QNAME\s*=\s*(\{.*?\})\s*;', h, re.S).group(1))
    m = re.search(r'const NATION_TILE=(\{.*?\]\]\})', h, re.S)
    assert m, 'NATION_TILE(시군구 지도 칸)을 찾지 못했다'
    tile = json.loads(re.sub(r'([{,])\s*(\w+)\s*:', r'\1"\2":', m.group(1)))
    tiles = [r[0] for r in tile['t']]
    assert len(tiles) == len(set(tiles)), '지도 칸 코드가 겹친다'
    assert set(q) <= set(tiles), '지도에 없는 시군구 코드가 SGG_QNAME 에 있다: %s' % sorted(set(q) - set(tiles))
    drawn = [c for c in tiles if c in q]
    seoul = sum(1 for c in drawn if q[c].startswith('서울 '))
    assert seoul and len(drawn) > seoul, '지도 칸을 못 셌다'
    assert (P.SGG_N, P.SEOUL_N) == (len(drawn) - seoul, seoul)
    said = [m['desc'] for m in P.MORE_ROTATION if '시군구' in m['desc']]
    assert said, 'MORE_ROTATION 에서 시군구 문장을 찾지 못했다'
    for s in said:
        assert '%d곳' % P.SGG_N in s and '%d개 구' % P.SEOUL_N in s,             '발행 문구의 타일 수가 지도와 다르다: %s' % s
