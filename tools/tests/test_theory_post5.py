# -*- coding: utf-8 -*-
"""사이클 이론 5편(고리 ④ 착공 → 입주) 가드 — 숫자는 theory_link4 가 데이터에서 세고, 단정이 깨지면 theory_guards.guard_values 가
멈춘다(블로그 초안 도구는 2026-11-13 에 지웠다 — 배치 기록 줄 batch_notes.theory_claim_lines 가 이 가드를 부른다).

⚠️ 실데이터로 단정("옛 시차라면 2025년에 드러났어야" 등)을 확인하는 시험은 두지 않는다. 데이터가 앞으로 가면(2026년 연간치가
들어오면) 단정이 깨질 수 있는데, 그걸 배치 게이트가 잡으면 그날 데이터 커밋 전체가 멈춘다(CLAUDE.md '게이트 시험은 데이터가
앞으로 가도 초록'). 성공 경로는 고정 스냅숏에서 본다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - guard_values 5편 갈래에서 Link4ClaimError 를 SystemExit 으로 바꾸는 except 를 지우면 → test_claim_break_stops_the_guard
  - link4_numbers 의 착공·준공 끝 달 검사를 옛 맨 assert 로 되돌리면 → 끝 달 어긋남 시험 둘(AssertionError 가 가드를 비켜 샌다)
  - guard_values 의 Link4DataError 갈래를 지우면 → 안내 시험('문장을 먼저 고칠 것'으로 글쓴이 탓을 한다)
  - link4_numbers 단정 모음의 KeyError·TypeError… 받기를 지우면 → 셈이 깨진 칸 시험(TypeError 가 그대로 샌다)
  - 단정 함수 하나(_fut_low)에 코드 오타(없는 키)를 넣거나 발행본이 읽는 값 함수 하나를 지우면 → 스냅숏 시험
픽스처: 가드 시험은 link4_numbers 를 예외를 던지는 가짜로 바꾼다. 끝 달 시험은 준공·착공 전국 두 계열만 둔 합성 STATS(분기를 닫지
않는 달에 한 표만 새 달을 받은 회차 — 착공 호출만 순단했거나 원천이 한 표를 늦게 실은 상태)이고, 셈이 깨진 칸 시험은 단정이 읽는
/cycle/ 칸 하나가 빈(null) 합성 D 다. 둘 다 실데이터에 기대지 않아 데이터가 앞으로 가도 같은 입력이다(5편 본문이 2026년 데이터를
전제하므로 합성 달도 2026년이다).
"""
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import theory_guards as T  # noqa: E402
import theory_link4 as L4  # noqa: E402

# 5편 발행본 본문이 읽는 데이터 칸(2026-11-13 초안 도구를 지울 때의 본문에서 링크·경험·지역 칸을 뺀 것) — 가드가 이 칸을 모두 내야 한다
SLOTS = {'arr_y', 'cn_lead', 'conv', 'dg_st', 'dg_st_old', 'dn25', 'dn25_old', 'dn_pk', 'dn_ytd', 'dn_ytd_since', 'fq_below',
         'fq_min4', 'fq_min4p', 'fq_min4v', 'fq_n', 'fut_high', 'fut_high_names', 'fut_low', 'fut_low_n', 'gb_lead', 'gg_fut', 'h1_24',
         'h1_25', 'h29p', 'h2_24', 'h2_25', 'h2_drop', 'ic_fut', 'jb_new', 'jb_old', 'lag_hi', 'lag_lo', 'lead_gap', 'lead_new',
         'lead_new_y', 'lead_old', 'lead_old_y', 'lead_r', 'nat_r', 'ref_q', 'ref_y', 'roll_from', 'roll_now', 'roll_prev', 'roll_ratio',
         'roll_to', 'sd_new', 'sd_old', 'se_r', 'shift_q', 'shift_y', 'st21', 'st22', 'st23', 'st_pk', 'st_ytd', 'st_ytd_up', 'win_y',
         'y26', 'y26p', 'y27', 'y27p', 'ytd_m'}


def test_claim_break_stops_the_guard(monkeypatch):
    def broken(adv, sts, D=None):
        raise L4.Link4ClaimError('dn25: 옛 시차 반례가 더는 성립하지 않는다')
    monkeypatch.setattr(L4, 'link4_numbers', broken)
    with pytest.raises(SystemExit) as e:
        T.guard_values(5, D={}, data=({}, {}))
    assert str(e.value) == '5편을 만들 수 없다 — dn25: 옛 시차 반례가 더는 성립하지 않는다. 문장을 먼저 고칠 것.', str(e.value)


def _sts(dn_last, st_last):
    """준공·착공 전국 두 계열만 둔 STATS — 2026년 1월부터 각자의 끝 달까지."""
    def ser(last):
        ds = ['2026.%02d' % m for m in range(1, int(last[5:]) + 1)]
        return {'dates': ds, 'series': {'전국': [1000] * len(ds)}}
    return {'준공': ser(dn_last), '착공': ser(st_last)}


