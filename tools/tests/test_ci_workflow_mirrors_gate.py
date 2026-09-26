# -*- coding: utf-8 -*-
"""PR·main 시험 워크플로(ci-tests.yml)가 배치 커밋 잡의 게이트와 같은 조건으로 돈다(2026-09-26 데이터 감사).

pytest 를 돌리는 워크플로가 데이터 배치 하나뿐이라, 개발 컨테이너에서 초록인 변경이 배치 조건에서 빨간 것은
병합 뒤 다음 배치의 '데이터 커밋 안 함'으로 처음 드러났다(2026-09-24~26 yaml 사고, 다섯 회 정지). ci-tests.yml
이 그 게이트를 PR 에서 먼저 돌린다. 둘이 어긋나면(파이썬 판·설치 목록·생성기 순서·체크아웃 깊이) PR 은 초록인데
배치는 빨간 옛 상태로 돌아가므로, 배치 쪽을 정본으로 삼아 같은지 본다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - ci-tests.yml 의 python-version 을 '3.11' 로 → 빨강
  - ci-tests.yml 의 pip 줄에 pyyaml 을 더하면 → 빨강(배치에 없는 패키지로 시험이 초록이 된다)
  - ci-tests.yml gate 잡에서 생성기 하나를 빼거나 pip 뒤로 옮기면 → 빨강
  - ci-tests.yml 의 fetch-depth 를 지우면 → 빨강
  - permissions 에 `contents: write` 를 넣거나 `git push` 를 넣으면 → 빨강
  - pull_request 트리거를 지우면 → 빨강
픽스처 없이 두 워크플로 파일을 읽는다. 스텝 해석은 test_test_deps_are_installed 의 것을 같이 쓴다.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_test_deps_are_installed import _pip_mods, _steps, TOOL_CMD, WF_DIR  # noqa: E402

CI = os.path.join(WF_DIR, 'ci-tests.yml')
BATCH = os.path.join(WF_DIR, 'update-cloud.yml')


def _job_text(path, job):
    y = io.open(path, encoding='utf-8').read()
    i = y.index('\n  %s:' % job)
    m = re.search(r'\n  [^\s#][^:\n]*:\s*\n', y[i + 1:])
    return y[i:i + 1 + m.start()] if m else y[i:]


def _gate_sequence(path, job):
    """그 잡의 (설치 전 생성기 순서, 설치 패키지, pytest 명령, python 판, fetch-depth)."""
    txt = _job_text(path, job)
    pre, mods, pytest_cmd, pip_seen = [], set(), None, False
    for st in _steps(path):
        if st['job'] != job:
            continue
        for line in st['run']:
            if line.lstrip().startswith('#'):
                continue
            m = re.search(r'\bpip install\b(.*)', line)
            if m:
                mods |= _pip_mods(m.group(1))
                pip_seen = True
            if not pip_seen:
                pre += TOOL_CMD.findall(line)
            m = re.search(r'(python3? -m pytest [^;|&]*?)\s*(?:;|\|\||&&|then|$)', line)
            if m and pytest_cmd is None:
                pytest_cmd = ' '.join(m.group(1).split())
    ver = re.search(r"python-version:\s*'([^']+)'", txt)
    depth = re.search(r'fetch-depth:\s*(\d+)', txt)
    return pre, mods, pytest_cmd, ver and ver.group(1), depth and depth.group(1)


def test_ci_gate_runs_like_the_batch_gate():
    want = _gate_sequence(BATCH, 'commit')
    got = _gate_sequence(CI, 'gate')
    assert want[0] and want[2] and want[3] and want[4], '배치 커밋 잡을 못 읽었다: %s' % (want,)
    labels = ('설치 전 생성기(순서)', '설치 패키지', 'pytest 명령', '파이썬 판', 'fetch-depth')
    diff = ['%s: 배치 %r / CI %r' % (lab, w, g) for lab, w, g in zip(labels, want, got) if w != g]
    assert not diff, 'ci-tests.yml 이 배치 게이트와 다르다:\n  ' + '\n  '.join(diff)


def test_bare_runtime_job_installs_nothing_and_runs_every_generator():
    pre, mods, _, ver, _ = _gate_sequence(CI, 'bare-runtime')
    batch_pre = _gate_sequence(BATCH, 'commit')[0]
    assert not mods, 'bare-runtime 잡이 패키지를 깐다: %s' % mods
    assert 'split_data' in pre and set(batch_pre) <= set(pre), (pre, batch_pre)
    assert ver == _gate_sequence(BATCH, 'commit')[3]


def test_ci_workflow_can_not_write_anything():
    y = io.open(CI, encoding='utf-8').read()
    code = '\n'.join(ln for ln in y.splitlines() if not ln.lstrip().startswith('#'))
    on = re.search(r'^on:[ \t]*\n((?:[ \t]+[^\n]*\n|\n)*)', code, re.M)
    on = on.group(1) if on else ''
    assert re.search(r'^  pull_request:', on, re.M), 'PR 에서 돌지 않는다'
    assert re.search(r'^  push:[ \t]*\n[ \t]+branches:[ \t]*\[[ \t]*main[ \t]*\]', on, re.M), 'main 푸시에서 돌지 않는다'
    assert re.search(r'^permissions:\s*\n\s+contents:\s*read\s*$', code, re.M), '권한이 읽기 전용이 아니다'
    assert not re.search(r':\s*write\b', code), '쓰기 권한이 있다'
    assert not re.search(r'\bgit\s+(push|commit)\b|gh\s+(pr|issue)\s', code), '커밋·푸시·이슈 명령이 있다'
    assert code.count('persist-credentials: false') == code.count('actions/checkout@'), '체크아웃이 토큰을 남긴다'
