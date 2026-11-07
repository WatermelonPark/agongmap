# -*- coding: utf-8 -*-
"""콘텐츠 디자인 검수(2026-11-07)에서 고친 것들 — 섹션 이름, 칩 줄, 허브 접기, 글 끝 행동, 그림·표·각주, 원고 알림.

재현한 실제 상태(2026-11-07 main, Chromium 375px·1280px):
- 한 섹션을 '반박'(빵부스러기·<title>)·'발언 검증'(칩)·'해설'(홈 푸터) 세 이름으로 불렀다(도시·GTX·단지 편도 둘씩).
- 600px 이하에서 질문 칩·지역 칩 줄이 가로 밀기(nowrap)라 다섯째 질문 칩과 경기 지역 칩 대부분이 단서 없이 화면 밖이었다.
- 지역 칩 거르기가 정확 일치라 '부천'을 누르면 '부천 원미구'·'부천 오정구' 글이 숨었고, 칩은 글 수 순이라 같은 시가 흩어졌다.
- 허브 '최근 글'이 40장을 한 번에 쌓아 375px 에서 약 7,200px 였다.
- 글 끝 상자 넷이 같은 테두리라 첫 행동이 없었고, 도시 글에는 시도 리포트 상자가 빠졌다(region 이 시라 _zone_link 가 못 찾았다).
- 혼자 선 캡처 그림에 '눌러서 크게 보기' 표시가 없었고, 표 밑 '※' 방법론 15줄이 본문 크기로 결과 절을 막았다.
- 도시 편에서 같은 두 줄 각주가 표 셋·그림 하나 밑에 네 번, 핵심 숫자 띠와 그림 카드에 같은 '34%'가 두 번 섰다.
"""
import io
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import content_check as CC         # noqa: E402
import content_md as CM            # noqa: E402
import home_src as HS              # noqa: E402
import make_content_pages as MC    # noqa: E402


