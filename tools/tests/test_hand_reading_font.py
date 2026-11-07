# -*- coding: utf-8 -*-
"""손 페이지(소개·FAQ·개인정보·퀴즈 랜딩 3종·404)와 공용 푸터 면책의 글자 하한 두 단계, 그리고 같은 검수에서 고친 손 페이지 화면.

2026-11-06 대표 결정 '읽는 글 14px 하한 채택': 읽는 문장(설명·주석·단락·카드 결론 줄·보기 줄·링크 카드 설명·푸터 면책)은
site_nav.READ_PX(14px) 이상, 라벨·축 눈금·표 칸·칩·날짜·캡션 한 줄은 site_nav.LABEL_PX(13px) 이상이다. 홈·시세 탭·생성 페이지의
하한 시험(test_home_min_font·test_view_min_font·test_page_min_font)은 아직 13px 한 단계로 보고, 이 파일이 손 페이지와 공용 푸터를
두 단계로 본다.

재현한 실제 상태(2026-11-07 디자인 검수 D, 저장소 그대로):
  · 퀴즈 랜딩 3종의 예시 보기 줄 `.q .qo` 13.5px(회색)·링크 카드 설명 `.links a span` 13px — 문장인데 라벨 하한만 넘었다(hand-2).
  · 공용 푸터 면책 문장이 손 페이지 `footer{font-size:13px}`·app.css `.disc{13px}`·지표 뼈대 `.disc{13px}` 를 따라 13px 이었다.
  · 링크 줄 '홈 · 소개 · FAQ · 개인정보처리방침 · 메일' 이 한 줄에 중점 넷이었다(hand-10).
  · 퀴즈 머리 CTA '🐣 부린이 테스트 시작하기' 와 바닥 CTA '지금 바로 테스트 시작 →' 가 같은 곳으로 가는데 말이 달랐고, 소개·FAQ·
    개인정보·404 의 홈 단추가 '🏠 아공맵 홈으로' 로 단추 안에 OS 색 이모지를 썼다(hand-9).
  · 404 에 되돌아가기가 없고 머리 라벨이 다른 손 페이지의 먹색 칩이 아니었다(hand-4).
  · FAQ 질문 summary 의 오른쪽 여백(20px)이 '+' 기호(right 18px, 20px 글자)를 비워 두지 않아 긴 질문이 기호에 닿았다(hand-1).
  · 개인정보 1·2항 표가 375px 에서 min-width 560px 로 밀려 '보유 기간'·'이전 국가·시점' 이 첫 화면에 없었다(hand-0).

변이(각각 실제로 넣어 빨간 것을 확인):
  · burini-test `.q .qo` 를 13.5px 로, redev-test `.links a span` 을 13px 로 되돌리면 test_hand_pages_keep_two_floors 가 빨강.
  · about `.chip` 을 12px 로 내리면 같은 시험이 빨강(라벨 하한).
  · site_nav.FOOTER_DISC 의 인라인 크기를 지우면(또는 READ_PX 를 13 으로) test_footer_disclaimer_is_reading_size 가 빨강.
  · investor-test 바닥 CTA 를 옛 '지금 바로 테스트 시작 →' 로, 404 홈 단추를 '🏠 아공맵 홈으로' 로 되돌리면 test_cta_wording 이 빨강.
  · 404 에서 history.back() 단추나 .chip 을 지우면 test_404_offers_a_way_back 이 빨강.
  · faq summary padding 을 옛 '16px 20px' 으로 되돌리면 test_faq_question_leaves_room_for_the_icon 이 빨강.
  · privacy 2항 표 한 칸의 data-label 을 지우거나 머리와 다르게 적으면, `.stack` 클래스를 지우면 test_privacy_key_tables_stack 이 빨강.
픽스처: 저장소의 손 페이지 HTML·site_nav 상수·make_quiz_share_pages.pages() 그대로(데이터·날짜와 무관 — 앞으로 가도 같은 답).
"""
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_quiz_share_pages as MQ  # noqa: E402
import site_nav as N  # noqa: E402

# 13~14px 사이가 허락되는 라벨 자리 — 선택자 맨 끝(주어)의 클래스·태그. 칩·표 머리·탭 라벨·한 줄 메타·코드 식별자·푸터 바탕
# (브랜드·링크·문의·자료 줄; 면책은 FOOTER_DISC 인라인 14px).
LABEL_SUBJECTS = {'chip', 'th', 'nav-btn', 'meta', 'code', 'footer', 'sfoot'}
LANDINGS = ('burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html')


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _css(html):
    return re.sub(r'/\*.*?\*/', '', ''.join(re.findall(r'<style[^>]*>(.*?)</style>', html, re.S)), flags=re.S)