@pytest.mark.parametrize('dn_last,st_last', [('2026.08', '2026.07'), ('2026.07', '2026.08')])
def test_series_end_mismatch_is_a_data_stop_not_a_traceback(dn_last, st_last):
    """착공·준공 끝 달이 갈리면 Link4DataError(Link4ClaimError 의 하위)로 멈춘다 — 날 AssertionError 가 아니다(전수리뷰 T3-6·BL2-3·T1-2).

    예전엔 맨 assert 라 AssertionError 가 render·link6_values 의 Link4ClaimError 받기와 게이트 시험의 SystemExit 거름을 모두
    비켜, 그 회차 게이트 시험 넷을 죽였다(수집 _hold_horizon·생성기는 판정 창이 그대로라 통과시킨다)."""
    with pytest.raises(L4.Link4DataError) as e:
        L4.link4_numbers({}, _sts(dn_last, st_last))
    assert isinstance(e.value, L4.Link4ClaimError)
    assert dn_last in str(e.value) and st_last in str(e.value), str(e.value)


def test_series_end_mismatch_tells_the_writer_to_wait_for_the_batch():
    """가드(5편)는 끝 달 어긋남을 글쓴이 탓으로 안내하지 않는다 — 다음 배치를 받은 뒤 다시 돌리라고 한다(4편 Link3DataError 와 같은
    갈래). 멈춤 문구에 NOT_THE_TEXT 가 들어 배치 기록 줄이 '데이터 상태'로 가른다."""
    with pytest.raises(SystemExit) as e:
        T.guard_values(5, D={}, data=({}, _sts('2026.08', '2026.07')))
    msg = str(e.value)
    assert '5편을 만들 수 없다' in msg and '착공·준공 마지막 달이 다르다' in msg and T.NOT_THE_TEXT in msg, msg
    assert '문장을 먼저 고칠 것' not in msg and 'git pull' in msg, msg


def test_arithmetic_break_in_a_claim_is_a_claim_stop_not_a_traceback(tmp_path, monkeypatch):
    """단정 하나가 빈 칸에 걸려 셈이 깨지면(TypeError 등) 그것도 Link4ClaimError 로 멈춘다 — 날 예외로 새지 않는다(대표 결정 D1).

    단정 모음은 이름순으로 돌아 arr_y(올해 + /cycle/ lead_new)가 맨 먼저다. 그 칸을 비운 합성 /cycle/ 페이지를 읽게 하고,
    재계산 시차(link45_leadtime)는 이 시험과 무관하므로 빈 값으로 바꿔 끼운다. 멈춤 문구에 예외 이름이 남는지도 본다 —
    배치 기록 줄에서 코드 결함과 데이터 상태를 사람이 가르는 단서다."""
    (tmp_path / 'cycle').mkdir()
    (tmp_path / 'cycle' / 'index.html').write_text('<script>const D = {"prose": {"lead_new": null}};</script>',
                                                   encoding='utf-8')
    monkeypatch.setattr(L4, 'ROOT', str(tmp_path))
    monkeypatch.setattr(L4.RC, 'link45_leadtime', lambda sts: (None, {}))
    adv = {'occupancy': {'regions': ['전국'], 'rows': [], 'ref': {'전국': 1}}, 'sido': {'L': '2026Q2', 'zones': []}}
    with pytest.raises(L4.Link4ClaimError) as e:
        L4.link4_numbers(adv, _sts('2026.08', '2026.08'))
    assert ' arr_y: TypeError' in str(e.value), str(e.value)


def _snapshot():
    """5편 고정 스냅숏(theory5_snapshot.json) — 2026-10-20 저장소의 ADV.occupancy·ADV.sido·STATS 준공·착공·인허가와 /cycle/ D 를
    옮겨 둔 것. 모든 단정이 서는 상태라 데이터가 앞으로 가도(2027년 자료 — 본문의 2026년 전제가 깨지는 날) 같은 입력이다."""
    import json
    with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'theory5_snapshot.json'), encoding='utf-8') as f:
        s = json.load(f)
    return s['adv'], s['sts'], s['D']


def test_snapshot_passes_every_claim_and_fills_every_slot():
    """성공 경로: 고정 스냅숏에서 link4_numbers 의 단정이 모두 서고 발행본 본문이 읽는 칸이 모두 빈 글 없이 나온다. 가드(guard_values)도
    같은 값을 낸다. 단정 모음의 넓은 받기(KeyError·TypeError → Link4ClaimError)는 단정 함수 안의 코드 회귀도 '데이터가 바뀌었다'로
    삼켜 게이트에서 안 보이게 한다 — 이 시험은 그 회귀를 빨갛게 드러낸다(전수리뷰 overflow G1a, 대표 결정 2026-10-18 D1).
    변이(실제로 확인): 단정 함수 하나(_fut_low)에 코드 오타(없는 키)를 넣으면, 값 함수 하나를 지우면 빨개진다."""
    adv, sts, D = _snapshot()
    v = L4.link4_numbers(adv, sts, D)
    assert SLOTS <= set(v), sorted(SLOTS - set(v))
    assert all(isinstance(v[k], str) and v[k] for k in SLOTS), [k for k in SLOTS if not v[k]]
    assert T.guard_values(5, D, (adv, sts)) == v
