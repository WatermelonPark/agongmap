# -*- coding: utf-8 -*-
"""블로그 초안 도구 리뷰(2026-10-05) D1·D2·D4·D5 와 series_links 자기 건너뛰기를 고정한다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - draft_edited 의 자리 표시자 검사를 옛 모양(주간 해석 INTERP 하나만)으로 되돌리면 → test_any_missing_placeholder_marks_edited,
    test_naver_main_keeps_hand_edited_drafts (D1: 지역 편 전망만 채운 초안이 덮였다)
  - draft_edited 가 지문을 보지 않으면(지문 분기 삭제) → test_stamp_decides_when_present
  - main 이 .new.html 을 side_path 없이 늘 같은 자리에 쓰면 → test_naver_main_keeps_hand_edited_drafts(.new.html 의 손본 내용이 덮인다)
  - side_path 의 '손대지 않은 자리면 그 자리' 분기를 빼면 → test_side_path_skips_only_hand_edited
  - make_theory_post.main 의 판별을 옛 조건(EXP 자리 표시자가 새 초안에 있고 옛 초안에 없을 때만)으로 되돌리면
    → test_theory_main_keeps_an_edited_episode_without_placeholder (D2: 1~4편은 경험 문단이 이미 채워져 자리 표시자가 없다)
  - _thumb_curve 가 고점을 그린 구간(2016.01~) 안에서만 찾으면 → test_thumb_peak_is_searched_over_the_full_series (D4)
  - thumb_message 를 옛 규칙(고점이 최근 3점 안이고 하락 3% 미만이면 '역대 최고가', 하락은 min(값, -1))으로 되돌리면
    → test_thumb_states_the_actual_fall
  - theory_link4.min_window 를 추정 분기만 훑게(start 를 첫 추정 분기로) 되돌리면 → test_min_window_includes_this_year,
    test_link4_min4_is_not_above_this_year (D5, 2026.08 데이터에서 231,328 > 215,877)
  - series_links 의 자기 건너뛰기를 `nm in 제목` 으로 되돌리면 → test_series_links_skip_self_by_zone_of_title

픽스처가 재현하는 실제 상태:
  - 초안: 주간 해석(INTERP)·지역 전망(OUTLOOK) 자리 표시자가 둘 다 있는 새 초안, 전망만 채운 지문 없는 옛 초안(2026-10-05
    이전에 만든 drafts/naver-*.html 의 모양), 데이터가 바뀌어 숫자만 다른 새 초안. 저장소 drafts/ 는 건드리지 않는다(tmp_path).
  - 이론 초안: 1~4편처럼 자리 표시자 없이 본문만 있는 render 결과(가짜 render).
  - 썸네일: 2014.01 부터의 합성 매매지수 — 경북처럼 고점(2015.08)이 그린 구간 앞에 있는 계열, 고점 두 달 뒤 -2.9%·-0.4% 인 계열.
  - 입주: 2026Q1~Q2 실적이 낮고 2026Q3 부터 추정인 합성 분기 계열(2026.08 데이터의 모양), 그리고 저장소 data.js 그대로.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402
import theory_link4 as L4  # noqa: E402

PH = P.DRAFT_PLACEHOLDERS


def _fresh(n=1, interp=True, outlook=True):
    return ('<h1>초안 %d</h1><p>숫자 %d</p>' % (n, n)
            + ('<p>%s</p>' % P.INTERP_PLACEHOLDER if interp else '<p>사람이 쓴 해석</p>')
            + ('<p>%s</p>' % P.OUTLOOK_PLACEHOLDER if outlook else '<p>사람이 쓴 전망</p>'))


# ── D1 판별 ──────────────────────────────────────────────────────────────
def test_any_missing_placeholder_marks_edited():
    fresh = _fresh(2)
    assert P.draft_edited(_fresh(1, outlook=False), fresh, PH), '지역 전망만 채운 옛 초안을 손대지 않은 것으로 본다'
    assert P.draft_edited(_fresh(1, interp=False), fresh, PH)
    assert not P.draft_edited(_fresh(1), fresh, PH), '자리 표시자가 그대로인 옛 초안(숫자만 다름)은 덮어도 된다'
    assert not P.draft_edited(_fresh(2).replace('</p>', '</p>\n'), fresh, PH, strict=True), '공백 차이는 손댄 것이 아니다'
    # 새 초안에 없는 자리(--week 는 지역 편이 없다)는 옛 초안에 없어도 손댄 것이 아니다
    assert not P.draft_edited(_fresh(1, outlook=False), _fresh(2, outlook=False), PH)


def test_stamp_decides_when_present():
    old = P.stamp_draft(_fresh(1))
    assert not P.draft_edited(old, _fresh(2), PH, strict=True), '생성기가 쓴 그대로인 초안은 데이터가 바뀌어도 덮는다'
    edited = old.replace('초안 1', '결론으로 바꾼 제목')   # 자리 표시자는 그대로 두고 제목만 고쳤다
    assert P.draft_edited(edited, _fresh(2), PH), '자리 표시자를 남긴 채 고친 초안을 덮는다'


def test_side_path_skips_only_hand_edited(tmp_path):
    path = str(tmp_path / 'naver-x.html')
    fresh = _fresh(3)
    assert P.side_path(path, fresh, PH).endswith('naver-x.new.html')
    (tmp_path / 'naver-x.new.html').write_text(P.stamp_draft(_fresh(2)), encoding='utf-8')
    assert P.side_path(path, fresh, PH).endswith('naver-x.new.html'), '손대지 않은 .new.html 은 그 자리에 다시 쓴다'
    (tmp_path / 'naver-x.new.html').write_text(_fresh(2, outlook=False), encoding='utf-8')
    assert P.side_path(path, fresh, PH).endswith('naver-x.new2.html')
    for i in range(2, P.SIDE_MAX + 1):
        (tmp_path / ('naver-x.new%d.html' % i)).write_text(_fresh(2, interp=False), encoding='utf-8')
    assert P.side_path(path, fresh, PH) is None, '모든 자리가 손본 초안인데 하나를 덮으려 한다'


# ── D1 main ──────────────────────────────────────────────────────────────
def _fake_main(monkeypatch, tmp_path, html, argv=()):
    adv = {'sido': {'zones': [{'z': '서울'}]}, 'weekly': {'rows': [{'p': '2026-09-28'}]}}
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(P.M, 'load', lambda: (adv, {}))
    monkeypatch.setattr(P.SZ, 'zone_order', lambda rows: [r['z'] for r in rows])
    monkeypatch.setattr(P, 'pick_zone', lambda pool: ('서울', 1, 16, lambda: None))
    monkeypatch.setattr(P, 'draft_weekly', lambda *a, **k: {'title': '주간'})
    monkeypatch.setattr(P, 'draft_zone', lambda *a, **k: {'title': '지역', 'seq': '1/16'})
    monkeypatch.setattr(P, 'render', lambda p, d1, d2: html)
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py'] + list(argv))
    assert P.main() == 0
    return tmp_path / 'naver-2026-09-28.html'


def test_naver_main_keeps_hand_edited_drafts(tmp_path, monkeypatch):
    path = tmp_path / 'naver-2026-09-28.html'
    new1 = tmp_path / 'naver-2026-09-28.new.html'
    # 지문 이전의 옛 초안에서 지역 전망만 채운 것(주간 해석 자리는 그대로) — 예전 판별은 이것을 덮었다
    path.write_text(_fresh(0, outlook=False), encoding='utf-8')
    _fake_main(monkeypatch, tmp_path, _fresh(1))
    assert '사람이 쓴 전망' in path.read_text(encoding='utf-8'), '지역 전망만 채운 옛 초안을 덮었다'
    assert '숫자 1' in new1.read_text(encoding='utf-8')
    path.unlink()
    _fake_main(monkeypatch, tmp_path, _fresh(2))
    _fake_main(monkeypatch, tmp_path, _fresh(3))
    assert '숫자 3' in path.read_text(encoding='utf-8'), '손대지 않은 초안은 새 데이터로 덮는다'
    path.write_text(path.read_text(encoding='utf-8').replace(P.OUTLOOK_PLACEHOLDER, '사람이 쓴 전망'), encoding='utf-8')
    _fake_main(monkeypatch, tmp_path, _fresh(4))
    assert '사람이 쓴 전망' in path.read_text(encoding='utf-8'), '지역 전망을 채운 초안을 덮었다'
    assert '숫자 4' in new1.read_text(encoding='utf-8'), '손대지 않은 .new.html 은 그 자리에 다시 쓴다'
    new1.write_text(new1.read_text(encoding='utf-8').replace(P.INTERP_PLACEHOLDER, '.new 에 쓴 해석'), encoding='utf-8')
    _fake_main(monkeypatch, tmp_path, _fresh(5))
    assert '.new 에 쓴 해석' in new1.read_text(encoding='utf-8'), '손본 .new.html 을 덮었다'
    assert '숫자 5' in (tmp_path / 'naver-2026-09-28.new2.html').read_text(encoding='utf-8')
    _fake_main(monkeypatch, tmp_path, _fresh(6), argv=['--force'])
    assert '숫자 6' in path.read_text(encoding='utf-8'), '--force 는 손본 초안도 덮는다'


# ── D2 이론 초안 ─────────────────────────────────────────────────────────
def test_theory_main_keeps_an_edited_episode_without_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(T, 'OUT', str(tmp_path))
    path = tmp_path / 'theory-01.html'
    monkeypatch.setattr(T, 'render', lambda post: '<p>본문 v1</p>')
    assert T.main(['1']) == 0
    monkeypatch.setattr(T, 'render', lambda post: '<p>본문 v2</p>')
    T.main(['1'])
    assert 'v2' in path.read_text(encoding='utf-8'), '생성기가 쓴 그대로인 초안은 새 데이터로 덮는다'
    path.write_text(path.read_text(encoding='utf-8').replace('본문 v2', '사람이 고친 본문'), encoding='utf-8')
    monkeypatch.setattr(T, 'render', lambda post: '<p>본문 v3</p>')
    T.main(['1'])
    assert '사람이 고친 본문' in path.read_text(encoding='utf-8'), '자리 표시자 없는 편의 손본 초안을 덮었다'
    assert 'v3' in (tmp_path / 'theory-01.new.html').read_text(encoding='utf-8')
    # 지문 이전의 옛 초안(지문 없음)이 새 초안과 다르면 손본 것으로 본다
    path.write_text('<p>지문 없는 옛 초안</p>', encoding='utf-8')
    T.main(['1'])
    assert '지문 없는 옛 초안' in path.read_text(encoding='utf-8')
    T.main(['1', '--force'])
    assert 'v3' in path.read_text(encoding='utf-8')


# ── D4 썸네일 고점 ───────────────────────────────────────────────────────
def _sts(vals, start=2014):
    dates = ['%d.%02d' % (start + i // 12, i % 12 + 1) for i in range(len(vals))]
    dates[-1] += ' p)'
    return {'매매지수': {'dates': dates, 'series': {'경북': vals}}}


def test_thumb_peak_is_searched_over_the_full_series():
    # 경북 모양: 2015.08 고점 120, 2016.01 부터는 115 에서 101.9 까지(전체 고점 대비 -15.1%, 그린 구간 고점 대비 -11.4%)
    pre = [100 + i for i in range(19)] + [120] + [118, 117, 116, 115]     # 2014.01 ~ 2015.12(고점 2015.08)
    vals = pre + [115 - i * 0.1 for i in range(132)]                      # 2016.01 ~
    c = P._thumb_curve(_sts(vals), '경북')
    assert c[0][0][0] == '2016.01', '곡선은 2016.01 부터 그린다'
    assert c[1] is None, '고점이 그린 구간 앞이면 위치는 None'
    want = (vals[-1] / 120 - 1) * 100
    assert abs(c[2] - want) < 1e-9, (c[2], want)
    assert P.thumb_message('경북', c)[0] == '경북, 고점에서 %s' % P.thumb_pct(want)


def test_thumb_states_the_actual_fall():
    base = [100 + i * 0.5 for i in range(60)]          # 2016.01 부터 오른다, 고점 129.5
    fall = base + [129.5 * 0.971, 129.5 * 0.971]       # 고점 두 달 뒤 -2.9%
    msg = P.thumb_message('경북', P._thumb_curve(_sts(fall, 2016), '경북'))[0]
    assert '역대 최고가' not in msg and msg.endswith('-3%'), msg
    small = base + [129.5 * 0.996]                      # -0.4%
    assert P.thumb_message('경북', P._thumb_curve(_sts(small, 2016), '경북'))[0] == '경북, 고점에서 -0.4%'
    assert '역대 최고가' in P.thumb_message('경북', P._thumb_curve(_sts(base, 2016), '경북'))[0]


# ── D5 가장 적은 네 분기 ─────────────────────────────────────────────────
def test_min_window_includes_this_year():
    v = {'2025Q4': 60, '2026Q1': 50, '2026Q2': 40, '2026Q3': 36, '2026Q4': 89,          # 2026Q1~Q2 실적
         '2027Q1': 53, '2027Q2': 54, '2027Q3': 54, '2027Q4': 98,
         '2028Q1': 26, '2028Q2': 58, '2028Q3': 57, '2028Q4': 91}
    rows = [{'p': p, 'v': [x]} for p, x in sorted(v.items())]
    a, b, s = L4.min_window(rows, '2026Q1')
    assert (a, b, s) == ('2026Q1', '2026Q4', 215), (a, b, s)
    year = {y: sum(x for p, x in v.items() if p.startswith(y)) for y in ('2026', '2027', '2028')}
    assert s <= min(year.values()), '가장 적은 네 분기가 어느 해 네 분기보다 많다 — 앞 문단 올해 입주와 어긋난다'


def test_link4_min4_is_not_above_this_year():
    """실데이터 대조. 5편 단정이 새 데이터로 깨지면(Link4ClaimError) 초안 도구가 멈출 일이라 여기서는 대조하지 않는다 —
    게이트가 데이터 커밋을 막지 않게(CLAUDE.md 게이트 시험 원칙)."""
    import make_sido_pages as M
    adv, sts = M.load()
    try:
        n = L4.link4_numbers(adv, sts)
    except L4.Link4ClaimError:
        return
    num = lambda k: int(n[k].replace(',', ''))
    assert num('fq_min4v') <= num('y26') and num('fq_min4v') <= num('y27'), (n['fq_min4'], n['fq_min4v'], n['y26'], n['y27'])


# ── series_links 자기 건너뛰기 ───────────────────────────────────────────
def test_series_links_skip_self_by_zone_of_title(monkeypatch):
    import close_published_issues as CP
    zone = CP.KIND_TO_CATEGORY['지역 공급']
    posts = [dict(date='2026-09-29', cat=zone, url='self', title='2026년 광주·전남 아파트 공급물량 전망, 모자랍니다'),
             dict(date='2026-09-22', cat=zone, url='busan', title='2026년 부산 아파트 공급물량 전망, 전남광주와 반대'),
             dict(date='2026-09-25', cat=CP.KIND_TO_CATEGORY['주간 시세'], url='week', title='주간 아파트가격 동향')]
    monkeypatch.setattr(CP, 'fetch_posts', lambda: posts)
    html = P.series_links('전남광주', 1)
    assert 'self' not in html, '검색 표기 제목의 자기 글을 건다'
    assert 'busan' in html, '이 지역 이름이 곁들여 나온 다른 지역 편을 건너뛴다'
