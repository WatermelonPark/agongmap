# -*- coding: utf-8 -*-
"""시도 리포트·콘텐츠 글·개인정보처리방침의 글자 하한 13px(2026-10-30 디자인 리뷰 — test_view_min_font 의 하한을 넓힌다).

재현한 실제 상태(2026-10-30 main, Chromium 375px 계산값): 시도 리포트의 판정 칩 .sc-tier 11.5px·신호등 .zl-d 11px·분기표
머리 11.5px·추정 칸 .zfut 11px·빵부스러기 12px, 콘텐츠 글의 표 머리 12.5px·이전/다음 라벨·면책 .cdisc 12px(10-31 면책은 공용 푸터로 옮겨 .cdisc 를 걷었다), 개인정보 표
머리 .78rem·칩 12.5px. 핵심 판정 숫자가 가장 작은 글자였다.

어떻게 가리나: 그 페이지가 싣는 CSS(링크한 /app.css + 페이지 안 <style>)의 규칙 가운데, 선택자의 클래스가 **모두 그 페이지
마크업에 있는** 규칙만 센다(손 목록 없음). font-size 가 px·rem 으로 13px 미만이면 빨강.
빼는 것: SVG 글자 규칙(fill: 을 쓰는 규칙 — 지도 라벨·그래프 축, CLAUDE.md 하한의 제외), 홈 전용 #view-home 규칙.

변이(실제로 확인): app.css .sc-tier 를 11.5px 로, make_content_pages .cnote 를 12px 로, 개인정보 th 를 .78rem 으로
되돌리면 각각 빨개진다.
2026-10-31(디자인 리뷰 2차)에 /weekly/·/monthly/·/cycle/ 을 더했다 — 재현한 상태: /weekly/ 머리 일정 줄·TOP 3 기준 줄·지도 캡션·
시군구 표 머리 12~12.5px(뼈대 <style>·make_weekly_page.TABLE_CSS), /monthly/ .secno 11.5px·.toc a 12.5px, /cycle/ 고리 근거 줄
.conf .meta·.read .lab 11.5px 등. 변이(실제로 확인): make_weekly_page 에서 put_min_font 호출을 빼면 /weekly/ 가, make_monthly_page
.secno 를 11.5px 로 되돌리면 /monthly/ 가, app.css .conf .meta 를 11.5px 로 되돌리면 /cycle/ 이 빨개진다.
픽스처: 생성기를 먼저 돌린 저장소의 /zone/서울/·시도 허브·콘텐츠 글 하나·/privacy/ 그대로(게이트와 같은 순서). 페이지가
아직 없으면(생성기 안 돈 사본) 그 페이지만 건너뛴다 — CI 에서는 건너뜀도 실패라 생성기가 돈 상태에서 돈다.
"""
import io
import os
import re
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import content_md as CM  # noqa: E402

