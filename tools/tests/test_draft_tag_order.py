# -*- coding: utf-8 -*-
"""초안에서 태그 칸은 각 글 묶음의 **맨 아래**(이미지 갤러리 뒤)에 온다(2026-10-09 대표: 태그는 다른 것을 다 쓴 뒤
발행 직전에 넣는다). 무엇을 깨뜨리면 빨개지나(실제로 확인): make_naver_post.render 에서 tagfield 를 본문 바로 뒤로
되돌리면 첫 시험이, make_theory_post 에서 같은 일을 하면 둘째 시험이 빨개진다.
픽스처: 최소 초안 dict(제목·본문·태그·이미지 안내) — 네트워크(경쟁 글 패널)는 끈다.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402


def test_weekly_and_zone_drafts_put_tags_last(monkeypatch):
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    d = dict(title='t', body='<p>b</p>', tags=['a'], imgnote='note', imgs=[], kw='k')
    html = P.render('2026-10-05', d, dict(d, seq='1 / 16'))
    for sec in html.split('<section class="draft">')[1:]:
        assert sec.index('class="tags"') > sec.index('📎'), '태그 칸이 이미지 안내보다 위에 있다'
        assert sec.index('class="tags"') > sec.index('id="b'), '태그 칸이 본문보다 위에 있다'


def test_theory_draft_puts_tags_last():
    src = inspect.getsource(T)
    i_tag = src.index("S.append(P.tagfield(")
    i_gal = src.index("S.append(P.img_gallery(post['imgs']))")
    assert i_tag > i_gal
