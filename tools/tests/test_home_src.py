# -*- coding: utf-8 -*-
"""홈 스크립트 읽기 입구(tools/home_src.py)를 고정한다 — 백로그 10 사전 작업.

2026-09-16 이동 모의: 홈 인라인 스크립트를 외부 파일로 옮기자 주간 생성기가 멈추고 시험 46건이 실패했는데,
더 나쁜 것은 조용히 꺼진 쪽이었다. 감시의 퀴즈 검토 기한 검사가 제도 문항 0개로 통과했고, '없어야 한다'류
단정 다섯 곳이 초록불로 남았다. 그래서 입구는 못 찾으면 예외를 던지고, 모든 읽는 쪽은 이 입구만 쓴다.
"""
import io
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import home_src as HS  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def test_reads_the_current_home_with_every_marker():
    s = HS.home_source()
    assert all(m in s for m in HS.MARKERS)
    assert len(s.encode('utf-8')) >= HS.MIN_BYTES


def _moved_copy(tmp_path):
    """홈을 복사하고 가장 큰 인라인 스크립트를 home-app.js 로 옮긴다(동결 창에서 할 일의 모의)."""
    s = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    ms = list(re.finditer(r'<script(?![^>]*\bsrc=)(?![^>]*ld\+json)[^>]*>(.*?)</script>', s, re.S))
    m = max(ms, key=lambda m: len(m.group(1)))
    (tmp_path / 'home-app.js').write_text(m.group(1), encoding='utf-8')
    (tmp_path / 'index.html').write_text(s[:m.start()] + '<script defer src="/home-app.js"></script>' + s[m.end():],
                                         encoding='utf-8')
    return str(tmp_path)


def test_moved_script_fails_loudly_until_external_is_set(tmp_path):
    root = _moved_copy(tmp_path)
    with pytest.raises(HS.HomeSourceError):
        HS.home_source(root=root)
    s = HS.home_source(root=root, external=('home-app.js',))
    assert all(m in s for m in HS.MARKERS), 'EXTERNAL 한 줄로 옮긴 스크립트를 따라가지 못한다'


def test_missing_file_raises(tmp_path):
    with pytest.raises(HS.HomeSourceError):
        HS.home_source(root=str(tmp_path))


def test_require_raises_when_the_target_was_not_read():
    with pytest.raises(AssertionError):
        HS.require('다른 파일 내용', 'function nextStepHTML', what='홈')
    HS.require('function nextStepHTML(){}', 'function nextStepHTML')


def test_is_home_only_matches_the_root_page():
    assert HS.is_home('index.html') and HS.is_home('.', 'index.html')
    assert not HS.is_home('zone', 'index.html') and not HS.is_home('weekly/index.html')


# ── 읽는 쪽이 입구만 쓰는가 ───────────────────────────────────────────────
DIRECT = re.compile(r"os\.path\.join\(\s*(?:ROOT|root|HERE,\s*os\.pardir|os\.path\.dirname\([^\n]*?\))\s*,\s*['\"]index\.html['\"]\s*\)")
HELPER_CALL = re.compile(r"_(?:read|src)\(\s*['\"]index\.html['\"]\s*\)")


def _offenders(src):
    out = []
    if DIRECT.search(src):
        out.append('루트 index.html 을 직접 연다')
    if HELPER_CALL.search(src) and 'HS.is_home(' not in src:
        out.append('_read/_src 로 홈을 읽는데 입구로 위임하지 않는다')
    return out


def test_scanner_catches_the_known_shapes():
    """스캐너가 죽으면 아래 시험이 조용히 통과한다 — 아는 모양을 실제로 잡는지 먼저 본다."""
    assert _offenders("h = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()")
    assert _offenders("open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.html'),")
    assert _offenders("def _read(*p):\n    return io.open(os.path.join(ROOT, *p)).read()\ns = _read('index.html')")
    assert not _offenders("p = os.path.join(ROOT, 'zone', z, 'index.html')")


def test_no_tool_or_test_reads_the_home_directly():
    bad = []
    for path in sorted(glob_py()):
        rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
        if rel in ('tools/home_src.py', 'tools/tests/test_home_src.py'):
            continue
        for why in _offenders(io.open(path, encoding='utf-8').read()):
            bad.append('%s: %s' % (rel, why))
    assert not bad, '홈 스크립트는 tools/home_src.py 로만 읽을 것:\n  ' + '\n  '.join(bad)


def glob_py():
    for dirpath, dirs, files in os.walk(os.path.join(ROOT, 'tools')):
        dirs[:] = [d for d in dirs if d not in ('cache', 'data', '__pycache__')]
        for fn in files:
            if fn.endswith('.py'):
                yield os.path.join(dirpath, fn)


def test_watchdog_fails_when_it_finds_no_policy_items():
    src = io.open(os.path.join(ROOT, 'tools', 'check_freshness.py'), encoding='utf-8').read()
    assert 'HS.home_source()' in src and '0개 찾았다' in src and 'HS.HomeSourceError' in src, (
        '감시가 제도 문항 0개·홈 스크립트 못 읽음을 실패로 올리지 않는다')
