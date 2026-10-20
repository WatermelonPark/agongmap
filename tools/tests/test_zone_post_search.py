# -*- coding: utf-8 -*-
"""지역 편 초안의 검색어·링크·제목 실험(2026-09-27 대표 승인, 조회수 조사 LINK-1·SRCH-1).

- 글 끝 링크는 회차와 상관없이 늘 그 지역 리포트로 가고, 캠페인에 회차가 붙는다(zone_deep_<seq>).
  문장은 회차마다 바뀐다(09-01 대표: 같은 문장이 반복되면 광고로 읽힌다).
- 제목 앞머리는 seq 5(세종)부터 B안('{연도} {검색 표기} 부동산 전망')·A안('{연도}년 {지역} 아파트
  공급물량 전망')을 번갈아 낸다. B안도 결론절에 '공급물량'을 한 번 넣는다.
- 첫 소제목은 '{지역} 적정 공급량과 N년 공급물량', 첫 문장에 '공급물량'과 '적정 공급량'.
- 태그는 그 지역 검색어 셋 + (미분양 경고 지역이면) '{지역}미분양'.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - cta() 의 목적지를 '/cycle/' 로 바꾸거나(옛 목적지 순환) 캠페인에서 회차를 빼면 → 링크 시험
  - title_arm() 이 늘 'A' 를 돌려주면 → 제목 실험 시험
  - 첫 소제목을 옛 '결론부터' 로 되돌리면 → 소제목 시험
  - 태그를 옛 일반어('아파트공급'·'집값전망')로 되돌리면 → 태그 시험
픽스처: 저장소의 실제 ADV.sido(세종) — 캡처·썸네일·RSS 는 끈다(네트워크·파일 쓰기 없음).
"""
import os
import re
import sys
from urllib.parse import quote

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_sido_pages as M  # noqa: E402
import sido_zones as SZ  # noqa: E402


# 조사일 전진 픽스처 — 실데이터 그대로(None), 전망 연도가 넘어가는 10월 첫 조사분, 한 해 더 뒤의 10월 조사분.
# 배치가 새 주를 덧붙이는 모양(마지막 행 복제 + 조사일만 바꿈)을 흉내 낸다.
SURVEYS = [None, '2026-10-05', '2027-10-04']


def _zone(monkeypatch, name='세종', seq=5, patch=None, survey=None):
    """실데이터로 지역 편 초안을 굽는다. survey 를 주면 ADV.weekly 끝에 그 조사일 행을 덧붙여 데이터 전진을 흉내 낸다.
    초안에 '_yr'(그 데이터의 전망 연도 — 정본 SZ.outlook_year(SZ.latest_survey(adv)))를 실어 기대값을 데이터에서 유도한다."""
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = M.load()
    if survey:
        rows = adv['weekly']['rows']
        rows.append(dict(rows[-1], p=survey))
    r = dict(next(z for z in adv['sido']['zones'] if z['z'] == name))
    r.update(patch or {})
    d = P.draft_zone(adv, sts, r, seq, 16)
    d['_yr'] = SZ.outlook_year(SZ.latest_survey(adv))
    assert d['_yr'], '조사일에서 전망 연도를 못 읽었다'
    return d


def test_cta_always_points_to_that_zone_report():
    href = '/zone/%s/?utm_source=naver_blog' % quote('세종')
    texts = []
    for seq in range(1, 19):
        h = P.cta('세종', seq)
        assert href in h, (seq, h)
        assert 'utm_campaign=zone_deep_%d"' % seq in h, (seq, h)
        texts.append(h.split('<br>')[0])
    assert all(a != b for a, b in zip(texts, texts[1:])), '인접 회차 문장이 같다'


def test_title_arms_alternate_from_seq5():
    arms = [P.title_arm(s) for s in range(1, 10)]
    assert arms == ['A', 'A', 'A', 'A', 'B', 'A', 'B', 'A', 'B']
    b = P.zone_title('세종', '2026', 3, '부족할까', 5)
    a = P.zone_title('대전', '2026', 3, '부족할까', 6)
    assert b.startswith('2026년 세종시 부동산 전망, ') and '공급물량' in b
    assert a.startswith('2026년 대전 아파트 공급물량 전망, ')


