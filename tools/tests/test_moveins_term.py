# -*- coding: utf-8 -*-
"""/moveins/ 의 제목·설명이 '착공 기준 추정'을 드러낸다 — 홈 마케팅 검수 C9(SEO-5), 2026-09-27.

재현하는 실제 상태(2026-09-26 검수): /moveins/ title 은 '아파트 입주물량 — 2026·2027 전국 시도별 입주 예정',
description 은 '…2026년 전국 N세대, 2027년 M세대 예정'이었다. 준공 실적 뒤의 분기는 착공 실적을 3년 밀어 추정한
값인데, 검색 결과에서는 분양이 확정된 단지 목록처럼 읽혔다. 블로그는 추정치를 입주물량이라 부르지 않는다(로컬 운영
메모) — 사이트는 검색 수요가 있는 '입주물량'을 머리에 유지하고, 이 표시로 그 차이를 메운다.

픽스처: 저장소의 실제 ADV.occupancy, 그리고 분기 라벨만 1년 민 것(데이터가 앞으로 가도 표시가 남는지).
"""
import copy
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_sido_pages as M  # noqa: E402


def _shift(adv, years):
    a = copy.deepcopy(adv)
    for r in a['occupancy']['rows']:
        y, q = re.match(r'^(\d{4})(Q[1-4])$', r['p']).groups()
        r['p'] = '%d%s' % (int(y) + years, q)
    return a


def _meta(html, attr, key):
    m = re.search(r'<meta %s="%s" content="([^"]*)"' % (attr, re.escape(key)), html)
    assert m, '%s=%s 메타를 못 찾았다' % (attr, key)
    return m.group(1)


@pytest.mark.parametrize('shift', [0, 1])
def test_moveins_title_and_description_say_start_based_estimate(shift):
    """title·meta description·og:title·og:description·JSON-LD description 모두에 '입주물량'과 MOVEINS_EST 가 있다.
    title 은 '아파트 입주물량' 으로 시작한다(검색어가 머리에).

    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): title 에서 MOVEINS_EST 를 빼 옛 '시도별 입주 예정' 으로 되돌리면,
    desc 에서 '준공 실적 이후 분기는 …으로' 구를 빼면(description·og:description·LD 가 함께), og 제목에서 '(… 포함)'
    을 빼면 빨개진다.
    """
    adv, _ = M.load()
    html, _ = I.build_moveins(_shift(adv, shift) if shift else adv)
    est = I.MOVEINS_EST
    assert est == '착공 기준 추정'
    title = re.search(r'<title>([^<]*)</title>', html).group(1)
    assert title.startswith('아파트 입주물량'), title
    ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    got = {'title': title,
           'description': _meta(html, 'name', 'description'),
           'og:title': _meta(html, 'property', 'og:title'),
           'og:description': _meta(html, 'property', 'og:description'),
           'ld': ld[0]['description']}
    bad = {k: v for k, v in got.items() if est not in v or '입주물량' not in v}
    assert not bad, "'%s' 표시가 빠졌다: %s" % (est, bad)
