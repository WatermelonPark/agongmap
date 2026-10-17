# -*- coding: utf-8 -*-
"""지역 편 지정·대기 지역 옵션(pick_zone 의 force·pending, --zone·--pending-zones) — 2026-10-17 주간 묶음용.

주간 묶음은 한 주에 지역 편을 두 편 쓴다. 첫 편은 예약만 걸리고 아직 RSS 에 없으므로, 그대로 두면 둘째 편도 같은
지역을 고른다. pending 은 그 지역을 이번 바퀴에 다룬 것으로 세고, force 는 지역을 직접 고른다(검색 이름도 받는다).

픽스처: test_post_rotation 과 같은 꼴의 rows(z·tot 두 키)와 published 사전. 실제 상황(10-17): 서울·대구 발행, 경남 예약.
무엇을 깨뜨리면 빨개지나(실제로 확인): pending 을 seen 에 넣는 줄을 지우면 대기 시험이, force 로 pick 을 바꾸는 줄을
지우면 지정 시험이, _zone_name 의 검색 이름 되돌리기를 지우면 검색 이름 시험이 빨개진다.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402

ROWS = [dict(z=z, tot=t) for z, t in (('서울', 300000), ('경기', 50000), ('대구', 47000), ('경남', 72000),
                                      ('전남광주', 52000), ('부산', 43000))]


@pytest.fixture(autouse=True)
def no_state(monkeypatch, tmp_path):
    monkeypatch.setattr(P, 'STATE', str(tmp_path / 'rot.json'))
    monkeypatch.setattr(P, 'PRIORITY', [])


def _pub(*names):
    return {n: {'u-' + n} for n in names}


def test_pending_zone_is_not_picked_again():
    first = P.pick_zone(ROWS, published=_pub('서울', '대구'))[0]['z']
    again = P.pick_zone(ROWS, published=_pub('서울', '대구'), pending=[first])[0]['z']
    assert again != first and again not in ('서울', '대구')


def test_force_picks_that_zone():
    assert P.pick_zone(ROWS, published=_pub('서울'), force='부산')[0]['z'] == '부산'


def test_force_accepts_the_search_name():
    assert P.pick_zone(ROWS, published={}, force='광주·전남')[0]['z'] == '전남광주'
    with pytest.raises(SystemExit):
        P.pick_zone(ROWS, published={}, force='없는곳')
