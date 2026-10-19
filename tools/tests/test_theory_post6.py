# -*- coding: utf-8 -*-
"""사이클 6편(입주 → 전세, 역전세)의 문장 전제 가드 — link6_values (2026-10-16).

본문이 문장으로 못 박는 것: ① 서울은 효과가 확인되지 않는다, ② 수도권으로 묶으면 서울보다 강하다, ③ 광역시가 도보다 강하다,
④ 확인된 수도권 시도는 한 분기 뒤에 반응한다, ⑤ 가장 강한 시도(대전)가 앞으로 입주가 적정물량을 넘는 곳이다, ⑥ 그런 시도가 있다,
⑦ 적정물량의 3분의 1에도 못 미치는 시도가 있다('가장 적은 곳은 …'), ⑧ 못 미치는 시도가 대부분이다. 하나라도 뒤집히면 초안을
만들지 않는다(3편 check_sync_claims 와 같은 원칙).

대표 결정 2026-10-18 D1: 지금 데이터가 발행본의 전제와 어긋나면 **초안 생성만** SystemExit 로 멈추고 게이트는 막지 않는다(그 상태는
batch_notes 의 ℹ️ 줄이 알린다). 그래서 실데이터 시험은 멈춤 갈래도 받고(멈춤 문구가 6편을 가리키는지 본다), 자리 채움·뒤집기 시험은
모든 전제가 서는 고정 스냅숏(SNAP)에서 돈다 — 데이터 연도·분기와 무관하게 늘 돈다(전수리뷰 T3-14: 예전 자리 채움 대조는 실데이터의
5편 연도 가드에 걸려 2027년 자료부터 영영 꺼졌다). 6편은 5편 단정(link4_numbers)에 묶이지 않는다(전수리뷰 BL2-4).

픽스처: SNAP 은 2026-10-18 저장소의 실제 값을 옮겨 적은 것이다 — /cycle/ D.link6_regional 14곳·D.prose 의 고리⑥ 칸, ADV.sido 판정
(16개 시도 + 집계 3행의 앞으로 3년 들어올 물량·적정물량·판정 split 문장, 판정 창 12분기). 실데이터 시험만 저장소 파일을 읽는다.
무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - link6_values 의 서울 유의 검사(①)를 지우면 → test_seoul_turning_significant_stops_the_draft
  - 가장 강한 시도 검사(⑤)를 지우면 → test_strongest_region_outside_the_oversupply_list_stops_the_draft
  - ⑦·⑧ 검사를 지우면 → test_no_region_below_a_third_stops_the_draft·test_most_regions_not_short_stops_the_draft
  - link6_values 가 다시 link4_numbers 를 부르면 → test_a_fifth_post_only_claim_does_not_stop_the_sixth
  - fut_lists 의 Link4ClaimError → SystemExit 변환을 지우면 → test_unreadable_judgement_cells_stop_the_draft_instead_of_raising
  - fut_lists 에 이름 함수(name=)를 넘기지 않으면 → test_region_names_follow_the_blog_display_name
  - link6_values 가 돌려주는 칸 하나(예: fut_low)를 빼면 → test_snapshot_passes_and_fills_every_slot
"""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_theory_post as T  # noqa: E402
import theory_link4 as L4  # noqa: E402

POST = next(p for p in T.POSTS if p['n'] == 6)
SLOTS = set(re.findall(r'%\((\w+)\)s', POST['body'])) - {'exp', 'zone', 'cycle', 'link'}

# /cycle/ D.link6_regional — (지역, 상관 r, 시차, 권역, 유의) — 2026-10-18
_L6 = [('대전', -0.48, 0, '지방', True), ('인천', -0.45, 1, '수도권', True), ('대구', -0.41, 1, '지방', True),
       ('충남', -0.40, 0, '지방', True), ('전북', -0.39, 1, '지방', True), ('경기', -0.35, 1, '수도권', True),
       ('부산', -0.32, 1, '지방', True), ('경북', -0.29, 0, '지방', True), ('강원', -0.29, 0, '지방', True),
       ('전남광주', -0.28, 0, '지방', True), ('울산', -0.25, 1, '지방', True), ('경남', -0.24, 0, '지방', False),
       ('충북', -0.17, 0, '지방', False), ('서울', -0.10, 1, '수도권', False)]
