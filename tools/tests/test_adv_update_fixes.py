# -*- coding: utf-8 -*-
"""update_adv_data.py 전체 점검(2026-09-23)에서 확인한 결함 여섯 건의 회귀 시험.

원천 호출 없이 돈다 — kosis·http_json·각 fetch 함수를 픽스처로 바꿔 끼운다. 각 시험의 독스트링에
① 무엇을 깨뜨리면 빨개지는지(실제로 깨뜨려 확인했다)와 ② 픽스처가 재현하는 실제 상태를 적었다.
지역 이름은 모델(sido_zones)·정본 상수(merge_regions.SRC/DST)에서 가져온다 — 손 목록을 두면
모델이 바뀔 때 이 시험만 낡는다.
"""
import datetime
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U  # noqa: E402
import sido_zones as SZ      # noqa: E402
from merge_regions import SRC, DST, W_GJ  # noqa: E402

MODEL = list(SZ.ORDER)
SIDO = [z for z in SZ.ORDER if z not in SZ.AGG]
KOSIS_AGG = {'전국': '총계', '수도권': '수도권소계', '지방': '지방소계'}   # BASIC_REGMAP의 역


# ── 1. 아파트 인허가 표(ADV.permits) ────────────────────────────────────────
def _permit_rows(cum):
    """DT_MLTM_1948 응답 모양. cum = {원천 지역명: 누계}."""
    return [{'C1_NM': KOSIS_AGG.get(r, r), 'C2_NM': '아파트', 'C4_NM': '아파트', 'DT': str(v)}
            for r, v in cum.items()]


def _cum(scale, merged):
    """모델 지역 전부에 값을 준 누계. merged=False면 통합 지역 대신 옛 두 이름으로 준다."""
    out = {}
    for i, z in enumerate(MODEL):
        if z == DST and not merged:
            out[SRC[0]] = 100 * scale
            out[SRC[1]] = 250 * scale
        else:
            out[z] = (i + 1) * 10 * scale
    return out


def test_permit_regions_follow_the_model():
    """인허가 표 지역 = 모델 전체(옛 두 이름 없음).

    변이: PERMIT_REGIONS 를 옛 REG15 파생(['전국','수도권','지방','서울','경기','인천'] + 광주·전남이 따로
          있는 15곳)으로 되돌리면 빨개진다(확인).
    픽스처: 없음 — 2026-09-23 저장분의 permits.regions 가 광주·전남을 따로 가진 20곳이었다.
    """
    assert set(U.PERMIT_REGIONS) == set(MODEL)
    assert not set(SRC) & set(U.PERMIT_REGIONS)


def test_permits_merge_old_names_by_sum_and_take_merged_row_after_the_switch(monkeypatch):
    """원천 전환기를 그대로 재현한다: 2026.06 누계까지는 광주·전남 두 행, 2026.12 누계는 전남광주 한 행.

    전남광주 = 광주 + 전남(물량 합, merge_regions 와 같은 규칙). 하반기 = 12월 누계 − 6월 누계가 두 바탕을
    가로질러도 맞아야 한다.

    변이: _fetch_apt_permits 의 필터를 예전처럼 `if reg not in PERMIT_REGIONS: continue` 로 되돌리면
          옛 두 이름이 버려져 2025·2026H1 전남광주가 None 이 되어 빨개진다(확인).
    픽스처: DT_MLTM_1948 이 2026.07분부터 '전남광주' 한 행만 내고 2026.06까지는 광주·전남을 따로 낸
            실제 상태(원천 최종변경일 2026-08-31). 2025년은 두 이름만 있는 온전한 해다.
    """
    book = {'202506': _cum(1, False), '202512': _cum(3, False),
            '202606': _cum(2, False), '202612': _cum(5, True)}

    def fake(params):
        prd = params['startPrdDe']
        if prd not in book:
            raise RuntimeError('KOSIS err 30: 데이터 없음')
        return _permit_rows(book[prd])

    monkeypatch.setattr(U, 'kosis', fake)
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    rows = {r['p']: dict(zip(U.PERMIT_REGIONS, r['v'])) for r in U.fetch_permits()}
    g, j = 100, 250
    assert rows['2025H1'][DST] == (g + j) * 1
    assert rows['2025H2'][DST] == (g + j) * 3 - (g + j) * 1
    assert rows['2026H1'][DST] == (g + j) * 2
    # 12월 누계는 원천 통합 행(모델 순서 값) − 6월 누계(두 조각의 합)
    merged_dec = (MODEL.index(DST) + 1) * 10 * 5
    assert rows['2026H2'][DST] == merged_dec - (g + j) * 2
    assert all(v is not None for p in rows for v in rows[p].values()), '빈칸이 생겼다'
    ref = U.permit_ref(U.PERMIT_REGIONS, U.fetch_permits())
    assert DST in ref, '통합 지역의 저점·고점(ref)이 없다 — 색·참조선이 빠진다'


