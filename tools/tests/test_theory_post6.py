# -*- coding: utf-8 -*-
"""사이클 6편(입주 → 전세, 역전세)의 문장 전제 가드 — link6_values (2026-10-16).

본문은 다섯 가지를 문장으로 못 박는다: 서울은 효과가 확인되지 않는다, 수도권으로 묶으면 서울보다 강하다, 광역시가
도보다 강하다, 확인된 수도권 시도는 한 분기 뒤에 반응한다, 가장 강한 시도(대전)가 앞으로 입주가 적정물량을 넘는 곳이다.
재산정으로 하나라도 뒤집히면 초안을 만들지 않아야 한다(3편 check_sync_claims 와 같은 원칙).

픽스처: 저장소의 실제 /cycle/ 정본(P.cycle_d())과 ADV. 그대로 두면 통과하고, 한 항목씩 뒤집은 사본은 멈춰야 한다.
무엇을 깨뜨리면 빨개지나(실제로 확인): link6_values 에서 서울 유의 검사를 지우면 첫째 뒤집기 시험이, 가장 강한 시도 검사를
지우면 둘째가 빨개진다. link6_values 의 Link4ClaimError → SystemExit 변환을 지우면 마지막 시험이 빨개진다.

데이터가 앞으로 가도 초록이어야 한다(게이트 시험): 5편 단정(theory_link4 — 앞으로 입주가 적정물량을 넘는 시도 목록 등)은
분기마다 바뀔 수 있다. 2026-10-17 다음 분기 전진 시험에서 fut_high 가 {'대전','충남'} 밖으로 넓어져 link4_numbers 가
Link4ClaimError 를 던졌고, 이 파일과 test_home_entry 가 그 예외로 빨개져 그날 배치 게이트를 멈출 뻔했다. 그래서 실데이터
시험은 5편 단정이 깨진 회차면 6편 초안이 SystemExit 로 멈추는지만 보고(멈추는 것이 맞는 동작이다), 뒤집기 시험은 5편 숫자를
'가장 강한 시도가 과잉 목록에 있다'는 고정 값으로 바꿔 끼워 자기가 뒤집은 전제 하나만 본다.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_theory_post as T  # noqa: E402


@pytest.fixture(scope='module')
def real():
    adv, sts = T.M.load()
    return T.P.cycle_d(), adv, sts


def _n4_ok(D):
    """5편 숫자 대역 — 지금 /cycle/ 정본에서 가장 강한 시도가 앞으로 입주 과잉 목록에 있는 상태(전제 ⑤가 서는 쪽)."""
    top = sorted(D['link6_regional'], key=lambda x: x['r'])[0]['region']
    return lambda adv, sts: {'fut_high_names': top}


def test_real_data_passes_and_fills_every_slot(real):
    D, adv, sts = real
    import theory_link4 as L4
    try:
        L4.link4_numbers(adv, sts)
    except L4.Link4ClaimError:
        # 5편 단정이 깨진 회차 — 6편도 멈춰야 한다(그 단정의 정합은 5편 가드·test_theory_post5 가 본다)
        with pytest.raises(SystemExit):
            T.link6_values(D, adv, sts)
        return
    v = T.link6_values(D, adv, sts)
    post = next(p for p in T.POSTS if p['n'] == 6)
    import re
    for k in set(re.findall(r'%\((\w+)\)s', post['body'])) - {'exp', 'zone', 'cycle', 'link'}:
        assert k in v, k


def test_seoul_turning_significant_stops_the_draft(real, monkeypatch):
    D, adv, sts = real
    import theory_link4 as L4
    monkeypatch.setattr(L4, 'link4_numbers', _n4_ok(D))
    D2 = copy.deepcopy(D)
    next(x for x in D2['link6_regional'] if x['region'] == '서울')['sig'] = True
    with pytest.raises(SystemExit):
        T.link6_values(D2, adv, sts)


def test_strongest_region_outside_the_oversupply_list_stops_the_draft(real, monkeypatch):
    D, adv, sts = real
    import theory_link4 as L4
    monkeypatch.setattr(L4, 'link4_numbers', _n4_ok(D))
    D2 = copy.deepcopy(D)
    x = next(x for x in D2['link6_regional'] if x['region'] == '서울')
    x['r'] = -0.9                      # 서울이 가장 강해진 가상 재산정(서울은 입주 과잉 지역이 아니다)
    with pytest.raises(SystemExit):
        T.link6_values(D2, adv, sts)


def test_link4_claim_break_stops_the_draft_instead_of_raising(real, monkeypatch):
    """5편 단정이 깨지면 6편은 SystemExit 로 멈춘다 — 초안 생성 가드(SystemExit)를 거르는 게이트 시험이 예외로 죽지 않게."""
    D, adv, sts = real
    import theory_link4 as L4

    def boom(adv, sts):
        raise L4.Link4ClaimError('fut_high: 목록이 바뀌었다')
    monkeypatch.setattr(L4, 'link4_numbers', boom)
    with pytest.raises(SystemExit) as e:
        T.link6_values(D, adv, sts)
    assert '6편을 만들 수 없다' in str(e.value)
