# -*- coding: utf-8 -*-
"""리포트·지표·사이클 디자인 검수 수정(2026-11-07, 영역 C — 지적 reports-0~13·indicators-0~12)을 고정한다.

재현한 실제 상태(2026-11-07 main, Chromium 375·1280px 실측):
  · 시도 리포트 분기표 — zone.js 가 scrollTop 을 넣은 **뒤** cueBox 가 상자를 .cue 로 감싸 scrollTop 이 0 으로 돌아가, 1280px 에서
    2017~2020 실적 14행만 보였다(미래 추정 행은 상자 안 아래). 375px 에서는 열 머리 바탕 줄·'착공 기준 추정'·참고 행 주석이 nowrap 이라
    앞 세 칸이 280px 를 먹어 매매 칸이 색띠만 보였다.
  · 허브 칸의 판정 문장이 13px 회색(신호등보다 약함), '이 지역 글'은 '다른 지역' 칸 18장 뒤 맨 끝, '시세도 함께' 칸 숫자 13px 회색,
    머리 '페이지 수정 2026-11-06'(기계 꼴), 허브 머리 두 문장이 flex 라 한 줄에 붙음.
  · /weekly/ '숫자의 출처'만 해라체, /monthly/ 칩이 제목과 같은 말·절 번호가 제 줄, 집계 행 파랑 4.49:1.
  · /moveins/ 375px 가 '적정물량/년' 열(비율의 분모)을 숨김, 지표 주석 13px, 머리 기준 줄 고아 줄바꿈·큰 숫자 단위 없음.
  · /cycle/ '쉽게 말하면' 상자 안에서 합니다체·한다체가 섞임, 절 끝 '다음' 이동 없음·참고 절 입구 없음, 참고 ① 두 상자만 남색 바탕,
    근거 단락(.note·.conf·캡션)이 13~13.5px.
픽스처: 저장소 data.js 로 생성기 함수를 바로 부른다(구워진 페이지에 기대지 않는다 — 생성기 앞에서 돌아도 같은 답). /cycle/ 과
        app.css·desk.css 는 손 파일 그대로.
"""
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_indicator_pages as I  # noqa: E402
import make_monthly_page as MO  # noqa: E402
import make_sido_pages as M  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _ctx():
    adv, stats = M.load()
    s = adv['sido']
    SZ.refresh_texts(s)
    return adv, stats, s


def _px(css, sel):
    """css 안에서 선택자 sel 규칙의 font-size(px). var(--fs-dense)=14, var(--fs-read)=16."""
    rules = re.findall(r'(?:^|[}\n])\s*%s\{([^}]*)\}' % re.escape(sel), css)   # 선택자가 그것 하나뿐인 규칙(앞 조상 선택자 없음)
    sizes = [f.group(1).strip() for f in (re.search(r'font-size:\s*([^;}]+)', r) for r in rules) if f]
    assert sizes, '%s 의 글자 크기 규칙을 못 찾았다' % sel
    v = sizes[0]
    return {'var(--fs-dense)': 14.0, 'var(--fs-read)': 16.0}.get(v) or float(v.rstrip('px'))


def _contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


# ── 시도 리포트 ─────────────────────────────────────────────────────────────────────────────

def test_quarter_table_scrolls_to_the_future_after_the_cue_wrap():
    """분기표를 맨 아래(미래 추정)로 내리는 줄은 cueBox 가 상자를 감싼 **뒤**다(reports-0 — 요소를 옮기면 scrollTop 이 0 이 된다).
    변이(실제로 확인): scrollTop 줄을 CUES 감싸기 앞으로 되돌리면 빨개진다."""
    js = M.zone_js()
    wrap = js.index('CUES.push(cueBox(s))')
    down = js.index('e.scrollTop=e.scrollHeight')
    assert wrap < down, 'scrollTop 을 cueBox 감싸기보다 먼저 넣는다 — 감싸는 순간 0 으로 돌아간다'