def test_permits_fold_needs_both_pieces_and_prefers_the_source_row():
    """한 조각만으로는 합치지 않고, 원천이 통합 행을 주면 그 값을 쓴다.

    변이: _fold_old_permits 의 `all(...)` 을 `any(...)` 로 바꾸고 None 을 0 으로 세면 첫 단정이,
          `_GJ_NEW not in out` 조건을 지우면 둘째 단정이 빨개진다(둘 다 확인).
    픽스처: 원천 순단으로 한 조각만 온 달 · 전환 달에 원천이 통합 행과 옛 행을 함께 준 경우.
    """
    assert DST not in U._fold_old_permits({SRC[0]: 100})
    assert U._fold_old_permits({SRC[0]: 100, SRC[1]: 250, DST: 999})[DST] == 999


# ── 2. 규모별(STATS['규모별']) ──────────────────────────────────────────────
def _size_rows(levels):
    """KOSIS 규모별 표 응답 모양. levels = {원천 지역명: {PRD_DE: 수준}} — 6구간에 같은 값."""
    out = []
    for i, (reg, mp) in enumerate(levels.items()):
        for p, v in mp.items():
            for si in range(6):
                out.append({'C2_NM': reg, 'C2': 'a%02d' % i, 'C3': str(si + 1),
                            'PRD_DE': p, 'DT': str(v)})
    return out


def _levels(pieces_months, merged_months=()):
    base = {}
    for i, z in enumerate(MODEL):
        if z == DST:
            continue
        base[z] = {p: 100.0 + i + k for k, p in enumerate(pieces_months)}
    base[SRC[0]] = {p: 100.0 + 2 * k for k, p in enumerate(pieces_months)}
    base[SRC[1]] = {p: 90.0 + 1 * k for k, p in enumerate(pieces_months)}
    if merged_months:
        base[DST] = {p: 200.0 + 3 * k for k, p in enumerate(merged_months)}
    return base


def test_size_series_builds_the_merged_region_from_old_names():
    """KOSIS 규모별 표가 광주·전남만 주는 달에도 전남광주가 생기고, 지수는 W_GJ 가중평균 수준의 전월비다.

    변이: _size_levels 의 `and reg not in _GJ_OLD` 를 지우면(옛 이름을 버리면) 전남광주가 사라져 빨개진다(확인).
    픽스처: 2026-09-23 저장분 data-size.json 이 18곳(광주·전남·전남광주 모두 없음)이던 상태를 만든 응답 —
            원천은 광주·전남을 따로 주는데 수집 필터가 모델 이름(전남광주)만 받았다.
    """
    ps = ['202604', '202605', '202606']
    got = U._size_series(_size_rows(_levels(ps)), True)
    assert set(got) == set(MODEL)
    lv = {p: 100.0 + 2 * k for k, p in enumerate(ps)}
    lj = {p: 90.0 + k for k, p in enumerate(ps)}
    mix = {p: lv[p] * W_GJ + lj[p] * (1 - W_GJ) for p in ps}
    want = round((mix['202606'] / mix['202605'] - 1) * 100, 2)
    assert got[DST]['202606'] == [want] * 6
    conv = U._size_series(_size_rows(_levels(ps)), False)
    assert conv[DST]['202606'] == [round(mix['202606'], 2)] * 6, '전환율(수준)도 같은 가중평균이어야 한다'


