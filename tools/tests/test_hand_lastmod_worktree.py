# -*- coding: utf-8 -*-
"""얕은 클론의 **작업 트리(git worktree)** 에서도 경계 커밋 날짜를 손 페이지 수정일로 믿지 않는다(2026-09-26 데이터 감사).

hand_lastmods 는 `.git/shallow` 에 적힌 경계 커밋이면 날짜를 버린다. 그 파일을 `rev-parse --git-dir` + 'shallow'
로 찾았는데, 작업 트리에서 --git-dir 은 `.git/worktrees/<이름>` 이고 shallow 는 공통 디렉터리(.git)에 있다.
그래서 작업 트리에서 생성기를 돌리면 창 밖에서 마지막으로 바뀐 손 페이지가 경계 커밋 날짜를 받아 sitemap
lastmod 가 앞으로 밀렸다(앞으로만 옮기는 규칙이라 되돌아오지도 않는다). 클라우드 에이전트가 `.claude/worktrees/`
에서, 로컬 세션이 `git worktree add --detach … origin/main` 에서 일한다.

무엇을 깨뜨리면 빨개지나(실제로 확인): hand_lastmods 의 `rev-parse --git-path shallow` 를 예전의
`rev-parse --git-dir` + 'shallow' 로 되돌리면 작업 트리 단정이 빨개진다(본 트리 단정은 그대로 초록).
픽스처: faq 를 마지막으로 바꾼 커밋이 얕은 클론(depth 1) 창 밖에 있는 저장소와, 그 얕은 클론에서 만든 작업 트리 —
배치 커밋 잡(fetch-depth 200)과 같은 얕은 상태를 작업 트리에서 본 모양이다.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402


def _git(cwd, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@t')
    return subprocess.run(['git'] + list(a), cwd=cwd, check=True, capture_output=True, env=env,
                          encoding='utf-8').stdout.strip()


def test_worktree_of_a_shallow_clone_does_not_trust_the_boundary(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    _git(str(src), 'init', '-q')
    (src / 'faq').mkdir()
    (src / 'faq' / 'index.html').write_text('faq', encoding='utf-8')
    _git(str(src), 'add', '.')
    _git(str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'faq', '--date', '2026-07-16T00:00:00')
    (src / 'other.txt').write_text('x', encoding='utf-8')
    _git(str(src), 'add', '.')
    _git(str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'other')

    shallow = tmp_path / 'shallow'
    _git(str(tmp_path), 'clone', '-q', '--depth', '1', 'file://' + str(src), str(shallow))
    wt = tmp_path / 'wt'
    _git(str(shallow), 'worktree', 'add', '-q', '--detach', str(wt), 'HEAD')
    # 픽스처 확인 — 작업 트리의 --git-dir 은 공통 디렉터리가 아니다(그래서 옛 코드가 shallow 를 못 찾았다).
    assert _git(str(wt), 'rev-parse', '--git-dir') != _git(str(wt), 'rev-parse', '--git-common-dir')

    assert '/faq/' not in dict(I.hand_lastmods(str(shallow))), '본 트리에서 경계 커밋을 믿었다'
    got = dict(I.hand_lastmods(str(wt)))
    assert '/faq/' not in got, '작업 트리에서 얕은 클론의 경계 커밋 날짜를 faq 수정일로 믿었다: %s' % got
