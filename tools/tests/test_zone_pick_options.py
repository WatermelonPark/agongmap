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


def test_pending_placeholder_is_not_cached_after_commit():
    """대기 자리표('pending:')는 이번 실행에서만 세고 순회 캐시(STATE)에 남지 않는다(전수리뷰 BL1-5).

    실제 상황(10-17): 서울·대구 발행, 경남 예약 상태에서 --pending-zones 경남으로 둘째 편을 저장(commit)했다. 경남이
    발행된 뒤에도 캐시의 'pending:경남' 이 남으면 경남이 두 편으로 세어져 한 바퀴 뒤 seq 가 한 칸 밀리고, 둘째 바퀴에서
    경남을 건너뛴다. 이미 오염된 캐시({'경남': ['pending:경남']})를 읽는 갈래도 함께 본다.
    무엇을 깨뜨리면 빨개지나(실제로 확인): pick_zone 에서 STATE 를 읽은 뒤 'pending:' 을 버리는 줄을 지우면 오염 캐시
    갈래가, pend 를 seen 에 넣어(seen.setdefault(z, set()).add('pending:'+z)) commit 이 쓰게 하면 커밋 갈래가 빨개진다.
    """
    import json
    names = [r['z'] for r in ROWS]
    pick, seq, total, commit = P.pick_zone(ROWS, published=_pub('서울', '대구'), pending=['경남'])
    assert pick['z'] not in ('서울', '대구', '경남') and seq == 4
    commit()
    st = json.load(open(P.STATE, encoding='utf-8'))
    assert not any(u.startswith('pending:') for v in st['posts'].values() for u in v)
    # 한 바퀴를 다 발행했다 → 다음은 둘째 바퀴 첫 편(seq = total + 1)
    pick, seq, total, _ = P.pick_zone(ROWS, published=_pub(*names))
    assert seq == total + 1
    # 둘째 바퀴: 경남만 빼고 모두 두 편 → 경남을 건너뛰지 않는다
    two = {n: {'u-' + n, 'v-' + n} for n in names if n != '경남'}
    two['경남'] = {'u-경남'}
    pick, seq, total, _ = P.pick_zone(ROWS, published=two)
    assert pick['z'] == '경남' and seq == 2 * total
    # 10-17 묶음 실행이 이미 써 둔 오염 캐시도 풀린다
    with open(P.STATE, 'w', encoding='utf-8') as f:
        json.dump({'posts': {'경남': ['pending:경남'], '서울': ['u-서울']}}, f, ensure_ascii=False)
    pick, seq, total, _ = P.pick_zone(ROWS, published=_pub(*names))
    assert seq == total + 1
