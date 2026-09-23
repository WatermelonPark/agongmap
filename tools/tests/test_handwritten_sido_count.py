# -*- coding: utf-8 -*-
"""손으로 쓴 페이지의 'N개 시도'가 모델의 시도 수와 같은지 본다.

생성기(make_sido_pages·make_indicator_pages)는 2026-09-23부터 시도 수를 모델에서 센다.
그러나 홈 머리(index.html의 description·JSON-LD), 소개(about/), 퀴즈 랜딩 3종은 사람이
쓴 파일이라 셀 수가 없다. 2026-09-10 광주·전남 통합 때 17→16을 사람이 찾아 고쳤고,
그때 무엇도 빨개지지 않았다(CLAUDE.md "사람이 센 수를 박지 않는다"). 다음 개편에서
여기가 빨개지도록 모델 값과 대조한다.

사이클 검증 곳 수('14개 시도 · 20년')는 다른 대상이라 뺀다 — CYCLE_SYNC_N 과의 일치는
test_cycle_count_sync 가 본다.

무엇을 깨뜨리면 빨개지나: index.html 의 '전국 16개 시도'를 '17개'로 바꾸면 실패한다(실제로
확인). 모델 쪽(sido_zones 의 지역 수)이 바뀌고 페이지를 안 고쳐도 같은 이유로 실패한다.
픽스처 없이 저장소의 실제 파일(손으로 쓴 페이지 6개)을 읽는다.
"""
import io
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sido_zones as SZ  # noqa: E402
import home_src as HS  # noqa: E402  (홈은 이 입구로만 읽는다 — 백로그 10)

HANDWRITTEN = ('index.html', 'about/index.html', 'faq/index.html',
               'burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html')

# '14개 시도 · 20년', '14개 시도 20년' 은 사이클 검증 곳 수다.
PAT = re.compile(r'(\d+)개 시도(?!\s*(?:·\s*)?20년)')


def test_handwritten_pages_say_model_sido_count():
    n = len([z for z in SZ.ORDER if z not in SZ.AGG])
    seen = 0
    bad = []
    for rel in HANDWRITTEN:
        if rel == 'index.html':
            s = HS.home_source()
        else:
            p = os.path.join(ROOT, rel)
            if not os.path.exists(p):
                continue
            s = io.open(p, encoding='utf-8').read()
        for m in PAT.finditer(s):
            seen += 1
            if int(m.group(1)) != n:
                line = s.count('\n', 0, m.start()) + 1
                bad.append('%s:%d %s' % (rel, line, m.group(0)))
    assert seen, '검사할 문구를 하나도 못 찾았다 — 패턴이나 파일 목록이 낡았다'
    assert not bad, '모델 시도 수는 %d인데 손으로 쓴 페이지가 다르게 말한다: %s' % (n, bad)
