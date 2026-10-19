# -*- coding: utf-8 -*-
"""주간 초안 본문(표·오른 곳·방향이 바뀐 곳)에 내부 지역 이름 '전남광주'가 보이지 않는다(검색 표기 '광주·전남').
10-12 주간 초안 표와 '지난주와 방향이 바뀐 곳은 … 전남광주(상승 전환)'에 그대로 나갔다(10-15 점검).
변이(실제로 확인): 표 행이나 방향 문장의 이름을 k/z 로 되돌리면 빨개진다. 픽스처: 저장소의 실제 ADV(캡처는 끈다)와, 최신 주
그 지역 값을 채운 사본 — 실데이터 최신 주에 그 지역 값이 비면(2026-04-27~07-06 전남광주 11주) 도구가 표·순위에서 그 행을 빼므로
검색 표기가 나온다는 단정은 사본에서만 건다(전수리뷰 BL1-3·T3-3 — 실데이터로 단정하면 그 주들 내내 게이트가 막혔다).
"""
import copy
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402


def _shown(d):
    return re.sub(r'href="[^"]*"', '', d['body'])


def test_weekly_body_uses_search_names(monkeypatch):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    adv, sts = P.M.load()
    W = adv['weekly']
    # 검색 표기가 내부 이름과 다르고 내부 이름을 품지 않는 지역('전남광주' → '광주·전남'; '세종' → '세종시' 는 글자로 못 가른다)
    pairs = [(k, P.SEARCH_NAME[k]) for k in W['regions'] if P.SEARCH_NAME.get(k, k) != k and k not in P.SEARCH_NAME[k]]
    assert pairs, '검색 표기가 다른 지역을 못 찾았다 — 시험이 헛돈다'
    shown = _shown(P.draft_weekly(adv, sts, shot=False))
    for k, _ in pairs:
        assert k not in shown, re.findall(r'.{20}%s.{20}' % k, shown)
    adv2 = copy.deepcopy(adv)
    last = adv2['weekly']['rows'][-1]
    for k, _ in pairs:
        i = W['regions'].index(k)
        last['ma'][i], last['je'][i] = 0.9, 0.03      # 그 주 1위로 — 표·오른 곳 문장에 반드시 실린다
    shown2 = _shown(P.draft_weekly(adv2, sts, shot=False))
    for k, nm in pairs:
        assert nm in shown2 and k not in shown2, (k, re.findall(r'.{20}%s.{20}' % k, shown2))
        # 방향 전환을 억지로 만든다 — 지난주 하락(−0.3%), 이번 주 상승(+0.3%). 결측인 주에도 '전환'이 서도록 두 주를 다 고친다
        W2 = dict(W, rows=W['rows'][:-2] + [dict(W['rows'][-2]), dict(W['rows'][-1])])
        i = W['regions'].index(k)
        for row, v in zip(W2['rows'][-2:], (-0.3, 0.3)):
            row['ma'] = list(row['ma'])
            row['ma'][i] = v
        para, _ = P.weekly_moves_sentences(W2)
        assert nm in para and k not in para, para
