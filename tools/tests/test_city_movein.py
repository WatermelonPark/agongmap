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
    10-17 천안 원천의 꼴('천안 휴먼빌 퍼스트시티(2회차)', 잔여 7세대 공고)을 줄여 옮겼다. 회차 공고는 입주 예정월이 한 달 늦다
    (같은 단지의 나중 동 — 묶음의 입주월은 공고일이 가장 이른 본 공고의 달이어야 순서와 무관하다)."""
    addr = '충청남도 천안시 서북구 성성동 100-1'
    later = '%s-%02d' % (ym_ch[:4], int(ym_ch[5:]) + 1)
    ann = [ch(ym_ch, '테스트 센트럴', addr, 500, '2026-03-02'),
           ch(later, '테스트 센트럴(2회차)', addr, 300, '2026-05-11'),
           ch(ym_ch, '테스트 센트럴(잔여세대)', addr, 7, '2026-07-20')]
    return {'occ': [occ('2027-03', '목록 단지', '충청남도 천안시 동남구 신부동 1-1', 400),
                    occ('2028-06', '끝 단지', '충청남도 천안시 동남구 청당동 1-1', 100)],
            'ch': [ann[i] for i in order]}


def test_announcement_only_complex_sums_rounds_in_any_order():
    """목록 기간(2027-09 ≤ 2028-06)과 목록 뒤(2028-10) 두 경우 모두, 원천 순서 여섯 가지가 같은 한 줄(800세대·출처 '청약홈')을 낸다.
    예전엔 목록 기간의 단독 행이 다음 공고의 짝이 되어 먼저 온 공고 값(500 또는 300)이 남고 출처가 '두 자료 모두'로 바뀌었다.
    변이(실제로 확인): 짝짓기 후보를 부동산원 행으로 한정한 것을 풀면(rows 에 단독 행을 바로 붙이면) 순서에 따라 n 이 갈려 빨개지고,
    재공고(잔여) 세대를 더하면 807 이 되어 빨개지고, 공고일 정렬(sorted … RCRIT_PBLANC_DE)을 빼면 묶음 입주월이 순서에 따라 갈려
    빨개진다."""
    import itertools
    for ym in ('2027-09', '2028-10'):
        seen = set()
        for order in itertools.permutations(range(3)):
            rows = C.merge(_round_raw(ym, order), '천안', '2026-10')['rows']
            t = [r for r in rows if '테스트' in r['name']]
            assert len(t) == 1, (ym, order, t)
            seen.add((t[0]['n'], t[0]['src'], t[0]['ch_n'], t[0]['name'], t[0]['ym']))
            assert sum(1 for r in rows if '+' in r['src']) == 0, rows     # 부동산원 행과 짝지어진 것이 없다
        assert seen == {(800, '청약홈', 800, '테스트 센트럴', ym)}, (ym, seen)


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


# ---- 전수리뷰 BL2-6·7·8·9·11: 도시 편 본문 문장(합성 캐시 + 저장소 ADV — 연도는 데이터의 마지막 주에서 센다)
def _metro_raw(now_y, n_next):
    """광역시 하나(대전)의 캐시: 다음 해(now_y+1) 입주 n_next 세대 한 단지 + 목록 끝 단지 하나 + 지난 공고 하나. 인구는 KOSIS 꼴."""
    y1 = now_y + 1
    return {'sido': '대전',
            'occ': [occ('%d-03' % y1, '대전 단지', '대전광역시 유성구 봉명동 1-1', n_next),
                    occ('%d-06' % (y1 + 1), '대전 끝', '대전광역시 서구 둔산동 1-1', 100)],
            'ch': [_ann('%d-05' % (now_y - 1), '대전 옛 단지', '대전광역시 서구 둔산동 2', 500, '%d-01-10' % (now_y - 3))],
            'pop': [{'C1_NM': '대전광역시', 'DT': '1440000', 'PRD_DE': '%d09' % now_y}]}


def _now_y():
    import make_city_post as MC
    return int(MC.P.M.load()[0]['weekly']['sgg']['rows'][-1]['p'][:4])


def test_metro_paragraph_compares_only_when_move_ins_dry_up(monkeypatch):
    """광역시 편의 준공 문단: 다음 해 입주가 최근 세 해 평균 준공의 절반(DONE_DROP) 아래일 때만 '수도꼭지가 거의 잠긴 셈'을 쓰고,
    아니면 숫자만 둔다. 준공 실적 단위는 '세대'다. 기본 제목의 '…에 그쳐' 결론절도 입주 공백(gap)일 때만 나온다.
    재현: 10-16 대구 틀이 대전(2027 입주가 최근 준공보다 많다)에서도 그대로 나가던 상태. 준공 실적은 저장소 ADV.occupancy.
    변이(확인): dried() 가드를 지워 늘 비교 문장을 쓰면 많은 쪽에서, '%s년 %s세대'를 '%s호'로 되돌리면, titles 가 gap 을 안 보면
    각각 빨개진다."""
    import re
    now_y = _now_y()
    MC, f = _city_facts(monkeypatch, _metro_raw(now_y, 1), '대전', '%d-10' % now_y, '대전')
    assert f['done'], '대전 준공 실적(ADV.occupancy)이 비었다'
    avg = sum(f['done'][y] for y in sorted(f['done'])[-3:]) / len(sorted(f['done'])[-3:])
    seen = {}
    for n_next in (1, int(avg * 2) + 1):          # 끊긴 해와 오히려 많은 해 — 두 갈래를 모두 지난다
        MC, f = _city_facts(monkeypatch, _metro_raw(now_y, n_next), '대전', '%d-10' % now_y, '대전')
        html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 3, '')
        assert not re.search(r'\d호', html), html
        seen[n_next] = ('수도꼭지' in html, MC.dried(f), MC.gap(f), MC.default_titles(f)[0])
    (d1, dr1, g1, t1), (d2, dr2, g2, t2) = seen[1], seen[int(avg * 2) + 1]
    assert d1 and dr1 and not d2 and not dr2, seen
    assert g1 and '그쳐' in t1 and ('그쳐' in t2) == g2, seen


def test_gun_particle_flat_week_and_tool_fonts(monkeypatch, tmp_path):
    """① 연속 상승이 가장 긴 곳이 군이면 '달성군가'가 아니라 '달성군이'(ga → P.iga). ② 이번 주 매매·전세가 모두 0.00 이면 소제목이
    '0주 연속 하락'이 아니라 '보합'이다(실제 156주 가운데 청주 2주·천안 1주가 그랬다). ③ 반기 차트는 저장소 글꼴(ZC.font)로 그려
    Windows 밖에서도 돈다. 변이(확인): '%s가'로 되돌리면 ①이, stxt 를 '+'가 아니면 '하락'으로 되돌리고 소제목 분기를 지우면 ②가,
    C:\\Windows 글꼴 경로로 되돌리면 ③이 빨개진다."""
    now_y = _now_y()
    MC, f = _city_facts(monkeypatch, _metro_raw(now_y, 1), '대전', '%d-10' % now_y, '대전')
    f['gu_w'] = {'달성군': dict(ma='+0.05', je='+0.01', sma=('+', 3), sje=('+', 1)),
                 '중구': dict(ma='+0.02', je='+0.01', sma=('+', 1), sje=('+', 1))}
    f['city_w'] = dict(ma='0.00', je='0.00', sma=('0', 0), sje=('0', 0))
    html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 3, '')
    assert '매매는 달성군이 +0.05%로 3주째' in html, html
    assert '이번 주 매매·전세 보합' in html and '0주 연속' not in html
    f['city_w'] = dict(ma='+0.02', je='0.00', sma=('+', 2), sje=('0', 0))
    assert '매매 2주 연속 상승' in MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 3, '')
    assert [MC.stxt(s) for s in (('+', 2), ('-', 4), ('0', 0), ('·', 0))] == ['2주 연속 상승', '4주 연속 하락', '보합', '보합']
    MC.chart(f, str(tmp_path / 'c.png'), MC.P.THUMB_PALETTES[MC.P.THUMB_GROUP['대전']])
    assert (tmp_path / 'c.png').stat().st_size > 0


def test_full_year_sentence_never_breaks(monkeypatch):
    """한 해를 다 센 해: 1월에 시작하면 그해도 든다. 다 센 해가 없으면(목록이 다음 해 중간에서 끝남) 비율 자리가 빈 '한 해 적정
    입주량의 입니다' 대신 그 사실을 쓴다. 재현: 2027-01 초안·목록 끝 2028-06 꼴(연도는 데이터에서 센다).
    변이(확인): full_years 를 '시작 연도 다음 해부터'로 되돌리면 1월 시작에서, fy 가 빈 갈래를 지우면 5월 시작에서 빨개진다."""
    now_y = _now_y()
    y = now_y + 1
    for start, want_full in (('%d-01' % y, [str(y)]), ('%d-05' % y, [])):
        MC, f = _city_facts(monkeypatch, _metro_raw(now_y, 3000), '대전', start, '대전')
        assert f['full_years'] == want_full, (start, f['full_years'], f['occ_max'])
        html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 3, '')
        assert '적정 입주량의 입니다' not in html and '적정 입주량의 예요' not in html
        assert ('다 센 해는 아직 없어요' in html) == (not want_full), html


def test_zone_post_follows_the_category_canon(monkeypatch):
    """도시 편 끝 지역 편 링크는 카테고리 이름 정본(P.ZONE_CAT ← CP.KIND_TO_CATEGORY)을 읽는다 — 글자로 박으면 정본이 바뀌는 날
    링크가 경고 없이 빠진다(make_naver_post.ZONE_CAT 리뷰 09-18 선례). 변이(확인): '지역별 아파트 공급' 글자로 되돌리면 빨개진다."""
    import datetime
    import close_published_issues as CPI
    import make_city_post as MC
    monkeypatch.setattr(MC.P, 'ZONE_CAT', '새 공급 카테고리')
    posts = [dict(date=datetime.date(2026, 8, 30), cat='새 공급 카테고리', url='u-dg',
                  title='2026년 대구 아파트 공급물량 전망, 안 팔리는데 지어지지도 않습니다')]
    monkeypatch.setattr(CPI, 'fetch_posts', lambda *a, **k: posts)
    assert MC.zone_post('대구')['url'] == 'u-dg'


def test_announcement_tally_uses_the_merge_classifier(monkeypatch):
    """올해 공고 집계(facts 의 ann_cnt·ann_hh)는 병합과 같은 분류(CM.adds_households)로 센다 — 본 공고 600 + '(2회차)' 200 은 넣고
    '(잔여세대)' 9 는 뺀다. 그래서 병합 줄의 세대(800)와 그해 공고 세대가 같다. 재현: 10-17 천안 원천처럼 회차 공고가 따로 나온
    단지(전수리뷰 BL2-5 — 예전 거르기는 꼬리가 붙은 공고를 모두 빼 회차 세대가 병합에는 들고 집계에서는 빠졌다).
    변이(확인): ann 거르기를 예전 'base_name(이름) == 이름'으로 되돌리면 ann_hh 가 600 이 되어 빨개진다."""
    now_y = _now_y()
    raw = _metro_raw(now_y, 1)
    addr = '대전광역시 중구 선화동 1-1'
    mv = '%d-09' % (now_y + 3)                 # 목록(끝 달 now_y+2 년 6월) 뒤 입주 — 청약홈 묶음으로 센다
    raw['ch'] = raw['ch'] + [_ann(mv, '대전 새 단지', addr, 600, '%d-03-02' % now_y),
                             _ann(mv, '대전 새 단지(2회차)', addr, 200, '%d-04-01' % now_y),
                             _ann(mv, '대전 새 단지(잔여세대)', addr, 9, '%d-05-01' % now_y)]
    MC, f = _city_facts(monkeypatch, raw, '대전', '%d-10' % now_y, '대전')
    y = str(now_y)
    assert (f['ann_cnt'][y], f['ann_hh'][y]) == (2, 800), (f['ann_cnt'], f['ann_hh'])
    row = [r for r in f['rows'] if r['name'] == '대전 새 단지']
    assert len(row) == 1 and row[0]['n'] == f['ann_hh'][y], row


def test_city_post_site_links_mid_and_end(monkeypatch):
    """도시 편 사이트 링크는 둘이다: 단지 표 바로 아래(utm_content=mid, 시도 리포트의 시군구 시세 표 #weekly-sgg)와 글 끝
    (utm_content=end, 분기별 공급 리포트). 캠페인은 도시별 city_<도시>, UTM 은 '#' 앞이다. 끝 문장은 댓글을 직접 청하지 않는다.
    재현: 10-20 총괄 진단 직전 상태(링크가 글 끝 하나뿐, '댓글로 알려 주세요' 끝 문장). 픽스처는 대전 도시 편(_metro_raw).
    변이(확인): 중간 링크 append 를 지우면, site_link 에서 utm_content 를 빼면, 끝 문장을 '댓글로 알려 주세요'로 되돌리면, 광역시 갈래(one)를 지우면, 링크 문장을 '사이트 리포트'로 되돌리면 각각 빨개진다."""
    import re
    from urllib.parse import quote
    now_y = _now_y()
    for k in range(5):                                  # 문장 변형(kk) 다섯 갈래를 모두 지난다
        MC, f = _city_facts(monkeypatch, _metro_raw(now_y, 1), '대전', '%d-10' % now_y, '대전')
        html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', k, '')
        hrefs = re.findall(r'href="([^"]*utm_source=naver_blog[^"]*)"', html)
        zone = [h for h in hrefs if '/zone/' in h]
        assert [re.search(r'utm_content=(\w+)', h).group(1) for h in zone] == ['mid', 'end'], hrefs
        assert all('utm_campaign=city_%s' % quote('대전') in h for h in zone), zone
        assert zone[0].endswith('#weekly-sgg') and '#' not in zone[1], zone
        assert all(h.index('?') < h.index('#') for h in zone if '#' in h), zone
        assert html.index(zone[0]) > html.index('</table>') > 0, '중간 링크가 단지 표 아래에 있지 않다'
        assert '댓글' not in html, html[-600:]
        links = [p for p in re.findall(r'<p>(.*?)</p>', html) if '/zone/' in p and 'utm_content' in p]
        assert len(links) == 2 and all('아공맵' in p and '사이트' not in p for p in links), links   # 독자는 '사이트'가 어디인지 모른다(10-20 총괄)
        assert '대전 바깥' not in html and '대전 전체' not in html, '광역시 편에서 도시와 시도 이름이 겹친다'


def test_month_less_row_shows_year_only(monkeypatch):
    """원천(입주예정물량정보)이 달 없이 연도만 준 단지는 표에 '2027.00'이 아니라 '2027년 중'으로 쓴다.
    재현: 10-22 서울 편 두산위브더프레스티지(구로구, '2027-00', 302세대)가 '2027.00'으로 찍혔다. 픽스처는 대전 목록에 그런 한 줄을 더한 것.
    변이(확인): body 의 '-00' 갈래를 지우면 빨개진다."""
    now_y = _now_y()
    raw = _metro_raw(now_y, 1)
    raw['occ'].append(occ('%d-00' % (now_y + 1), '대전 달없음', '대전광역시 서구 둔산동 3-3', 302))
    MC, f = _city_facts(monkeypatch, raw, '대전', '%d-10' % now_y, '대전')
    html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 0, '')
    assert '.00</td>' not in html and '<td>%d년 중</td>' % (now_y + 1) in html, html[:400]


def test_copula_after_vowel_ending(monkeypatch):
    """'…세대'·'…%' 뒤 서술격 조사는 '예요'다('1,088세대이에요' 금지). 자리에 들어가는 값이 늘 세대수·퍼센트로 끝나 받침이 없다.
    재현: 10-23 진주·서울 초안의 '해마다 나누면 …세대이에요', '…%이에요'. 픽스처는 대전 목록(_metro_raw), 회차 0~4 모든 틀.
    변이(확인): 틀 세 곳 가운데 하나를 '%s이에요'로 되돌리면 빨개진다."""
    import re
    now_y = _now_y()
    for k in range(5):
        for start in ('%d-10' % now_y, '%d-05' % (now_y + 1)):
            MC, f = _city_facts(monkeypatch, _metro_raw(now_y, 3000), '대전', start, '대전')
            html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', k, '')
            assert not re.search(r'(세대|%)이에요', html), (k, start)


def test_city_without_announcements(monkeypatch):
    """2020년 이후 청약홈 분양 공고가 하나도 없는 도시도 초안이 나온다(공고 절은 '한 건도 없습니다'로 짧게).
    재현: 10-23 구미(입주 예정 2곳, 공고 0)에서 statistics.median 빈 목록으로 멈췄다. 픽스처는 대전 목록에서 청약홈 행을 모두 뺀 것.
    변이(확인): facts 의 'if ann else None' 을 지우면(StatisticsError), body 의 past 갈래를 지우면(max 빈 목록) 각각 빨개진다."""
    now_y = _now_y()
    raw = _metro_raw(now_y, 1)
    raw['ch'] = []
    MC, f = _city_facts(monkeypatch, raw, '대전', '%d-10' % now_y, '대전')
    assert f['ann_med'] is None
    html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 0, '')
    assert '2020년 이후 한 건도 없습니다' in html and '분양 공고는 한 건도 없어요' in html
    # 올해 처음 공고가 난 도시(견줄 지난 해가 없음)도 같은 짧은 문단으로 쓴다
    raw['ch'] = [_ann('%d-05' % (now_y + 3), '대전 첫 공고', '대전광역시 서구 둔산동 9', 400, '%d-02-10' % now_y)]
    MC, f = _city_facts(monkeypatch, raw, '대전', '%d-10' % now_y, '대전')
    assert f['ann_med'] is not None
    html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', 0, '')
    assert '올해 1건(400세대)뿐이에요' in html, html[:300]


def test_need_is_two_percent_of_households(monkeypatch):
    """적정 입주량 셈 문장은 '인구 ÷ 2.5 = 약 N가구, 가구 수의 2% = 연 M세대'다. 2.5로 나눈 값은 가구 수라 '약 N세대'로 쓰지 않는다
    (10-23 대표 지적, 총괄 전달: '가구당 2.5명으로 나눈 세대의 2%'는 가구와 세대를 섞어 쓴 잘못). 픽스처는 대전 목록, 회차 0~4 모든 틀.
    변이(확인): 틀 하나를 '약 %s세대'로 되돌리면 빨개진다."""
    import re
    now_y = _now_y()
    for k in range(5):
        MC, f = _city_facts(monkeypatch, _metro_raw(now_y, 3000), '대전', '%d-10' % now_y, '대전')
        html = MC.body(f, ('a', 'b'), 'x.xlsx', '전망', k, '')
        assert '가구 수의 2%' in html and not re.search(r'약 [\d,]+세대', html), k
