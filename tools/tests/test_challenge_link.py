# -*- coding: utf-8 -*-
"""대결 링크 해석(readChallenge)과 수락 이벤트(challenge_accepted)를 고정한다(백로그 15, 리뷰 15번).

2026-09-16 리뷰:
  - readChallenge 가 점수 상한을 10으로 박아 두었다. 공유 페이지 생성기는 QUIZ_LEN 에서 0..N 을 만든다 —
    문항 수를 바꾸면 두 자리가 갈려 N점짜리 대결 링크가 조용히 무시된다.
  - challenge_accepted 가 대결 URL 을 새로고침·이어 풀기로 다시 열 때마다 발화해 수락 수가 부풀었다.

실제 home-app.js 의 함수를 꺼내 node 로 돌린다.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)


def _fn(src, name):
    a = src.find('function %s(' % name)
    assert a >= 0, '%s 를 찾지 못했다' % name
    b = src.find('\n}', a) + 2
    return src[a:b]


def _run(body):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    s = HS.home_source()
    js = ('let STORE={}, THROW=false;'
          'const sessionStorage={getItem(k){if(THROW)throw new Error("x");return k in STORE?STORE[k]:null},'
          'setItem(k,v){if(THROW)throw new Error("x");STORE[k]=String(v)}};'
          'let location={search:""}; let QUIZ_LEN=10;\n%s\n%s\n;(function(){%s})();'
          'process.stdout.write(JSON.stringify(OUT));') % (_fn(s, 'readChallenge'), _fn(s, 'challengeFirstSeen'), body)
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-800:]
    return json.loads(p.stdout.decode('utf-8'))


def test_score_cap_follows_quiz_len():
    """점수 상한은 QUIZ_LEN 이다 — 문항 수를 12로 바꾸면 12점 링크가 통하고 13점은 막힌다.

    깨뜨리면 빨개지는 것: readChallenge 의 상한을 sc>10 으로 되돌리면 12점 링크가 null 이 된다(변이로 확인).
    픽스처: QUIZ_LEN 만 12로 바꾼 상태의 실제 readChallenge.
    """
    o = _run("""QUIZ_LEN=12; const r=s=>{location.search=s;return readChallenge();};
OUT={ok12:r('?c=12&s=beginner&q=abc'), no13:r('?c=13&s=beginner'), neg:r('?c=-1&s=calc'), ten:r('?c=10&s=investor')};""")
    assert o['ok12'] and o['ok12']['score'] == 12, '문항 수가 12인데 12점 대결 링크를 버린다 — 상한이 박혀 있다'
    assert o['no13'] is None and o['neg'] is None, '상한 밖 점수를 받아들인다'
    assert o['ten'] and o['ten']['score'] == 10


def test_challenge_accepted_counts_once_per_link_per_tab():
    """같은 대결 링크를 다시 열어도 수락은 한 번만 센다. 다른 링크는 새로 센다. 저장소가 막히면 매번 센다.

    깨뜨리면 빨개지는 것: challengeFirstSeen 이 늘 true 를 돌려주게 하거나 boot 에서 가드를 빼면(변이로 확인).
    픽스처: 같은 탭(sessionStorage 공유)에서 같은 링크를 두 번, 다른 시드 링크를 한 번 연 흐름.
    """
    o = _run("""const a={set:'beginner',score:7,seed:123}, b={set:'beginner',score:7,seed:456};
const seq=[challengeFirstSeen(a), challengeFirstSeen(a), challengeFirstSeen(b)];
THROW=true; const blocked=[challengeFirstSeen(a), challengeFirstSeen(a)];
OUT={seq, blocked};""")
    assert o['seq'] == [True, False, True], '같은 대결을 다시 열 때 또 센다(또는 다른 대결을 못 센다): %s' % o['seq']
    assert o['blocked'] == [True, True], '저장소가 막힌 브라우저에서 수락을 빠뜨린다'
    src = HS.home_source()
    boot = _fn(src, 'boot')
    assert re.search(r"if\(challengeFirstSeen\(CHALLENGE\)\)track\('challenge_accepted'", boot), (
        'boot 가 challenge_accepted 를 가드 없이 보낸다')
