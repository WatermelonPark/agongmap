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


# ---- 전수리뷰 BL2-6·7·8·9·11: 도시 편 본문 문장(합성 캐시 + 저장소 ADV — 연도는 데이터의 마지막 주에서 센다)


def test_public_and_private_announcements_pair_with_the_listed_complex():
    """10-26 평택 원천: 부동산원 '고덕자연&하우스디(A4)' 517세대와 청약홈 '고덕 자연앤 하우스디(A4BL)(국민)' 328·'(민영)' 189 는
    한 단지다. 주소가 서로 다르게 적히고 입주 월도 석 달 밀려(청약 공고 뒤 일정 변경) 이름이 똑같아야만 짝지어진다. norm 에서 '(국민)/(민영)' 꼬리 떼기나 '&'→'앤'을 지우면
    세 행(517·328·189)이 되어 빨개진다(확인)."""
    raw = {'occ': [occ('2028-02', '고덕자연&하우스디(A4)', '경기도 평택시 고덕동 A4블록', 517),
                   occ('2028-06', '끝 단지', '경기도 평택시 비전동 1-1', 100)],
           'ch': [ch('2028-05', '고덕 자연앤 하우스디(A4BL)(국민)', '경기도 평택시 고덕국제화계획지구 A4BL', 328),
                  ch('2028-05', '고덕 자연앤 하우스디(A4BL)(민영)', '경기도 평택시 고덕국제화계획지구 A4BL', 189)]}
    rows = C.merge(raw, '평택', '2026-10')['rows']
    assert sorted(r['n'] for r in rows) == [100, 517], rows
    assert [r['ch_n'] for r in rows if r['n'] == 517] == [517]
