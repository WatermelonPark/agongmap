# -*- coding: utf-8 -*-
"""조판 치수 토큰을 고정한다(백로그 24, 2026-09-18 디자인 오딧 6번).

재현하는 실제 상태: 오딧이 1280px 에서 잰 값이다. h1 이 34(월간)·36(FAQ·소개)·38(주간)·40(홈·퀴즈)·42(시도)·
62px(사이클) 여섯 가지, 본문 단 폭이 516·576·772·832px 네 가지, 본문 글자가 13·14.5·15·16px 네 가지였다.
원인은 페이지군마다 style 블록을 따로 들고 있어서다(app.css 를 쓰는 곳은 홈·시도·사이클뿐).

그래서 app.css :root 에 두 단계씩의 토큰을 정본으로 두고,
  - 지표 생성기(월간·입주·전세가율)는 생성할 때 그 선언을 읽어 싣는다(make_indicator_pages.type_tokens),
  - 손으로 쓴 페이지(주간 틀·FAQ·소개·개인정보·퀴즈 3종)는 같은 줄을 사본으로 든다.
이 시험이 사본과 정본의 일치, 그리고 각 페이지군의 h1·단 폭·본문이 토큰을 쓰는지를 본다.

무엇을 깨뜨리면 빨개지나(실제로 확인):
  - app.css 의 --h1-doc 을 clamp(26px,5.6vw,36px) 로 바꾸면 사본 여섯 곳이 갈려 test_token_copies_match 가 빨개진다.
  - faq 의 h1 을 옛 값 clamp(26px,6vw,36px) 로 되돌리면 test_page_families_use_the_tokens 가 빨개진다.
  - privacy 의 .wrap 을 760px 로, about 의 p 를 15px 로 되돌려도 같은 시험이 빨개진다.
  - 사이클 절 제목을 옛 문장 "집이 모자란 곳에서, 전세가 먼저 오른다" 로 되돌리면 test_cycle_section_titles_fit 가 빨개진다.
"""
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 손으로 쓴 페이지 → (h1 단계, 본문 단계). app.css 를 읽지 않아 토큰 사본을 들고 있어야 하는 곳.
HAND = {
    'weekly/index.html': ('report', 'dense'),
    'faq/index.html': ('doc', 'read'),
    'about/index.html': ('doc', 'read'),
    'privacy/index.html': ('doc', 'read'),
    'burini-test/index.html': ('report', 'read'),
    'investor-test/index.html': ('report', 'read'),
    'redev-test/index.html': ('report', 'read'),
}


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _decls(css):
    """토큰 이름 → 값. 같은 이름이 두 번 선언되면 둘 다 모아 돌려준다(갈림을 숨기지 않는다)."""
    out = {}
    for name in I.TYPE_TOKENS:
        out[name] = [v.strip() for v in re.findall(r'(?<![\w-])' + re.escape(name) + r'\s*:\s*([^;}]+)[;}]', css)]
    return out


def _style(html):
    return ''.join(re.findall(r'<style[^>]*>(.*?)</style>', html, re.S))


def _rule(css, selector):
    """선택자 하나의 선언 블록(첫 번째). 없으면 None."""
    m = re.search(r'(?:^|[}\s])' + re.escape(selector) + r'\{([^}]*)\}', css)
    return m.group(1) if m else None


def test_app_css_declares_each_token_once():
    d = _decls(_read('app.css'))
    for name, vals in d.items():
        assert len(vals) == 1, 'app.css 에 %s 선언이 %d개다 — 정본은 하나여야 한다' % (name, len(vals))


def test_token_copies_match():
    canon = {k: v[0] for k, v in _decls(_read('app.css')).items()}
    for rel in HAND:
        got = _decls(_style(_read(rel)))
        for name, want in canon.items():
            assert got[name] == [want], '%s 의 %s 가 정본(app.css %s)과 다르다: %s' % (rel, name, want, got[name])
    # 생성기는 app.css 를 읽어 싣는다 — 껍데기에 자리표시가 있고, 채운 결과에 정본 값이 그대로 들어가야 한다.
    assert '__TOKENS__' in I.SHELL, '지표 껍데기에 토큰 자리(__TOKENS__)가 없다'
    filled = _decls(_style(I.fill(I.SHELL, title='t', body='')))
    for name, want in canon.items():
        assert filled[name] == [want], '지표 생성기의 %s 가 정본과 다르다: %s' % (name, filled[name])