_PROSE = {'l6_total': '14', 'l6_sig': '11', 'l6_metro': '−0.38', 'l6_prov': '−0.30', 'seoul_l6': '−0.10',
          'sudo_l6': '−0.40', 'rate_r': '−0.57'}
# ADV.sido 판정 — (지역, 앞으로 3년 들어올 물량, 적정물량, 판정 문장의 퍼센트, 집계 여부) — 2026-10-18
_ZONES = [('전국', 714127, 1140000, 63, True), ('수도권', 408895, 600000, 68, True), ('지방', 305232, 540000, 57, True),
          ('서울', 72786, 224400, 32, False), ('경기', 269529, 306000, 88, False), ('인천', 66579, 69600, 96, False),
          ('부산', 47172, 72000, 66, False), ('대구', 10122, 60000, 17, False), ('대전', 30352, 26400, 115, False),
          ('세종', 6622, 7200, 92, False), ('울산', 11750, 24000, 49, False), ('전남광주', 38055, 68400, 56, False),
          ('충남', 47017, 42000, 112, False), ('충북', 25230, 32400, 78, False), ('경남', 34335, 72000, 48, False),
          ('경북', 19181, 60000, 32, False), ('전북', 16727, 30000, 56, False), ('강원', 15282, 31200, 49, False),
          ('제주', 3388, 14400, 24, False)]


def _snap():
    """모든 전제가 서는 고정 스냅숏 (D, adv) — 시험마다 새 사본."""
    D = {'prose': dict(_PROSE),
         'link6_regional': [dict(region=r, r=v, lag=lag, zone=zn, sig=s) for r, v, lag, zn, s in _L6]}
    zones = [dict(z=z, fut=f, need=n, agg=a, split=dict(rows=[['지난 4년', '적정물량보다 덜 지었습니다'],
                                                         ['앞으로 3년', '적정물량의 %d%%가 들어옵니다' % p]]))
             for z, f, n, p, a in _ZONES]
    return D, {'sido': {'H': 12, 'zones': zones}}


def _zone(adv, name):
    return next(z for z in adv['sido']['zones'] if z['z'] == name)


def _stops(D, adv, why):
    with pytest.raises(SystemExit) as e:
        T.link6_values(D, adv)
    msg = str(e.value)
    assert msg.startswith('6편을 만들 수 없다') and why in msg, msg
    assert '5편' not in msg, '6편 멈춤이 5편 문장을 가리킨다: %s' % msg


def test_snapshot_passes_and_fills_every_slot():
    """전제가 모두 서는 스냅숏에서는 본문의 자리 표시자를 하나도 빠뜨리지 않고 채운다 — 데이터 연도와 무관하게 늘 돈다(T3-14)."""
    D, adv = _snap()
    v = T.link6_values(D, adv)
    assert SLOTS and SLOTS <= set(v), sorted(SLOTS - set(v))
    assert v['fut_high'] == '대전 115%, 충남 112%' and v['fut_high_names'] == '대전·충남', v
    assert v['fut_low'] == '대구 17%, 제주 24%, 경북 32%, 서울 32%' and v['win_y'] == '3', v


def test_real_data_passes_or_stops_with_a_named_premise():
    """저장소 실데이터: 전제가 서면 모든 자리를 채우고, 깨진 회차면 6편 문장의 전제를 이름으로 대며 멈춘다(D1 — 게이트는 막지 않는다).
    그 밖의 예외(TypeError 등)는 코드 결함이라 그대로 빨갛다."""
    adv, _ = T.M.load()
    D = T.P.cycle_d()
    try:
        v = T.link6_values(D, adv)
    except SystemExit as e:
        msg = str(e.value)
        assert msg.startswith('6편을 만들 수 없다 — ') and len(msg) > len('6편을 만들 수 없다 — ') + 5, msg
        assert '5편' not in msg, msg
        return
    assert SLOTS <= set(v), sorted(SLOTS - set(v))


def test_seoul_turning_significant_stops_the_draft():
    D, adv = _snap()
    next(x for x in D['link6_regional'] if x['region'] == '서울')['sig'] = True
    _stops(D, adv, '서울이 유의로 나온다')


