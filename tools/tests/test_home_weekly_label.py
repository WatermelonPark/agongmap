# -*- coding: utf-8 -*-
"""홈 '이번 주 시군구 지도' 구역의 머리말 한 줄(백로그 45, 2026-10-16 대표 승인).

재현하는 실제 상태: 10-03 에 날짜 머리줄을 뺀 뒤 이 구역 h2 는 매주 결론 문장('경기 +0.26%, 가장 크게 올랐습니다')뿐이라,
휴대폰에서 모드 단추 '월간 시세'를 고르고 내려온 사람이 바로 아래 주간 시군구 격자를 월간 결과로 읽었다(대표 제보, 375px 재현).
그래서 h2 위에 날짜 없는 구역 이름 한 줄(#wk-label, .hs-kicker — 홈 다른 구역 머리말과 같은 모양)을 둔다. 10-03 에 뺀 날짜
머리줄의 id(wk-kicker)는 쓰지 않는다 — test_weekly_release 가 그 머리줄이 되살아나지 않는지 따로 본다. 고정 문구라 applyWeeklyStatus 가
바꾸지 않고(늦은 주 발표일 접두는 h2 에), 문구는 모드 단추 이름('주간 시세')을 그대로 쓰고 단위('시군구')를 붙인다 — 요청서 예시
'이번 주 시군구 시세'보다 단추와 같은 말이라야 위아래가 이어져 읽힌다(요청서도 그렇게 권한다).
픽스처: 저장소 index.html·home-app.js(home_src)·make_naver_post.WEEKLY_SHOTS.

변이(각각 실제로 확인): 머리말을 지우거나 h2 아래로 옮기면, 문구를 모드 단추 이름과 다르게('이번 주 시군구 시세') 쓰면, applyWeeklyStatus 가 머리말을
건드리면, 블로그 캡처 상자를 홈 주간 구역으로 바꾸면 빨개진다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_naver_post as P  # noqa: E402

KICKER = '주간 시세 · 시군구'        # 머리말 문구 — 시험은 이 상수를 마크업에서 찾는다(문구를 여러 곳에 박지 않는다)


def _files():
    return dict(HS.home_files())


def _weekly_section(html):
    i = html.index('id="home-weekly-grid"')
    return html[html.rindex('<section', 0, i):html.index('</section>', i)]


def test_kicker_sits_right_above_the_weekly_conclusion():
    sec = _weekly_section(_files()[HS.HOME])
    m = re.search(r'<div class="hs-kicker" id="wk-label">([^<]+)</div>\s*<h2 id="wk-h2">', sec)
    assert m, '주간 시군구 구역 h2 바로 위에 머리말이 없다'
    assert m.group(1) == KICKER
    assert sec.index('id="wk-label"') < sec.index('id="home-weekly-grid"')
    btn = re.search(r'<button[^>]*data-m="weekly"[^>]*>([^<]+)</button>', _files()[HS.HOME])   # 모드 단추 '주간 시세'
    assert btn and KICKER.startswith(btn.group(1).strip()) and '시군구' in KICKER, '머리말이 모드 단추 이름과 단위(시군구)를 말하지 않는다'
    assert not re.search(r'\d', KICKER), '머리말에 날짜를 싣지 않는다(10-03 대표 요청 — 날짜는 h2 접두가 말한다)'


def test_weekly_status_leaves_the_kicker_alone():
    src = _files()['home-app.js']
    m = re.search(r'^function applyWeeklyStatus\(.*?^\}', src, re.S | re.M)
    assert m and 'wk-h2' in m.group(0)
    assert 'wk-label' not in src, '머리말은 고정 문구다 — 스크립트가 바꾸지 않는다'


def test_blog_capture_boxes_are_the_stats_tab_ones():
    """블로그 주간 캡처는 시세 탭 시장동향 상자(#week-map 안 순위·지도)를 뜬다 — 홈 주간 구역의 머리말과 무관하다."""
    assert P.WEEKLY_SHOTS == {'top10': '.map-rank', 'map': '.map-scroll'}
    assert "getElementById('week-map')" in P._SHOT_JS
