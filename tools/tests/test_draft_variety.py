# -*- coding: utf-8 -*-
"""블로그 초안 반복률 — 같은 카테고리 이웃 회차끼리 뼈대가 같은 문장이 WARN(25%) 아래인지(2026-10-15).

배경: 발행 글 18편 측정에서 직전 글과 뼈대가 같은 문장이 주간 42~46%·지역 편 29~43%였다(사이클 2~7%, 도시 1%).
네이버는 같거나 거의 같은 글·자동 생성 틀을 거른다. 생성기가 매주 같은 안내 문장을 깔던 탓이라, 안내 문장은
지우거나 회차마다 돌리고(_wk·_rot), 지역 편의 CD 금리 문장(그 주 모든 지역 편이 같은 숫자)은 뺐다.

무엇을 깨뜨리면 빨개지나(실제로 확인): _wk 가 늘 0 을 돌려주면 주간 시험이, draft_zone 의 k3 를 0 으로 고정하면
지역 편 시험이, CD 문장을 되살리면 금리 시험이, title_warnings 가 빈 목록만 돌려주면 제목 시험이 빨개진다.
교대 직후 첫 주간(10-19 조사분)이 옛 문구(0번)를 받으면 전환 시험이 빨개진다(ROT_SHIFT 를 0 으로 바꿔 확인).
픽스처: 저장소의 실제 ADV 로 이웃한 두 주(지난 회차는 _cut_weekly)와 이웃 회차 지역 편(캡처·썸네일·RSS 는 끈다).
"""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import blog_similarity as B  # noqa: E402
import make_naver_post as P  # noqa: E402


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    return P.M.load()


def _s(d):
    return B.sentences(B.html_paras(d['body']))


def test_weekly_neighbours_do_not_repeat(env):
    adv, sts = env
    a = P.draft_weekly(P._cut_weekly(adv, 1), sts, shot=False)
    b = P.draft_weekly(adv, sts, shot=False)
    assert B.overlap(_s(a), _s(b)) < B.WARN, [B.skeleton(x) for x in _s(b) if B.skeleton(x) in set(map(B.skeleton, _s(a)))]


def test_zone_neighbours_do_not_repeat(env):
    adv, sts = env
    zs = [r for r in adv['sido']['zones'] if not r.get('agg')]
    rates = [B.overlap(_s(P.draft_zone(adv, sts, zs[i], 7 + i, len(zs))), _s(P.draft_zone(adv, sts, zs[i + 1], 8 + i, len(zs))))
             for i in range(len(zs) - 1)]
    assert max(rates) < B.WARN, [round(x * 100) for x in rates]


def test_zone_has_no_rate_sentence(env):
    adv, sts = env
    zs = [r for r in adv['sido']['zones'] if not r.get('agg')]
    body = P.draft_zone(adv, sts, zs[0], 7, len(zs))['body']
    assert 'CD 91일물' not in body and '금리가 걸립니다' not in body


def test_title_warnings_catch_generic_words():
    assert P.title_warnings('2027년 광주·전남 아파트 공급물량 전망, 강보합 국면이지만 내년 2분기부터 입주가 크게 줄어듭니다')
    assert not P.title_warnings('2027년 경남 부동산 전망, 공급물량이 절반에 못 미쳐 오름세가 이어집니다')
    assert not P.title_warnings('[한국부동산원] 주간 아파트가격 동향(10월 둘째 주) | 경기는 가장 크게 올랐습니다')


def test_skeleton_ignores_numbers_and_regions():
    assert B.skeleton('서울 매매는 +0.16% 올랐습니다.') == B.skeleton('경기 매매는 +0.26% 올랐습니다.')
    assert B.overlap(['서울 매매는 +0.10%입니다.'], ['부산 매매는 -0.02%입니다.', '완전히 다른 문장 하나입니다.']) == 0.5


def test_first_weekly_after_the_switch_does_not_reuse_the_old_wording():
    """0번 문장은 교대 이전 문구다. 10-15 에 옛 틀로 낸 주간 글 다음 회차(10-19 조사분)가 0번이면 다시 겹친다."""
    assert P._wk('2026-10-19', 3) != 0


def _paras(body):
    return re.findall(r'<p>(.*?)</p>', body, re.S)


def _tokens(u, html):
    """배수 표기 u('1.1배'·'5%')가 온전한 숫자로 나온 횟수. 다른 숫자의 꼬리('+0.07%'·'4.7%' 안의 '7%')는 세지 않는다."""
    return len(re.findall(r'(?<![\d.,+\-−])' + re.escape(u), re.sub(r'<[^>]+>', '', html)))


