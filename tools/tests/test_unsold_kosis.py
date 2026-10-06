# -*- coding: utf-8 -*-
"""미분양 원천을 KOSIS 국토교통부 표(DT_MLTM_2080)로 옮긴 것(2026-10-07 대표 승인) — 배치와 감시가 같은 원천·같은 행을 본다.

재현하는 실제 상태: R-ONE 미분양표(T237973129847263)는 2026.07 에 광주·전남·전남광주 행을 모두 빠뜨려 배치가 그 달을 보류했고
화면이 2026.06 에 묶였다. KOSIS 표는 같은 통계를 2026.08 까지, 통합 행 '전남광주'로 준다. 옮기기 전 배치 대조(probe_unsold_alt,
10-07 run 37493505689)에서 2026.03~06 네 달 17곳이 R-ONE 값과 모두 같았다. 표 모양(같은 회차 실측): C1 지역(전국·수도권·시도·
'전남광주') · C2 부문(총합·공공부문·민간부문) · C3 규모(총합·공공부문·소계·면적 구간) · 항목 '호'.

변이(각각 실제로 확인):
  · _fetch_supply_kosis 의 분류 거르기(cfg['only'])를 지우면 → 부문·규모 행이 총합을 덮어 값 시험 빨강.
  · 증분 조회의 `keys[-months:]` 자르기를 지우면 → 달 수 시험 빨강.
  · 시딩(months=0)에서 '자료 없음(err 30)'을 넘기지 않으면 → 시딩 시험 빨강.
  · 감시 source_jobs 가 미분양을 R-ONE(rone_latest_complete)으로 보내면 → 감시 갈래 시험 빨강.
  · update_supply 가 fetch_supply 대신 _fetch_supply_one 을 부르면 → 배치 갈래 시험 빨강.
  · 감시 kosis_supply_latest 가 get= 을 넘기지 않으면(배치 http_json 60초·3번) → 감시 타임아웃 시험 빨강.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check_freshness as C  # noqa: E402
import update_adv_data as U  # noqa: E402

CFG = U.SUPPLY_CONF['미분양']


def _rows(ym, vals):
    out = []
    for reg, v in vals.items():
        b = {'PRD_DE': ym, 'C1_NM': reg, 'ITM_NM': '호'}
        out += [dict(b, C2_NM='총합', C3_NM='총합', DT='%d' % v),
                dict(b, C2_NM='민간부문', C3_NM='총합', DT='%d' % (v - 3)),
                dict(b, C2_NM='총합', C3_NM='소계', DT='1'),
                dict(b, C2_NM='총합', C3_NM='85㎡초과', DT='2')]
    return out


def test_config_points_at_the_kosis_table():
    assert CFG.get('via') == 'kosis' and CFG['org'] == '116' and CFG['tbl'] == 'DT_MLTM_2080'
    assert CFG['only'] == {'C2_NM': '총합', 'C3_NM': '총합'} and CFG['itm'] == '호'


def test_unsold_comes_from_the_total_rows_and_keeps_the_last_months(monkeypatch):
    rows = []
    for k, ym in enumerate(('202603', '202604', '202605', '202606', '202607', '202608')):
        rows += _rows(ym, {'서울': 1000 + k, '전남광주': 3000 + k, '전국': 60000 + k, '수도권': 18000 + k})
    seen = []
    monkeypatch.setattr(U, 'kosis', lambda p, get=None: seen.append(dict(p)) or rows)
    got = U.fetch_supply(CFG, {'서울', '전남광주', '전국', '수도권'}, 2)
    assert sorted(got) == [(2026, 7), (2026, 8)], sorted(got)
    assert got[(2026, 8)] == {'서울': 1005.0, '전남광주': 3005.0, '전국': 60005.0, '수도권': 18005.0}
    p = seen[0]
    assert p['tblId'] == 'DT_MLTM_2080' and p['objL3'] == 'ALL' and p['newEstPrdCnt'] == '6', p


def test_seeding_walks_every_year_and_skips_years_without_data(monkeypatch):
    years = []

    def fake(p, get=None):
        y = int(p['startPrdDe'][:4])
        years.append(y)
        if y < 2010:
            raise RuntimeError('KOSIS err 30: 데이터가 존재하지 않습니다.')
        return _rows('%d06' % y, {'서울': y})
    monkeypatch.setattr(U, 'kosis', fake)
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    got = U.fetch_supply(CFG, {'서울'}, 0)
    assert years[0] == 2000 and years == sorted(years) and len(years) > 20
    assert (2010, 6) in got and (2009, 6) not in got and got[(2026, 6)]['서울'] == 2026.0


def test_batch_routes_unsold_through_the_kosis_fetch(monkeypatch):
    called = []
    monkeypatch.setattr(U, 'SUPPLY_CONF', {'미분양': CFG})
    monkeypatch.setattr(U, 'fetch_supply', lambda cfg, regions, months=None: called.append(cfg['tbl']) or {})
    monkeypatch.setattr(U, '_fetch_supply_one', lambda *a, **k: pytest.fail('미분양이 R-ONE 경로로 갔다'))
    failed = []
    U.update_supply({}, failed=failed)
    assert called == ['DT_MLTM_2080'] and failed == ['미분양']     # 빈 응답은 실패로 남는다(전수리뷰 #8)


def test_watchdog_routes_unsold_to_kosis(monkeypatch):
    got = []
    monkeypatch.setattr(C, 'rone_latest_complete', lambda *a, **k: pytest.fail('미분양 감시가 R-ONE 으로 갔다'))
    monkeypatch.setattr(C, 'kosis_supply_latest', lambda cfg, since=None, want_total=False: got.append(cfg['tbl']) or '202608')
    jobs = C.source_jobs({'미분양': {'dates': ['2026.06'], 'series': {}}})
    assert jobs[('supply', '미분양')]() == '202608' and got == ['DT_MLTM_2080']


def test_watchdog_kosis_fetch_uses_the_watchdog_timeout(monkeypatch):
    """감시는 원천 조회를 FETCH_TIMEOUT(25초, 재시도 20초) 한 번으로 셈해 잡 예산(30분)을 맞췄다. 배치 조회(http_json 60초·3번·쉼)를
    타면 원천이 막힌 날 이 계열 하나가 3분 넘게 붙잡는다(2026-10-07 리뷰). 픽스처: 배치 조회는 부르면 실패, 감시 조회는 2026.08 표."""
    seen = []
    monkeypatch.setattr(U, 'http_json', lambda *a, **k: pytest.fail('감시가 배치의 http_json 으로 조회했다'))
    rows = _rows('202608', {r: 10 for r in set(U.SUPPLY_SIDO) | set(U._GJ_OLD)})
    monkeypatch.setattr(C, 'get_json', lambda url: seen.append(url) or rows)
    C._COMPLETE_CACHE.clear()
    assert C.kosis_supply_latest(CFG) == '202608' and len(seen) == 1 and 'DT_MLTM_2080' in seen[0]
