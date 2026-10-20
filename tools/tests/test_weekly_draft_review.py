# -*- coding: utf-8 -*-
"""주간 블로그 초안의 지도 범례·계열 날짜·서울 구 수(2026-10-18 전수리뷰 BL1-6·BL1-9·BL1-13·X1-15).

- BL1-6: 지도 캡처는 .map-scroll(SVG 타일)만 찍어 화면 범례 줄('타일 값: 위 = 매매 · 아래 = 전세')이 그림에 없다. 본문 지도
  자리 바로 뒤에 범례 한 줄(MAP_LEGEND)을 둔다.
- BL1-9: 서울 구·시군구 계열이 시도보다 한 주 늦은 회차(서울 구 응답이 빈 주에 수집이 직전 블록을 그대로 둔다)에 지난 조사분
  순위를 '이번 주' 문장으로 쓰지 않는다.
- BL1-13·X1-15: '서울 N개 구 가운데'의 N 은 그 주 값이 온 구의 수다(/weekly/ count_text 와 같은 셈) — 25 를 박지 않는다.

픽스처: 저장소의 실제 ADV(캡처·경쟁 글 패널은 끄고 OUT 은 임시 폴더). 날짜가 갈리는 상태와 부분 응답 주는 실제 행을 고친 사본으로
늘 만든다 — 데이터가 앞으로 가도 같은 갈래를 본다. 문장 틀 번호(_wk)는 고정해 세 틀을 모두 돈다.
"""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402


@pytest.fixture
def real(monkeypatch, tmp_path):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    return P.M.load()


def _text(body):
    """태그와 대괄호 자리 표시자를 걷은 보이는 글자."""
    return re.sub(r'\[[^\]]*\]', '', re.sub(r'<[^>]+>', '', body))


def test_map_legend_follows_the_map_placeholder(real, monkeypatch):
    """세 문장 틀 모두 지도 자리 바로 다음 문단이 범례(위 = 매매, 아래 = 전세)다.

    변이(확인): draft_weekly 에서 범례 문단(body.append MAP_LEGEND) 줄을 지우면 빨개진다. MAP_LEGEND 한 틀에서 '전세'를 빼도
    빨개진다.
    픽스처: 실제 ADV 최신 주, _wk 를 0·1·2 로 고정한 세 초안.
    """
    adv, sts = real
    seen = set()
    for k in range(3):
        monkeypatch.setattr(P, '_wk', lambda p, n, k=k: k % n)
        body = P.draft_weekly(adv, sts, shot=False)['body']
        i = body.index('[여기에 전국 시군구 지도 이미지를 넣어 주세요]')
        nxt = re.search(r'<p>(.*?)</p>', body[i:].split('</p>', 1)[1]).group(1)
        assert nxt == P.MAP_LEGEND[k], nxt
        assert re.search('위.*매매.*아래.*전세', nxt), nxt
        seen.add(nxt)
    assert len(seen) == 3


def _sgg_two_rows(W, p_prev, p_last):
    """실제 시군구 코드로 만든 두 주 계열 — 둘째 주에 순서가 뒤집혀 상승 TOP 10 이 모두 순위가 뛴다."""
    S = copy.deepcopy(W['sgg'])
    n = len(S['codes'])
    a = [round(0.01 * i, 2) for i in range(n)]
    S['rows'] = [dict(p=p_prev, ma=list(a), je=list(a)), dict(p=p_last, ma=list(reversed(a)), je=list(reversed(a)))]
    return S


def test_stale_seoul_and_sgg_rows_are_not_reported_as_this_week(real):
    """시도 최신 주보다 늦은 서울 구·시군구 행은 '이번 주' 문장으로 쓰지 않고, 같은 날이면 쓴다.

    변이(확인): draft_weekly 의 같은 날 행 고르기를 S['rows'][-1] 로 되돌리면 늦은 갈래가, weekly_moves_sentences 의
    `S['rows'][-1]['p'] == W['rows'][-1]['p']` 조건을 지우면 순위 문장 단정이 빨개진다.
    픽스처: 실제 ADV 사본. ① 서울 구 마지막 행을 떼어 시도보다 한 주 늦은 상태(전수리뷰 BL1-9 재현과 같은 모양 — 서울 구 응답이
    빈 회차) ② 시군구를 실제 코드의 합성 두 주(상승 TOP 10 이 모두 순위가 뛴다)로 두고 마지막 날을 시도와 같게/한 주 늦게.
    서울 구 마지막 행은 모두 +0.1% 로 둬 같은 날 갈래에서 상위 3 이 늘 있다.
    """
    adv, sts = real
    W = adv['weekly']
    p = W['rows'][-1]['p']
    pp = W['rows'][-2]['p']
    fresh = copy.deepcopy(adv)
    FS = fresh['weekly']['seoul']
    FS['rows'][-1] = dict(FS['rows'][-1], p=p, ma=[0.1] * len(FS['regions']))
    fresh['weekly']['sgg'] = _sgg_two_rows(W, pp, p)
    stale = copy.deepcopy(fresh)
    stale['weekly']['seoul']['rows'] = [r for r in stale['weekly']['seoul']['rows'] if r['p'] != p]
    stale['weekly']['sgg'] = _sgg_two_rows(W, W['rows'][-3]['p'], pp)
    assert stale['weekly']['seoul']['rows'][-1]['p'] < p

    gu_pat = r'서울 안에서는|서울 \d+개 구 가운데서는|서울을 구별로 보면'
    rk = '순위가 가장 많이 뛴 곳은'
    body = P.draft_weekly(fresh, sts, shot=False)['body']
    assert re.search(gu_pat, body) and rk in body, '같은 날 갈래에서 문장이 빠졌다 — 단정이 헛돈다'
    body = P.draft_weekly(stale, sts, shot=False)['body']
    assert not re.search(gu_pat, body), '한 주 늦은 서울 구 순위를 이번 주 문장으로 썼다'
    assert rk not in body, '한 주 늦은 시군구 순위 이동을 이번 주 문장으로 썼다'
    assert P.weekly_moves_sentences(stale['weekly'])[1] == ''


def test_seoul_gu_count_is_the_regions_with_values(real, monkeypatch):
    """'서울 N개 구 가운데'의 N 은 그 주 값이 온 구의 수다(/weekly/ 가 count_text('서울 %d개 구' % len(gu)) 로 세는 것과 같다).

    변이(확인): 문장을 '서울 25개 구 가운데서는' 으로 되돌리면 빨개진다.
    픽스처: 실제 ADV 사본의 서울 구 마지막 행(시도와 같은 날로 맞춤)에서 앞의 두 구를 결측(None)으로 둔 부분 응답 주
    (update_adv_data._merge_hist 독스트링, 2026-09-26 감사 #8), 문장 틀은 그 문장이 나오는 1번으로 고정.
    """
    adv, sts = real
    adv = copy.deepcopy(adv)
    S = adv['weekly']['seoul']
    p = adv['weekly']['rows'][-1]['p']
    ma = [0.1] * len(S['regions'])
    ma[0] = ma[1] = None
    S['rows'][-1] = dict(S['rows'][-1], p=p, ma=ma)
    monkeypatch.setattr(P, '_wk', lambda q, n: 1 % n)
    body = P.draft_weekly(adv, sts, shot=False)['body']
    n = sum(v is not None for v in ma)
    assert n == len(S['regions']) - 2 and ('서울 %d개 구 가운데서는' % n) in body, _text(body)[:400]