MIN = 13.0


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _strip_media(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    out, i = [], 0
    while True:
        m = re.search(r'@media[^{]*\{', css[i:])
        if not m:
            out.append(css[i:])
            break
        out.append(css[i:i + m.start()])
        j, depth = i + m.end(), 1
        start = j
        while depth and j < len(css):
            depth += {'{': 1, '}': -1}.get(css[j], 0)
            j += 1
        out.append(css[start:j - 1])
        i = j
    return ''.join(out)


def _rules(css):
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', _strip_media(css)):
        yield m.group(1).strip(), m.group(2)


def _tokens(css):
    """CSS 변수 가운데 길이 값인 것 → {이름: px}. 같은 이름이 여러 번 정의되면(미디어 구간 포함) **가장 작은 값**을 본다 —
    어느 폭에서든 하한 아래로 내려가면 잡는다."""
    out = {}
    # clamp(최소, 선호, 최대) 는 최소값을 본다(--h1-report 가 그 꼴이다) — 가장 작아질 때가 하한에 걸리는지가 물음이다.
    for name, num, unit in re.findall(r'(--[\w-]+)\s*:\s*(?:clamp\(\s*)?([\d.]+)(px|rem)\b', _strip_media(css)):
        v = float(num) * (16 if unit == 'rem' else 1)
        out[name] = min(v, out.get(name, v))
    return out


def _px(body, tokens=None):
    """규칙의 글자 크기(px). `font-size:var(--이름)` 은 그 변수의 값으로 푼다. 예전엔 변수를 풀지 않고 '크기 없음'으로 넘겨,
    --fs-dense 를 11px 로 바꿔도 이 시험이 초록이었다(2026-11-13 전수 리뷰 — 읽는 문장 여럿이 그 변수로 크기를 받는다)."""
    m = re.search(r'font-size:\s*([\d.]+)(px|rem)\b', body)
    if m:
        return float(m.group(1)) * (16 if m.group(2) == 'rem' else 1)
    m = re.search(r'font-size:\s*var\(\s*(--[\w-]+)', body)
    if m:
        return (tokens or {}).get(m.group(1))
    return None


def _small_rules(rel):
    page = _read(rel)
    return _small_rules_of(page, _read('app.css') if 'href="/app.css"' in page else '')


def _small_rules_of(page, sheet=''):
    css = sheet + ''.join(re.findall(r'<style>(.*?)</style>', page, re.S))
    tokens = _tokens(css)
    body = page[page.find('<body'):]
    have = set()
    for m in re.finditer(r'class="([^"]*)"', body):
        have |= set(m.group(1).split())
    have_tags = set(re.findall(r'<([a-z][a-z0-9]*)\b', body))
    bad = []
    for sel, rb in _rules(css):
        px = _px(rb, tokens)
        if px is None or px >= MIN or 'fill:' in rb or '#view-home' in sel:
            continue
        for one in sel.split(','):
            cls = re.findall(r'\.([A-Za-z][\w-]*)', one)
            tags = set(re.findall(r'(?:^|[\s>+~])([a-z][a-z0-9]*)', one))
            if 'svg' in one or '#' in one or (not cls and not tags & have_tags):
                continue
            if all(c in have for c in cls):
                bad.append('%s %gpx' % (one.strip(), px))
    return bad


def _pages():
    out = ['zone/서울/index.html', 'zone/index.html', 'privacy/index.html',
           'weekly/index.html', 'monthly/index.html', 'cycle/index.html']   # 2026-10-31 디자인 리뷰 2차에서 넓혔다
    built = CM.built(ROOT)
    if built:
        sec, slug, _ = built[0]
        out.append('%s/%s/index.html' % (sec, slug))
    return out


@pytest.mark.parametrize('rel', _pages())
def test_report_content_and_privacy_text_is_at_least_13px(rel):
    if not os.path.exists(os.path.join(ROOT, rel)):
        pytest.skip('%s 가 아직 구워지지 않았다' % rel)
    bad = _small_rules(rel)
    assert not bad, '%s 에 13px 미만 글자 규칙: %s' % (rel, bad)


def test_font_sizes_given_by_a_css_variable_are_measured():
    """글자 크기를 CSS 변수로 받는 규칙도 잰다 — 변수 값이 하한 아래면 잡는다.

    왜: 이 시험은 `font-size:var(--fs-dense)` 를 '크기 없음'으로 넘겼다. 그 변수를 11px 로 바꿔 다시 구워도 글자·디자인·접근성
        시험 644개가 초록이었다 — 리포트의 읽는 문장 여럿(.zwk-lead·.zyear·.note)이 그 변수로 크기를 받는다.
    변이(실제로 확인): _px 에서 var(...) 갈래를 지우면 첫 단정이 빨개진다. _tokens 가 첫 정의만 보면(가장 작은 값을 보지 않으면)
          셋째 단정이 빨개진다.
    픽스처: 변수로 크기를 받는 규칙 하나가 든 합성 페이지 — 변수 값이 하한 아래, 하한, 그리고 좁은 화면에서만 하한 아래인 세 꼴.
            그리고 저장소의 실제 리포트가 변수로 크기를 받는 규칙을 실제로 갖고 있는지(이 시험이 재는 것이 실재하는지).
    """
    page = '<style>:root{--fs-x:%s}%s.note{font-size:var(--fs-x)}</style><body><p class="note">글</p></body>'
    assert _small_rules_of(page % ('11px', '')) == ['.note 11px']
    assert _small_rules_of(page % ('%dpx' % MIN, '')) == []
    assert _small_rules_of(page % ('14px', '@media(max-width:400px){:root{--fs-x:12px}}')) == ['.note 12px']
    rel = 'zone/서울/index.html'
    if not os.path.exists(os.path.join(ROOT, rel)):
        pytest.skip('%s 가 아직 구워지지 않았다' % rel)
    css = _read('app.css') + ''.join(re.findall(r'<style>(.*?)</style>', _read(rel), re.S))
    used = set(re.findall(r'font-size:\s*var\(\s*(--[\w-]+)', css))
    assert used, '리포트에 변수로 크기를 받는 규칙이 없다 — 이 시험의 전제를 다시 볼 것'
    missing = sorted(used - set(_tokens(css)))
    assert not missing, '크기 변수의 값을 찾지 못했다(하한을 잴 수 없다): %s' % missing