def test_quarter_table_wraps_on_phones_and_keeps_the_baseline_in_the_header():
    """375px 분기표는 열 머리 바탕 줄·추정 칸·참고 행 단추를 줄바꿈해 매매·전세 칸이 첫 화면에 온다(reports-1). 바탕 줄은 열 머리에
    그대로 둔다(2026-10-21 대표 지적). 변이(실제로 확인): WK_CSS 의 600px 규칙을 지우거나 <wbr> 를 빼면 빨개진다."""
    css = M.WK_CSS
    m = re.search(r'@media \(max-width:600px\)\{(.*?)\}\}', css)
    assert m, '좁은 화면 분기표 규칙이 없다'
    for sel in ('.ztb th small.zbase{white-space:normal', '.ztb td.zfut{white-space:normal', '.ztb tfoot .rbtn{'):
        assert sel in m.group(1), sel
    src = io.open(os.path.join(ROOT, 'tools', 'make_sido_pages.py'), encoding='utf-8').read()
    assert '세대<wbr>=100%%</small>' in src


def test_hub_cards_lead_with_the_verdict_in_the_grade_colour():
    """허브·'다른 지역' 칸의 판정 문장은 등급 클래스를 단 i.zv 이고 14px·600·등급 글자색이다(reports-2). 등급 글자색은 지면 위 4.5:1 이상.
    변이(실제로 확인): build_hub 가 다시 맨 <i> 를 굽거나, app.css i.zv 를 13px 로 되돌리면 빨개진다."""
    _, stats, s = _ctx()
    h = M.build_hub(s, stats)
    for z in s['zones']:
        assert re.search(r'<a href="/zone/%s/"><b>[^<]+</b>.*?<i class="zv %s">' % (re.escape(__import__('urllib.parse').parse.quote(z['z'])), z['grade']), h, re.S), z['z']
    page = M.build_page('서울', s, stats, {}, s['zones'])
    others = page[page.index('<h2>다른 지역</h2>'):]
    assert others.count('<i class="zv g') == len(s['zones']) - 1
    css = _read('app.css')
    assert _px(css, '.zlinks a i.zv') >= 14
    for g, col in re.findall(r'\.zlinks a i\.zv\.(g\d)\{color:(#[0-9a-f]{6})\}', css):
        assert _contrast(col, '#f4f6f5') >= 4.5 and _contrast(col, '#e9edeb') >= 4.5, (g, col)


def test_region_posts_follow_the_numbers_and_fold_after_four():
    """'이 지역 글' 자리는 '숫자로 보면' 바로 뒤(분기표 앞)이고 바닥글에는 없다. POSTS_CAP 편이 넘으면 zone.js 가 나머지를 접고 단추를
    단다(reports-3). 변이(실제로 확인): POSTS_SLOT 을 FOOT 로 되돌리면 순서 단정이, zone.js 의 zp-cut 을 지우면 접기 단정이 빨개진다."""
    _, stats, s = _ctx()
    page = M.build_page('경기', s, stats, {}, s['zones'])
    assert page.count(M.POSTS_SLOT) == 1 and M.POSTS_SLOT not in M.FOOT
    at = page.index(M.POSTS_SLOT)
    assert page.index('<h2>숫자로 보면</h2>') < at < page.index('의 분기별 공급</h2>')
    js = M.zone_js()
    assert 'sec.classList.add("zp-cut")' in js and 'length<=%d)' % M.POSTS_CAP in js
    assert '.zposts.zp-cut .kgrid>:nth-child(n+%d){display:none}' % (M.POSTS_CAP + 1) in M.WK_CSS


