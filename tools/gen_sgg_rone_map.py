# -*- coding: utf-8 -*-
"""SGG_RONE_CLS(월간)·SGG_RONE_CLS_WK(주간) — KOSIS SGG 코드 → R-ONE CLS_ID 매핑 재생성·검증.

update_adv_data.SGG_RONE_CLS 는 월간, SGG_RONE_CLS_WK 는 주간 시군구 시세를 R-ONE 에서 받기 위한 매핑인데,
예전 주석이 존재하지 않는 `tools/scratchpad gen_map2.py`(월간)·`gen_map_wk.py`(주간)를 가리켜 부동산원이 표를
재구조화하면 재생성 방법이 없었다(2026-08-01 병렬 세션 인수인계 ①, 주간은 전수리뷰 A-9). 이 스크립트가 두 표의
절차다 — 저장소 안의 자료와 R-ONE 최신 시점 응답만으로 복원된다. ⚠️ 매핑은 손으로 옮기는 표라 원천이 새 시군구를
내기 시작해도 **저절로 붙지 않는다**(인천 신설 4구 월간 — 배치 기록 줄이 알린다, batch_notes.sgg_map_gap_lines).

재료
  · KOSIS 코드 목록      : update_adv_data.SGG_CODES (index.html NATION_TILE과 동일 집합)
  · KOSIS 코드 → 지역명  : 홈 SGG_QNAME (예: 'a80703' → '양주')
  · R-ONE CLS_ID → 지역명: R-ONE 매매지수표(월간 A_2024_00045 · 주간 T244183132827305) 최신 시점 행의
                           CLS_ID / CLS_NM / CLS_FULLNM

매칭 규칙
  R-ONE CLS_NM은 '양주시'처럼 접미사가 붙고 SGG_QNAME은 '양주'라 접미사(시/군/구)를
  떼고 맞춘다. 이름이 겹치는 구(중구·동구 등)는 그 행이 어느 시도 행 **밑에** 있는지로 가른다 —
  시도 행은 배치 수집과 같은 함수(update_adv_data.rone_sido_key: 평평한 이름, 없으면 가장 얕은 '>이름')로 찾는다.
  ⚠️ 예전엔 CLS_FULLNM 의 첫 토큰을 시도로 봤다. R-ONE 이 광주·전남을 '전남광주>광주'·'전남광주>전남' 밑으로 옮긴 뒤로는
  첫 토큰이 '전남광주'라 광주·전남 시도와 시군구 13개를 못 붙였다(전수리뷰 A-9 — 합성 계층으로 재현).

사용
  python tools/gen_sgg_rone_map.py                    # 월간: 현재 매핑과 대조만(변경 없음)
  python tools/gen_sgg_rone_map.py --write            # 월간: tools/data/sgg_rone_cls.json 으로 저장
  python tools/gen_sgg_rone_map.py --weekly [--write] # 주간: SGG_RONE_CLS_WK 와 대조(저장은 sgg_rone_cls_wk.json)
  --write 는 현재 매핑에만 있는 코드(재생성이 못 붙인 코드)가 하나라도 있으면 쓰지 않는다 — 통째로 옮기면 그 시군구가 빈다.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import update_adv_data as U
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

# 표 종류 → (R-ONE 표, 주기, 시점 칸, 대조할 현재 매핑 이름(update_adv_data), 저장 파일)
KINDS = {
    'monthly': (U.RONE_MONTHLY_TBL['maega'], 'MM', 'WRTTIME_IDTFR_ID', 'SGG_RONE_CLS', 'sgg_rone_cls.json'),
    'weekly': (U.RONE_TBL['maega'], 'WK', 'WRTTIME_DESC', 'SGG_RONE_CLS_WK', 'sgg_rone_cls_wk.json'),
}
# 최신 시점 하나가 쪽 경계에 걸려도 온전히 담기는 행 수(주간 한 주 ~236행·월간 한 달 ~234행) — 감시 RONE_FALLBACK_ROWS 와 같은 크기
NEED_ROWS = 3000


# KOSIS SGG 코드의 시도 접두 → R-ONE CLS_FULLNM의 시도 토큰
SIDO_PREFIX = {
    'a7': '서울', 'a8': '경기', 'a9': '인천', 'b1': '부산', 'b2': '대구',
    'b3': '광주', 'b4': '대전', 'b5': '울산', 'b6': '세종',
    'c1': '강원', 'c2': '충북', 'c3': '충남', 'c4': '전북', 'c5': '전남',
    'c6': '경북', 'c7': '경남', 'c8': '제주',
}
SUFFIX = re.compile(r'(특별자치시|특별자치도|광역시|특별시|시|군|구)$')


def _key():
    """RONE_API_KEY 는 환경 변수로만 읽는다(공개 저장소 규칙 — 키 파일 경로를 코드에 적지 않는다).
    로컬에서는 러너처럼 저장소 밖 키 파일을 먼저 불러 환경 변수로 넘긴 뒤 돌린다."""
    k = os.environ.get('RONE_API_KEY', '').strip()
    if k:
        return k
    raise SystemExit('RONE_API_KEY 환경 변수 필요')


def qname_map():
    """index.html SGG_QNAME — KOSIS 코드 → 표시용 지역명(접미사 없는 형태)."""
    h = HS.home_source()
    m = re.search(r'SGG_QNAME\s*=\s*(\{.*?\})\s*;', h, re.S)
    if not m:
        raise SystemExit('index.html에서 SGG_QNAME을 찾지 못했다 — 구조가 바뀌었는지 확인할 것')
    return json.loads(m.group(1).replace("'", '"'))


def rone_rows(kind):
    """R-ONE 표의 최근 행(배치 수집과 같은 조회 — 쪽 경계에 최신 시점이 잘리지 않게 끝에서 NEED_ROWS 행, 최근 석 달 창)."""
    _key()
    tbl, cycle = KINDS[kind][:2]
    return U._rone_recent_rows(tbl, NEED_ROWS, cycle=cycle, since=U._rone_since(cycle, 3))


def rone_regions(rows, field):
    """R-ONE 최신 시점 행 → [(CLS_ID, CLS_FULLNM, 이름토큰들, CLS_NM)]."""
    stamps = [str(r.get(field) or '').strip() for r in rows]
    mx = max(t for t in stamps if t)
    out = []
    for r, t in zip(rows, stamps):
        if t != mx:
            continue
        full = (r.get('CLS_FULLNM') or '').strip()
        parts = [p.strip() for p in full.split('>') if p.strip()]
        nm = (r.get('CLS_NM') or (parts[-1] if parts else '')).strip()
        out.append((int(r['CLS_ID']), '>'.join(parts), parts, nm))
    return out


def sido_rows(regions):
    """{시도 토큰(SIDO_PREFIX 값·'전국'): 그 시도 행의 CLS_FULLNM} — 배치 수집과 같은 함수(rone_sido_key)로 찾는다."""
    fulls = [full for _, full, _, _ in regions]
    out = {}
    for s in sorted(set(SIDO_PREFIX.values()) | {'전국'}):
        k = U.rone_sido_key(fulls, s)
        if k:
            out[s] = k
    return out


def sido_of(full, srows):
    """행 CLS_FULLNM 이 어느 시도 행 밑에 있나(가장 긴 시도 행 경로가 앞에 붙은 것). 없으면 ''."""
    best = ''
    for s, k in srows.items():
        if s != '전국' and full.startswith(k + '>') and len(k) > len(srows.get(best, '')):
            best = s
    return best


def strip_sfx(s):
    return SUFFIX.sub('', s) or s


def build(kind='monthly', rows=None):
    """kind 표의 매핑을 다시 만든다 → (매핑, 못 붙인 것 [(코드, 이름, 이유)]). rows 를 주면 원천 대신 그것을 읽는다(시험)."""
    field, cur_name = KINDS[kind][2:4]
    cur = getattr(U, cur_name)
    qn = qname_map()
    regions = rone_regions(rone_rows(kind) if rows is None else rows, field)
    srows = sido_rows(regions)
    # (시도토큰, 이름토큰) -> CLS_ID. 같은 이름이 여러 depth에 있으면 더 깊은 쪽(구)을 우선.
    idx = {}
    for cid, full, parts, nm in regions:
        k = (sido_of(full, srows), strip_sfx(nm))
        if k not in idx or len(parts) > idx[k][1]:
            idx[k] = (cid, len(parts))
    # 전국·시도 레벨: SGG_QNAME(타일 표시용)엔 없고 R-ONE 시도 행(sido_rows)에 있다.
    # ⚠️ 시도명엔 strip_sfx를 쓰지 않는다 — '대구'가 '대'로 잘린다(접미사 정규식이
    # 끝의 '구'를 시군구 접미사로 본다). 시도 행은 이름 그대로 찾는다.
    cid_of = {full: cid for cid, full, _, _ in regions}
    top = {s: cid_of[k] for s, k in srows.items()}
    # 분구 도시 본체(a80102 안양 등): SGG_QNAME엔 '안양 동안구'처럼 구 단위만 있어
    # 시 레벨 이름이 없다. 같은 접두를 공유하는 하위 코드들의 시 이름에서 되찾는다
    # (예: a801021 '안양 만안구' → 시 이름 '안양').
    # 부모 코드 자릿수가 지역마다 달라(경기 a801021→a80102, 충북 c20101→c201)
    # 고정 슬라이스는 못 쓴다. SGG_CODES에 실재하는 모든 접두를 후보로 등록한다.
    codeset = set(U.SGG_CODES)
    city_of = {}
    for c, n in qn.items():
        if ' ' not in n:
            continue
        city = strip_sfx(n.split(' ')[0])
        for L in range(len(c) - 1, 1, -1):
            pre = c[:L]
            if pre in codeset:
                city_of.setdefault(pre, city)
                break

    out, miss = {}, []
    for code in U.SGG_CODES:
        sido = SIDO_PREFIX.get(code[:2])
        # ① 전국
        if code == 'a0':
            if '전국' in top:
                out[code] = top['전국']
            else:
                miss.append((code, '전국', 'R-ONE 최상위에 전국 없음'))
            continue
        # ② 시도 자체(a7, b1 …)
        if sido and code == code[:2]:
            if sido in top:
                out[code] = top[sido]
            else:
                miss.append((code, sido, 'R-ONE 시도 레벨 없음'))
            continue
        nm = qn.get(code) or city_of.get(code)
        if not sido or not nm:
            miss.append((code, nm or '(이름없음)', '접두/이름 없음'))
            continue
        # SGG_QNAME이 '고양 덕양구'처럼 시+구 형태면 마지막 토큰이 R-ONE 이름
        leaf = strip_sfx(nm.split(' ')[-1])
        hit = idx.get((sido, leaf))
        if hit:
            out[code] = hit[0]
        else:
            # 현재 매핑에도 없으면 R-ONE 미수록(신설 행정구역 등) — 결함이 아니다.
            why = ('R-ONE 미수록(신설·개편 등)' if code not in cur
                   else '%s에서 %s 못 찾음' % (sido, leaf))
            miss.append((code, nm, why))

    # 폴백 — 천안(c301)·전주(c401)는 구 코드가 자식이 아니라 '형제'라(c302/c303이
    # c301의 하위가 아님) 접두 규칙으로 시 이름을 못 얻는다. 경기·충북은 자식 구조라
    # 위에서 해결된다. KOSIS 코드 체계가 시도별로 다른 탓이므로, 남은 코드와 남은
    # R-ONE 시 레벨 항목이 그 시도에서 **정확히 1:1일 때만** 짝짓는다(모호하면 포기).
    used = set(out.values())
    unnamed = [(c, SIDO_PREFIX.get(c[:2])) for c, n, why in miss if why == '접두/이름 없음']
    # qn에 '<시> <구>' 형태로 등장하는 분구 도시 이름(시도별)
    split_cities = {}
    for c, n in qn.items():
        sd = SIDO_PREFIX.get(c[:2])
        # '경기 광주'처럼 앞말이 시도 이름인 이름표(동명 광역시와 가르려고 붙인 머리말)는 분구 도시가 아니다(전수리뷰 H2-21)
        if ' ' in n and n.split(' ')[0] != sd:
            split_cities.setdefault(sd, set()).add(strip_sfx(n.split(' ')[0]))
    for sido in {sd for _, sd in unnamed if sd}:
        codes = [c for c, sd in unnamed if sd == sido]
        cands = [(cid, nm) for (sd, nm), (cid, _d) in
                 ((k, v) for k, v in idx.items() if k[0] == sido)
                 if cid not in used and nm in (split_cities.get(sido) or set())]
        if len(codes) == 1 and len(cands) == 1:
            out[codes[0]] = cands[0][0]
            miss = [m for m in miss if m[0] != codes[0]]
    return out, miss


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    kind = 'weekly' if '--weekly' in argv else 'monthly'
    built, miss = build(kind)
    cur = getattr(U, KINDS[kind][3])
    same = sum(1 for k, v in built.items() if cur.get(k) == v)
    diff = {k: (cur.get(k), v) for k, v in built.items() if k in cur and cur[k] != v}
    only_cur = sorted(set(cur) - set(built))
    only_new = sorted(set(built) - set(cur))
    print('[%s] 재생성 %d개 · 현재 %d개' % (kind, len(built), len(cur)))
    print('  일치 %d · 불일치 %d · 현재에만 %d · 신규 %d'
          % (same, len(diff), len(only_cur), len(only_new)))
    if diff:
        print('  불일치(코드: 현재→재생성):')
        for k, (a, b) in sorted(diff.items())[:20]:
            print('    %-10s %s -> %s' % (k, a, b))
    if only_cur:
        print('  현재에만 있음(재생성이 못 찾음):', ', '.join(only_cur[:20]))
    if only_new:
        print('  신규(현재 매핑에 없음 — 손으로 옮길 후보):', ', '.join('%s=%s' % (k, built[k]) for k in only_new[:20]))
    if miss:
        print('  매칭 실패 %d건:' % len(miss))
        for c, n, why in miss[:15]:
            print('    %-10s %-12s %s' % (c, n, why))
    if '--write' in argv:
        if only_cur:
            # 통째로 옮기면 그 시군구가 지도에서 빈다 — 못 붙인 이유(계층 개편 등)를 먼저 고친다.
            raise SystemExit('쓰지 않는다: 현재 매핑에만 있는 코드 %d개(%s) — 재생성이 못 붙인 이유를 먼저 확인할 것'
                             % (len(only_cur), ', '.join(only_cur[:10])))
        out = os.path.join(HERE, 'data', KINDS[kind][4])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(built, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print('saved', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
