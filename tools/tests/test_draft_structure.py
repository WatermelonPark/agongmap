# -*- coding: utf-8 -*-
"""블로그 초안 구조 점검(2026-10-15) — 결론 먼저, 주간 썸네일, 그 주 세부 키워드 태그, 지역 편 방어 문장 제거.

배경: 블로그 평소 방문 하루 8명, 10-09~13 네 편이 더한 방문 글당 0~7명. 주간 초안은 해석(결론)을 표·TOP10·지도 뒤
맨 아래에 두어 CLAUDE.md 블로그 구조(결론 → 내용)와 거꾸로였고, 홈피드(유입 90%) 카드에 썸네일 대신 TOP10 표가 떴다.
지역 편 미분양 문단은 '부족 판정과 어긋나 보이지만 모순이 아닙니다 —'로 부정형 시작·엠대시였고, 판정 문장에 '모자란'이 남았다.

무엇을 깨뜨리면 빨개지나(실제로 확인): 해석 칸을 표 뒤로 되돌리면 순서 시험이(자리 표시자 위치 기준), imgs 에서 썸네일을 빼면 썸네일 시험이,
태그를 '집값전망' 고정으로 되돌리면 태그 시험이, 미분양 문단을 옛 문장으로 되돌리면 지역 편 시험이 빨개진다.
픽스처: 저장소의 실제 ADV(캡처·경쟁 글 패널은 끈다). 지역 편은 미분양 경고가 붙는 실제 시도를 고른다.
"""
import copy
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


def _top_tag(top):
    return P.TAG_NAME.get(top, P.SEARCH_NAME.get(top, top)).replace('·', '') + '아파트값'


def _week_with(adv, vals, rest=-0.02):
    """최신 주 시도 매매값을 vals({시도: 값})로, 나머지 시도는 rest 로 바꾼 사본(전국·수도권·지방 집계 칸은 그대로)."""
    adv = copy.deepcopy(adv)
    W = adv['weekly']
    last = W['rows'][-1]
    for i, z in enumerate(W['regions']):
        if z in P.MW.SIDO:
            last['ma'][i] = vals.get(z, rest)
    return adv


def test_weekly_fifth_tag_is_this_weeks_top_region(weekly):
    """다섯째 태그는 그 주 가장 많이 오른 시도의 세부 키워드다('경기아파트값'). 오른 시도가 없는 주는 '집값전망'으로 내린다(도구 규칙).

    예전 시험은 실데이터 최신 주에서 up[0][0] 을 조건 없이 읽어, 오른 시도가 하나도 없는 주(실데이터 156주 가운데 2024-01-01·
    2024-12-30~2025-01-20 다섯 주, 모두 연말연초)에 IndexError 로 게이트를 막았다(전수리뷰 BL1-2). 이제 실데이터는 도구와 같은 규칙
    (MW.SIDO 순서·MW.top3)으로 기대값을 셈하고, 두 갈래는 합성 주로 늘 본다.
    변이(실제로 확인): 태그를 '집값전망' 고정으로 되돌리면 ① 합성 주가, `if up else '집값전망'` 을 지우면 ② 합성 주가 빨개진다.
    픽스처: 저장소의 실제 ADV 최신 주 + 그 주를 고친 사본 둘 — ① 한 시도만 +0.30%(나머지 −0.02%), 태그 이름 정본(TAG_NAME)이
    바꾸는 시도를 골라 그 길까지 본다 ② 모든 시도 −0.02%(오른 곳이 없는 연말연초 주의 모양).
    """
    adv, d = weekly
    W = adv['weekly']
    val = dict(zip(W['regions'], W['rows'][-1]['ma']))
    up, _ = P.MW.top3([(k, val[k]) for k in P.MW.SIDO if k in val and val[k] is not None])
    assert d['tags'][3] == (_top_tag(up[0][0]) if up else '집값전망'), d['tags']
    assert d['tags'][:3] == ['주간아파트가격동향', '주간아파트동향', '아파트시세'], d['tags']
    _, sts = P.M.load()
    top = next((z for z in P.TAG_NAME if z in P.MW.SIDO and z in W['regions']), P.MW.SIDO[0])
    t1 = P.draft_weekly(_week_with(adv, {top: 0.30}), sts, shot=False)['tags']
    assert t1[3] == _top_tag(top) != '집값전망', t1
    t2 = P.draft_weekly(_week_with(adv, {}), sts, shot=False)['tags']
    assert t2[3] == '집값전망', t2


def test_zone_unsold_paragraph_is_not_defensive(monkeypatch):
    """지역 편 미분양 경고 문단(세 문장 틀 모두)이 방어 문장('모순이 아닙니다')·'모자'·엠대시 없이 나간다.

    예전 시험은 실데이터에 미분양 경고 지역이 없으면 pytest.skip 했다 — CI 에서는 건너뜀이 실패라, 경고 지역이 0곳이 되는 회차
    (미분양 이력으로 되짚으면 2014~16·2021년에 그런 달이 있다)에 게이트가 막혔다(전수리뷰 BL1-4·T1-3). 또 seq=7 한 틀만 봤다.
    이제 실제 경고 지역(있으면)과 실제 시도 한 줄을 경고로 바꾼 합성 행(늘)을, 문장 틀 세 개(k3 = 0·1·2)마다 굽는다. 모델 한계
    덧붙임(MODEL_LIMIT_NOTE)이 붙는 지역은 고르지 않는다 — 그 안내문은 이 시험이 보는 미분양 문단이 아니다.
    변이(실제로 확인): 미분양 경고 문단 첫 틀을 옛 '부족 판정과 어긋나 보이지만 모순이 아닙니다 — …'로 되돌리면 빨개진다.
    픽스처: 저장소의 실제 ADV(캡처·경쟁 글 패널·썸네일은 끈다) + 그 행을 uwarn=True·um≥1.2·미분양≥1,000세대로 덮은 사본.
    """
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'series_links', lambda nm, seq, total=None: '')
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    adv, sts = P.M.load()
    zs = [r for r in adv['sido']['zones'] if not r.get('agg')]
    notes = getattr(P.M, 'MODEL_LIMIT_NOTE', None) or {}
    plain = [r for r in zs if r['z'] not in notes and r.get('um') is not None]
    assert plain, '고를 시도가 없다 — 시험이 헛돈다'
    base = plain[0]
    rows = [r for r in plain if r.get('uwarn') and r.get('unsold')][:1] + [
        dict(base, uwarn=True, um=max(base['um'], 1.2), unsold=max(base.get('unsold') or 0, 1000))]
    total = len(zs)
    seqs = {}
    for seq in range(1, 3 * total + 1):          # 미분양 문단 틀은 draft_zone 과 같은 k3 규칙으로 돈다
        seqs.setdefault((P._rot(seq, 3, total) + P.ROT_SHIFT) % 3, seq)
    assert sorted(seqs) == [0, 1, 2], seqs
    for r in rows:
        for k3, seq in sorted(seqs.items()):
            d = P.draft_zone(adv, sts, r, seq, total)
            text = re.sub(r'<[^>]+>', '', d['body']).replace('첫 이미지가 대표 이미지가 됩니다', '')
            assert '분기 적정물량의 %s' % P.umx(r['um']) in text, (r['z'], k3, '경고 문단이 안 찍혔다 — 시험이 헛돈다')
            assert '모순이 아닙니다' not in text, (r['z'], k3)
            assert '모자' not in text, (r['z'], k3, re.findall(r'.{15}모자.{10}', text))
            assert '—' not in re.sub(r'\[[^\]]*\]', '', text), (r['z'], k3, re.findall(r'.{20}—.{10}', text))
