# -*- coding: utf-8 -*-
"""사이클 이론편(1~7편) 전제 가드 — 초안만 멈추고 게이트는 막지 않으며, 멈춘 편은 배치 기록 줄로 알린다(대표 결정 2026-10-18 D1).

이론편 본문은 발행 당시 데이터의 사실(‘공급이 적은 분기에 전세가 더 올랐다’, ‘금리가 올랐는데 매매·전세가 함께 올랐다’ …)을
문장으로 못 박는다. 지금 데이터가 그 전제와 어긋나면 make_theory_post.guard_values 가 SystemExit 로 그 편의 초안 생성을 멈춘다.
게이트 시험은 그 데이터 상태로 실패하지 않고(실데이터 시험은 멈춤 갈래도 받는다), batch_notes.theory_claim_lines 가 편마다 ℹ️ 한
줄을 배치 기록에 올린다(옛 3편 sync_claim_lines 를 접었다). 가드가 SystemExit 말고 다른 예외로 죽으면 코드 결함이다 — 실데이터
시험이 그대로 빨갛고, 기록 줄은 '검사 불가'다.

픽스처: 실데이터 시험은 저장소 data.js·cycle/index.html 을 그대로 읽는다(편마다 통과 또는 멈춤 — 실데이터가 한 갈래뿐이면 빠진
갈래를 합성으로 채워 두 갈래가 늘 돈다). 나머지는 guard_values 를 편마다 정한 결과(통과·멈춤·코드 결함)로 바꾼 합성 상태다 — 1·2편이
같은 고리① 문구로 멈춘 날(2026-09 재산정 같은), 금리 인하로 7편 ③이 깨진 날, 6편 가드가 셈을 못 하고 죽은 날.
무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - theory_claim_lines 가 SystemExit 를 삼키면(빈 목록) → test_stopped_posts_get_one_info_line_each·실데이터 시험의 합성 갈래
  - 같은 이유로 멈춘 이웃 편 묶기를 빼면 → test_stopped_posts_get_one_info_line_each('1편'·'2편' 두 줄이 된다)
  - 코드 결함(그 밖의 예외) 받기를 빼면 → test_crashing_guard_is_reported_as_unchecked(예외가 그대로 샌다)
  - 도구·데이터를 못 올릴 때의 받기를 빼면 → test_unloadable_tools_are_reported
  - render 가 guard_values 를 거치지 않고 제 가드를 따로 두면 → test_render_and_batch_notes_share_one_guard
  - theory_claim_lines 가 데이터 상태 멈춤(멈춤 문구의 T.NOT_THE_TEXT)을 가르지 않거나, 데이터 상태 멈춤 문구 하나에서 그 말을
    빼면 → test_data_state_stops_are_not_blamed_on_the_published_post
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import batch_notes as N  # noqa: E402
import format_batch_report as F  # noqa: E402
import make_theory_post as T  # noqa: E402

STOP_LINE = re.compile(r'^%s 사이클 ([\d·]+)편 (?:전제가 지금 데이터와 어긋남 — .+ \(초안 생성만 멈춤, 발행본 재검토\)'
                       r'|초안 생성 멈춤\(데이터 상태, 발행본과 무관\) — .+)$' % re.escape(N.ML.MARK))
DATA_LINE = re.compile(r'^%s 사이클 ([\d·]+)편 초안 생성 멈춤\(데이터 상태, 발행본과 무관\) — ' % re.escape(N.ML.MARK))


def _reported(lines):
    """기록 줄에서 '멈췄다'고 알린 편 번호들(전제가 어긋남·데이터 상태 두 꼴)."""
    out = set()
    for ln in lines:
        m = STOP_LINE.match(ln)
        if m:
            out.update(int(x) for x in m.group(1).split('·'))
    return out


def _stop7(D):
    raise SystemExit('7편을 만들 수 없다 — 최근 금리가 오르는 동안 매매·전세가 함께 오르지 않았다(합성). 문장을 먼저 고칠 것.')


def test_every_post_guard_on_real_data_fills_or_is_reported(monkeypatch):
    """저장소 실데이터로 1~7편 가드를 돌린다: 통과한 편은 초안 본문 자리 표시자가 하나도 남지 않고, 멈춘 편은 멈춤 문구가 그 편을
    가리키며 batch_notes 기록 줄에 그 편이 실린다. 가드가 날 예외로 죽으면(코드 결함) 이 시험이 빨갛다 — 기록 줄에도 '검사 불가'가
    없어야 한다."""
    monkeypatch.setattr(T.P, 'rivals', lambda *a, **k: None)
    D, data = T.P.cycle_d(), T.M.load()
    seen = {'ok': [], 'stop': []}

    def check(n, lines):
        try:
            T.guard_values(n, D, data)
        except SystemExit as e:
            m = re.match(r'^([\d·]+)편을 만들 수 없다 — .+', str(e))
            assert m and str(n) in m.group(1).split('·'), str(e)
            assert n in _reported(lines), ('%d편이 멈췄는데 기록 줄에 없다' % n, lines)
            seen['stop'].append(n)
            return
        html = T.render(next(p for p in T.POSTS if p['n'] == n))
        assert '%(' not in html, '%d편 초안에 채우지 못한 자리가 남았다' % n
        seen['ok'].append(n)

    lines = N.theory_claim_lines()
    assert not [ln for ln in lines if '검사 불가' in ln], lines
    assert all(STOP_LINE.match(ln) for ln in lines), lines
    for post in T.POSTS:
        check(post['n'], lines)
    assert len(seen['ok']) + len(seen['stop']) == len(T.POSTS) >= 7
    if not seen['stop']:                  # 실데이터가 모두 통과한 회차 — 멈춤 갈래를 합성으로 채운다(금리 인하로 7편 ③이 깨진 날)
        monkeypatch.setattr(T, 'link7_values', _stop7)
        check(7, N.theory_claim_lines())
    if not seen['ok']:                    # 모두 멈춘 회차 — 통과 갈래를 합성으로 채운다(3편 동조성 가드를 연다)
        monkeypatch.setattr(T, 'check_sync_claims', lambda rows=None: None)
        check(3, [])
    assert seen['ok'] and seen['stop'], seen


def _stub(monkeypatch, outcomes):
    """guard_values 를 편마다 정한 결과로 바꾼다 — 값이 예외면 던지고, 없으면 통과. 저장소 데이터는 읽지 않는다."""
    monkeypatch.setattr(T.P, 'cycle_d', lambda: {})
    monkeypatch.setattr(T.M, 'load', lambda: ({}, {}))

    def guard(n, D=None, data=None):
        r = outcomes.get(n)
        if isinstance(r, BaseException):
            raise r
        return {}
    monkeypatch.setattr(T, 'guard_values', guard)


def test_no_line_when_every_premise_holds(monkeypatch):
    _stub(monkeypatch, {})
    assert N.theory_claim_lines() == []


def test_stopped_posts_get_one_info_line_each(monkeypatch):
    """멈춘 편마다 ℹ️ 한 줄 — 같은 문구로 멈춘 이웃 편(1·2편은 고리① 전제를 함께 쓴다)은 한 줄로 묶고, 멈춤 문구 머리('N편을 만들
    수 없다 — ')와 꼬리('문장을 먼저 고칠 것')는 떼고 이유만 싣는다."""
    l1 = '1·2편을 만들 수 없다 — 고리① 전제(공급이 적은 분기의 전세 상승률 > 많은 분기)가 /cycle/ 정본과 어긋난다(0.5 · 1 · 1.2). 문장을 먼저 고칠 것.'
    _stub(monkeypatch, {1: SystemExit(l1), 2: SystemExit(l1),
                        7: SystemExit('7편을 만들 수 없다 — 최근 금리가 오르는 동안 매매·전세가 함께 오르지 않았다. 7편 문장을 먼저 고칠 것.')})
    out = N.theory_claim_lines()
    assert out == [
        '%s 사이클 1·2편 전제가 지금 데이터와 어긋남 — 고리① 전제(공급이 적은 분기의 전세 상승률 > 많은 분기)가 /cycle/ 정본과 '
        '어긋난다(0.5 · 1 · 1.2). (초안 생성만 멈춤, 발행본 재검토)' % N.ML.MARK,
        '%s 사이클 7편 전제가 지금 데이터와 어긋남 — 최근 금리가 오르는 동안 매매·전세가 함께 오르지 않았다. '
        '(초안 생성만 멈춤, 발행본 재검토)' % N.ML.MARK], out
    assert _reported(out) == {1, 2, 7}
    assert all(not F.LAG_LINE.match(ln) for ln in out), '뒤처짐 줄로 읽히면 형식기가 참고 줄로 싣지 않는다'


def test_crashing_guard_is_reported_as_unchecked(monkeypatch):
    """가드가 SystemExit 말고 다른 예외로 죽으면(코드 결함 — 끝 분기 빈칸의 TypeError 같은) 배치를 멈추지 않고 '검사 불가'로 적는다."""
    _stub(monkeypatch, {6: TypeError("'>' not supported between instances of 'NoneType' and 'float'")})
    assert N.theory_claim_lines() == ["%s 사이클 6편 검사 불가 — TypeError: '>' not supported between instances of "
                                      "'NoneType' and 'float'" % N.ML.MARK]


def _data_stops(monkeypatch):
    """데이터 상태로 멈추는 갈래마다 실제 가드(guard_values)를 돌려 얻은 멈춤 [(편, SystemExit)] — 합성 입력이라 저장소 데이터와 무관하다."""
    import theory_link3 as L3

    def grab(n, D, data):
        with pytest.raises(SystemExit) as e:
            T.guard_values(n, D, data)
        return n, e.value

    def rebased(adv, sts):
        raise L3.Link3DataError('매매지수 기준 단절 — 매매지수 2026.01 (27개 지역, 예: 서울 189.83→94.62)')
    monkeypatch.setattr(L3, 'link3_numbers', rebased)
    sts5 = {k: {'dates': ['2026.%02d' % m for m in range(1, last + 1)], 'series': {'전국': [1000] * last}}
            for k, last in (('준공', 8), ('착공', 7))}
    adv6 = {'sido': {'H': 12, 'zones': [dict(z='가', fut=1000, need=0)]}}
    D6 = {'prose': {}, 'link6_regional': []}

    def D7(je):
        return {'rate_overlay': {'t': [2026.0, 2026.25, 2026.5], 'maemae': [100.0, 101.0, 102.0], 'jeonse': je,
                                 'rate': [3.0, 3.1, 3.2], 'jratio': [None] * 3}, 'prose': {'rate_r': '−0.5', 'rate_n': '3'}}
    return [grab(4, {}, ({}, {})), grab(5, {}, ({}, sts5)), grab(6, D6, (adv6, None)),
            grab(7, D7([None, None, None]), None), grab(7, D7([100.0, None, 101.0]), None)]


def test_data_state_stops_are_not_blamed_on_the_published_post(monkeypatch):
    """문장 전제가 아니라 데이터 상태로 멈춘 편은 '전제가 어긋남 … 발행본 재검토'가 아니라 '데이터 상태' 줄로 알린다 — 발행본을 다시
    볼 일이 아니라 다음 배치에서 풀리는 일인데, 같은 꼴로 쓰면 월요일 확인 메일이 발행본 재검토를 시킨다(전수리뷰 G1a 검토).
    멈춤 문구와 판별이 한 상수(make_theory_post.NOT_THE_TEXT)를 쓰는지도 갈래마다 실제 가드의 문구로 본다.

    변이(각각 실제로 확인): theory_claim_lines 가 NOT_THE_TEXT 로 가르지 않으면(모두 '전제가 어긋남') 다섯 갈래가 모두 빨갛다. 4편
    Link3DataError 멈춤 문구에서 NOT_THE_TEXT 를 빼면(고치기 전 문구) 4편 갈래가 빨갛다.
    픽스처: 갈래마다 그 상태만 만든 합성 입력 — 4편 매매지수 기준 단절(2026-09-28 실제 사례 모양의 Link3DataError), 5편 준공 2026.08·
    착공 2026.07(착공 표만 한 달 늦은 회차, Link4DataError), 6편 적정물량이 0 인 판정 칸, 7편 세 값이 다 찬 분기가 없는 금리 오버레이와
    가운데 분기 전세가 빈 오버레이."""
    stops = _data_stops(monkeypatch)
    assert len(stops) == 5
    for n, e in stops:
        assert T.NOT_THE_TEXT in str(e), (n, str(e))
        _stub(monkeypatch, {n: e})
        out = N.theory_claim_lines()
        assert len(out) == 1 and DATA_LINE.match(out[0]) and DATA_LINE.match(out[0]).group(1) == str(n), out
        assert '발행본 재검토' not in out[0] and STOP_LINE.match(out[0]) and _reported(out) == {n}, out


def test_unloadable_tools_are_reported(monkeypatch):
    def boom():
        raise RuntimeError('/cycle/ 에서 D 블록을 찾지 못했다')
    monkeypatch.setattr(T.P, 'cycle_d', boom)
    out = N.theory_claim_lines()
    assert out == ['%s 사이클 이론편 검사 불가 — RuntimeError: /cycle/ 에서 D 블록을 찾지 못했다' % N.ML.MARK], out


def test_render_and_batch_notes_share_one_guard(monkeypatch):
    """초안 도구(render)와 배치 기록(theory_claim_lines)은 같은 가드 함수(guard_values) 하나를 부른다 — 둘이 따로 재면 한쪽이
    멈추는데 다른 쪽은 '이상 없음'이라 말할 수 있다(CLAUDE.md 같은 대상은 같은 코드)."""
    def guard(n, D=None, data=None):
        if n == 5:
            raise SystemExit('5편을 만들 수 없다 — 가상의 깨진 전제. 문장을 먼저 고칠 것.')
        return {}
    monkeypatch.setattr(T, 'guard_values', guard)
    monkeypatch.setattr(T.P, 'rivals', lambda *a, **k: None)
    with pytest.raises(SystemExit) as e:
        T.render(next(p for p in T.POSTS if p['n'] == 5))
    assert '가상의 깨진 전제' in str(e.value)
    assert _reported(N.theory_claim_lines()) == {5}


def test_info_lines_reach_the_monday_report():
    """ℹ️ 이론편 줄이 형식기(format_batch_report.build)의 월요일 본문 '참고'에 실린다 — 두 파일 사이의 형식 계약."""
    ln = '%s 사이클 7편 전제가 지금 데이터와 어긋남 — 최근 금리가 오르는 동안 매매·전세가 함께 오르지 않았다. ' \
         '(초안 생성만 멈춤, 발행본 재검토)' % N.ML.MARK
    assert STOP_LINE.match(ln)
    body, mention = F.build(ln + '\n', '2026-12-21 17:10', 'https://example.invalid/run', 'owner', 0)
    assert mention and '사이클 7편 전제가' in body, body