def _rules(css):
    """(선택자, 본문) — @media 안 규칙도 낸다(좁은 화면에서만 작아지는 글자도 본다)."""
    flat = re.sub(r'@media[^{]*\{', '', css)
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', flat):
        yield m.group(1).strip(), m.group(2)


def _root_vars(css):
    out = {}
    for sel, body in _rules(css):
        if sel == ':root':
            out.update(dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+)', body)))
    return out


def _px(val, rootv, depth=0):
    """글자 크기 값 → 가장 작게 그려질 px(clamp·min 은 가장 작은 값). 못 읽으면 None."""
    val = val.strip()
    if depth > 5:
        return None
    m = re.fullmatch(r'var\((--[\w-]+)\)', val)
    if m:
        return _px(rootv.get(m.group(1), ''), rootv, depth + 1) if m.group(1) in rootv else None
    nums = [float(a) * (16 if u == 'rem' else 1) for a, u in re.findall(r'([\d.]+)(px|rem)\b', val)]
    return min(nums) if nums else None


def _subject(sel):
    """선택자 맨 끝 복합 선택자의 (클래스·태그 낱말들, 가상 요소 여부)."""
    last = re.split(r'[\s>+~]+', sel.strip())[-1]
    pseudo = '::' in last
    base = last.split('::')[0].split(':')[0]
    toks = set(re.findall(r'\.([\w-]+)', base))
    tag = re.match(r'[a-z][a-z0-9]*', base)
    if tag:
        toks.add(tag.group(0))
    return toks, pseudo


def _floor_breaks(rel, html):
    css = _css(html)
    rootv = _root_vars(css)
    bad = []
    for sel, body in _rules(css):
        fs = re.search(r'font-size\s*:\s*([^;]+)', body)
        if not fs:
            continue
        px = _px(fs.group(1), rootv)
        if px is None:
            continue
        for one in sel.split(','):
            toks, pseudo = _subject(one)
            if px < N.LABEL_PX:
                bad.append('%s %s{%gpx} < 라벨 하한 %s' % (rel, one.strip(), px, N.LABEL_PX))
            elif px < N.READ_PX:
                # 가상 요소는 칸 이름(attr())이나 한 줄 안내(20자 이하)일 때만 라벨이다
                lit = re.search(r"content\s*:\s*(attr\([^)]*\)|'[^']{0,20}'|\"[^\"]{0,20}\")", body)
                if not (toks & LABEL_SUBJECTS or (pseudo and lit)):
                    bad.append('%s %s{%gpx} < 읽는 글 하한 %s' % (rel, one.strip(), px, N.READ_PX))
    for m in re.finditer(r'style="[^"]*font-size:\s*([\d.]+)px', html):
        if float(m.group(1)) < N.READ_PX:
            bad.append('%s 인라인 %s' % (rel, m.group(0)))
    return bad


def test_canon_values():
    assert (N.READ_PX, N.LABEL_PX) == (14, 13), '하한 정본이 2026-11-06 결정(읽는 글 14·라벨 13)과 다르다'
    assert N.FOOTER_PX == N.LABEL_PX


def test_hand_pages_keep_two_floors():
    """손 페이지 <style> 의 모든 글자 규칙: 13px 미만은 없고, 14px 미만은 라벨 자리(LABEL_SUBJECTS)뿐이다. 인라인 글자도 14px 이상."""
    bad, seen = [], 0
    for rel in N.HAND_FOOTER_PAGES:
        html = _read(rel)
        seen += sum(1 for _ in _rules(_css(html)))
        bad += _floor_breaks(rel, html)
    assert seen > 100, '손 페이지 규칙을 거의 못 읽었다(%d)' % seen
    assert not bad, bad


def _disc_px(foot):
    m = re.search(r'<(\w+)[^>]*\bstyle="[^"]*font-size:\s*([\d.]+)px[^"]*"[^>]*>\s*' + re.escape(N.DISCLAIMER), foot)
    return m and float(m.group(2))


def test_footer_disclaimer_is_reading_size():
    """공용 푸터의 면책 문장은 READ_PX 이상이다 — 손 페이지·생성 페이지·퀴즈 점수 페이지가 같은 FOOTER_DISC 한 줄을 싣는다.
    인라인 크기라 손 페이지 footer 13px·app.css .disc 13px·지표 뼈대 .disc 13px 위에서도 이긴다. 링크 줄에는 메일이 없고
    문의 줄(FOOTER_CONTACT)이 따로 있다."""
    feet = {'HAND_FOOTER': N.HAND_FOOTER, 'site_footer(src)': N.site_footer('국토교통부'), 'site_footer()': N.site_footer('')}
    for path, body in MQ.pages()[:1]:
        feet['퀴즈 점수 페이지'] = re.search(r'<footer.*?</footer>', body, re.S).group(0)
    for name, foot in feet.items():
        px = _disc_px(foot)
        assert px and px >= N.READ_PX, '%s 면책 글자 %s' % (name, px)
        assert N.FOOTER_CONTACT in foot and 'mailto' not in N.FOOTER_LINKS, name
    assert N.FOOTER_LINKS.count(' · ') <= 3, '링크 줄 중점이 넷 이상이다'


