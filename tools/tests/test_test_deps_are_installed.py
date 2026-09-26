# -*- coding: utf-8 -*-
"""배치 게이트가 까는 패키지(pytest·pillow) 밖의 서드파티 모듈을 도구·시험이 쓰지 않는지 본다.

배치 커밋 잡은 setup-python 3.12 위에 `pip install pytest pillow` 만 한다. 시험 하나가 `import yaml`
을 하고 있었는데, 러너 시스템 파이썬에는 yaml 이 있어 몰랐다가 2026-09-23 커밋 잡 파이썬을 3.12 로
고정한 뒤 ModuleNotFoundError 로 게이트가 막혀 데이터 갱신이 09-24~26 다섯 회 연속 멈췄다. 개발
컨테이너에도 시스템 yaml 이 있어 로컬 pytest 로는 재현되지 않았다 — 그래서 가져오기 목록을 직접 본다.

무엇을 깨뜨리면 빨개지나: 아무 시험·도구에 `import yaml`(또는 requests 등)을 넣으면 실패한다(실제로
확인). 워크플로의 설치 목록에서 pillow 를 빼도 PIL 을 쓰는 곳 때문에 실패한다.
픽스처 없이 저장소의 실제 파일과 update-cloud.yml 의 pip 설치 줄을 읽는다.
"""
import ast
import glob
import io
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
WF = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
# pip 패키지 이름 → import 이름
PIP_TO_MOD = {'pytest': {'pytest', '_pytest'}, 'pillow': {'PIL'}}


def _installed_mods():
    y = io.open(WF, encoding='utf-8').read()
    m = re.search(r'pip install --quiet ([^|\n]+)', y)
    assert m, '커밋 잡의 pip 설치 줄을 못 찾았다'
    mods = set()
    for pkg in m.group(1).split():
        pkg = re.split(r'[<>=]', pkg)[0].lower()
        mods |= PIP_TO_MOD.get(pkg, {pkg})
    return mods


def _local_mods():
    names = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, 'tools', '*.py'))}
    names |= {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, 'tools', 'tests', '*.py'))}
    return names


def _module_level(tree):
    """모듈을 불러올 때 바로 실행되는 문장(맨 위, 그리고 맨 위 if/try 안). 함수 안에서 필요할 때만
    가져오는 import(make_beginner_cards 의 numpy 등)는 그 함수를 부를 때만 필요하므로 뺀다."""
    todo = list(tree.body)
    while todo:
        n = todo.pop()
        yield n
        if isinstance(n, (ast.If, ast.Try)):
            todo.extend(n.body + n.orelse + getattr(n, 'finalbody', []))
            for h in getattr(n, 'handlers', []):
                todo.extend(h.body)


def _third_party_imports(path, local):
    tree = ast.parse(io.open(path, encoding='utf-8').read(), path)
    out = set()
    for node in _module_level(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        for n in names:
            top = n.split('.')[0]
            if top in sys.stdlib_module_names or top in local:
                continue
            out.add(top)
    return out


def _local_imports(path, local):
    tree = ast.parse(io.open(path, encoding='utf-8').read(), path)
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split('.')[0])
    return out & local


def _reachable(local):
    """시험 전부와 배치 워크플로가 부르는 도구에서 출발해, 로컬 import 로 닿는 파일 전부.
    사람이 가끔 돌리는 1회성 도구(원화 배경 제거의 numpy, PDF 기준표 파싱의 fitz 등)는 게이트가
    부르지 않으므로 뺀다."""
    tools = os.path.join(ROOT, 'tools')
    start = set(glob.glob(os.path.join(tools, 'tests', '*.py')))
    y = io.open(WF, encoding='utf-8').read()
    start |= {os.path.join(tools, n + '.py') for n in re.findall(r'python3? tools/(\w+)\.py', y)}
    seen, todo = set(), [p for p in start if os.path.exists(p)]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        for m in _local_imports(p, local):
            for cand in (os.path.join(tools, m + '.py'), os.path.join(tools, 'tests', m + '.py')):
                if os.path.exists(cand) and cand not in seen:
                    todo.append(cand)
    return seen


def test_tests_and_batch_tools_only_import_what_the_gate_installs():
    allowed = _installed_mods()
    local = _local_mods()
    files = _reachable(local)
    assert len(files) > 50, '검사 대상이 너무 적다 — 출발점 찾기가 낡았다(%d개)' % len(files)
    bad = []
    for f in sorted(files):
        extra = _third_party_imports(f, local) - allowed
        if extra:
            bad.append('%s: %s' % (os.path.relpath(f, ROOT), ', '.join(sorted(extra))))
    assert not bad, ('배치 게이트(pip install %s)에 없는 모듈을 가져온다 — CI 에서 ModuleNotFoundError 로 '
                     '데이터 갱신이 막힌다:\n  %s' % (' '.join(sorted(allowed)), '\n  '.join(bad)))
