# -*- coding: utf-8 -*-
"""conftest 의 '시험이 저장소 파일을 바꾸면 실패' 감시가 .gitignore 에 든 배치 상태 파일도 보는지(2026-10 리뷰 E3).

감시는 `git status --porcelain -uall` 에 오른 파일만 견줬다. -uall 은 무시 파일을 보여 주지 않아, 시험이 저장소 루트의
.fetch_failed(러너 채택·ℹ️ 줄)나 .stats_changed 를 고쳐 써도 전체가 초록이었다 — 배치 게이트는 그 파일이 있는 작업
트리에서 돌고 커밋 잡이 게이트 뒤에 그것을 읽는다.

변이(실제로 확인): conftest 의 `_STATE_FILES` 를 빈 튜플로 바꾸면 이 시험이 빨개진다(rc 0, 파일 목록 없음).
픽스처: 임시 폴더에 저장소와 같은 모양(<루트>/tools/tests/conftest.py)을 만들고, 루트의 .fetch_failed 를 고쳐 쓰는
시험 하나를 pytest 로 띄운다. 루트에 미리 .fetch_failed 가 있는 상태(배치 러너 산출물)와 없는 상태 둘 다 본다.
임시 폴더는 git 저장소가 아니라 git status 부분은 비고, 상태 파일 감시만 돈다. 실제 저장소에는 쓰지 않는다.
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WRITER = ('import os\n'
          'ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))\n'
          'def test_writes_state():\n'
          '    open(os.path.join(ROOT, ".fetch_failed"), "w", encoding="utf-8").write("착공")\n')
READER = 'def test_ok():\n    assert True\n'


def _run(root, body):
    t = root / 'tools' / 'tests'
    t.mkdir(parents=True, exist_ok=True)
    shutil.copy(os.path.join(HERE, 'conftest.py'), str(t / 'conftest.py'))
    io.open(str(t / 'test_x.py'), 'w', encoding='utf-8').write(body)
    env = {k: v for k, v in os.environ.items() if k not in ('GITHUB_ACTIONS', 'AGONGMAP_ALLOW_SKIP')}
    env['GIT_CEILING_DIRECTORIES'] = str(root.parent)   # 임시 폴더의 git 이 위로 올라가 저장소를 찾지 않게
    p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', str(t)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=120)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def test_writing_a_gitignored_batch_state_file_fails_the_run(tmp_path):
    rc, out = _run(tmp_path / 'a', WRITER)
    assert rc != 0 and '저장소 파일을 바꿨다' in out and '.fetch_failed' in out, out[-400:]
    # 배치 러너처럼 루트에 이미 .fetch_failed 가 있어도 내용이 바뀌면 잡는다.
    b = tmp_path / 'b'
    b.mkdir()
    (b / '.fetch_failed').write_text('', encoding='utf-8')
    rc, out = _run(b, WRITER)
    assert rc != 0 and '.fetch_failed' in out, out[-400:]
    # 상태 파일을 건드리지 않는 실행은 그대로 초록이다.
    rc, out = _run(tmp_path / 'c', READER)
    assert rc == 0, out[-400:]