def test_score_pages_use_the_hand_shell():
    """퀴즈 점수 공유 페이지의 JS 없는 폴백도 손 페이지 틀이다 — 먹색 칩, 문서 h1 토큰, 공용 푸터(hand-11)."""
    for path, body in MQ.pages():
        assert body.count(N.HAND_FOOTER) == 1, path
        assert '<div class="chip">' in body and 'font-size:var(--h1-doc)' in body, path
        assert not _floor_breaks(path, body), _floor_breaks(path, body)


EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]')


def _ctas(html):
    return [(h, re.sub(r'<[^>]+>', '', t).strip())
            for h, t in re.findall(r'<a class="cta"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)]


def test_cta_wording():
    """같은 곳으로 가는 퀴즈 CTA 는 한 문구('… 테스트 시작하기', 꼬리 화살표 없음)이고, 손 페이지 단추 글자에는 OS 색 이모지가 없다."""
    bad = []
    for rel in LANDINGS:
        starts = [t for h, t in _ctas(_read(rel)) if h.startswith('/#test-')]
        if len(starts) < 2 or len(set(starts)) != 1 or not starts[0].endswith('테스트 시작하기'):
            bad.append('%s 시작 CTA %s' % (rel, starts))
    for rel in N.HAND_FOOTER_PAGES:
        html = _read(rel)
        for h, t in _ctas(html) + [('button', re.sub(r'<[^>]+>', '', t).strip())
                                     for t in re.findall(r'<button class="cta[^"]*"[^>]*>(.*?)</button>', html, re.S)]:
            if EMOJI.search(t) or '→' in t:
                bad.append('%s 단추 %r' % (rel, t))
    assert not bad, bad


def test_404_offers_a_way_back():
    s = _read('404.html')
    assert re.search(r'<button class="cta sub"[^>]*onclick="history\.back\(\)"[^>]*>이전 페이지로</button>', s), '되돌아가기 단추가 없다'
    assert '<div class="chip">' in s and re.search(r'(?:^|[}\s])\.chip\{[^}]*background:var\(--ink\)', _css(s)), '먹색 머리 칩이 없다'


def test_faq_question_leaves_room_for_the_icon():
    """FAQ 질문(summary)의 오른쪽 안쪽 여백이 펼침 기호(absolute right + 기호 폭)보다 넓다 — 긴 질문 글자가 기호에 닿지 않는다."""
    css = _css(_read('faq/index.html'))
    body = dict(_rules(css))
    pad = re.search(r'padding\s*:\s*([^;]+)', body['summary']).group(1).split()
    right = float({1: pad[0], 2: pad[1], 3: pad[1], 4: pad[1]}[len(pad)].rstrip('px'))
    icon = body['summary::after']
    off = float(re.search(r'right\s*:\s*([\d.]+)px', icon).group(1))
    w = re.search(r'(?:^|;)\s*width\s*:\s*([\d.]+)px', icon)
    width = float(w.group(1)) if w else float(re.search(r'font-size\s*:\s*([\d.]+)px', icon).group(1))
    assert right >= off + width + 8, 'summary 오른쪽 여백 %gpx 가 기호(right %gpx + %gpx)를 비우지 않는다' % (right, off, width)


def test_privacy_key_tables_stack():
    """개인정보 1·2항 표(보유 기간·이전 국가가 든 표)는 좁은 화면에서 행마다 카드로 쌓인다(.scroll.stack) — 칸마다 그 열 머리와 같은
    data-label 이 붙어 열 이름이 카드 안에 보인다. 첫 칸(구분·수탁자)은 카드 제목이라 이름표가 없다."""
    s = _read('privacy/index.html')
    tables = re.findall(r'<div class="scroll stack">\s*<table>(.*?)</table>', s, re.S)
    assert len(tables) == 2, '쌓는 표가 1·2항 둘이 아니다: %d' % len(tables)
    for t in tables:
        heads = re.findall(r'<th>([^<]+)</th>', t)
        assert '보유 기간' in heads or '이전 국가·시점' in heads, heads
        for row in re.findall(r'<tr>(.*?)</tr>', t.split('</thead>', 1)[1], re.S):
            cells = re.findall(r'<td(?: data-label="([^"]*)")?>', row)
            assert cells == [''] + heads[1:], '칸 이름표 %s ≠ 머리 %s' % (cells, heads)
    assert re.search(r'@media \(max-width:600px\)\{\s*\.scroll\.stack\{', _css(s)), '좁은 화면 쌓기 규칙이 없다'
