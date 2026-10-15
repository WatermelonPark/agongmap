# -*- coding: utf-8 -*-
"""주간 초안 본문(표·오른 곳·방향이 바뀐 곳)에 내부 지역 이름 '전남광주'가 보이지 않는다(검색 표기 '광주·전남').
10-12 주간 초안 표와 '지난주와 방향이 바뀐 곳은 … 전남광주(상승 전환)'에 그대로 나갔다(10-15 점검).
변이(실제로 확인): 표 행이나 방향 문장의 이름을 k/z 로 되돌리면 빨개진다. 픽스처: 저장소의 실제 ADV(캡처는 끈다).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402


def test_weekly_body_uses_search_names(monkeypatch):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    adv, sts = P.M.load()
    d = P.draft_weekly(adv, sts, shot=False)
    shown = re.sub(r'href="[^"]*"', '', d['body'])
    assert '전남광주' not in shown, re.findall(r'.{20}전남광주.{20}', shown)
    assert '광주·전남' in shown
    W = adv['weekly']
    W2 = dict(W, rows=W['rows'][:-1] + [dict(W['rows'][-1])])
    i = W['regions'].index('전남광주')
    prev = W['rows'][-2]['ma'][i]
    W2['rows'][-1]['ma'] = list(W['rows'][-1]['ma'])
    W2['rows'][-1]['ma'][i] = 0.3 if (prev is None or prev <= 0) else -0.3   # 방향 전환을 억지로 만든다
    para, _ = P.weekly_moves_sentences(W2)
    assert '전남광주' not in para
