# -*- coding: utf-8 -*-
"""미분양 대체 원천 조사 도구(tools/probe_unsold_alt.py) — 기록만 하고 배치를 절대 멈추지 않는가, 그리고 결정에 필요한
'최신 달 · 광주/전남 행 유무'를 바르게 읽는가.

재현한 실제 상태(2026-10-06): R-ONE 미분양 표는 2026.07 에 광주·전남 행이 없어 배치가 그 달을 보류한다. 이 도구는
KOSIS 국토교통부 표가 같은 달에 광주·전남(또는 '전남광주')을 주는지 본다. 픽스처는 KOSIS 응답 모양(TBL_ID·TBL_NM·
ORG_ID, PRD_DE·C1_NM)을 흉내 낸 가짜 응답이다 — 네트워크·키 없이 돈다.

변이(각각 실제로 확인):
  · summarize 가 최신 달 대신 가장 이른 달(min)을 고르면 '최신 202608' 단정이 빨강.
  · GJ 에서 '전남광주'·'광주'·'전남'을 빼면 '광주·전남 행' 단정이 빨강.
  · main 이 표 조회 예외를 잡지 않으면 '조회 실패' 단정과 '0 으로 끝난다' 단정이 빨강.
  · search 가 다른 기관(ORG_ID 408) 표를 거르지 않으면 표 수 단정이 빨강.
  · sido_totals 가 규모 합계('계') 행만 고르지 않으면(규모별 행이 시도 값을 덮어씀), _short 가 '서울특별시'를 '서울'로
    줄이지 않으면 → 대조 시험 빨강.
대조 픽스처(2026-10-06 배치 실측 모양): DT_MLTM_2080 은 C1=지역(전체 이름, 통합 행 '전남광주')·C2=규모(계·60㎡이하…),
R-ONE 계열은 2026.06 까지. 2026.05·06 은 같은 값, 2026.07·08 은 R-ONE 에 없는 달.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import probe_unsold_alt as P  # noqa: E402


def _fake(search_rows, data):
    calls = []

    def get(url, params, timeout=25):
        calls.append((url, dict(params)))
        if url == P.SEARCH_API:
            return search_rows
        tbl = params['tblId']
        v = data[tbl]
        if isinstance(v, Exception):
            raise v
        return v
    return get, calls


SEARCH = [
    {'ORG_ID': '116', 'TBL_ID': 'DT_A', 'TBL_NM': '시도별 미분양현황'},
    {'ORG_ID': '116', 'TBL_ID': 'DT_A', 'TBL_NM': '시도별 미분양현황'},          # 같은 표가 두 번 — 한 번만
    {'ORG_ID': '408', 'TBL_ID': 'DT_X', 'TBL_NM': '미분양 다른 기관'},           # 다른 기관 — 뺀다
    {'ORG_ID': '116', 'TBL_ID': 'DT_B', 'TBL_NM': '공사완료후 미분양현황'},
    {'ORG_ID': '116', 'TBL_ID': 'DT_C', 'TBL_NM': '주택건설실적'},               # 이름에 '미분양' 없음 — 뺀다
]


def _rows(period, names):
    return [{'PRD_DE': period, 'C1_NM': n} for n in names]


def test_reads_latest_month_and_gwangju_jeonnam_rows(capsys):
    data = {
        'DT_A': _rows('202607', ['전국', '서울', '광주', '전남']) + _rows('202608', ['전국', '서울', '전남광주']),
        'DT_B': _rows('202606', ['전국', '서울']),
    }
    get, calls = _fake(SEARCH, data)
    assert P.main(get=get, key='k') == 0
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.startswith('::notice title=미분양 대체 원천 조사::')]
    assert len(lines) == 2, out                                   # DT_A·DT_B 둘(중복·다른 기관·다른 이름 제외)
    assert '최신 202608' in lines[0] and '광주·전남 행: 전남광주' in lines[0], lines[0]
    assert '최신 202606' in lines[1] and '광주·전남 행: 없음' in lines[1], lines[1]
    assert all(p.get('orgId', P.ORG) == P.ORG for _, p in calls)  # 국토교통부 표만 조회


def test_never_stops_the_batch(capsys):
    get, _ = _fake(SEARCH, {'DT_A': RuntimeError('KOSIS err 21: 잘못된 요청'), 'DT_B': []})
    assert P.main(get=get, key='k') == 0
    out = capsys.readouterr().out
    assert '조회 실패' in out and 'DT_A' in out, out
    assert P.main(get=get, key='') == 0                            # 키가 없으면 조용히 건너뜀

    def boom(url, params, timeout=25):
        raise OSError('connection reset')
    assert P.main(get=boom, key='k') == 0
    out = capsys.readouterr().out
    assert '검색 실패' in out and '받지 못했다' in out, out   # 검색이 죽어도 후보 표 대조는 따로 시도한다


def test_widens_classification_levels_until_rows_come():
    """분류 단계가 둘인 표 — objL1 만 주면 KOSIS 가 err 를 준다. objL2 까지 넓혀 받는다."""
    seen = []

    def get(url, params, timeout=25):
        seen.append(tuple(k for k in ('objL1', 'objL2', 'objL3') if k in params))
        if 'objL2' not in params:
            raise RuntimeError('KOSIS err 20: 필수요청변수값이 누락')
        return _rows('202608', ['전국'])
    assert P.table_rows('k', 'DT_A', get)[0]['PRD_DE'] == '202608'
    assert seen == [('objL1',), ('objL1', 'objL2')]


def test_candidate_shape_and_comparison_with_the_current_series(capsys):
    def rows(ym, reg, total, parts):
        out = [{'PRD_DE': ym, 'C1_NM': reg, 'C2_NM': '계', 'ITM_NM': '미분양', 'DT': str(total)}]
        out += [{'PRD_DE': ym, 'C1_NM': reg, 'C2_NM': nm, 'ITM_NM': '미분양', 'DT': str(v)} for nm, v in parts]
        return out
    data = []
    for ym, seoul, gj in (('202605', 985, 3000), ('202606', 1013, 3100), ('202607', 1100, 3200), ('202608', 1200, 3300)):
        data += rows(ym, '서울특별시', seoul, [('60㎡이하', 400), ('60~85㎡', seoul - 400)])
        data += rows(ym, '전남광주', gj, [('60㎡이하', 1), ('60~85㎡', gj - 1)])
    stats = {'미분양': {'dates': ['2026.05', '2026.06'],
                        'series': {'서울': [985.0, 1013.0], '전남광주': [3000.0, 3999.0]}}}
    tot = P.sido_totals(data)
    assert tot['202606'] == {'서울': 1013.0, '전남광주': 3100.0}, tot['202606']
    lines = P.compare(tot, stats)
    assert lines[0] == '2026.05: 같음 2곳, 다름 0곳', lines
    assert lines[1].startswith('2026.06: 같음 1곳, 다름 1곳 (전남광주 3999↔3100)'), lines
    assert lines[2].startswith('2026.07: R-ONE 계열에 없는 달 — 지역 2곳'), lines
    assert 'C2_NM 3개(계·60㎡이하·60~85㎡)' in P.shape(data)

    def get(url, params, timeout=25):
        if url == P.SEARCH_API:
            return []
        return data
    P.candidate('k', get, stats)
    out = capsys.readouterr().out
    assert '::notice title=미분양 대조::DT_MLTM_2080 2026.05: 같음 2곳' in out, out
