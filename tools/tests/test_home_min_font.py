# -*- coding: utf-8 -*-
"""홈 화면 글자 하한 13px(2026-09-28 대표 결정 — 홈 작은 글씨 정리)을 CSS 정적 검사로 고정한다.

재현한 실제 상태(2026-09-27 main, Chromium 계산값): 홈(#view-home 과 홈 푸터)에 13px 미만 글자가 서른 곳 넘게 있었다 —
등급 배지 11px·카드 셋째 줄 11.5px·범례 11~11.5px·지도 아래 두 줄 12px·주간 머리줄 12px·격자 지역 이름 11px·표지 10.5px·
전세 값 11px·퀴즈 '결과 예시' 11.5px·푸터 11.5~12.5px 등. 대표가 고른 줄은 지우고 남은 글자는 13px 이상으로 키웠다.
이 시험은 브라우저 없이(CI 에 playwright 가 없다) app.css·index.html <style> 의 font-size 선언을 읽어, 홈 요소에 걸릴 수 있는
규칙이 13px 아래를 말하지 않는지 본다.

어떻게 '홈 요소에 걸리는 규칙'을 가리나 — 손 목록 없이 마크업·스크립트에서 센다:
  - 홈 토큰: index.html 의 #view-home 마크업(class·id)·하단 탭바(모든 페이지 공용 — 라벨 크기는 site_nav.LABEL_PX, test_site_nav)와
    body 표지, home-app.js 문자열 안의 클래스 이름.
  - 규칙의 클래스·아이디가 모두 홈 토큰이어야 홈에 걸릴 수 있다(:not(…) 안은 세지 않는다). 하나라도 홈에 없는 토큰이면 다른
    화면(시도 리포트·통계 탭 등)의 규칙이다.
  - 홈에만 있는 토큰이 하나라도 있으면 그 규칙은 13px 이상이어야 한다.
  - 모든 토큰이 다른 페이지와 같이 쓰는 공용 클래스(.sc-tier·.ft-src·.legal-disc 등 — 저장소의 다른 HTML·통계/퀴즈 화면에도
    있다)면 전역 규칙은 그대로 두고, 홈 안에서만 '#view-home <그 클래스>' 로 13px 이상을 덮는 규칙이 더 높은 특이도로 있어야
    한다(시도 리포트의 고정폭 배지 62px 를 건드리지 않기 위해).
빼는 것(대표 지시와 기하 제약 — 현재 크기는 보고로만 남긴다):
  - SVG 글자: 지도 지역 라벨(.map-box text — viewBox 가 줄어 320px 에서 7.5~8.4px 로 그려진다), 그래프 축 글자(<text> 의
    클래스 — home-app.js 에서 센다), 사이클 도식(index.html 의 font-size 속성). 도형 크기·라벨 상자가 글자에 묶여 있다.
  - 표 보기의 20열 표(#tb-main, 표를 굽는 함수 tbDraw·refBtn 에서만 나오는 클래스): 줄 높이 25px·붙박이 표두 둘째 줄 top 30px·
    참고 행 bottom 27px 가 11~12px 글자에 맞춰져 있다. 표 밖의 표 보기 조작부(범례·기간·대비·설명)는 13px 이상이다.

변이(각각 실제로 넣어 빨간 것을 확인): .hs-kicker 를 12px 로, 주간 지도 아랫줄 .wg-foot 을 12px 로 내리면 홈 전용 규칙 단정이,
520px 이하 미디어에 `.wg-foot{font-size:11.5px}` 를 넣으면 같은 단정이(미디어 안도 본다), 덮기 규칙에서 '#view-home .sc-tier' 를
빼면 공용 규칙 단정이, 퀴즈 '결과 예시'(.qs-label)를 11.5px 로 되돌리면 홈 전용 규칙 단정이, 하단 탭바 .nav-btn 을 11.5px 로
되돌리면 공용 규칙 단정이 빨개진다.
픽스처: 저장소 app.css·index.html·home-app.js 그대로(데이터와 무관 — 날짜가 앞으로 가도 같은 답).
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
MIN_PX = 13.0
SCOPE = '#view-home'                 # 공용 클래스를 홈에서만 덮을 때 쓰는 머리(홈 푸터도 이 안에 있다)
TABLE_ID = '#tb-main'                # 표 보기 20열 표
TABLE_FUNCS = ('tbDraw', 'refBtn')   # 그 표를 굽는 함수 — 여기서만 나오는 클래스는 표 안 글자다
STATS_MARK = '<!-- ===== 통계보기 대시보드 ===== -->'


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _files():
    return dict(HS.home_files())


# ── JS 문자열·함수 ────────────────────────────────────────────────────────────────────────────────

def _js_strings(src):
    """JS 소스의 문자열 리터럴 내용(작은따옴표·큰따옴표·백틱)만 이어 붙인다. 주석은 건너뛴다(주석 속 따옴표에 속지 않게)."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith('//', i):
            i = src.find('\n', i)
            i = n if i < 0 else i
        elif src.startswith('/*', i):
            i = src.find('*/', i + 2)
            i = n if i < 0 else i + 2
        elif c in '\'"`':
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == '\\':
                    j += 1
                elif src[j] == '\n' and c != '`':
                    break
                j += 1
            out.append(src[i + 1:j])
            i = j + 1
        else:
            i += 1
    return '\n'.join(out)