def test_market_cards_show_the_number_large():
    """'시세도 함께' 칸은 '숫자로 보면'과 같은 .zcell — 큰 숫자(strong)와 아래 줄(small)로 나뉜다(reports-6). 부호 색은 주간 표의 MW.sign.
    변이(실제로 확인): next_links 를 옛 .zlinks 한 줄 칸으로 되돌리면 빨개진다."""
    html = M.next_links('서울', {'regions': ['서울'], 'rows': [{'p': '2026-10-12', 'ma': [0.12], 'je': [-0.05]}]}, {})
    assert '<div class="zgrid zmk">' in html
    assert '<a class="zcell" href="/weekly/"><b>이번 주 매매</b><strong class="up">+0.12%</strong><small>전세 -0.05% · ' in html, html


def test_page_modified_date_reads_long_and_does_not_churn_the_page():
    """머리 '페이지 수정'은 읽는 꼴(SZ.day_long)이고, keep_dates 는 그 날짜만 다른 판을 '안 바뀜'으로 본다(reports-8). JSON-LD 는 ISO.
    변이(실제로 확인): _mask_dates 에서 PAGE_DAY_RE 를 빼면 둘째 단정이(매일 새 판), day_long 을 빼면 첫 단정이 빨개진다."""
    _, stats, s = _ctx()
    page = M.build_page('서울', s, stats, {}, s['zones'])
    assert '페이지 수정 %s</span>' % SZ.day_long(M._today()) in page
    old = page.replace('페이지 수정 %s' % SZ.day_long(M._today()), '페이지 수정 2020년 1월 2일')
    kept, _, changed = M.keep_dates(page, old, M._today())
    assert kept == old and changed is False
    other = page.replace('<h2>숫자로 보면</h2>', '<h2>숫자로</h2>')
    assert M.keep_dates(other, old, M._today())[2] is True


def test_hub_head_breaks_and_monthly_is_a_link_line():
    """허브 머리는 블록이라 <br> 이 두 문장을 가르고, '매달 발표되는 통계'는 제 절이 아니라 '읽는 법' 아래 한 줄이다(reports-13).
    변이(실제로 확인): .zlead.zlead-s 의 display:block 을 지우거나 옛 절을 되살리면 빨개진다."""
    _, stats, s = _ctx()
    h = M.build_hub(s, stats)
    assert '매달 발표되는 통계' not in h
    read = h[h.index('class="zread"'):]
    assert '<p class="zsub zmonthly"><a href="/monthly/">' in read
    assert re.search(r'\.zlead\.zlead-s\{display:block', _read('app.css'))


def test_report_sentences_are_14px():
    """리포트의 문장 칸(.zsub·.znote·.zs-note·.zwarn·.zg-note·.zl-legend·.tb-refnote·.zyear·.zwk-none)은 14px(reports-12).
    변이(실제로 확인): app.css .zsub 를 13px 로 되돌리면 빨개진다."""
    css = _read('app.css')
    for sel in ('.zsub', '.znote', '.zwarn', '.zg-note', '.tb-refnote'):
        assert _px(css, sel) >= 14, sel
    assert _px(css, '.zs-note,.zs-est') >= 14
    assert 'font-size:var(--fs-dense)' in re.search(r'\.zl-legend\{[^}]*\}', css).group(0)
    assert '.zyear{font-size:var(--fs-dense)' in M.WK_CSS and '.zwk-none{font-size:var(--fs-dense)' in M.WK_CSS


# ── /weekly/·/monthly/ ─────────────────────────────────────────────────────────────────────

def test_weekly_source_speaks_like_the_rest_of_the_page():
    """'숫자의 출처'는 합쇼체(reports-11). 표 주석 .note 는 14px(reports-12). 지도 위 '옆으로 밀어' 줄(reports-7).
    변이(실제로 확인): SOURCE_TEXT 를 옛 '그대로 쓴다' 로 되돌리면 빨개진다."""
    ends = re.findall(r'([가-힣])\.(?:\s|$)', MW.SOURCE_TEXT)
    assert ends and set(ends) == {'다'} and all(re.findall(r'니다\.', MW.SOURCE_TEXT)), MW.SOURCE_TEXT
    assert not re.search(r'(?<!니)다\.', MW.SOURCE_TEXT), MW.SOURCE_TEXT
    assert '.sggt .note{font-size:var(--fs-dense)' in MW.TABLE_CSS
    W, Q = MW.load()
    head = MW.build(W, Q)[0]
    assert head.index('class="mm-swipe-top"') < head.index('<div class="cue"><div class="mm-scroll">')
    assert '.mm-swipe-top{display:block' in MW.MAP_CSS


