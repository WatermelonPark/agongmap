# -*- coding: utf-8 -*-
"""이론편 가드의 4편(theory_link3)·1·2편(link1_values) 몫 — 블로그 도구 전수 리뷰(2026-09-30) 묶음 BL 항목 73·76·78.

블로그 초안 도구는 2026-11-13 에 지웠고(가드만 남겼다) 그 도구만의 리뷰 시험(썸네일·--week·main 덮기·카테고리·두 바퀴·주간 표·
지표 절)도 함께 지웠다. 4편 숫자(theory_link3)와 1·2편 고리①(theory_guards.link1_values)은 배치 기록 줄이 부르는 가드라 남긴다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - theory_link3.link3_numbers 첫머리 연속성 검사를 지우면 → test_link3_stops_on_a_rebased_index (#73)
  - theory_link3 의 _se_pm·_ic_q assert 를 지우거나 except 를 AssertionError 만으로 되돌리면 → link3 가드 시험들 (#78)
  - _min2025 가 조사를 붙이지 않으면(옛 '는' 박기) → test_link3_min2025_carries_its_own_particle
  - link1_values 의 전제 검사를 지우거나 '가운데' 절 판정(mid_ok)을 늘 참으로 두면 → test_link1_values_follow_the_site_numbers (#76)
  - link3_numbers 의 except 에서 TypeError 를 빼면 → test_link3_gap_in_the_index_window_is_a_claim_stop_not_a_traceback

픽스처가 재현하는 실제 상태:
  - 지수 단절: 2026-09-28 데이터(3a823bc)처럼 계열 중간에서 여러 지역 값이 한꺼번에 절반으로 떨어진 합성 계열
    (판정 정본은 rebuild_cycle_analysis.index_breaks — 문턱 자체의 시험은 그쪽 묶음 C 시험에 있다).
  - link3 가드: 저장소 data.js 에서 매매지수 기준 단절을 시험 안에서만 이어 붙이고(단절이 없으면 그대로), 인허가를
    본문이 전제하는 반기(LATEST_H)까지, 매매지수를 그 반기 끝 달까지로 자르고, 수도권·지방 판정 칸(split·pbr)을
    2026-09-30 사이트 문장 그대로의 고정 값(FROZEN_SPLIT)으로 둔 상태 — 데이터가 앞으로 가도 같은 입력이 되게 고정한다
    (4편 '지금' 단정이 새 데이터로 뒤집히면 가드가 멈추지만 게이트는 막지 않는다 — 통합 검토). 여기에 리뷰가 재현한
    변이(서울 2021·22 인허가 ×0.8, 인천 ×1.5, 2025H2 행 이름 바꿈, 2026H2 행 추가, 받침으로 끝나는 시도가 2025년 최저
    목록의 끝에 오게 한 인허가)를 얹는다.
네트워크·저장소 파일 쓰기 없음.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as M  # noqa: E402
import rebuild_cycle_analysis as RC  # noqa: E402
import sido_zones as SZ  # noqa: E402
import theory_guards as T  # noqa: E402
import theory_link3 as L3  # noqa: E402


def _idx_sts(vals, others=None, name='세종'):
    """세종 계열 vals + 다른 두 지역(기본은 RISE). 기준 단절은 여러 지역이 같은 달에 함께 끊기는 모양이다."""
    dates = ['%d.%02d' % (2016 + i // 12, i % 12 + 1) for i in range(len(vals))]
    dates[-1] += ' p)'
    o = others if others is not None else RISE
    return {'매매지수': {'dates': dates, 'series': {name: vals, '대구': list(o), '부산': list(o)}}}


RISE = [100.0 + i for i in range(60)]
REBASED = RISE[:48] + [v / 2 for v in RISE[48:]]        # 2020.01 부터 새 기준 — 한 달에 −50%


# ── #73 지수 기준 단절 ────────────────────────────────────────────────────
def test_link3_stops_on_a_rebased_index():
    with pytest.raises(L3.Link3DataError) as e:
        L3.link3_numbers({}, _idx_sts(REBASED, REBASED))
    assert '기준 단절' in str(e.value)


# ── #78 4편 단정 가드 ────────────────────────────────────────────────────
def _link3_fixture():
    adv, sts = M.load()
    adv, sts = copy.deepcopy(adv), copy.deepcopy(sts)
    mm = sts['매매지수']
    for _ in range(5):                       # 시험 안에서만 이어 붙인다(데이터에는 연결계수를 쓰지 않는다 — 대표 결정 ①)
        br = RC.index_breaks(sts, ('매매지수',))
        if not br:
            break
        i = mm['dates'].index(br[0][1])
        for ser in mm['series'].values():
            prev = next((v for v in reversed(ser[:i]) if v is not None), None)
            if i < len(ser) and prev and ser[i]:
                f = prev / ser[i]
                for k in range(i, len(ser)):
                    if ser[k] is not None:
                        ser[k] *= f
    assert not RC.index_breaks(sts, ('매매지수',))
    rows = adv['permits']['rows']
    adv['permits']['rows'] = rows[:next(i for i, r in enumerate(rows) if r['p'] == L3.LATEST_H) + 1]
    # 배치가 매 회차 움직이는 입력은 LATEST_H 끝 달에서 멈춘다 — 4편의 '지금' 단정(_se_pk: 최신 확정치 > 지난 정점,
    # _boom_n 의 30개월 창)이 데이터 전진으로 뒤집히면 도구가 멈추는 것이 맞지만(로컬 세션이 돌릴 때 드러난다), 그날 배치의
    # 데이터 커밋까지 막으면 안 된다(CLAUDE.md '게이트 시험은 데이터가 앞으로 가도 초록'). 이 시험들은 가드의 동작을 본다.
    end = '%s.%s' % (L3.LATEST_H[:4], '06' if L3.LATEST_H.endswith('H1') else '12')
    k = [d.split()[0] for d in mm['dates']].index(end) + 1
    mm['dates'] = mm['dates'][:k]
    mm['series'] = {r: v[:k] for r, v in mm['series'].items()}
    # 판정 칸(adv['sido'] zones 의 split·pbr)도 분기마다 바뀐다 — 사이트 판정 문장과 같은 모양의 고정 값으로 둔다.
    for x in adv['sido']['zones']:
        if x['z'] in FROZEN_SPLIT:
            rows_, pbr = FROZEN_SPLIT[x['z']]
            x['split'] = dict(x['split'], rows=[list(r) for r in rows_])
            x['pbr'] = pbr
    return adv, sts


# 2026-09-30 사이트 판정 문장(make_sido_pages 가 굽는 split 두 줄·pbr) 그대로 — 판정이 분기마다 바뀌어도 가드 시험 입력은 고정
FROZEN_SPLIT = {
    '수도권': ((('지난 4년', '적정물량보다 20% 덜 지었습니다'), ('앞으로 3년', '적정물량의 68%가 들어옵니다')), 0.968),
    '지방': ((('지난 4년', '적정물량보다 14% 덜 지었습니다'), ('앞으로 3년', '적정물량의 57%가 들어옵니다')), 0.663),
}


def _scale(adv, region, years, f):
    R = adv['permits']['regions']
    for r in adv['permits']['rows']:
        if r['p'][:4] in years and r['v'][R.index(region)] is not None:
            r['v'][R.index(region)] *= f


def test_link3_baseline_passes_on_a_continuous_index():
    adv, sts = _link3_fixture()
    out = L3.link3_numbers(adv, sts)
    assert out['ic_q'] == '0.5배'


@pytest.mark.parametrize('region,f,key', [('서울', 0.8, 'se_pm'), ('인천', 1.5, 'ic_q')])
def test_link3_direction_claims_are_guarded(region, f, key):
    adv, sts = _link3_fixture()
    _scale(adv, region, ('2021', '2022'), f)
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert (' %s:' % key) in str(e.value), str(e.value)


def test_link3_beyond_percent_is_the_site_integer():
    """4편 '최근 2년 인허가를 착공으로 환산하면 적정물량의 N%'(sd_pbr·jb_pbr)는 시도 리포트 '3년 너머' 줄(판정 split ref 문장)이 찍은
    정수를 그대로 읽는다 — 다시 세지 않는다(전수리뷰 Z1-3·X1-3, CLAUDE.md '블로그 도구는 배치가 구운 값을 읽고 재계산하지 않는다').
    재현한 실제 상태(2026-10-18): '%.0f' 는 짝수 쪽 반올림이라 저장값 0.965(수도권)를 '96%'로 써 사이트 리포트의 97% 와 갈렸다. 저장
    pbr 은 소수 셋째 자리로 줄인 값이라, 원값으로 구운 사이트 정수와 저장값을 다시 반올림한 정수도 경계에서 갈린다.
    픽스처: 4편 고정 스냅숏(_link3_fixture)에서 판정 ref 문장은 97%·43% 인데 저장 pbr 은 0.9649·0.4249(다시 반올림하면 96·42)인 상태.
    변이(실제로 확인): _sd_pbr·_jb_pbr 을 SZ.pbr_pct(pbr) 재계산이나 '%.0f%%' % (pbr*100) 로 되돌리면 빨개진다."""
    adv, sts = _link3_fixture()
    for x in adv['sido']['zones']:
        if x['z'] in ('수도권', '지방'):
            pct, x['pbr'] = {'수도권': (97, 0.9649), '지방': (43, 0.4249)}[x['z']]
            x['split'] = dict(x['split'], ref=['3년 너머', '최근 2년 인허가를 착공으로 환산하면 적정물량의 %d%%입니다' % pct, '', False])
    v = L3.link3_numbers(adv, sts)
    assert (v['sd_pbr'], v['jb_pbr']) == ('97%', '43%'), v
    assert SZ.pbr_pct(0.9649) != 97          # 픽스처가 재계산과 문장 읽기를 가르는 경계 값인지


def test_link3_missing_half_year_is_a_claim_error_not_a_traceback():
    adv, sts = _link3_fixture()
    for r in adv['permits']['rows']:
        if r['p'] == '2025H2':
            r['p'] = '2025H9'                # 연간 합은 그대로, 반기 한 칸만 못 찾게
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert 'StopIteration' in str(e.value)


def test_link3_new_half_year_stops_the_now_sentences():
    adv, sts = _link3_fixture()
    last = adv['permits']['rows'][-1]
    adv['permits']['rows'].append(dict(last, p='2026H2', v=list(last['v'])))
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert 'jb_h1' in str(e.value)


def test_link3_min2025_carries_its_own_particle():
    adv, sts = _link3_fixture()
    v = L3.link3_numbers(adv, sts)['min2025']
    names, part = v[:-1], v[-1]
    assert part == ('은' if RC._jong(names.split('·')[-1]) else '는')
    # 실데이터의 끝 지역(제주)은 받침이 없어 '는'을 박아도 초록이다 — 받침으로 끝나는 시도가 끝에 오는 상태를 만든다.
    # 그 시도의 2025년을 2007년 이후 최저로 낮추고(0 은 아니게), 모델 순서상 그 뒤 시도는 2025년을 올려 목록에서 뺀다.
    R = adv['permits']['regions']
    sido = [rg for rg in R if rg not in SZ.AGG]
    tgt = [rg for rg in sido if RC._jong(T.SEARCH_NAME.get(rg, rg))][-1]
    for r in adv['permits']['rows']:
        if r['p'][:4] == '2025':
            for rg in sido[sido.index(tgt):]:
                i = R.index(rg)
                if r['v'][i]:
                    r['v'][i] = r['v'][i] * (0.01 if rg == tgt else 100)
    v = L3.link3_numbers(adv, sts)['min2025']
    assert v.endswith('·' + T.SEARCH_NAME.get(tgt, tgt) + '은'), (tgt, v)


# ── #76 1·2편 고리① ─────────────────────────────────────────────────────
def _d(rise, lo, hi):
    return {'link1_new': {'jeonse_rise': rise}, 'prose': {'l1_lo': lo, 'l1_hi': hi}}


def test_link1_values_follow_the_site_numbers():
    """1·2편 고리① 칸은 /cycle/ 본문 칸(prose.l1_lo·l1_hi) 글자 그대로이고, 방향 문구는 두 값에서 고르며, 전제(적은 분기 > 많은 분기)가
    깨지면 멈춘다(#76). l1_mid 는 2편 '가운데가 가장 높은 이유' 절이 서는지(세 구간 가운데 '보통'이 가장 높은지)다.
    변이(실제로 확인): link1_values 의 전제 검사를 지우면, mid_ok 를 늘 참으로 두면 빨개진다.
    픽스처: 2026-09 /cycle/ 정본 값(2.66 · 1.74 · −0.36)과 초안을 처음 쓸 때의 모양(1.42 · 1.9 · 0.63), 뒤집힌 가상 재산정."""
    v = T.link1_values(_d([2.66, 1.74, -0.36], '2.7', '−0.4'))       # 2026-09 /cycle/ 정본
    assert (v['l1_lo'], v['l1_hi'], v['l1_dir'], v['l1_mid']) == ('2.7', '−0.4', '하락으로 돌아섭니다.', False)
    v = T.link1_values(_d([1.42, 1.9, 0.63], '1.4', '0.6'))                # 초안을 처음 쓸 때의 모양
    assert v['l1_dir'] == '절반 이하로 떨어집니다.' and v['l1_mid'] is True
    with pytest.raises(SystemExit) as e:
        T.link1_values(_d([0.5, 1.0, 1.2], '0.5', '1.2'))
    assert str(e.value).startswith('1·2편을 만들 수 없다 — 고리① 전제') and str(e.value).endswith('문장을 먼저 고칠 것.'), str(e.value)


def test_link3_gap_in_the_index_window_is_a_claim_stop_not_a_traceback():
    """매매지수 30개월 창(_boom_n)에 빈 칸(None)이 끼면 날 TypeError 로 죽지 않고 Link3ClaimError(예외 이름을 남긴다)로 모이고, 가드
    (theory_guards.guard_values)는 SystemExit 로 4편만 멈춘다 — 데이터 상태는 게이트를 막지 않는다(대표 결정 2026-10-18 D1).
    픽스처: 4편 고정 스냅숏에서 서울 2023.06 한 칸을 비운 상태(원천이 한 달을 늦게 주거나 merge 가 새 열을 None 으로 만든 꼴).
    변이(실제로 확인): link3_numbers 의 except 에서 TypeError 를 빼면 TypeError 가 새어 빨개진다."""
    adv, sts = _link3_fixture()
    mm = sts['매매지수']
    mm['series']['서울'][[d.split()[0] for d in mm['dates']].index('2023.06')] = None
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert 'TypeError' in str(e.value), str(e.value)
    with pytest.raises(SystemExit) as e:
        T.guard_values(4, T.cycle_d(), (adv, sts))
    assert str(e.value).startswith('4편을 만들 수 없다'), str(e.value)
