# -*- coding: utf-8 -*-
"""감시의 나이 상한(check_freshness.MAX_AGE_*) — 원천 표 자체가 멈춘 것을 잡는다(2026-10 리뷰 C2, 대표 결정).

원천 대조(check)는 '원천이 우리보다 최신인가'만 봐서, 원천 표가 갱신을 멈추면(표 폐지 뒤 옛 표가 그대로 응답하는 등)
우리와 원천이 같은 옛 시점에 함께 서 있어 영원히 초록이었다. 상한은 우리 최신 시점이 **끝난 날**부터 감시의 오늘(KST)
까지를 재어, 계열별 상한을 넘으면 원천과 같은 시점이어도 실패시킨다.

여기서는 감시의 오늘(C.TODAY)을 **데이터에서 유도한 날**로 고정한다 — 실데이터의 달·날짜를 숫자로 박지 않으므로
데이터가 앞으로 가도 같은 판정을 한다. 원천 호출 없음(main() 은 test_freshness_parallel 의 하니스로 돈다).
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import check_freshness as C  # noqa: E402
from test_freshness_parallel import _live, _run  # noqa: E402  (main() 통째 하니스 — 네트워크 없음)

DAY = datetime.timedelta(days=1)


def _series():
    """저장소 데이터의 계열별 (이름, 최신 시점, 상한) — main() 이 넘기는 상한과 같은 짝."""
    adv, last = _live()
    import update_adv_data as U
    out = [('주간', adv['weekly']['rows'][-1]['p'],
            C.weekly_max_age(adv['weekly']['rows'][-1]['p'], adv.get('holidays'))),
           ('월간', adv['monthly']['rows'][-1]['p'], C.MAX_AGE_MONTHLY),
           ('금리', last['금리'], C.MAX_AGE_RATE),
           ('전월세전환율', adv['bubble']['prd'], C.MAX_AGE_BUBBLE_CONV),
           ('주담대 금리', adv['bubble']['loan']['p'], C.MAX_AGE_BUBBLE_LOAN)]
    out += [(n, last[n], C.MAX_AGE_BASIC) for n in sorted(U.BASIC_CONF) + ['규모별'] + sorted(U.SUPPLY_CONF)]
    out += [(n, last[n], C.MAX_AGE_ANNUAL) for n in sorted(U.ANNUAL_CONF)]
    # 시도 지표(ADV.sido.L)는 분기 표기('2026Q2')라 period_end 가 못 읽는다 — main() 과 같이 분기 끝날(_q_to_date)로 잰다
    out.append(('시도 지표', C._q_to_date(adv['sido']['L']), C.MAX_AGE_SIDO_Q))
    return adv, out


def test_period_end_reads_every_period_shape():
    """주간은 그 날, 월은 말일(윤년 2월·12월 포함), 연은 12월 31일. 못 읽으면 None.

    변이(확인): period_end 의 월 분기를 `return datetime.date(y, m, 1)`(시작일)로 바꾸면 빨개진다.
    픽스처: 데이터에 실제로 있는 표기 — 'YYYY-MM-DD'(주간), 'YYYY.MM'·'YYYY.MM p)'(KOSIS), 'YYYY-MM'(R-ONE 월간), 'YYYY'(연간).
    """
    assert C.period_end('2026-09-28') == datetime.date(2026, 9, 28)
    assert C.period_end('2026.08 p)') == datetime.date(2026, 8, 31)
    assert C.period_end('2028-02') == datetime.date(2028, 2, 29)
    assert C.period_end('202612') == datetime.date(2026, 12, 31)
    assert C.period_end('2024') == datetime.date(2024, 12, 31)
    assert C.period_end('') is None and C.period_end('2026-13') is None


@pytest.mark.parametrize('kind', ['주간', '월간', '미분양', '보급률', '전월세전환율'])
def test_frozen_source_fails_only_beyond_the_ceiling(monkeypatch, kind):
    """원천이 우리와 **같은** 시점을 돌려주는(표가 멈춘) 계열은 상한 날까지 통과, 하루 넘으면 실패 — 사유에 계열 이름과
    나이가 있다. 연간 계열은 상한이 길다(정상 지연에 오경보를 내지 않게).

    변이(확인): check() 끝의 `return too_old(label, ours, max_age)` 를 `return None` 으로 바꾸면 '하루 넘은 날' 단정이
    빨개진다. too_old 의 `age <= max_age` 를 `age < max_age` 로 바꾸면 '상한 날' 단정이 빨개진다.
    픽스처: 저장소 데이터의 그 계열 최신 시점과 main() 이 쓰는 상한. 오늘은 '시점이 끝난 날 + 상한'(데이터에서 유도).
    """
    _, rows = _series()
    label, ours, cap = next(r for r in rows if r[0] == kind)
    end = C.period_end(ours)
    frozen = lambda: C.digits(ours)  # noqa: E731  원천도 같은 시점에 멈춰 있다
    monkeypatch.setattr(C, 'TODAY', end + cap * DAY)
    assert C.check(label, ours, frozen, None, _retry=False, max_age=cap) is None
    monkeypatch.setattr(C, 'TODAY', end + (cap + 1) * DAY)
    r = C.check(label, ours, frozen, None, _retry=False, max_age=cap)
    assert r and label in r and '%d일' % (cap + 1) in r and '상한 %d일' % cap in r, r
    if kind == '보급률':
        assert cap >= 3 * 365, '연간 계열에 짧은 상한 — 해마다 정상 발표 지연에 오경보가 난다'


def test_ceiling_holds_when_the_source_cannot_be_reached(monkeypatch):
    """원천 조회가 재시도까지 죽어도 우리 값의 나이는 잴 수 있다 — 상한을 넘었으면 실패. 1차 실패는 재시도 큐에 상한을
    싣고 넘어가, 계열당 fails 항목은 하나다(개수 게이트의 분모가 부풀지 않는다).

    변이(확인): retry_failed 의 check 호출에서 `max_age=max_age` 를 빼면 실패 사유가 사라져 빨개진다. check() 의 건너뜀
    분기를 `return None` 으로 되돌려도 빨개진다.
    retry_failed 는 전역 C.FETCH_TIMEOUT 을 20 으로 바꾼다 — monkeypatch 로 잡아 두어 시험이 끝나면 감시 기본값으로 돌아간다
    (test_freshness_invariant._reset_retry 와 같은 이유, 전수리뷰 T1 overflow). 확인: 그 줄을 지우고 같은 세션에서 이 파일 뒤에
    `C.FETCH_TIMEOUT == 25` 를 보는 임시 시험을 돌리면 'assert 20 == 25' 로 빨갛고, 두면 초록이다.
    픽스처: 저장소 데이터의 월간 최신 시점, 오늘은 그 달 말일 + 상한 + 1일, 원천은 매번 타임아웃.
    """
    adv, _ = _live()
    mo = adv['monthly']['rows'][-1]['p']
    monkeypatch.setattr(C, 'TODAY', C.period_end(mo) + (C.MAX_AGE_MONTHLY + 1) * DAY)
    monkeypatch.setattr(C.time, 'sleep', lambda s: None)
    monkeypatch.setattr(C, 'FETCH_TIMEOUT', C.FETCH_TIMEOUT)   # retry_failed 가 바꾸는 전역 타임아웃을 시험 끝에 되돌린다
    for lst in (C.SKIPPED, C.RETRYQ, C.FETCH_FAIL):
        lst.clear()

    def dead():
        raise OSError('timed out')
    try:
        fails = [C.check('월간', mo, dead, C.GRACE_MONTHLY, max_age=C.MAX_AGE_MONTHLY)]
        assert fails == [None] and len(C.RETRYQ) == 1
        C.retry_failed(fails, wait=0)
        bad = [f for f in fails if f]
        assert C.SKIPPED == ['월간'] and len(bad) == 1 and '월간: 최신 시점' in bad[0], fails
    finally:
        for lst in (C.SKIPPED, C.RETRYQ, C.FETCH_FAIL):
            lst.clear()


def test_weekly_ceiling_allows_a_skipped_holiday_week():
    """원천은 긴 연휴 주에 조사를 한 주 거른다(data.js 실측: 2025-01-20→02-03, 2025-09-29→10-13). 다음 발표 주에
    공휴일이 끼면 주간 상한에 한 주를 더한다 — 건너뛴 주에 발표마저 하루 밀린 목요일 밤(17일)에 헛경보를 내지 않게.

    변이(확인): weekly_max_age 의 `+ (WR.WEEK if hedge else 0)` 를 지우면 첫 단정이 빨개진다.
    픽스처: 저장소 데이터의 최신 조사기준일 p 와, 그 다음 발표 목요일(p+10)이 공휴일인 달력 / 빈 달력.
    """
    adv, _ = _live()
    p = adv['weekly']['rows'][-1]['p']
    thu = (C.period_end(p) + (C.WR.WEEK + C.WR.PUB_OFFSET) * DAY).isoformat()
    assert C.weekly_max_age(p, [thu]) == C.MAX_AGE_WEEKLY + C.WR.WEEK
    assert C.weekly_max_age(p, []) == C.MAX_AGE_WEEKLY
    # 한 주를 건너뛴 정상 회차: 다음 조사분(p+14)의 발표 전날(수요일)까지는 평상 상한으로도 통과한다.
    assert 2 * C.WR.WEEK + C.WR.PUB_OFFSET - 1 <= C.MAX_AGE_WEEKLY
    assert C.MAX_AGE_WEEKLY > C.GRACE_WEEKLY


def test_frozen_weekly_fails_through_main(monkeypatch, capsys):
    """main() 경로: 원천과 라이브가 같은 주에 멈춘 채 주간 상한을 하루 넘기면 결정론 실패(rc=2)다 — 조회는 다 성공했고
    데이터 자체가 낡았으니 새 IP 로 다시 볼 일이 아니다. 실패 목록에 계열 이름과 나이가 찍힌다.

    변이(확인): main() 의 주간 check 에서 `max_age=weekly_max_age(...)` 를 빼면 주간 실패 줄이 사라져 빨개진다.
    픽스처: 하니스의 정상 날 원천(라이브와 같은 시점 = 멈춘 원천), 오늘 = 최신 조사기준일 + 주간 상한 + 1일.
    """
    adv, _ = _live()
    wk = adv['weekly']['rows'][-1]['p']
    cap = C.weekly_max_age(wk, adv.get('holidays'))
    r = _run(monkeypatch, capsys, 4, today=C.period_end(wk) + (cap + 1) * DAY)
    assert r['rc'] == C.EXIT_DETERMINISTIC, r['out'][-800:]
    fail_block = r['out'][r['out'].index('FAIL:'):]
    assert '주간: 최신 시점 %s 이(가) 끝난 지 %d일' % (wk, cap + 1) in fail_block, fail_block[:800]


def test_current_data_passes_every_ceiling(monkeypatch, capsys):
    """저장소의 지금 데이터는 상한에 걸리지 않는다 — 오늘을 '최신 주간을 정상으로 들고 있을 수 있는 마지막 날'
    (조사기준일 + GRACE_WEEKLY)로 고정하고 main() 을 돌려 초록이어야 한다.

    ⚠️ 원천이 정당하게 늦는 계열(완비 보류 중인 미분양 등)이 상한에 닿는 것은 **데이터가 앞으로 가서 생기는 일**이라
    시험을 빨갛게 하지 않고 경고만 남긴다(CLAUDE.md '날짜가 지나서 생기는 일은 게이트가 아니라 감시 경고로' — 빨갛게 하면
    배치 커밋·PR CI·매일 예약이 그날 같이 막힌다). 그 경보는 감시(check_freshness)가 실패 메일로 낸다.
    대신 상한이 계열의 정상 발표 주기를 덮는지는 아래 test_ceilings_cover_the_publication_cadence 가 데이터와 무관하게 본다.
    변이(확인): too_old 의 판정(age <= max_age)을 age >= max_age 로 뒤집으면 지금 데이터 실행이 빨개진다.
    픽스처: 저장소의 실제 data.js·data-rest.json·data-size.json(하니스), 오늘 = 최신 주간 조사기준일 + GRACE_WEEKLY.
    """
    adv, rows = _series()
    today = C.period_end(adv['weekly']['rows'][-1]['p']) + C.GRACE_WEEKLY * DAY
    over = [(n, p, (today - C.period_end(p)).days, cap) for n, p, cap in rows
            if (today - C.period_end(p)).days > cap]
    if over:
        import warnings
        warnings.warn('나이 상한에 닿은 계열 %s — 감시가 알린다(시험은 막지 않는다)' % over)
        return
    r = _run(monkeypatch, capsys, 4, today=today)
    assert r['rc'] == 0 and 'VERDICT=ok' in r['out'], r['out'][-800:]
    assert '끝난 지' not in r['out']


def test_ceilings_cover_the_publication_cadence():
    """상한은 계열의 정상 발표 지연을 덮어야 한다 — 짧으면 원천이 정상인 달에도 감시가 헛경보를 낸다.
    하한(일)은 발표 주기에서 잡는다: 주간은 다음 발표 + 연휴로 한 주 거른 경우(14), 월간·금리는 다음 달 중순 발표의
    두 달 치(60), 기본통계·공급은 다음 달 말 발표 + 한 달(95), 전환율·주담대는 실측 정상 지연(90·56) 이상, 연간은 2년(730).
    변이(확인): MAX_AGE_BASIC 을 30 으로, MAX_AGE_WEEKLY 를 9 로, MAX_AGE_SIDO_Q 를 100 으로 줄이면 빨개진다.
    픽스처: 없음(상수만 — 데이터가 앞으로 가도 같은 판정). 모든 MAX_AGE_ 상수가 하한 표에 있는지도 본다(새 상한이 하한 없이
    들어오지 않게).
    """
    floors = {'MAX_AGE_WEEKLY': 14, 'MAX_AGE_MONTHLY': 60, 'MAX_AGE_RATE': 60, 'MAX_AGE_BASIC': 95,
              'MAX_AGE_BUBBLE_CONV': 90, 'MAX_AGE_BUBBLE_LOAN': 56, 'MAX_AGE_ANNUAL': 730,
              'MAX_AGE_SIDO_Q': 125}   # 분기: 분기 끝 + 다음 분기 마지막 달 준공 발표(이듬달 말)까지 약 123일
    low = {k: (getattr(C, k), v) for k, v in floors.items() if getattr(C, k) < v}
    assert not low, '상한이 정상 발표 지연보다 짧다(상한, 하한): %s' % low
    assert set(floors) == {n for n in dir(C) if n.startswith('MAX_AGE_')}, '하한 표에 없는 MAX_AGE_ 상수가 있다'


def test_sido_quarter_ceiling_fails_through_main(monkeypatch, capsys):
    """main() 경로: 라이브 ADV.sido.L(준공 전국 마지막 완결 분기)이 끝난 지 MAX_AGE_SIDO_Q 일을 넘으면 '시도 지표' 실패 줄이
    찍힌다 — 상한을 켠 날(오늘 고정)에만. 상한 날까지는 그 줄이 없다.

    변이(확인): main() 의 시도 지표 검사를 `fails.append(None)` 으로 지우면 첫 단정이, check_age 의 `age > grace` 를
          `age >= grace` 로 바꾸면 둘째 단정이 빨개진다.
    픽스처: 하니스의 정상 날 원천, 오늘 = L 분기 끝 + 상한 + 1일 / + 상한(데이터에서 유도 — 분기를 박지 않는다).
    """
    adv, _ = _live()
    end = C.period_end(C._q_to_date(adv['sido']['L']))
    line = '시도 지표(마지막 수집 %s, 경과 %d일 > %d일)'
    r = _run(monkeypatch, capsys, 4, today=end + (C.MAX_AGE_SIDO_Q + 1) * DAY)
    assert line % (end.isoformat(), C.MAX_AGE_SIDO_Q + 1, C.MAX_AGE_SIDO_Q) in r['out'], r['out'][-800:]
    r = _run(monkeypatch, capsys, 4, today=end + C.MAX_AGE_SIDO_Q * DAY)
    assert '시도 지표(마지막 수집' not in r['out'], r['out'][-800:]


def test_harness_with_ceilings_off_stays_green_however_far_today_moves(monkeypatch, capsys):
    """상한을 끈 하니스(_run 에 today 없음)는 감시의 오늘이 아무리 앞으로 가도 초록이다 — main() 의 날짜 판정이 모두 MAX_AGE_
    고리를 거친다. 그래야 이 하니스를 쓰는 시험(test_freshness_parallel·test_quiz_review_is_a_warning)이 데이터가 멈춘 날에도
    게이트를 막지 않는다(그 경보는 감시가 실패 메일로 낸다).

    재현하는 실제 상태: '시도 지표' 나이 검사가 숫자 200 을 main() 에 박아 하니스가 끄지 못했다. 준공 원천이 멈춰 L 이 2026Q2 에
    머문 채 KST 2027-01-17(6/30 + 201일)이 되면 test_watchdog_stays_green_on_a_normal_day_after_the_deadline·
    test_majority_outage_fails_through_main 이 빨개졌다(전수리뷰 F-1 — 오늘을 고정해 재현).
    변이(확인): main() 의 시도 지표 검사를 상수 대신 숫자 200 으로 되돌리면 빨개진다.
    픽스처: 하니스의 정상 날 원천, 감시의 오늘 = 실제 오늘 + 10년(상한을 켰다면 모든 계열이 넘을 날).
    """
    monkeypatch.setattr(C, 'TODAY', C.TODAY + 3650 * DAY)
    r = _run(monkeypatch, capsys, 4)
    assert r['rc'] == 0 and 'VERDICT=ok' in r['out'], r['out'][-800:]