def _tail_twins(adv):
    """주간 변동률 숫자가 퍼센트 배수(um<1 → '5%'·'57%')로 끝나는 주를 모든 지역에 만든 사본. 2026-09-21(세종 전세 +0.07% —
    부족분 대비 '4.7%' 와 함께 '7%' 두 번)·08-03(서울 '(전주 +0.25%)'·'전세가 +0.25%')처럼, 본문을 부분 문자열로 세던 옛 시험이
    배수를 두 번 말한 것으로 잘못 센 상태다(실데이터 80주 되감기에서 13주)."""
    adv = copy.deepcopy(adv)
    W = adv['weekly']
    cur, prv = W['rows'][-1], W['rows'][-2]
    for r in adv['sido']['zones']:
        u = P.umx(r['um']) if r.get('um') is not None else ''
        if r['z'] in W['regions'] and re.match(r'^\d+%$', u):
            i, v = W['regions'].index(r['z']), int(u[:-1]) / 100.0
            cur['ma'][i], cur['je'][i], prv['ma'][i] = 1 + v, v, 2 + v     # '+1.57%'·'+0.57%'·'(전주 +2.57%)'
    return adv


def test_zone_says_the_unsold_multiple_once(env):
    """지역 편이 미분양 배수(예: 1.1배)를 두 번 말하지 않는다(10-17 대표 리뷰: 경남 편 '미분양 1.1배'가 두 절에 나왔다).

    문단 단위로 본다: 순위 문단('N개 시도 가운데 … 번째')에는 그 지역 배수가 없고, 미분양 경고 지역의 미분양 문단에는 배수가 꼭 한 번
    있다(경고가 아닌 지역의 미분양 문단에는 없다). 예전 시험은 본문 전체를 부분 문자열로 세어(body.count('7%')) 주간 변동률
    '+0.07%'·부족분 대비 '4.7%' 의 꼬리까지 세었다 — 배수를 두 번 말하지 않아도 주간 값 끝자리만으로 게이트가 막혔다(전수리뷰
    BL1-1·T1-1). um 이 None 인 지역(sido_zones 가 허용한다)은 순위 문단 자체가 없어야 하고, umx(None) 을 부르지 않는다.

    변이(실제로 확인): 순위 문장에 배수를 되살리면(6215ffd 이전 '분기 적정물량과 견주면 <b>%s</b>로 …') 실데이터·사본 모두 빨개진다.
    픽스처: 저장소 실제 ADV 의 시도 전부(실데이터) + 주간 변동률 숫자가 퍼센트 배수로 끝나는 사본(_tail_twins — 옛 시험이 헛빨강을
    내던 상태, 이 시험은 초록이어야 한다). 두 갈래(경고 지역·아닌 지역)가 늘 돌도록, 데이터에 경고 지역이 없으면 실제 시도 한 줄을
    경고로 바꾼 합성 행을, um 이 None 인 지역이 없으면 그런 합성 행을 더한다.
    """
    adv, sts = env
    for case in (adv, _tail_twins(adv)):
        zs = [r for r in case['sido']['zones'] if not r.get('agg')]
        rows = list(zs)
        base = next(r for r in zs if r.get('um') is not None)
        if not any(r.get('uwarn') and r.get('unsold') and r.get('um') is not None for r in zs):
            rows.append(dict(base, uwarn=True, um=max(base['um'], 1.2), unsold=max(base.get('unsold') or 0, 1000)))
        if not any(r.get('um') is None for r in zs):
            rows.append(dict(base, um=None, uwarn=False))
        seen = {'warn': 0, 'plain': 0, 'none': 0}
        for i, r in enumerate(rows):
            ps = _paras(P.draft_zone(case, sts, r, 7 + i, len(zs))['body'])
            rank = [p for p in ps if '번째' in p and '개 시도' in p]
            if r.get('um') is None:
                assert not rank, (r['z'], rank)
                seen['none'] += 1
                continue
            u = P.umx(r['um'])
            assert len(rank) == 1, (r['z'], rank)
            assert _tokens(u, rank[0]) == 0, ('순위 문단이 배수를 다시 말한다', r['z'], u, rank[0])
            unsold = [p for p in ps if r.get('unsold') and '<b>%s세대</b>' % P.num(r['unsold']) in p]
            if r.get('uwarn') and r.get('unsold'):
                assert len(unsold) == 1 and _tokens(u, unsold[0]) == 1, (r['z'], u, unsold)
                seen['warn'] += 1
            elif unsold:
                assert len(unsold) == 1 and _tokens(u, unsold[0]) == 0, (r['z'], u, unsold)
                seen['plain'] += 1
        assert all(seen.values()), seen
