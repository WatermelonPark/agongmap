# -*- coding: utf-8 -*-
"""초안 HTML 안에 캡처 이미지를 직접 싣는다(2026-09-27 사용자 요청).

초안에는 이미지 파일 이름만 적혀 있어서, 주간 초안의 시군구 지도가 만들어졌는지도
초안에서 보이지 않았다. 이제 img_gallery 가 이미지를 base64 로 박아 초안 파일 하나만으로
보이게 한다. 본문 복사 상자에는 넣지 않는다(클립보드가 수 MB가 되고, 스마트에디터가
data URI 이미지를 어떻게 받는지 확인할 수 없다).

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - render 에서 `S.append(img_gallery(...))` 줄을 지우면 → 싣는 시험 두 개
  - img_gallery 를 본문 field 안(d['body'] 뒤)에 붙이면 → 복사 상자 시험
  - draft_weekly 의 imgs 에서 지도(sgg)를 빼면 → 주간 지도 시험
  - img_gallery 가 없는 파일을 조용히 건너뛰게 바꾸면 → 없는 파일 시험
  - make_theory_post.render 에서 P.img_gallery 줄을 지우면 → 이론 초안 시험
픽스처: tmp_path 에 만든 작은 PNG 바이트(실제 캡처 파일의 이름·자리 이름을 그대로 쓴다).
네이버 경쟁 글 조회는 막는다(키 없는 PC와 같은 경로). 저장소의 drafts/ 는 건드리지 않는다.
"""
import base64
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402

PNG = b'\x89PNG\r\n\x1a\n' + b'agongmap-test-image'
B64 = base64.b64encode(PNG).decode('ascii')


def _png(tmp_path, name):
    p = tmp_path / name
    p.write_bytes(PNG)
    return str(p)


def _draft(imgs, body='<p>본문</p><p>[여기에 전국 시군구 지도 이미지를 넣어 주세요]</p>'):
    return dict(title='제목', body=body, tags=['아공맵'], kw='주간아파트가격동향',
                imgnote='지도·표를 자동으로 떴습니다.', imgs=imgs)


def _copy_box(html, tid):
    m = re.search(r'<div class="box [^"]*" id="%s">(.*?)</div></div>' % tid, html, re.S)
    assert m, tid
    return m.group(1)


def test_render_embeds_draft_images(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    top = _png(tmp_path, 'weekly-top10.png')
    sgg = _png(tmp_path, 'weekly-sgg.png')
    html = P.render('2026-09-21', _draft([(top, '상승·하락 TOP10'), (sgg, '전국 시군구 지도')]), None)
    assert html.count('data:image/png;base64,%s' % B64) == 2
    assert '[전국 시군구 지도]' in html and '[상승·하락 TOP10]' in html


def test_images_stay_out_of_the_copy_box(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    sgg = _png(tmp_path, 'weekly-sgg.png')
    html = P.render('2026-09-21', _draft([(sgg, '전국 시군구 지도')]), None)
    box = _copy_box(html, 'b1')
    assert '<img' not in box and 'base64' not in box
    assert 'data:image/png;base64' in html


def test_weekly_draft_lists_the_map(monkeypatch):
    """주간 초안이 지도와 TOP10 을 싣도록 imgs 를 넘기는지 — 캡처는 막고 경로만 흉내 낸다."""
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py'])
    monkeypatch.setattr(P, 'capture_weekly_map',
                        lambda: ('drafts\\weekly-sgg.png', 'drafts\\weekly-top10.png', None))
    adv, sts = P.M.load()
    d = P.draft_weekly(adv, sts)
    names = [rel for rel, _ in d['imgs']]
    assert 'drafts\\weekly-sgg.png' in names and 'drafts\\weekly-top10.png' in names


def test_missing_file_is_reported_not_dropped(tmp_path):
    out = P.img_gallery([(str(tmp_path / 'nope.png'), '전국 시군구 지도')])
    assert '이미지 파일이 없습니다' in out and '전국 시군구 지도' in out
    assert P.img_gallery([(None, '전국 시군구 지도')]) == ''   # 캡처를 안 뜬 회차는 조용히


def test_theory_draft_embeds_images(tmp_path, monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    _png(tmp_path, 'cycle-loop.png')
    post = next(p for p in T.POSTS if p['n'] == 1)
    html = T.render(post)
    assert 'data:image/png;base64,%s' % B64 in html
    assert '<img' not in _copy_box(html, 'b1')