def test_strongest_region_outside_the_oversupply_list_stops_the_draft():
    D, adv = _snap()
    next(x for x in D['link6_regional'] if x['region'] == '서울')['r'] = -0.9   # 서울이 가장 강해진 가상 재산정
    _stops(D, adv, '가장 강한 시도(서울)')


def test_no_oversupply_region_stops_the_draft():
    D, adv = _snap()
    for z in adv['sido']['zones']:
        z['fut'] = min(z['fut'], z['need'] * 0.9)      # 적정물량을 넘는 시도가 없다
    _stops(D, adv, '앞으로 입주가 적정물량을 넘는 시도가 없다')


def test_no_region_below_a_third_stops_the_draft():
    D, adv = _snap()
    for z in adv['sido']['zones']:
        z['fut'] = max(z['fut'], z['need'] * 0.4)      # '가장 적은 곳은 …' 목록이 빈다
    _stops(D, adv, '3분의 1에도 못 미치는 시도가 없다')


def test_most_regions_not_short_stops_the_draft():
    D, adv = _snap()
    for name in ('경기', '인천', '세종', '충북', '부산', '전남광주'):   # 적정물량을 넘는 곳이 2곳 → 8곳(못 미치는 곳 8/16)
        z = _zone(adv, name)
        z['fut'] = z['need'] * 1.01
    _stops(D, adv, '대부분이 아니다')


def test_a_fifth_post_only_claim_does_not_stop_the_sixth(monkeypatch):
    """5편 단정이 깨진 회차(예: 2026년 착공 증가율·2027년 자료의 연도 가드)에도 6편은 제 전제만 보고 나온다(전수리뷰 BL2-4)."""
    def boom(adv, sts):
        raise L4.Link4ClaimError('st_ytd_up: 5편만의 단정이 깨졌다')
    monkeypatch.setattr(L4, 'link4_numbers', boom)
    D, adv = _snap()
    assert SLOTS <= set(T.link6_values(D, adv))


def test_unreadable_judgement_cells_stop_the_draft_instead_of_raising():
    """판정 칸을 못 읽으면(키가 바뀌었다·적정물량이 0) 날 예외가 아니라 SystemExit 로 멈춘다 — 초안 가드를 SystemExit 로 거르는
    게이트 시험(test_home_entry 의 _all_drafts)이 죽지 않게. 문장 탓이 아니라고 안내한다."""
    D, adv = _snap()
    _zone(adv, '대구')['need'] = 0
    with pytest.raises(SystemExit) as e:
        T.link6_values(D, adv)
    assert '6편을 만들 수 없다' in str(e.value) and '문장 탓이 아니다' in str(e.value), str(e.value)


def test_region_names_follow_the_blog_display_name():
    """앞으로 입주 목록의 지역 이름도 같은 글의 다른 지역 이름(l6_top1 등)과 같은 블로그 검색 표기(SEARCH_NAME — 화면 이름 정본
    SZ.DISPLAY_NAME 에 '세종시'를 더한 것)로 나간다. 키('전남광주')가 글에 새지 않는다.
    픽스처: 스냅숏에서 세종이 가장 강하고(고리⑥ 14곳에 없는 세종을 한 줄 더한 가상 재산정) 적정물량의 130%가, 전남광주에 120%가
    들어오는 상태로 바꾼 것."""
    D, adv = _snap()
    assert not any(x['region'] == '세종' for x in D['link6_regional'])
    D['link6_regional'].append(dict(region='세종', r=-0.9, lag=0, zone='지방', sig=True))
    for name, pct in (('세종', 130), ('전남광주', 120)):
        z = _zone(adv, name)
        z['fut'] = z['need'] * pct / 100
        z['split']['rows'][1][1] = '적정물량의 %d%%가 들어옵니다' % pct
    v = T.link6_values(D, adv)
    assert v['l6_top1'] == '세종시는' and v['fut_high_names'].startswith('세종시·'), v
    assert v['fut_high'].startswith('세종시 130%, 광주·전남 120%'), v
    shown = ' '.join(v[k] for k in ('fut_high', 'fut_high_names', 'fut_low', 'l6_top1', 'l6_top3'))
    assert '전남광주' not in shown, shown
