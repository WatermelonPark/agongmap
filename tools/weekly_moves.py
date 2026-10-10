# -*- coding: utf-8 -*-
"""주간 '지난주와 무엇이 달라졌나'의 파이썬 정본 — 방향 표지와 시군구 순위 이동(홈 마케팅 검수 B7·RET-5, 2026-09-27).

주간 변동률은 대개 ±0.3%p 안에서 움직여 한 주 값만으로는 무엇이 바뀌었는지 보이지 않는다. 그래서 두 가지를
배치가 **여기서 한 번** 계산하고 화면·블로그는 결과를 읽기만 한다(CLAUDE.md 데이터 원칙: 사이트와 블로그가 다른
숫자를 말하면 안 된다).

  1. 방향 표지(시도·집계 19곳, 매매) — 블로그 주간 초안(make_naver_post)이 moves 를 부른다. 홈 주간 구역·/weekly/ 머리의
     시도 칸과 '방향이 바뀐 곳' 줄은 광역 단위를 걷으며 빠졌다(2026-10-02·10-03 대표 요청 — 시군구 지도로 바꿈).
  2. 시군구 순위 이동(매매) — /weekly/ 시군구 전체 표와 블로그 주간 초안이 rank_moves 를 부른다. 홈 통계 탭의
     상승·하락 TOP 10(home-app.js sggRanks·rankTables, 블로그가 캡처해 싣는 표)은 같은 규칙을 JS 로 계산한다 —
     둘이 같은 순위를 내는지는 test_weekly_moves 가 실데이터로 node 대조한다.

■ 표지 판정 규칙(정본 — 바꾸면 홈·/weekly/·블로그가 함께 바뀐다)
  - 한 주의 방향은 **표시값**(make_weekly_page.pv2r, 소수 둘째 자리 half-up — 사이트 pv2r 와 같다)의 부호다.
    표시가 0.00 이면 **보합**(방향 0)이다. 원값 +0.004 는 화면에 '0.00'으로 찍히므로 상승으로 세지 않는다 —
    원값 부호로 세면 '0.00' 칸에 '상승 전환'이 붙어 글자와 표지가 다른 말을 한다(2026-08-08 pv2 규칙과 같은 이유).
  - 연속(streak): 최신 주부터 거꾸로 같은 방향(상승 또는 하락)이 이어진 주 수. 보합·결측(None)에서 끊긴다.
    최신 주가 보합이거나 결측이면 0. 전체 이력(data.js 156주)으로 센다 — 코어가 싣는 최근 WINDOW 주로 자르지 않는다.
  - 표지(하나만, 위에서 먼저 맞는 것):
      · 'N주 연속 상승' / 'N주 연속 하락' — 연속이 STREAK_MIN(3)주 이상. 연속이 **그 지역의 첫 값까지** 닿으면(그보다
        앞은 우리 자료에 없다) 'N주 이상 연속 상승'이라 적는다 — 이력이 156주뿐이라 '156주 연속'은 사실보다 짧게 말할 수 있다.
        첫 값 앞의 결측(보관 이력 중간에 새로 생긴 시군구 코드 — 화성 분구 등)은 '이력 없음'이라 같은 뜻이다. 첫 값 **뒤**의
        결측에서 끊긴 연속은 '이상'이 아니다(그 앞 값이 있었다) — opened() 한 곳에서 판정한다(2026-09-27 D4 검토).
      · '상승 전환' / '하락 전환' — 이번 주가 상승(하락)인데 **바로 앞 회차**가 상승(하락)이 아니었다(하락·보합 → 상승).
        '보합에서 상승 전환'은 보도자료·기사가 쓰는 말과 같다. 앞 회차 값이 없으면(결측) 전환이라 하지 않는다.
      · 그 밖(2주 연속, 보합, 결측)은 표지 없음 — 새 소식이 아니다.
  - '앞 회차'는 rows 의 바로 앞 행이다(홈 TOP 10 의 '지난주'와 같다). 발표가 한 주 빠진 회차라도 날짜로 건너뛰지 않는다.
  - 표지는 매주 화면에 다시 그려지는 **상태**다. 블로그는 회차 간 반복을 피해(CLAUDE.md '회차 간 반복 금지') 이번 주에
    **새로 생긴 변화**만 쓴다 — news() 참고: 전환, 연속 STREAK_MIN 주에 막 들어선 곳, 연속이 이정표(MILESTONES)에 닿은 곳.

■ 시군구 순위 규칙(home-app.js sggRanks 와 같다)
  - 대상: 이름표(SGG_QNAME)에 있고 그 주 값이 있는 시군구. 순위는 **원값** 내림차순(1 = 가장 많이 오른 곳),
    같은 값이면 계열 순서(codes)가 앞선 곳이 먼저다(안정 정렬 — JS Array.sort 도 안정 정렬이다).
    원값으로 매기는 이유: 표시값(소수 둘째)으로 매기면 같은 '+0.05'가 수십 곳이라 순위가 계열 순서로 정해진다.
  - 이동 = 지난주 순위 − 이번 주 순위(양수 = 순위가 올라감, 홈 TOP 10 의 ▲). 지난주에 순위가 없던 곳은 None(NEW).

표준 라이브러리만 쓴다(split_data 는 fetch 잡에서 pip 없이 돈다).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sido_zones as SZ  # noqa: E402

# 홈 코어(data-core.js)에 싣는 최근 주 수. 표지는 전체 이력으로 판정해 싣고, 행은 이만큼만 싣는다.
WINDOW = 4
# 'N주 연속' 표지를 붙이는 최소 연속 주 수(RET-5 '3주 연속 ▲').
STREAK_MIN = 3

UP, DN = 'up', 'dn'
TXT_TURN = {UP: '상승 전환', DN: '하락 전환'}
TXT_STREAK = {UP: '%d주 연속 상승', DN: '%d주 연속 하락'}
TXT_STREAK_OPEN = {UP: '%d주 이상 연속 상승', DN: '%d주 이상 연속 하락'}   # 연속이 보관 이력 첫 주까지 닿았을 때
# 블로그가 '오래 이어진 연속'을 다시 쓰는 주(연속 주 수가 이 값에 막 닿은 주만). 3주(STREAK_MIN)는 '새로 연속에 들어선 곳'으로
# 따로 쓰고, 4주는 그 바로 다음 주라 두 주 연달아 같은 곳을 말하게 되므로 뺐다. 대략 두 달·한 분기·반년·1년·2년·3년.
MILESTONES = (8, 13, 26, 52, 104, 156)
LINE_HEAD = '지난주와 방향이 바뀐 곳'
LINE_NONE = '지난주와 방향이 바뀐 시도는 없습니다'


def _pv2r(v):
    import make_weekly_page as MW   # 반올림 정본(사이트 pv2r 와 node 로 대조됨). 순환 가져오기를 피해 안에서 부른다
    return MW.pv2r(v)


def direction(v):
    """표시값 부호: 1 상승 · -1 하락 · 0 보합 · None 결측."""
    if v is None:
        return None
    r = _pv2r(v)
    return 1 if r > 0 else (-1 if r < 0 else 0)


def streak(vals):
    """vals(오래된 주 → 최신 주)의 끝에서 같은 방향이 이어진 주 수. 상승이면 +N, 하락이면 −N, 보합·결측이면 0."""
    if not vals:
        return 0
    d = direction(vals[-1])
    if not d:
        return 0
    n = 0
    for v in reversed(vals):
        if direction(v) != d:
            break
        n += 1
    return n * d


def opened(vals, n):
    """끝에서 n 주 이어진 연속이 그 계열의 **첫 값**까지 닿았나(앞은 전부 결측 = 보관 이력 밖). 1|0."""
    return 1 if n and all(v is None for v in vals[:len(vals) - n]) else 0


def tag(vals):
    """vals(오래된 주 → 최신 주)의 이번 주 표지. (방향 'up'|'dn', 문구, 연속 주 수, 이력 끝까지 닿았나 1|0) 또는 None
    — 규칙은 모듈 머리말."""
    s = streak(vals)
    if not s:
        return None
    k, n = (UP if s > 0 else DN), abs(s)
    if n >= STREAK_MIN:
        o = opened(vals, n)
        return k, (TXT_STREAK_OPEN if o else TXT_STREAK)[k] % n, n, o
    if n == 1 and len(vals) >= 2 and direction(vals[-2]) is not None:
        return k, TXT_TURN[k], 1, 0
    return None


def moves(W):
    """ADV.weekly(regions·rows) → 이번 주 표지. 행이 둘 미만이거나 날짜가 없으면 None.

    돌려주는 것:
      {'p': 최신 조사일, 'prev': 앞 회차 조사일,
       'tags': {지역: ['up'|'dn', 문구, 연속 주 수, 이력 끝 1|0]}   — 표지가 있는 지역만(집계 포함). 전환은 연속 1,
       'turned': [[시도, 'up'|'dn'], …]   — 전환 표지가 붙은 시도(집계 제외), 표시 순서(DISPLAY_ORDER),
       'line': '지난주와 방향이 바뀐 곳: 부산 상승 전환 · 대구 하락 전환' 또는 LINE_NONE}
    """
    rows = W.get('rows') or []
    regs = W.get('regions') or []
    if len(rows) < 2 or not rows[-1].get('p'):
        return None
    tags = {}
    for i, r in enumerate(regs):
        vals = [(row.get('ma') or [])[i] if i < len(row.get('ma') or []) else None for row in rows]
        t = tag(vals)
        if t:
            tags[r] = list(t)
    order = [z for z in SZ.DISPLAY_ORDER if z not in SZ.AGG] + [z for z in regs if z not in SZ.DISPLAY_ORDER]
    turned = [[z, tags[z][0]] for z in order if z in tags and tags[z][2] == 1]
    return {'p': rows[-1]['p'], 'prev': rows[-2].get('p'), 'tags': tags, 'turned': turned,
            'line': turned_line(turned)}


def turned_line(turned):
    """전환 시도 목록 → 한 줄('지난주와 방향이 바뀐 곳: …')."""
    if not turned:
        return LINE_NONE
    return '%s: %s' % (LINE_HEAD, ' · '.join('%s %s' % (z, TXT_TURN[k]) for z, k in turned))


def news(mv):
    """이번 주에 **새로 생긴** 방향 변화 — 블로그 주간 초안이 쓴다(회차 간 반복 금지). 집계는 뺀다.

    돌려주는 것 {'turned': [(시도, 'up'|'dn')], 'entered': [(시도, 'up'|'dn')] — 연속 STREAK_MIN 주에 막 들어선 곳,
    'milestone': [(시도, 'up'|'dn', N)] — 연속이 MILESTONES 에 막 닿은 곳(이력 끝까지 닿은 '이상' 연속은 빼다 — 실제 길이를
    모른다)}. 목록은 표시 순서(DISPLAY_ORDER). 연속이 매주 1씩 느는 곳(예: 85주 → 86주)은 이정표가 아니면 싣지 않는다.
    """
    order = {z: i for i, z in enumerate(SZ.DISPLAY_ORDER)}
    tags = sorted(((z, t) for z, t in ((mv or {}).get('tags') or {}).items() if z not in SZ.AGG),
                  key=lambda x: order.get(x[0], 99))
    return {'turned': [(z, t[0]) for z, t in tags if t[2] == 1],
            'entered': [(z, t[0]) for z, t in tags if t[2] == STREAK_MIN and not t[3]],
            'milestone': [(z, t[0], t[2]) for z, t in tags if t[2] in MILESTONES and not t[3]]}


# ── 시군구 순위 ───────────────────────────────────────────────────────────────────────────────

def sgg_ranks(codes, row, names, met='ma'):
    """home-app.js sggRanks 와 같은 순위. (순서 [(코드, 값)], {코드: 순위})."""
    src = row.get(met) or []
    arr = [(c, src[i]) for i, c in enumerate(codes) if c in names and i < len(src) and src[i] is not None]
    arr.sort(key=lambda x: -x[1])        # 안정 정렬 — 같은 값은 계열 순서
    return arr, {c: i + 1 for i, (c, _) in enumerate(arr)}


def rank_moves(S, names, met='ma'):
    """ADV.weekly.sgg → 이번 주 순위와 이동.

    돌려주는 것: [(코드, 이번 주 값, 순위, 이동 또는 None)] — 순위 순서. 이동 = 지난주 순위 − 이번 주 순위.
    행이 하나뿐이면 모든 이동이 None 이다.
    """
    rows = S.get('rows') or []
    if not rows:
        return []
    order, rk = sgg_ranks(S['codes'], rows[-1], names, met)
    prev = sgg_ranks(S['codes'], rows[-2], names, met)[1] if len(rows) > 1 else {}
    return [(c, v, rk[c], (prev[c] - rk[c]) if c in prev else None) for c, v in order]


def move_text(d):
    """이동 → 표에 찍는 글자. 홈 TOP 10 dcell 과 같은 모양('▲3위' 대신 표 칸이 좁아 '▲3')."""
    if d is None:
        return 'NEW'
    if d > 0:
        return '▲%d' % d
    if d < 0:
        return '▼%d' % -d
    return '–'


# ── 시군구 → 시도(판정 단위) · 누적 · 시도 리포트 주간 표(홈 마케팅 검수 D4, 2026-09-27) ─────────────────
# 시도 리포트(make_sido_pages)가 그 시도의 시군구 주간 표를 굽는다. 순위·방향·연속은 위 함수(sgg_ranks·direction·
# streak)를 그대로 쓴다 — /weekly/ 표·블로그 초안과 같은 숫자여야 한다(같은 값을 재는 코드는 같은 함수).

# 시군구 코드(KOSIS 계열)의 시도 접두. home-app.js SIDO_PREFIX·sidoOf 의 파이썬 거울이다 — 홈 통계 탭의 '시도 → 시군구'
# 선택(sggOfSido)과 시도 리포트 표가 같은 시군구를 같은 시도에 둔다. 일치는 test_zone_weekly 가 실데이터 전 코드로
# node 대조한다(한쪽만 고치면 빨개진다). 수도권 셋(a7·a8·그 밖의 a)은 sidoOf 처럼 접두 두 글자가 아니라 첫 글자 뒤로 가른다.
SGG_PREFIX = {'a7': '서울', 'a8': '경기', 'a9': '인천', 'b1': '부산', 'b2': '대구', 'b3': '광주', 'b4': '대전',
              'b5': '울산', 'b6': '세종', 'c1': '강원', 'c2': '충북', 'c3': '충남', 'c4': '전북', 'c5': '전남',
              'c6': '경북', 'c7': '경남', 'c8': '제주'}
CUM_WEEKS = 12          # 시도 리포트 주간 표의 누적 창(주)


def sgg_sido(code):
    """시군구 코드 → 원천 시도 이름(home-app.js sidoOf 와 같은 답). 전국(a0)·모르는 접두는 None."""
    if not code:
        return None
    if code[0] == 'a':
        if code == 'a0':
            return None
        if code.startswith('a7'):
            return '서울'
        if code.startswith('a8'):
            return '경기'
        return '인천'
    return SGG_PREFIX.get(code[:2])


def sgg_zone(code):
    """시군구 코드 → 판정 단위(sido_zones.ORDER 의 이름). 광주·전남 시군구는 통합 단위(전남광주)로 — 통합 이름은
    과거 시계열 병합의 정본(merge_regions.SRC·DST)에서 읽는다. 시군구 주간 값 자체는 원천(R-ONE)이 계속 따로 낸다."""
    from merge_regions import SRC, DST   # 쓸 때 가져온다(표준 라이브러리만 쓰는 모듈)
    s = sgg_sido(code)
    return DST if s in SRC else s


def in_zone(code, z):
    """시군구 코드가 판정 단위 z 에 드는가 — 집계(전국·수도권·지방)는 소속 시도의 권역(SZ.REGION)으로 모은다. 전국 칸(a0)처럼
    시도가 없는 코드는 어디에도 들지 않는다. 시도 리포트의 표(zone_names)와 잘라 낸 지도(make_sido_pages.zone_tile)가 같은
    판정을 쓴다(10-10 코드 리뷰 — 같은 식이 두 곳에 따로 있었다)."""
    zz = sgg_zone(code)
    return zz is not None and (z == '전국' or zz == z or (z in SZ.AGG and SZ.REGION.get(zz) == z))


def zone_names(codes, names, z):
    """판정 단위 z 에 드는 시군구의 이름표 부분집합 {코드: 이름}(in_zone). 이름표(SGG_QNAME)에 없는 코드는 넣지 않는다 —
    홈 TOP 10·/weekly/ 표와 같은 대상."""
    return {c: names[c] for c in codes if c in names and in_zone(c, z)}


def _iso(p):
    import datetime
    try:
        return datetime.date(*(int(x) for x in str(p)[:10].split('-')))
    except (TypeError, ValueError):
        return None


def cum_window(rows, weeks=CUM_WEEKS):
    """최근 weeks 주 누적에 들어가는 행 번호 — **조사일로** 고른다(최신 조사일 − 7×weeks 일 < 조사일 ≤ 최신).

    행 번호 차(rows[-12:])로 잡지 않는다: 발표를 한 주 거른 회차가 있으면 12행이 13주가 된다(CLAUDE.md '전월·1년 전 칸은
    인덱스 차가 아니라 라벨로' 와 같은 이유). 거른 주의 변동은 다음 회차 값에 실려 있으므로(전 회차 대비) 창 안 행을 모두 이으면
    그 기간의 지수 변화와 같다. 창의 기준 주(최신 − weeks 주) **그 행**이 없으면 None — 이력이 창보다 짧을 때뿐 아니라
    기준 주가 원천이 거른 주일 때도 그렇다. 그 주가 없으면 창 첫 행이 '기준 주 한 주 전 → 다음 주' 두 주 치 변동을 싣고
    들어와 누적이 weeks+1 주(91일)를 덮는데 'weeks 주'로 적히기 때문이다(실데이터 2025-01-27·2025-10-06 거른 주의 12주 뒤
    회차, 전수리뷰 #12). 원천 값을 쪼개 채우지 않으므로 그 회차의 누적 칸은 비운다."""
    if not rows:
        return None
    last = _iso(rows[-1].get('p'))
    if last is None:
        return None
    import datetime
    base = last - datetime.timedelta(days=7 * weeks)
    ds = [_iso(r.get('p')) for r in rows]
    if base not in ds:
        return None
    return [k for k, d in enumerate(ds) if d is not None and base < d <= last]


def cum_change(rows, idx, i, met):
    """창(idx) 안 주간 변동률을 이어 곱한 누적 변동률(%) — 지수로 되돌리면 (기말 ÷ 기초 − 1) × 100 과 같다.
    창이 없거나 창 안에 결측이 하나라도 있으면 None(빈 주를 0 으로 세지 않는다)."""
    if not idx:
        return None
    acc = 1.0
    for k in idx:
        src = rows[k].get(met) or []
        v = src[i] if i < len(src) else None
        if v is None:
            return None
        acc *= 1 + v / 100.0
    return (acc - 1) * 100


def zone_table(S, names, z):
    """시도 리포트 주간 표의 행 — 판정 단위 z 의 시군구를 이번 주 매매 순(sgg_ranks 와 같은 순서·같은 대상)으로.

    돌려주는 것: [{'c': 코드, 'name': 이름, 'ma'/'je': 이번 주 원값, 'ma12'/'je12': CUM_WEEKS 주 누적(원값) 또는 None,
    'sma'/'sje': 연속(streak — 상승 +N·하락 −N·0), 'oma'/'oje': 연속이 보관 이력 첫 주까지 닿았나}] — 행이 둘 미만이면 [].
    표시(반올림)는 부르는 쪽이 make_weekly_page.pv2 로 한다. 연속은 streak() 그대로(표시값 부호, 보합·결측에서 끊김, 전체 이력).
    """
    rows = (S or {}).get('rows') or []
    codes = (S or {}).get('codes') or []
    if len(rows) < 2:
        return []
    sub = zone_names(codes, names, z)
    order, _ = sgg_ranks(codes, rows[-1], sub, 'ma')
    idx = {c: k for k, c in enumerate(codes)}
    win = cum_window(rows)
    out = []
    for c, _v in order:
        i = idx[c]
        r = {'c': c, 'name': names[c]}
        for met in ('ma', 'je'):
            vals = [((row.get(met) or [])[i] if i < len(row.get(met) or []) else None) for row in rows]
            s = streak(vals)
            r[met] = vals[-1]
            r[met + '12'] = cum_change(rows, win, i, met)
            r['s' + met] = s
            r['o' + met] = opened(vals, abs(s))
        out.append(r)
    return out


def streak_text(s, opened=0):
    """연속 → 표 칸 글자(칸 머리가 '연속(주)'라 단위는 뺀다). '▲5' · '▼3' · 이력 첫 주까지 닿으면 '▲156 이상'
    (TXT_STREAK_OPEN 과 같은 뜻) · 보합·결측 '–'."""
    if not s:
        return '–'
    return '%s%d%s' % ('▲' if s > 0 else '▼', abs(s), ' 이상' if opened else '')