def test_page_families_use_the_tokens():
    """각 페이지군의 h1·단 폭·본문 글자가 토큰을 쓴다(숫자를 다시 박으면 빨개진다)."""
    app = _read('app.css')
    shell = _style(I.SHELL)
    checks = [
        ('app.css .zhead h1(시도 리포트·허브)', _rule(app, '.zhead h1'), 'font-size', 'var(--h1-report)'),
        ('app.css .hero h1(사이클 표지)', _rule(app, '.hero h1'), 'font-size', 'var(--h1-report)'),
        ('app.css .wrap', _rule(app, '.wrap'), 'max-width', 'var(--col-wide)'),
        ('app.css p', _rule(app, 'p'), 'font-size', 'var(--fs-read)'),
        ('지표 껍데기 h1', _rule(shell, 'h1'), 'font-size', 'var(--h1-doc)'),
        ('지표 껍데기 .wrap', _rule(shell, '.wrap'), 'max-width', 'var(--col-read)'),
        ('지표 껍데기 p', _rule(shell, 'p'), 'font-size', 'var(--fs-read)'),
    ]
    for rel, (h1, body) in HAND.items():
        css = _style(_read(rel))
        checks.append((rel + ' h1', _rule(css, 'h1'), 'font-size', 'var(--h1-%s)' % h1))
        checks.append((rel + ' .wrap', _rule(css, '.wrap'), 'max-width', 'var(--col-read)'))
        p = _rule(css, 'details p') if rel.startswith('faq') else (_rule(css, 'p') or _rule(css, 'body'))
        if rel.startswith('privacy'):
            p = _rule(css, 'body')          # 개인정보는 본문 글자를 body 에 둔다
        checks.append((rel + ' 본문', p, 'font-size', 'var(--fs-%s)' % body))
    bad = []
    for what, block, prop, want in checks:
        if block is None:
            bad.append('%s: 규칙을 찾지 못했다' % what)
            continue
        m = re.search(r'(?<![\w-])' + prop + r'\s*:\s*([^;]+)', block)
        if not m or m.group(1).strip() != want:
            bad.append('%s: %s 가 %s 가 아니다(%s)' % (what, prop, want, m.group(1).strip() if m else '없음'))
    assert not bad, '\n'.join(bad)


# /cycle/ 절 제목(백로그 24 잔여, 오딧 8번). 375px 에서 7개(Pretendard 기준, 오딧 당시 9개)가 두 줄로 꺾였다.
# 부연은 .t-sub 부제 줄로 내렸다. 줄 수는 브라우저가 정하지만, 제목 줄 폭은 운영 글꼴(tools/fonts 의 Pretendard Bold,
# h2 는 700)로 미리 잴 수 있다 — Chromium 에 같은 글꼴을 물려 잰 폭과 소수점까지 같았다(294.19 vs 294.1, 2026-09-23).
# 기준 폭과 글자 크기는 app.css 에서 읽는다(375px − .wrap 좌우 여백, clamp 최소값).
VIEWPORT = 375


def _cycle_title_budget(app, selector):
    rule = _rule(app, selector)
    size = int(re.search(r'font-size:clamp\((\d+)px', rule).group(1))
    track = float(re.search(r'letter-spacing:(-?[\d.]+)em', rule).group(1))
    pad = int(re.search(r'padding:0 (\d+)px', _rule(app, '.wrap')).group(1))
    return size, track, VIEWPORT - 2 * pad


def test_cycle_section_titles_fit():
    ImageFont = pytest.importorskip('PIL.ImageFont')
    app = _read('app.css')
    s = _read('cycle/index.html')
    heads = re.findall(r'<h2 class="(t|tldr-h)"[^>]*>(.*?)</h2>', s, re.S)
    assert len(heads) >= 10, '사이클 절 제목을 찾지 못했다 — 마크업이 바뀌었으면 이 시험도 고칠 것'
    font_path = os.path.join(ROOT, 'tools', 'fonts', 'Pretendard-Bold.subset.ttf')
    long_ = []
    for cls, inner in heads:
        title = re.sub(r'<[^>]+>', '', inner.split('<span class="t-sub">')[0]).strip()
        size, track, width = _cycle_title_budget(app, 'h2.t' if cls == 't' else '.tldr-h')
        w = ImageFont.truetype(font_path, size).getlength(title) + track * size * len(title)
        if w > width:
            long_.append('%s(%.0fpx > %dpx)' % (title, w, width))
    assert not long_, '%dpx 에서 두 줄로 꺾일 절 제목: %s — 부연은 <span class="t-sub"> 로 내릴 것' % (VIEWPORT, long_)
