# -*- coding: utf-8 -*-
"""경보 이슈가 없거나 닫혀도 멈춤 시계가 이어지게 캐시에 표식을 남긴다(백로그 59).

`tools/post_alert.sh find`는 **열린** 경보 이슈만 본다. 이슈가 없거나 닫히면 `format_batch_report`가 읽는 표식이 비어,
'데이터 갱신이 하루 넘게 멈춤' 메일의 시계가 매 회차 처음으로 돌아간다(그래서 같은 멈춤에 메일이 늦거나 반복된다).
이제 `update-cloud` 커밋 잡은 표식을 `actions/cache`에도 남기고, 이슈 본문이 비면 그 표식으로 잇는다.
"""
import io
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
YML = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')


def _t():
    return io.open(YML, encoding='utf-8').read()


def test_workflow_restores_and_saves_the_state_cache():
    """커밋 잡이 표식 캐시를 복원·저장하고, 복원은 결과 보고 앞, 저장은 뒤에 온다.

    변이(실제로 확인): 저장 스텝을 지우면 이 시험이 빨개진다.
    픽스처: 저장소의 update-cloud.yml — 글자로 읽는다(러너에서만 도는 셸이라 여기서 실행할 수 없다).
    """
    t = _t()
    assert 'actions/cache/restore@v4' in t and 'actions/cache/save@v4' in t
    assert 'path: .stall_state' in t
    assert 'stall-state-' in t and 'restore-keys:' in t
    assert t.index('actions/cache/restore@v4') < t.index('python3 tools/format_batch_report.py') < t.index('actions/cache/save@v4')


def test_state_in_falls_back_to_the_cache_when_the_issue_is_missing():
    """이슈 본문이 비면 캐시 표식으로 `_state_in.txt`를 채운다 — 형식기 호출 앞이어야 한다.

    변이(실제로 확인): 폴백 줄을 지우면 이 시험이 빨개진다.
    """
    t = _t()
    fb = 'cp .stall_state/state.txt _state_in.txt'
    assert fb in t, '이슈가 없을 때 캐시 표식으로 잇는 줄이 없다'
    assert t.index(fb) < t.index('python3 tools/format_batch_report.py'), '캐시 폴백이 형식기 앞이어야 한다'


def test_state_is_written_to_the_cache_after_the_report():
    """형식기가 표식을 바꿨을 때(_state_out.txt) 캐시에도 같은 표식을 남긴다.

    변이(실제로 확인): `cp _state_out.txt ...` 줄을 지우면 이 시험이 빨개진다.
    """
    t = _t()
    w = 'cp _state_out.txt .stall_state/state.txt'
    assert w in t
    assert t.index('python3 tools/format_batch_report.py') < t.index(w) < t.index('actions/cache/save@v4')


def test_an_empty_cache_state_does_not_wipe_a_restored_marker():
    """표식이 안 바뀐 회차에 빈 파일로 덮지 않는다 — 복원해 둔 표식을 그대로 둔다.

    변이(실제로 확인): `[ -f .stall_state/state.txt ] || : > …` 줄을 `: > .stall_state/state.txt`로 되돌리면 빨개진다.
    """
    t = _t()
    assert '[ -f .stall_state/state.txt ] || : > .stall_state/state.txt' in t
