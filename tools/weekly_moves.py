# -*- coding: utf-8 -*-
"""주간 '지난주와 무엇이 달라졌나'의 파이썬 정본 — 방향 표지와 시군구 순위 이동(홈 마케팅 검수 B7·RET-5, 2026-09-27).

주간 변동률은 대개 ±0.3%p 안에서 움직여 한 주 값만으로는 무엇이 바뀌었는지 보이지 않는다. 그래서 두 가지를
배치가 **여기서 한 번** 계산하고 화면·블로그는 결과를 읽기만 한다(CLAUDE.md 데이터 원칙: 사이트와 블로그가 다른
숫자를 말하면 안 된다).

  1. 방향 표지(시도·집계 19곳, 매매) — split_data 가 ADV.weekly.moves 로 싣고 홈 주간 격자가 읽는다.
     /weekly/ 타일과 블로그 주간 초안(make_naver_post)도 같은 함수(moves)를 부른다.
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
      · 'N주 연속 상승' / 'N주 연속 하락' — 연속이 STREAK_MIN(3)주 이상. 연속이 **보관 이력의 첫 주까지** 닿으면(그보다
        앞은 우리 자료에 없다) 'N주 이상 연속 상승'이라 적는다 — 이력이 156주뿐이라 '156주 연속'은 사실보다 짧게 말할 수 있다.
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


def tag(vals):
    """vals(오래된 주 → 최신 주)의 이번 주 표지. (방향 'up'|'dn', 문구, 연속 주 수, 이력 끝까지 닿았나 1|0) 또는 None
    — 규칙은 모듈 머리말."""
    s = streak(vals)
    if not s:
        return None
    k, n = (UP if s > 0 else DN), abs(s)
    if n >= STREAK_MIN:
        opened = 1 if n == len(vals) else 0
        return k, (TXT_STREAK_OPEN if opened else TXT_STREAK)[k] % n, n, opened
    if n == 1 and len(vals) >= 2 and direction(vals[-2]) is not None:
        return k, TXT_TURN[k], 1, 0
    return None


def moves(W):
    """ADV.weekly(regions·rows) → 이번 주 표지. 행이 둘 미만이거나 날짜가 없으면 None.

    돌려주는 것(split_data 가 ADV.weekly.moves 로 싣는 모양 그대로):
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
    """전환 시도 목록 → 한 줄. 홈 격자 머리·/weekly/ 타일 아래가 이 문장을 그대로 쓴다."""
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