def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i, depth = src.index('{', m.end()), 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _has_token(blob, tok):
    return re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(tok), blob) is not None


# ── CSS ──────────────────────────────────────────────────────────────────────────────────────────

def _split_top(s, sep=','):
    out, depth, cur = [], 0, ''
    for ch in s:
        depth += {'(': 1, ')': -1}.get(ch, 0)
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def _rules(css, media=''):
    """[(미디어 조건, 선택자, 선언)] — 주석을 벗기고 @media 안까지. @font-face·@keyframes 등은 건너뛴다."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out, i = [], 0
    while True:
        j = css.find('{', i)
        if j < 0:
            return out
        pre = css[i:j].strip()
        k, depth = j + 1, 1
        while depth:
            depth += {'{': 1, '}': -1}.get(css[k], 0)
            k += 1
        body = css[j + 1:k - 1]
        if pre.startswith('@media'):
            out += _rules(body, pre[len('@media'):].strip())
        elif not pre.startswith('@'):
            out += [(media, sel, body) for sel in _split_top(pre)]
        i = k


def _root_vars(rules):
    v = {}
    for media, sel, body in rules:
        if sel == ':root' and not media:
            v.update(re.findall(r'(--[\w-]+)\s*:\s*([^;]+)', body))
    return v


def _font_px(body, rootv):
    """선언의 글자 크기 하한(px). 없으면 None. clamp()·min()·max() 는 가장 작은 px, var() 는 :root 값으로 푼다.
    px 로 풀 수 없는 값(em·% 등)은 NaN — 홈 규칙이면 실패로 알린다(이 시험이 모르는 단위)."""
    vals = re.findall(r'(?:^|;)\s*font-size\s*:\s*([^;]+)', body)
    vals += [v for v in re.findall(r'(?:^|;)\s*font\s*:\s*([^;]+)', body) if re.search(r'\d(?:px|em|%)', v)]
    if not vals:
        return None
    lo = None
    for v in vals:
        v = re.sub(r'var\((--[\w-]+)\)', lambda m: rootv.get(m.group(1), m.group(0)), v.strip())
        if v in ('inherit', 'initial', 'unset'):
            continue
        px = [float(x) for x in re.findall(r'([\d.]+)px', v)]
        if not px or re.search(r'\d(?:em|rem|%)', v):
            return float('nan')
        lo = min(px) if lo is None else min(lo, min(px))
    return lo


def _compounds(sel):
    s = re.sub(r':not\([^)]*\)', '', sel)
    return [c for c in re.split(r'\s*[>+~]\s*|\s+', s.strip()) if c]


def _tokens(sel):
    s = re.sub(r':not\([^)]*\)', '', sel)
    return set(re.findall(r'\.([\w-]+)', s)) | {'#' + x for x in re.findall(r'#([\w-]+)', s)}


def _subject(sel):
    c = _compounds(sel)[-1]
    el = re.match(r'[a-z][a-z0-9]*', c)
    return (el.group(0) if el else ''), _tokens(c)


def _spec(sel):
    inner = ' '.join(re.findall(r':not\(([^)]*)\)', sel))
    s = re.sub(r':not\([^)]*\)', '', sel) + ' ' + inner
    ids = len(re.findall(r'#[\w-]+', s))
    cls = len(re.findall(r'\.[\w-]+|\[[^\]]*\]|(?<!:):(?!:)[\w-]+', s))
    els = len(re.findall(r'(?:^|[\s>+~])[a-z][a-z0-9]*', s)) + s.count('::')
    return (ids, cls, els)


# ── 홈 토큰 ───────────────────────────────────────────────────────────────────────────────────────

def _class_attr_tokens(text):
    out = set()
    for m in re.finditer(r'class=\\?"([^"\\]*)', text):
        out |= {t for t in m.group(1).split() if re.fullmatch(r'[\w-]+', t)}
    return out


def _home_tokens():
    """(홈 마크업 토큰, 홈 스크립트 판정 함수 재료, 표 안에서만 나오는 문자열, SVG 글자 클래스, 다른 화면 토큰, 분할 파일 문자열).

    스크립트 문자열의 클래스는 두 갈래로 센다: ① class="…" 로 굽는 것은 그대로 홈 토큰, ② 인자로 넘겨 붙이는 것('wc wc-agg')은
    문자열 속 낱말이라 다른 뜻('adv' 모드 이름, '.nav-btn' 탭바 선택자)과 섞인다 — index.html 의 홈 밖 마크업(탭바·통계·퀴즈
    화면)에 있는 클래스면 홈 토큰으로 치지 않는다."""
    f = _files()
    idx, app = f['index.html'], f['home-app.js']
    a, b = idx.index('<div id="view-home">'), idx.index(STATS_MARK)
    nav = re.search(r'<nav class="bottomnav">.*?</nav>', idx, re.S)   # 하단 탭바도 홈 화면 글자다(2026-09-28 검토)
    view = idx[a:b] + nav.group(0)
    outside = idx[:a] + idx[b:nav.start()] + idx[nav.end():]
    home = set()
    for m in re.finditer(r'class="([^"]*)"', view):
        home |= set(m.group(1).split())
    home |= {'#' + x for x in re.findall(r'\bid="([^"]+)"', view)}
    home |= set(re.search(r'<body class="([^"]*)"', idx).group(1).split())
    table_src = ''.join(_js_func(app, n) for n in TABLE_FUNCS)
    rest = app
    for n in TABLE_FUNCS:
        rest = rest.replace(_js_func(app, n), '')
    s_rest, s_table = _js_strings(rest), _js_strings(table_src)
    built = _class_attr_tokens(s_rest)
    outside_tok = set()
    for m in re.finditer(r'class="([^"]*)"', outside):
        outside_tok |= set(m.group(1).split())
    svg = set()
    for m in re.finditer(r'<text[^>]*class="([\w -]+)"', app):
        svg |= set(m.group(1).split())
    other = set(outside_tok)
    for path in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
        rel = os.path.relpath(path, ROOT)
        if rel == 'index.html' or rel.startswith(('tools' + os.sep, 'docs' + os.sep, '.')):
            continue
        for m in re.finditer(r'class="([^"]*)"', io.open(path, encoding='utf-8').read()):
            other |= set(m.group(1).split())
    parts = '\n'.join(_js_strings(f[p]) for p in HS.PARTS)
    other |= _class_attr_tokens(parts)   # 통계·퀴즈 화면이 굽는 클래스(table.adv 등)
    return home, (built, s_rest, outside_tok), s_table, svg, other, parts


def _classify():
    css_rules = _rules(_read('app.css'))
    for block in re.findall(r'<style>(.*?)</style>', _files()['index.html'], re.S):
        css_rules += _rules(block)
    rootv = _root_vars(css_rules)
    home, (built, s_rest, outside_tok), s_table, svg, other, parts = _home_tokens()

    def in_home(t):
        if t in home or t in built:
            return True
        return not t.startswith('#') and t not in outside_tok and t not in other and _has_token(s_rest, t)

    def in_table(t):
        return not in_home(t) and not t.startswith('#') and _has_token(s_table, t)

    def shared(t):
        return t in other or (not t.startswith('#') and _has_token(parts, t))

    checked, exempt, bad, overrides = [], [], [], []
    for media, sel, body in css_rules:
        px = _font_px(body, rootv)
        if sel.startswith(SCOPE + ' ') and px is not None and px >= MIN_PX and not media:
            overrides.append((sel[len(SCOPE) + 1:], _spec(sel)))
    for media, sel, body in css_rules:
        px = _font_px(body, rootv)
        if px is None:
            continue
        toks = _tokens(sel)
        if not toks or any(not (in_home(t) or in_table(t)) for t in toks):
            continue                                    # 다른 화면(또는 요소만 쓰는 전역) 규칙
        el, subj = _subject(sel)
        why = ('표 보기 20열 표' if TABLE_ID in toks or (subj and all(in_table(t) for t in subj))
               else 'SVG 글자' if el == 'text' or (subj and subj <= svg) else None)
        if why:
            exempt.append((why, media, sel, px))
            continue
        checked.append((media, sel, px))
        if px >= MIN_PX:
            continue
        if any(in_home(t) and not shared(t) for t in toks):
            bad.append('%s%s{font-size ≥ %.1fpx} — 홈 전용 규칙' % (('@media' + media + ' ') if media else '', sel, px))
            continue
        ok = any(subj <= _tokens(o) and _subject(o)[1] >= subj and ospec > _spec(sel) for o, ospec in overrides)
        if not ok:
            bad.append('%s%s{%.1fpx} — 공용 클래스인데 홈에서 %s 로 13px 이상을 덮는 규칙이 없다'
                       % (('@media' + media + ' ') if media else '', sel, px, SCOPE))
    return checked, exempt, bad


def test_home_text_is_at_least_13px():
    checked, exempt, bad = _classify()
    assert not bad, '홈 화면 글자가 13px 아래다(2026-09-28 대표 결정 — 하한 13px):\n' + '\n'.join(bad)
    # 분류기 자체 점검 — 마크업에서 온 것(.hs-kicker), 스크립트에서만 온 것(.wg-foot·.gr-note), 공용 덮기(.sc-tier),
    # 표 안(.ri), SVG(.gr-rt·지도 라벨)가 각자 제 자리에 가야 이 시험이 무엇이든 본다(추출이 비면 조용히 초록이 된다).
    sels = {s for _, s, _ in checked}
    for want in ('.hs-kicker', '.wg-foot', '.gr-note', '.sc-tier', '#view-home .sc-tier', '.nav-btn'):
        assert want in sels or any(want in s for s in sels), '%s 규칙을 홈 규칙으로 읽지 못했다 — 추출기를 볼 것' % want
    ex = {(w, s) for w, _, s, _ in exempt}
    assert ('표 보기 20열 표', '.ri') in ex and ('SVG 글자', '.gr-box .gr-rt') in ex and ('SVG 글자', '.map-box text.ml-s') in ex, ex


def test_home_inline_styles_are_at_least_13px():
    """홈 마크업·홈 스크립트 문자열의 style="…font-size:…" 도 13px 이상이다(SVG 의 font-size 속성은 위와 같은 까닭으로 뺀다).
    변이: 홈 격자 칸에 style="font-size:11px" 를 넣으면 빨개진다(확인)."""
    f = _files()
    idx = f['index.html']
    view = idx[idx.index('<div id="view-home">'):idx.index(STATS_MARK)]
    blob = view + '\n' + _js_strings(f['home-app.js'])
    small = [m.group(0) for m in re.finditer(r'style="[^"]*font-size:\s*([\d.]+)px', blob) if float(m.group(1)) < MIN_PX]
    assert not small, small
