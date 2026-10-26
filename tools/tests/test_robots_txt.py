# -*- coding: utf-8 -*-
"""robots.txt 가 AI 검색·답변 크롤러를 이름으로 밝혀 허용하고, 어느 크롤러에도 사이트를 막지 않는다(2026-10-26 요청서 50 —
사이트 글이 AI 검색에 인용되는 것이 목표, 대표 결정: CCBot 포함 전부 허용).

변이(각각 실제로 확인): robots.txt 에서 `User-agent: GPTBot` 묶음을 지우면 첫 단정이, 그 묶음의 `Allow: /` 를
`Disallow: /` 로 바꾸면 둘째 단정이, Sitemap 줄의 도메인을 바꾸면 셋째 단정이 빨개진다.
픽스처: 저장소 robots.txt 그대로(손으로 쓰는 파일).
"""
import io
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
AI_BOTS = ('GPTBot', 'ChatGPT-User', 'OAI-SearchBot', 'PerplexityBot', 'ClaudeBot', 'Claude-SearchBot',
           'Google-Extended', 'Bingbot', 'Yeti', 'CCBot')


def _groups(txt):
    """{user-agent: [규칙 줄]} — 빈 줄·주석은 건너뛴다."""
    out, cur = {}, None
    for ln in txt.splitlines():
        ln = ln.split('#', 1)[0].strip()
        if not ln:
            continue
        k, _, v = ln.partition(':')
        k, v = k.strip().lower(), v.strip()
        if k == 'user-agent':
            cur = v
            out.setdefault(cur, [])
        elif cur is not None and k in ('allow', 'disallow'):
            out[cur].append((k, v))
    return out


def test_ai_crawlers_are_named_and_nothing_is_disallowed():
    txt = io.open(os.path.join(ROOT, 'robots.txt'), encoding='utf-8').read()
    g = _groups(txt)
    missing = [b for b in AI_BOTS if ('allow', '/') not in g.get(b, [])]
    assert not missing, '이름으로 허용하지 않은 AI 크롤러: %s' % missing
    blocked = sorted(ua for ua, rules in g.items() for k, v in rules if k == 'disallow' and v)
    assert not blocked, '사이트를 막는 크롤러가 있다: %s' % blocked
    host = io.open(os.path.join(ROOT, 'CNAME'), encoding='utf-8').read().strip()
    assert re.search(r'(?m)^Sitemap: https://%s/sitemap\.xml$' % re.escape(host), txt), 'Sitemap 줄이 정식 도메인이 아니다'
