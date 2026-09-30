# -*- coding: utf-8 -*-
"""감시 원천 조회의 모양 — 쪽 나눔·조회 실패 분류·배치와 같은 인자(전수리뷰 #35·#36·#38·#40·#109).

다른 감시 시험은 원천 함수(rone_region_names·rone_latest_complete…)를 통째로 가짜로 바꾼다. 그래서 그 함수들
안의 쪽 나눔, 실패 분류, 조회 인자는 한 번도 시험되지 않았다. 여기서는 더 아래(get_json·urlopen)를 가짜로 두고
진짜 함수를 돌린다.

픽스처 get_json(_pager)은 R-ONE OpenAPI 의 실제 모양을 따른다: 행은 시점 오름차순으로 쌓이고, START_WRTTIME 이
있으면 그 시점부터만 세며, pIndex·pSize 로 1000행씩 자른다(pSize=1 이면 머리의 list_total_count 만 본다). 창이
통째로 비면 표 블록 대신 {'RESULT': {'CODE': 'INFO-200'}} 가 온다.
"""
import copy
import datetime
import io
import os
import sys
import urllib.error
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import check_freshness as C  # noqa: E402

U = C.U


def _pager(rows, tkey, calls=None):
    def get_json(url):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if calls is not None:
            calls.append(q)
        rs = rows
        if 'START_WRTTIME' in q:
            s = q['START_WRTTIME']
            rs = [r for r in rs if C.digits(r[tkey])[:len(s)] >= s]
        if not rs:
            return {'RESULT': {'CODE': 'INFO-200'}}
        pi, ps = int(q['pIndex']), int(q['pSize'])
        return {'SttsApiTblData': [{'head': [{'list_total_count': len(rs)}]},
                                   {'row': rs[(pi - 1) * ps: pi * ps]}]}
    return get_json


# ---------------------------------------------------------------------------
# #35 지역 계층 — 최신 한 시점의 이름만 본다
# ---------------------------------------------------------------------------

WEEKS = ['2026-08-24', '2026-08-31', '2026-09-07', '2026-09-14', '2026-09-21']
BASE = [{'지방': '지방권'}.get(z, z) for z in U.WEEKLY_REGIONS]
GUS = ['서울>도심권>G%02d구' % i for i in range(25)]
# 한 주 236행(배치 주석의 실측)을 채우는 시군구 행
FILL = ['경기>시%03d' % i for i in range(236 - len(BASE) - len(GUS))]


def _week_rows(name_of, weeks=WEEKS, old=0):
    rows = [{'WRTTIME_DESC': '2020-01-06', 'CLS_FULLNM': 'X%d' % i} for i in range(old)]
    for w in weeks:
        rows += [{'WRTTIME_DESC': w, 'CLS_FULLNM': n} for n in name_of(w)]
    return rows


def _regions(monkeypatch, rows, since='20260801'):
    """주간 표 하나(월간도 같은 함수)를 rows 로 돌려 check_region_rows 결과를 본다."""
    monkeypatch.setattr(C, 'get_json', _pager(rows, 'WRTTIME_DESC'))
    monkeypatch.setattr(C, '_region_since', lambda cycle: since)
    C.FETCH_FAIL[:] = []
    names = C.rone_region_names('T', 'WK')
    fails = C.check_region_rows(fetch=lambda t, c: names)
    assert C.FETCH_FAIL == []
    return names, fails