def _read(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        pytest.skip('%s 가 아직 없다' % rel)
    return io.open(p, encoding='utf-8').read()


# ── 섹션 이름: 한 섹션 한 이름 ──────────────────────────────────────────────
def test_one_name_per_section_everywhere():
    """섹션 이름은 TOPICS 의 짧은 이름 하나다 — SECTION_META·칩·빵부스러기·<title>·og:title·홈 푸터가 모두 같은 글자.

    기대 이름은 **여기 적는다**(TOPICS 에서 만들면 상수를 바꿀 때 기대값도 같이 바뀐다).
    변이(실제로 확인): SECTION_META 를 옛 손 표('반박' 등)로 되돌리면 첫 단정이, index.html 푸터를 '해설'로 되돌리면 넷째 단정이
    빨개진다.
    픽스처: 생성기를 먼저 돌린 저장소의 섹션 목록 넷과 손으로 쓴 홈(index.html)의 푸터 세 벌.
    """
    want = {'city': '도시 입주물량', 'gtx': '역세권 첫 집', 'danji': '재건축·리모델링', 'column': '발언 검증'}
    assert {k: v[0] for k, v in MC.SECTION_META.items()} == want
    assert {sec: short for _k, _q, short, sec in CM.TOPICS} == want
    for sec, name in want.items():
        page = _read('%s/index.html' % sec)
        assert '<title>%s | 아공맵</title>' % name in page, sec
        assert '<meta property="og:title" content="%s">' % name in page, sec
        assert '› <b>%s</b></nav>' % name in page, sec + ' 빵부스러기'
        assert '<a class="rchip" href="/%s/" aria-current="page">%s</a>' % (sec, name) in page, sec + ' 칩'
    home = _read(HS.HOME)          # 손으로 쓴 홈 마크업(푸터)만 본다 — 홈 스크립트는 읽지 않는다
    for sec, name in want.items():
        got = set(re.findall(r'<a href="/%s/">([^<]+)</a>' % sec, home))
        assert got == {name}, '홈 푸터의 /%s/ 링크 글자가 섹션 이름과 다르다: %s' % (sec, sorted(got))


def test_section_chip_and_city_filter_look_different():
    """지금 섹션 칩은 aria-current(테두리 꼴), 지역 칩의 켜짐은 .on(채움) — 둘 다 먹색 채움이라 어느 것이 페이지인지 몰랐다.

    변이(실제로 확인): section_chips 를 ' on' 클래스로 되돌리면 빨개진다.
    """
    chips = MC.section_chips('gtx')
    assert 'aria-current="page"' in chips and ' on"' not in chips and 'class="rchip on"' not in chips
    assert '.rchip[aria-current=page]{' in MC.LIST_CSS


# ── 칩 줄 ────────────────────────────────────────────────────────────────
def test_chip_rows_wrap_on_a_phone():
    """질문 칩·지역 칩 줄은 휴대폰에서도 접어 내린다(가로 밀기 nowrap 이 없다). 칩 높이는 35px 안팎(위아래 10px).

    변이(실제로 확인): LIST_CSS 에 600px 이하 '.rchips{flex-wrap:nowrap;overflow-x:auto}' 를 되살리면 빨개진다.
    """
    css = MC.LIST_CSS
    assert 'nowrap' not in re.sub(r'\.qc-n\{[^}]*\}', '', css), '칩 줄이 다시 가로 밀기다'
    assert re.search(r'\.rchips\{[^}]*flex-wrap:wrap', css) and re.search(r'\.cf-c\{[^}]*flex-wrap:wrap', css)
    assert re.search(r'\.rchip\{[^}]*padding:10px 12px', css)


def test_city_chips_group_a_city_with_its_districts_and_filter_by_prefix():
    """지역 칩은 시도 안에서 이름 순(시 → 그 구), 구 칩이 둘 이상인 시는 시 칩을 세우고, 구 칩 글자는 시 칩 뒤에서 구 이름만.
    거르기는 앞말 + 빈칸 일치라 '부천'이 '부천 원미구' 글도 남긴다.

    변이(실제로 확인): city_groups 의 정렬을 글 수 순으로 되돌리면 첫 단정이, 시 칩 세우기를 지우면 둘째가, FILTER_JS 의
    "'|'+c+' '" 비교를 지우면 마지막 단정이 빨개진다.
    픽스처: 그날 경기 줄 모양 — 부천·부천 원미구·부천 오정구, 고양 구만 셋, 성남 분당구 하나, 서울 전체·서울 노원구.
    """
    def m(slug, cities, n=1):
        return [{'section': 'danji', 'slug': '%s%d' % (slug, i), 'title': 't', 'city': cities, 'topic': 'redevelop',
                 'date': '2026-11-01', 'updated': '2026-11-01'} for i in range(n)]
    metas = (m('a', ['부천 원미구'], 3) + m('b', ['부천']) + m('c', ['부천 오정구']) + m('d', ['고양 덕양구'], 2)
             + m('e', ['고양 일산동구']) + m('f', ['고양 일산서구']) + m('g', ['성남 분당구'], 4)
             + m('h', ['서울 노원구']) + [{'section': 'column', 'slug': 'z', 'title': 't', 'region': '서울', 'topic': 'claim',
                                           'date': '2026-11-01', 'updated': '2026-11-01'}])
    groups = dict(MC.city_groups(metas))
    assert groups['경기'] == ['고양', '고양 덕양구', '고양 일산동구', '고양 일산서구', '부천', '부천 오정구', '부천 원미구', '성남 분당구']
    assert groups['서울'] == ['서울 전체', '서울 노원구'], '시도 이름으로 시 칩을 세웠거나 전체가 뒤에 섰다'
    chips = MC.city_chips(metas)
    assert '<button type="button" class="rchip" data-city="부천 원미구">원미구</button>' in chips
    assert '<button type="button" class="rchip" data-city="성남 분당구">성남 분당구</button>' in chips
    assert '<button type="button" class="rchip on" data-city="">전체 %d편</button>' % len(metas) in chips
    assert "d.indexOf('|'+c+'|')>=0||d.indexOf('|'+c+' ')>=0" in MC.FILTER_JS


# ── 허브 접기 ────────────────────────────────────────────────────────────
def test_hub_recent_folds_after_the_first_batch():
    """cards_grid(fold=HUB_FIRST) 는 카드를 모두 싣되 .kfold 로 접고 '글 N편 더 보기'를 단다. JS 가 없으면 noscript 가 편다.
    거르는 동안·더 보기를 누른 뒤에는 접힘을 푼다(FILTER_JS).

    변이(실제로 확인): cards_grid 에서 noscript 를 빼면 셋째 단정이, FILTER_JS 의 kfold 토글을 빼면 넷째가 빨개진다.
    픽스처: 합성 글 15편(접힘 기준 12를 넘는다)과 5편(넘지 않는다).
    """
    metas = [{'section': 'city', 'slug': 's%02d' % i, 'title': 't%d' % i, 'city': ['구미'], 'topic': 'moveins',
              'date': '2026-11-01', 'updated': '2026-11-%02d' % (i + 1)} for i in range(15)]
    g = MC.cards_grid(metas, fold=MC.HUB_FIRST)
    assert g.count('<a class="kcard"') == 15 and '<div class="kgrid kfold">' in g
    assert '<button type="button" class="rchip kmore">글 3편 더 보기</button>' in g
    assert '<noscript><style>.kfold .kcard:nth-child(n){display:flex}' in g
    assert "g.classList.toggle('kfold',!on&&!open)" in MC.FILTER_JS and 'mb.hidden=on||open' in MC.FILTER_JS
    small = MC.cards_grid(metas[:5], fold=MC.HUB_FIRST)
    assert 'kfold' not in small and 'kmore' not in small


# ── 글 끝 ────────────────────────────────────────────────────────────────
def test_post_tail_has_one_primary_action_and_a_way_back():
    """글 끝 '이 지역 더 보기'의 첫 상자 하나만 채우고(.cgo), 도시 글에도 시도 리포트 상자가 있다(zone_of 로 푼 시도 키).
    이전·다음 뒤에 섹션 목록으로 돌아가는 링크가 있다.

    변이(실제로 확인): region_box 를 _zone_link(meta['region']) 로 되돌리면 둘째 단정이, build_page 의 cnav-hub 링크를 지우면
    넷째 단정이 빨개진다.
    픽스처: 그날 수원 도시 편 모양(region '수원', city '수원')과 저장소에 구워진 글 하나.
    """
    import content_tables as CT
    data = CT.load()
    city = {'section': 'city', 'slug': 'suwon-x', 'title': '수원 입주', 'region': '수원', 'city': ['수원'], 'topic': 'moveins',
            'date': '2026-11-01', 'updated': '2026-11-01'}
    box = MC.region_box(city, data, [])
    assert box.count('class="cgo"') == 1
    assert '<a class="cgo" href="/zone/' in box, '도시 글에 시도 리포트 상자가 없다'
    assert '.cmore-l a.cgo{' in MC.EXTRA_CSS
    built = CM.built(ROOT)
    if not built:
        pytest.skip('구워진 글이 없다')
    sec, slug, _ = built[0]
    page = _read('%s/%s/index.html' % (sec, slug))
    assert re.search(r'<a class="cnav-hub" href="/[a-z]+/"><span>이 질문의 글 모두</span>', page), '섹션 목록으로 돌아가는 길이 없다'


# ── 그림·표·각주 ─────────────────────────────────────────────────────────
def test_alone_images_get_a_caption_and_a_tap_hint():
    """혼자 선 그림은 figure + figcaption('그림 이름 · 눌러서 크게 보기')이고 원본으로 여는 링크다. 문장 속 그림은 링크만.

    변이(실제로 확인): content_img_src 의 fig 를 빼면(링크만 남기면) 첫 단정이 빨개진다.
    """
    got = MC.content_img_src('<p><img src="img/a.png" alt="평형별 시세" loading="lazy"></p>\n'
                             '<p>글 <img src="img/b.png" alt="" loading="lazy"> 끝</p>', 'danji')
    assert ('<figure class="cfig"><a class="cimg" href="/content/danji/img/a.png" target="_blank" rel="noopener">'
            '<img src="/content/danji/img/a.png"' in got)
    assert '<figcaption>평형별 시세 · <a href="/content/danji/img/a.png" target="_blank" rel="noopener">%s</a></figcaption>' % MC.IMG_HINT in got
    assert got.count('<figure') == 1 and '<p>글 <a class="cimg" href="/content/danji/img/b.png"' in got


def test_note_paragraphs_fold_and_wide_tables_get_a_hint():
    """'※' 문단: 짧으면 14px 각주 문단(.cnotep), 길면 접는 칸(.cfold). 열이 WIDE_COLS 이상인 표는 '옆으로 밀어 N열 모두 보기'.

    변이(실제로 확인): markdown 이 _para 대신 '<p>' 를 쓰면 첫·둘째 단정이, _tab_hint 를 빼면 셋째가 빨개진다.
    픽스처: 그날 GTX 동탄 편 표 밑 문단 모양(※ 로 여는 1,000자 문단)과 11열 표.
    """
    long = '※ ' + '표는 입주 2년 안 신축입니다. ' * 20
    h = MC.markdown('※ 짧은 기준입니다.\n\n' + long)
    assert '<p class="cnotep">※ 짧은 기준입니다.</p>' in h
    assert '<details class="cfold"><summary>%s</summary><p>표는 입주' % MC.NOTE_SUMMARY in h
    t = MC.markdown('| ' + ' | '.join('열%d' % i for i in range(11)) + ' |\n|' + '---|' * 11 + '\n| ' + ' | '.join(['1'] * 11) + ' |')
    assert '<p class="ctab-hint">옆으로 밀어 11열 모두 보기</p>' in t
    assert 'ctab-hint' not in MC.markdown('| a | b |\n|---|---|\n| 1 | 2 |')


def test_repeated_notes_and_cards_that_repeat_the_key_are_dropped():
    """같은 각주가 잇따르면 둘째부터 '출처는 위와 같습니다', 그림 숫자 카드 가운데 핵심 숫자 띠와 같은 값은 뺀다.

    변이(실제로 확인): fill_placeholders 의 note_of 를 빼면 첫 단정이, _card_in_key 거르기를 빼면 둘째가 빨개진다.
    픽스처: 실제 데이터의 한 도시(목록에 있는 첫 도시) — 그날 수원 편처럼 그림 하나 + 같은 출처 표 하나, key 는 '적정물량의 N%'.
    """
    import content_tables as CT
    data = CT.load()
    cities = sorted((data.get('cities') or {}).get('cities') or {})
    if not cities:
        pytest.skip('도시 입주 자료가 없다')
    name = next((c for c in cities if CT.city(data, c)), None)
    if not name:
        pytest.skip('도시 입주 자료가 없다')
    spec = CT.chart(data, 'moveins', [name])
    ratio = [v for k, v in spec['cards'] if k == '적정물량 대비']
    body = '{{chart:moveins:%s}}\n\n{{table:moveins:%s}}\n\n{{table:moveins:%s}}\n' % (name, name, name)
    key = {'label': 'l', 'value': '적정물량의 %s' % ratio[0]} if ratio else None
    _filled, blocks = MC.fill_placeholders(body, data, key=key)
    note = CT.table(data, 'moveins', [name])[2]
    assert spec['note'] in blocks[0] and (note in blocks[1] or note == spec['note']), '첫 각주가 줄었다'
    assert MC.SAME_NOTE in blocks[2] and note not in blocks[2], '같은 각주가 잇따라 두 번 나온다'
    if ratio:
        assert ('<b>%s</b>' % ratio[0]) not in blocks[0], '핵심 숫자 띠와 같은 카드가 남았다'
    assert MC._card_in_key('34%', {'value': '적정물량의 34%'}) and not MC._card_in_key('4%', {'value': '적정물량의 34%'})


def test_reading_text_in_content_pages_is_at_least_14px():
    """읽는 글(문장) 14px 하한(2026-11-06 대표 결정) — 질문 카드 결론, 출처 목록, 3년 합계, ※ 각주 문단, 접은 칸 본문, 그림 캡션
    없는 글 단 문장. 라벨(칩·날짜·캡션)은 13px 그대로다.

    변이(실제로 확인): LIST_CSS 의 .qcard ul 을 13px 로 되돌리면 빨개진다(그날 1280px 에서 8곳이 13px 였다).
    """
    css = MC.EXTRA_CSS
    for sel in (r'\.qcard ul', r'\.csrc', r'\.cfoot3', r'\.cbody p\.cnotep', r'\.cbody \.cfold p'):
        m = re.search(r'(?:^|\n|\})%s\{[^}]*font-size:([\d.]+)px' % sel, css)
        assert m and float(m.group(1)) >= 14, '%s 글자가 14px 아래다' % sel
    m = re.search(r'\n\.rh2\{([^}]*)\}', css)
    assert m and 'font-size:20px' in m.group(1) and 'font-weight:700' in m.group(1), '허브 절 제목이 뼈대 h2 급이 아니다'


# ── 원고 알림 ────────────────────────────────────────────────────────────
def test_content_check_notes_card_numbers_and_wide_tables():
    """원고 검사가 카드 핵심 숫자 셋(제목 되풀이·같은 섹션 중복·소수 둘째 자리)과 넓은 원고 표를 ※ 알림으로 낸다 — 고칠 곳(종료
    코드)에는 세지 않는다.

    변이(실제로 확인): key_notes 의 제목 비교를 지우면 첫 단정이, 중복 비교를 지우면 둘째가, table_notes 의 열 수 비교를 지우면
    마지막이 빨개진다.
    픽스처: 그날 원고 모양 — 도시 편(제목·key 모두 '적정물량의 24%'), 발언 검증 셋(같은 '적정물량의 28%'), 단지 편('105.95%').
    """
    front = 'title: %s\nsection: %s\nkey:\n  - label: l\n    value: v\n'
    e = [('c/a.md', front % ('진주 적정물량의 24%입니다', 'city'),
          {'section': 'city', 'title': '진주 2027년 입주는 적정물량의 24%입니다', 'key': {'label': 'l', 'value': '적정물량의 24%'}}),
         ('k/a.md', front % ('a', 'column'), {'section': 'column', 'title': 'a', 'key': {'value': '적정물량의 28%'}}),
         ('k/b.md', front % ('b', 'column'), {'section': 'column', 'title': 'b', 'key': {'value': '적정물량의 28%'}}),
         ('d/a.md', front % ('17평형 3억', 'danji'), {'section': 'danji', 'title': '17평형 3억', 'key': [{'value': '105.95%'}]}),
         ('d/b.md', front % ('24평형', 'danji'), {'section': 'danji', 'title': '24평형 2.9배 아닙니다', 'key': {'value': '29배'}})]
    got = CC.key_notes(e)
    assert any('제목에 이미 있는 값' in w for _l, w in got['c/a.md'])
    assert any('같은 섹션 k/b.md' in w for _l, w in got['k/a.md'])
    assert any('소수 둘째 자리' in w for _l, w in got['d/a.md'])
    assert 'd/b.md' not in got, '2.9 안의 9 를 29 로 잘못 잡았다'
    assert all(ln == 3 for notes in got.values() for ln, _w in notes), '알림 줄이 key 줄이 아니다'
    wide = CC.table_notes('a\n| ' + ' | '.join('h%d' % i for i in range(9)) + ' |\n|' + '---|' * 9 + '\n')
    assert wide and wide[0][0] == 2 and '9열' in wide[0][1]
    assert not CC.table_notes('| a | b |\n|---|---|\n')
