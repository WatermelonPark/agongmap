# -*- coding: utf-8 -*-
"""도시 입주 예정 단지 편(블로그 '지역별 아파트 공급' 카테고리, 제목에 '입주물량')의 재료 — 원천 수집과 단지 병합.

2026-09-30 청주 시범 편을 스크래치 스크립트로 만들었다가 임시 폴더가 비워져 잃었다(10-16). 광역시 편(대구)을 쓰기 전에
저장소로 옮기면서 리뷰 F23(광역시에서 한 단지를 두 번 세거나 다른 단지와 짝짓는 문제)을 함께 고쳤다.

원천(키는 환경 변수로만 읽는다):
  - 한국부동산원 입주예정물량정보(공공데이터포털 15111714, 30세대 이상 단지별) — DATA_GO_KR_KEY
  - 청약홈 APT 분양정보(ApplyhomeInfoDetailSvc) — DATA_GO_KR_KEY
  - KOSIS 주민등록인구(DT_1B040A3, 시군구) — KOSIS_API_KEY

    python tools/city_movein.py 대구 2026-10 --fetch    원천을 받아 tools/cache/city/ 에 두고 병합 결과를 찍는다
    python tools/city_movein.py 청주 2026-10 충북        도시와 시도 이름이 다르면 셋째 인자로 시도(사이트 이름)

합치는 규칙: 입주예정물량정보 마지막 달(occ_max)까지는 그 자료가 정본이다. 청약홈에도 있는 단지는 한 번만 세고 세대수는
입주예정물량정보 값을 쓴다. occ_max 다음 달부터는 청약홈 공고의 입주 예정월로 채운다(청약 공급 세대만이라 조합원·임대 몫이
빠진다). 시작 달(초안을 만드는 달)의 입주분까지 넣는다(09-30 대표). 청약홈에만 있는 공고는 같은 단지끼리 묶고, '(N회차)'·
조합원 취소분은 세대를 더하며 잔여·무순위 같은 재공고는 더하지 않는다(tail_kind, 전수리뷰 BL2-5).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache', 'city')
OCC_API = 'https://api.odcloud.kr/api/15111714/v1/uddi:0b257760-ac19-4841-adb4-b38b4d153397'
CH_API = 'https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail'
POP_TBL = dict(orgId='101', tblId='DT_1B040A3', itmId='T20', objL1='ALL', prdSe='M', newEstPrdCnt='1')


def _get(url, params):
    q = urllib.parse.urlencode(dict(params, serviceKey=os.environ['DATA_GO_KR_KEY']))
    with urllib.request.urlopen(url + '?' + q, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def source_names(sido):
    """사이트 시도 키 → 청약홈 지역 이름들. 판정 단위를 합친 '전남광주'는 원천이 통합 전 두 이름(광주·전남)으로 준다
    (정본 merge_regions.SRC·DST — 손으로 적지 않는다, 전수리뷰 BL2-15)."""
    import merge_regions as MR
    return tuple(MR.SRC) if sido == MR.DST else (sido,)


def site_key(name):
    """원천 이름(통합 전 두 이름, merge_regions.SRC)을 사이트 시도 키('전남광주')로. 그 밖의 이름은 그대로."""
    import merge_regions as MR
    return MR.DST if name in MR.SRC else name


def full_names(sido):
    """사이트 시도 키 → 주소·KOSIS 행의 시도 전체 이름들('전남광주' → 광주광역시·전라남도). 정본은 update_adv_data.BUBBLE_SHORT."""
    import update_adv_data as U
    src = source_names(sido)
    return tuple(k for k, v in U.BUBBLE_SHORT.items() if v in src)


def fetch(sido):
    """sido(사이트 시도 키, '대구'·'전남광주')의 원천을 받아 캐시에 쓴다. 입주예정물량정보는 전국을 다 받는다(도 안 몫에 쓴다).
    청약홈은 원천 지역 이름마다 받아 합친다(source_names)."""
    occ, page = [], 1
    while True:
        d = _get(OCC_API, {'page': page, 'perPage': 1000})
        occ += d.get('data') or []
        if len(occ) >= d.get('totalCount', 0) or not d.get('data'):
            break
        page += 1
    ch = []
    for area in source_names(sido):
        got, page = [], 1
        while page <= 40:
            d = _get(CH_API, {'page': page, 'perPage': 500, 'cond[SUBSCRPT_AREA_CODE_NM::EQ]': area})
            got += d.get('data') or []
            if len(got) >= d.get('matchCount', d.get('totalCount', 0)) or not d.get('data'):
                break
            page += 1
        ch += got
    import update_adv_data as U
    pop = U.kosis(POP_TBL)
    os.makedirs(CACHE, exist_ok=True)
    raw = dict(sido=sido, occ=occ, ch=ch, pop=pop)
    with open(os.path.join(CACHE, '%s.json' % sido), 'w', encoding='utf-8') as f:
        json.dump(raw, f, ensure_ascii=False)
    return raw


def load(sido):
    with open(os.path.join(CACHE, '%s.json' % sido), encoding='utf-8') as f:
        return json.load(f)


def norm(s):
    s = re.sub(r'[^0-9A-Za-z가-힣]', '', s or '')
    for w in ('블록', 'BL', '지구', '주택', '아파트'):
        s = s.replace(w, '')
    return s.lower()


# 청약홈 공고 이름의 꼬리(같은 단지의 추가 공고) — 떼고 한 단지로 묶는다(F23 ①). 꼬리는 두 갈래다(전수리뷰 BL2-5):
#   _ADD      같은 단지의 **또 다른 공급분** — 세대를 더한다('(2회차)'로 나눠 공급한 세대, 조합원 취소분).
#   _RESUPPLY 이미 공급한 세대를 **다시 내놓은 공고** — 세대를 더하지 않는다(잔여·무순위·계약취소·재공급·사후접수·추가입주자·임의공급).
# 병합(merge)과 올해 공고 집계(make_city_post.facts)가 이 분류(tail_kind) 하나를 쓴다.
_ADD = r'조합원\s*취소분|\d+\s*회차'
_RESUPPLY = r'잔여\s*세대|추가\s*입주자|무순위|계약\s*취소\s*주택|계약\s*취소|임의\s*공급|재공급|사후\s*접수'
_TAIL = re.compile(r'\s*[\(\[]?\s*(%s|%s).*$' % (_ADD, _RESUPPLY))


def base_name(s):
    return _TAIL.sub('', s or '').strip()


def tail_kind(s):
    """공고 이름의 꼬리 종류 — 'main'(본 공고), 'add'(세대를 더하는 추가 공급), 'resupply'(세대를 더하지 않는 재공고)."""
    m = _TAIL.search(s or '')
    if not m:
        return 'main'
    return 'add' if re.match(_ADD, m.group(1)) else 'resupply'


def adds_households(s):
    """이 공고의 세대가 새 공급으로 더해지는가(본 공고·추가 공급) — 병합과 공고 집계가 같은 답을 쓴다."""
    return tail_kind(s) != 'resupply'


def addr_key(addr):
    """주소를 번지까지 정규화한 열쇠 — '대구광역시 수성구 범어동 123-4번지 일원' → '수성구범어동123'."""
    a = re.sub(r'\s+', '', addr or '')
    m = re.search(r'([가-힣]+[구군])([가-힣0-9]+?[동읍면리가로])(산?\d+)', a)
    return ''.join(m.groups()) if m else norm(a)[:14]


_SUFFIX = ('', '시', '광역시', '특별시', '특별자치시')


def in_city(addr, city, within=None):
    """주소의 앞 두 낱말 가운데 하나가 그 도시인가. 글자 포함으로 보면 '해운대구'가 '대구'에 걸린다(10-16 대구 편 실측:
    부산 해운대구 단지 924세대가 대구로 들어왔다). within(시도 이름들)을 주면 둘째 낱말에서 맞은 도시는 첫 낱말이 그 시도일
    때만 받는다 — '경기도 광주시'가 광주(광주광역시)로 들어오지 않게(전수리뷰 BL2-15). 첫 낱말이 곧 도시('광주광역시')면 받는다."""
    t = (addr or '').split()[:2]
    names = [city + x for x in _SUFFIX]
    if t and t[0] in names:
        return True
    if len(t) > 1 and t[1] in names:
        return within is None or t[0] in within
    return False


def within_of(raw):
    """캐시(raw)의 시도 키로 주소 첫 낱말이 될 수 있는 이름들(전체·짧은 이름). 키가 없으면 None(거르지 않는다)."""
    sido = raw.get('sido')
    return (full_names(sido) + source_names(sido)) if sido else None


def gu_of(addr, city):
    t = (addr or '').split()
    for i, w in enumerate(t[:2]):
        if w in [city + x for x in _SUFFIX] and i + 1 < len(t) and re.fullmatch(r'[가-힣]+[구군]', t[i + 1]):
            return t[i + 1]
    return ''


def _months(ym):
    return int(ym[:4]) * 12 + int(ym[5:7])


def merge(raw, city, start):
    """도시 단지 목록. city 는 주소에 들어가는 이름('대구', '청주'), start 는 'YYYY-MM'.

    짝짓기는 부동산원 행에만 한다. 청약홈에만 있는 공고는 기간과 관계없이 (단지 이름, 주소 열쇠, 입주 월 ±6개월)로 한 묶음에
    모으고, 묶음 세대는 본 공고·추가 공급(tail_kind)의 합이다(재공고는 더하지 않는다). 공고는 공고일 순으로 처리해 원천이 주는
    순서와 무관하게 같은 답을 낸다(전수리뷰 BL2-5: 목록 기간의 청약홈 단독 행이 다음 공고의 짝이 되어 세대가 순서에 따라 갈리고
    출처가 '두 자료 모두'로 바뀌었다)."""
    occ_max = max(r['입주예정월'] for r in raw['occ'] if r.get('입주예정월'))
    within = within_of(raw)
    occ = [r for r in raw['occ'] if in_city(r.get('주소'), city, within) and (r.get('입주예정월') or '') >= start]
    ch = sorted((r for r in raw['ch'] if in_city(r.get('HSSPLY_ADRES'), city, within)),
                key=lambda c: (c.get('RCRIT_PBLANC_DE') or '', c.get('HOUSE_NM') or '', c.get('TOT_SUPLY_HSHLDCO') or ''))
    rows = [dict(ym=r['입주예정월'], name=r['아파트명'], gu=gu_of(r['주소'], city), addr=r['주소'],
                 n=int(r['세대수'] or 0), kind=r['사업유형'], src='입주예정물량정보', note='') for r in occ]
    groups = []
    for c in ch:
        ym = c.get('MVN_PREARNGE_YM') or ''
        ym = ym[:4] + '-' + ym[4:6] if len(ym) >= 6 else ''
        if not ym or ym < start:
            continue
        n = int(c.get('TOT_SUPLY_HSHLDCO') or 0)
        add = adds_households(c.get('HOUSE_NM'))
        b = norm(base_name(c.get('HOUSE_NM')))
        akey = addr_key(c.get('HSSPLY_ADRES'))
        # ② 짝짓기(부동산원 행만): 이름이 정확히 같은 행을 먼저 고르고, 없으면 (이름 일부 + 같은 주소 열쇠 또는 같은 달) 행.
        #    예전의 '이름 앞 6글자 같음'만으로는 광역시에서 다른 단지끼리 붙었다(F23).
        best = None
        for i, r in enumerate(rows):
            a = norm(r['name'])
            gap = abs(_months(r['ym']) - _months(ym))
            if a == b and gap <= 6:      # 이름이 똑같으면 입주 월이 몇 달 밀려도 같은 단지다(10-17 전주 '에코시티 더 클래스' 5월↔8월)
                best = i
                break
            if gap > 2:
                continue
            part = bool(a and b and (a in b or b in a))
            if best is None and part and (addr_key(r['addr']) == akey or r['ym'] == ym):
                best = i
            # 이름이 전혀 달라도(부동산원 '본리동자이' ↔ 청약홈 '달서자이 제니크', 10-16 대구) 같은 구·같은 달·같은 세대수면 같은 단지다.
            if best is None and r['ym'] == ym and r['n'] == n and r['gu'] and r['gu'] == gu_of(c.get('HSSPLY_ADRES'), city):
                best = i
        if best is not None:
            r = rows[best]
            r['ch_n'] = r.get('ch_n', 0) + (n if add else 0)
            r['ch_date'] = min(r.get('ch_date') or '9', c.get('RCRIT_PBLANC_DE') or '9')
            r['src'] = '입주예정물량정보 + 청약홈'
            r['note'] = '두 자료에 모두 있음, 세대수는 입주예정물량정보'
            continue
        # ① 청약홈 단독 공고는 같은 단지끼리 묶는다 — 추가·취소분·회차 공고가 따로 세지지 않게(F23).
        g = next((g for g in groups if g['key'] == (b, akey) and abs(_months(g['ym']) - _months(ym)) <= 6), None)
        if g is None:
            g = dict(key=(b, akey), ym=ym, name=base_name(c.get('HOUSE_NM')), gu=gu_of(c.get('HSSPLY_ADRES'), city),
                     addr=c.get('HSSPLY_ADRES'), n=0, re_n=None, kind='분양', src='청약홈', ch_date=c.get('RCRIT_PBLANC_DE'))
            groups.append(g)
        else:
            g['ch_date'] = min(g['ch_date'] or '9', c.get('RCRIT_PBLANC_DE') or '9')
        if add:
            g['n'] += n
        elif g['re_n'] is None:
            g['re_n'] = n         # 재공고뿐인 묶음은 첫 재공고 세대로 센다(본 공고가 목록 밖이다)
    for g in groups:
        if not g['n']:
            g['n'] = g['re_n'] or 0
        if g['ym'] <= occ_max and g['n'] < 30:
            continue      # 부동산원 목록은 30세대 이상 단지다. 그보다 작은 청약홈 묶음은 잔여·추가 공고다(10-17 천안 '용곡 두산위브' 7세대)
        del g['key'], g['re_n']
        g['ch_n'] = g['n']
        # 부동산원 목록 기간인데 그쪽에 없는 공고는 목록 갱신 뒤에 나온 공고다(10-16 대구 '더샵 동인센트리체' 10-02 공고).
        g['note'] = '입주예정물량정보에 없음 · 청약 공급 세대만 셈' if g['ym'] <= occ_max else '청약 공급 세대만 셈(조합원·임대 몫 제외)'
        rows.append(g)
    rows.sort(key=lambda r: (r['ym'], r['name']))
    return dict(city=city, start=start, occ_max=occ_max, rows=rows)


def population(raw, name):
    """(인구, 기준 'YYYYMM'). KOSIS 행 이름은 '대구광역시'·'청주시'·'충청북도'처럼 붙는다. 같은 줄기의 이름이 여럿이면
    정확한 이름 → 광역시·특별시 → '…시' 순으로 고른다 — 도시 광주가 경기 광주시(KOSIS 행 광주시)가 아니라 광주광역시가 되게(전수리뷰 BL2-15)."""
    rows = {}
    for x in raw['pop']:
        rows.setdefault(x.get('C1_NM') or '', x)
    for nm in (name, name + '특별시', name + '광역시', name + '특별자치시', name + '시'):
        if nm in rows:
            return int(float(rows[nm]['DT'])), rows[nm]['PRD_DE']
    raise KeyError(name)


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    city, start = args[0], args[1]
    sido = site_key(args[2] if len(args) > 2 else city)      # 통합 전 원천 이름 → 사이트 시도 키
    raw = fetch(sido) if '--fetch' in argv else load(sido)
    m = merge(raw, city, start)
    from collections import Counter
    by = Counter()
    for r in m['rows']:
        by[r['ym'][:4]] += r['n']
    print('occ_max', m['occ_max'], '단지', len(m['rows']), '세대', sum(r['n'] for r in m['rows']), dict(sorted(by.items())))
    print('인구', population(raw, city))
    for r in m['rows']:
        print(' ', r['ym'], '%6d' % r['n'], r['kind'][:4], r['src'][:6], r.get('ch_n', ''), r['gu'], r['name'][:34])
    return 0


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    sys.exit(main(sys.argv[1:]))
