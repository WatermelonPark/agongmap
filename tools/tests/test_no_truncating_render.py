# -*- coding: utf-8 -*-
"""파일을 연 뒤에 render 를 돌리지 않는다 — 생성이 도중에 멈추면 기존 파일이 빈 파일이 된다(2026-09-18 리뷰 7번).

`io.open(path, 'w').write(render(...))` 는 파일을 먼저 열어 0바이트로 만든 뒤 render 를 돌린다. 이론 3편의 생성 가드(SystemExit)가
걸리자 사람이 해석 문단을 채워 둔 초안이 18,140바이트에서 0바이트가 됐다(그 초안 도구는 2026-11-13 에 지웠다). 같은 꼴이 다른
도구에 생기지 않게 tools/*.py 전부를 본다.

무엇을 깨뜨리면 빨개지나(실제로 확인): 아무 도구에 `io.open(path, 'w', encoding='utf-8').write(render(post))` 한 줄을 넣으면 빨개진다.
픽스처: 저장소의 tools/*.py 원문.
"""
import glob
import io
import os
import re

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_no_tool_opens_a_file_before_rendering_into_it():
    bad = []
    for p in glob.glob(os.path.join(TOOLS, '*.py')):
        s = io.open(p, encoding='utf-8').read()
        for m in re.finditer(r"open\([^()\n]*['\"]w['\"][^()\n]*\)\.write\(\s*render\(", s):
            bad.append('%s:%d' % (os.path.basename(p), s[:m.start()].count('\n') + 1))
    assert not bad, '파일을 연 뒤에 render 를 돌린다 — 멈추면 0바이트가 남는다: %s' % bad
