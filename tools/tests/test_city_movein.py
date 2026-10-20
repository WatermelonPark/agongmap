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
    # 천안은 구 코드 공통 앞부분이 'c30'이라 줄이면 충남 전체(c3)로 갔다(10-17). 첫 구 앞의 이름 없는 칸이 도시 합계다.
    assert MC.city_codes('천안', codes)[0] == 'c301'
    assert MC.city_codes('원주', codes) == ('c102', [])      # 구가 없는 시


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


def test_tiny_and_shifted_announcements_are_not_new_complexes():
    """10-17 천안·전주 원천: 부동산원 목록 기간의 30세대 미만 청약홈 공고(잔여분 7세대)는 새 단지가 아니고, 이름이 똑같은
    단지는 입주 월이 석 달 밀려도 같은 단지다. 30세대 규칙이나 6개월 창을 지우면 빨개진다(확인)."""
    raw = {'occ': [occ('2027-08', '전주 에코시티 더 클래스', '전라북도 전주시 덕진구 송천동 1-1', 44),
                   occ('2028-06', '끝 단지', '전라북도 전주시 완산구 효자동 1-1', 100)],
           'ch': [ch('2027-05', '전주 에코시티 더 클래스', '전라북도 전주시 덕진구 송천동2가 1', 48),
                  ch('2026-10', '천안 용곡 두산위브', '전라북도 전주시 완산구 용곡동 1', 7)]}
    rows = C.merge(raw, '전주', '2026-10')['rows']
    assert sorted(r['n'] for r in rows) == [44, 100], rows


def test_announcement_round_tail_is_not_part_of_the_name():
    """청약홈 공고 이름의 '(2회차)' 꼬리는 단지 이름이 아니다(10-17 천안 '천안 휴먼빌 퍼스트시티(2회차)'가 본문에 그대로 나갔다).
    _TAIL 에서 회차 규칙을 지우면 빨개진다(확인)."""
    assert C.base_name('천안 휴먼빌 퍼스트시티(2회차)') == '천안 휴먼빌 퍼스트시티'
    assert C.base_name('천안 아이파크 시티 2단지(2회차)') == '천안 아이파크 시티 2단지'


def test_outlook_file_splits_into_lead_and_outlook(tmp_path, monkeypatch):
    """전망 파일 첫 덩어리는 글머리 결론으로 맨 앞에 간다(10-17 대표 리뷰: 결론이 글 끝에만 있었다). 빈 줄로 나누는 규칙을
    지우면(한 덩어리로 돌려주면) 빨개진다(확인). 픽스처는 원주 전망 파일의 꼴(결론 두 문장 + 빈 줄 + 전망)."""
    import make_city_post as MC
    monkeypatch.setattr(MC, 'OUT', str(tmp_path))
    (tmp_path / 'city-원주-outlook.txt').write_text('원주는 결론입니다. 둘째 문장입니다.\n\n제 판단으로는, 전망입니다.', encoding='utf-8')
    f = dict(city='원주', city_w=dict(sje=('+', 1), sma=('-', 18), je='+0.09', ma='-0.01'), now_y=2026, by_year={}, need=2925,
             share=lambda v: 0, ann_med=32, ann_cnt={'2026': 0}, ann_hh={'2026': 0}, gu_w={})   # ann_hh: 공고 세대수(cb395a3 ann_hh_now) — 실제 f 는 ann_cnt 와 함께 만든다
    lead, outlook = MC.outlook_text(f)
    assert lead == '원주는 결론입니다. 둘째 문장입니다.' and outlook == '제 판단으로는, 전망입니다.'


# ---- 전수리뷰 BL2-5: 청약홈 단독 공고의 묶음·세대 규칙(순서 무관, 회차는 더하고 재공고는 더하지 않는다)
def _round_raw(ym_ch, order):
    """부동산원 목록(끝 달 2028-06)에 없는 단지 하나의 본 공고 500 + '(2회차)' 300 + '(잔여세대)' 7. order 로 원천 순서를 바꾼다.
    10-17 천안 원천의 꼴('천안 휴먼빌 퍼스트시티(2회차)', 잔여 7세대 공고)을 줄여 옮겼다."""
    addr = '충청남도 천안시 서북구 성성동 100-1'
    ann = [ch(ym_ch, '테스트 센트럴', addr, 500, '2026-03-02'),
           ch(ym_ch, '테스트 센트럴(2회차)', addr, 300, '2026-05-11'),
           ch(ym_ch, '테스트 센트럴(잔여세대)', addr, 7, '2026-07-20')]
    return {'occ': [occ('2027-03', '목록 단지', '충청남도 천안시 동남구 신부동 1-1', 400),
                    occ('2028-06', '끝 단지', '충청남도 천안시 동남구 청당동 1-1', 100)],
            'ch': [ann[i] for i in order]}


