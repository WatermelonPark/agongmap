# -*- coding: utf-8 -*-
"""블로그 썸네일 정사각형 틀(백로그 47, 2026-10-19 대표 승인)과 썸네일 기본 문구(전수리뷰 BL1-8·BL1-15·overflow).

네이버 앱 홈피드 카드(370px)·모바일 검색(104px)·RSS 는 대표 이미지를 가운데 정사각형으로 다시 자른다. 1200x900 썸네일은
좌우 25%가 잘려 10-16 대구 도시 편의 큰 글줄('2027년 입주 2,846세대', 1,036px)이 '027년 입주 2,846세'로 노출됐다.
요청서의 수치(1080 정사각형 · 안전 구역 x·y 60~1020 · 캐러셀 자리 x ≥ 920, y ≤ 120 · 글줄 폭 960px · 큰 글줄 92~104px ·
라벨 40px 이상)는 설계 규격이라 시험이 글자 그대로 들고 있다 — 코드 상수(THUMB_*)가 규격에서 벗어나면 빨개지게.

무엇을 깨뜨리면 빨개지나(실제로 확인):
  - THUMB_SAFE 상한 1020 → 1080 → test_every_box_sits_in_the_safe_area (막대가 1080 까지 깔린다)
  - THUMB_MAX_LINE 을 1080 으로(넘치는 글줄을 그대로 그림) → test_too_wide_line_makes_no_thumbnail
  - thumb_message_bars 첫 줄에서 지역 이름을 빼면 → test_region_name_is_in_the_big_line
  - thumb_weekly_message 의 보합 갈래(elif … '서울 보합')를 지우면 → test_weekly_default_never_says_zero_weeks
  - thumb_zone 이 막대 배경에도 thumb_message(고점 대비)를 쓰면 → test_bars_background_uses_the_supply_grade
  - _weekly_focus 가 W['regions'] 순서로 1위를 고르면(옛 사본) → test_week_top_sido_is_one_helper
  - thumb_weekly 가 --weekly-thumb-msg 일 때만 다시 그리면 → test_region_option_alone_redraws
  - thumb_line_fill 의 빨강 검사를 지우면 → test_red_is_never_on_numbers
픽스처: 저장소의 실제 ADV(occupancy·weekly — 지역 16곳의 입주 막대와 156주 곡선)와, 그 최신 주만 고친 사본(서울 표시 0.00 주 —
실데이터 2025-01-20 의 +0.0036 그대로, 서울 3주 하락, 서울 결측, 원값이 같은 두 시도). 도시 편은 대구 10-16 초안의 기본 문구를
그대로 쓴 합성 사실(반기 입주 8칸)이다.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_city_post as MC  # noqa: E402

SPEC_PX, SPEC_LO, SPEC_HI, SPEC_CX, SPEC_CY, SPEC_LINE = 1080, 60, 1020, 920, 120, 960
DAEGU = ['2027년 입주 2,846세대', '*적정의 31%*']      # 10-16 대구 도시 편 기본 문구(104px 에서 1,036px 남짓)


def _city_f():
    hs = ['2024-03', '2024-09', '2025-03', '2025-09', '2026-03', '2026-09', '2027-03', '2027-09']
    return dict(city='대구', start='2024-01', last_ym='2027-09', years=['2024', '2025', '2026', '2027'],
                rows=[{'ym': hs[0]}, {'ym': hs[-1]}], need=12000,
                by_half={MC.half(h): v for h, v in zip(hs, (9000, 8000, 6000, 4000, 2000, 900, 1500, 1300))})


def _assert_safe(marks):
    assert marks
    for kind, text, px, (x0, y0, x1, y1) in marks:
        assert SPEC_LO <= x0 and SPEC_LO <= y0 and x1 <= SPEC_HI and y1 <= SPEC_HI, (kind, text, (x0, y0, x1, y1))
        assert not (x1 > SPEC_CX and y0 < SPEC_CY), ('캐러셀 자리', kind, text)
        if kind == 'text':
            assert x1 - x0 <= SPEC_LINE, text
            assert px >= 40, ('라벨 40px 미만', text, px)


def test_canvas_is_square_with_previews(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(P.sys, 'argv', ['x'])
    rel = P.thumb_zone({'z': '세종', 'grade': 'g1'}, '2027', 3, sts={})
    path = os.path.join(P.ROOT, rel)
    assert Image.open(path).size == (SPEC_PX, SPEC_PX)
    for n in (370, 104):
        assert Image.open(os.path.splitext(path)[0] + '-%dpx.png' % n).size == (n, n)


def test_every_box_sits_in_the_safe_area(tmp_path, monkeypatch):
    """지역 16곳(입주 막대)·주간(52주 곡선)·도시 편(반기 막대) 모두 글자·표식 상자가 안전 구역 안, 캐러셀 자리는 비었다.
    큰 글줄은 92~104px, 라벨은 40px 이상."""
    monkeypatch.setattr(P.sys, 'argv', ['x'])
    adv, sts = P.M.load()
    zones = [z for z in adv['sido']['zones'] if not z.get('agg')]
    kinds = set()
    for r in zones:
        nm = r['z']
        bars = P._thumb_bars(adv, nm)     # 입주 막대를 못 쓰는 지역(해가 6개 미만)은 곡선 갈래 — 그래도 틀은 같아야 한다
        marks = []
        P._draw_thumb(P.THUMB_GROUP[nm], None if bars else P._thumb_curve(sts, nm), P.thumb_chip(nm, '2027'),
                      P.thumb_message_bars(nm, r['grade']),
                      str(tmp_path / ('z-%s.png' % nm)), ['m'], bars=bars, _marks=marks)
        _assert_safe(marks)
        kinds |= {k for k, *_ in marks}
        big = [px for k, t, px, _ in marks if k == 'text' and px > 60]
        assert big and all(92 <= px <= 104 for px in big)
    assert {'text', 'bar', 'ref'} <= kinds
    W = adv['weekly']
    marks = []
    P._draw_thumb('수도권', P._weekly_curve(W, '서울'), '9월 셋째 주 아파트값', P.thumb_weekly_message(W),
                  str(tmp_path / 'w.png'), ['m'], _marks=marks)
    _assert_safe(marks)
    marks = []
    MC.thumb(_city_f(), str(tmp_path / 'c.png'), ['대구 입주 절벽', '*적정의 31%*'], P.THUMB_PALETTES['영남'], _marks=marks)
    _assert_safe(marks)
    assert any(k == 'bar' for k, *_ in marks)


def test_too_wide_line_makes_no_thumbnail(tmp_path, monkeypatch):
    """960px 을 넘는 글줄은 줄이지 않고 그 썸네일만 만들지 않는다 — 도시 편·지역 편·주간 초안 모두, 초안은 '썸네일 없음'을 적고 나간다."""
    assert P.THUMB_SKIP == '썸네일 없음(문구가 960px을 넘음)'
    path = tmp_path / 'thumb-city-대구.png'
    with pytest.raises(P.ThumbTooWide):
        MC.thumb(_city_f(), str(path), DAEGU, P.THUMB_PALETTES['영남'])
    assert not path.exists()
    # 지역 편 초안: --thumb-msg 가 넘치면 썸네일 없이 초안이 나가고 안내 칸이 그 사실을 적는다.
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    monkeypatch.setattr(P, 'rival_panel', lambda *a, **k: '')
    adv, sts = P.M.load()
    r = dict(next(z for z in adv['sido']['zones'] if not z.get('agg')))
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot', '--thumb-msg', '|'.join(DAEGU)])
    d = P.draft_zone(adv, sts, r, 1, 16)
    assert P.THUMB_SKIP in d['imgnote'] and d['imgs'][0][0] is None
    assert not os.path.exists(os.path.join(str(tmp_path), 'thumb-%s.png' % r['z']))
    # 주간 초안도 같다(한 번 실행에 주간·지역 초안을 함께 만들므로 멈추지 않는다).
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot', '--weekly-thumb-msg', '|'.join(DAEGU)])
    w = P.draft_weekly(adv, sts, shot=False)
    assert P.THUMB_SKIP in w['imgnote'] and w['imgs'][0][0] is None and w['body']


def test_region_name_is_in_the_big_line():
    """지역 이름은 큰 글줄이나 차트 제목 줄(칩)에 든다(10-09 대표 결정) — 기본 문구는 큰 글줄 첫 줄에 블로그 표기로."""
    adv, sts = P.M.load()
    zones = [z for z in adv['sido']['zones'] if not z.get('agg')]
    assert zones
    for r in zones:
        name = P.SEARCH_NAME.get(r['z'], r['z'])
        assert name in P.thumb_message_bars(r['z'], r['grade'])[0]
        assert name in P.thumb_message(r['z'], ([], None, -12.0))[0]
        assert name in P.thumb_chip(r['z'], '2027')
    assert P.thumb_message('전남광주', ([], None, -15.0))[0].startswith('광주·전남')
    W = adv['weekly']
    msg = P.thumb_weekly_message(W)
    up, _ = P.week_top3(W)
    assert any('서울' in x for x in msg) or (up and P.SEARCH_NAME.get(up[0][0], up[0][0]) in msg[-1])


def _seoul(W, vals):
    """서울 계열 끝을 vals 로 바꾼 사본(앞은 실데이터 그대로)."""
    W = copy.deepcopy(W)
    i = W['regions'].index('서울')
    for row, v in zip(W['rows'][-len(vals):], vals):
        row['ma'][i] = v
    return W


def test_weekly_default_never_says_zero_weeks():
    """서울 표시 0.00(실데이터 2025-01-20 의 +0.0036)·결측 주에 '서울 0주째 하락'을 찍지 않는다(BL1-8). 셈은 정본 WM.streak."""
    W = P.M.load()[0]['weekly']
    flat = P.thumb_weekly_message(_seoul(W, [0.05, 0.0036]))
    assert flat[0] == '서울 보합' and not any('0주째' in x for x in flat)
    miss = P.thumb_weekly_message(_seoul(W, [0.05, None]))
    assert not any(x.startswith('서울') for x in miss) and miss
    assert P.thumb_weekly_message(_seoul(W, [0.03, -0.02, -0.05, -0.01]))[0] == '서울 3주째 하락'
    i = W['regions'].index('서울')
    allup = _seoul(W, [0.01] * len(W['rows']))
    assert P.thumb_weekly_message(allup)[0] == '서울 %d주 이상 상승' % len(W['rows'])
    real = [r['ma'][i] for r in W['rows']]
    s = P.WM.streak(real)
    assert (str(abs(s)) in P.thumb_weekly_message(W)[0]) if s else True


def test_bars_background_uses_the_supply_grade(monkeypatch):
    """막대 배경 썸네일의 기본 문구는 매매가 고점 대비가 아니라 사이트 판정 낱말이다(BL1-15). --thumb-msg 는 그대로 이긴다."""
    adv, sts = P.M.load()
    got = {}
    monkeypatch.setattr(P, '_draw_thumb', lambda group, curve, chip, lines, path, msg, bars=None:
                        got.update(lines=lines, bars=bars) or 'x.png')
    seen = set()
    for r in [z for z in adv['sido']['zones'] if not z.get('agg')]:
        P.thumb_zone(r, '2027', 3, sts, None, adv=adv)
        if not got['bars']:      # 막대를 못 쓰는 지역은 곡선 문구 그대로(배경과 같은 계열)
            assert got['lines'] == P.thumb_message(r['z'], P._thumb_curve(sts, r['z']))
            continue
        assert not any('고점' in x or '최고가' in x for x in got['lines']), got['lines']
        assert got['lines'][1].strip('*') in P.SZ.GRADE_LABS[r['grade']]
        seen.add(r['grade'])
    assert seen, '막대 배경 지역이 하나도 없다 — 시험이 빈 채로 통과한다'
    P.thumb_zone(r, '2027', 3, sts, ['내 문구', '*둘째*'], adv=adv)
    assert got['lines'] == ['내 문구', '*둘째*']


def test_week_top_sido_is_one_helper(monkeypatch):
    """그 주 1위 시도는 초안 본문·태그·썸네일 문구·곡선 지역이 한 도우미(week_top3 — MW.SIDO 순서)로 고른다.
    픽스처: 최신 주에서 원천 순서와 MW.SIDO 순서가 거꾸로인 두 시도에 같은 원값을 주고 나머지는 내림(실제로 0회였지만 생길 수 있는 동률)."""
    adv, sts = P.M.load()
    W = adv['weekly']
    reg = W['regions']
    sido = [z for z in P.MW.SIDO if z in reg]
    a, b = next((x, y) for x in sido for y in sido if sido.index(x) < sido.index(y) and reg.index(x) > reg.index(y))
    adv = copy.deepcopy(adv)
    last = adv['weekly']['rows'][-1]
    for i, z in enumerate(reg):
        if z in sido:
            last['ma'][i] = 0.3 if z in (a, b) else -0.02
    W = adv['weekly']
    assert P.week_top3(W)[0][0][0] == a
    assert P._weekly_focus(W, []) == a
    assert P.SEARCH_NAME.get(a, a) in P.thumb_weekly_message(W)[-1]
    monkeypatch.setattr(P, 'rival_panel', lambda kw: '')
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    tags = P.draft_weekly(adv, sts, shot=False)['tags']
    assert tags[3] == P.TAG_NAME.get(a, P.SEARCH_NAME.get(a, a)).replace('·', '') + '아파트값'


def test_region_option_alone_redraws(tmp_path, monkeypatch):
    """--weekly-thumb-region 만 줘도 썸네일을 다시 그린다(예전엔 기존 파일을 지켜 지역 옵션이 조용히 무시됐다)."""
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    W = P.M.load()[0]['weekly']
    path = tmp_path / ('thumb-weekly-%s.png' % W['rows'][-1]['p'])
    path.write_bytes(b'old')
    monkeypatch.setattr(P.sys, 'argv', ['x', '--weekly-thumb-region', '부산'])
    P.thumb_weekly(W, {}, None)
    assert path.read_bytes() != b'old'
    path.write_bytes(b'old')
    monkeypatch.setattr(P.sys, 'argv', ['x'])
    P.thumb_weekly(W, {}, None)
    assert path.read_bytes() == b'old', '옵션이 없으면 기존 썸네일을 지킨다(_keep_existing_thumb)'


def test_red_is_never_on_numbers():
    """빨강은 표식에만 — 사이트에서 빨강은 상승이라 숫자 글자에 쓰지 않는다. 영남 판 강조색(살구 빨강)도 숫자 줄은 먹색."""
    ink = (19, 30, 36)
    red = P.THUMB_PALETTES['영남'][3]
    blue = P.THUMB_PALETTES['수도권'][3]
    assert P._is_red(red) and not P._is_red(blue)
    assert P.thumb_line_fill('*적정의 31%*', ink, red) == ink
    assert P.thumb_line_fill('*다시 오를까*', ink, red) == red
    assert P.thumb_line_fill('*경기 +0.26%*', ink, blue) == blue
    assert P.thumb_line_fill('서울 88주째 상승', ink, blue) == ink
    assert not any(P._is_red(p[3]) for g, p in P.THUMB_PALETTES.items() if g != '영남')


def test_old_frame_thumbnail_is_redrawn(tmp_path):
    """백로그 47 이전 틀(1200x900)로 그린 기존 썸네일은 문구 없이 다시 돌려도 지키지 않는다 — 지키면 옛 썸네일이 홈피드
    정사각형 자르기에 그대로 나간다. 정사각형(THUMB_PX)으로 그린 것과 그림으로 안 열리는 파일은 예전처럼 지킨다.

    변이: _keep_existing_thumb 의 크기 검사(size != (THUMB_PX, THUMB_PX) → False)를 지우면 빨개진다(실제로 확인).
    픽스처: drafts/ 에 남아 있는 10-19 이전 초안 썸네일과 같은 1200x900 PNG, 새 틀 1080 정사각형 PNG, 깨진 파일."""
    from PIL import Image
    old, new, bad = (str(tmp_path / n) for n in ('old.png', 'new.png', 'bad.png'))
    Image.new('RGB', (1200, 900)).save(old)
    Image.new('RGB', (SPEC_PX, SPEC_PX)).save(new)
    open(bad, 'wb').write(b'x')
    assert not P._keep_existing_thumb(old, None, argv=['x'])
    assert P._keep_existing_thumb(new, None, argv=['x'])
    assert P._keep_existing_thumb(bad, None, argv=['x'])
    assert not P._keep_existing_thumb(new, None, argv=['x', '--force-thumb'])