def test_monthly_heading_numbers_and_chip():
    """/monthly/ 절 번호는 h2 안(reports-9), 칩은 제목과 다른 말(최신 기준), 집계 행 파랑은 paper2 위 4.5:1 이상(reports-10).
    변이(실제로 확인): sec() 를 옛 '<div class="secno">' 로 되돌리거나 SHELL --dn 을 #2f6db3 으로 되돌리면 빨개진다."""
    out = MO.sec('price', 1, '시도별 매매', '2026년 9월', '한국부동산원', '<table></table>')
    assert '<h2><span class="secno">1</span>시도별 매매</h2>' in out and '<div class="secno">' not in out
    src = io.open(os.path.join(ROOT, 'tools', 'make_monthly_page.py'), encoding='utf-8').read()
    assert '<div class="chip">이달의 통계</div>' not in src and '<div class="chip">최신 %s 기준</div>' in src
    dn = re.search(r'--dn:(#[0-9a-f]{6})', I.SHELL).group(1)
    assert _contrast(dn, '#e9edeb') >= 4.5 and _contrast(dn, '#f4f6f5') >= 4.5, dn


# ── /moveins/·/jeonse-ratio/ ────────────────────────────────────────────────────────────────

def test_moveins_keeps_the_denominator_on_phones_and_heads_read_cleanly():
    """좁은 화면은 지난해(3열)만 숨기고 적정물량/년(6열 — 비율의 분모)은 남기며, 숨김 안내는 표 아래 한 줄에 있다(indicators-2).
    큰 숫자 옆 단위(indicators-9), 기준 줄 조각 nowrap(indicators-8), 주석 14px(indicators-1).
    변이(실제로 확인): 480px 규칙에 nth-child(6) 을 되살리거나, big 에서 <small>세대</small> 를 빼면 빨개진다."""
    adv, stats, _ = _ctx()
    html, _ = I.build_moveins(adv, '2031-03-03')
    m = re.search(r'@media\(max-width:480px\)\{(#utable\.mv[^{]*)\{display:none\}\}', html)
    assert m and 'nth-child(3)' in m.group(1) and 'nth-child(6)' not in m.group(1), m and m.group(1)
    note = re.search(r'<div class="note">([^<]*<b>[^<]*</b>[^<]*)</div>', html).group(1)
    assert '좁은 화면은' in note and '열을 숨깁니다' in note
    assert re.search(r'<div class="big">[\d,]+<small>세대</small></div>', html)
    assert '<span class="nw">· ' in html
    jr, _ = I.build_jeonse(stats, '2031-03-03')
    assert re.search(r'<span class="nw">· \d{4}년 \d{1,2}월 기준</span>', jr)
    assert SZ.basis_month(jr), '감시가 읽는 시점 문구가 깨졌다'
    assert _px(I.SHELL, '.note') >= 14


# ── /cycle/ ────────────────────────────────────────────────────────────────────────────────

def _cycle():
    return _read(os.path.join('cycle', 'index.html'))


def test_cycle_plain_boxes_speak_one_voice():
    """'쉽게 말하면' 상자(.read)의 문장은 모두 합니다체(indicators-3 — 한 상자 안에서 '돌아섰다…드러납니다'가 섞였다).
    변이(실제로 확인): 고리③ 상자 첫 문장을 옛 '성립한다.' 로 되돌리면 빨개진다."""
    s = _cycle()
    boxes = re.findall(r'<div class="read">(.*?)</div>', s, re.S)
    assert len(boxes) >= 9, len(boxes)
    for b in boxes:
        t = re.sub(r'<[^>]+>', '', b)
        t = re.sub(r'"[^"]*"', '', t)                      # 따옴표 안 인용('집값 오르면 공급 는다')은 문장 끝이 아니다
        bad = re.findall(r'(?<!니)다[.)]', t)
        assert not bad, '한다체 문장이 섞였다: %s' % t[:80]


