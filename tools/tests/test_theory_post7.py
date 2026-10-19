# -*- coding: utf-8 -*-
"""사이클 7편(금리와 집값)의 문장 전제 가드 — link7_values (2026-10-16).

본문이 못 박는 것: ① 금리 바닥 뒤 1년 매매 상승이 전세의 3배를 넘는다, ② 고금리 국면에서 매매가 전세보다 먼저·크게 꺾였다,
③ 최근 금리가 오르는 동안 매매·전세가 함께 올랐다, ④ 금리–매매 상관이 음수다. 하나라도 뒤집히면 초안을 만들지 않아야 한다.

대표 결정 2026-10-18 D1: /cycle/ 금리 오버레이는 배치가 매일 다시 굽고, ③은 시장 국면에 대한 단정이라(지난 39분기 중 21분기에
거짓) 금리 인하기에 깨진다 — 그때 멈추는 것은 **초안 생성만**이고 게이트는 막지 않는다(그 상태는 batch_notes 의 ℹ️ 줄이 알린다,
전수리뷰 BL2-2·T3-4·X1-1). 그래서 실데이터 시험은 멈춤 갈래도 받고, 자리 채움·뒤집기 시험은 네 전제가 모두 서는 고정 스냅숏(SNAP)에서
돈다 — 실데이터에 기대면 ③이 깨진 국면에서 뒤집기 시험이 다른 이유의 SystemExit 로 헛통과한다.

픽스처: SNAP 은 2026-10-18 저장소 /cycle/ D.rate_overlay(수도권 분기 매매·전세 지수, CD금리 분기 평균, 2015Q1~2026Q3)와
D.prose 의 rate_r·rate_n 을 옮겨 적은 것이다. 끝 분기 전세 빈칸 시험은 매매가 새 분기 첫 달(잠정)을 받고 전세가 한 달 늦은 회차
(2026-08-28~09-27 에 실제로 /cycle/ 끝 칸이 [137.5, None] 이었다)를 SNAP 끝에 한 분기 덧붙여 재현한다.
무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - link7_values 의 '세 값이 다 찬 분기만' 자르기를 지우면 → test_incomplete_last_quarter_uses_the_last_complete_quarter(TypeError)
  - 첫 검사(3배)를 지우면 → test_sales_not_three_times_jeonse_in_the_low_rate_year_stops_the_draft
  - 둘째 검사(고금리 순서)를 지우면 → test_jeonse_peaking_first_stops_the_draft
  - 셋째 검사(최근 동반 상승)를 지우면 → test_prices_falling_while_rates_rise_stops_the_draft·test_rates_falling_to_a_new_low_stops_the_draft
  - 넷째 검사(상관 음수)를 지우면 → test_positive_rate_correlation_stops_the_draft
  - 돌려주는 칸 하나(예: mm_now)를 빼면 → test_snapshot_passes_and_fills_every_slot
"""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_theory_post as T  # noqa: E402

POST = next(p for p in T.POSTS if p['n'] == 7)
SLOTS = set(re.findall(r'%\((\w+)\)s', POST['body'])) - {'exp', 'zone', 'cycle', 'link'}

# /cycle/ D.rate_overlay — 2015Q1 부터 분기마다(2026-10-18)
_MM = [52.8, 54.2, 55.6, 56.2, 56.1, 56.6, 58.0, 59.1, 58.9, 59.6, 61.1, 61.3, 62.2, 62.9, 64.9, 66.3, 64.9, 64.7, 66.2,
       67.9, 70.6, 72.9, 78.2, 82.0, 88.8, 94.7, 103.4, 105.9, 103.7, 103.3, 95.8, 84.7, 82.2, 85.3, 87.9, 87.7, 87.2,
       88.0, 90.5, 90.5, 90.3, 91.4, 92.9, 94.7, 96.6, 98.3, 101.3]
_JE = [58.2, 60.8, 64.2, 66.6, 67.4, 67.9, 69.0, 70.2, 70.3, 71.2, 72.0, 71.8, 71.1, 70.4, 71.4, 71.9, 69.9, 70.1, 72.0,
       74.5, 76.2, 77.8, 81.6, 85.5, 86.0, 88.9, 91.4, 92.6, 91.0, 92.9, 91.3, 86.8, 81.2, 82.6, 85.5, 88.5, 89.5, 91.1,
       92.4, 91.6, 89.3, 90.2, 91.9, 94.6, 96.2, 99.0, 100.5]
_RT = [2.07, 1.77, 1.63, 1.61, 1.65, 1.54, 1.35, 1.44, 1.49, 1.4, 1.39, 1.5, 1.65, 1.65, 1.65, 1.77, 1.88, 1.83, 1.57,
       1.5, 1.37, 0.97, 0.7, 0.65, 0.72, 0.69, 0.81, 1.17, 1.46, 1.8, 2.74, 3.9, 3.64, 3.63, 3.74, 3.83, 3.69, 3.59,
       3.52, 3.4, 2.94, 2.66, 2.53, 2.69, 2.77, 2.85, 3.02]


def _snap():
    """네 전제가 모두 서는 고정 스냅숏 D — 시험마다 새 사본."""
    t = [2015 + i * 0.25 for i in range(len(_MM))]
    return {'rate_overlay': {'t': t, 'maemae': list(_MM), 'jeonse': list(_JE), 'rate': list(_RT),
                             'jratio': [None] * len(t)},
            'prose': {'rate_r': '−0.57', 'rate_n': '46'}}


