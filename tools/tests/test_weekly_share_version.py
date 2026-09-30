# -*- coding: utf-8 -*-
"""주간 공유 카드 주소에 발표일 판을 붙인다(홈 마케팅 검수 A7·VIRAL-2, 2026-09-27).

재현하는 실제 상태(2026-09-26 curl): /weekly/ 의 og:image 가 매주 같은 주소(share/weekly-map.png)라, 이미지 주소로
미리보기를 보관하는 카카오톡·네이버에는 지난주 지도가 붙어 나올 수 있었다. og:description 은 이미 '9/21 조사 ·
9/24 발표'처럼 날짜를 담는데 그림만 주소가 같았다.

카드는 make_weekly_share 가 매주 같은 파일 이름으로 덮어쓰고(감시가 그 주소에서 조사일을 읽는다), /weekly/ 생성기가
og:image·twitter:image 주소에 카드 머리의 발표일을 ?v= 로 붙인다. 두 생성기는 배치에서 따로 돌므로 날짜를 같은
함수(make_weekly_page.share_version)로 셈하고, 같은 데이터에서 같은 값이 나오는지를 여기서 본다.

카드 파일의 경로도 같은 대상이다. 카드 생성기가 쓰는 파일, 페이지 og:image 가 가리키는 파일, 감시가 조사일을 읽는
파일이 모두 make_weekly_page.SHARE_REL 하나에서 나오는지를 본다. 처음 판은 날짜만 묶고 경로는 두 생성기가 따로
적었는데, og:image 를 저장소에 없는 파일로 바꿔도 이 파일의 시험이 모두 초록이었다(A7 검토 지적, 2026-09-27).
"""
import copy
import glob
import io
import os
import re
import sys
from urllib.parse import urlsplit

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_weekly_page as MW  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DOMAIN = io.open(os.path.join(ROOT, 'CNAME'), encoding='utf-8').read().strip()   # 정식 도메인(GitHub Pages)

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


def fake_card(path, **meta):
    """PIL 없이 tEXt 메타만 든 PNG 를 쓴다 — 페이지 생성기(png_text)는 그림이 아니라 메타만 읽는다."""
    import zlib
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    def chunk(typ, data):
        return len(data).to_bytes(4, 'big') + typ + data + zlib.crc32(typ + data).to_bytes(4, 'big')
    body = b''.join(chunk(b'tEXt', k.replace('_', '-').encode() + b'\x00' + v.encode()) for k, v in meta.items())
    with open(path, 'wb') as f:
        f.write(MW.PNG_SIG + body + chunk(b'IEND', b''))


def test_og_image_url_carries_the_version_the_card_was_baked_with(tmp_path):
    """og:image·twitter:image·공유 버튼 그림 주소의 판(?v=)은 디스크의 카드가 **실제로 그린** 발표일(PNG 메타 agongmap-pub)이다.

    새 주차 카드가 구워졌으면 그 주 발표일, 카드 생성이 실패해 지난 카드가 남았으면 지난 발표일 — 새 판 주소가 옛 그림을
    가리키지 않는다(전수리뷰 #85: 카카오톡·네이버가 옛 그림을 새 판 주소에 붙여 그 주 내내 내보냈다).
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): share_img 가 데이터의 발표일(share_version(W 최신 p))을 쓰면 두 번째
    단정이 빨강, render 에서 put_share_image 를 빼면 첫 단정이 빨강, share_payload 의 img 를 데이터 판으로 되돌리면 빨강.
    픽스처: 저장소 weekly/index.html 뼈대와 data.js 주간 계열에 먼 미래 주차를 덧붙인 것. 카드는 임시 폴더에 메타만 든
    PNG 로 둔다 — ① 그 주 카드가 구워진 회차, ② 카드 생성이 실패해 지난주 카드가 남은 회차.
    """
    W, Q = _fixture()
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    card = tmp_path.joinpath(*MW.SHARE_REL.split('/'))

    fake_card(card, agongmap_basis=SURVEY, agongmap_pub=RELEASE)
    og, tw = _metas(MW.render(page, W, Q, root=str(tmp_path)))
    want = MW.SHARE_IMG + '?v=' + RELEASE
    assert og == [want] and tw == [want], 'og:image %s · twitter:image %s — 기대 %s' % (og, tw, want)

    old = '2029-12-27'
    fake_card(card, agongmap_basis='2029-12-24', agongmap_pub=old)
    og, tw = _metas(MW.render(page, W, Q, root=str(tmp_path)))
    want = MW.SHARE_IMG + '?v=' + old
    assert og == [want] and tw == [want], '카드는 %s 판인데 og:image 가 %s 를 가리킨다' % (old, og)
    assert MW.share_payload(W, root=str(tmp_path))['img'] == want