@pytest.mark.parametrize('survey', SURVEYS)
def test_first_heading_and_sentence_carry_search_terms(monkeypatch, survey):
    """제목 연도는 데이터(최신 주간 조사일)의 전망 연도다 — 연도를 박으면 10월 조사분이 들어오는 날 게이트가 데이터 커밋을
    막는다(전수리뷰 #98: '2026' 을 박아 2026-10-05 조사분에서 빨개졌고, 임시로 둔 ('2026년','2027년') 목록도 2027-10 조사분에서
    같은 일이 난다). 변이(실제로 확인): make_naver_post.draft_zone 의 yr 를 '2026' 으로 고정하면 2026-10-05·2027-10-04 칸이
    빨개지고, 단정을 옛 연도 목록으로 되돌리면 2027-10-04 칸이 빨개진다."""
    d = _zone(monkeypatch, survey=survey)
    yrs = SZ.LEAD_Q // 4
    h = '<h3>세종시 적정 공급량과 %d년 공급물량</h3>' % yrs   # 검색 표기(SEARCH_NAME)
    assert h in d['body']
    first = d['body'].split(h, 1)[1].split('</p>', 1)[0]
    assert '적정 공급량' in first and '공급물량' in first
    assert d['title'].startswith('%s년 세종시 부동산 전망' % d['_yr']) and '제목 실험 B안' in d['seq']


def test_tags_are_the_zone_search_terms(monkeypatch):
    d = _zone(monkeypatch, patch={'uwarn': False})
    assert d['tags'] == ['세종아파트공급물량', '세종적정공급량', '세종부동산전망', '세종아파트', '아공맵']
    d = _zone(monkeypatch, patch={'uwarn': True})
    assert '세종미분양' in d['tags'] and len(d['tags']) == 5


def test_title_year_is_the_outlook_year():
    """10월부터는 다음 해를 쓴다(2026-09-27 대표 결정). 변이: sido_zones.OUTLOOK_NEXT_FROM_MONTH(정본 — 블로그는 그 이름을 가져다
    쓴다)를 13 으로 두면 빨개진다."""
    assert P.outlook_year('2026-09-21') == '2026'
    assert P.outlook_year('2026-10-05') == '2027'
    assert P.outlook_year('2026-12-28') == '2027'
    assert P.outlook_year('') == ''


def test_no_mojara_in_zone_title_or_lead(monkeypatch):
    """'모자랍니다'가 블덱스에서 '#모자'로 뽑혔다(2026-09-28). 변이: ask 를 '모자랄까'로 되돌리면 빨개진다."""
    d = _zone(monkeypatch)
    assert '모자' not in d['title'] and '모자라' not in d['body'].split('</p>', 3)[1]


@pytest.mark.parametrize('survey', SURVEYS)
def test_gwangju_jeonnam_uses_search_forms(monkeypatch, survey):
    """전남광주는 제목·첫 문장 '광주·전남', 태그 '광주'(2026-09-29 키워드도구: 광주아파트 5,740 대 전남광주부동산 160/월).
    변이: SEARCH_NAME·TAG_NAME 에서 전남광주를 빼면 빨개지고, _zone_of_title 이 검색 표기를 안 받으면 역매핑 시험이 빨개진다.
    연도는 데이터에서 유도한다(전수리뷰 #98 — 박힌 연도 목록은 2027-10 조사분에서 게이트를 막는다)."""
    d = _zone(monkeypatch, name='전남광주', seq=6, survey=survey)
    assert d['title'].startswith('%s년 광주·전남 아파트 공급물량 전망, ' % d['_yr'])
    assert '<h3>광주·전남 적정 공급량과' in d['body']
    assert '광주아파트' in d['tags'] or '광주미분양' in d['tags']
    assert '광주부동산전망' in d['tags']
    names = [z for z in SZ.ORDER if z not in SZ.AGG]
    assert P._zone_of_title(d['title'], names) == '전남광주'
    # 보이는 글자에 내부 이름이 남지 않는다 — 소제목·글 끝 링크 이름(2026-10-08 실제 초안에서 '전남광주는 지금 어떤
    # 상태인가'·'전남광주 공급 리포트'가 나갔다). 주소(href)의 /zone/전남광주/ 는 판정 단위 이름이라 그대로다.
    # 변이: draft_zone 소제목이나 cta() 의 보이는 이름을 nm 으로 되돌리면 빨개진다.
    shown = re.sub(r'href="[^"]*"', '', d['body'])
    assert '전남광주' not in shown, re.findall(r'.{20}전남광주.{20}', shown)
    # 상태 소제목은 회차마다 돈다(반복률, 10-15) — 어느 틀이든 검색 이름으로 시작해야 한다.
    assert re.search(r'<h3>광주·전남(은 지금 어떤 상태일까| 시세와 미분양|의 지금, 시세부터)</h3>', d['body'])



