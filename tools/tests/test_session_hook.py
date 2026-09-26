# -*- coding: utf-8 -*-
"""클라우드 세션 시작 훅이 배치 게이트와 같은 파이썬 판·같은 설치 목록의 **격리** 환경을 만든다(2026-09-26 데이터 감사).

예전 훅은 컨테이너의 python3(3.11, 시스템 yaml 등이 보임)에 pytest·pillow 를 깔았다. 그래서 세션에서 초록인
시험이 배치(setup-python 3.12, pytest·pillow 만)에서 빨개졌다 — 2026-09-24~26 에 시험 하나의 `import yaml` 이
데이터 갱신을 다섯 회 멈췄다. 이제 훅은 update-cloud.yml 의 파이썬 판으로 시스템 site-packages 없는 가상환경을
만들고 그 pip 줄의 패키지만 깐 뒤 PATH 앞에 둔다. 배치 쪽을 정본으로 삼아 둘이 같은지 본다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - 훅의 PKGS 에 pyyaml 을 더하면 → 설치 목록 단정이 빨강
  - 훅의 PY312 기본값을 /usr/bin/python3 로 바꾸면 → 파이썬 판 단정이 빨강
  - `-m venv` 에 --system-site-packages 를 붙이면 → 격리 단정이 빨강
  - 맨 앞의 CLAUDE_CODE_REMOTE 확인을 지우면 → 로컬 세션 무동작 단정이 빨강(환경 파일에 줄이 써진다)
  - PATH 를 환경 파일에 내보내지 않으면 → 빨강
픽스처: 저장소의 실제 훅과 update-cloud.yml. 로컬 세션(CLAUDE_CODE_REMOTE 없음)으로 훅을 실제로 한 번 돌리는데,
설치·네트워크 없이 끝나야 하는 경로다(임시 환경 파일·임시 캐시 경로, pip 는 색인 금지로 막는다).
"""
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_test_deps_are_installed import _pip_mods, WF_DIR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HOOK = os.path.join(ROOT, '.claude', 'hooks', 'session-start.sh')


def _hook_code():
    return '\n'.join(ln.split(' #')[0] for ln in io.open(HOOK, encoding='utf-8').read().splitlines()
                     if not ln.lstrip().startswith('#'))


def _batch():
    y = io.open(os.path.join(WF_DIR, 'update-cloud.yml'), encoding='utf-8').read()
    commit = y[y.index('\n  commit:'):]
    ver = re.search(r"python-version:\s*'([^']+)'", commit).group(1)
    pip = re.search(r'\bpip install\b(.*)', commit).group(1)
    return ver, _pip_mods(pip)


def test_hook_builds_the_batch_python_with_the_batch_packages_only():
    code = _hook_code()
    ver, mods = _batch()
    m = re.search(r'^PKGS="([^"]*)"', code, re.M)
    assert m and _pip_mods(m.group(1)) == mods, '훅 설치 목록이 배치 게이트와 다르다: %r vs %s' % (m and m.group(1), mods)
    m = re.search(r'^PY312="\$\{AGONGMAP_PY312:-([^}]*)\}"', code, re.M)
    assert m and m.group(1).endswith('python' + ver), '훅이 배치와 다른 파이썬(%s)으로 만든다 — 배치는 %s' % (
        m and m.group(1), ver)
    assert re.search(r'"\$PY312" -m venv ', code), '격리 가상환경을 만들지 않는다'
    assert 'system-site-packages' not in code, '시스템 site-packages 를 보이게 하면 yaml 같은 것이 다시 섞인다'
    assert re.search(r'export PATH=\\"\$VENV/bin:\\\$PATH\\"', code), '가상환경을 PATH 앞에 내보내지 않는다'


def test_hook_does_nothing_in_a_local_session(tmp_path):
    env_file = tmp_path / 'env'
    env_file.write_text('', encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_CODE_REMOTE'}
    env.update(CLAUDE_ENV_FILE=str(env_file), XDG_CACHE_HOME=str(tmp_path / 'cache'),
               AGONGMAP_PY312=str(tmp_path / 'no-python'), PIP_NO_INDEX='1')
    p = subprocess.run(['bash', HOOK], env=env, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    assert env_file.read_text(encoding='utf-8') == '', '로컬 세션에서 환경을 바꿨다'
    assert not (tmp_path / 'cache').exists(), '로컬 세션에서 가상환경을 만들었다'
