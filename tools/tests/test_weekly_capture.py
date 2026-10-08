# -*- coding: utf-8 -*-
"""주간 초안 이미지(TOP10·시군구 지도)를 픽셀 오프셋이 아니라 화면 요소로 찍는다(2026-10-09).

10-05~06 홈 개편 뒤 옛 오프셋 캡처가 'TOP10' 칸에 경기 타일 조각을, '지도' 칸에 위가 잘리고 푸터가 붙은
그림을 넣었다(대표 지적 10-09). 이제 capture_weekly_map 은 홈 사본에 스크립트를 넣어 `#week-map` 안의 상자
하나만 보이게 하고 찍는다. 이 시험은 그 상자 이름이 지금 사이트 코드와 맞는지 지킨다 — 홈이 상자 이름을 바꾸면
캡처는 '상자를 못 찾음'으로 비게 되는데, 그 전에 여기서 빨개진다.

무엇을 깨뜨리면 빨개지나(실제로 확인): WEEKLY_SHOTS 의 '.map-rank' 를 '.rank-box2' 로 바꾸면 이름 시험이,
_SHOT_JS 를 사본에 넣지 않으면(_weekly_shot_page 가 원본을 그대로 돌려주면) 사본 시험이 빨개진다.
픽스처: 저장소의 실제 index.html·home-stats.js(크롬은 띄우지 않는다).
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_shot_boxes_exist_in_site_code():
    home = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    stats = io.open(os.path.join(ROOT, 'home-stats.js'), encoding='utf-8').read()
    assert 'id="week-map"' in home
    for key, sel in P.WEEKLY_SHOTS.items():
        cls = sel.lstrip('.')
        assert ('"%s"' % cls in stats) or ("'%s'" % cls in stats) or ('class="%s"' % cls in stats) \
            or ('class="%s' % cls in stats), (key, sel)


def test_shot_page_carries_the_script():
    page = P._weekly_shot_page()
    assert page and P._SHOT_JS in page and page.count('</body>') == 1


def test_zone_head_is_shot_below_the_two_column_width():
    """리포트 머리 캡처 폭은 사이트가 두 단으로 바뀌는 폭(app.css 의 가장 작은 min-width 두 단 문턱)보다 좁아야 한다.
    변이: ZONE_HEAD_W 를 1100 으로 되돌리면 빨개진다(10-08 광주·전남 초안에 리포트 전체가 한 장으로 들어간 원인)."""
    import re
    css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    widths = [int(w) for w in re.findall(r'@media\s*\(min-width:\s*(\d+)px\)', css) if int(w) >= 1000]
    assert widths and P.ZONE_HEAD_W < min(widths), (P.ZONE_HEAD_W, widths)
