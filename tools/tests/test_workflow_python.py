# -*- coding: utf-8 -*-
"""파이썬을 부르는 워크플로 잡은 모두 setup-python 으로 3.12 를 고정한다(전수리뷰 F overflow).

옛 발행 알림·발행 확인 워크플로(2026-11-13 삭제)가 러너 시스템 파이썬(ubuntu-24.04 의 3.12, 다음 판은 다른 판)을 그대로
썼다. 러너 판을 올리는 날(runner-trial 은 그런 잡을 돌려 보지 않는다) 판이 바뀌어 폐지된 API(datetime.utcnow 등)에서 조용히
깨질 수 있었다. 새 워크플로가 같은 실수를 하지 않게 남긴다.
"""
import glob
import io
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def _jobs():
    for f in sorted(glob.glob(os.path.join(ROOT, '.github', 'workflows', '*.yml'))):
        y = io.open(f, encoding='utf-8').read()
        jobs = y[y.index('\njobs:\n'):]
        for m in re.finditer(r'^  ([A-Za-z0-9_-]+):\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)', jobs, re.S | re.M):
            code = '\n'.join(ln for ln in m.group(2).splitlines() if not ln.strip().startswith('#'))
            yield os.path.basename(f), m.group(1), code


def test_every_python_job_pins_setup_python():
    """파이썬(python·python3)을 부르는 잡마다 actions/setup-python 이 있고 3.12 다.

    변이(실제로 확인): watchdog.yml 의 첫 setup-python 스텝을 지우면 빨강.
    픽스처: 저장소의 실제 워크플로 전부(.github/workflows/*.yml).
    """
    py, bad = [], []
    for wf, job, code in _jobs():
        if re.search(r'(^|[\s;|&(])python3?\s', code, re.M):
            py.append((wf, job))
            m = re.search(r'uses:\s*actions/setup-python@\S+\s*\n\s*with:\s*\n\s*python-version:\s*[\'"]?([\d.]+)', code)
            if not (m and m.group(1) == '3.12'):
                bad.append('%s:%s' % (wf, job))
    assert len(py) >= 5 and any(wf == 'watchdog.yml' for wf, _ in py), py   # 잡 자르기가 깨져 빈 목록으로 통과하지 않게
    assert not bad, '파이썬을 부르는데 setup-python 3.12 가 없는 잡: %s' % bad


def test_no_utcnow_in_workflows():
    """datetime.utcnow() 는 3.12 에서 폐지 예고(DeprecationWarning)다 — 워크플로 인라인 파이썬에도 쓰지 않는다.
    변이(실제로 확인): watchdog.yml 인라인 파이썬(python - << 'PY')에 datetime.datetime.utcnow() 한 줄을 넣으면 빨강. 픽스처: 저장소
    워크플로 전부."""
    hit = ['%s:%s' % (wf, job) for wf, job, code in _jobs() if 'utcnow(' in code]
    assert not hit, hit
