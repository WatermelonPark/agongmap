# -*- coding: utf-8 -*-
"""없는 값이 조용히 빠지지 않는다 (백로그 16, 리뷰 2026-09-16 8·9번).

두 자리를 잠근다.

① 인허가 신호가 비면 리포트의 '3년 너머' 줄이 경고 없이 사라진다. 틀린 값이 아니라 없는
   값이라 어떤 검사에도 안 걸렸다. tools/batch_notes.py 가 그것을 ⚠️ 줄로 올리고, 그 줄이
   메일까지 간다.
② 감시의 값 대조가 통과 결과(None)를 fails 에 넣어 개수 게이트의 분모를 부풀렸다.

⚠️ 픽스처에 지금의 지역 이름을 박지 않는다(2026-09-11 에 그런 시험이 배치를 막았다).
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import batch_notes as N  # noqa: E402
import check_freshness as C  # noqa: E402
import format_batch_report as F  # noqa: E402
import update_adv_data as U  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def _adv(*zones):
    return {'sido': {'zones': [{'z': z, 'pbr': p} for z, p in zones]}}


# ── ① 인허가 신호가 빠진 지역 ─────────────────────────────────────────────

def test_zone_without_signal_is_named():
    """신호가 None 인 지역만, 표시 순서 그대로 이름이 나온다.

    변이: permit_gaps 의 조건을 `is None` 에서 `not z.get('pbr')` 로 바꾸면 빨개진다
          (신호가 정확히 0.0 인 지역까지 '빠짐'으로 잘못 알린다).
    픽스처: 세 지역 중 하나는 신호가 None(인허가 누계 중간에 빈 달이 생겨 24개월 창을 못
            채운 상태), 하나는 0.0(인허가가 실제로 0), 하나는 정상.
    """
    adv = _adv(('가', 0.8), ('나', None), ('다', 0.0))
    assert N.permit_gaps(adv) == ['나']
    out = N.lines(adv)
    assert len(out) == 1 and out[0].startswith(N.WARN) and '나' in out[0]


def test_nothing_is_printed_when_every_zone_has_a_signal():
    """평상시에는 한 줄도 찍지 않는다 — 찍으면 매 회차 메일이 간다.

    변이: lines() 가 gaps 가 비어도 줄을 만들게 바꾸면 빨개진다.
    픽스처: 모든 지역에 신호가 있는 상태(2026-09-17 현재의 19곳이 이렇다).
    """
    assert N.lines(_adv(('가', 0.8), ('나', 1.2))) == []
    assert N.lines({}) == []


def test_live_data_has_no_gap_right_now():
    """저장된 data.js 로도 돈다. 값을 단정하지 않고 읽히는지와 모양만 본다.

    변이: batch_notes.zones 가 읽는 키를 `zones` 가 아닌 다른 이름으로 바꾸면 빨개진다
          (지역을 하나도 못 읽어 늘 '빠짐 없음'이 되는 상태).
    픽스처: 저장소의 실제 data.js.
    """
    import month_lag as ML
    adv, _ = ML.load()
    zones = N.zones(adv)          # 도구가 읽는 바로 그 자리로 읽는다
    assert len(zones) >= 10, '지역을 읽지 못했다 — 검사가 헛돈다'
    assert all('pbr' in z for z in zones), 'pbr 칸이 없는 지역이 있다 — 빠짐을 셀 수 없다'
    assert isinstance(N.permit_gaps(adv), list)


def test_gap_line_reaches_the_mail():
    """워크플로가 그 줄을 배치 기록에 올리고, 알림이 사람 말로 바꿔 메일을 보낸다.

    변이: 워크플로의 `NOTES=$(python3 tools/batch_notes.py` 줄이나 그 아래 rep 을 지우면
          빨개진다. format_batch_report 의 '인허가 신호 빠짐' 대응을 지우면 내부 문구가
          본문에 그대로 새어 마지막 단정이 빨개진다.
    픽스처: 나머지는 전부 정상인 수요일 회차에 빠짐 줄 하나가 더해진 기록.
    """
    wf = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    code = '\n'.join(ln for ln in wf.splitlines() if not ln.lstrip().startswith('#'))
    i = code.find('NOTES=$(python3 tools/batch_notes.py')
    assert i >= 0, '워크플로가 batch_notes 를 부르지 않는다'
    assert re.search(r'rep "\$LN"', code[i:i + 400]), '읽은 줄을 배치 기록에 올리지 않는다'
    assert i < code.find('git add -A -- $TARGETS'), '커밋 뒤에 부르면 그 회차 기록에 못 실린다'
    raw = ('✅ 러너 3/3 clean · 채택 주간 2026-09-14 / 월간 2026-08 / 공급 2026Q2\n'
           + N.lines(_adv(('가', None)))[0] + '\n')
    body, mail = F.build(raw, '2026-09-17 18:33', 'u', 'O', 2)
    assert mail is True
    assert "'3년 너머' 줄이 빠졌습니다" in body
    assert '누계 결측' not in body and 'pbr' not in body, '내부 용어가 본문에 샜다'


# ── ② 감시의 개수 게이트 분모 ─────────────────────────────────────────────

def _series(n_dates=2):
    dates = ['2026.%02d' % (5 + i) for i in range(n_dates)]
    return {'dates': dates, 'series': {r: [1.0] * n_dates for r in U.SUPPLY_SIDO}}


def test_value_check_does_not_refetch_after_a_failed_lookup(monkeypatch):
    """나이 검사 조회가 실패해 캐시가 비었으면 원천을 다시 부르지 않는다.

    변이: supply_value_fail 의 캐시 조건(`not in _COMPLETE_CACHE`)을 지우면 빨개진다.
    픽스처: 원천이 광역 장애라 앞선 조회가 실패한 상태 — 캐시에 그 (표, 시작월)이 없다.
            2026-08-12 에 KOSIS·R-ONE 이 함께 타임아웃 났을 때의 모양이다.
    """
    monkeypatch.setattr(C, '_COMPLETE_CACHE', {})
    calls = []

    def spy(*a, **k):
        calls.append(a)
        raise RuntimeError('원천 타임아웃')
    monkeypatch.setattr(C, 'rone_latest_complete', spy)
    assert C.supply_value_fail('분양', _series(), 'T', '202605') is None
    # ⚠️ 예외를 던져 잡으려 하면 안 된다. check_supply_value 가 조회 실패를 except 로 삼키므로
    #    그 시험은 조건을 지워도 초록이다(2026-09-17 실제로 그랬다). 호출 횟수를 센다.
    assert calls == [], '실패한 조회 직후에 원천을 다시 불렀다'


def test_value_check_still_reports_a_real_mismatch(monkeypatch):
    """조회가 성공한 계열은 그대로 값을 견준다 — 조건을 넣다가 검사 자체를 꺼뜨리지 않는다.

    변이: supply_value_fail 이 늘 None 을 돌려주게 바꾸면 빨개진다.
    픽스처: 시점은 같은데 원천 시도 합이 우리 것보다 5 큰 상태(갱신이 멈춘 계열).
    """
    n = len(U.SUPPLY_SIDO)
    monkeypatch.setattr(C, '_COMPLETE_CACHE', {('T', '202605'): ('202606', float(n + 5))})
    r = C.supply_value_fail('분양', _series(), 'T', '202605')
    assert r and '값' in r


def test_main_never_appends_a_passing_value_check():
    """통과(None)를 fails 에 넣지 않는다 — len(fails) 는 개수 게이트의 분모다.

    변이: main 의 공급 구획을 `fails.append(supply_value_fail(...))` 로 되돌리면 빨개진다.
          분모가 계열 수만큼 부풀어, 절반 넘게 조회에 실패해도 SKIPPED×2 > len(fails) 가
          거짓이 되어 OK 가 찍힌다(2026-08-13 재시도 루프에서 확정한 것과 같은 회귀).
    픽스처: check_freshness.py 원문. main 은 원천을 스무 번 불러야 돌아 직접 실행하지 못한다.
    """
    src = io.open(os.path.join(ROOT, 'tools', 'check_freshness.py'), encoding='utf-8').read()
    code = '\n'.join(ln for ln in src.splitlines() if not ln.lstrip().startswith('#'))
    assert not re.search(r'fails\.append\(\s*(?:check_supply_value|supply_value_fail)\(', code)
    m = re.search(r'r = supply_value_fail\([^\n]*\)\s*\n\s*if r:\s*\n\s*fails\.append\(r\)', code)
    assert m, '값 대조 결과를 참일 때만 넣는 구조가 아니다'


# ── ③ 퀴즈 검토 기한 경과는 배치 기록의 ℹ️ 줄로 사람에게 간다 ─────────────────────────
QUIZ_SRC = ("{q:'가상 제도 문항 <b>하나</b>', opts:['a','b'], asof:'2026-09-15', review:'2026-12-15', answer:0},"
            "{q:'가상 제도 문항 둘', opts:['a','b'], asof:'2026-09-15', review:'2027-03-15', answer:1},")


def test_overdue_quiz_item_becomes_an_info_line():
    """기한이 지난 제도 문항만, 형식기가 '참고'로 싣는 ℹ️ 줄로 나온다. 기한 전날에는 아무것도 없다.

    감시는 기한 경과를 경고(주석)로만 남겨 메일이 가지 않는다(2026-09-26 데이터 감사 #13). 이 줄이 사람에게
    닿는 통로다 — 형식기는 ℹ️ 줄을 월요일 확인 메일에 싣는다.
    변이: quiz_review_lines 가 빈 목록만 돌려주면 이 시험이, main() 에서 붙이는 줄을 지우면 아래 main 시험이
          빨개진다(둘 다 확인). ⚠️ lines(adv) 에 넣으면 날짜가 지나는 날 위 '한 줄도 없다'
          시험이 빨개져 게이트가 데이터 커밋을 막으므로 따로 둔다.
    픽스처: 홈 퀴즈와 같은 모양(asof·review)의 가상 문항 둘 — 실제 첫 기한(2026-12-15)과 그다음(2027-03-15).
    """
    import datetime
    D = datetime.date
    assert N.quiz_review_lines(D(2026, 12, 14), QUIZ_SRC) == []
    out = N.quiz_review_lines(D(2026, 12, 15), QUIZ_SRC)
    assert len(out) == 1 and out[0].startswith(N.ML.MARK) and '가상 제도 문항 하나' in out[0], out
    assert not F.LAG_LINE.match(out[0]), '뒤처짐 줄로 읽히면 형식기가 참고 줄로 싣지 않는다'
    assert len(N.quiz_review_lines(D(2027, 3, 15), QUIZ_SRC)) == 2


def test_quiz_line_reaches_the_monday_report():
    """ℹ️ 퀴즈 줄이 형식기(format_batch_report.build)의 월요일 본문에 실린다 — 두 파일 사이의 형식 계약."""
    import datetime
    ln = N.quiz_review_lines(datetime.date(2026, 12, 15), QUIZ_SRC)[0]
    body, mention = F.build(ln + '\n', '2026-12-21 17:10', 'https://example.invalid/run', 'owner', 0)
    assert mention and '가상 제도 문항 하나' in body, body


def test_main_appends_quiz_lines_from_the_real_home(tmp_path, monkeypatch, capsys):
    """배치가 부르는 main() 이 실제 홈 스크립트로 퀴즈 검사를 해 줄을 붙인다(오늘을 먼 미래로 돌려 기한을 넘긴다).

    변이: main() 에서 `+ quiz_review_lines(kst.today())` 를 지우면 빨개진다(확인).
    픽스처: 인허가 신호가 모두 있는 최소 data.js(인허가 줄 없음) + 저장소의 실제 홈 스크립트, 오늘 = 2099-01-01.
    """
    import json
    import kst
    p = tmp_path / 'data.js'
    p.write_text('/*ADV_DATA_START*/ const ADV=%s; /*ADV_DATA_END*/\nconst STATS={};\n'
                 % json.dumps(_adv(('가', 0.8)), ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(kst, 'today', lambda now=None: __import__('datetime').date(2099, 1, 1))
    assert N.main(['--data', str(p)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out and all(ln.startswith(N.ML.MARK) and '검토 기한' in ln for ln in out), out
    assert not any('검사 불가' in ln for ln in out), out
