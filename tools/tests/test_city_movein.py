# -*- coding: utf-8 -*-
"""도시 입주 예정 단지 병합(city_movein.merge) — 광역시 편에서 단지를 두 번 세거나 남의 단지와 짝짓지 않는지(2026-10-16).

픽스처는 10-16 대구 편을 만들며 실제로 마주친 네 경우를 줄여 옮긴 것이다(주소·이름·세대수는 원천 그대로).
  ① 부산 해운대구 단지가 '대구' 글자 포함으로 대구에 들어왔다(924세대).
  ② 부동산원 '본리동자이'와 청약홈 '달서자이 제니크'(같은 구·같은 달·같은 360세대)가 짝지어지지 않아 두 번 셀 뻔했다.
  ③ 부동산원 목록 끝(occ_max) 뒤 같은 단지의 본 공고와 '(조합원 취소분)' 공고가 두 단지로 셌다(리뷰 F23 ①).
  ④ 이름 앞 여섯 글자만 같은 다른 단지끼리 짝지어졌다(옛 규칙 a[:6] == b[:6], 리뷰 F23 ②).

무엇을 깨뜨리면 빨개지나(실제로 확인): in_city 를 글자 포함으로 되돌리면 ①이, 구·달·세대수 규칙을 지우면 ②가,
occ_max 뒤 (주소, 달) 묶음을 지우면 ③이, 이름 앞 여섯 글자 규칙을 되살리면 ④가 빨개진다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import city_movein as C  # noqa: E402


def occ(ym, name, addr, n, kind='분양'):
    return {'입주예정월': ym, '아파트명': name, '주소': addr, '세대수': str(n), '사업유형': kind}


def ch(ym, name, addr, n, d='2026-01-01'):
    return {'MVN_PREARNGE_YM': ym.replace('-', ''), 'HOUSE_NM': name, 'HSSPLY_ADRES': addr, 'TOT_SUPLY_HSHLDCO': str(n),
            'RCRIT_PBLANC_DE': d}


RAW = {
    'occ': [
        occ('2027-02', '본리동자이', '대구광역시 달서구 본리동 661-9', 360),
        occ('2027-10', 'e편한세상 센텀 하이베뉴', '부산광역시 해운대구 재송동 1030-0', 924),
        occ('2027-06', '힐스테이트 대명센트럴', '대구광역시 남구 대명동 100-1', 500),
        occ('2028-06', '마지막 달 단지', '대구광역시 중구 남산동 1-1', 100),
    ],
    'ch': [
        ch('2027-02', '달서자이 제니크', '대구광역시 달서구 본리동 661-9번지 일원', 360, '2026-08-06'),
        ch('2027-07', '힐스테이트 대명센트럴2차', '대구광역시 남구 봉덕동 900-3', 300, '2025-03-01'),
        ch('2028-10', '범어역 파크드림 디아르', '대구광역시 수성구 수성동4가 996번지 일원', 47, '2026-03-27'),
        ch('2028-10', '범어역 파크드림 디아르(조합원 취소분)', '대구광역시 수성구 수성동4가 996번지', 3, '2026-06-01'),
    ],
}


def _rows():
    return C.merge(RAW, '대구', '2026-10')['rows']


def test_haeundae_is_not_daegu():
    assert not C.in_city('부산광역시 해운대구 재송동 1030-0', '대구')
    assert C.in_city('대구광역시 중구 사일동 15-1', '대구')
    assert C.in_city('충청북도 청주시 흥덕구 복대동', '청주')
    assert all('해운대' not in r['addr'] for r in _rows())


def test_same_gu_month_and_units_is_one_complex():
    r = [x for x in _rows() if x['gu'] == '달서구']
    assert len(r) == 1 and r[0]['n'] == 360 and r[0]['ch_n'] == 360, r


def test_extra_announcements_after_the_list_are_one_complex():
    r = [x for x in _rows() if '디아르' in x['name']]
    assert len(r) == 1, r
    assert r[0]['n'] == 50 and r[0]['name'] == '범어역 파크드림 디아르'


def test_a_shared_name_prefix_alone_does_not_pair():
    r = [x for x in _rows() if x['gu'] == '남구']
    assert sorted(x['n'] for x in r) == [300, 500], r     # 부동산원 대명센트럴 500 과 청약홈 2차 300 은 다른 단지


def test_city_code_is_the_weekly_code_above_its_districts():
    """도시 코드는 구 코드의 공통 앞부분을 주간 시세 코드에 있을 때까지 줄인 것 — 공통 앞부분 그대로('b20')면 시세 칸을 못 찾는다
    (10-16 첫 실행에서 ValueError). 구 목록은 홈 이름표(SGG_QNAME)에서 센다. while 조건에서 주간 코드 확인을 빼면 빨개진다(확인)."""
    import make_city_post as MC
    codes = MC.P.M.load()[0]['weekly']['sgg']['codes']
    code, gus = MC.city_codes('대구', codes)
    assert code == 'b2' and len(gus) >= 8 and all(c.startswith('b2') for _, c in gus)
    code, gus = MC.city_codes('청주', codes)
    assert code == 'c201' and [g for g, _ in gus] == ['상당구', '서원구', '청원구', '흥덕구']


def test_zone_post_link_picks_the_same_sido_zone_post_not_a_city_post(monkeypatch):
    """도시 편 끝의 '시도 단위로 본 글' 링크 — 같은 시도의 최신 **지역 편**만 고른다. 픽스처는 10-16 RSS 의 실제 제목 셋
    (대구 지역 편, 청주 도시 편, 광주·전남 지역 편)에 가상의 대구 도시 편 하나를 더한 것. 지역 이름 대조(_zone_of_title)를 빼면
    광주·전남 편이 골라져 빨개진다(확인). 도시 편은 _zone_of_title 이 이미 None 으로 거르고('입주물량' 제목),
    is_city_post 는 그 위의 두 번째 방어선이라 그것만 빼서는 빨개지지 않는다."""
    import datetime
    import close_published_issues as CPI
    import make_city_post as MC
    posts = [
        dict(date=datetime.date(2026, 8, 30), cat='지역별 아파트 공급', url='u-dg',
             title='2026년 대구 아파트 공급물량 전망, 안 팔리는데 지어지지도 않습니다'),
        dict(date=datetime.date(2026, 10, 8), cat='지역별 아파트 공급', url='u-cj',
             title='2027년 청주 아파트 입주물량, 정점을 찍고 2029년엔 4분의 1로 줄어듭니다'),
        dict(date=datetime.date(2026, 10, 12), cat='지역별 아파트 공급', url='u-gj',
             title='2027년 광주·전남 아파트 공급물량 전망, 강보합 국면이지만 내년 2분기부터 입주가 크게 줄어듭니다'),
        dict(date=datetime.date(2026, 10, 20), cat='지역별 아파트 공급', url='u-dg-city',
             title='2027년 대구 아파트 입주물량, 적정의 15%에 그쳐 전세가 먼저 오릅니다'),
    ]
    monkeypatch.setattr(CPI, 'fetch_posts', lambda *a, **k: posts)
    assert MC.zone_post('대구')['url'] == 'u-dg'
    assert MC.zone_post('충북') is None