def test_cycle_sections_point_to_the_next_one():
    """본문·참고 절은 끝에 '다음 · …' 링크가 있고 순서는 왼쪽 목차(.dtoc)와 같다. 30초 요약 아래 참고 ①~④ 입구, 끝 요약 항목마다 절로
    가는 링크가 있다(indicators-4·12). 변이(실제로 확인): 고리③ 절의 cy-next 를 지우거나 다른 절을 가리키게 하면 빨개진다."""
    s = _cycle()
    toc = re.findall(r'<li><a href="#(\w+)">', re.search(r'<nav class="dtoc".*?</nav>', s, re.S).group(0))
    steps = [x for x in toc if x.startswith(('link', 'score', 'ref'))]
    for a, b in zip(steps, steps[1:] + ['summary']):
        sec = re.search(r'id="%s"><div class="wrap">(.*?)</div></section>' % a, s, re.S).group(1)
        m = re.findall(r'<p class="cy-next"><a href="#(\w+)">', sec)
        assert m == [b], (a, m, b)
    refs = re.search(r'<p class="tldr-refs">(.*?)</p>', s).group(1)
    assert re.findall(r'href="#(ref\d)"', refs) == ['ref1', 'ref2', 'ref3', 'ref4']
    take = re.search(r'<section class="take" id="summary">(.*?)</section>', s, re.S).group(1)
    go = re.findall(r'class="take-go" href="#(\w+)"', take)
    assert len(go) == take.count('<li>') and all(('id="%s"' % g) in s for g in go)


def test_cycle_has_one_chart_world_and_reading_sizes():
    """차트 상자는 모두 흰 .chartbox(남색 인라인 바탕 없음 — indicators-5), 링크 카드에 이모지 없음(indicators-7 일부), 근거 단락·캡션은
    14px 이상(indicators-0), 글자 초록은 #1a6b54 하나(indicators-6 — .cl-high·.v-strong).
    변이(실제로 확인): 참고 ① 상자에 style="background:#1d2742" 를 되살리거나 app.css .note 를 13.5px 로 되돌리면 빨개진다."""
    s = _cycle()
    assert not re.search(r'<div class="chartbox"[^>]*style=', s)
    links = re.search(r'<div class="links">(.*?)</div>', s, re.S).group(1)
    assert not re.search('[\U0001F300-\U0001FAFF☀-➿]', links), links
    css = _read('app.css')
    assert _px(css, '.note') >= 14 and _px(css, '.conf .ctxt') >= 14 and _px(css, '.chartbox .cap') >= 14
    assert '#157a61' not in css
    assert '<div class="howto">' not in s and s.index('class="mainbanner"') < s.index('class="howto-d"') < s.index('id="link1"')


# ── desk.css ───────────────────────────────────────────────────────────────────────────────

def test_desk_layouts_for_posts_weekly_links_and_doc_measure():
    """리포트 글 카드 두 열(reports-4), /weekly/ '더 둘러보기' 두 열(reports-13), doc 글 문단 720px(indicators-10).
    변이(실제로 확인): desk.css 에서 셋 중 하나를 지우면 빨개진다."""
    d = _read('desk.css')
    assert 'body[data-desk=report] .zposts .kgrid{grid-template-columns:repeat(2,minmax(0,1fr))}' in d
    assert 'body[data-desk=weekly] .links{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))' in d
    assert re.search(r'body\[data-desk=doc\] \.wrap>p,[^{]*\{max-width:720px\}', d)
