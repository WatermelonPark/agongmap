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


def _lum(c):
    f = lambda x: (x / 255) / 12.92 if x / 255 <= 0.03928 else (((x / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _on(fill, bg):
    """rgba(r,g,b,a) 를 바탕 위에 합성한 색(불투명이면 그대로)."""
    if fill.startswith('rgba'):
        r, g, b, a = [float(x) for x in re.findall(r'[\d.]+', fill)]
        return tuple(c * a + bg[i] * (1 - a) for i, c in enumerate((r, g, b)))
    return _hex(fill)


def _cr(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_map_cell_numbers_and_report_table_cells_reach_4_5_to_1():
    """전국 시군구 지도 칸 숫자는 칸 색 위에서 4.5:1 이상 — 진한 칸(알파 MAP_INK_A 이상)은 먹색 글자(2026-11-12 대표 결정 '진한 칸 글자만
    먹색'). '0.00' 칸 글자는 #4e5d61. 시도 리포트 표의 가장 진한 칸 위 먹색 글자도 4.5:1 이상(tint 최대 알파 0.78).
    실제 상태(11-12 접근성 점검): 주간 지도 636개 중 107개, 월간 848개 중 221개가 미달(최저 2.72:1 — #8f2318 글자·#e36c62 칸),
    '0.00' 칸 4.40:1, 리포트 표 19칸 4.40:1.
    변이(실제로 확인): make_weekly_page 의 tcol 에서 먹색 갈래를 지우거나 MAP_INK_A 를 0.9 로 올리면, tint 의 0.78 을 0.8 로 되돌리면
    빨개진다(홈 거울은 test_sgg_map 이 한 글자까지 대조한다).
    픽스처: 합성 값(기준 ref 의 0~1.6배, 양·음·0·빈 값)을 실은 sgg_map_svg 출력, 지면색(#f4f6f5) 바탕."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import make_weekly_page as MW
    import make_sido_pages as MS
    ref = 0.2
    codes = [t[0] for t in MW.nation_tile()['t']]
    span = [-0.32, -0.2, -0.13, -0.08, -0.02, 0.0, None, 0.004, 0.03, 0.06, 0.09, 0.12, 0.2, 0.33]
    vals = {c: span[k % len(span)] for k, c in enumerate(codes)}
    svg = MW.sgg_map_svg([vals, vals], ['매매', '전세'], ref)
    paper = _hex('#f4f6f5')
    cells = re.findall(r'rx="3" fill="([^"]+)" stroke="#d8dfdc"/><text [^>]*fill="(#\w{6})">', svg)
    assert len(cells) > 100, len(cells)
    low = [(f, t, round(_cr(_on(f, paper), _hex(t)), 2)) for f, t in cells if _cr(_on(f, paper), _hex(t)) < 4.5]
    assert not low, low[:5]
    worst = MS.tint(1.0, 1.0)
    assert _cr(_on(worst, paper), _hex('#131e24')) >= 4.5 and _cr(_on(MS.tint(-1.0, 1.0), paper), _hex('#131e24')) >= 4.5


def test_series_lines_and_labels_have_the_dark_variants():
    """계열색의 흰 바탕 대비(2026-11-12 대표 결정 '글자·선만 진한 변형'): 그래프 선은 3:1 이상(WCAG 1.4.11), 보통 크기 글자는 4.5:1 이상.
    실제 상태(접근성 점검): 기본통계 금리 선 #e8b84b 1.84:1, /cycle/ 착공 선 #d99a00 2.45:1, /cycle/ 도식 '신축공급'(16.5px·600)
    초록 #1f8a70 4.26:1, '3~5' 배지(흰 글자 14px) 4.26:1.
    변이(실제로 확인): DS_COLOR 금리를 '#e8b84b' 로, cycle FLOW 를 '#d99a00' 으로 되돌리면 빨개진다.
    픽스처: 저장소의 home-stats.js(home_src 로)·cycle/index.html."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import home_src as HS
    stats = next(t for f, t in HS.home_files() if f.endswith('home-stats.js'))
    white = (255, 255, 255)
    rate = re.search(r"금리:'(#[0-9a-f]{6})'", re.search(r'const DS_COLOR=\{(.*?)\};', stats, re.S).group(1)).group(1)
    assert _cr(_hex(rate), white) >= 3, rate
    cyc = io.open(os.path.join(ROOT, 'cycle', 'index.html'), encoding='utf-8').read()
    flow = re.search(r'FLOW="(#[0-9a-fA-F]{6})"', cyc).group(1)
    assert _cr(_hex(flow), white) >= 3, flow
    lab = re.search(r'fill="(#[0-9a-fA-F]{6})">신축공급</text>', cyc).group(1)
    badge = re.search(r'<rect x="206\.0" y="341\.5"[^>]*fill="(#[0-9a-fA-F]{6})"/>', cyc).group(1)
    assert _cr(_hex(lab), white) >= 4.5 and _cr(_hex(badge), white) >= 4.5, (lab, badge)