def test_size_change_never_mixes_source_and_weighted_bases():
    """원천 통합 행이 중간부터 생기면, 그 첫 달 전월비는 가중평균끼리, 그 다음 달부터는 원천끼리 잰다.

    변이: _size_fold_old 에서 수준을 먼저 합쳐(lv = 가중평균, 원천으로 덮기) 한 번에 _size_changes 를
          돌리면 전환 달(202606) 값이 '원천 200 ÷ 가중평균 ~98' 로 +100% 남짓이 되어 빨개진다(확인).
    픽스처: R-ONE 이 2026.06부터 통합 지수를 함께 내기 시작한 것과 같은 모양 — 원천 통합 행은 06·07,
            옛 두 행은 04~07. 원천 통합 수준(200대)과 가중평균 수준(~98)이 크게 다르다.
    """
    ps = ['202604', '202605', '202606', '202607']
    got = U._size_series(_size_rows(_levels(ps, ['202606', '202607'])), True)[DST]
    lv = {p: 100.0 + 2 * k for k, p in enumerate(ps)}
    lj = {p: 90.0 + k for k, p in enumerate(ps)}
    mix = {p: lv[p] * W_GJ + lj[p] * (1 - W_GJ) for p in ps}
    assert got['202606'] == [round((mix['202606'] / mix['202605'] - 1) * 100, 2)] * 6
    assert got['202607'] == [round((203.0 / 200.0 - 1) * 100, 2)] * 6, '원천 통합값이 있으면 그걸로 잰다'


def test_size_guard_requires_every_model_region():
    """지역이 하나라도 빠지면 채택하지 않는다 — 직전의 80%만 넘으면 통과하던 비율 가드를 대체.

    변이: build_size 의 `lack` 검사를 지우면(예전 0.8 비율 가드만 남기면) 한 곳만 빠진 응답이 통과해 빨개진다(확인).
    픽스처: 2026-09-23 저장분과 같은 상태 — 모델에서 통합 지역 하나가 빠진 지표 넷.
    """
    ps = ['202604', '202605', '202606']
    metrics = {}
    for name, _, is_idx in U.SIZE_TBLS:
        m = U._size_series(_size_rows(_levels(ps)), is_idx)
        m.pop(DST)
        metrics[name] = m
    prev = {'dates': ['2026.05', '2026.06'], 'regions': MODEL}
    with pytest.raises(RuntimeError, match=DST):
        U.build_size(metrics, prev)
    for name, _, is_idx in U.SIZE_TBLS:
        metrics[name] = U._size_series(_size_rows(_levels(ps)), is_idx)
    out = U.build_size(metrics, prev)
    assert set(out['regions']) == set(MODEL)


def test_size_note_discloses_the_weighted_bridge():
    """화면 각주(※ D.note)가 통합 지역을 어떻게 이었는지와 그 가중치를 정본 값으로 밝힌다(계산법 공개).

    변이: build_size 의 note 를 예전 문구('지수 3종은 … 수준(%)')로 되돌리면 빨개진다(확인).
    픽스처: 모델 지역이 다 있는 평상 응답 — 각주는 가드를 통과한 회차에만 실린다.
    """
    ps = ['202605', '202606']
    metrics = {name: U._size_series(_size_rows(_levels(ps)), is_idx) for name, _, is_idx in U.SIZE_TBLS}
    note = U.build_size(metrics, {})['note']
    assert DST in note and ('%.3f' % W_GJ) in note


# ── 3. merge_basic: 늦게 도착한 옛 달 ───────────────────────────────────────
def test_late_month_is_sorted_into_place_with_all_series():
    """불완비로 버린 달이 다음 달보다 늦게 들어와도 dates 는 시간순이고, 지역 값이 같은 칸을 따라간다.

    변이: merge_basic 끝의 `_sort_by_date(D)` 를 지우면 dates 가 [..06, 08, 07] 로 남아 빨개진다(확인).
    픽스처: 미분양 실제 경로 — 2026.07 은 원천이 광주·전남을 빠뜨려 _drop_incomplete 가 버리고(2026-09-10 실측)
            2026.08 만 붙는다. 다음 회차에 07 이 완비되어 들어온다.
    """
    D = {'dates': ['2026.05', '2026.06'], 'series': {z: [1.0, 2.0] for z in SIDO}}
    first = {(2026, 7): {z: 7.0 for z in SIDO if z != DST},       # 한 지역 결측 → 버려진다
             (2026, 8): {z: 8.0 for z in SIDO}}
    U._drop_incomplete(first, SIDO, '미분양')
    assert list(first) == [(2026, 8)]
    U.merge_basic(D, first)
    U.merge_basic(D, {(2026, 7): {z: 7.0 for z in SIDO}})
    assert D['dates'] == ['2026.05', '2026.06', '2026.07', '2026.08']
    for z in SIDO:
        assert D['series'][z] == [1.0, 2.0, 7.0, 8.0], z
    stats = {'미분양': D}
    assert SZ.unsold_latest(stats, SIDO[0]) == (8.0, '2026.08'), '최신이 마지막 칸이 아니다'