def test_other_zone_posts_name_gwangju_jeonnam_by_its_search_form(monkeypatch):
    """전남광주가 다른 지역 편·주간 지표에 이름으로 실릴 때도 검색 표기('광주·전남')다(전수리뷰 BL1-7·T3-12).

    - 미분양 배수 최저 지역 편의 비교 문장('가장 높은 …의 N분의 1')
    - 주간 '이번 주의 지표: 30년 넘은 아파트' 상위 3
    - 경쟁 글 패널 검색어(kw)
    변이(확인): draft_zone 의 cmp_txt 를 esc(top['z']) 로, extra_section 노후 절을 esc(k) 로, kw 를 nm 으로 되돌리면 각각 빨개진다.
    픽스처: 실제 ADV.sido 사본에서 전남광주 um 을 모든 시도보다 크게(최저 지역은 데이터에서 고른다) 두고, 노후주택30년 계열은
    전남광주가 1위인 합성 한 해(집계 제외 시도 전부 채움)로 둔다 — 지금 데이터(전남광주 미분양 배수 중위·노후 4위)와 무관하게
    두 경로를 늘 탄다.
    """
    import copy
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = M.load()
    adv = copy.deepcopy(adv)
    # 전남광주 미분양 배수가 빈 달(그 지역만 값이 없는 회차)에도 같은 경로를 타게 전남광주는 값 유무와 무관하게 고르고,
    # 견줄 다른 지역 값이 하나도 없으면 한 곳을 합성 값으로 채운다 — 데이터가 앞으로 가도 StopIteration 으로 죽지 않는다.
    zs = [z for z in adv['sido']['zones'] if not z.get('agg')]
    gj = next(z for z in zs if z['z'] == '전남광주')
    others = [z for z in zs if z is not gj and z.get('um') is not None]
    if not others:
        others = [next(z for z in zs if z is not gj)]
        others[0]['um'] = 0.1
    gj['um'] = max(z['um'] for z in others) + 5
    zs = others + [gj]
    low = min(others, key=lambda z: z['um'])
    assert low['z'] != '전남광주'
    d = P.draft_zone(adv, sts, dict(low), 1, len(zs))
    shown = re.sub(r'href="[^"]*"', '', d['body'])
    assert '가장 높은 광주·전남(' in shown, '비교 문장이 안 나왔다 — 시험이 헛돈다'
    assert '전남광주' not in shown, re.findall(r'.{20}전남광주.{20}', shown)
    assert '전남광주' not in d['kw']
    assert P.draft_zone(adv, sts, dict(gj), 1, len(zs))['kw'] == '광주·전남 아파트 공급물량'
    sts = copy.deepcopy(sts)
    ser = {k: [1000 + i] for i, k in enumerate(k for k in SZ.ORDER if k not in SZ.AGG)}
    ser['전남광주'] = [9999999]
    sts['노후주택30년'] = {'dates': ['2025'], 'series': ser}
    html = P.extra_section(adv, sts, 3)
    assert '광주·전남 9,999,999세대' in html and '전남광주' not in html, html


