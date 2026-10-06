# -*- coding: utf-8 -*-
"""모든 워크플로가 같은 고정 판 러너에서 돌고, 러너 판 시험(runner-trial.yml)만 다음 판을 쓴다(2026-10-06 대표 결정).

왜: GitHub 이 ubuntu-latest 를 2026-10-19 부터 Ubuntu 26 으로 옮긴다. 'latest' 가 섞여 있으면 판이 바뀌는 날
배치·감시가 예고 없이 다른 OS 에서 돈다. 고정 판은 ci-tests.yml 의 기본값(`inputs.runner || '<판>'`) 하나를 정본으로 읽는다.

변이(각각 실제로 확인):
  · 아무 워크플로의 runs-on 하나를 ubuntu-latest 로 되돌리면 → 고정 시험 빨강.
  · runner-trial.yml 의 runner 를 고정 판과 같게 하면 → 시험 판 단정 빨강(시험이 아무것도 시험하지 않는다).
  · runner-trial.yml 이 ci-tests.yml 대신 다른 것을 부르면 → 빨강.
픽스처: 저장소의 실제 워크플로 파일들.
"""
import glob
import io
import os
import re

WF = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.github', 'workflows'))


def _read(name):
    return io.open(os.path.join(WF, name), encoding='utf-8').read()


def _pinned():
    m = re.search(r"runs-on:\s*\$\{\{\s*inputs\.runner\s*\|\|\s*'([^']+)'\s*\}\}", _read('ci-tests.yml'))
    assert m, 'ci-tests.yml 에서 고정 판 기본값을 못 읽었다'
    return m.group(1)


def test_every_workflow_runs_on_the_pinned_runner():
    pin = _pinned()
    assert re.fullmatch(r'ubuntu-\d\d\.04', pin), pin
    bad, seen = [], 0
    for p in sorted(glob.glob(os.path.join(WF, '*.yml'))):
        for v in re.findall(r'^\s*runs-on:\s*(.+?)\s*$', io.open(p, encoding='utf-8').read(), re.M):
            seen += 1
            if v != pin and 'inputs.runner' not in v:
                bad.append('%s: %s' % (os.path.basename(p), v))
    assert seen >= 10, '러너 줄을 %d개밖에 못 읽었다 — 파서 확인' % seen
    assert not bad, '고정 판(%s)이 아닌 러너: %s' % (pin, bad)


def test_trial_calls_ci_tests_on_the_next_runner():
    txt = _read('runner-trial.yml')
    assert re.search(r'uses:\s*\./\.github/workflows/ci-tests\.yml', txt), 'runner-trial 이 ci-tests.yml 을 부르지 않는다'
    m = re.search(r'runner:\s*(ubuntu-\d\d\.04)', txt)
    assert m, 'runner-trial 에서 시험 판을 못 읽었다'
    assert m.group(1) > _pinned(), '시험 판(%s)이 고정 판(%s)보다 새 판이 아니다' % (m.group(1), _pinned())