# ── 4. update_basic: 실패가 기록에 닿는다 ───────────────────────────────────
def _boom(*a, **k):
    raise RuntimeError('KOSIS err 99: 픽스처')


def test_basic_failures_are_recorded(monkeypatch):
    """준공·규모별·공급·연간 계열이 죽으면 그 이름이 failed 에 남는다(.fetch_failed 로 간다).

    변이: update_basic 의 계열 루프에서 `failed.append(name)` 을 지우면 첫 단정이, update_supply 의
          `failed.append(name)` 을 지우면 공급 단정이 빨개진다(둘 다 확인).
    픽스처: KOSIS 가 준공 표에만 오류를 내고 규모별·연간 표도 오류, R-ONE 공급 표도 오류인 회차 —
            예전엔 전부 print 로만 끝나 배치 기록이 ✅였다.
    """
    stats = {n: {'dates': [], 'series': {}} for n in U.BASIC_CONF}
    monkeypatch.setattr(U, 'read_current_stats', lambda: stats)
    monkeypatch.setattr(U, 'write_stats', lambda s: None)
    monkeypatch.setattr(U, 'ECOS_KEY', '')
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)

    def basic(name, *a, **k):
        if name == '준공':
            raise RuntimeError('KOSIS err 99')
        return {}, {}
    monkeypatch.setattr(U, '_fetch_basic_one', basic)
    monkeypatch.setattr(U, 'kosis', _boom)
    monkeypatch.setattr(U, '_fetch_supply_one', _boom)
    failed = []
    U.update_basic(failed)
    assert '준공' in failed and '착공' not in failed
    assert '규모별' in failed
    assert set(U.SUPPLY_CONF) <= set(failed)
    # 연간 계열은 STATS 에 없으면 조용히 건너뛰는 설계라 여기 픽스처(연간 없음)에서는 안 남는다


def test_main_records_soft_failures_without_changing_rc(monkeypatch, tmp_path):
    """부분 실패는 .fetch_failed 에 실리지만 rc=3 판정(len(failed) >= 5)에는 들어가지 않는다.

    변이: main 의 rc 판정을 `len(failed + soft_failed) >= 5` 로 바꾸면 SystemExit(3) 이 나서 빨개지고,
          .fetch_failed 에 `failed` 만 쓰면 둘째 단정이 빨개진다(둘 다 확인).
    픽스처: R-ONE(주간·월간)·인허가·공휴일이 죽고(주요 4갈래) 새 데이터가 하나도 없는 회차에, 기본통계
            계열 여섯이 KOSIS 오류로 죽은 상태. 주요 실패가 5 미만이므로 예전과 같이 rc=0 이어야 한다.
    """
    src = io.open(U.DATA, encoding='utf-8').read()
    data = tmp_path / 'data.js'
    data.write_text(src, encoding='utf-8')
    monkeypatch.setattr(U, 'DATA', str(data))
    monkeypatch.setattr(U, 'ROOT', str(tmp_path))
    monkeypatch.setattr(U, 'KEY', 'x')
    monkeypatch.setattr(U, 'ECOS_KEY', '')
    for fn in ('fetch_weekly', 'fetch_monthly', 'fetch_permits', 'fetch_holidays'):
        monkeypatch.setattr(U, fn, _boom)
    soft = list(U.BASIC_CONF)

    def basic(failed=None):
        failed.extend(soft)
        return []
    monkeypatch.setattr(U, 'update_basic', basic)
    import sido_zones
    _, _, _, adv = U.read_current_adv()
    monkeypatch.setattr(sido_zones, 'calc', lambda st: adv['sido'])
    monkeypatch.setattr(sido_zones, 'supply_rows',
                        lambda st: {k: adv['occupancy'].get(k) for k in ('rows',)})
    monkeypatch.setattr(sys, 'argv', ['update_adv_data.py', '--update'])
    U.main()
    rec = (tmp_path / '.fetch_failed').read_text(encoding='utf-8').split(',')
    assert set(soft) <= set(rec), '기본통계 실패가 .fetch_failed 에 없다'
    assert {'weekly', 'monthly', 'permits', 'holidays'} <= set(rec)


