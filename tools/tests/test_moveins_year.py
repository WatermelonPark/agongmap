# -*- coding: utf-8 -*-
"""/moveins/ 의 머리 연도가 데이터를 따라가는지 본다(2026-09-23 전체 점검).

생성기가 표의 세 해('2025','2026','2027')와 제목·설명·og 제목의 '2026년 전국', 정렬 기준 '2026'을 문자로
박아 두고 있었다. 2027년이 와도 페이지가 계속 2026년을 머리로 내건다. 규칙은 '마지막 실적 분기의 해 =
머리 연도(Y)', 표는 Y−1·Y·Y+1 이다(make_indicator_pages.build_moveins 주석).

깨뜨리면 빨개지는 것: build_moveins 의 `years` 를 옛 `['2025', '2026', '2027']` 로, 또는 제목·og 제목을 옛
'2026' 문자로 되돌리면 test_headline_moves_with_the_latest_actual_quarter 가 빨개진다(둘 다 변이로 확인).
픽스처: 저장소의 실제 ADV.occupancy 를 분기 라벨만 4분기(1년) 뒤로 민 것 — 1년 뒤 같은 모양의 데이터가
들어온 상태(마지막 실적 2027Q2, 예정 2029Q2까지 → 2030Q2까지)를 재현한다. 값은 건드리지 않는다.
"""
import copy
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_sido_pages as M  # noqa: E402


def _shift(adv, years):
    a = copy.deepcopy(adv)
    for r in a['occupancy']['rows']:
        m = re.match(r'^(\d{4})(Q[1-4])$', r['p'])
        r['p'] = '%d%s' % (int(m.group(1)) + years, m.group(2))
    return a


def _heads(html):
    return re.findall(r'<th data-num>([^<]+)</th>', html)


def test_headline_is_the_year_of_the_latest_actual_quarter():
    """오늘 데이터에서 머리 연도가 마지막 실적 분기의 해(2026Q2 → 2026)다.

    깨뜨리면 빨개지는 것: 머리 연도를 마지막 **예정** 분기의 해(`rows[-1]['p']`, 2029)에서 읽게 바꾸면
    빨개진다(변이로 확인). 픽스처: 저장소의 실제 ADV.occupancy 그대로.
    """
    adv, _ = M.load()
    rows = adv['occupancy']['rows']
    y = int([r['p'] for r in rows if not r.get('e')][-1][:4])
    html, _ = I.build_moveins(adv)
    assert _heads(html)[:3] == [str(y - 1), str(y), str(y + 1)]
    assert '%d·%d 전국' % (y, y + 1) in html
    assert '아파트 입주물량 — %d년 전국' % y in html


def test_headline_moves_with_the_latest_actual_quarter():
    """데이터가 1년 흐르면 머리 연도·표의 세 해·제목·og 제목·본문 연도가 함께 1년 넘어간다.

    깨뜨리면 빨개지는 것: `years` 를 옛 문자 목록으로, 또는 og 제목을 옛 '2026년 전국'으로 되돌리면
    빨개진다(각각 변이로 확인). 픽스처: 실제 데이터의 분기 라벨을 4분기 민 것(모듈 독스트링).
    """
    adv, _ = M.load()
    y = int([r['p'] for r in adv['occupancy']['rows'] if not r.get('e')][-1][:4])
    html, _ = I.build_moveins(_shift(adv, 1))
    ny = y + 1
    assert _heads(html)[:3] == [str(ny - 1), str(ny), str(ny + 1)], _heads(html)
    assert '%d 충족률' % ny in html
    assert '<title>아파트 입주물량 — %d·%d 전국' % (ny, ny + 1) in html
    assert 'content="아파트 입주물량 — %d년 전국' % ny in html
    assert '%d년 전국 입주물량' % ny in html
    assert '%d년 적정수요를 가장 덜 채운 곳' % ny in html
    assert '%d년 전국' % y not in html, '한 해 지난 데이터인데 옛 머리 연도(%d년 전국)가 남았다' % y
