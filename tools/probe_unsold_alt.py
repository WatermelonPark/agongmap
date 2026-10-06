# -*- coding: utf-8 -*-
"""미분양 대체 원천 조사(기록만) — KOSIS 국토교통부 미분양 표에 최신 달과 광주·전남(또는 통합 행)이 있는가.

왜(2026-10-06 대표 결정, 로컬 전용 작업과 별개로 클라우드 배치에서 조사): 지금 미분양은 한국부동산원 R-ONE 표
(update_adv_data.SUPPLY_CONF['미분양'], T237973129847263)에서 받는다. 그 표는 2026.07 에 광주·전남 행이 없고
2026.08 은 아직 없어, 배치가 시도가 빠진 달을 통째로 보류하는 규칙(_drop_incomplete) 때문에 화면이 2026.06 에 묶였다.
원천을 바꿀지 정하기 전에, 같은 통계를 KOSIS 가 어디까지·어떤 지역 이름으로 내는지 배치 로그로 본다.

무엇을 하나: KOSIS 통합검색으로 '미분양' 표를 찾고(국토교통부 116), 표마다 최근 몇 달을 받아 '최신 달 · 그 달의
지역 수 · 광주/전남/전남광주 행 유무'를 한 줄씩 찍는다. data.js 는 건드리지 않는다. 키(KOSIS_API_KEY)는 배치에만 있고,
실패해도 배치를 멈추지 않는다(늘 0 으로 끝난다). 결정이 나면 이 도구와 워크플로 한 줄을 걷는다.

사용:  KOSIS_API_KEY=... python tools/probe_unsold_alt.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request

SEARCH_API = 'https://kosis.kr/openapi/statisticsSearch.do'
DATA_API = 'https://kosis.kr/openapi/Param/statisticsParameterData.do'
ORG = '116'                      # 국토교통부
KEYWORD = '미분양'
MAX_TABLES = 6                   # 검색 결과가 많아도 이만큼만 본다(배치 시간)
RECENT = 4                       # 표마다 최근 몇 개 시점
GJ = ('광주', '전남', '전남광주', '광주광역시', '전라남도')


def _get(url, params, timeout=25):
    q = dict(params, method='getList', format='json', jsonVD='Y')
    with urllib.request.urlopen(url + '?' + urllib.parse.urlencode(q), timeout=timeout) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
    if isinstance(data, dict) and data.get('err'):
        raise RuntimeError('KOSIS err %s: %s' % (data.get('err'), data.get('errMsg')))
    return data


def search(key, get=_get):
    """'미분양' 이 이름에 든 국토교통부 표 [(tblId, 표 이름)] — 검색 순서 그대로, 같은 표는 한 번."""
    rows = get(SEARCH_API, {'apiKey': key, 'searchNm': KEYWORD, 'orgId': ORG, 'resultCount': 50}) or []
    out, seen = [], set()
    for r in rows if isinstance(rows, list) else []:
        tbl, nm = r.get('TBL_ID'), r.get('TBL_NM') or ''
        if tbl and r.get('ORG_ID', ORG) == ORG and KEYWORD in nm and tbl not in seen:
            seen.add(tbl)
            out.append((tbl, nm))
    return out


def table_rows(key, tbl, get=_get):
    """최근 RECENT 개 월 자료. 분류 단계가 표마다 달라 objL1 만 → objL2·objL3 까지 넓혀 가며 받는다."""
    base = {'apiKey': key, 'orgId': ORG, 'tblId': tbl, 'itmId': 'ALL', 'prdSe': 'M', 'newEstPrdCnt': RECENT}
    last = None
    for extra in ({'objL1': 'ALL'}, {'objL1': 'ALL', 'objL2': 'ALL'}, {'objL1': 'ALL', 'objL2': 'ALL', 'objL3': 'ALL'}):
        try:
            rows = get(DATA_API, dict(base, **extra))
            if isinstance(rows, list) and rows:
                return rows
        except Exception as e:      # 분류 단계가 안 맞으면 KOSIS 가 err 를 준다 — 다음 모양으로
            last = e
    if last:
        raise last
    return []


def summarize(tbl, nm, rows):
    """표 하나의 한 줄 — 최신 달, 그 달 지역 수, 광주·전남 관련 행 이름."""
    by = {}
    for r in rows:
        p = str(r.get('PRD_DE') or '')
        names = [str(r.get(k) or '') for k in ('C1_NM', 'C2_NM', 'C3_NM')]
        by.setdefault(p, set()).update(n for n in names if n)
    if not by:
        return 'KOSIS %s %s — 자료 없음' % (tbl, nm)
    latest = max(by)
    names = by[latest]
    gj = sorted(n for n in names if any(g in n for g in GJ))
    periods = ','.join(sorted(by))
    return ('KOSIS %s %s — 최신 %s(받은 달 %s), 그 달 분류 %d개, 광주·전남 행: %s'
            % (tbl, nm, latest, periods, len(names), '·'.join(gj) if gj else '없음'))


# ── 대조(2026-10-07): 10-06 첫 조사에서 DT_MLTM_2080(규모별 미분양현황)이 2026.08 까지·'전남광주' 통합 행을 줬다.
# 원천을 바꾸기 전에 그 표의 모양(분류·항목)과, 지금 계열(R-ONE, data.js STATS['미분양'])과 같은 달의 시도 값이 같은지 본다.
CANDIDATE = 'DT_MLTM_2080'
COMPARE_MONTHS = 6
TOTAL_NAMES = ('계', '합계', '소계', '전체', '총계')
_FULL = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주',
         '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '경기도': '경기', '강원도': '강원',
         '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북',
         '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '제주도': '제주'}


def _short(n):
    n = (n or '').strip()
    return _FULL.get(n, n)


def shape(rows):
    """표 모양 한 줄 — 분류 단계별 이름 수와 앞 몇 개, 항목 이름."""
    parts = []
    for k in ('C1_NM', 'C2_NM', 'C3_NM', 'ITM_NM', 'UNIT_NM'):
        names = []
        for r in rows:
            v = str(r.get(k) or '')
            if v and v not in names:
                names.append(v)
        if names:
            parts.append('%s %d개(%s)' % (k, len(names), '·'.join(names[:8])))
    return ' / '.join(parts)


def sido_totals(rows):
    """{YYYYMM: {지역: 값}} — 지역(C1)을 빼고 나머지 분류가 모두 합계 이름이거나 없는 행만 쓴다. 항목이 여럿이면 첫 항목."""
    first_itm = next((str(r.get('ITM_NM') or '') for r in rows), '')
    out = {}
    for r in rows:
        if str(r.get('ITM_NM') or '') != first_itm:
            continue
        rest = [str(r.get(k) or '') for k in ('C2_NM', 'C3_NM') if r.get(k)]
        if any(x not in TOTAL_NAMES for x in rest):
            continue
        try:
            v = float(str(r.get('DT')).replace(',', ''))
        except (TypeError, ValueError):
            continue
        out.setdefault(str(r.get('PRD_DE')), {})[_short(r.get('C1_NM'))] = v
    return out


def compare(tot, stats):
    """R-ONE 계열과 같은 달의 지역 값 대조 — 줄 목록."""
    d = (stats or {}).get('미분양') or {}
    dates, series = d.get('dates') or [], d.get('series') or {}
    lines = []
    for ym in sorted(tot):
        lab = '%s.%s' % (ym[:4], ym[4:6])
        if lab not in dates:
            lines.append('%s: R-ONE 계열에 없는 달 — 지역 %d곳(%s)' % (lab, len(tot[ym]), '·'.join(sorted(tot[ym])[:20])))
            continue
        i = dates.index(lab)
        same, diff = 0, []
        for reg, v in sorted(tot[ym].items()):
            ser = series.get(reg)
            if not ser or i >= len(ser) or ser[i] is None:
                continue
            if abs(ser[i] - v) < 0.5:
                same += 1
            else:
                diff.append('%s %g↔%g' % (reg, ser[i], v))
        lines.append('%s: 같음 %d곳, 다름 %d곳%s' % (lab, same, len(diff), (' (' + ', '.join(diff[:8]) + ')') if diff else ''))
    return lines


def _stats():
    try:
        import month_lag as ML
        return ML.load()[1]
    except Exception as e:
        print('probe_unsold_alt: data.js 를 읽지 못했다 — %s' % e)
        return {}


def candidate(key, get=_get, stats=None):
    base = {'apiKey': key, 'orgId': ORG, 'tblId': CANDIDATE, 'itmId': 'ALL', 'prdSe': 'M', 'newEstPrdCnt': COMPARE_MONTHS}
    rows = None
    for extra in ({'objL1': 'ALL'}, {'objL1': 'ALL', 'objL2': 'ALL'}, {'objL1': 'ALL', 'objL2': 'ALL', 'objL3': 'ALL'}):
        try:
            got = get(DATA_API, dict(base, **extra))
            if isinstance(got, list) and got:
                rows = got
                print('probe_unsold_alt: %s 요청 모양 %s' % (CANDIDATE, ','.join(sorted(extra))))
                break
        except Exception as e:
            print('probe_unsold_alt: %s %s — %s' % (CANDIDATE, ','.join(sorted(extra)), str(e)[:120]))
    if not rows:
        print('::notice title=미분양 대조::%s 를 받지 못했다' % CANDIDATE)
        return
    print('::notice title=미분양 표 모양::%s — %s' % (CANDIDATE, shape(rows)))
    for ln in compare(sido_totals(rows), _stats() if stats is None else stats):
        print('::notice title=미분양 대조::%s %s' % (CANDIDATE, ln))


def main(get=_get, key=None):
    key = os.environ.get('KOSIS_API_KEY', '') if key is None else key
    if not key:
        print('probe_unsold_alt: KOSIS_API_KEY 없음 — 건너뜀')
        return 0
    try:
        tables = search(key, get)
    except Exception as e:
        print('probe_unsold_alt: 검색 실패 — %s: %s' % (type(e).__name__, str(e)[:160]))
        tables = []
    if not tables:
        print('probe_unsold_alt: 국토교통부 표 가운데 이름에 "%s" 가 든 표를 찾지 못했다' % KEYWORD)
    for tbl, nm in tables[:MAX_TABLES]:
        try:
            line = summarize(tbl, nm, table_rows(key, tbl, get))
        except Exception as e:
            line = 'KOSIS %s %s — 조회 실패 %s: %s' % (tbl, nm, type(e).__name__, str(e)[:120])
        # ::notice:: 는 실행 요약에 남아 로그를 열지 않아도 보인다
        print('::notice title=미분양 대체 원천 조사::' + line)
    if len(tables) > MAX_TABLES:
        print('probe_unsold_alt: 표 %d개 중 앞 %d개만 봤다' % (len(tables), MAX_TABLES))
    try:                     # 검색이 실패해도 후보 표 대조는 따로 돈다(표 ID 를 안다)
        candidate(key, get)
    except Exception as e:
        print('probe_unsold_alt: 대조 실패 — %s: %s' % (type(e).__name__, str(e)[:160]))
    return 0

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:          # 곁가지 — 무엇이 터져도 배치를 멈추지 않는다
        print('probe_unsold_alt: 예기치 않은 실패 — %s: %s' % (type(e).__name__, str(e)[:160]))
        raise SystemExit(0)
