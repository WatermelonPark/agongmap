# -*- coding: utf-8 -*-
"""워크플로가 부르는 도구·시험이 **그 자리에서 깔려 있는** 패키지만 가져오는지 본다.

배치 커밋 잡은 setup-python 3.12 위에 `pip install pytest pillow` 만 한다. 시험 하나가 `import yaml`
을 하고 있었는데, 러너 시스템 파이썬에는 yaml 이 있어 몰랐다가 2026-09-23 커밋 잡 파이썬을 3.12 로
고정한 뒤 ModuleNotFoundError 로 게이트가 막혀 데이터 갱신이 09-24~26 다섯 회 연속 멈췄다. 개발
컨테이너에도 시스템 yaml 이 있어 로컬 pytest 로는 재현되지 않았다 — 그래서 가져오기 목록을 직접 본다.

⚠️ 허용 목록은 **단계마다 다르다**(2026-09-26 데이터 감사). 처음 판은 커밋 잡의 pip 줄 하나로 모든 파일을
재서, pip 전에 도는 것들이 PIL·pytest 를 가져와도 초록이었다. 실제로는 이것들이 맨 3.12 위에서 돈다:
  - fetch 잡(update_adv_data·split_data) — pip 가 아예 없다. split_data 가 죽으면 세 러너 모두 'crash' 라 재시도도 없다.
  - 커밋 잡에서 pip 줄 **앞**의 생성기 다섯 — 죽으면 '❌ … 커밋 안 함'.
  - `if: always()` 처럼 앞 스텝이 실패해도 도는 스텝(결과 보고의 format_batch_report) — pip 전에 죽은 회차에도 돈다.
  - watchdog.yml(check_freshness 와 그것이 가져오는 전부)·publish-check.yml(close_published_issues) — pip 가 없다.
그래서 워크플로 파일을 잡·스텝·줄 순서대로 읽어 명령마다 그 시점까지 깔린 패키지를 허용 목록으로 쓴다.
pytest·pillow 는 시험(pytest 줄 시점)과 커밋 잡의 pip 줄 **뒤** 명령에만 허용된다. 한 파일이 여러 곳에서
닿으면 가장 엄한 곳을 따른다. 워크플로 안에 인라인으로 적은 파이썬(`python - <<'PY'`)도 같이 본다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - 아무 시험·도구에 `import yaml`(또는 requests 등) → 빨강
  - make_monthly_page 맨 위에 `from PIL import Image` → 빨강(생성기는 pip 전)
  - split_data 맨 위에 `import pytest` → 빨강(fetch 잡에는 pip 가 없다)
  - quiz_review 맨 위에 `from PIL import ImageFont` → 빨강(check_freshness 가 가져오고, 감시에는 pip 가 없다)
  - make_weekly_page 맨 위에 `import make_weekly_share`(모듈 맨 위에서 PIL 을 가져온다) → 빨강(간접 도달)
  - format_batch_report 맨 위에 `from PIL import Image` → 빨강(`if: always()` 스텝)
  - 워크플로 설치 목록에서 pillow 를 빼면 시험이 PIL 을 쓰는 곳 때문에 빨강
  - _entries 가 `if: always()` 스텝도 pip 뒤로 치게 바꾸면 → 해석기 확인 시험이 빨강
  (대조군: pip 뒤에 도는 batch_notes 맨 위에 PIL 을 넣으면 초록이다 — 그 자리에는 깔려 있다.)
픽스처 없이 저장소의 실제 파일과 .github/workflows/*.yml 을 읽는다. 스텝 해석이 낡으면 조용히 통과하지 않게,
pip 전에 돌아야 하는 명령을 더 단순한 텍스트 잘라 읽기로 한 번 더 뽑아 서로 맞춰 본다.
"""
import ast
import glob
import io
import os
import re
import sys
import textwrap

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
TOOLS = os.path.join(ROOT, 'tools')
WF_DIR = os.path.join(ROOT, '.github', 'workflows')
# pip 패키지 이름 → import 이름
PIP_TO_MOD = {'pytest': {'pytest', '_pytest'}, 'pillow': {'PIL'}}
# 앞 스텝이 실패해도 도는 스텝 — pip 줄이 안 돌았을 수 있으므로 맨 환경으로 본다
RUNS_AFTER_FAILURE = re.compile(r'always\(\)|failure\(\)|cancelled\(\)')
TOOL_CMD = re.compile(r'\bpython3?(?:\s+-[A-Za-z]+)*\s+tools/(\w+)\.py')
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def _pip_mods(rest):
    mods = set()
    for tok in rest.split():
        if tok in ('||', '&&', ';', '|') or tok.startswith('#'):
            break
        if tok.startswith('-'):
            continue
        pkg = re.split(r'[<>=\[]', tok)[0].lower()
        mods |= PIP_TO_MOD.get(pkg, {pkg})
    return mods


