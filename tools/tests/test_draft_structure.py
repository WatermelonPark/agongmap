# -*- coding: utf-8 -*-
"""블로그 초안 구조 점검(2026-10-15) — 결론 먼저, 주간 썸네일, 그 주 세부 키워드 태그, 지역 편 방어 문장 제거.

배경: 블로그 평소 방문 하루 8명, 10-09~13 네 편이 더한 방문 글당 0~7명. 주간 초안은 해석(결론)을 표·TOP10·지도 뒤
맨 아래에 두어 CLAUDE.md 블로그 구조(결론 → 내용)와 거꾸로였고, 홈피드(유입 90%) 카드에 썸네일 대신 TOP10 표가 떴다.
지역 편 미분양 문단은 '부족 판정과 어긋나 보이지만 모순이 아닙니다 —'로 부정형 시작·엠대시였고, 판정 문장에 '모자란'이 남았다.

무엇을 깨뜨리면 빨개지나(실제로 확인): 해석 칸을 표 뒤로 되돌리면 순서 시험이(자리 표시자 위치 기준), imgs 에서 썸네일을 빼면 썸네일 시험이,
태그를 '집값전망' 고정으로 되돌리면 태그 시험이, 미분양 문단을 옛 문장으로 되돌리면 지역 편 시험이 빨개진다.
픽스처: 저장소의 실제 ADV(캡처·경쟁 글 패널은 끈다). 지역 편은 미분양 경고가 붙는 실제 시도를 고른다.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import sido_zones as SZ  # noqa: E402


@pytest.fixture
def weekly(monkeypatch, tmp_path):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    adv, sts = P.M.load()
    return adv, P.draft_weekly(adv, sts, shot=False)


def test_weekly_puts_the_interpretation_before_the_table(weekly):
    body = weekly[1]['body']
    # 해석 칸의 소제목은 회차마다 돈다(반복률, 10-15) — 자리 표시자 위치로 본다.
    assert body.index(P.INTERP_PLACEHOLDER) < body.index('<table'), '해석(결론)이 표보다 뒤에 있다'
    assert body.index('[여기에 썸네일') < body.index(P.INTERP_PLACEHOLDER)


def test_weekly_has_a_thumbnail_first(weekly):
    path, label = weekly[1]['imgs'][0]
    assert label.startswith('썸네일') and path, weekly[1]['imgs']
    assert os.path.exists(os.path.normpath(os.path.join(P.ROOT, path))), (path, os.listdir(P.OUT))


def test_weekly_fifth_tag_is_this_weeks_top_region(weekly):
    adv, d = weekly
    W = adv['weekly']
    last = W['rows'][-1]
    sido = [(z, v) for z, v in zip(W['regions'], last['ma']) if z not in SZ.AGG and v is not None]
    up, _ = P.MW.top3(sido)
    top = up[0][0]
    want = P.TAG_NAME.get(top, P.SEARCH_NAME.get(top, top)).replace('·', '') + '아파트값'
    assert d['tags'][3] == want and d['tags'][:3] == ['주간아파트가격동향', '주간아파트동향', '아파트시세'], d['tags']


def test_zone_unsold_paragraph_is_not_defensive(monkeypatch):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'series_links', lambda nm, seq, total=None: '')
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    adv, sts = P.M.load()
    rows = [r for r in adv['sido']['zones'] if not r.get('agg') and r.get('uwarn')]
    if not rows:
        pytest.skip('미분양 경고 지역이 없는 회차')
    d = P.draft_zone(adv, sts, rows[0], 7, 16)
    text = re.sub(r'<[^>]+>', '', d['body']).replace('첫 이미지가 대표 이미지가 됩니다', '')
    assert '모순이 아닙니다' not in text
    assert '모자' not in text, re.findall(r'.{15}모자.{10}', text)
    assert '—' not in re.sub(r'\[[^\]]*\]', '', text), re.findall(r'.{20}—.{10}', text)
