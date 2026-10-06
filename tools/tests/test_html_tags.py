# -*- coding: utf-8 -*-
"""저장소의 모든 HTML 여는 태그는 속성 사이가 띄어져 있다 — '<details id="q2"None>' 같은 붙은 찌꺼기가 없다.

재현하는 실제 상태: 2026-10-06 FAQ 데스크톱 목차 작업에서 편집 스크립트가 파이썬 None 을 속성 자리에 써 q2~q11 이
'<details id="q2"None>' 이 됐다. 브라우저는 그냥 넘겨 화면도 목차 시험(test_desk — id 만 본다)도 초록이었다(2026-10-07 리뷰).
픽스처: 저장소의 실제 페이지(생성 페이지는 배치·CI 처럼 생성기를 먼저 돌린 상태). <script>·<style> 안은 보지 않는다.

변이(실제로 확인): faq/index.html 의 '<details id="q2">' 를 '<details id="q2"None>' 로 되돌리면 → 빨강.
"""
import io
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SKIP_DIRS = ('drafts', 'logs', 'node_modules')
CODE = re.compile(r'<(script|style)\b.*?</\1>', re.S)
TAG = re.compile(r'<[a-zA-Z][^<>]*>')
GLUED = re.compile(r'="[^"]*"[^\s/>]')


def test_no_glued_attributes():
    bad = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in SKIP_DIRS]
        for f in files:
            if not f.endswith('.html'):
                continue
            path = os.path.join(d, f)
            html = CODE.sub('', io.open(path, encoding='utf-8').read())
            bad += ['%s: %s' % (os.path.relpath(path, ROOT), m.group(0)[:80])
                    for m in TAG.finditer(html) if GLUED.search(m.group(0))]
    assert not bad, '속성이 붙은 태그: %s' % bad[:10]