def test_province_tags_use_the_city_people_search(monkeypatch):
    """도 단위 편의 태그는 대표 도시(2026-09-29 키워드도구: 충북아파트 70 대 청주아파트 11,310/월). 제목은 도 이름 유지.
    변이: CITY_TAG 에서 충북을 빼면 빨개진다."""
    d = _zone(monkeypatch, name='충북', seq=7, patch={'uwarn': False})
    assert '청주부동산전망' in d['tags'] and '청주아파트' in d['tags'] and '충북아파트공급물량' in d['tags']
    assert '충북' in d['title']


def test_zone_draft_stops_when_the_site_window_differs(monkeypatch):
    """배치가 구운 판정 창 H 가 블로그 셈의 SZ.LEAD_Q 와 다르면(부분 수집으로 H=11) 지역 편을 만들지 않고 멈춘다 — 블로그만 다른
    적정물량·배수를 쓰지 않게(전수리뷰 BL1 overflow: H=11 이면 블로그 '3년 적정물량 224,400'·4.4배 vs 사이트 '2.75년 205,700'·4.0배).
    같은 창이면 그대로 만든다.
    변이(확인): draft_zone 의 H 가드를 지우면 빨개진다.
    픽스처: 실제 ADV.sido 사본의 H 를 LEAD_Q−1 로 둔 상태(update_adv_data 가 막는 부분 수집의 모양)."""
    import copy
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = M.load()
    r = dict(next(z for z in adv['sido']['zones'] if not z.get('agg')))
    ok = copy.deepcopy(adv)
    ok['sido']['H'] = SZ.LEAD_Q
    assert P.draft_zone(ok, sts, r, 1, 16)['body']
    bad = copy.deepcopy(adv)
    bad['sido']['H'] = SZ.LEAD_Q - 1
    with pytest.raises(SystemExit) as e:
        P.draft_zone(bad, sts, r, 1, 16)
    assert '판정 창' in str(e.value)


def test_unsold_comparison_names_the_top_region_by_blog_name(monkeypatch):
    """미분양이 가장 적은 지역 편의 '가장 높은 ○○(…)에 비하면 N분의 1' 비교는 최고 지역을 블로그 이름(SEARCH_NAME)으로 쓴다 —
    키를 그대로 찍으면 광주·전남이 최고인 회차에 '가장 높은 전남광주'가 나간다(전수리뷰 X1-5).
    픽스처: 저장소 ADV.sido 에서 광주·전남(키 '전남광주')의 미분양 배수(um)만 최고값보다 크게 올린 상태 — 초안은 um 이 가장 낮은
    지역으로 굽는다. 변이(실제로 확인): draft_zone 의 cmp_txt 에서 SEARCH_NAME 을 빼고 top['z'] 를 그대로 쓰면 빨개진다."""
    key = '전남광주'
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = M.load()
    zs = [z for z in adv['sido']['zones'] if not z.get('agg') and z.get('um') is not None]
    assert len(zs) > 2 and any(z['z'] == key for z in zs), [z['z'] for z in zs]
    top = max(z['um'] for z in zs)
    for z in zs:
        if z['z'] == key:
            z['um'] = top + 1.0
    low = min((z for z in zs if z['z'] != key), key=lambda z: z['um'])
    for z in zs:                      # 같은 값으로 묶인 지역이 있어도 이 지역이 맨 아래가 되게(데이터에 따라 동률이 생긴다)
        if z is not low and z['um'] <= low['um']:
            z['um'] = low['um'] + 0.01
    body = P.draft_zone(adv, sts, dict(low), 3, 16)['body']
    shown = re.sub(r'href="[^"]*"', '', body)
    assert '가장 높은 %s(' % P.SEARCH_NAME[key] in shown, re.findall(r'가장 높은.{0,30}', shown)
    assert key not in shown, re.findall(r'.{20}%s.{20}' % key, shown)
