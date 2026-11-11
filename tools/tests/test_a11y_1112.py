# -*- coding: utf-8 -*-
"""2026-11-12 접근성 점검(.claude/skills/agongmap-a11y-check) 결과 가운데 마크업으로 잠글 수 있는 것.

  - role="img" 인 SVG 안에 링크가 없다 — img 역할 안의 링크는 iOS VoiceOver 등에서 읽히지 않는다(/cycle/ 순환 도식에 링크 6개).
  - /cycle/ '이 리포트를 읽는 법' 접는 칸 초점 고리는 초록 배너 위에서 흰색이다(먹색 고리는 바탕과 2.64:1).
"""
import glob
import io
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def test_no_links_inside_an_img_role_svg():
    """변이(실제로 확인): cycle/index.html 순환 도식의 role="group" 을 옛 role="img" 로 되돌리면 빨개진다.
    픽스처: 저장소에 있는 모든 HTML(생성 페이지 포함 — 생성기가 같은 꼴을 굽지 않는지도 본다)."""
    bad = []
    for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.split(os.sep)[0] in ('drafts', 'logs', 'node_modules'):
            continue
        s = io.open(f, encoding='utf-8').read()
        for m in re.finditer(r'<svg\b[^>]*\brole="img"[^>]*>(.*?)</svg>', s, re.S):
            if re.search(r'<a\b', m.group(1)):
                bad.append(rel)
    assert not bad, 'role="img" SVG 안에 링크가 있다: %s' % sorted(set(bad))
    assert 'role="group" aria-label="부동산 공급 사이클 순환 다이어그램"' in io.open(
        os.path.join(ROOT, 'cycle', 'index.html'), encoding='utf-8').read()


def test_cycle_howto_focus_ring_is_white_on_the_green_banner():
    """변이(실제로 확인): .howto-d>summary:focus-visible 규칙을 지우면 빨개진다. 픽스처: 저장소의 /cycle/ 손 문서."""
    s = io.open(os.path.join(ROOT, 'cycle', 'index.html'), encoding='utf-8').read()
    assert re.search(r'\.howto-d>summary:focus-visible\{outline:2px solid #fff', s)


def test_reading_sentences_that_were_13px_are_14px():
    """마침표로 끝나는 읽는 문장은 14px(2026-11-06 대표 결정 '읽는 글 14px', 정본 site_nav.READ_PX). 접근성 점검(11-12)에서 13px 로
    남아 있던 자리: 홈 퀴즈 예시 설명, 리포트 '…입니다' 참조 줄, 링크 카드 설명(지표 뼈대·/cycle/·/weekly/ 뼈대), /cycle/ '한계.'
    문단, /monthly/ 공유 안내, /weekly/ 서울 구 요약 줄. 이 페이지들의 글자 시험은 아직 13px 한 단계라 걸리지 않았다.
    변이(실제로 확인): page_share 의 .pshare-lead 를 13px 로 되돌리거나 put_nav 의 .sub 바꾸기를 지우면 빨개진다.
    픽스처: 저장소의 실제 원본과, 13px 줄을 담은 합성 주간 뼈대에 put_nav 를 돌린 결과."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import site_nav as N
    import page_share as PS
    import make_weekly_page as MW

    def px(text, sel):
        m = re.search(re.escape(sel) + r'\{[^}]*?font-size:(\d+(?:\.\d+)?)px', text)
        assert m, sel
        return float(m.group(1))
    app = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    ind = io.open(os.path.join(ROOT, 'tools', 'make_indicator_pages.py'), encoding='utf-8').read()
    cyc = io.open(os.path.join(ROOT, 'cycle', 'index.html'), encoding='utf-8').read()
    wk = MW.put_nav(io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
                    .replace('  .sub{font-size:14px;', '  .sub{font-size:13px;')
                    .replace('.links a span{display:block;font-size:14px;', '.links a span{display:block;font-size:13px;'))
    for text, sel in ((app, '.rcard.rc-sample .rc-desc'), (app, '.zs-ref'), (ind, '.links a span'), (cyc, '.links a span'),
                      (cyc, 'footer .src'), (PS.CSS, '.pshare-lead'), (wk, '  .sub'), (wk, '.links a span')):
        assert px(text, sel) >= N.READ_PX, sel
