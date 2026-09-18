# -*- coding: utf-8 -*-
"""CI(GitHub Actions)에서는 건너뜀(skip)이 곧 실패다.

이 저장소의 시험 여럿이 환경이 없으면 조용히 건너뛴다 — node 가 없으면 서비스 워커·퀴즈 섞기·반올림 대조가,
얕은 클론이면 sw.js 버전 단조 증가가, 생성 파일이 없으면 /monthly/·사이클 검사가 skip 이다. 로컬에서는
합리적이지만 배치 게이트에서는 "방어선이 안 돌았는데 초록"이 된다. 실제로 클라우드 게이트가
"366 passed, 1 skipped" 였고 그 1건(sw 버전)은 한 번도 돈 적이 없었다(2026-09-18 리뷰).

여기서는 GITHUB_ACTIONS 가 켜져 있으면 skip 을 실패로 바꾼다. 로컬은 그대로다.
정말로 건너뛰어야 하는 회차는 AGONGMAP_ALLOW_SKIP=1 로 풀 수 있다(인프라 문제를 코드 회귀로 오인하지 않게).

무엇을 깨뜨리면 빨개지나: 이 훅을 지우면 test_ci_skips_are_failures 가 빨개진다(실제로 확인).
"""
import os

import pytest


def _ci_forbids_skip():
    return bool(os.environ.get('GITHUB_ACTIONS')) and not os.environ.get('AGONGMAP_ALLOW_SKIP')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call' and rep.skipped and _ci_forbids_skip():
        rep.outcome = 'failed'
        reason = rep.longrepr[2] if isinstance(rep.longrepr, tuple) else str(rep.longrepr)
        rep.longrepr = ('CI 에서는 건너뜀이 실패다 — 방어선이 안 돌았는데 초록이 되면 안 된다. 사유: %s '
                        '(인프라 문제면 AGONGMAP_ALLOW_SKIP=1)' % reason)