def _rel(url):
    """미리보기 주소 → 저장소 안 상대 경로('share/…png'). 쿼리(?v=)는 파일 이름이 아니다."""
    return urlsplit(url).path.lstrip('/')


def test_card_and_page_use_the_same_release_date_and_file(tmp_path, monkeypatch):
    """같은 데이터로 공유 카드와 /weekly/ 를 구우면, og:image 가 가리키는 **바로 그 파일**에 카드가 구워지고 그 카드
    머리의 발표일(PNG 메타 agongmap-pub)이 og:image 의 판(?v=)과 같다.

    두 생성기가 날짜나 경로를 따로 셈하면 카드 그림과 미리보기 주소의 판이 갈리거나, 미리보기가 없는 파일을
    가리킨다(배치에서 둘은 따로 돈다). 카드는 og:image 주소의 경로로 열어 본다 — 시험이 경로를 따로 적으면 두
    생성기의 불일치를 시험이 덮는다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): make_weekly_page.SHARE_IMG 를 저장소에 없는
    'https://www.agongmap.co.kr/share/weekly-card.png' 로 바꾸면, make_weekly_share 의 out 을
    os.path.join(ROOT, 'share', 'weekly-map-live.png') 로 따로 적으면, _pubdate 를 자체 셈(+4일)으로 바꾸거나
    카드가 W['rows'][-2] 를 그리게 하면 빨개진다.
    픽스처: 위와 같은 먼 미래 주차. 카드는 임시 폴더에 굽는다(저장소의 share/ 는 건드리지 않는다).
    """
    pytest.importorskip('PIL')
    import make_weekly_share as WS
    from PIL import Image
    W, Q = _fixture()
    monkeypatch.setattr(WS, 'load_weekly', lambda: W)
    monkeypatch.setattr(WS, 'ROOT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_weekly_share.py'])
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    og, tw = _metas(MW.render(page, W, Q))
    assert len(og) == 1 and tw == og, 'og:image %s · twitter:image %s' % (og, tw)
    card = tmp_path.joinpath(*_rel(og[0]).split('/'))
    card.parent.mkdir(parents=True, exist_ok=True)
    WS.main()
    og, tw = _metas(MW.render(page, W, Q, root=str(tmp_path)))   # 판은 구워진 카드에서 읽는다(#85)
    wrote = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob('*.png'))
    assert card.is_file(), (
        'og:image 가 가리키는 %s 에 카드가 없다 — 카드 생성기가 쓴 파일: %s' % (_rel(og[0]), wrote))
    meta = Image.open(str(card)).text
    assert meta.get('agongmap-basis') == SURVEY, meta
    assert og == [MW.SHARE_IMG + '?v=' + meta.get('agongmap-pub', '?')], (
        '카드에 찍힌 발표일(%s)과 og:image 판(%s)이 다르다' % (meta.get('agongmap-pub'), og))


def test_card_generator_restamps_the_page_and_home_data(tmp_path, monkeypatch):
    """배치 순서(페이지·홈 데이터 → 게이트 → 카드) 그대로: 페이지와 data-core 는 카드보다 먼저 구워져 지난 카드 판을
    가리키고, 카드 생성기가 새 카드를 구운 직후 restamp_share 로 같은 회차 안에서 주소를 새 판으로 고친다(전수리뷰 #85).
    카드 생성이 실패하면 이 단계에 닿지 않아 주소는 지난 판(= 남은 그림의 판)에 머문다 — 위 시험이 그 경우를 본다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): make_weekly_share.main 에서 restamp_share 호출을 지우면 빨강(페이지가 지난 판에
    남는다). restamp_share 가 data-core.js 를 빼면 빨강.
    픽스처: 임시 저장소 뿌리에 지난주 카드(메타만 든 PNG)·그 판으로 구운 weekly/index.html·그 판 주소를 담은 data-core.js 를
    두고, 먼 미래 주차 데이터로 카드 생성기를 돌린다.
    """
    pytest.importorskip('PIL')
    import make_weekly_share as WS
    W, Q = _fixture()
    old = '2029-12-27'
    fake_card(tmp_path.joinpath(*MW.SHARE_REL.split('/')), agongmap_basis='2029-12-24', agongmap_pub=old)
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    (tmp_path / 'weekly').mkdir()
    io.open(str(tmp_path / 'weekly' / 'index.html'), 'w', encoding='utf-8', newline='').write(
        MW.render(page, W, Q, root=str(tmp_path)))
    (tmp_path / 'data-core.js').write_text('const ADV={"share":{"img":"%s?v=%s"}};' % (MW.SHARE_IMG, old),
                                           encoding='utf-8')
    assert _metas((tmp_path / 'weekly' / 'index.html').read_text(encoding='utf-8'))[0] == [MW.SHARE_IMG + '?v=' + old]

    monkeypatch.setattr(WS, 'load_weekly', lambda: W)
    monkeypatch.setattr(WS, 'ROOT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_weekly_share.py'])
    WS.main()
    want = MW.SHARE_IMG + '?v=' + RELEASE
    html = (tmp_path / 'weekly' / 'index.html').read_text(encoding='utf-8')
    og, tw = _metas(html)
    assert og == [want] and tw == [want], '카드를 새로 구웠는데 페이지가 %s 를 가리킨다' % og
    assert '?v=' + old not in html, '공유 버튼 그림 주소가 지난 판에 남았다'
    assert want in (tmp_path / 'data-core.js').read_text(encoding='utf-8'), '홈 데이터의 공유 그림 주소가 지난 판에 남았다'