def test_announcement_only_complex_sums_rounds_in_any_order():
    """목록 기간(2027-09 ≤ 2028-06)과 목록 뒤(2028-10) 두 경우 모두, 원천 순서 여섯 가지가 같은 한 줄(800세대·출처 '청약홈')을 낸다.
    예전엔 목록 기간의 단독 행이 다음 공고의 짝이 되어 먼저 온 공고 값(500 또는 300)이 남고 출처가 '두 자료 모두'로 바뀌었다.
    변이(실제로 확인): 짝짓기 후보를 부동산원 행으로 한정한 것을 풀면(rows 에 단독 행을 바로 붙이면) 순서에 따라 n 이 갈려 빨개지고,
    재공고(잔여) 세대를 더하면 807 이 되어 빨개진다."""
    import itertools
    for ym in ('2027-09', '2028-10'):
        seen = set()
        for order in itertools.permutations(range(3)):
            rows = C.merge(_round_raw(ym, order), '천안', '2026-10')['rows']
            t = [r for r in rows if '테스트' in r['name']]
            assert len(t) == 1, (ym, order, t)
            seen.add((t[0]['n'], t[0]['src'], t[0]['ch_n'], t[0]['name']))
            assert sum(1 for r in rows if '+' in r['src']) == 0, rows     # 부동산원 행과 짝지어진 것이 없다
        assert seen == {(800, '청약홈', 800, '테스트 센트럴')}, (ym, seen)


def test_resupply_after_the_list_does_not_add_households():
    """목록 뒤(occ_max 다음) 본 공고 47 + '(무순위)' 12 는 47 이고, '(조합원 취소분)' 3 은 더해 50 이다(10-16 대구 '범어역 파크드림
    디아르' 꼴). 무순위를 '추가 공급'(_ADD)으로 옮기면 빨개진다(확인)."""
    addr = '대구광역시 수성구 수성동4가 996번지'
    raw = dict(RAW, ch=RAW['ch'] + [ch('2028-10', '범어역 파크드림 디아르(무순위)', addr, 12, '2026-09-01')])
    r = [x for x in C.merge(raw, '대구', '2026-10')['rows'] if '디아르' in x['name']]
    assert len(r) == 1 and r[0]['n'] == 50, r
    assert [C.tail_kind(x) for x in ('A', 'A(2회차)', 'A(조합원 취소분)', 'A(잔여세대)', 'A(무순위)', 'A 계약취소주택', 'A(사후접수)')] \
        == ['main', 'add', 'add', 'resupply', 'resupply', 'resupply', 'resupply']


# ---- 전수리뷰 BL2-15: 광주·전남(판정 단위 '전남광주')의 도시 편 — 원천 이름·경기 광주시
def test_merged_sido_key_maps_to_both_source_names():
    """사이트 키 '전남광주'는 청약홈 '광주'·'전남' 두 이름으로 받고, 주소·KOSIS 의 시도 전체 이름은 광주광역시·전라남도다(정본
    merge_regions.SRC·update_adv_data.BUBBLE_SHORT 에서 센다). source_names 가 키를 그대로 돌려주면 빨개진다(확인)."""
    import merge_regions as MR
    assert C.source_names(MR.DST) == tuple(MR.SRC)
    assert C.source_names('대구') == ('대구',)
    assert set(C.full_names(MR.DST)) == {'광주광역시', '전라남도'}
    assert C.site_key('광주') == MR.DST and C.site_key('청주') == '청주'


