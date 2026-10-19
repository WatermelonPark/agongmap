# -*- coding: utf-8 -*-
"""배치 커밋 잡의 푸시 루프와 체크아웃 출발점(전수리뷰 F-3).

concurrency 로 대기(pending)한 update-cloud 런은 github.sha 가 런이 생길 때의 main 이라, 체크아웃이 그 값을 받으면 앞 런의
데이터 커밋 전 data.js 위에서 수집·커밋한다. data.js 는 ADV·STATS 가 각각 한 줄이라 두 커밋 내용이 조금만 달라도
pull --rebase 가 같은 줄에서 충돌하고(3회 모두), 실패 문구는 '사람이 같은 줄을 고친 것'으로 오안내했다. 내용이 같으면
rebase 가 패치를 버려 커밋한 것이 없는데도 '✅ 커밋·푸시'로 보고했다.
"""
import io
import os
import re
import subprocess

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
WF = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')


def _job(y, name):
    m = re.search(r'^  %s:\n(.*?)(?=^  [a-z][\w-]*:\n|\Z)' % re.escape(name), y, re.S | re.M)
    assert m, '%s 잡을 찾지 못했다' % name
    return m.group(1)


def test_fetch_and_commit_checkout_latest_main():
    """fetch·commit 두 잡의 체크아웃이 `ref: main` 이다 — 대기한 런도 잡이 시작할 때의 main 끝(앞 런 데이터 포함)에서
    출발한다. 한쪽만 바꾸면 여전히 옛 기준 위 커밋이라 충돌한다.

    변이(실제로 확인): 둘 중 어느 잡의 `ref: main` 줄을 지워도 빨강.
    픽스처: 저장소의 update-cloud.yml 원문(2026-10-05 대기 런 37302379328 이 옛 main fc47a4e7 에서 출발한 상태를 막는 설정).
    """
    y = io.open(WF, encoding='utf-8').read()
    for name in ('fetch', 'commit'):
        blk = _job(y, name)
        co = re.search(r'- uses: actions/checkout@\S+\n(?:\s+with:\n)?((?:\s{10,}.*\n)*)', blk)
        assert co, '%s 잡에 체크아웃이 없다' % name
        assert re.search(r'^\s+ref:\s*main\b', co.group(1), re.M), \
            '%s 잡 체크아웃이 런 생성 시점의 sha 를 받는다 — 대기 런이 옛 data.js 에서 출발한다' % name


def _push_loop():
    y = io.open(WF, encoding='utf-8').read()
    a = y.index('          pushed=0\n')
    b = y.index('          if [ "$pushed" -eq 0 ]; then', a)
    c = y.index('\n          fi\n', b) + len('\n          fi\n')
    return '\n'.join(ln[10:] for ln in y[a:c].splitlines())


