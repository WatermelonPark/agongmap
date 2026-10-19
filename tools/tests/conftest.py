# -*- coding: utf-8 -*-
"""CI(GitHub Actions)에서는 건너뜀(skip)이 곧 실패다.

이 저장소의 시험 여럿이 환경이 없으면 조용히 건너뛴다 — node 가 없으면 서비스 워커·퀴즈 섞기·반올림 대조가,
얕은 클론이면 sw.js 버전 단조 증가가, 생성 파일이 없으면 /monthly/·사이클 검사가 skip 이다. 로컬에서는
합리적이지만 배치 게이트에서는 "방어선이 안 돌았는데 초록"이 된다. 실제로 클라우드 게이트가
"366 passed, 1 skipped" 였고 그 1건(sw 버전)은 한 번도 돈 적이 없었다(2026-09-18 리뷰).

여기서는 GITHUB_ACTIONS 가 켜져 있으면 skip 을 실패로 바꾼다. 로컬은 그대로다.
정말로 건너뛰어야 하는 회차는 AGONGMAP_ALLOW_SKIP=1 로 풀 수 있다(인프라 문제를 코드 회귀로 오인하지 않게).

무엇을 깨뜨리면 빨개지나: 이 훅을 지우면 test_ci_skips_are_failures 가 빨개진다(실제로 확인).

모듈 수준 건너뜀(모듈 맨 위 `pytest.importorskip(...)`, `pytest.skip(..., allow_module_level=True)`, unittest.SkipTest)은
시험 실행(runtest)이 아니라 수집 단계의 CollectReport 로 끝나 위 훅을 지나지 않는다 — 파일 전체가 'N skipped' 로
초록인 채 빠졌다(전수리뷰 #91). pytest_collectreport 가 그것을 모아 실행 끝(sessionfinish)에 종료 코드를 1로 바꾼다.
수집 오류로 바꾸지 않는 이유: 수집 오류는 나머지 시험 전체를 중단시켜 다른 결과까지 가린다.
무엇을 깨뜨리면 빨개지나: pytest_collectreport 를 지우면 test_ci_module_skips_are_failures 가 빨개진다(확인).
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


_COLLECT_SKIPS = []


def pytest_collectreport(report):
    if report.skipped and _ci_forbids_skip():
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        _COLLECT_SKIPS.append('%s — %s' % (report.nodeid or '?', reason))


def _fail_collect_skips(session):
    if not _COLLECT_SKIPS:
        return
    tr = session.config.pluginmanager.get_plugin('terminalreporter')
    msg = ('CI 에서는 건너뜀이 실패다 — 모듈 수준 건너뜀으로 파일 전체가 안 돌았다(%d개): %s '
           '(인프라 문제면 AGONGMAP_ALLOW_SKIP=1)' % (len(_COLLECT_SKIPS), '; '.join(_COLLECT_SKIPS[:10])))
    if tr:
        tr.write_line(msg, red=True)
    else:
        print(msg)
    session.exitstatus = 1


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

# git status 에 오르지 않는(.gitignore) 배치 상태 파일. 배치 게이트는 이 파일들이 있는 작업 트리에서 돌고, 커밋 잡이
# 게이트 **뒤**에 읽는다(.fetch_failed → ℹ️ 줄, .stats_changed → 변경 내역, .supply_stalled → 알림). 시험이 저장소 루트의
# 것을 고쳐 쓰면 그 회차 보고가 바뀌는데, -uall 은 무시 파일을 보여 주지 않아 아래 감시에 걸리지 않았다(2026-10 리뷰 E3).
# --ignored 로 통째로 보면 __pycache__·캐시가 잡음이 되므로 이름으로 둔다 — 새 상태 파일을 .gitignore 에 올리면 여기에도
# 올린다. 디렉터리(.batch.lock/)는 들어 있는 이름 목록을 본다.
# 무엇을 깨뜨리면 빨개지나: 이 목록을 비우면 test_repo_write_guard 가 빨개진다(실제로 확인).
_STATE_FILES = ('.fetch_failed', '.stats_changed', '.supply_stalled', '.indexnow_key', '.batch.lock',
                'tools/data/.reseed_tries.json', 'tools/data/.reseed.lock', 'tools/serp-history.jsonl')

# 통째로 보는 무시 폴더. drafts/ 는 블로그 초안·썸네일을 두는 로컬 전용 자리라 덮이면 되돌릴 데가 없다. 시험이 draft_weekly·
# draft_zone 을 부르면 --no-shot 이어도 썸네일을 그 자리에 그렸고(합성 픽스처의 '서울 +0.30%' 그림이 실제 조사일 이름으로 남아
# 로컬 세션의 그 주 초안 대표 이미지가 됐다), 위 감시는 무시 폴더를 못 봐 초록이었다(전수리뷰 T1-5·T3-11·BL1-12). 이름만 보면
# 덮어쓰기를 못 잡으므로 파일마다 (크기, mtime_ns)를 본다. 쓰기 자리 자체는 아래 _drafts_out_of_repo 가 임시 폴더로 돌린다.
# 무엇을 깨뜨리면 빨개지나: 이 목록에서 'drafts' 를 빼면 test_repo_write_guard 의 drafts 시험이 빨개진다(실제로 확인).
_WATCH_DIRS = ('drafts',)


def _tree_snap(snap, p):
    fp = os.path.join(_ROOT, p)
    if not os.path.isdir(fp):
        snap[p] = 'absent'
        return
    snap[p] = 'dir'
    for base, dirs, files in os.walk(fp):
        dirs.sort()
        for f in sorted(files):
            q = os.path.join(base, f)
            key = '%s/%s' % (p, os.path.relpath(q, fp).replace(os.sep, '/'))
            try:
                st = os.stat(q)
                snap[key] = '%d|%d' % (st.st_size, st.st_mtime_ns)
            except OSError:
                snap[key] = 'unreadable'


def _state_snap():
    snap = {}
    for p in _STATE_FILES:
        fp = os.path.join(_ROOT, p)
        try:
            if os.path.isdir(fp):
                snap[p] = 'dir:' + '/'.join(sorted(os.listdir(fp)))
            elif os.path.isfile(fp):
                snap[p] = hashlib.sha1(open(fp, 'rb').read()).hexdigest()
            else:
                snap[p] = 'absent'
        except OSError:
            snap[p] = 'unreadable'
    for p in _WATCH_DIRS:
        _tree_snap(snap, p)
    return snap


def _dirty():
    snap = _state_snap()     # git 을 못 불러도 상태 파일은 본다
    try:
        out = subprocess.run(['git', 'status', '--porcelain', '-uall', '-z'], cwd=_ROOT,
                             capture_output=True, timeout=60).stdout.decode('utf-8', 'replace')
    except Exception:
        return snap
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


# ── 초안 도구의 쓰기 자리를 시험마다 임시 폴더로 ─────────────────────────────────────────
# 블로그 초안 도구는 쓰기 자리를 모듈 상수로 둔다(make_naver_post.OUT·STATE, make_theory_post.OUT — import 때 P.OUT 을 베낀
# 사본이라 따로 돌린다 —, make_city_post.OUT, 모두 <저장소>/drafts). 시험마다 돌리면 하나를 빠뜨린 시험이 저장소에 쓴다(위 감시가
# 그것을 잡는다). 그래서 모든 시험에서 세 도구를 올려 새 임시 폴더로 돌린다 — 함수 안에서 도구를 import 하는 시험(test_home_entry
# 의 _all_drafts)을 혼자 돌려도 빠지지 않게 sys.modules 에 없으면 여기서 올린다. 시험이 제 tmp_path 로 다시 돌리면 그쪽이 이긴다
# (이 픽스처가 먼저 돈다). 폴더는 만들어 두기만 하고 그 안에 아무것도 쓰지 않는다.
# 무엇을 깨뜨리면 빨개지나: 이 픽스처를 지우면 test_repo_write_guard 의 쓰기 자리 시험이, 그리고 주간·지역 초안을 굽는 시험 여럿이
# 저장소 drafts/ 에 썸네일을 써 위 감시가 실행 전체를 빨갛게 만든다(실제로 확인).
_DRAFT_TOOLS = (('make_naver_post', ('OUT', 'STATE')), ('make_theory_post', ('OUT',)), ('make_city_post', ('OUT',)))


@pytest.fixture(autouse=True)
def _drafts_out_of_repo(monkeypatch, tmp_path_factory):
    import importlib
    import sys
    tools = os.path.join(_ROOT, 'tools')
    if tools not in sys.path:
        sys.path.insert(0, tools)
    d = None
    for name, attrs in _DRAFT_TOOLS:
        try:
            m = sys.modules.get(name) or importlib.import_module(name)
        except Exception:      # 못 올리는 도구는 그 도구를 쓰는 시험이 스스로 실패한다(임시 저장소 사본에는 도구가 없다)
            continue
        if d is None:
            d = str(tmp_path_factory.mktemp('drafts'))
        for a in attrs:
            old = getattr(m, a, None)
            if old is None:
                continue
            # STATE 같은 파일 자리는 이름을 지키고 폴더만 바꾼다
            monkeypatch.setattr(m, a, d if a == 'OUT' else os.path.join(d, os.path.basename(old)))


# ── 1·2편 고리① 전제가 서는 /cycle/ D ───────────────────────────────────────────────────
# 이론 1·2편을 렌더링해 다른 것(이미지 싣기·시도 수 문장)을 보는 시험이 저장소 D 의 고리① 칸에 기대면, 손으로 돌리는 사이클 재산정이
# 그 전제를 뒤집는 날(공급이 적은 분기의 전세 상승률 ≤ 많은 분기) link1_values 의 SystemExit 로 게이트가 빨개진다 — 대표 결정
# 2026-10-18 D1 은 그때 초안 생성만 멈추고 게이트는 막지 않는다. 이 픽스처는 저장소 D 사본에서 고리① 칸만 2026-09 /cycle/ 정본
# 값(적음 2.66 · 보통 1.74 · 많음 −0.36, 본문 칸 2.7 · −0.4)으로 두고 make_naver_post.cycle_d 를 그 사본으로 바꾼다.
# 무엇을 깨뜨리면 빨개지나: 이 픽스처를 쓰는 시험에서 픽스처를 빼고 저장소 D 의 고리① 을 뒤집으면(rise [0.5, 1.0, 1.2]) 그 시험들이
# SystemExit 로 빨개진다(실제로 확인).
@pytest.fixture
def link1_holds(monkeypatch):
    import copy
    import sys
    tools = os.path.join(_ROOT, 'tools')
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import make_naver_post as P
    D = P.cycle_d()
    D['link1_new'] = dict(D.get('link1_new') or {}, jeonse_rise=[2.66, 1.74, -0.36])
    D['prose'] = dict(D.get('prose') or {}, l1_lo='2.7', l1_hi='−0.4')
    monkeypatch.setattr(P, 'cycle_d', lambda: copy.deepcopy(D))
    return D


def pytest_sessionfinish(session, exitstatus):
    _fail_collect_skips(session)
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
