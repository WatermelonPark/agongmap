# -*- coding: utf-8 -*-
"""지역 공유 카드(share/zone-<키>.png, make_zone_cards — 사람이 돌리는 도구)는 화면 이름 정본과 정본 용어를 그린다(전수리뷰 Z1-5·P-2).

재현한 실제 상태(2026-10-18): 도구가 zone/ 디렉터리 이름(판정 단위 키)을 그대로 그려, /zone/전남광주/ 의 공유 미리보기(og:image)가
제목('광주·전남')과 다른 '전남광주' 카드였다. 19장 공통 부제는 10-06 에 버린 이름 '필요한 집 vs 들어올 집'이었다. 도구를 다시 돌려도 같은
카드가 나왔고, test_display_name 은 HTML 글자만 보아 그림을 잡지 못했다. og:image 주소에 판(?v=)이 없어 다시 구운 카드도 카카오톡·
네이버가 보관한 옛 미리보기에 닿지 않았다.
"""
import hashlib
import io
import glob
import os
import re
import sys
import urllib.parse

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as P  # noqa: E402
import make_zone_cards as ZC  # noqa: E402
import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def test_card_draws_the_display_name_and_the_canon_subtitle(tmp_path, monkeypatch):
    """도구가 그리는 글자: 큰 이름은 SZ.disp(키), 부제는 정본 용어('적정물량'). 파일 이름은 키 그대로(og:image 가 키로 찾는다).
    변이(실제로 확인): make() 가 label(name) 대신 name(키)을 그리게 되돌리면, SUB 를 옛 '필요한 집 vs 들어올 집'으로 되돌리면 빨개진다.
    픽스처: DISPLAY_NAME 의 키마다(지금 '전남광주') 임시 폴더에 한 장씩 굽고 ImageDraw.text 를 가로채 그린 글자를 모은다. 이름이 키와
    같은 지역(서울)도 한 장 — 바뀌지 않는 갈래."""
    drawn = []
    real = ImageDraw.ImageDraw.text

    def spy(self, xy, text, *a, **kw):
        drawn.append(text)
        return real(self, xy, text, *a, **kw)
    monkeypatch.setattr(ImageDraw.ImageDraw, 'text', spy)
    monkeypatch.setattr(ZC, 'OUT_DIR', str(tmp_path))
    keys = sorted(SZ.DISPLAY_NAME) + ['서울']
    assert SZ.DISPLAY_NAME and SZ.disp('서울') == '서울'
    for k in keys:
        drawn.clear()
        out = ZC.make(k)
        assert os.path.basename(out) == 'zone-%s.png' % k
        assert SZ.disp(k) in drawn and ZC.SUB in drawn, (k, drawn)
        if SZ.disp(k) != k:
            assert not any(k in t for t in drawn), (k, drawn)
    assert '적정물량' in ZC.SUB and not any(t in ZC.SUB for t in ('필요', '수요', '과잉'))


def test_committed_cards_match_the_tool():
    """저장소에 커밋된 카드가 지금 도구의 글자로 구운 것이다 — 카드는 배치가 굽지 않아(사람이 돌린다), 도구만 고치고 다시 돌리지 않으면
    옛 카드가 그대로 퍼진다. 도구가 PNG 글 칸에 싣는 label·sub 를 읽어 SZ.disp(키)·ZC.SUB 와 대조하고, 판정 단위마다 한 장씩 있는지 본다.
    변이(실제로 확인): 옛 도구로 구운 share/zone-전남광주.png(글 칸 없음·'전남광주')를 되돌려 놓으면, SUB 만 바꾸고 카드를 다시 굽지 않으면
    빨개진다. 지역 구성이 바뀌어(판정 단위 키) 카드가 모자라도 빨개진다 — 그때는 make_zone_cards 를 다시 돌린다.
    픽스처: 저장소 share/zone-*.png(19장)."""
    cards = {os.path.basename(p)[len('zone-'):-len('.png')]: p for p in glob.glob(os.path.join(ROOT, 'share', 'zone-*.png'))}
    assert set(cards) == set(SZ.ORDER), sorted(set(cards) ^ set(SZ.ORDER))
    for k, p in sorted(cards.items()):
        t = Image.open(p).text
        assert (t.get('label'), t.get('sub')) == (SZ.disp(k), ZC.SUB), (k, t)


def test_report_og_image_carries_the_card_version():
    """리포트 og:image 는 그 지역 카드 주소에 카드 내용 해시(?v=8자리)를 붙인다 — 다시 구운 카드가 보관된 미리보기를 대신하게. 카드가 없는
    자리(허브 '시도별 공급')는 브랜드 카드.
    변이(실제로 확인): zone_card 가 ?v= 를 빼면 빨개진다.
    픽스처: 저장소 share/zone-<키>.png 와 head() 가 구운 머리."""
    for z in sorted(SZ.DISPLAY_NAME) + ['서울']:
        with open(os.path.join(ROOT, 'share', 'zone-%s.png' % z), 'rb') as f:
            v = hashlib.sha1(f.read()).hexdigest()[:8]
        want = '%s/share/zone-%s.png?v=%s' % (P.SITE, urllib.parse.quote(z), v)
        h = P.head(z, 'd', 't')
        assert re.search(r'<meta property="og:image" content="([^"]*)">', h).group(1) == want, z
    hub = P.head('시도별 공급', 'd', 't', url=P.SITE + '/zone/', crumb=False, desk='read')
    assert re.search(r'<meta property="og:image" content="([^"]*)">', hub).group(1) == P.SITE + '/og-brand.png'