# ── 5. _merge_hist: 열 목록이 바뀐 회차 ─────────────────────────────────────
def test_history_is_realigned_by_name_when_columns_change():
    """최신 응답의 열 목록이 바뀌어도 옛 행 값이 한 칸씩 밀리지 않는다.

    변이: _merge_hist 의 `older = _align_rows(...)` 줄을 지우면 옛 행의 '다구' 자리에 '나구' 값이 읽혀
          빨개진다(확인).
    픽스처: 2026-07 인천 행정구역 개편처럼 구 하나가 없어지고 새 구가 생긴 회차. 옛 열 [가구, 나구, 다구],
            새 열 [가구, 다구, 라구]. 저장분 두 주 + 새 응답 한 주.
    """
    cur = {'regions': ['가구', '나구', '다구'],
           'rows': [{'p': '2026-06-29', 'ma': [1.0, 2.0, 3.0], 'je': [4.0, 5.0, 6.0]},
                    {'p': '2026-07-06', 'ma': [1.1, 2.1, 3.1], 'je': [4.1, 5.1, 6.1]}]}
    new = {'regions': ['가구', '다구', '라구'],
           'rows': [{'p': '2026-07-13', 'ma': [1.2, 3.2, 9.2], 'je': [4.2, 6.2, 9.9]}]}
    out = U._merge_hist(new, cur, 156, '시험')
    assert out['regions'] == ['가구', '다구', '라구']
    by = {r['p']: r for r in out['rows']}
    assert by['2026-06-29']['ma'] == [1.0, 3.0, None]
    assert by['2026-07-06']['je'] == [4.1, 6.1, None]
    assert by['2026-07-13']['ma'] == [1.2, 3.2, 9.2]
    # 시군구 블록은 열 이름이 'codes' 다 — 같은 방어가 거기서도 돌아야 한다
    cur_s = {'codes': ['a1', 'a2'], 'rows': [{'p': '2026-06', 'ma': [1.0, 2.0]}]}
    new_s = {'codes': ['a2', 'a3'], 'rows': [{'p': '2026-07', 'ma': [2.5, 3.5]}]}
    assert U._merge_hist(new_s, cur_s, 120)['rows'][0]['ma'] == [2.0, None]


def test_history_untouched_when_columns_are_the_same():
    """열 목록이 같으면 옛 행을 그대로 둔다(평상 회차의 동작이 바뀌지 않는다).

    변이: _align_rows 의 '같으면 그대로' 조기 반환에서 열 비교를 지우면, 같은 열인데도 모든 행을 새로
          만들고 경고를 찍어 빨개진다(확인).
    픽스처: 2026-09-23 저장분처럼 서울 25구 열이 매주 같은 평상 회차.
    """
    cols = ['가구', '나구']
    old = [{'p': '1', 'ma': [1, 2]}]
    assert U._align_rows(old, cols, list(cols)) is old


# ── 6. 공휴일: 한 해만 실패한 회차 ──────────────────────────────────────────
def test_holidays_keep_saved_year_when_that_year_fails(monkeypatch):
    """내년 조회만 실패하면 내년분은 저장 목록을 그대로 쓰고, 실패는 기록에 남는다.

    변이: fetch_holidays 의 `out += kept` 를 지우면 내년 공휴일이 저장 목록에서 사라져 빨개진다(확인).
    픽스처: 공공데이터포털 특일 API 가 올해분은 주고 내년분 조회에서 순단으로 예외가 난 회차.
            저장분에는 두 해가 다 있다.
    """
    yr = datetime.date.today().year
    prev = ['%d-01-01' % yr, '%d-12-25' % yr, '%d-01-01' % (yr + 1), '%d-03-01' % (yr + 1)]

    def fake(url, tries=3):
        if 'solYear=%d' % (yr + 1) in url:
            raise RuntimeError('timeout')
        return {'response': {'body': {'items': {'item': [
            {'locdate': int('%d0101' % yr)}, {'locdate': int('%d1225' % yr)},
            {'locdate': int('%d1009' % yr)}]}}}}

    monkeypatch.setattr(U, 'DATAGO_KEY', 'x')
    monkeypatch.setattr(U, 'http_json', fake)
    failed = []
    got = U.fetch_holidays(prev, failed)
    assert '%d-10-09' % yr in got, '성공한 해의 새 값이 안 들어왔다'
    assert '%d-01-01' % (yr + 1) in got and '%d-03-01' % (yr + 1) in got, '실패한 해의 저장분이 사라졌다'
    assert failed == ['holidays:%d' % (yr + 1)]
