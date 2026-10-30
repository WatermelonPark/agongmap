# -*- coding: utf-8 -*-
"""시도 리포트·콘텐츠 글·개인정보처리방침의 글자 하한 13px(2026-10-30 디자인 리뷰 — test_view_min_font 의 하한을 넓힌다).

재현한 실제 상태(2026-10-30 main, Chromium 375px 계산값): 시도 리포트의 판정 칩 .sc-tier 11.5px·신호등 .zl-d 11px·분기표
머리 11.5px·추정 칸 .zfut 11px·빵부스러기 12px, 콘텐츠 글의 표 머리 12.5px·이전/다음 라벨·면책 .cdisc 12px, 개인정보 표
머리 .78rem·칩 12.5px. 핵심 판정 숫자가 가장 작은 글자였다.

어떻게 가리나: 그 페이지가 싣는 CSS(링크한 /app.css + 페이지 안 <style>)의 규칙 가운데, 선택자의 클래스가 **모두 그 페이지
마크업에 있는** 규칙만 센다(손 목록 없음). font-size 가 px·rem 으로 13px 미만이면 빨강.
빼는 것: SVG 글자 규칙(fill: 을 쓰는 규칙 — 지도 라벨·그래프 축, CLAUDE.md 하한의 제외), 홈 전용 #view-home 규칙.

변이(실제로 확인): app.css .sc-tier 를 11.5px 로, make_content_pages .cdisc 를 12px 로, 개인정보 th 를 .78rem 으로
되돌리면 각각 빨개진다.
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


def _px(body):
    m = re.search(r'font-size:\s*([\d.]+)(px|rem)\b', body)
    if not m:
        return None
    return float(m.group(1)) * (16 if m.group(2) == 'rem' else 1)


def _small_rules(rel):
    page = _read(rel)
    css = ''.join(re.findall(r'<style>(.*?)</style>', page, re.S))
    if 'href="/app.css"' in page:
        css = _read('app.css') + css
    body = page[page.find('<body'):]
    have = set()
    for m in re.finditer(r'class="([^"]*)"', body):
        have |= set(m.group(1).split())
    have_tags = set(re.findall(r'<([a-z][a-z0-9]*)\b', body))
    bad = []
    for sel, rb in _rules(css):
        px = _px(rb)
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
    out = ['zone/서울/index.html', 'zone/index.html', 'privacy/index.html']
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
