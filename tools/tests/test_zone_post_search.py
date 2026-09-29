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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_sido_pages as M  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _zone(monkeypatch, name='세종', seq=5, patch=None):
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = M.load()
    r = dict(next(z for z in adv['sido']['zones'] if z['z'] == name))
    r.update(patch or {})
    return P.draft_zone(adv, sts, r, seq, 16)


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
    assert b.startswith('2026 세종시 부동산 전망, ') and '공급물량' in b
    assert a.startswith('2026년 대전 아파트 공급물량 전망, ')


def test_first_heading_and_sentence_carry_search_terms(monkeypatch):
    d = _zone(monkeypatch)
    yrs = SZ.LEAD_Q // 4
    h = '<h3>세종시 적정 공급량과 %d년 공급물량</h3>' % yrs   # 검색 표기(SEARCH_NAME)
    assert h in d['body']
    first = d['body'].split(h, 1)[1].split('</p>', 1)[0]
    assert '적정 공급량' in first and '공급물량' in first
    assert d['title'].startswith('2026 세종시 부동산 전망') and '제목 실험 B안' in d['seq']


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


def test_gwangju_jeonnam_uses_search_forms(monkeypatch):
    """전남광주는 제목·첫 문장 '광주·전남', 태그 '광주'(2026-09-29 키워드도구: 광주아파트 5,740 대 전남광주부동산 160/월).
    변이: SEARCH_NAME·TAG_NAME 에서 전남광주를 빼면 빨개지고, _zone_of_title 이 검색 표기를 안 받으면 역매핑 시험이 빨개진다."""
    d = _zone(monkeypatch, name='전남광주', seq=6)
    assert d['title'].startswith('2027년 광주·전남 아파트 공급물량 전망, ') or d['title'].startswith('2026년 광주·전남 아파트 공급물량 전망, ')
    assert '<h3>광주·전남 적정 공급량과' in d['body']
    assert '광주아파트' in d['tags'] or '광주미분양' in d['tags']
    assert '광주부동산전망' in d['tags']
    names = [z for z in SZ.ORDER if z not in SZ.AGG]
    assert P._zone_of_title(d['title'], names) == '전남광주'


def test_province_tags_use_the_city_people_search(monkeypatch):
    """도 단위 편의 태그는 대표 도시(2026-09-29 키워드도구: 충북아파트 70 대 청주아파트 11,310/월). 제목은 도 이름 유지.
    변이: CITY_TAG 에서 충북을 빼면 빨개진다."""
    d = _zone(monkeypatch, name='충북', seq=7, patch={'uwarn': False})
    assert '청주부동산전망' in d['tags'] and '청주아파트' in d['tags'] and '충북아파트공급물량' in d['tags']
    assert '충북' in d['title']