def test_rename_in_the_newest_week_is_caught(monkeypatch):
    """(a) 최신 주에서만 R-ONE 이 '전남광주' 묶음 이름을 바꿨다. 배치 sido() 는 그 주를 못 집어 광주·전남이
    None 이 되는데, 앞 주 행의 옛 이름이 같은 쪽에 섞여 있으면 감시가 통과했다.

    변이(확인): rone_region_names 가 시점을 가리지 않고 모든 행의 이름을 모으게(`by[max(by)]` → 모든 집합의 합집합)
    바꾸면 결측이 사라져 빨개진다.
    예전 구현(창 없이 표 전체의 마지막 쪽)도 이 픽스처에서 빨개진다: 마지막 쪽 708행에 세 주가 섞인다.
    픽스처: 창 밖 옛 행 1000개 + 세 주. 앞 두 주는 '전남광주', 최신 주만 '광주전남' — 2026-07 에 '전남광주'가 새로 생긴 것과 같은 종류의 개편.
    """
    def name_of(w):
        if w == WEEKS[-1]:
            return [('광주전남' if n == '전남광주' else n) for n in BASE] + GUS + FILL
        return BASE + GUS + FILL
    names, fails = _regions(monkeypatch, _week_rows(name_of, WEEKS[-3:], old=1000))
    assert '전남광주' not in names
    assert any('지역 결측' in f and '전남광주' in f for f in fails), fails


def test_mid_level_change_across_weeks_is_not_a_gu_collision(monkeypatch):
    """(b) 서울 중간 계층이 앞 주와 최신 주에서 다르다. 한 주 안에서는 구 이름이 겹치지 않고 배치 seoul_gu 도
    한 주씩 돌아 멀쩡하다 — 감시가 두 주를 섞으면 25개 구 전부에 '이름 충돌' 결정론 red 를 냈다.

    변이(확인): 위와 같은 '모든 시점 합집합' 변이로 25건의 충돌이 나와 빨개진다.
    픽스처: 앞 주 '서울>강북지역>도심권>X구', 최신 주 '서울>도심권>X구'.
    """
    def name_of(w):
        g = GUS if w == WEEKS[-1] else [x.replace('서울>', '서울>강북지역>') for x in GUS]
        return BASE + g + FILL
    _, fails = _regions(monkeypatch, _week_rows(name_of, WEEKS[-3:], old=1000))
    assert fails == [], fails


def test_newest_week_split_across_pages_is_read_whole(monkeypatch):
    """(c) 창 안의 행이 1000을 넘어 최신 주가 두 쪽에 걸친다(5주 × 236 = 1180행 → 마지막 쪽 180행). 마지막 쪽만
    읽으면 최신 주의 앞 행(전국·수도권…)이 빠져 '지역 결측' 오탐이 났다.

    변이(확인): _rone_rows 가 마지막 쪽 하나만 읽게(`while p >= 1 and …` 루프를 한 번만 돌게) 바꾸면 빨개진다.
    픽스처: 창(2026-08-01~) 안에 다섯 주, 창 밖 옛 행 1000개 — 실제 주간 표(16만 행)의 뒤쪽 모양.
    """
    _, fails = _regions(monkeypatch, _week_rows(lambda w: BASE + GUS + FILL, old=1000))
    assert fails == [], fails


def test_empty_window_falls_back_to_the_tail_of_the_whole_table(monkeypatch):
    """창이 통째로 비면(원천이 한참 뒤처짐) 전량으로 되돌려 뒤에서부터 읽는다. 예외를 던지면 조회 실패로 읽힌다.

    변이(확인): _rone_rows 의 `if since: return _rone_rows(tbl, cycle)` 폴백을 지우면 RuntimeError 로 빨개진다.
    픽스처: 창이 미래(2099)로 잡힌 경우 — 조회 대상 주들은 전부 창 앞에 있다.
    """
    names, fails = _regions(monkeypatch, _week_rows(lambda w: BASE + GUS + FILL, old=2500),
                            since='20990101')
    assert fails == [] and '전국' in names


def test_region_window_comes_from_the_batch_helper(monkeypatch):
    """창 계산은 배치와 같은 함수(U._rone_since)다 — 주간은 YYYYMMDD, 월간은 YYYYMM."""
    assert C._region_since('WK') == U._rone_since('WK', C.REGION_WINDOW['WK'])
    assert C._region_since('MM') == U._rone_since('MM', C.REGION_WINDOW['MM'])
    assert len(C._region_since('WK')) == 8 and len(C._region_since('MM')) == 6


