# -*- coding: utf-8 -*-
"""네이버 글 끝 출처·면책 줄 없음(2026-11-10 대표 결정: "쓸데없다", "빼버려").

주간·지역 초안 생성기가 글 끝에 붙이던 '※ 숫자는 한국부동산원·국토교통부…' 류 출처 줄과 '개인 견해·투자 판단은 각자' 면책 줄을
뺐다. 발행창구 점검이 이 두 가지를 막으므로, 생성기가 다시 붙이면 매주 원고가 발행 단계에서 걸린다.
사이트 쪽 계산법 공개·공용 푸터 면책은 별개라 여기서 보지 않는다.

무엇을 깨뜨리면 빨개지나(실제로 확인): draft_weekly 나 draft_zone 끝에 옛 면책 줄(DISCLAIMERS 세 문장 중 하나)을 다시 붙이면
두 시험이 각각 빨개진다. 픽스처: 저장소의 실제 ADV(캡처·경쟁 글 패널은 끈다), 지역 편은 면책 문장이 회차마다 돌던 세 갈래
(seq 1~3)를 모두 돈다.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402

BANNED = re.compile(r'※[^<]*(한국부동산원|출처)|개인(의)? ?견해|개인 ?의견|투자 ?(판단|결정|결과)|투자자문')


def _shown(html):
    return re.sub(r'<[^>]+>', '', html)


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    return P.M.load()


def test_weekly_draft_has_no_source_or_disclaimer_footer(env):
    adv, sts = env
    text = _shown(P.draft_weekly(adv, sts, shot=False)['body'])
    assert not BANNED.search(text), BANNED.search(text).group(0)


def test_zone_draft_has_no_source_or_disclaimer_footer(env):
    adv, sts = env
    zs = [r for r in adv['sido']['zones'] if not r.get('agg')]
    assert zs, '지역이 없다 — 시험이 헛돈다'
    for seq in (1, 2, 3):
        text = _shown(P.draft_zone(adv, sts, dict(zs[0]), seq, len(zs))['body'])
        m = BANNED.search(text)
        assert not m, (seq, m and m.group(0))
