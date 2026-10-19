# -*- coding: utf-8 -*-
"""같은 원천 표(DT_MLTM_1948 아파트)를 두 경로로 받는 인허가가 어긋나면 그 해를 다시 받는다(전수리뷰 A-1·H2-1).

재현하는 실제 상태: 투자지표 인허가(ADV.permits, fetch_permits)는 2007~올해 6·12월 누계를 매 회차 전부 다시 받고, 기본통계
인허가(STATS)는 최근 BASIC_MONTHS 달만 다시 받는다. 원천이 2026-10-07 회차에 2025년을 고치자 ADV.permits 만 따라가 전국 2025
하반기가 232,955 대 224,469 로 갈렸다(저장소 data.js 에서 19칸 — 이 파일의 실데이터 시험이 같은 함수로 센다). 착공·준공은 대조할
두 번째 경로가 없어, 인허가가 어긋난 해에 셋을 함께 다시 받는다. 게이트로 막지 않고 배치 기록 ℹ️ 줄로 알린다.
픽스처: 2025~2026 누계 STATS(전국·서울)와 같은 표에서 온 반기 행 — 2025 하반기 전국만 원천이 고친 값(ADV 쪽). 지역 이름은
모델(sido_zones.ORDER)의 집계 첫 칸과 첫 시도에서 가져온다.

변이(각각 실제로 확인):
  - permit_half_mismatch 의 하반기를 12월 누계 그대로(− 6월 누계 없이) 견주면 첫 시험이 빨개진다.
  - update_basic 의 `if permits: changed += heal_permit_years(...)` 를 지우면 둘째 시험이 빨개진다.
  - heal_permit_years 의 `years[:PERMIT_HEAL_YEARS]` 를 `years` 로 바꾸면(어긋난 해를 한 회차에 다 받으면) 호출 수 단정이 빨개진다.
  - 재수집 실패를 failed 에 남기는 줄을 지우면 셋째 시험이 빨개진다.
  - main() 이 update_basic 에 ADV.permits 를 넘기지 않으면 넷째 시험이 빨개진다.
  - update-cloud.yml 커밋 잡에서 '원천 소급 정정 반영' rep 를 지우면 다섯째 시험이 빨개진다.
"""
import copy
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U   # noqa: E402
import sido_zones as SZ       # noqa: E402
import month_lag as ML        # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
NAT = SZ.AGG[0]                                          # 집계 첫 칸(전국)
ONE = next(z for z in SZ.ORDER if z not in SZ.AGG)       # 첫 시도
MONTHS = ['%d.%02d' % (y, m) for y in (2024, 2025, 2026) for m in range(1, 13)][:-4]   # 2024.01 ~ 2026.08


def _cum(nat12, one12, scale):
    """월 누계 — 해마다 1월부터 쌓인다. 6월 누계는 12월의 절반 남짓."""
    out = {NAT: [], ONE: []}
    for lab in MONTHS:
        y, m = int(lab[:4]), int(lab[5:])
        f = m / 12.0
        out[NAT].append(round(nat12[y] * f * scale))
        out[ONE].append(round(one12[y] * f * scale))
    return out


def _stats():
    nat12, one12 = {2024: 360, 2025: 340, 2026: 300}, {2024: 36, 2025: 40, 2026: 30}
    st = {name: {'dates': [], 'series': {}} for name in U.BASIC_CONF}      # 다른 기본통계 계열은 빈 채로(이 시험 밖)
    st.update({name: {'dates': list(MONTHS), 'series': _cum(nat12, one12, k + 1)}
               for k, name in enumerate(U.PERMIT_HEAL_SERIES)})
    return st


def _permits(stats, fix=()):
    """STATS 인허가 누계에서 만든 반기 행(두 경로가 같은 상태). fix = [(반기, 지역, 원천이 고친 값)]."""
    D = stats['인허가']
    at = {lab: i for i, lab in enumerate(D['dates'])}
    regs = [NAT, ONE]
    rows = []
    for y in (2024, 2025, 2026):
        j6, j12 = at.get('%d.06' % y), at.get('%d.12' % y)
        rows.append({'p': '%dH1' % y, 'v': [D['series'][r][j6] for r in regs]})
        if j12 is not None:
            rows.append({'p': '%dH2' % y, 'v': [D['series'][r][j12] - D['series'][r][j6] for r in regs]})
    for p, reg, v in fix:
        next(r for r in rows if r['p'] == p)['v'][regs.index(reg)] = v
    return {'regions': regs, 'rows': rows}