# ---------------------------------------------------------------------------
# #36 공급 완비 판정 — 창의 모든 쪽
# ---------------------------------------------------------------------------

SIDO = [z for z in U.WEEKLY_REGIONS if z not in ('전국', '수도권', '지방')]


def _unsold_rows(months, gone_from):
    """미분양표 모양: 시도마다 '<시도>>계' 1행 + 시군구 13행(달마다 ~230행). gone_from 부터 광주·전남이 없다."""
    rows = []
    for m in months:
        for z in SIDO:
            parts = list(U._GJ_OLD) if z == U._GJ_NEW else [z]
            if z == U._GJ_NEW and m >= gone_from:
                continue
            for p in parts:
                rows.append({'WRTTIME_IDTFR_ID': m, 'CLS_FULLNM': p + '>계', 'DTA_VAL': '10'})
                rows += [{'WRTTIME_IDTFR_ID': m, 'CLS_FULLNM': '%s>X%d' % (p, i), 'DTA_VAL': '1'}
                         for i in range(13)]
    return rows


def test_held_supply_month_survives_a_window_over_one_page(monkeypatch):
    """배치는 원천 7월분부터 광주·전남 행이 없어 미분양을 2026.06 에 일부러 멈춰 둔다(백로그 4). since 는 '우리 시점
    −1달'로 고정되므로 원천이 앞서 나갈수록 창이 커진다. 9월분이 나와 창이 1000행을 넘으면 마지막 쪽에는 미완비
    9월의 꼬리만 남아, 감시가 9월을 '완비 최신'으로 읽고 의도된 보류를 매일 결정론 red 로 냈다.

    변이(확인): _rone_rows 를 마지막 쪽 하나만 읽게 되돌리면 '202609' 로 빨개진다.
    픽스처: 2026.05~09 다섯 달(1100행 남짓, 두 쪽), 07월부터 광주·전남 없음 — 원천 9월분 발표 뒤의 실제 상태.
    """
    rows = _unsold_rows(['202605', '202606', '202607', '202608', '202609'], '202607')
    assert len(rows) > C.RONE_PAGE
    monkeypatch.setattr(C, 'get_json', _pager(rows, 'WRTTIME_IDTFR_ID'))
    monkeypatch.setattr(C, '_COMPLETE_CACHE', {})
    since = C._supply_since('2026.06')
    assert C.rone_latest_complete('T', since) == '202606'
    # 그 달과 견주면 보류는 뒤처짐이 아니다.
    assert C.check('미분양', '2026.06', lambda: C.rone_latest_complete('T', since),
                   C.GRACE_MONTHLY) is None


# ---------------------------------------------------------------------------
# #38 파생 페이지·공유 카드의 조회 실패 분류
# ---------------------------------------------------------------------------

class _Body:
    def __init__(self, b):
        self.b = b

    def read(self):
        return self.b.encode('utf-8')


def _web(fault):
    """fault = {주소 조각: 'timeout' | 404}. 나머지는 정상 페이지."""
    def urlopen(req, timeout=0):
        url = req.full_url
        for part, how in fault.items():
            if part in url:
                if how == 'timeout':
                    raise TimeoutError('timed out')
                raise urllib.error.HTTPError(url, how, 'Not Found', {}, None)
        if '/zone/' in url:
            return _Body('<p>2026.06 기준 · 분기 적정물량</p>')
        if '/jeonse-ratio/' in url:
            return _Body('<p>2026.06 기준</p>')
        return _Body('<div class="note">2025년 1분기까지 준공 실적</div>')
    return urlopen


