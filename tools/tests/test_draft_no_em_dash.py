# -*- coding: utf-8 -*-
"""블로그에 그대로 나가는 생성기 고정 문구에 엠대시(—)를 쓰지 않는다(한국어 지침). 10-09 점검에서 주간 초안 소제목
'이번 주의 지표 — 전세가율'과 이론 초안 링크 글자 '우리 동네 공급은 어떤가 — 시도별 리포트'가 발행본에 실렸다.
무엇을 깨뜨리면 빨개지나(실제로 확인): 소제목을 '이번 주의 지표 — %s' 로, 링크 글자를 옛 문구로 되돌리면 빨개진다.
픽스처: 생성기 소스 문자열(코드 주석의 엠대시는 대상이 아니므로 h3 와 link( 글자만 본다).

2026-10-18 전수리뷰 T1-6: 위 두 자리만 보던 사이 주간 '더 보기' 퀴즈 링크 셋('부린이 테스트 — …', 4주에 한 번)과 세종 편
덧붙임(사이트 정본 MODEL_LIMIT_NOTE 의 '— 가격이 바닥이던'), 이론 1·2편 고정 문구가 엠대시를 실었다. 이제 주간 초안 전부(이번 주의
지표·더 보기 4칸 × 문장 틀 3개)와 모든 시도 지역 편(문장 틀 3개씩)의 보이는 글자(태그·대괄호 자리 표시자를 걷은 것), 이론 초안
소스의 본문 문단·소제목을 본다.
"""
import io
import os
import re
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _src(name):
    return io.open(os.path.join(TOOLS, name), encoding='utf-8').read()


def test_weekly_indicator_headings_have_no_em_dash():
    hs = re.findall(r"<h3>이번 주의 지표[^<]*</h3>", _src('make_naver_post.py'))
    assert hs and not [h for h in hs if '—' in h], hs


def test_theory_link_texts_have_no_em_dash():
    texts = re.findall(r"link\('([^']*)'", _src('make_theory_post.py'))
    assert texts and not [t for t in texts if '—' in t], texts


sys.path.insert(0, TOOLS)


def _shown(html):
    """태그·대괄호 자리 표시자(사람이 지우는 안내)를 걷은 보이는 글자."""
    return re.sub(r'\[[^\]]*\]', '', re.sub(r'<[^>]+>', '', html))


@pytest.fixture
def P(monkeypatch, tmp_path):
    import make_naver_post as P
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'thumb_weekly', lambda *a, **k: None)
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    return P


def test_every_weekly_draft_variant_has_no_em_dash(P, monkeypatch):
    """주간 초안: 이번 주의 지표·더 보기 4칸(rot_index) × 문장 틀 3개(_wk) 전부.
    변이(확인): MORE_ROTATION 퀴즈 링크 글자를 옛 '부린이 테스트 — 내 감각은 몇 점인가' 로 되돌리면 빨개진다.
    픽스처: 저장소의 실제 ADV 최신 주(캡처·썸네일·경쟁 글 패널은 끈다), rot 와 문장 틀만 고정해 바꾼다."""
    adv, sts = P.M.load()
    n = 0
    for rot in range(4):
        for k in range(3):
            monkeypatch.setattr(P, 'rot_index', lambda p, rot=rot: rot)
            monkeypatch.setattr(P, '_wk', lambda p, m, k=k: k % m)
            text = _shown(P.draft_weekly(adv, sts, shot=False)['body'])
            assert '—' not in text, (rot, k, re.findall(r'.{20}—.{10}', text))
            n += 1
    assert n == 12


def test_every_zone_draft_has_no_em_dash(P):
    """지역 편: 모든 시도(집계 제외) × 문장 틀 3개. 모델 한계 덧붙임(세종)도 블로그 문구(blog_limit_note)로 실린다.
    변이(확인): draft_zone 이 MODEL_LIMIT_NOTE 를 그대로(lstrip 만) 실으면 세종 편에서 빨개진다.
    픽스처: 저장소의 실제 ADV.sido. 덧붙임이 붙는 지역이 하나 이상 있는지 함께 본다(없으면 그 경로를 안 본 것이다)."""
    adv, sts = P.M.load()
    zs = [r for r in adv['sido']['zones'] if not r.get('agg')]
    total = len(zs)
    seqs = {}
    for seq in range(1, 3 * total + 1):
        seqs.setdefault((P._rot(seq, 3, total) + P.ROT_SHIFT) % 3, seq)
    assert sorted(seqs) == [0, 1, 2], seqs
    noted = 0
    for r in zs:
        for seq in seqs.values():
            text = _shown(P.draft_zone(adv, sts, dict(r), seq, total)['body'])
            assert '—' not in text, (r['z'], seq, re.findall(r'.{20}—.{10}', text))
            noted += '덧붙임.' in text
    assert noted and P.M.MODEL_LIMIT_NOTE, '덧붙임이 붙은 지역 편이 없다 — 그 경로를 보지 않았다'


def test_theory_body_paragraphs_have_no_em_dash():
    """이론 초안 소스의 본문 문단·소제목(대괄호 자리 표시자 제외)에 엠대시가 없다.
    변이(확인): 1편 '예를 들어 ①번 고리, …' 를 옛 '①번 고리 — …' 로 되돌리면 빨개진다.
    픽스처: make_theory_post 소스 문자열(편마다 전제 가드를 지나야 렌더되므로 소스의 고정 문구를 본다)."""
    src = _src('make_theory_post.py')
    blocks = re.findall(r'<(?:p|h3|li)>(?!\[)([^<]*)</', src)
    assert len(blocks) > 50, len(blocks)
    bad = [b for b in blocks if '—' in b]
    assert not bad, bad