def test_half_year_mismatch_names_only_the_revised_cell():
    st = _stats()
    D = st['인허가']
    h2 = D['series'][NAT][D['dates'].index('2025.12')] - D['series'][NAT][D['dates'].index('2025.06')]
    assert U.permit_half_mismatch(_permits(st), st) == [], '같은 상태인데 어긋남이라 한다'
    got = U.permit_half_mismatch(_permits(st, [('2025H2', NAT, h2 + 10)]), st)
    assert got == [('2025H2', NAT, h2 + 10, h2)], got


def _run_basic(monkeypatch, st, permits, heal):
    """update_basic 을 st 위에서 돌린다. 평소 창 조회는 빈 응답, (계열, 끝 달) 재수집 조회는 heal(name, upto)."""
    calls = []
    monkeypatch.setattr(U, 'read_current_stats', lambda: st)
    monkeypatch.setattr(U, 'write_stats', lambda s: None)
    monkeypatch.setattr(U, 'ECOS_KEY', '')
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    for fn in ('update_size', 'update_supply', 'update_annual'):
        monkeypatch.setattr(U, fn, lambda *a, **k: [])
    monkeypatch.setattr(U, 'drop_raw_aggregates', lambda stats: {})
    monkeypatch.setattr(U, '_hold_horizon', lambda *a: False)

    def fetch(name, months=None, upto=None):
        if upto is None:
            return {}, {}
        calls.append((name, upto))
        return heal(name, upto), {}
    monkeypatch.setattr(U, '_fetch_basic_one', fetch)
    failed = []
    changed = U.update_basic(failed, permits)
    return changed, failed, calls


def test_revised_year_is_refetched_for_the_three_mltm_series(monkeypatch):
    st = _stats()
    D = st['인허가']
    i6, i12 = D['dates'].index('2025.06'), D['dates'].index('2025.12')
    fixed12 = D['series'][NAT][i12] + 10
    permits = _permits(st, [('2025H2', NAT, D['series'][NAT][i12] - D['series'][NAT][i6] + 10),
                            ('2024H1', NAT, 1)])                 # 더 옛 해도 어긋났다 — 이번 회차는 늦은 해 하나만
    other = [n for n in U.PERMIT_HEAL_SERIES if n != '인허가'][0]

    def heal(name, upto):
        if name == '인허가':
            return {(2025, 12): {NAT: fixed12}}
        if name == other:
            return {(2025, 3): {NAT: 777}}
        return {}
    changed, failed, calls = _run_basic(monkeypatch, st, permits, heal)
    assert sorted(calls) == sorted((n, (2025, 12)) for n in U.PERMIT_HEAL_SERIES), calls
    assert D['series'][NAT][i12] == fixed12 and st[other]['series'][NAT][st[other]['dates'].index('2025.03')] == 777
    tok = [t for t in changed if U.REVISION_MARK in t]
    assert len(tok) == 1 and '2025' in tok[0], changed
    assert not failed, failed
    assert [b[0] for b in U.permit_half_mismatch(permits, st)] == ['2024H1'], '고친 해가 그대로이거나 옛 해가 사라졌다'


def test_refetch_failure_or_lasting_mismatch_is_recorded(monkeypatch):
    st = _stats()
    D = st['인허가']
    h2 = D['series'][NAT][D['dates'].index('2025.12')] - D['series'][NAT][D['dates'].index('2025.06')]
    permits = _permits(st, [('2025H2', NAT, h2 + 10)])

    def boom(name, upto):
        raise RuntimeError('KOSIS err 20: 픽스처')
    changed, failed, _ = _run_basic(monkeypatch, copy.deepcopy(st), permits, boom)
    assert failed == ['인허가:원천 정정 재수집 실패(2025)'] and not any(U.REVISION_MARK in t for t in changed)
    changed, failed, _ = _run_basic(monkeypatch, st, permits, lambda name, upto: {})
    assert failed == ['인허가:원천 정정 대조 어긋남(2025)'], failed