def _steps(path):
    """[{job, if, run: [줄]}] — 이 저장소 워크플로의 모양(2칸 들여쓰기, 스텝은 6칸 '- ')만 읽는다."""
    lines = io.open(path, encoding='utf-8').read().splitlines()
    out, job, cur, in_jobs, i = [], None, None, False, 0
    while i < len(lines):
        ln = lines[i]
        if re.match(r'^jobs:\s*$', ln):
            in_jobs = True
        elif in_jobs and re.match(r'^  [^\s#][^:]*:\s*$', ln):
            job, cur = ln.strip()[:-1], None
        elif in_jobs and ln.startswith('      - '):
            cur = {'job': job, 'if': '', 'run': []}
            out.append(cur)
            ln = '        ' + ln[8:]            # '- if: …'·'- run: …' 처럼 첫 키가 대시 줄에 붙은 경우
        if cur is not None:
            m = re.match(r'^        if:\s*(.*)$', ln)
            if m:
                cur['if'] = m.group(1)
            m = re.match(r'^        run:\s*(.*)$', ln)
            if m:
                v = m.group(1).strip()
                if v[:1] in ('|', '>'):
                    body = []
                    while i + 1 < len(lines) and (not lines[i + 1].strip()
                                                  or len(lines[i + 1]) - len(lines[i + 1].lstrip()) > 8):
                        i += 1
                        body.append(lines[i])
                    cur['run'] = textwrap.dedent('\n'.join(body)).splitlines()
                else:
                    cur['run'] = [v]
        i += 1
    return out


def _entries():
    """워크플로의 파이썬 진입점 → 그 시점에 깔려 있는 모듈.

    돌려주는 것: (도구 {경로: 허용}, 시험 허용 또는 None, 인라인 코드 [(이름, 코드, 허용)])
    """
    tools, tests, inline = {}, None, []

    def put(p, allowed):
        tools[p] = tools[p] & allowed if p in tools else set(allowed)
    for wf in sorted(glob.glob(os.path.join(WF_DIR, '*.yml'))):
        installed = {}
        for st in _steps(wf):
            inst = installed.setdefault(st['job'], set())
            avail = set() if RUNS_AFTER_FAILURE.search(st['if']) else set(inst)
            body, j = st['run'], 0
            while j < len(body):
                line = body[j]
                if line.lstrip().startswith('#'):
                    j += 1
                    continue
                hd = HEREDOC.search(line)
                if hd:                            # heredoc 본문은 셸 명령이 아니다(파이썬 코드거나 글)
                    k = j + 1
                    while k < len(body) and body[k].strip() != hd.group(1):
                        k += 1
                    if re.search(r'\bpython3?\s+-\s*<<', line):
                        inline.append(('%s:%s' % (os.path.basename(wf), st['job']),
                                       textwrap.dedent('\n'.join(body[j + 1:k])), set(avail)))
                    j = k + 1
                    continue
                m = re.search(r'\bpip install\b(.*)', line)
                if m:
                    mods = _pip_mods(m.group(1))
                    inst |= mods
                    avail |= mods
                for name in TOOL_CMD.findall(line):
                    put(os.path.normpath(os.path.join(TOOLS, name + '.py')), avail)
                if re.search(r'\bpython3? -m pytest\b', line):
                    tests = set(avail) if tests is None else tests & avail
                j += 1
    return tools, tests, inline


def _local_mods():
    names = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(TOOLS, '*.py'))}
    names |= {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(TOOLS, 'tests', '*.py'))}
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


def _third_party_imports(tree, local):
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


def _parse(path):
    return ast.parse(io.open(path, encoding='utf-8').read(), path)


def _local_imports(path, local):
    out = set()
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            out |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.add(node.module.split('.')[0])
    return out & local


