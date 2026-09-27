# -*- coding: utf-8 -*-
"""홈 첫 화면 글꼴 서브셋(홈 마케팅 검수 B11·MOB-2, 2026-09-27)을 고정한다.

재현한 실제 상태: CDN Pretendard 가변 글꼴(dynamic-subset)이 첫 화면 글자를 덮느라 17조각(약 436KB)을 받았고, Chromium
망 속도 모사(CPU 4배 감속, 375px)에서 글꼴을 막은 경우보다 지도 완성이 일반 4G 3.4초·느린 4G 3.1초 늦었다(요청서 기준
0.5초). 홈이 쓰는 글자만 담은 서브셋(글자폭 표 HVAR 추가)을 자체 호스팅·preload 해 고쳤다. tools/make_home_font.py 가
webfonts/home-<해시>.woff2 와 index.html 의 HOME_FONT 구간을 함께 굽는다.

이 구조가 조용히 망가지는 길은 셋이다 — 모두 화면은 멀쩡하고(다음 글꼴 CDN 이 그린다) 느려지기만 한다.
  ① 홈 문구에 새 글자를 넣고 도구를 안 돌림 → 그 글자 때문에 CDN 조각을 다시 받고 재배치가 되살아난다.
  ② preload 와 @font-face 가 다른 파일을 가리키거나 파일이 없음 → preload 가 버려지고 글꼴이 두 번 오거나 안 온다.
  ③ app.css body 글꼴 목록이 바뀌었는데 홈 목록은 옛것 → 홈만 다른 글꼴 차례로 그린다.
글꼴 파일 안(cmap)은 fonttools 없이 못 읽으므로(woff2 는 brotli) 도구가 cmap 에서 만든 unicode-range 를 대신 믿는다.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import make_home_font as F  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _html():
    return dict(HS.home_files())['index.html']


def _block():
    h = _html()
    assert h.count(F.START) == 1 and h.count(F.END) == 1, 'index.html 에 HOME_FONT 구간이 하나 있어야 한다'
    return re.search(re.escape(F.START) + r'(.*?)' + re.escape(F.END), h, re.S).group(1)


def test_preload_and_font_face_point_to_the_same_existing_file():
    """preload 가 @font-face 와 같은 파일을 같은 방식(as=font·type·crossorigin)으로 받고, 그 파일이 저장소에 있다.

    preload 는 우선순위를 낮춘다(fetchpriority="low") — 기본 우선순위면 느린 4G 에서 글꼴이 첫 배치보다 먼저 와 FCP·h1 이
    약 1.5초 늦는 회차가 5회 중 3회였다(낮추면 1회).
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): preload 에서 crossorigin 을 빼면(글꼴 요청은 CORS 라 preload 가 버려지고
    두 번 받는다), fetchpriority="low" 를 빼면, src 의 파일 이름을 바꾸면(없는 파일), 구간을 통째로 비우면.
    픽스처: 저장소 index.html 의 HOME_FONT 구간과 webfonts/ 폴더.
    """
    b = _block()
    pre = re.findall(r'<link rel="preload" href="(/webfonts/home-[0-9a-f]+\.woff2)" as="font" type="font/woff2" crossorigin'
                     r' fetchpriority="low">', b)
    src = set(re.findall(r'src:url\((/webfonts/home-[0-9a-f]+\.woff2)\)', b)) | set(re.findall(r"url\((/webfonts/home-[0-9a-f]+\.woff2)\) format", b))
    assert len(pre) == 1, '서브셋 preload 가 없거나 모양이 다르다(as=font·type·crossorigin): %r' % b[:300]
    assert src == {pre[0]}, 'preload(%s)와 @font-face(%s)가 다른 파일이다' % (pre[0], sorted(src))
    assert os.path.isfile(os.path.join(ROOT, *pre[0].strip('/').split('/'))), '글꼴 파일이 저장소에 없다: %s' % pre[0]
    assert re.search(r"font-family:'%s';[^}]*font-display:swap" % F.FAMILY, b), '@font-face 에 font-display:swap 이 없다'
    assert os.path.isfile(os.path.join(ROOT, F.FONT_DIR, 'LICENSE.txt')), '글꼴 라이선스(OFL) 전문이 webfonts/ 에 없다'
    left = [f for f in os.listdir(os.path.join(ROOT, F.FONT_DIR)) if f.startswith('home-') and '/%s/%s' % (F.FONT_DIR, f) != pre[0]]
    assert not left, '쓰지 않는 옛 서브셋이 남았다(도구가 지운다): %s' % left


def test_home_static_text_is_inside_the_subset():
    """홈 마크업의 한글 음절·ASCII 가 서브셋 unicode-range 안에 있다 — 문구를 고치고 도구를 안 돌리면 빨개진다.

    배치가 매 회차 고쳐 쓰는 요약 구간(HOME_SUMMARY)과 통계·퀴즈 화면은 보지 않는다(데이터 문구라 게이트가 데이터에
    막히면 안 되고, 두 화면은 열 때 CDN 조각을 받는다). 도구가 모으는 것과 같은 함수(static_home_text)로 센다.
    무엇을 깨뜨리면 빨개지나(실제로 확인): 홈 마크업(view-home 안)에 서브셋에 없는 한글 '뷁' 을 넣으면.
    픽스처: 저장소 index.html 과 그 HOME_FONT 구간.
    """
    b = _block()
    ur = re.search(r'unicode-range:([^;}]+)', b)
    assert ur, 'unicode-range 가 없다'
    have = F.parse_ranges(ur.group(1))
    text = F.static_home_text(_html())
    need = {c for c in text if 0xAC00 <= ord(c) <= 0xD7A3 or 0x20 <= ord(c) <= 0x7E}
    assert len([c for c in need if ord(c) >= 0xAC00]) > 100, '홈 마크업에서 한글을 거의 못 읽었다 — 이 시험이 헛돈다'
    miss = sorted(c for c in need if ord(c) not in have)
    assert not miss, ('홈 문구에 서브셋에 없는 글자가 있다: %s — `pip install fonttools brotli` 뒤 '
                      '`python tools/make_home_font.py` 로 다시 구울 것' % ''.join(miss))


def test_home_font_stack_is_the_site_stack_with_the_subset_first():
    """홈 body 글꼴 목록 = 서브셋 한 개 + app.css body 목록. 서브셋에 없는 글자는 사이트와 같은 차례로 그린다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): app.css body 의 font-family 를 바꾸고 도구를 안 돌리면, 홈 목록에서
    'Pretendard Variable' 을 빼면.
    픽스처: 저장소 app.css 와 index.html HOME_FONT 구간.
    """
    m = re.search(r'body\.home-app\{font-family:([^}]+)\}', _block())
    assert m, '홈 body 글꼴 목록이 없다'
    assert m.group(1).strip() == "'%s',%s" % (F.FAMILY, F.body_stack(ROOT)), m.group(1)


def test_subset_is_cut_from_the_same_pretendard_as_the_cdn():
    """서브셋 원본 판(도구의 PRETENDARD)이 홈 CDN 링크의 판과 같다 — 다르면 서브셋 글자와 CDN 글자가 모양이 갈린다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): index.html CDN 주소의 pretendard@v1.3.9 를 v1.3.8 로 바꾸면.
    """
    vers = set(re.findall(r'orioncactus/pretendard@v([\d.]+)/', _html()))
    assert vers == {F.PRETENDARD}, 'CDN 판 %s 와 서브셋 원본 판 %s 가 다르다' % (sorted(vers), F.PRETENDARD)