def _append(D, mm, je, rt):
    r = D['rate_overlay']
    r['t'].append(r['t'][-1] + 0.25)
    for k, v in (('maemae', mm), ('jeonse', je), ('rate', rt), ('jratio', None)):
        r[k].append(v)


def _stops(D, why):
    with pytest.raises(SystemExit) as e:
        T.link7_values(D)
    assert str(e.value).startswith('7편을 만들 수 없다') and why in str(e.value), str(e.value)


def test_snapshot_passes_and_fills_every_slot():
    """전제가 모두 서는 스냅숏에서는 본문 자리 표시자를 하나도 빠뜨리지 않고 채운다 — 실데이터 국면과 무관하게 늘 돈다."""
    v = T.link7_values(_snap())
    assert SLOTS and SLOTS <= set(v), sorted(SLOTS - set(v))
    assert (v['now_from'], v['r_from'], v['now_to'], v['r_to']) == ('2025년 3분기', '2.53', '2026년 3분기', '3.02'), v
    assert (v['low_q'], v['mm_pk_q'], v['je_pk_q']) == ('2020년 4분기', '2021년 4분기', '2022년 2분기'), v


def test_real_data_passes_or_stops_with_a_named_premise():
    """저장소 실데이터: 전제가 서면 모든 자리를 채우고, 깨진 회차(금리 인하기 등)면 7편 문장의 전제를 대며 멈춘다(D1 — 게이트는
    막지 않는다). 그 밖의 예외(끝 분기 빈칸의 TypeError 등)는 코드 결함이라 그대로 빨갛다."""
    try:
        v = T.link7_values(T.P.cycle_d())
    except SystemExit as e:
        msg = str(e)
        assert msg.startswith('7편을 만들 수 없다 — ') and len(msg) > len('7편을 만들 수 없다 — ') + 5, msg
        import batch_notes as N      # 그 상태는 배치 기록 ℹ️ 줄로 알린다(D1) — 편 번호가 실렸는지 본다
        # 전제가 어긋난 줄이든 데이터 상태 줄(오버레이 빈 분기 — T.NOT_THE_TEXT)이든 7편이 실려야 한다
        tags = [re.match(r'\S+ 사이클 ([\d·]+)편 (?:전제가|초안 생성 멈춤)', ln) for ln in N.theory_claim_lines()]
        assert any(m and '7' in m.group(1).split('·') for m in tags), msg
        return
    assert SLOTS <= set(v), sorted(SLOTS - set(v))


def test_incomplete_last_quarter_uses_the_last_complete_quarter():
    """매매·금리는 새 분기가 있는데 전세가 아직 없는 끝 분기(전세지수가 한 달 늦게 실리는 회차)는 건너뛰고, 세 값이 다 찬 마지막
    분기로 센다 — TypeError 로 죽지 않는다(전수리뷰 BL2-1·C-1)."""
    D = _snap()
    want = T.link7_values(D)
    _append(D, _MM[-1] + 1.0, None, _RT[-1] + 0.1)
    assert T.link7_values(D) == want


def test_gap_inside_the_overlay_is_a_data_stop():
    """세 값이 찬 분기 사이에 빈 분기가 있으면 'N분기 뒤' 셈이 틀어지므로 문장 탓이 아닌 데이터 결함으로 멈춘다."""
    D = _snap()
    D['rate_overlay']['jeonse'][30] = None
    _stops(D, '빈 분기가 있다')


def test_sales_not_three_times_jeonse_in_the_low_rate_year_stops_the_draft():
    D = _snap()
    r = D['rate_overlay']
    lo = r['rate'].index(min(r['rate']))
    r['maemae'][lo + 4] = r['maemae'][lo] * 1.2           # 매매가 20%만 올랐다면(전세 8%) '세 배 넘게'가 거짓이 된다
    _stops(D, '3배를 넘지 않는다')


def test_jeonse_peaking_first_stops_the_draft():
    D = _snap()
    r = D['rate_overlay']
    lo = r['rate'].index(min(r['rate']))
    r['jeonse'][lo + 1] = max(r['jeonse']) + 5            # 전세가 매매보다 먼저 정점을 찍었다면 '매매가 먼저 꺾였다'가 거짓
    _stops(D, '매매가 먼저')


def test_prices_falling_while_rates_rise_stops_the_draft():
    D = _snap()
    r = D['rate_overlay']
    r['maemae'][-1] = min(r['maemae'][-8:]) - 1             # 최근 금리 상승 중 매매가 내렸다면 '지금은 공급'이 거짓이 된다
    _stops(D, '최근 금리가 오르는 동안')


def test_rates_falling_to_a_new_low_stops_the_draft():
    """금리가 최근 8분기 저점 아래로 내려간 분기가 실리면(인하기) '금리가 올랐는데 함께 올랐다'가 거짓 — 초안만 멈춘다(X1-1 의 상태)."""
    D = _snap()
    _append(D, _MM[-1] * 1.002, _JE[-1] * 1.002, min(_RT[-8:]) - 0.08)
    _stops(D, '최근 금리가 오르는 동안')


def test_positive_rate_correlation_stops_the_draft():
    D = _snap()
    D['prose']['rate_r'] = '0.12'
    _stops(D, '상관이 음수가 아니다')