def test_watchdog_reads_the_card_the_page_points_at(monkeypatch):
    """감시(check_freshness.live_card_basis)가 조사일을 읽는 주소가 /weekly/ og:image 주소(판 쿼리를 뺀 것)와 같다.

    감시가 다른 파일을 읽으면 라이브 미리보기 카드가 몇 주째 옛 주차여도 감시는 초록이다(2026-08-06 카드 3주
    정지와 같은 모양). 감시는 이 생성기의 SHARE_REL·png_text_bytes 를 그대로 쓴다(전수 리뷰 통합 — 예전엔 주소와 PNG
    읽기를 따로 적었다). 이 시험은 감시가 다시 손 주소로 돌아가는 것을 막는다.
    무엇을 깨뜨리면 빨개지나(실제로 확인): check_freshness 의 카드 주소를 손 문자열 '/share/weekly-map2.png' 로 바꾸면
    빨개진다.
    픽스처: 네트워크 없이 urlopen 을 가로채 요청 주소만 모은다(빈 응답이라 감시는 None 을 돌려준다).
    """
    import check_freshness as C
    seen = []

    class _Resp:
        def read(self):
            return b''

    def fake(req, *a, **k):
        seen.append(getattr(req, 'full_url', req))
        return _Resp()

    monkeypatch.setattr(C.urllib.request, 'urlopen', fake)
    assert C.live_card_basis() is None
    assert seen == [MW.SHARE_IMG], '감시가 읽는 카드 %s ≠ /weekly/ og:image %s' % (seen, MW.SHARE_IMG)


def test_no_page_points_at_the_weekly_card_without_a_version():
    """저장소의 어느 페이지도 주간 카드를 판 없는 주소로 미리보기 이미지로 쓰지 않고, /weekly/ 의 og:image·
    twitter:image 는 정식 도메인(CNAME) 위의, 저장소에 실제로 있는 파일을 가리킨다(홈은 og-brand.png 를 쓴다).

    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 생성기를 돌린 뒤 weekly/index.html 의 og:image 에서 ?v= 를 지우면,
    손 페이지의 og:image 를 share/weekly-map.png 로 바꾸면, make_weekly_page.SHARE_IMG 를 저장소에 없는
    share/weekly-card.png 로 바꾸고 make_weekly_page 를 돌리면, SITE 를 다른 도메인으로 바꾸면 빨개진다.
    픽스처: 저장소의 모든 HTML(생성 페이지 포함)과 저장소의 share/ 파일. 배치는 카드를 이 시험 뒤에 굽지만
    파일 이름이 매주 같으므로 저장소에 이미 있다 — 카드 파일 이름을 바꾸는 변경은 새 카드를 먼저 올려야 한다.
    """
    card = MW.SHARE_REL
    bad = []
    for p in glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True):   # '**' 는 루트 홈도 담는다
        if os.sep + 'drafts' + os.sep in p:
            continue
        og, tw = _metas(io.open(p, encoding='utf-8').read())
        bad += ['%s: %s' % (os.path.relpath(p, ROOT), u) for u in og + tw
                if _rel(u) == card and not re.search(r'\?v=\d{4}-\d{2}-\d{2}$', u)]
    assert not bad, '주간 카드를 판 없는 주소로 미리보기에 쓰는 페이지: %s' % bad
    og, tw = _metas(io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read())
    assert len(og) == 1 and len(tw) == 1, (og, tw)
    for u in og + tw:
        assert urlsplit(u).netloc == DOMAIN, '/weekly/ 미리보기 이미지가 정식 도메인(%s) 밖: %s' % (DOMAIN, u)
        assert os.path.isfile(os.path.join(ROOT, *_rel(u).split('/'))), (
            '/weekly/ 미리보기 이미지가 저장소에 없는 파일을 가리킨다: %s' % u)
