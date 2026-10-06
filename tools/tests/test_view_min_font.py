# -*- coding: utf-8 -*-
"""시세 탭·퀴즈 화면·푸터 글자 하한 13px(백로그 36-3, 2026-10-06) — 홈의 하한(test_home_min_font, 2026-09-28 대표 결정)을 넓힌다.

재현한 실제 상태(2026-10-06 main, Chromium 375px 계산값): 시세 탭에 13px 미만 글자가 서른 갈래 넘게 있었다 — 발표 일정 .rel 11.5px,
TOP 10 머리 11px·표 12~12.5px·순위 변동 12px, 출처 .src-note 11.5px, 그래프·표 단추 12px, 버블밴드 칩 11px, 기본통계 단추 12.5px,
퀴즈 결과 .rc-hint 11.5px, 모든 화면 푸터(.legal-disc·.ft-src 11.5px, .ft-meta·.minifooter 12px).

어떻게 가리나 — test_home_min_font 의 CSS 읽기를 그대로 쓰고, 토큰만 이 화면들에서 센다(손 목록 없음):
  - 시세 탭 토큰: index.html 의 #view-stats 마크업(class·id) + home-stats.js 가 class="…" 로 굽는 클래스.
  - 퀴즈 토큰: index.html 의 #view-test 마크업 + home-quiz.js 가 굽는 클래스.
  - 푸터 토큰: 모든 화면의 .minifooter 안 마크업.
  - 규칙의 클래스·아이디가 모두 (위 셋 ∪ 홈 토큰)이고, 하나라도 위 셋에만 있는 토큰이면 13px 이상이어야 한다.
빼는 것: SVG 글자(그래프 축·지도 라벨 — test_home_min_font 와 같은 까닭), 기본통계 규모별 표 둘째 줄(#stat-tbl .szsub — 18열 머리에
  두 줄로 들어가는 칸 이름), 홈 표 보기 20열 표(#tb-main — 홈 시험이 따로 뺀다).

변이(각각 실제로 넣어 빨간 것을 확인): .rel 을 11.5px 로, .legal-disc 를 11.5px 로, .rc-hint 를 11.5px 로 되돌리면 빨강.
픽스처: 저장소 app.css·index.html·home-stats.js·home-quiz.js 그대로(데이터와 무관 — 날짜가 앞으로 가도 같은 답).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_home_min_font as H  # noqa: E402  (CSS 읽기·토큰 뽑기를 홈 시험과 같은 함수로)

EXEMPT_SUBJECT = {'szsub'}      # 규모별 표 18열 머리의 둘째 줄


def _view(idx, start, end):
    a = idx.index(start)
    b = idx.index(end, a)
    return idx[a:b]


def _markup_tokens(html):
    out = set()
    for m in re.finditer(r'class="([^"]*)"', html):
        out |= set(m.group(1).split())
    out |= {'#' + x for x in re.findall(r'\bid="([^"]+)"', html)}
    return out


def _tokens():
    f = H._files()
    idx = f['index.html']
    stats = _view(idx, '<div id="view-stats"', '<div id="view-test"')
    test = _view(idx, '<div id="view-test"', '<nav class="bottomnav">')
    foot = ''.join(re.findall(r'<div class="minifooter">.*?\n  </div>', idx, re.S))
    view = _markup_tokens(stats) | _markup_tokens(test)
    view |= H._class_attr_tokens(H._js_strings(f['home-stats.js'])) | H._class_attr_tokens(H._js_strings(f['home-quiz.js']))
    feet = _markup_tokens(foot)          # 푸터는 홈에도 있지만(홈은 #view-home 으로 덮는다) 전역 규칙 자체가 13px 이상이어야 한다
    home = H._home_tokens()[0]
    return (view - home) | feet, view | feet | home


def _classify():
    css_rules = H._rules(H._read('app.css'))
    for block in re.findall(r'<style>(.*?)</style>', H._files()['index.html'], re.S):
        css_rules += H._rules(block)
    rootv = H._root_vars(css_rules)
    own, allowed = _tokens()
    checked, bad = [], []
    for media, sel, body in css_rules:
        px = H._font_px(body, rootv)
        if px is None:
            continue
        toks = H._tokens(sel)
        if not toks or not toks <= allowed or not toks & own:
            continue
        el, subj = H._subject(sel)
        if el == 'text' or H.TABLE_ID in toks or (subj and subj <= EXEMPT_SUBJECT) or sel.startswith(H.SCOPE + ' '):
            continue
        checked.append(sel)
        if not px >= H.MIN_PX:
            bad.append('%s%s{%.1fpx}' % (('@media' + media + ' ') if media else '', sel, px))
    return checked, bad


def test_stats_quiz_and_footer_text_is_at_least_13px():
    checked, bad = _classify()
    assert not bad, '시세 탭·퀴즈·푸터 글자가 13px 아래다(백로그 36-3):\n' + '\n'.join(bad)
    # 추출기 점검 — 비면 조용히 초록이 된다
    for want in ('.rel', '.src-note', '.legal-disc', '.ft-src', '.rc-hint', '.rk-up', '.gt button'):
        assert any(want in s for s in checked), '%s 규칙을 읽지 못했다 — 추출기를 볼 것' % want


def test_stats_and_quiz_inline_styles_are_at_least_13px():
    """시세 탭·퀴즈 마크업과 두 스크립트 문자열의 style="…font-size:…" 도 13px 이상이다."""
    f = H._files()
    idx = f['index.html']
    blob = _view(idx, '<div id="view-stats"', '<nav class="bottomnav">') + H._js_strings(f['home-stats.js']) + H._js_strings(f['home-quiz.js'])
    small = [m.group(0)[-60:] for m in re.finditer(r'style="[^"]*font-size:\s*([\d.]+)px', blob) if float(m.group(1)) < H.MIN_PX]
    # 스크립트가 굽는 <style> 조각(버블밴드 값 글자 .bb-v 가 여기 있었다 — 11px)
    for block in re.findall(r'<style>(.*?)</style>', blob, re.S):
        small += ['<style> %s' % sel for _, sel, body in H._rules(block)
                  if (H._font_px(body, {}) or 99) < H.MIN_PX]
    assert not small, small
