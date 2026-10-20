# -*- coding: utf-8 -*-
"""퀴즈 제도 문항의 검토 기한이 지나도 감시(watchdog)는 빨개지지 않는다 — 경고로만 남는다(2026-09-26 데이터 감사).

check_freshness.main() 이 QR.overdue(...) 를 fails 에 넣고 있어, 2026-12-15(1개)·2027-03-15(4개)부터 누가
home-app.js 를 고칠 때까지 감시가 매일 VERDICT=final 로 빨개질 참이었다. 그 기간의 'Run failed' 메일은 퀴즈
때문인지 진짜 데이터 뒤처짐 때문인지 구별되지 않는다 — 진짜 경보가 이미 예상한 빨강 속에 묻힌다. 이제 기한
경과는 WARN 목록·::warning:: 주석·잡 요약으로만 나가고, 진짜 뒤처짐은 그대로 빨갛다. 제도 문항을 0개 찾은 것
(감시가 조용히 꺼진 것)은 계속 실패다(test_home_src 의 취지).

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - main() 의 `WARN.extend(_qw)` 를 `fails.extend(_qw)` 로 되돌리면 → 정상 날 시나리오가 rc=2 로 빨강
  - check_quiz_review 가 기한 지난 문항을 warns 대신 fails 에 넣으면 → 단위 단정과 정상 날 시나리오가 빨강
  - check_quiz_review 의 '0개면 실패' 를 지우면 → 0개 단정이 빨강
  - _emit_warnings 호출을 지우면 → 로그의 WARN 단정이 빨강
픽스처: 저장소의 실제 home-app.js(home_src 로 읽는다)와, 모든 검토 기한이 지난 가짜 오늘(2030-01-01, KST).
main() 은 test_freshness_parallel 의 하니스로 통째로 돌린다 — 라이브 응답은 저장소 파일, 원천은 라이브와 같은
시점(정상 날)이고, 진짜 뒤처짐 시나리오는 연간 '보급률'만 원천이 1년 앞선 상태다.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_freshness as C  # noqa: E402
import quiz_review as QR  # noqa: E402
from test_freshness_parallel import _run  # noqa: E402  (main() 통째 하니스 — 네트워크 없음)

LATE = datetime.date(2030, 1, 1)


def test_overdue_items_are_warnings_not_failures():
    n = len(QR.items(C.HS.home_source()))
    assert n > 0
    fails, warns = C.check_quiz_review(LATE)
    assert fails == [] and len(warns) == n, (fails, warns)
    assert C.check_quiz_review(datetime.date(2026, 9, 15)) == ([], [])


def test_zero_quiz_items_still_fails():
    fails, warns = C.check_quiz_review(LATE, src='// 제도 문항이 하나도 없는 홈 스크립트')
    assert fails and '0개' in fails[0] and warns == []


def test_watchdog_stays_green_on_a_normal_day_after_the_deadline(monkeypatch, capsys):
    monkeypatch.setattr(C.KST, 'today', lambda now=None: LATE)
    r = _run(monkeypatch, capsys, 4)
    assert r['rc'] == 0, '검토 기한 경과만으로 감시가 빨개졌다:\n' + r['out'][-800:]
    assert 'VERDICT=ok' in r['out'] and 'WARN: 알림' in r['out'] and '검토 기한' in r['out']


def test_real_staleness_is_still_red_after_the_deadline(monkeypatch, capsys):
    monkeypatch.setattr(C.KST, 'today', lambda now=None: LATE)
    r = _run(monkeypatch, capsys, 4, bump={'보급률': 1})
    assert r['rc'] == C.EXIT_DETERMINISTIC, r['out'][-800:]
    fail_block = r['out'][r['out'].index('FAIL:'):]
    assert '보급률' in fail_block and '검토 기한' not in fail_block, '퀴즈 알림이 실패 목록에 섞였다'


def test_warnings_reach_the_job_summary_and_annotations(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    p = tmp_path / 'summary.md'
    C._emit_warnings(['퀴즈 제도 문항 검토 기한 2026-12-15 지남: LTV 40% 문항'], str(p))
    out = capsys.readouterr().out
    assert '::warning title=감시 알림(실패 아님)::퀴즈 제도 문항 검토 기한 2026-12-15 지남: LTV 40%25 문항' in out
    assert '검토 기한 2026-12-15' in p.read_text(encoding='utf-8')


def test_review_tags_are_read_in_any_order_and_half_tags_fail():
    """제도 문항의 asof·review 는 자리·순서와 상관없이 읽힌다. 하나만 단 문항은 감시가 실패로 알린다(전수리뷰 P 묶음 overflow).

    재현한 상태(2026-10-18): quiz_review.ITEM 이 asof 를 opts 바로 뒤, review 를 asof 바로 뒤에서만 찾아, review 를 먼저 쓰거나 answer 뒤에
    단 제도 문항은 조용히 빠졌고 check_quiz_review 는 0개일 때만 실패했다.
    픽스처: 실제 홈 스크립트의 제도 문항 수와, 세 꼴(정순·역순·answer 뒤)의 합성 문항 + review 를 빠뜨린 합성 문항.
    변이(실제로 확인): items() 를 옛 정순 정규식으로 되돌리면, check_quiz_review 의 half_tagged 실패를 지우면 빨개진다.
    """
    src = C.HS.home_source()
    assert len(QR.items(src)) == src.count("asof:'") > 0, '실제 홈의 제도 문항 가운데 못 읽은 것이 있다'
    syn = ("{q:'정순', opts:['O','X'], asof:'2026-09-15', review:'2027-03-15', answer:0, exp:'a'},\n"
           "{q:'역순', opts:['O','X'], review:'2027-03-15', asof:'2026-09-15', answer:0, exp:'b'},\n"
           "{q:'뒤에', opts:['O','X'], answer:1, asof:'2026-09-15', review:'2026-12-15', exp:'c'},\n"
           "{q:'제도 아님', opts:['O','X'], answer:1, exp:'d'},\n")
    assert [q for q, _, _ in QR.items(syn)] == ['정순', '역순', '뒤에']
    assert QR.half_tagged(syn) == [] and C.check_quiz_review(LATE, src=syn)[0] == []
    half = syn + "{q:'반쪽', opts:['O','X'], asof:'2026-09-15', answer:0, exp:'e'},\n"
    assert QR.half_tagged(half) == ['반쪽']
    fails, _ = C.check_quiz_review(LATE, src=half)
    assert fails and '반쪽' in fails[0], fails
