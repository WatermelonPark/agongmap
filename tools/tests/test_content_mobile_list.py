# -*- coding: utf-8 -*-
"""콘텐츠 목록 휴대폰 개선(2026-11-19 대표 지적 '글 선택이 모바일에서 너무 불편', 결정 '시도 한 줄 + 도시 둘째 줄'·'촘촘한 목록형').

왜 이 시험이 있나. 휴대폰에서 시도별 도시 칩을 모두 펼친 벽이 한 화면을 넘어 /city/ 첫 화면에 글이 한 편도 없었고, 카드 하나가
화면의 3분의 1이라 21편을 보려면 다섯 화면을 밀어야 했다. 이제 지역 거르기는 첫 줄 '전체'·시도 단추(글 수), 시도를 누르면 그
시도의 도시 줄만 열린다. 허브·섹션 목록 카드는 휴대폰에서 목록형(.klist)이다. 실제 휴대폰 폭(iPhone 13)에서 구운 /city/ 를 열어
경기 → 7편, 김포 → 1편, 김포 해제 → 경기 7편, 경기 해제 → 21편으로 걸러지는 것을 확인했다(Playwright, 2026-11-19).

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - city_chips 가 시도 단추를 빼면 → test_first_row_is_all_and_provinces
  - 시도 단추의 글 수를 도시 칩 수로 세면 → test_first_row_is_all_and_provinces
  - .klist .kcard[hidden] 규칙을 빼면(목록형 grid 가 [hidden] 을 이겨 거른 카드가 보였다 — 실제로 났던 결함) → test_compact_css_keeps_filtered_cards_hidden
  - build_index 의 compact='klist ksec' 를 빼면 → test_lists_use_the_compact_layout
  - JS 가 없을 때 도시 줄을 숨기면(.cityf:not(.js) 대신 .cityf 로) → test_without_js_every_city_row_shows
픽스처: 합성 글(경기 셋 — 수원 둘·김포 하나, 부산 하나)과 생성기의 CSS·스크립트 글자.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_content_pages as MC  # noqa: E402


def _m(slug, cities, sec='city', topic='moveins'):
    return {'section': sec, 'slug': slug, 'title': '결론 ' + slug, 'city': cities, 'topic': topic,
            'date': '2026-11-01', 'updated': '2026-11-01'}


METAS = [_m('a', ['수원']), _m('b', ['수원']), _m('c', ['김포']), _m('d', ['부산'])]


def test_first_row_is_all_and_provinces():
    chips = MC.city_chips(METAS)
    head = re.search(r'<div class="cf-s">(.*?)</div>', chips).group(1)
    assert '<button type="button" class="rchip on" data-city="">전체 4편</button>' in head
    sidos = re.findall(r'data-sido="([^"]+)">[^<]*<small>(\d+)</small>', head)
    assert sidos == [('경기', '3'), ('부산', '1')], '시도 단추는 표시 순서로, 글 수는 그 시도 글 수(도시 칩 수가 아니다): %s' % sidos
    rows = re.findall(r'<div class="cf-g" data-sido="([^"]+)">', chips)
    assert rows == ['경기', '부산'], '시도 단추마다 그 시도의 도시 줄이 짝으로 있어야 한다'


def test_without_js_every_city_row_shows():
    css = MC.EXTRA_CSS
    assert '.cityf:not(.js) .cf-sd{display:none}' in css, 'JS 가 없으면 시도 단추를 숨기고 도시 줄을 모두 보여야 한다'
    assert '.cityf.js .cf-g{display:none}' in css and '.cityf.js .cf-g.open{display:flex}' in css
    assert "f.classList.add('js')" in MC.FILTER_JS, 'JS 가 돌 때만 두 단 모양으로 바꾼다'


def test_compact_css_keeps_filtered_cards_hidden():
    mob = re.search(r'@media \(max-width:767px\)\{(.*?)\n\}', MC.EXTRA_CSS, re.S).group(1)
    assert '.klist .kcard{display:grid' in mob
    assert '.klist .kcard[hidden]{display:none}' in mob, '목록형 grid 가 [hidden] 을 이겨 거른 카드가 보인다'
    assert 'overflow-x:auto' in mob and 'mask-image' in mob, '휴대폰 시도 줄은 옆으로 밀고 끝을 흐려 더 있다는 단서를 둔다'


def test_lists_use_the_compact_layout():
    idx, _ = MC.build_index('city', METAS)
    assert '<div class="kgrid klist ksec">' in idx, '섹션 목록 카드가 목록형이 아니다'
    hub = MC.build_reports(METAS)
    hub = hub[0] if isinstance(hub, tuple) else hub
    assert 'class="kgrid klist' in hub, '허브 최근 글 카드가 목록형이 아니다'
    assert 'klist' not in MC.cards_grid(METAS), '홈·시도 리포트 카드(기본)는 그대로여야 한다'
