# -*- coding: utf-8 -*-
"""주간 공유 카드 주소에 발표일 판을 붙인다(홈 마케팅 검수 A7·VIRAL-2, 2026-09-27).

재현하는 실제 상태(2026-09-26 curl): /weekly/ 의 og:image 가 매주 같은 주소(share/weekly-map.png)라, 이미지 주소로
미리보기를 보관하는 카카오톡·네이버에는 지난주 지도가 붙어 나올 수 있었다. og:description 은 이미 '9/21 조사 ·
9/24 발표'처럼 날짜를 담는데 그림만 주소가 같았다.

카드는 make_weekly_share 가 매주 같은 파일 이름으로 덮어쓰고(감시가 그 주소에서 조사일을 읽는다), /weekly/ 생성기가
og:image·twitter:image 주소에 카드 머리의 발표일을 ?v= 로 붙인다. 두 생성기는 배치에서 따로 돌므로 날짜를 같은
함수(make_weekly_page.share_version)로 셈하고, 같은 데이터에서 같은 값이 나오는지를 여기서 본다.
"""
import copy
import glob
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_weekly_page as MW  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 픽스처 주차: 실제 데이터와 겹치지 않는 먼 월요일(조사일)과 그 목요일(발표일). 날짜 셈은 여기서 따로 적어 대조한다.
SURVEY, RELEASE = '2030-01-07', '2030-01-10'


def _fixture():
    """저장소 data.js 의 주간 계열에 최신 주차 하나를 덧붙인다(값은 직전 주 그대로, 날짜만 다음 조사일)."""
    W, Q = MW.load()
    W = copy.deepcopy(W)
    for key in ('rows',):
        W[key].append(dict(W[key][-1], p=SURVEY))
    for part in ('sgg', 'seoul'):
        if part in W and W[part].get('rows'):
            W[part]['rows'].append(dict(W[part]['rows'][-1], p=SURVEY))
    return W, Q


def _metas(html):
    og = re.findall(r'<meta property="og:image" content="([^"]*)">', html)
    tw = re.findall(r'<meta name="twitter:image" content="([^"]*)">', html)
    return og, tw


def test_og_image_url_carries_the_release_date_of_the_card():
    """새 주차가 들어오면 og:image·twitter:image 주소가 그 주 발표일(?v=)로 바뀐다.

    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): render 에서 put_share_image 를 빼면, share_version 이 발표일 대신
    조사일(p)을 돌려주면, put_share_image 가 W['rows'][0](첫 주차)을 읽으면 빨개진다.
    픽스처: 저장소 weekly/index.html 뼈대와 data.js 주간 계열에 먼 미래 주차 하나를 덧붙인 것.
    """
    W, Q = _fixture()
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    og, tw = _metas(MW.render(page, W, Q))
    want = MW.SHARE_IMG + '?v=' + RELEASE
    assert og == [want] and tw == [want], 'og:image %s · twitter:image %s — 기대 %s' % (og, tw, want)


def test_card_and_page_use_the_same_release_date(tmp_path, monkeypatch):
    """같은 데이터로 공유 카드와 /weekly/ 를 구우면 카드 머리의 발표일(PNG 메타 agongmap-pub)과 og:image 의 판이 같다.

    두 생성기가 날짜를 따로 셈하면 카드 그림과 미리보기 주소의 판이 갈린다(배치에서 둘은 따로 돈다).
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): make_weekly_share._pubdate 를 자체 셈(+4일)으로 바꾸거나, 카드가
    W['rows'][-2] 를 그리게 하면 빨개진다.
    픽스처: 위와 같은 먼 미래 주차. 카드는 임시 폴더에 굽는다(저장소의 share/ 는 건드리지 않는다).
    """
    pytest.importorskip('PIL')
    import make_weekly_share as WS
    from PIL import Image
    W, Q = _fixture()
    monkeypatch.setattr(WS, 'load_weekly', lambda: W)
    monkeypatch.setattr(WS, 'ROOT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_weekly_share.py'])
    (tmp_path / 'share').mkdir()
    WS.main()
    meta = Image.open(str(tmp_path / 'share' / 'weekly-map.png')).text
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    og, _ = _metas(MW.render(page, W, Q))
    assert meta.get('agongmap-basis') == SURVEY, meta
    assert og == [MW.SHARE_IMG + '?v=' + meta.get('agongmap-pub', '?')], (
        '카드에 찍힌 발표일(%s)과 og:image 판(%s)이 다르다' % (meta.get('agongmap-pub'), og))


def test_no_page_points_at_the_weekly_card_without_a_version():
    """저장소의 어느 페이지도 주간 카드를 판 없는 주소로 미리보기 이미지로 쓰지 않는다(홈은 og-brand.png 를 쓴다).

    무엇을 깨뜨리면 빨개지나: 생성기를 돌린 뒤 weekly/index.html 의 og:image 에서 ?v= 를 지우면, 또는 손 페이지의
    og:image 를 share/weekly-map.png 로 바꾸면 빨개진다(실제로 확인). 픽스처: 저장소의 모든 HTML(생성 페이지 포함).
    """
    bad = []
    for p in glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True):   # '**' 는 루트 홈도 담는다
        if os.sep + 'drafts' + os.sep in p:
            continue
        og, tw = _metas(io.open(p, encoding='utf-8').read())
        bad += ['%s: %s' % (os.path.relpath(p, ROOT), u) for u in og + tw
                if 'weekly-map.png' in u and not re.search(r'weekly-map\.png\?v=\d{4}-\d{2}-\d{2}$', u)]
    assert not bad, '주간 카드를 판 없는 주소로 미리보기에 쓰는 페이지: %s' % bad
