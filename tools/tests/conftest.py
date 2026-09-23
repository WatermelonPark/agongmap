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
    # setup 단계도 본다 — 픽스처 안의 pytest.skip(예: /monthly/ 파일이 없으면 건너뛰는 픽스처)은
    # setup 에서 나므로 call 만 보면 CI 에서도 "3 passed, 8 skipped" 로 초록이었다(2026-09-23 점검).
    if rep.when in ('setup', 'call') and rep.skipped and _ci_forbids_skip():
        rep.outcome = 'failed'
        reason = rep.longrepr[2] if isinstance(rep.longrepr, tuple) else str(rep.longrepr)
        rep.longrepr = ('CI 에서는 건너뜀이 실패다 — 방어선이 안 돌았는데 초록이 되면 안 된다. 사유: %s '
                        '(인프라 문제면 AGONGMAP_ALLOW_SKIP=1)' % reason)


# ── 시험이 저장소 파일을 고치면 전체 실행을 실패로 만든다 ─────────────────────────────
# test_tools_actually_run 이 도구 5개·파일 5개의 mtime 만 봐서, 다른 시험에서 split_data.main()·
# make_sido_pages.main() 을 부르면 zone/*·data-*.json 25개가 넘는 파일을 다시 써도 전체가 초록이었다
# (2026-09-23 시험 점검). 배치 게이트는 생성기 **뒤**에 돌므로, 시험이 파일을 고치면 그 결과가 그대로
# 커밋된다. 실행 전후 git status 에 오른 파일의 내용 해시를 비교한다 — 원래 수정 중이던 파일은
# 내용이 그대로면 통과다.
# 무엇을 깨뜨리면 빨개지나: 아무 시험에서 저장소 파일(예: about/index.html)에 한 줄을 덧붙이면
# 실행 끝에 exit 1 과 파일 목록이 나온다(실제로 확인).
import hashlib  # noqa: E402
import subprocess  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_BEFORE = None


def _dirty():
    try:
        out = subprocess.run(['git', 'status', '--porcelain', '-uall', '-z'], cwd=_ROOT,
                             capture_output=True, timeout=60).stdout.decode('utf-8', 'replace')
    except Exception:
        return None
    snap = {}
    for ent in out.split('\0'):
        if len(ent) < 4:
            continue
        p = ent[3:]
        fp = os.path.join(_ROOT, p)
        try:
            snap[p] = hashlib.sha1(open(fp, 'rb').read()).hexdigest() if os.path.isfile(fp) else 'gone'
        except OSError:
            snap[p] = 'unreadable'
    return snap


def pytest_sessionstart(session):
    global _BEFORE
    _BEFORE = _dirty()


def pytest_sessionfinish(session, exitstatus):
    if _BEFORE is None:
        return
    after = _dirty()
    if after is None:
        return
    changed = sorted(p for p in set(after) | set(_BEFORE) if after.get(p) != _BEFORE.get(p))
    if changed:
        tr = session.config.pluginmanager.get_plugin('terminalreporter')
        msg = ('시험 실행이 저장소 파일을 바꿨다(%d개) — 시험은 tmp_path 에만 써야 한다: %s'
               % (len(changed), ', '.join(changed[:10])))
        if tr:
            tr.write_line(msg, red=True)
        session.exitstatus = 1
