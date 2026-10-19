# -*- coding: utf-8 -*-
"""공유 카드(주간 share/weekly-map.png·월간 share/monthly-card.png)와 /monthly/ 공유 문구가 그리는 글자·색 기준·범례 방향.

카드는 게이트 뒤에서 굽는 PNG 라 화면 이름 시험(test_display_name)·지도 시험이 보지 못했다. 여기서는 그림 대신 그리는
호출(ImageDraw.text·cell_bg)을 가로채 본다(전수리뷰 X1-4·X2-3·Z2-3·Z2-11·X2-9·Z2-7).

픽스처: data.js 의 실제 주간·월간 계열에서 마지막 회차만 고쳐, 판정 단위 키와 화면 이름이 다른 지역(DISPLAY_NAME 의 키,
지금은 '전남광주')을 그 회차 '가장 많이 오른 곳'으로 둔 합성 회차. 120개월 중 17개월이 실제로 이 모양이었다
(전남광주가 매매 변동 상위에 든 달 — 2022-09 '… 전남광주 -1.23%').
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
pytest.importorskip('PIL')
from PIL import ImageDraw  # noqa: E402

import make_monthly_page as MP  # noqa: E402
import make_monthly_share as MS  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import make_weekly_share as WS  # noqa: E402
import sido_zones as SZ  # noqa: E402

KEYS = sorted(SZ.DISPLAY_NAME)


def _top_key(regs):
    """화면 이름이 따로 있는 판정 단위 키 가운데 이 계열에 있는 것 하나."""
    ks = [k for k in KEYS if k in regs]
    assert ks, 'DISPLAY_NAME 의 키가 계열 지역에 하나도 없다 — 픽스처 전제가 바뀌었다'
    return ks[0]


def _bump(rows, regs, key, v=1.5):
    row = rows[-1]
    row['ma'] = [v if r == key else (0.01 if (x is not None) else x) for r, x in zip(regs, row['ma'])]


def _capture(monkeypatch):
    seen = []
    orig = ImageDraw.ImageDraw.text

    def spy(self, xy, text, *a, **k):
        seen.append((xy, text))
        return orig(self, xy, text, *a, **k)
    monkeypatch.setattr(ImageDraw.ImageDraw, 'text', spy)
    return seen


def _weekly():
    W = copy.deepcopy(WS.load_weekly())
    key = _top_key(W['regions'])
    _bump(W['rows'], W['regions'], key)
    return W, key


def _monthly():
    adv, sts = MP.load()
    adv = copy.deepcopy(adv)
    mo = adv['monthly']
    key = _top_key(mo['regions'])
    _bump(mo['rows'], mo['regions'], key)
    return adv, sts, key


def _no_keys(texts, key):
    joined = '\n'.join(texts)
    assert texts, '그린 글자가 없다'
    leaked = [k for k in KEYS if k in joined]
    assert not leaked, '카드가 판정 단위 키를 그대로 그렸다(화면 이름은 SZ.disp): %s' % leaked
    assert SZ.disp(key) in joined, '화면 이름 %s 이 카드에 없다' % SZ.disp(key)


def test_monthly_card_draws_display_names(monkeypatch):
    """월간 카드의 타일 이름·'가장 많이 오른 곳'이 화면 이름(SZ.disp)이다.

    변이(실제로 확인): make_monthly_share.draw 의 '가장 많이 오른 곳' 줄을 items[0][0](키)로, 또는 타일 글자를 name(키)으로
    되돌리면 빨강.
    """
    adv, _, key = _monthly()
    seen = _capture(monkeypatch)
    MS.draw(adv)
    texts = [t for _, t in seen]
    _no_keys(texts, key)
    assert any(t.startswith(SZ.disp(key) + ' ') and t.endswith('%') for t in texts), \
        "'가장 많이 오른 곳' 줄에 화면 이름이 없다: %s" % texts


def test_weekly_card_draws_display_names(monkeypatch):
    """주간 카드의 타일 이름·요약 줄이 화면 이름이다(백로그 46, make_weekly_share 168·182행).

    변이(실제로 확인): make_weekly_share.draw 의 요약 줄 _SZ.disp(r) 를 r 로 되돌리면 빨강.
    """
    W, key = _weekly()
    seen = _capture(monkeypatch)
    WS.draw(W)
    _no_keys([t for _, t in seen], key)


def test_monthly_share_text_uses_display_names():
    """/monthly/ 공유 문구(카카오 피드 description·navigator.share text)의 지역도 화면 이름이다.

    변이(실제로 확인): make_monthly_page.share_payload 를 옛 식 ' · '.join('%s %s' % x for x in top[1]) 로 되돌리면 빨강.
    """
    adv, sts, key = _monthly()
    text = MP.share_payload(adv, sts)['text']
    assert SZ.disp(key) in text, text
    assert not [k for k in KEYS if k in text], text


def test_cards_paint_with_the_home_map_refs(monkeypatch):
    """두 카드의 만색 기준은 홈 지도 정본(make_weekly_page.map_refs = WK_MAP_REF·MO_MAP_REF)을 읽는다(전수리뷰 Z2-11).

    홈 기준을 가상의 값(주간 0.3·월간 0.8)으로 바꾼 상태에서 카드가 cell_bg 에 넘긴 기준을 본다 — 지금 실제 값(0.4·1.0)으로만
    보면 카드가 옛 리터럴을 써도 같아 초록이다.
    변이(실제로 확인): make_weekly_share.draw 의 ref 를 0.4 리터럴로, 또는 make_monthly_share.draw 의 ref 를 1.0 리터럴로 바꾸면 빨강.
    """
    real = MW.map_refs()
    assert set(real) == {'week', 'month'} and all(v > 0 for v in real.values()), real
    fake = {'week': 0.3, 'month': 0.8}
    monkeypatch.setattr(MW, 'map_refs', lambda src=None: dict(fake))
    refs = []
    orig = WS.cell_bg

    def spy(v, ref):
        refs.append(ref)
        return orig(v, ref)
    monkeypatch.setattr(WS, 'cell_bg', spy)
    W, _ = _weekly()
    WS.draw(W)
    assert refs and set(refs) == {fake['week']}, refs
    refs.clear()
    adv, _, _ = _monthly()
    MS.draw(adv)
    assert refs and set(refs) == {fake['month']}, refs


def test_weekly_card_legend_runs_fall_to_rise(monkeypatch):
    """주간 카드 범례는 왼쪽 하락 → 오른쪽 상승(시세 가로축 정본, 2026-10-06 대표 결정 — 전수리뷰 X2-9·Z2-7).

    변이(실제로 확인): LEGEND 를 (('상승', UP), ('하락', DN)) 로 되돌리면 빨강.
    """
    assert [w for w, _ in WS.LEGEND] == ['하락', '상승']
    assert dict(WS.LEGEND) == {'하락': WS.DN, '상승': WS.UP}
    W, _ = _weekly()
    seen = _capture(monkeypatch)
    WS.draw(W)
    xs = {t: xy[0] for xy, t in seen if t in ('하락', '상승')}
    assert set(xs) == {'하락', '상승'}, seen
    assert xs['하락'] < xs['상승'], xs


def test_weekly_page_map_legend_runs_fall_to_rise():
    """/weekly/ 머리 지도 범례(mm-cap)도 하락 → 상승이다 — 홈 주간 구역(같은 시군구 지도)과 같은 방향.

    변이(실제로 확인): make_weekly_page 의 mm-cap 두 span 순서를 상승 먼저로 되돌리면 빨강.
    """
    import re
    W, Q = MW.load()
    html = MW.build(W, Q)[0]
    m = re.search(r'<div class="mm-cap">(.*?)</div>', html, re.S)
    assert m, 'mm-cap 범례가 없다'
    words = [w for w in re.findall(r'</i>([^<]+)</span>', m.group(1)) if w in ('하락', '상승')]
    assert words == ['하락', '상승'], words