def test_main_hands_the_permit_rows_to_the_basic_update(monkeypatch, tmp_path):
    from test_adv_main_guards import _Run
    run = _Run(monkeypatch, tmp_path)
    run.quiet()
    seen = {}

    def basic(failed=None, permits=None):
        seen['permits'] = permits
        return []
    monkeypatch.setattr(U, 'update_basic', basic)
    run.main()
    assert seen.get('permits') == run.before['permits'], '기본통계 갱신이 투자지표 인허가를 받지 못했다'


def test_revision_token_reaches_the_batch_record():
    yml = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    code = '\n'.join(l for l in yml.splitlines() if not l.lstrip().startswith('#'))
    up = code[code.find('name: 산출물 업로드'):code.find('commit:')]
    assert '.stats_changed' in up, '변경 토큰 파일이 아티팩트에 안 실린다'
    assert re.search(r'grep \'%s\'' % re.escape(U.REVISION_MARK), code), '커밋 잡이 원천 정정 토큰을 찾지 않는다'
    assert re.search(r'rep "%s 원천 소급 정정 반영' % re.escape(ML.MARK), code), 'ℹ️ 줄이어야 한다 — ⚠️ 면 매 회차 메일이 간다'


def test_live_data_mismatch_is_counted_by_the_same_function():
    """저장소 data.js 로도 돈다 — 값은 단정하지 않는다(배치가 다음 회차에 고친다). 어긋난 칸이 있으면 모두 반기 꼴이고 두 값이 다르다."""
    adv, st = ML.load()
    bad = U.permit_half_mismatch(adv.get('permits'), st)
    assert adv.get('permits', {}).get('rows'), '투자지표 인허가를 못 읽었다 — 대조가 헛돈다'
    for p, reg, v, got in bad:
        assert re.match(r'^\d{4}H[12]$', p) and reg in adv['permits']['regions'] and round(got) != round(v)


def test_heal_never_adds_months_or_touches_an_open_year(monkeypatch):
    """다시 받기는 다 찬 해의 이미 있는 달만 고친다 — 새 달을 덧붙이면 앞에서 돈 _hold_horizon 을 비켜 준공·착공 끝 분기가 갈라진다.

    재현하는 상태: 올해(픽스처 2026, 8월까지) 상반기 칸이 그날 기본통계 조회 실패로 투자지표와 어긋난 회차 — 예전 코드는 2026 을
    upto=(2026,12)로 다시 받아 원천이 막 낸 착공 새 달(2026.09)을 덧붙였다. 다 찬 해(2025)의 재수집 응답에 섞인 픽스처 밖 달(2023.05)도
    덧붙이지 않는다.
    변이: heal_permit_years 의 `if (int(h[:4]), 12) in have.get('인허가', ())` 를 지우면 2026 호출 단정이, merge_basic 앞
    `if ym in have[name]` 거르기를 지우면 덧붙인 달 단정이 빨개진다(각각 실제로 확인).
    """
    st = _stats()
    D = st['인허가']
    j6 = D['dates'].index('2026.06')
    permits = _permits(st, [('2026H1', NAT, D['series'][NAT][j6] + 5)])
    _, _, calls = _run_basic(monkeypatch, copy.deepcopy(st), permits, lambda name, upto: {(2026, 9): {NAT: 1}})
    assert calls == [], '12월이 없는 올해를 다시 받았다: %s' % calls

    st = _stats()
    D = st['인허가']
    i6, i12 = D['dates'].index('2025.06'), D['dates'].index('2025.12')
    permits = _permits(st, [('2025H2', NAT, D['series'][NAT][i12] - D['series'][NAT][i6] + 10)])
    before = {n: list(st[n]['dates']) for n in U.PERMIT_HEAL_SERIES}
    _, _, calls = _run_basic(monkeypatch, st, permits,
                             lambda name, upto: {(2025, 12): {NAT: 5}, (2023, 5): {NAT: 9}, (2026, 9): {NAT: 9}})
    assert calls, '어긋난 다 찬 해를 다시 받지 않았다 — 거르기 단정이 헛돈다'
    assert {n: st[n]['dates'] for n in U.PERMIT_HEAL_SERIES} == before, '다시 받기가 달을 덧붙였다'
    assert all(st[n]['series'][NAT][i12] == 5 for n in U.PERMIT_HEAL_SERIES), '있는 달은 고쳐야 한다'