def _gate_after_derived(monkeypatch, fault):
    monkeypatch.setattr(C.urllib.request, 'urlopen', _web(fault))
    for lst in (C.SKIPPED, C.FETCH_FAIL, C.RETRYQ):
        lst.clear()
    adv = {'sido': {'zones': [{'z': '서울'}, {'z': '제주'}], 'unsold_prd': '2026.06'},
           'occupancy': {'rows': [{'p': '2025Q1', 'e': False}]}}
    stats = {'전세가율': {'dates': ['2026.06'], 'series': {}}}
    fails = [None] * 17 + C.check_derived_pages(adv, stats)
    try:
        with pytest.raises(SystemExit) as e:
            C._gate(fails)
        return e.value.code, fails
    finally:
        for lst in (C.SKIPPED, C.FETCH_FAIL, C.RETRYQ):
            lst.clear()


def test_zone_page_timeout_is_retryable_not_final(monkeypatch):
    """지역 페이지 한 장이 15초 타임아웃에 걸린 것은 망 사정이다. 예전엔 bad 에 들어가 '원천 조회는 전부 성공 ·
    생성기가 실패했거나 배포가 안 된 것'이라는 결정론 red(rc 2)로 즉시 경보했다.

    변이(확인): _hard_http 를 `return True`(모두 결정론)로 바꾸면 rc 가 2 가 되어 빨개진다.
    픽스처: /zone/제주/ 만 socket 타임아웃, 나머지 페이지는 정상.
    """
    rc, fails = _gate_after_derived(monkeypatch, {urllib.parse.quote('제주'): 'timeout'})
    assert rc == C.EXIT_RETRYABLE
    assert not [f for f in fails if f], '망 오류를 데이터 실패로 올렸다'


@pytest.mark.parametrize('part', ['/jeonse-ratio/', '/moveins/', urllib.parse.quote('제주')])
def test_missing_page_404_is_a_deterministic_failure(monkeypatch, part):
    """HTTP 404 는 파일이 배포에서 빠진 결정론적 사고다. 예전엔 전세가율·입주물량 404 가 SKIPPED '참고' 한 줄로
    VERDICT=ok 초록이었다.

    변이(확인): _hard_http 를 `return False`(모두 망 오류)로 바꾸면 전세가율·입주물량은 rc 0(초록), 지역 페이지는
    rc 1 이 되어 빨개진다.
    픽스처: 해당 페이지 하나만 404, 나머지 정상.
    """
    rc, fails = _gate_after_derived(monkeypatch, {part: 404})
    assert rc == C.EXIT_DETERMINISTIC
    assert any('404' in f for f in fails if f), fails


# ---------------------------------------------------------------------------
# #40·#109 배치와 같은 원천 조회 인자·같은 '최신 달' 규칙
# ---------------------------------------------------------------------------

class _Stop(Exception):
    pass


def _ecos_code(url):
    """ECOS StatisticSearch 주소 → (통계표, 주기, 항목)."""
    parts = urllib.parse.urlsplit(url).path.rstrip('/').split('/')
    return parts[-5], parts[-4], parts[-1]


def test_cd_rate_query_matches_the_batch(monkeypatch):
    """감시 ecos_latest() 와 배치 update_rate() 가 같은 ECOS 계열(통계표·주기·항목)을 부른다.

    변이(확인): C.RATE_ECOS 의 항목을 '2010001' 로 바꾸면 빨개진다(배치 쪽 문자를 바꿔도 마찬가지).
    픽스처: 두 함수의 HTTP 호출을 가로채 실제로 만든 주소만 본다(원천에는 나가지 않는다).
    """
    seen = {}
    monkeypatch.setattr(U, 'ECOS_KEY', 'k')

    def batch_http(url, tries=3):
        seen['batch'] = url
        raise _Stop

    def wd_get(url):
        seen['wd'] = url
        raise _Stop
    monkeypatch.setattr(U, 'http_json', batch_http)
    monkeypatch.setattr(C, 'get_json', wd_get)
    with pytest.raises(_Stop):
        U.update_rate({'금리': {}})
    with pytest.raises(_Stop):
        C.ecos_latest()
    assert _ecos_code(seen['batch']) == _ecos_code(seen['wd']) == C.RATE_ECOS


