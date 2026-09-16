# -*- coding: utf-8 -*-
"""클라우드 배치의 검증 게이트(pytest)는 생성기 뒤, 커밋 앞에 있어야 한다.

2026-09-16 전체 리뷰: 게이트가 생성기 앞에 있었는데, 그 사이 세 세션이 넣은 정합 시험 5개
(weekly/·zone/·monthly/)가 **커밋된 옛 페이지**를 **새 data.js**로 다시 구운 결과와 대조했다.
데이터가 정상적으로 바뀐 날(주간 발표·인허가 새 달)마다 게이트가 빨개져 그날 데이터 커밋
전체가 막힌다. 로컬 러너는 pytest 없이 돌아 PC가 먼저 돌면 가려진다.

워크플로 셸은 pytest가 실행할 수 없으므로 줄 순서를 본다. 검사기가 헛돌지 않는지는
뒤집은 문자열로 함께 확인한다.
"""
import io
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
WF = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')

GENERATORS = ('make_sido_pages.py', 'make_indicator_pages.py', 'make_monthly_page.py',
              'make_weekly_page.py', 'refresh_cycle_data.py')
GATE = r'python3 -m pytest tools/tests/'
COMMIT = r'git commit -m "데이터 자동 갱신"'


def _line_of(text, needle):
    """주석이 아닌 줄에서 needle 이 처음 나오는 줄 번호. 없으면 None."""
    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if s.startswith('#'):
            continue
        if needle in s:
            return i
    return None


def gate_order(text):
    """(게이트가 모든 생성기 뒤인가, 게이트가 커밋 앞인가, 못 찾은 이름들)."""
    gate, commit = _line_of(text, GATE), _line_of(text, COMMIT)
    gens = {g: _line_of(text, 'python3 tools/' + g) for g in GENERATORS}
    missing = [n for n, v in [('gate', gate), ('commit', commit)] + list(gens.items()) if v is None]
    if missing:
        return False, False, missing
    return all(gate > v for v in gens.values()), gate < commit, []


def test_gate_runs_after_every_generator_and_before_commit():
    text = io.open(WF, encoding='utf-8').read()
    after_gens, before_commit, missing = gate_order(text)
    assert not missing, '워크플로에서 찾지 못한 호출: %s' % missing
    assert after_gens, 'pytest 게이트가 생성기 앞에 있다 — 정합 시험이 옛 페이지와 새 데이터를 대조해 데이터가 바뀐 날 커밋을 막는다'
    assert before_commit, 'pytest 게이트가 커밋 뒤에 있다 — 게이트가 아무것도 막지 못한다'


def test_checker_goes_red_when_order_is_reversed():
    text = io.open(WF, encoding='utf-8').read()
    gate_line = next(l for l in text.splitlines() if GATE in l and not l.strip().startswith('#'))
    first_gen = next(l for l in text.splitlines()
                     if 'python3 tools/' + GENERATORS[0] in l and not l.strip().startswith('#'))
    # 게이트 줄을 첫 생성기 앞으로 옮긴 문자열 — 2026-09-16 이전 모양
    reversed_text = text.replace(gate_line + '\n', '', 1).replace(first_gen, gate_line + '\n' + first_gen, 1)
    assert reversed_text != text, '뒤집기 치환이 안 됐다 — 이 검사 자체가 헛돈다'
    after_gens, before_commit, missing = gate_order(reversed_text)
    assert not missing and before_commit and not after_gens, '뒤집은 순서를 검사기가 잡지 못한다'
