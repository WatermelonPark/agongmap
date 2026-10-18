# -*- coding: utf-8 -*-
"""썸네일 배경이 글마다 달라지는지 — 지역 편은 그 지역의 해마다 입주 막대, 주간 글은 그 주 1위 시도의 52주 곡선(2026-10-17).

대표 지적: "썸네일에 그래프가 똑같은 거 계속 갖다 쓰는 것 같다." 지역 편은 10년 매매지수 곡선이라 2021년 정점 모양이
지역마다 거의 같았고, 주간 글은 매주 전국 지수 곡선이었다.
픽스처: 저장소의 실제 ADV(occupancy·weekly). 대구(2023~24 정점 뒤 절벽)와 대전(앞으로가 높다)은 막대 모양이 달라야 한다.
무엇을 깨뜨리면 빨개지나(실제로 확인): thumb_zone 이 bars 를 넘기지 않으면 첫 시험이, thumb_weekly 가 전국 곡선을 다시
쓰면 둘째 시험이 빨개진다.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402


def _capture(monkeypatch):
    got = {}
    monkeypatch.setattr(P, '_draw_thumb', lambda group, curve, chip, lines, path, msg, bars=None:
                        got.update(curve=curve, bars=bars) or 'x.png')
    return got


def test_zone_thumb_draws_that_regions_move_in_bars(monkeypatch):
    adv, sts = P.M.load()
    got = _capture(monkeypatch)
    P.thumb_zone({'z': '대구'}, '2027', 3, sts, ['a', '*b*'], adv=adv)
    dg = got['bars']
    P.thumb_zone({'z': '대전'}, '2027', 3, sts, ['a', '*b*'], adv=adv)
    dj = got['bars']
    assert dg and dj and dg != dj
    assert any(e for _, _, e in dg[0]) and any(not e for _, _, e in dg[0])      # 실적과 추정이 함께 있다


def _week(W, vals, rest=-0.05):
    """최신 주 매매값을 vals({시도: 값})로, 나머지 시도는 rest 로 바꾼 W 사본(집계 칸은 그대로 — _weekly_focus 와 같은 시도 거르기)."""
    W = copy.deepcopy(W)
    last = W['rows'][-1]
    for i, z in enumerate(W['regions']):
        if z not in P.SZ.AGG:
            last['ma'][i] = vals.get(z, rest)
    return W


def test_weekly_thumb_curve_follows_the_weeks_top_region(monkeypatch):
    """주간 썸네일 곡선은 그 주 매매 상승 1위 시도의 52주 곡선이고, 오른 시도가 없는 주는 전국 곡선이다(_weekly_focus 규칙).

    예전 시험은 실데이터 최신 주로 focus != '전국' 을 단정해, 오른 시도가 없는 주(실데이터 2024-12-30~2025-01-20 네 주 연속 등)에
    게이트를 막았다(전수리뷰 T3-5·BL1-2). 실데이터는 '곡선 = 그 주 초점의 곡선'만 보고, 두 갈래는 합성 주로 늘 본다.
    변이(실제로 확인): thumb_weekly 가 초점 대신 전국 곡선(_weekly_curve(W, '전국'))을 쓰면 ① 합성 주가 빨개진다.
    픽스처: 저장소의 실제 ADV.weekly(156주) + 최신 주만 고친 사본 둘 — ① 한 시도만 +0.5%(나머지 −0.05%) ② 모든 시도 −0.05%.
    """
    adv, sts = P.M.load()
    W = adv['weekly']
    got = _capture(monkeypatch)
    monkeypatch.setattr(P.sys, 'argv', ['x'])
    P.thumb_weekly(W, sts, ['a', '*b*'])
    focus = P._weekly_focus(W, [])
    assert got['curve'] == (P._weekly_curve(W, focus) or P._thumb_curve(sts, '전국'))
    nat = P._weekly_curve(W, '전국')
    top = next(z for z in P.MW.SIDO if z in W['regions'] and P._weekly_curve(_week(W, {z: 0.5}), z) not in (None, nat))
    W1 = _week(W, {top: 0.5})
    P.thumb_weekly(W1, sts, ['a', '*b*'])
    assert P._weekly_focus(W1, []) == top
    assert got['curve'] == P._weekly_curve(W1, top) != P._weekly_curve(W1, '전국')
    W2 = _week(W, {})
    P.thumb_weekly(W2, sts, ['a', '*b*'])
    assert P._weekly_focus(W2, []) == '전국'
    assert got['curve'] == (P._weekly_curve(W2, '전국') or P._thumb_curve(sts, '전국'))