def test_size_query_matches_the_batch(monkeypatch):
    """감시 '규모별' 조회와 배치 update_size() 가 같은 기관·표·objL1(규모 전체)을 부른다.

    변이(확인): C.SIZE_KOSIS 의 objL1 을 '02' 로 바꾸면 빨개진다.
    픽스처: 배치 kosis() 와 감시 get_json 을 가로채 첫 조회의 인자만 본다.
    """
    seen = {}

    def batch_kosis(params):
        seen['batch'] = params
        raise _Stop

    def wd_get(url):
        seen['wd'] = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        raise _Stop
    monkeypatch.setattr(U, 'kosis', batch_kosis)
    monkeypatch.setattr(C, 'get_json', wd_get)
    with pytest.raises(_Stop):
        U.update_size({})
    with pytest.raises(_Stop):
        C.source_jobs({'규모별': {}})['규모별']()
    for k in ('orgId', 'tblId', 'objL1'):
        assert seen['batch'][k] == seen['wd'][k], k


def _bubble_rows(aug='half'):
    """전월세전환율 응답: 06월은 19곳, 07월은 광주·전남 옛 이름 두 행(→ 전남광주 한 곳)으로 19곳, 08월은 먼저 일부만
    올라온 달, 그리고 아파트가 아닌 행·시군구 행. 배치가 07월을 쓰는 모양이다. 08월 모양(aug):
      'half'  — 절반(9곳)만(옛 두 문턱 모두 못 넘는 달)
      'one'   — 한 곳(제주)만 빠진 18곳(옛 감시 문턱 '10곳 이상'은 넘고 배치 '모델 전부'는 못 넘는 달)
      'gj'    — 전남광주 자리에 광주 조각만 온 19곳(옛 감시는 한 조각도 전남광주로 셌다)"""
    names = {v: k for k, v in U.BUBBLE_SHORT.items()}
    rows = []

    def add(prd, rg, c1='아파트', code=None):
        rows.append({'PRD_DE': prd, 'C1_NM': c1, 'C2_NM': names.get(rg, rg),
                     'C2': code or 'a%02d' % (len(rows) % 90), 'DT': '5.1'})
    rest = [r for r in U.BUBBLE_REGIONS if r != U._GJ_NEW]
    aug_regs = {'half': U.BUBBLE_REGIONS[:len(U.BUBBLE_REGIONS) // 2],
                'one': [r for r in U.BUBBLE_REGIONS if r != U.BUBBLE_REGIONS[-1]],
                'gj': rest + [U._GJ_OLD[0]]}[aug]
    for prd, regs in (('202606', U.BUBBLE_REGIONS),
                      ('202607', rest + list(U._GJ_OLD)),
                      ('202608', aug_regs)):
        for rg in regs:
            add(prd, rg)
        add(prd, '서울', c1='연립다세대')
        add(prd, '수원시', code='a150101')
    return rows


def _loan_rows():
    return [{'TIME': t, 'DATA_VALUE': v} for t, v in (('202605', '4.3'), ('202606', '4.4'),
                                                     ('202607', '4.48'))]


@pytest.mark.parametrize('aug', ['half', 'one', 'gj'])
def test_bubble_watchdog_reads_the_same_month_as_the_batch(monkeypatch, aug):
    """감시(bubble_conv_latest·ecos_latest(BUBBLE_ECOS))가 배치 fetch_bubble 과 같은 달을 '원천 최신'으로 본다.
    기준이 갈리면 배치가 일부러 안 쓴 반쪽 달을 감시가 뒤처짐으로 읽거나, 반대로 진짜 뒤처짐을 놓친다. 두 코드는
    응답 해석(U.bubble_conv_by_prd)과 완비 판정(U.bubble_full_months)을 한 함수로 쓴다.

    변이(확인): 감시를 옛 규칙('10곳 이상', 한 조각도 전남광주)으로 되돌리면 'one'·'gj' 가, 배치 완비 판정을 옛
    `len(by_prd[p]) >= 10` 으로 되돌리면 'one'·'gj' 가 빨개진다(통합 검토 전에는 08월이 9곳뿐인 'half' 하나라
    두 변이 모두 초록이었다). 조회 인자를 바꿔도(C.BUBBLE_ECOS 의 항목을 'BECBLA0301' 로) 인자 단정이 빨개진다.
    픽스처: _bubble_rows(08월은 일부만 먼저 올라온 달 세 모양)와 주담대 금리 07월까지 — 2026-09 운영 데이터(prd·loan.p
    2026.07)와 같은 모양.
    """
    kosis_rows, loan_rows = _bubble_rows(aug), _loan_rows()
    seen = {}
    monkeypatch.setattr(U, 'KEY', 'k')
    monkeypatch.setattr(U, 'ECOS_KEY', 'k')

    def batch_kosis(params):
        seen['bk'] = params
        return copy.deepcopy(kosis_rows)

    def batch_http(url, tries=3):
        seen['be'] = url
        return {'StatisticSearch': {'row': copy.deepcopy(loan_rows)}}

    def wd_get(url):
        if 'kosis.kr' in url:
            seen['wk'] = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            return copy.deepcopy(kosis_rows)
        seen['we'] = url
        return {'StatisticSearch': {'row': copy.deepcopy(loan_rows)}}
    monkeypatch.setattr(U, 'kosis', batch_kosis)
    monkeypatch.setattr(U, 'http_json', batch_http)
    monkeypatch.setattr(C, 'get_json', wd_get)

    bub = U.fetch_bubble()
    assert C.digits(bub['prd']) == C.bubble_conv_latest() == '202607'
    assert C.digits(bub['loan']['p']) == C.ecos_latest(C.BUBBLE_ECOS) == '202607'
    for k in ('orgId', 'tblId', 'objL1', 'objL2', 'prdSe', 'newEstPrdCnt'):
        assert str(seen['bk'][k]) == seen['wk'][k], k
    assert _ecos_code(seen['be']) == _ecos_code(seen['we']) == C.BUBBLE_ECOS


@pytest.mark.parametrize('label,ours,today,src,grace', [
    ('전월세전환율', '2026.05', (2026, 9, 10), '202606', 'GRACE_BUBBLE_CONV'),   # 나이 132일
    ('전월세전환율', '2026.06', (2026, 9, 28), '202607', 'GRACE_BUBBLE_CONV'),   # 나이 119일
    ('주담대 금리', '2026.06', (2026, 8, 26), '202607', 'GRACE_BUBBLE_LOAN'),    # 나이 86일
])
def test_bubble_grace_covers_the_measured_release_lag(monkeypatch, label, ours, today, src, grace):
    """버블밴드 두 계열은 원천에 새 달이 올라온 날(2026 실측) 우리 값이 이미 50일을 넘는다 — 그날 감시가 배치보다
    먼저 돌면(감시 예약 18:07 KST) GRACE_MONTHLY 로는 곧바로 실패 메일이었다(통합 검토). 발표 당일은 유예 안이고,
    배치가 한 달을 통째로 놓쳐 유예를 넘기면 실패다.

    변이(실제로 확인): main 의 버블 두 줄을 GRACE_MONTHLY 로 되돌리거나 GRACE_BUBBLE_CONV 를 100 으로 줄이면 빨개진다.
    픽스처: 2026 발표일의 실측 나이(전환율 09-10·09-28, 주담대 08-26)와 원천이 한 달 앞선 상태.
    """
    g = getattr(C, grace)
    monkeypatch.setattr(C, 'TODAY', datetime.date(*today))
    assert C.check(label, ours, lambda: src, g, _retry=False) is None
    late = datetime.date(*today) + datetime.timedelta(days=g - C.age_days(ours) + 1)
    monkeypatch.setattr(C, 'TODAY', late)
    assert C.check(label, ours, lambda: src, g, _retry=False), '유예를 넘긴 뒤처짐을 놓쳤다'
    body = io.open(C.__file__, encoding='utf-8').read()
    assert "pre[('bubble', '%s')], %s)" % ('전환율' if grace.endswith('CONV') else '주담대', grace) in body


def test_every_live_adv_key_is_classified():
    """커버리지 가드의 ADV 목록이 라이브 ADV 키를 전부 분류한다(감시하거나, 이유를 적고 빼거나).

    변이(확인): ADV_WATCHED 에서 'bubble' 을 빼면 빨개진다(main() 의 가드도 '감시 누락 ADV 키 bubble' 로 실패한다).
    픽스처: 저장소의 data.js ADV 블록 — 배치가 쓰는 실제 키.
    """
    import json
    import re
    root = os.path.join(os.path.dirname(__file__), '..', '..')
    t = open(os.path.join(root, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'/\*ADV_DATA_START\*/const ADV=(\{.*?\});', t, re.S).group(1))
    assert not set(C.ADV_WATCHED) & set(C.ADV_UNWATCHED)
    assert set(adv) <= set(C.ADV_WATCHED) | set(C.ADV_UNWATCHED), \
        sorted(set(adv) - set(C.ADV_WATCHED) - set(C.ADV_UNWATCHED))
    assert 'bubble' in C.ADV_WATCHED


# ---------------------------------------------------------------------------
# R-ONE 쪽 읽기 — 연결이 끊기면 다시 받고, 쪽 사이를 쉰다(배치와 같은 방식)
# ---------------------------------------------------------------------------

def test_rone_pages_retry_a_dropped_connection_and_pause(monkeypatch):
    """R-ONE 이 요청을 응답 없이 끊어도(RemoteDisconnected) 감시는 그 쪽을 다시 받아 지역 계층을 판정한다. 쪽 사이를 쉰다.

    재현하는 실제 상태: #35 로 창의 모든 쪽을 연달아 읽게 된 뒤 첫 감시(2026-10-01 00:52·00:55 KST)에서 두 러너 모두
    주간·월간 지역 목록 조회가 'Remote end closed connection without response' 로 끊겨 감시가 빨갛게 끝났다(다른 원천
    대조는 모두 초록). 배치는 같은 조회를 http_json(tries=3)과 쪽 사이 0.15초 쉼으로 받아 왔다.
    픽스처: _pager 가 쪽마다 첫 요청을 RemoteDisconnected 로 끊고 둘째 요청에 답한다(한 주 236행 × 5주 = 2쪽).
    변이(실제로 확인): _rone_get 의 다시 받기를 빼면(get_json 한 번) RemoteDisconnected 로 빨개지고, _rone_rows 의 쪽 사이
    쉼을 빼면 쉼 단정이 빨개진다. 4xx 를 다시 받게 하면 404 단정(요청 한 번)이 빨개진다.
    """
    import http.client
    rows = _week_rows(lambda w: BASE + GUS + FILL)
    inner, seen, sleeps = _pager(rows, 'WRTTIME_DESC'), {}, []

    def flaky(url):
        seen[url] = seen.get(url, 0) + 1
        if seen[url] == 1:
            raise http.client.RemoteDisconnected('Remote end closed connection without response')
        return inner(url)
    monkeypatch.setattr(C, 'get_json', flaky)
    monkeypatch.setattr(C.time, 'sleep', lambda s: sleeps.append(s))
    monkeypatch.setattr(C, '_region_since', lambda cycle: '20260801')
    names = C.rone_region_names('T', 'WK')
    assert set(BASE) <= names, sorted(names)[:5]
    assert all(n == 2 for n in seen.values()), seen
    assert C.RONE_PAGE_PAUSE in sleeps, '쪽 사이를 쉬지 않는다'

    calls = []

    def missing(url):
        calls.append(url)
        raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)
    monkeypatch.setattr(C, 'get_json', missing)
    with pytest.raises(urllib.error.HTTPError):
        C.rone_region_names('T', 'WK')
    assert len(calls) == 1, '4xx 를 다시 받았다 — 결정론적 답이다'
