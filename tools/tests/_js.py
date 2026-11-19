# -*- coding: utf-8 -*-
"""시험이 홈 스크립트 조각을 node 에 올릴 때 쓰는 공용 도우미(표준 라이브러리만 — 게이트는 pytest·pillow 만 깐다).

같은 두 함수(중괄호 짝으로 함수 떼기, node 실행)가 시험 파일 스무 곳 남짓에 조금씩 다른 꼴로 복제돼 있었다(2026-11-13 전수
리뷰 — 한쪽은 node 가 없으면 건너뛰고 한쪽은 단정하는 식으로 정책도 갈렸다). 새 시험은 여기 것을 쓰고, 옛 시험은 고칠 때 옮긴다.
"""
import json
import os
import shutil
import subprocess
import tempfile

import pytest


def fn(src, name):
    """src 에서 `function name(…){…}` 를 중괄호 짝으로 떼어 낸다(줄 머리의 선언만 — 호출·주석 속 이름에 걸리지 않게)."""
    src_n = '\n' + src   # 맨 앞 줄의 선언도 줄 머리로 친다
    for head in ('\nfunction %s(' % name, '\nasync function %s(' % name):
        a = src_n.find(head)
        if a >= 0:
            break
    else:
        raise AssertionError('함수 %s 를 찾지 못했다' % name)
    i, depth = src.index('{', a), 0
    for j in range(i, len(src)):
        c = src[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[a:j + 1]
    raise AssertionError('함수 %s 의 끝을 찾지 못했다' % name)


def fns(src, *names):
    return '\n'.join(fn(src, n) for n in names)


def node(js, timeout=60, args=(), timeout_msg=None):
    """js 를 node 로 돌려 표준 출력(JSON)을 돌려준다. node 가 없으면 건너뛴다 — CI 에서는 건너뜀도 실패라 헛통과가 아니다.

    js 는 임시 파일로 넘긴다(명령줄 한도가 없다). args 는 그 뒤에 붙는 명령줄 인자(js 에서 process.argv.slice(2)).
    timeout_msg 를 주면 시간 초과를 그 문구의 시험 실패로 바꾼다 — '끝나지 않는' 결함을 재는 시험용(없으면 TimeoutExpired 그대로).
    """
    if not shutil.which('node'):
        pytest.skip('node 없음')
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(js)
    try:
        p = subprocess.run(['node', path] + [str(a) for a in args], capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        if timeout_msg is None:
            raise
        pytest.fail(timeout_msg)
    finally:
        os.remove(path)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8'))
