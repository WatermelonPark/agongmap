# -*- coding: utf-8 -*-
"""초안 바탕화면 바로가기(2026-09-27 대표 요청) — 종류마다 이름이 고정된 아이콘 하나가 가장 최근 초안을 가리킨다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - desktop_shortcut 이 절대 경로 대신 받은 경로를 그대로 넘기면 → 대상 경로 시험
  - pytest 중에는 만들지 않는 가드를 지우면 → 시험 중 생성 금지 시험(임시 폴더를 가리키는 아이콘이 바탕화면에 생긴다)
  - 주간·지역 또는 사이클 생성기의 main 에서 바로가기 호출을 지우면 → 연결 시험
픽스처: PowerShell 을 부르지 않는 가짜 run. 실제 바탕화면은 건드리지 않는다.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402


class _Run:
    def __init__(self):
        self.calls = []

    def __call__(self, args, **kw):
        self.calls.append((args, kw))
        return type('R', (), {'returncode': 0, 'stdout': b'Desktop/x.lnk'})()


def test_passes_absolute_target_and_fixed_name(monkeypatch):
    monkeypatch.setattr(P.os, 'name', 'nt')
    run = _Run()
    got = P.desktop_shortcut(os.path.join('drafts', 'naver-2026-09-21.html'), P.SHORTCUTS['naver'], run=run)
    assert got
    args, kw = run.calls[0]
    assert args[0] == 'powershell' and 'CreateShortcut' in args[-1]
    assert kw['env']['AGM_LNK_TARGET'] == os.path.abspath(os.path.join('drafts', 'naver-2026-09-21.html'))
    assert kw['env']['AGM_LNK_NAME'] == '아공맵 블로그 초안 (주간·지역)'


def test_never_creates_during_tests(monkeypatch):
    monkeypatch.setattr(P.os, 'name', 'nt')

    called = []
    monkeypatch.setattr(P.subprocess, 'run', lambda *a, **k: called.append(a))
    assert P.desktop_shortcut('x.html', '이름') is None
    assert not called, '시험 중에 바탕화면 바로가기를 만들려 했다'


def test_both_generators_update_their_shortcut():
    # 새 초안을 쓴 경우와, 손본 초안이 있어 .new.html 로 비켜 쓴 경우 둘 다 아이콘을 맞춘다.
    assert inspect.getsource(P.main).count("desktop_shortcut(path, SHORTCUTS['naver'])") == 2
    assert "P.desktop_shortcut(path, P.SHORTCUTS['theory'])" in inspect.getsource(T.main)