def _git(cwd, *args):
    subprocess.run(['git', '-c', 'init.defaultBranch=main', *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _setup(tmp_path, a_line, b_line, b_file='data.js'):
    """원격 main 에 data.js 한 줄. 앞 런(A)이 그 줄을 a_line 으로 바꿔 먼저 푸시하고, 대기 런(B)은 옛 main 에서
    b_file 을 b_line 으로 바꿔 커밋한 상태를 만든다."""
    env_user = ('-c', 'user.name=stats-bot', '-c', 'user.email=bot@example.invalid')
    origin = tmp_path / 'origin.git'
    _git(tmp_path, 'init', '-q', '--bare', str(origin))
    seed = tmp_path / 'seed'
    _git(tmp_path, 'clone', '-q', str(origin), str(seed))
    (seed / 'data.js').write_text('const ADV={"a":1};\n', encoding='utf-8')
    (seed / 'other.txt').write_text('x\n', encoding='utf-8')
    _git(seed, 'add', 'data.js', 'other.txt')
    _git(seed, *env_user, 'commit', '-q', '-m', 'seed')
    _git(seed, 'push', '-q', 'origin', 'HEAD:main')
    b = tmp_path / 'b'
    _git(tmp_path, 'clone', '-q', '-b', 'main', str(origin), str(b))
    a = tmp_path / 'a'
    _git(tmp_path, 'clone', '-q', '-b', 'main', str(origin), str(a))
    (a / 'data.js').write_text(a_line, encoding='utf-8')
    _git(a, 'add', 'data.js')
    _git(a, *env_user, 'commit', '-q', '-m', '데이터 자동 갱신')
    _git(a, 'push', '-q')
    (b / b_file).write_text(b_line, encoding='utf-8')
    _git(b, 'add', b_file)
    _git(b, *env_user, 'commit', '-q', '-m', '데이터 자동 갱신')
    for k, v in (('user.name', 'stats-bot'), ('user.email', 'bot@example.invalid')):
        _git(b, 'config', k, v)
    return b


def _run_loop(b, tmp_path):
    fake = tmp_path / 'bin'
    fake.mkdir()
    (fake / 'python3').write_text('#!/bin/sh\necho "✅ IndexNow 시험"\n', encoding='utf-8')
    os.chmod(fake / 'python3', 0o755)
    (fake / 'sleep').write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    os.chmod(fake / 'sleep', 0o755)
    rep = tmp_path / 'rep.txt'
    script = 'set -e\nR=%s\nNF=1\nrep() { echo "$1" >> "$R"; }\n%s\n' % (str(rep), _push_loop())
    env = dict(os.environ, PATH='%s:%s' % (fake, os.environ.get('PATH', '')), GIT_TERMINAL_PROMPT='0')
    p = subprocess.run(['bash', '-c', script], cwd=b, env=env, capture_output=True, text=True)
    return p.returncode, (rep.read_text(encoding='utf-8') if rep.exists() else '')


def test_push_loop_reports_already_applied_conflict_and_success(tmp_path):
    """워크플로의 푸시 루프 셸을 그대로 잘라 실제 git 저장소 셋(원격·앞 런·대기 런)에서 돌린다.

    ① 앞 런과 같은 내용(같은 data.js 줄) → rebase 가 패치를 버린다 → '➖ … 이미 커밋'(✅ 커밋·푸시 아님), rc 0.
    ② 앞 런과 다른 내용(같은 줄을 다르게) → 3회 충돌 → '❌ 푸시 3회 실패 … 겹친 배치 런 … 작성자: stats-bot', rc 1.
    ③ 다른 파일만 바꿈 → 정상 푸시 '✅ 커밋·푸시'.
    변이(실제로 확인): '이미 반영' 분기(HEAD == FETCH_HEAD 검사)를 지우면 ① 이 '✅ 커밋·푸시'가 되어 빨강. 실패 문구에서
    '겹친 배치 런'·작성자 표기를 지우면 ② 가 빨강.
    픽스처: 2026-10-05 겹친 두 런(앞 런 70c50c7 커밋 뒤 대기 런이 옛 main 에서 같은 데이터·다른 데이터를 만든 경우)을
    한 줄 data.js 로 줄였다.
    """
    (tmp_path / 's1').mkdir()
    b = _setup(tmp_path / 's1', 'const ADV={"a":2};\n', 'const ADV={"a":2};\n')
    rc, rep = _run_loop(b, tmp_path / 's1')
    assert rc == 0 and '➖' in rep and '이미 커밋' in rep and '✅ 커밋·푸시' not in rep, (rc, rep)

    (tmp_path / 's2').mkdir()
    b = _setup(tmp_path / 's2', 'const ADV={"a":2};\n', 'const ADV={"a":3};\n')
    rc, rep = _run_loop(b, tmp_path / 's2')
    assert rc == 1 and '푸시 3회 실패' in rep and '겹친 배치 런' in rep and 'stats-bot' in rep, (rc, rep)

    (tmp_path / 's3').mkdir()
    b = _setup(tmp_path / 's3', 'const ADV={"a":2};\n', 'y\n', b_file='other.txt')
    rc, rep = _run_loop(b, tmp_path / 's3')
    assert rc == 0 and '✅ 커밋·푸시' in rep and '✅ IndexNow 시험' in rep, (rc, rep)
