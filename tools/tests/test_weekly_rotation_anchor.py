# -*- coding: utf-8 -*-
"""주간 글 4주 로테이션('이번 주의 지표'·더 보기 링크)이 해가 바뀌어도 한 주씩 넘어간다(2026-09-26 데이터 감사).

rot_index 가 ISO 주차로 `(주차-1) % 4` 를 셌다. 53주인 해에는 W53 과 다음 해 W01 이 둘 다 0 이라, 2026-12-28 과
2027-01-04 조사분 글이 같은 전세가율 절과 같은 링크 묶음을 연달아 싣는다(회차 간 반복 금지 위반). 고정 월요일에서
지난 주 수로 센다(write-reminder.yml 의 격주 판정과 같은 방식).

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - rot_index 를 옛 식 `(date.isocalendar()[1] - 1) % 4` 로 되돌리면 → 2026-12-28 → 2027-01-04 에서 연속 단정이 빨강
  - ROT_ANCHOR 를 다른 월요일(예: 2026-01-05)로 옮기면 → 올해 순서 유지 단정이 빨강
픽스처: 2024~2040 년의 모든 월요일(R-ONE 주간 조사 기준일은 월요일이고 연말 주도 거르지 않는다 — 2024-12-30,
2025-12-29 가 실제 계열에 있다). 53주인 해(2026·2032·2037)가 들어 있는지 시험이 스스로 확인한다.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402


def _mondays(y0, y1):
    d = datetime.date(y0, 1, 1)
    d += datetime.timedelta(days=(7 - d.weekday()) % 7)
    out = []
    while d.year <= y1:
        out.append(d)
        d += datetime.timedelta(days=7)
    return out


def test_rotation_moves_one_step_every_week_across_years():
    ms = _mondays(2024, 2040)
    assert [d for d in ms if d.isocalendar()[1] == 53], '픽스처에 53주인 해가 없다 — 시험이 아무것도 못 가른다'
    stuck = [(a.isoformat(), b.isoformat()) for a, b in zip(ms, ms[1:])
             if P.rot_index(b.isoformat()) != (P.rot_index(a.isoformat()) + 1) % 4]
    assert not stuck, '로테이션이 한 칸씩 넘어가지 않는 주: %s' % stuck[:3]


def test_rotation_keeps_the_order_already_published_this_year():
    """2026 년에 이미 나간 글의 순서를 바꾸지 않는다 — 기준 월요일이 ISO 2026-W01 첫날이라 옛 식과 같다."""
    for d in _mondays(2026, 2026):
        if d.isocalendar()[0] != 2026:
            continue
        assert P.rot_index(d.isoformat()) == (d.isocalendar()[1] - 1) % 4, d