def test_gyeonggi_gwangju_is_not_gwangju_metro():
    """입주예정물량정보는 전국을 받는다. '경기도 광주시' 단지가 광주(광주광역시) 행에 섞이지 않고, 인구는 광주광역시 줄을 고른다.
    within 거르기를 빼면(in_city 가 둘째 낱말만 보면) 경기 광주시 단지가 들어와 빨개지고, population 이 '광주시'를 먼저 보면
    빨개진다(확인). 픽스처는 실제 주소 꼴(경기도 광주시 오포읍)과 KOSIS 행 이름(광주시·광주광역시)을 줄여 옮겼다."""
    raw = {'sido': '전남광주',
           'occ': [occ('2027-03', '광주 단지', '광주광역시 북구 운암동 1-1', 300),
                   occ('2027-04', '오포 단지', '경기도 광주시 오포읍 신현리 1-1', 900),
                   occ('2028-06', '끝 단지', '전라남도 순천시 해룡면 1-1', 100)],
           'ch': [ch('2028-10', '경기 광주 공고', '경기도 광주시 태전동 1-1', 500, '2026-05-01')],
           'pop': [{'C1_NM': '광주시', 'DT': '390000', 'PRD_DE': '202609'},
                   {'C1_NM': '광주광역시', 'DT': '1400000', 'PRD_DE': '202609'}]}
    rows = C.merge(raw, '광주', '2026-10')['rows']
    assert [r['name'] for r in rows] == ['광주 단지'], rows
    assert C.population(raw, '광주') == (1400000, '202609')
    assert C.in_city('경기도 광주시 오포읍', '광주')          # 시도를 모르면(옛 캐시) 예전처럼 받는다
    assert C.in_city('전라남도 순천시 해룡면', '순천', C.within_of(raw))


def _ann(ym, name, addr, n, d):
    """facts 가 세는 청약홈 분양 공고 한 줄(아파트·분양주택)."""
    return dict(ch(ym, name, addr, n, d), RENT_SECD_NM='분양주택', HOUSE_SECD_NM='APT')


def _gwangju_raw():
    """광주·전남 캐시(시도 키 '전남광주')를 줄인 것: 광주광역시 단지 3,000, 경기 광주시 단지 900(전국 목록에 섞여 온다), 전남 순천
    단지 100(목록 끝 2028-06). 인구 행은 KOSIS 꼴(광주시·광주광역시·전라남도)."""
    return {'sido': '전남광주',
            'occ': [occ('2027-03', '광주 단지', '광주광역시 북구 운암동 1-1', 3000),
                    occ('2027-04', '오포 단지', '경기도 광주시 오포읍 신현리 1-1', 900),
                    occ('2028-06', '순천 끝', '전라남도 순천시 해룡면 1-1', 100)],
            'ch': [_ann('2024-05', '광주 옛 단지', '광주광역시 북구 운암동 2', 500, '2022-01-10'),
                   _ann('2029-01', '광주 새 단지', '광주광역시 서구 화정동 1', 600, '2026-03-01')],
            'pop': [{'C1_NM': '광주시', 'DT': '390000', 'PRD_DE': '202609'},
                    {'C1_NM': '광주광역시', 'DT': '1400000', 'PRD_DE': '202609'},
                    {'C1_NM': '전라남도', 'DT': '1800000', 'PRD_DE': '202609'}]}


def _city_facts(monkeypatch, raw, city, start, sido):
    """합성 캐시로 make_city_post.facts 를 돌린다(시세 칸은 저장소 ADV). RSS 는 빈 목록으로 막는다(망 없음)."""
    import close_published_issues as CPI
    import make_city_post as MC
    monkeypatch.setattr(MC.CM, 'load', lambda s: raw)
    monkeypatch.setattr(CPI, 'fetch_posts', lambda *a, **k: [])
    return MC, MC.facts(city, start, sido)


def test_gwangju_city_post_runs_on_the_merged_sido(monkeypatch):
    """광주·전남 안의 도시 편이 끝까지 돈다(예전엔 facts 의 next() 가 '전남광주'에서 StopIteration, '광주'로 주면 ValueError,
    '전남'이면 THUMB_GROUP KeyError). 시도 몫은 광주광역시·전라남도 두 이름을 합쳐 세고(경기 광주시 900 은 빠진다),
    본문은 시도를 화면 이름('광주·전남')으로 쓴다. 변이(확인): full_names 를 한 이름만 돌려주게 하면 sido_all·pop_share 가
    어긋나 빨개지고, 본문의 sname 을 sido 로 되돌리면 '전남광주'가 보여 빨개진다."""
    import re
    import merge_regions as MR
    MC, f = _city_facts(monkeypatch, _gwangju_raw(), '광주', '2026-10', MR.DST)
    assert f['sido_all'] == 3100 and f['sido_city'] == 3000, f
    assert abs(f['pop_share'] - 1400000 / 3200000) < 1e-9 and f['pop'] == 1400000
    html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 3, '')
    seen = re.sub(r'<[^>]+>', ' ', html)
    assert MR.DST not in seen and MC.P.SEARCH_NAME[MR.DST] in seen
    with __import__('pytest').raises(SystemExit):
        MC.main(['광주', '2026-10', '경기광주'])        # 사이트 시도 키가 아니면 알아듣게 멈춘다
