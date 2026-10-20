# -*- coding: utf-8 -*-
"""저장분 정합 검사(합계 관계 4종) — 굳은 과거를 잡는 유일한 장치.

나이·원천 대조는 **최신 시점 하나**만 본다. 모든 수집이 '최근 N개'만 다시 받으므로
그 창 밖 과거는 최초 시딩 판본이 영구히 굳는데, 2026-08-08 감사에서 전세가율
2,593셀·매매지수 6,041셀·주간 시세 360행이 그렇게 굳어 있던 게 드러났다. 그때까지
감시는 매일 OK였다 — '언제 것이냐'는 보면서 '무슨 값이냐'는 아무도 안 봤다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import check_freshness as C


def _stats(nat, over=None, name='준공'):
    """전국·수도권·지방 + 16시도를 모두 갖춘 STATS를 만든다.

    행이 빠지면 검사가 '축없음'으로 건너뛰므로, 합계 규칙을 시험하려면 전 축이
    있어야 한다. nat은 전국 시계열이고, 기본 배분은 서울이 전부 가져간다.
    over로 특정 행만 덮어쓴다.
    """
    n = len(nat)
    ser = {'전국': list(nat), '수도권': list(nat), '지방': [0] * n,
           '서울': list(nat)}
    for r in C.SIDO17:
        ser.setdefault(r, [0] * n)
    for r, v in (over or {}).items():
        ser[r] = list(v)
    return {name: {'dates': ['2011.%02d' % (i + 1) for i in range(n)], 'series': ser}}


def test_clean_data_passes():
    assert C.check_sido_sum(_stats([30, 40])) == []


def test_catches_a_corrupted_past_cell():
    """창 밖 과거가 굳어 원천과 갈라진 상황 — 정확히 이걸 잡으려고 만들었다."""
    st = _stats([30, 40], {'서울': [30 + 5000, 40], '수도권': [30 + 5000, 40]})
    fails = C.check_sido_sum(st)
    assert any('2011.01' in f for f in fails), fails
    assert any('--heal-basic' in f for f in fails), '교정 방법을 안내해야 한다'


def test_null_counts_as_zero():
    """KOSIS의 null은 결측이 아니라 0이다(시도합÷전국이 모든 연도 1.00으로 증명).
    None을 건너뛰면 합이 모자라 오탐이 난다."""
    st = _stats([30], {'서울': [30], '경기': [None]})
    assert C.check_sido_sum(st) == []


def test_skips_periods_before_a_series_starts():
    """계열이 시작되기 전 구간은 전국 행도 None이다 — 0이 아니므로 판정에서 뺀다
    (세종 2012.07 출범)."""
    st = _stats([None, 40], {'서울': [None, 40], '수도권': [None, 40],
                             '지방': [None, 0], '전국': [None, 40]})
    assert C.check_sido_sum(st) == []


def test_rounding_slack_does_not_alarm():
    """소수 계열은 반올림으로 1 미만 차가 생긴다 — 그걸로 매일 red를 만들면
    감시가 무시된다."""
    st = _stats([30.0], {'서울': [10.4], '경기': [19.9], '수도권': [30.0]})
    assert C.check_sido_sum(st) == []


def test_aggregate_rules_localize_the_corruption():
    """시도합=전국 하나만 보면 '어딘가 틀렸다'까지다. 집계 관계를 함께 보면
    수도권/지방 중 어느 쪽인지 갈려 범위가 1/3로 줄어든다."""
    cap = C.check_sido_sum(_stats([30], {'서울': [37], '경기': [0], '인천': [0]}))
    assert any('수도권' in f for f in cap), cap
    assert not any('지방=' in f for f in cap), '엉뚱한 쪽까지 짚으면 좁히는 의미가 없다'

    loc = C.check_sido_sum(_stats([30], {'서울': [30], '부산': [7]}))
    assert any('지방' in f for f in loc), loc
    assert not any('수도권=' in f for f in loc)


def test_missing_sido_row_is_reported_as_such():
    """시도 행이 통째로 사라진 것 자체가 사고다(2026-08-06 세종이 존 매핑에서
    소거된 전례). 원인이 '값이 틀렸다'가 아니라 '행이 없다'라는 걸 말해줘야 한다."""
    st = _stats([30])
    del st['준공']['series']['세종']
    fails = C.check_sido_sum(st)
    assert any('시도 행 결측' in f and '세종' in f for f in fails), fails


def test_missing_row_does_not_become_a_false_sum_alarm():
    """없는 행을 0으로 세고 비교하면 '값이 틀렸다'는 오탐이 된다 — 그 규칙은
    건너뛰고 결측만 보고해야 한다.

    결측 보고까지 본다(전수리뷰 #39). 예전엔 '(축없음)' 표시만 하고 실패로 올리지 않아 이 시험이 '오탐 없음'만
    확인하며 초록이었다. 변이(확인): check_sido_sum 의 agg_gone 보고를 지우면 빨개진다.
    """
    st = _stats([30])
    del st['준공']['series']['수도권']
    fails = C.check_sido_sum(st)
    assert not any('수도권=' in f for f in fails), fails
    assert any('집계 행 결측' in f and '수도권' in f for f in fails), fails


def test_latest_national_cell_missing_is_reported():
    """최신 달 전국 칸만 None 이다. merge_basic 은 새 달을 전 지역 None 열로 만든 뒤 원천이 준 지역만 채우므로,
    KOSIS 가 '총계' 행을 빼거나 이름을 바꾸면 이 모양이 된다 — 기본 탭인 전국의 최신 달이 빈다.

    변이(확인): 집계 칸 구멍 검사(`holes`)를 지우면 빨개진다(예전엔 None 칸을 위치 불문 건너뛰어 [] 였다).
    픽스처: 전 축이 갖춰진 두 달에서 전국 마지막 칸만 None.
    """
    st = _stats([30, 40])
    st['준공']['series']['전국'][-1] = None
    fails = C.check_sido_sum(st)
    assert any('전국 칸 결측' in f and '2011.02' in f for f in fails), fails


def test_short_national_column_is_a_hole_too():
    """전국 열이 다른 열보다 짧다(끝 칸이 아예 없다) — None 과 같은 결측이다.

    변이(확인): holes 조건에서 `i >= len(col)` 을 지우면 빨개진다.
    픽스처: 두 달 중 전국 열만 한 칸.
    """
    st = _stats([30, 40])
    st['준공']['series']['전국'] = [30]
    fails = C.check_sido_sum(st)
    assert any('전국 칸 결측' in f for f in fails), fails


def test_missing_national_row_is_not_silently_skipped():
    """전국 행이 통째로 없으면 예전엔 그 계열이 출력 줄도 남기지 않고 빠졌다(초록).

    변이(확인): 계열 머리의 `continue` 조건에 `not ser.get('전국')` 을 되살리면 빨개진다.
    픽스처: 인허가에서 전국 행만 삭제.
    """
    st = _stats([30], name='인허가')
    del st['인허가']['series']['전국']
    fails = C.check_sido_sum(st)
    assert any('인허가 집계 행 결측' in f and '전국' in f for f in fails), fails


def test_rule_set_does_not_shrink_silently():
    """대상 계열·규칙이 줄면 검사가 꺼진 줄 모른다. 검사 대상 시도(SIDO17)는 판정 모델의 시도 전부(SZ.ORDER 에서 집계 셋만 뺀
    것)여야 한다 — 손으로 센 '16'을 박지 않는다(모델이 바뀌면 이 숫자만 따로 고쳐야 했다. 2026-09-10 광주·전남 통합 때 그랬다).
    모델 자체에서 지역이 조용히 빠지는 일은 test_live_data_satisfies_every_rule 이 실데이터 '시도합=전국'으로 잡는다.

    변이(각각 실제로 확인): check_freshness 의 SIDO17 에서 한 곳을 빼면(`[:-1]`) 이 시험과 실데이터 규칙 시험이 함께 빨개진다.
          SUM_SERIES·SUM_RULES 에서 하나를 빼도 빨개진다.
    픽스처: check_freshness 의 규칙 상수와 판정 모델(sido_zones.ORDER·AGG).
    """
    import sido_zones as SZ
    assert set(C.SUM_SERIES) == {'준공', '착공', '인허가', '분양', '미분양'}
    assert len(C.SUM_RULES) == 4
    want = [z for z in SZ.ORDER if z not in SZ.AGG]
    assert want and C.SIDO17 == want, '감시가 판정 모델의 시도 일부만 더한다: 빠짐 %s' % sorted(set(want) - set(C.SIDO17))


def test_sido17_excludes_aggregate_rows():
    """저장분에는 집계 행이 섞여 있다(STATS 22곳 · ADV.sido 20곳). 같이 더하면
    이중계상이라 전국의 세 배가 나온다 — 17은 실제 행정구역만이라는 뜻이다."""
    for agg in ('전국', '수도권', '지방', '기타광역시', '기타지방'):
        assert agg not in C.SIDO17
    assert set(C.CAPITAL3) == {'서울', '경기', '인천'}
    assert set(C.CAPITAL3) | set(C.LOCAL14) == set(C.SIDO17)
    assert not (set(C.CAPITAL3) & set(C.LOCAL14)), '수도권과 지방이 겹치면 이중계상'


def test_live_data_satisfies_every_rule():
    """실제 저장분에서 성립하는지 — 여기서 깨지면 데이터가 오염된 것이다."""
    import io
    import json
    import re
    root = os.path.join(os.path.dirname(__file__), '..', '..')
    src = io.open(os.path.join(root, 'data.js'), encoding='utf-8').read()
    st = json.loads(re.search(r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)',
                              src, re.S).group(1))
    assert C.check_sido_sum(st) == []


# ---------------------------------------------------------------------------
# 파생 페이지 — 화면이 데이터와 같은 시점으로 구워졌는가
# ---------------------------------------------------------------------------

import urllib.parse as _up

OKP = '<p>2026.06 기준 · 분기 적정물량</p>'
OLDP = '<p>2026.05 기준 · 분기 적정물량</p>'


class _FakeWeb:
    """라이브 대신 미리 정한 페이지를 돌려준다."""

    def __init__(self, pages):
        self.pages = pages

    def __call__(self, req, timeout=0):
        url = getattr(req, 'full_url', req)
        body = self.pages.get(url, '')
        return type('R', (), {'read': lambda _self: body.encode('utf-8')})()


MVP = '<div class="note">표두를 누르면 정렬. %s, 이후는 <b>착공 실적을 3년 뒤로 밀어</b> 추정한 값입니다.</div>'


def _derived(monkeypatch, seoul, gyeonggi, jr='2026.06 기준', mv=MVP % '2026년 2분기까지 준공 실적',
             nat=None):
    pages = {
        C.SITE + '/zone/' + _up.quote('전국') + '/': (nat if nat is not None else OKP),
        C.SITE + '/zone/' + _up.quote('서울') + '/': seoul,
        C.SITE + '/zone/' + _up.quote('경기') + '/': gyeonggi,
        C.SITE + '/jeonse-ratio/': jr,
        C.SITE + '/moveins/': mv,
    }
    monkeypatch.setattr(C.urllib.request, 'urlopen', _FakeWeb(pages))
    # ⚠️ 기대 시점은 준공이 아니라 unsold_prd다 — 페이지가 찍는 문자열('기준 ·
    # 분기 적정물량')의 날짜가 미분양 기준월이기 때문(2026-08-10 리뷰로 교정).
    adv = {'sido': {'zones': [{'z': '전국'}, {'z': '서울'}, {'z': '경기'}],
                    'unsold_prd': '2026.06'},
           'occupancy': {'rows': [{'p': '2026Q2', 'e': False}]}}
    stats = {'준공': {'dates': ['2026.06'], 'series': {}},
             '전세가율': {'dates': ['2026.06'], 'series': {}}}
    return C.check_derived_pages(adv, stats)


def test_derived_pages_pass_when_fresh(monkeypatch):
    assert _derived(monkeypatch, OKP, OKP) == []


def test_derived_pages_catch_a_partially_stale_bake(monkeypatch):
    """생성기가 도중에 죽으면 일부만 새 시점이 된다 — data.js만 보는 감시로는
    원리적으로 못 잡던 상태다."""
    f = _derived(monkeypatch, OKP, OLDP)
    assert len(f) == 1 and '경기(2026.05)' in f[0], f


def test_derived_pages_treat_missing_marker_as_failure(monkeypatch):
    """표기가 사라지면 페이지 구조가 바뀐 것이다 — 조용히 통과시키면 감시가 꺼진
    채로 남는다."""
    f = _derived(monkeypatch, OKP, '<p>없음</p>')
    assert len(f) == 1 and '표기 없음' in f[0], f


NEWP = '<p>2026년 6월 기준 · 분기 적정물량</p>'
NEWOLDP = '<p>2026년 5월 기준 · 분기 적정물량</p>'


def test_derived_pages_read_the_readable_month(monkeypatch):
    r"""화면 시점은 읽는 꼴('2026년 6월 기준', 날짜 두 단계 — 백로그 36-1)이다. 감시는 그 꼴과 옛 꼴('2026.06 기준')을 둘 다 읽는다
    — 배포 사이에 옛 페이지가 섞여 있어도 오탐하지 않고, 새 꼴의 옛 달은 잡는다.

    변이(실제로 확인): check_freshness 의 두 정규식을 옛 `(\d{4}\.\d{2}) 기준…` 로 되돌리면 새 꼴 페이지가 '시점 표기 없음'으로
    빨강. SZ.basis_month 가 달을 0 채움 없이('2026.6') 돌려주면 unsold_prd('2026.06')와 갈려 빨강.
    픽스처: 생성기가 굽는 지역 카드 주석·/jeonse-ratio/ 머리 한 줄의 새 꼴, 옛 꼴과 섞인 배포 상태.
    """
    assert _derived(monkeypatch, NEWP, NEWP, nat=NEWP, jr='전세가율 · 2026년 6월 기준') == []
    assert _derived(monkeypatch, NEWP, OKP, jr='2026.06 기준') == [], '옛 꼴과 섞인 배포를 오탐했다'
    f = _derived(monkeypatch, NEWP, NEWOLDP, jr='전세가율 · 2026년 6월 기준')
    assert len(f) == 1 and '경기(2026.05)' in f[0], f
    f = _derived(monkeypatch, NEWP, NEWP, jr='전세가율 · 2026년 5월 기준')
    assert len(f) == 1 and '/jeonse-ratio/가 2026.05' in f[0], f


def test_moveins_reads_the_on_screen_basis(monkeypatch):
    """/moveins/ 시점은 화면 주석의 'YYYY년 N분기까지 준공 실적'을 데이터 마지막 실적 분기와 대조한다.

    전수 리뷰 #18 로 두 지표 페이지의 dateModified 가 '내용이 바뀐 날(keep_dates·KST)'이 되어 데이터 시점을 말하지
    않는다. 예전 감시는 dateModified 를 max(분기 끝 달 1일, datePublished) 와 견줬으므로, 새 분기가 들어온 날
    본문이 바뀌면 dateModified 가 그날(예: 2026-10-02)이 되어 매일 오탐이 났다.
    픽스처: 생성기 주석과 같은 모양의 한 줄(맞음·한 분기 옛값·표기 없음·옛 JSON-LD 만 있는 페이지).
    변이(실제로 확인): check_derived_pages 를 옛 dateModified 대조로 되돌리면 첫 단정(맞음 → [])이 빨개지고,
    `m.group(0) != want` 를 빼면 옛 분기 단정이, 표기 없음 분기를 통과로 바꾸면 마지막 두 단정이 빨개진다.
    """
    assert _derived(monkeypatch, OKP, OKP) == []
    f = _derived(monkeypatch, OKP, OKP, mv=MVP % '2026년 1분기까지 준공 실적')
    assert len(f) == 1 and 'moveins' in f[0] and '2026년 2분기' in f[0], f
    f = _derived(monkeypatch, OKP, OKP, mv='<p>없음</p>')
    assert len(f) == 1 and 'moveins' in f[0] and '없다' in f[0], f
    f = _derived(monkeypatch, OKP, OKP, mv='"dateModified": "2026-10-02"')
    assert len(f) == 1 and 'moveins' in f[0], f


def test_moveins_basis_marker_is_what_the_generator_prints():
    """감시가 찾는 문구(C.MOVEINS_BASIS·_RE)가 생성기(make_indicator_pages.build_moveins)가 실제로 찍는 문구다.

    같은 문구를 두 코드가 따로 적었으니 한쪽만 바뀌면 감시가 '표기 없음'으로 매일 빨개지거나, 정규식이 넓어져
    엉뚱한 분기를 읽는다. 픽스처: 저장소 ADV(마지막 실적 분기는 데이터에서 — 박지 않는다).
    변이(실제로 확인): 생성기 주석을 상수 대신 손 문구('%(lastact)s 준공 실적')로 되돌리거나, 감시의 MOVEINS_BASIS 를
    생성기 상수 대신 따로 적은 사본('%s년 %s분기 준공 실적')으로 바꾸면 빨개진다.
    """
    import make_indicator_pages as I
    import make_sido_pages as P
    adv, _ = P.load()
    html, _ = I.build_moveins(adv, '2031-03-03')
    last = [r['p'] for r in adv['occupancy']['rows'] if not r.get('e')][-1]
    found = re.findall(C.MOVEINS_BASIS_RE, html)
    assert found and set(found) == {(last[:4], last[5:])}, found
    assert C.MOVEINS_BASIS % (last[:4], last[5:]) in html


# ---------------------------------------------------------------------------
# 원천 조회 재시도 — 광역 장애(2026-08-12)는 IP를 바꿔도 소용없다
# ---------------------------------------------------------------------------

def _reset_retry(monkeypatch):
    """재시도 대기·건너뜀 목록을 비우고 원천 타임아웃을 60초로 둔다. 타임아웃은 monkeypatch 로 바꿔 시험이 끝나면 감시 기본값
    (C.FETCH_TIMEOUT 25초)으로 되돌린다 — 예전엔 전역에 60(과 retry_failed 가 바꾼 20)을 그대로 남겨, 시험 순서에 따라 뒤 시험이
    보는 값이 갈렸다(전수리뷰 T1 overflow)."""
    C.RETRYQ.clear()
    C.SKIPPED.clear()
    monkeypatch.setattr(C, 'FETCH_TIMEOUT', 60)


def test_transient_origin_outage_recovers_on_retry(monkeypatch):
    """1차 조회가 죽었다 재시도에 살아나면 건너뜀도 실패도 아니어야 한다 —
    2026-08-12 KOSIS·R-ONE 광역 타임아웃(14/18)이 정확히 이 모양이었다."""
    _reset_retry(monkeypatch)
    monkeypatch.setattr(C.time, 'sleep', lambda s: None)
    calls = {'n': 0}

    def flaky():
        calls['n'] += 1
        if calls['n'] == 1:
            raise OSError('timed out')
        return '2026.06'

    fails = [C.check('월간', '2026.06', flaky, 50)]
    assert C.RETRYQ and not C.SKIPPED, '1차 실패는 확정이 아니라 재시도 대기여야 한다'
    C.retry_failed(fails, wait=0)
    assert not C.SKIPPED and not [f for f in fails if f]
    assert calls['n'] == 2


def test_persistent_outage_still_alarms(monkeypatch):
    """재시도까지 죽으면 SKIPPED로 확정 — 게이트를 무디게 하는 게 아니다.
    표 ID 변경·키 만료는 여기로 와야 잡힌다."""
    _reset_retry(monkeypatch)
    monkeypatch.setattr(C.time, 'sleep', lambda s: None)

    def dead():
        raise OSError('timed out')

    fails = [C.check('월간', '2026.06', dead, 50)]
    C.retry_failed(fails, wait=0)
    assert C.SKIPPED == ['월간'], '재시도까지 실패하면 기존 게이트로 가야 한다'
    _reset_retry(monkeypatch)


def test_gate_arithmetic_survives_the_retry_pass(monkeypatch):
    """SKIPPED 목록만 보면 부족하다 — 판정은 'SKIPPED×2 > len(fails)' 산식이
    한다. 첫 구현이 재시도 결과(None)를 fails에 그대로 append해 분모를 부풀렸고,
    2026-08-12 시나리오(18계열 중 14 지속 실패)가 28>32 거짓으로 **OK를 찍었다**
    (2026-08-13 리뷰에서 재현·확정). main()의 산식을 그대로 복제해 잠근다."""
    _reset_retry(monkeypatch)
    monkeypatch.setattr(C.time, 'sleep', lambda s: None)

    def dead():
        raise OSError('timed out')

    fails = []
    for i in range(18):
        getter = dead if i < 14 else (lambda: '2026.06')
        fails.append(C.check('s%02d' % i, '2026.06', getter, 50))
    C.retry_failed(fails, wait=0)
    assert len(C.SKIPPED) == 14
    assert not [f for f in fails if f], '뒤처짐이 아니라 조회 실패다 — bad는 비어야 한다'
    assert len(C.SKIPPED) * 2 > len(fails), \
        '지속 광역 장애가 OK로 통과한다 — 재시도가 분모를 부풀렸는지 확인'
    _reset_retry(monkeypatch)


def test_retry_still_catches_a_genuinely_stale_series(monkeypatch):
    """재시도에 살아난 원천이 더 최신이면 뒤처짐 검사는 그대로 받아야 한다 —
    재시도가 '봐주기'가 되면 감시가 켜진 채 아무것도 안 보게 된다."""
    _reset_retry(monkeypatch)
    monkeypatch.setattr(C.time, 'sleep', lambda s: None)
    calls = {'n': 0}

    def flaky_and_newer():
        calls['n'] += 1
        if calls['n'] == 1:
            raise OSError('timed out')
        return '2026.07'

    fails = [C.check('월간', '2026.05', flaky_and_newer, 50)]
    C.retry_failed(fails, wait=0)
    bad = [f for f in fails if f]
    assert bad and '월간' in bad[0], '뒤처짐이 재시도 뒤에도 잡혀야 한다'
    _reset_retry(monkeypatch)


# ---------------------------------------------------------------------------
# R-ONE 기간 필터 — 깊은 페이지가 서버에 끊기는 것을 피한다(2026-08-15)
# ---------------------------------------------------------------------------

import update_adv_data as U  # noqa: E402


def test_rone_since_formats_and_rolls_over_the_year():
    """주간은 YYYYMMDD, 월간은 YYYYMM. 연초에 back이 달을 넘기면 해가 줄어야 한다 —
    여기서 틀리면 창이 미래로 잡혀 매번 폴백(=필터 무효)이 돈다."""
    import datetime

    class Feb(datetime.date):
        @classmethod
        def today(cls):
            return cls(2026, 2, 10)

    real = datetime.date
    datetime.date = Feb
    try:
        assert U._rone_since('MM', 4) == '202510'
        assert U._rone_since('MM', 14) == '202412'
        assert U._rone_since('WK', 8) == '20250601'
        assert U._rone_since('MM', 1) == '202601'
    finally:
        datetime.date = real


def test_empty_window_falls_back_to_the_full_table(monkeypatch):
    """창이 비면 R-ONE은 표 블록 대신 {'RESULT':{'CODE':'INFO-200'}}를 준다.
    그대로 인덱싱하면 KeyError로 죽고, 조용히 []를 돌려주면 배치가 '원천에 자료가
    없다'로 읽어 계열이 갱신되지 않는다 — 성능 최적화가 데이터 사고가 되는 길이다.
    필터를 풀고 다시 받아야 한다."""
    seen = []
    empty = {'RESULT': {'CODE': 'INFO-200', 'MESSAGE': '해당하는 데이터가 없습니다.'}}
    full = {'SttsApiTblData': [{'head': [{'list_total_count': 2}]},
                               {'row': [{'WRTTIME_IDTFR_ID': '202606'}]}]}

    def fake(url, tries=3):
        seen.append(url)
        return empty if 'START_WRTTIME' in url else full

    monkeypatch.setattr(U, 'http_json', fake)
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    rows = U._rone_recent_rows('T1', 100, cycle='MM', since='209901')
    assert rows, '빈 창에서 폴백이 안 돌았다'
    assert any('START_WRTTIME' in u for u in seen) and any('START_WRTTIME' not in u for u in seen)


def test_seeding_never_narrows_the_window(monkeypatch):
    """시딩(months=0)은 26년치 전량이 목적이다. 여기에 기간 필터가 걸리면 과거가
    통째로 사라진다 — 되돌리기 어려운 사고다."""
    seen = {}

    def fake(tbl, need, cycle='WK', since=None):
        seen['since'] = since
        return [{'WRTTIME_IDTFR_ID': '202606', 'CLS_FULLNM': '전국', 'DTA_VAL': '1'}]

    monkeypatch.setattr(U, '_rone_recent_rows', fake)
    U._fetch_supply_one(U.SUPPLY_CONF['분양'], {'전국'}, 0)      # R-ONE 경로(미분양은 10-07 KOSIS 로 옮겼다)
    assert seen['since'] is None, '시딩에 기간 필터가 걸렸다'
    U._fetch_supply_one(U.SUPPLY_CONF['분양'], {'전국'}, 8)
    assert seen['since'], '증분인데 필터가 없다 — 깊은 페이지로 되돌아갔다'


def test_watchdog_supply_check_lower_bounds_by_our_own_date(monkeypatch):
    """감시의 하한은 **우리 시점**이어야 한다. 오늘 날짜 기준으로 잡으면 우리가
    많이 뒤처졌을 때 창 밖이 되어 뒤처짐을 못 본다.

    생산 함수(_supply_since)와 그것을 부르는 source_jobs 의 공급 getter 를 직접 본다(전수리뷰 #93). 예전 시험은
    하한을 시험 안에서 스스로 계산해 가짜에 넣었으므로, _supply_since 를 오늘 기준으로 바꿔도 초록이었다.
    변이(확인): _supply_since 본문을 `t = datetime.date.today(); return '%04d%02d' % (t.year, t.month)` 로 바꾸면
    빨개진다.
    픽스처: 미분양이 2026.06 에 멈춰 있고(백로그 4의 실제 보류 상태) 원천은 2026.07 을 낸 날. 미분양은 2026-10-07 KOSIS 로
            옮겨 R-ONE 하한을 쓰지 않으므로 같은 모양을 R-ONE 에 남은 분양 계열로 본다.
    """
    assert C._supply_since('2026.06') == '202605'
    assert C._supply_since('2026.01') == '202512'      # 연 넘김
    assert C._supply_since(None) is None
    assert C._supply_since('2026') is None
    got = {}

    def fake_complete(tbl, since=None, want_total=False):
        got[tbl] = since
        return '202607'

    monkeypatch.setattr(C, 'rone_latest_complete', fake_complete)
    stats = {'분양': {'dates': ['2026.05', '2026.06'], 'series': {}}}
    jobs = C.source_jobs(stats)
    tbl = U.SUPPLY_CONF['분양']['tbl']
    r = C.check('분양', '2026.06', jobs[('supply', '분양')], C.GRACE_MONTHLY)
    assert got[tbl] == '202605', got
    assert r and '분양' in r, '원천이 더 최신인데 뒤처짐을 못 잡았다'


def test_aggregate_regions_are_monitored_too(monkeypatch):
    """전국·수도권·지방도 페이지가 **있다**(zone/전국/ 등) — 예전엔 '없다'는 틀린
    전제로 감시에서 빼서, 유입이 가장 많은 전국 페이지의 스테일을 원리적으로
    못 잡았다(2026-08-10 리뷰). 집계 페이지만 옛 시점이어도 잡혀야 한다."""
    f = _derived(monkeypatch, OKP, OKP, nat=OLDP)
    assert len(f) == 1 and '전국(2026.05)' in f[0], f


# ---------------------------------------------------------------------------
# 지역 계층 — 배치가 20지역을 집을 수 있는가 (2026-08-26)
# ---------------------------------------------------------------------------

def _names(monkeypatch, names):
    C.FETCH_FAIL[:] = []
    monkeypatch.setattr(C, 'rone_region_names', lambda tbl, cycle: set(names))


def _full(extra=()):
    """20개 지역이 전부 집히는 최소 계층 + 추가 행."""
    base = []
    for z in C.U.WEEKLY_REGIONS:
        base.append({'지방': '지방권'}.get(z, z))
    return set(base) | set(extra)


def test_current_hierarchy_passes(monkeypatch):
    """2026-07 개편 직후의 실제 모양 — 광주·전남이 상위 묶음 밑에 있어도
    '가장 얕은 >이름'으로 집히므로 통과해야 한다."""
    names = _full() | {'전남광주>광주', '전남광주>전남'}   # 하위가 함께 있어도 상위를 집는다
    _names(monkeypatch, names)
    assert C.check_region_rows() == []
    assert C.FETCH_FAIL == []


def test_missing_region_is_caught(monkeypatch):
    """진짜 실패 모드 — 원천이 상위 묶음을 또 바꿔 배치가 경로를 못 찾는 경우.
    시점도 최신이고 시세는 합계 검사 대상도 아니라, 이 검사가 없으면
    **아무 경보 없이 광주 시세만 사라진다**(실제로 15개월 결측 전례)."""
    names = _full() - {'전남광주'}          # 통합 지역이 통째로 사라진 경우
    _names(monkeypatch, names)
    fails = C.check_region_rows()
    assert fails and any('전남광주' in f and '결측' in f for f in fails), fails
    assert not any('서울' in f for f in fails), '집히는 지역을 잡으면 오탐'


def test_sido_lookup_matches_the_batch_rule():
    """감시가 배치와 **같은 규칙**으로 찾아야 한다. 규칙이 갈리면 감시는 통과하는데
    배치만 못 집는(또는 그 반대) 상태가 된다."""
    names = {'서울', '전남광주>광주', '전남광주>전남>광주시', '지방권'}
    assert C._sido_lookup(names, '서울') == '서울'
    assert C._sido_lookup(names, '지방') == '지방권'       # 별칭
    # 얕은 것 우선 — 시군구가 아니라 시도를 집는다
    assert C._sido_lookup(names, '광주') == '전남광주>광주'
    assert C._sido_lookup(names, '없는지역') is None


def test_seoul_gu_name_collision_is_caught(monkeypatch):
    """서울 구 추출은 마지막 조각을 키로 쓴다(rsplit이 실제로 쓰이는 유일한 자리).
    같은 구 이름이 두 경로에 있으면 뒤엣것이 앞엣것을 덮어 한 구가 유실된다."""
    _names(monkeypatch, _full() | {'서울>강북지역>도심권>중구', '서울>강남지역>서남권>중구'})
    fails = C.check_region_rows()
    assert fails and any('중구' in f and '충돌' in f for f in fails), fails


def test_lookup_failure_is_not_read_as_healthy(monkeypatch):
    """조회 실패는 '이상 없음'이 아니라 '못 봤다'다. 조용히 통과시키면 감시가
    켜진 채 아무것도 안 보는 상태가 된다 — FETCH_FAIL로 보낸다(SKIPPED는
    게이트 분자라 쓰지 않는다)."""
    C.FETCH_FAIL[:] = []
    def dead(tbl, cycle):
        raise OSError('timed out')
    monkeypatch.setattr(C, 'rone_region_names', dead)
    monkeypatch.setattr(C, 'REGION_RETRY_WAITS', (0, 0))      # 재시도는 돌되 쉬지 않는다
    monkeypatch.delenv(C.REGION_STATE_ENV, raising=False)     # 상태 폴더가 없으면 예전 그대로 곧바로 '못 봤다'
    assert C.check_region_rows() == []
    assert len(C.FETCH_FAIL) == 2, C.FETCH_FAIL
    # 판정까지 본다(전수리뷰 #37). 예전엔 다른 실패가 없는 날 _gate 가 'VERDICT=ok' 를 찍고 돌아왔다 —
    # FETCH_FAIL 은 다른 실패가 이미 있을 때 종료 코드를 가를 때만 쓰였다.
    # 변이(확인): _gate 의 `if FETCH_FAIL:` 분기를 지우면 SystemExit 이 안 나 빨개진다.
    C.SKIPPED[:] = []
    try:
        import pytest
        with pytest.raises(SystemExit) as e:
            C._gate([None] * 17)
        assert e.value.code == C.EXIT_RETRYABLE
    finally:
        C.FETCH_FAIL[:] = []


def test_batch_and_watchdog_resolve_regions_identically():
    """배치와 감시가 **같은 계층에서 같은 행**을 집어야 한다 — 감시의 _sido_lookup 은 배치 규칙 함수 그 자체다(전수리뷰 A-7).

    예전 이 시험은 두 수집 클로저와 감시 거울의 원문에 규칙 문자열이 하나라도 있는지만 봐서, 월간 쪽 별칭만 바뀌어도 초록이었다.
    지금은 한 함수(update_adv_data.rone_sido_key)를 셋이 부르고, 수집 행동(계층 픽스처로 fetch_weekly_rone·fetch_monthly_rone 을
    돌려 지역마다 맞는 행의 값이 실리는지)은 test_rone_region_lookup 이 본다. 여기서는 감시가 쓰는 계층 모양 하나를 더 본다.
    변이(실제로 확인): check_freshness 에 `_sido_lookup` 을 따로 적은 함수로 두면 동일성 단정이, rone_sido_key 의 min 을 max 로
    바꾸면 '전남광주>광주' 미끼(통합 지역 밑 옛 조각) 단정이 빨개진다.
    픽스처: 감시 시험의 _full() — 2026-07 R-ONE 계층(평평한 시도 + 통합 지역 밑 옛 두 조각).
    """
    from merge_regions import SRC, DST
    assert C._sido_lookup is U.rone_sido_key
    piece = '%s>%s' % (DST, SRC[0])
    names = _full() | {'%s>%s' % (DST, p) for p in SRC} | {'%s>%s' % (piece, SRC[0])}
    for z in U.WEEKLY_REGIONS:
        assert C._sido_lookup(names, z) == U.RONE_ALIAS.get(z, z), z
    assert C._sido_lookup(names, SRC[0]) == piece, '얕은 행이 아니라 깊은 미끼를 집었다'


def test_region_count_gate_follows_the_model():
    """감시의 지역 수 기대값은 **모델에서 파생**되어야 한다.

    2026-09-10 광주·전남 통합(20곳→19곳) 때 이 게이트에 20이 박혀 있어, 데이터는
    멀쩡한데 감시가 이틀 연속 빨개졌다("ADV.sido 지역이 19곳뿐이다(20곳이어야 함)").
    감시자만 옛 세상을 보고 있었던 셈이다. 모델이 바뀌면 기대값도 따라와야 한다.

    숫자 리터럴이 다시 들어오는 것을 막는 게 목적이라 소스를 직접 본다.
    """
    import io as _io, os, re
    root = os.path.join(os.path.dirname(__file__), '..')
    src = _io.open(os.path.join(root, 'check_freshness.py'), encoding='utf-8').read()
    seg = src[src.index("n_z = len(sido['zones'])"):]
    seg = seg[:seg.index('check_age')]
    assert 'len(SZ.REF_Q)' in seg, '지역 수 기대값이 모델에서 오지 않는다'
    lit = re.findall(r'n_z\s*<\s*(\d+)', seg)
    assert not lit, '지역 수를 숫자로 박았다: %s' % lit


def test_region_count_gate_passes_on_live_data():
    """실제 라이브 지역 수로 이 게이트가 통과하는지 — 배포 전에 여기서 잡는다."""
    import io as _io, json, os, re
    import sido_zones as SZ
    root = os.path.join(os.path.dirname(__file__), '..', '..')
    core = _io.open(os.path.join(root, 'data-core.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'const ADV=(\{.*?\});', core, re.S).group(1))
    n = len(adv['sido']['zones'])
    assert n == len(SZ.REF_Q), \
        '데이터 지역 %d곳 vs 모델 %d곳 — 한쪽만 바뀌면 감시가 매일 빨개진다' % (n, len(SZ.REF_Q))


def _kst_epoch(stamp):
    """'2026-10-20 23:50' (KST) → UTC epoch 초."""
    import datetime
    kst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.strptime(stamp, '%Y-%m-%d %H:%M').replace(tzinfo=kst).timestamp()


def test_region_list_drop_is_retried_then_warned_then_failed_on_the_second_day(monkeypatch, tmp_path):
    """지역 목록 조회가 끊기면(2026-10-03·04 감시 실패 — R-ONE 이 응답 없이 끊음, 대조는 전부 일치) 간격을 두고 다시 부르고,
    끝까지 끊기면 첫 회차는 경고, 이틀(이웃 예약 회차) 연속이면 '못 봤다'(FETCH_FAIL → 재확인 → 실패)로 올린다
    (2026-10-06 대표 결정).

    재현한 실제 상태: 병렬로 받아 둔 지역 목록이 RemoteDisconnected 로 실패한 회차. 상태 폴더는 감시 워크플로가
    actions/cache 로 실행 사이에 이어 주는 WATCH_STATE_DIR. 시각은 실측 감시 시작 시각(예약 18:07 KST 에 +0~10시간)을 쓴다.
    변이(각각 실제로 확인): _region_names_retry 가 다시 부르지 않고 곧바로 던지면 첫 단정(되살아남)이 빨강.
    region_fail_tolerated 가 직전 실패를 보지 않으면(escalate 를 늘 False) 둘째 회차 단정이 빨강. 같은 실행의 결정을 따르지
    않고 다시 계산하면(같은 실행 두 번째 호출이 '직전 회차'를 못 찾아 경고) 재확인 잡 단정이 빨강.
    """
    names = {'전국', '수도권', '지방', '서울', '서울>강남구'} | {'%s' % z for z in C.U.WEEKLY_REGIONS}
    calls = []

    def flaky_direct(tbl, cycle):
        calls.append(tbl)
        if len(calls) == 1:
            raise OSError('Remote end closed connection')
        return names

    def dead_pre(tbl, cycle):
        raise OSError('Remote end closed connection without response')
    t = _kst_epoch
    # ① 다시 부르면 살아난다 — 실패도 경고도 없다
    C.FETCH_FAIL[:] = []
    del C.WARN[:]
    C.check_region_rows(fetch=dead_pre, now=t('2026-10-03 23:10'), state_dir=str(tmp_path), run_id='r1',
                        retry=lambda f, t_, c: C._region_names_retry(f, t_, c, waits=(0, 0), direct=flaky_direct))
    assert not C.FETCH_FAIL and not C.WARN, (C.FETCH_FAIL, C.WARN)

    def all_dead(f, t_, c):
        return C._region_names_retry(f, t_, c, waits=(0,), direct=dead_pre)
    # ② 끝까지 끊긴 첫 회차 — 경고만
    C.check_region_rows(fetch=dead_pre, now=t('2026-10-03 23:10'), state_dir=str(tmp_path), retry=all_dead, run_id='r1')
    assert not C.FETCH_FAIL and len(C.WARN) == 1 and '다음 회차' in C.WARN[0], (C.FETCH_FAIL, C.WARN)
    # 같은 실행의 재확인 잡 — 같은 결정(경고)
    del C.WARN[:]
    C.check_region_rows(fetch=dead_pre, now=t('2026-10-03 23:40'), state_dir=str(tmp_path), retry=all_dead, run_id='r1')
    assert not C.FETCH_FAIL and len(C.WARN) == 1
    # ③ 다음 회차도 끊김 — 실패로 올린다(재확인 잡도 같은 결정)
    del C.WARN[:]
    for stamp in ('2026-10-04 23:15', '2026-10-04 23:50'):
        C.FETCH_FAIL[:] = []
        C.check_region_rows(fetch=dead_pre, now=t(stamp), state_dir=str(tmp_path), retry=all_dead, run_id='r2')
        assert len(C.FETCH_FAIL) == len(C.REGION_TABLES) and not C.WARN, (C.FETCH_FAIL, C.WARN)
    # ④ 셋째 회차에 받으면 기록을 지운다 — 그다음 끊김은 다시 첫 회차(경고)
    C.FETCH_FAIL[:] = []
    C.check_region_rows(fetch=lambda t_, c: names, now=t('2026-10-05 22:00'), state_dir=str(tmp_path), run_id='r3')
    assert not (tmp_path / C.REGION_STATE_FILE).exists()
    C.check_region_rows(fetch=dead_pre, now=t('2026-10-06 22:00'), state_dir=str(tmp_path), retry=all_dead, run_id='r4')
    assert not C.FETCH_FAIL and len(C.WARN) == 1
    del C.WARN[:]


def test_region_fail_rounds_cross_midnight(tmp_path):
    """같은 회차·이웃 회차를 KST 달력 날짜가 아니라 실행 id 와 경과 시간으로 가른다(전수리뷰 F-2).

    재현한 실제 상태: 감시 예약 실행은 18:07 KST 예약에 +0~10시간 늦게 시작해 자정을 걸친다(2026-10 실측
    10-03 23:17, 10-04 23:45, 10-06 03:21(10-05 예약분), 10-07 00:53, 10-14 01:54(10-13 예약분)→10-14 23:28).
    (a) 한 실행의 1차 23:50·재확인 00:10 → 둘 다 경고(첫 회차). (b) 매일 끊긴 실측 시작 열 → 경고·실패·실패·실패.
    (c) 같은 KST 날의 이웃 예약 회차(01:54 → 23:28) → 둘째는 실패. (d) 수동 재실행(실행 id 다름, 2시간 뒤)은 그 결정을 따른다
    — 경고였으면 경고, (f) 이미 실패로 올린 회차 뒤의 수동 재실행이면 실패.
    변이(실제로 확인): region_fail_tolerated 를 옛 달력 날짜 판정(prev 날짜 == 오늘이면 결정 따름, == 어제면 올림)으로
    되돌리면 (a) 재확인과 (b)·(c) 단정이 빨강. REGION_NEXT_ROUND_H 를 24로 줄이면 (b) 의 10-06 03:21 단정이 빨강.
    같은 회차 경과 시간 분기를 빼고 실행 id 만 보면(`if same_run:`) (f) 가 빨강(수동 재실행이 실패를 경고로 뒤집는다).
    """
    def run(d, seq):
        out = []
        for stamp, rid in seq:
            out.append(C.region_fail_tolerated(_kst_epoch(stamp), str(d), rid))
        return out
    a = tmp_path / 'a'
    assert run(a, [('2026-10-20 23:50', 'x'), ('2026-10-21 00:10', 'x')]) == [True, True]
    b = tmp_path / 'b'
    assert run(b, [('2026-10-03 23:17', 'r1'), ('2026-10-04 23:45', 'r2'),
                   ('2026-10-06 03:21', 'r3'), ('2026-10-07 00:53', 'r4')]) == [True, False, False, False]
    c = tmp_path / 'c'
    assert run(c, [('2026-10-14 01:54', 'r1'), ('2026-10-14 23:28', 'r2')]) == [True, False]
    d = tmp_path / 'd'
    assert run(d, [('2026-10-20 22:00', 'r1'), ('2026-10-21 00:00', 'manual')]) == [True, True]
    f = tmp_path / 'f'
    assert run(f, [('2026-10-20 22:00', 'r1'), ('2026-10-21 22:30', 'r2'), ('2026-10-22 00:30', 'manual')]) == \
        [True, False, False]
    # 회차가 하루 넘게 비면(성공 회차는 기록을 지운다) 다시 첫 회차
    e = tmp_path / 'e'
    assert run(e, [('2026-10-20 22:00', 'r1'), ('2026-10-23 22:00', 'r2')]) == [True, True]


def test_price_source_uses_period_window_and_page_retry(monkeypatch):
    """감시 핵심 계열 '주간'·'월간' 원천 조회가 배치처럼 기간 창(START_WRTTIME)을 주고, 쪽마다 끊기면 다시 받는다(전수리뷰 F-4).
    창이 없으면 주간 매매 표 170쪽 안팎의 깊은 쪽을 읽는데, R-ONE 은 그 요청을 간헐적으로 응답 없이 끊는다(2026-08-15 실측).

    변이(실제로 확인): source_jobs 의 '주간' 람다에서 since 를 빼면(rone_latest(tbl, 'WK')) 첫 단정이 빨강. rone_latest 의
    head 조회나 마지막 쪽 조회를 get_json 으로 되돌리면(재시도 없음) 둘째 단정(각 조회의 첫 호출 끊김 뒤 성공)이 빨강.
    픽스처: 합성 ADV(주간 2026-01-05·월간 2026-01 — 연 넘김 창) 와 가짜 R-ONE(창 안 2,500행 = 3쪽, head·마지막 쪽의 첫 호출은 끊김).
    """
    seen = {}

    def fake_latest(tbl, cycle, since=None):
        seen[cycle] = since
        return 'x'
    monkeypatch.setattr(C, 'rone_latest', fake_latest)
    adv = {'weekly': {'rows': [{'p': '2026-01-05'}]}, 'monthly': {'rows': [{'p': '2026-01'}]}}
    jobs = C.source_jobs({}, adv)
    jobs['주간']()
    jobs['월간']()
    assert seen == {'WK': '20251201', 'MM': '202512'}, seen
    assert C._price_since(None, 'WK') is None       # 우리 시점을 못 읽으면 예전처럼 전량

    monkeypatch.undo()
    calls = []

    def fake_get(url):
        calls.append(url)
        if len(calls) in (1, 3):
            raise OSError('Remote end closed connection without response')
        if 'pSize=1&' in url + '&':
            return {'SttsApiTblData': [{'head': [{'list_total_count': 2500}]}]}
        return {'SttsApiTblData': [{'row': [{'WRTTIME_DESC': '2026-01-12'}, {'WRTTIME_DESC': '2026-01-19'}]}]}
    monkeypatch.setattr(C, 'get_json', fake_get)
    monkeypatch.setattr(C.time, 'sleep', lambda s: None)
    assert C.rone_latest('T', 'WK', '20251201') == '2026-01-19'
    assert len(calls) == 4 and all('START_WRTTIME=20251201' in u for u in calls), calls
    assert 'pIndex=3&' in calls[-1] + '&', calls[-1]