def _reach(starts, local):
    """{출발 파일: 허용} → {닿는 파일: 허용(여러 곳에서 닿으면 교집합)}. 사람이 가끔 돌리는 1회성 도구
    (원화 배경 제거의 numpy, PDF 기준표 파싱의 fitz 등)는 어디서도 안 닿으므로 빠진다."""
    allowed = {}
    for s, al in starts.items():
        seen, todo = set(), [s]
        while todo:
            p = todo.pop()
            if p in seen or not os.path.exists(p):
                continue
            seen.add(p)
            allowed[p] = allowed[p] & al if p in allowed else set(al)
            for m in _local_imports(p, local):
                for cand in (os.path.join(TOOLS, m + '.py'), os.path.join(TOOLS, 'tests', m + '.py')):
                    cand = os.path.normpath(cand)
                    if os.path.exists(cand) and cand not in seen:
                        todo.append(cand)
    return allowed


def _cmd_tools(text):
    return {os.path.normpath(os.path.join(TOOLS, n + '.py')) for ln in text.splitlines()
            if not ln.lstrip().startswith('#') for n in TOOL_CMD.findall(ln)}


def test_step_parser_sees_every_bare_runtime_command():
    """해석기 자체 확인 — pip 전에 도는 명령을 텍스트 잘라 읽기로 따로 뽑아, 해석기가 그것들을 전부
    '깔린 것 없음'으로 분류하는지 본다. 해석기가 스텝을 놓치면 여기서 빨개진다."""
    tools, tests, _ = _entries()
    y = io.open(os.path.join(WF_DIR, 'update-cloud.yml'), encoding='utf-8').read()
    fetch = y[y.index('\n  fetch:'):y.index('\n  commit:')]
    commit = y[y.index('\n  commit:'):]
    pre_pip = commit[:commit.index('pip install')]
    must_bare = _cmd_tools(fetch) | _cmd_tools(pre_pip)
    # 앞 스텝이 실패해도 도는 스텝(결과 보고 등)은 pip 뒤에 있어도 맨 환경일 수 있다
    for chunk in commit.split('\n      - ')[1:]:
        if RUNS_AFTER_FAILURE.search(chunk.split('run:')[0]):
            must_bare |= _cmd_tools(chunk)
    for wf in ('watchdog.yml', 'publish-check.yml'):
        must_bare |= _cmd_tools(io.open(os.path.join(WF_DIR, wf), encoding='utf-8').read())
    assert len(must_bare) >= 5, '맨 환경 명령을 거의 못 찾았다 — 워크플로 모양이 바뀌었다: %s' % sorted(must_bare)
    wrong = sorted(os.path.basename(p) for p in must_bare if tools.get(p) != set())
    assert not wrong, 'pip 전에 도는 명령을 설치 뒤로 분류했다(해석기 고장): %s' % wrong
    assert tests and {'pytest', 'PIL'} <= tests, '시험 시점의 설치 목록을 못 읽었다: %s' % tests


def test_tests_and_batch_tools_only_import_what_their_step_installs():
    local = _local_mods()
    tools, tests, inline = _entries()
    starts = dict(tools)
    for p in glob.glob(os.path.join(TOOLS, 'tests', '*.py')):
        p = os.path.normpath(p)
        starts[p] = starts[p] & tests if p in starts else set(tests)
    allowed = _reach(starts, local)
    assert len(allowed) > 50, '검사 대상이 너무 적다 — 출발점 찾기가 낡았다(%d개)' % len(allowed)
    bad = []
    for f in sorted(allowed):
        extra = _third_party_imports(_parse(f), local) - allowed[f]
        if extra:
            bad.append('%s: %s (그 자리에 깔린 것: %s)' % (os.path.relpath(f, ROOT), ', '.join(sorted(extra)),
                                                     ', '.join(sorted(allowed[f])) or '표준 라이브러리뿐'))
    for name, code, al in inline:
        extra = _third_party_imports(ast.parse(code), local) - al
        if extra:
            bad.append('%s 인라인 파이썬: %s' % (name, ', '.join(sorted(extra))))
    assert not bad, ('워크플로의 그 단계에 깔려 있지 않은 모듈을 가져온다 — CI 에서 ModuleNotFoundError 로 '
                     '데이터 갱신·감시가 멈춘다:\n  %s' % '\n  '.join(bad))
