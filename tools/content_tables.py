# -*- coding: utf-8 -*-
"""원고의 자리표(`{{table:...}}`·`{{v:...}}`)를 사이트 데이터로 채운다(백로그 50).

왜 자리표인가. 원고에 숫자를 손으로 적으면 그 글은 쓴 날에 멈춘다. 배치는 매일 도는데 글만 옛 숫자를
말하게 된다 — 저장소 규칙(CLAUDE.md '사람이 센 수를 코드에 박지 않는다')을 콘텐츠로 넓힌 것이다.
모르는 자리표·없는 지역·빈 값은 **실패**다. 빈 표나 '·' 를 조용히 내보내면 AI 가 그걸 인용한다.

쓸 수 있는 것(자리표 이름 = 종류:인자…)
  moveins:<지역>[:<연도>]  입주물량. 연도를 주면 그 해 분기별, 없으면 연도별 합계(예정 포함)
  supply:<지역>            공급 판정 요약(적정물량·앞으로 3년·재고·누적 과부족·등급)
  stats:<계열>:<지역>      STATS 계열 최근 12기간(인허가·미분양·전세가율·준공·착공)
  weekly:<지역>            최근 8주 매매·전세 변동률
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATS_SERIES = ('인허가', '미분양', '전세가율', '준공', '착공')
WEEKLY_WEEKS = 8
STATS_PERIODS = 12


class TableError(Exception):
    """자리표를 채우지 못했다 — 생성기가 배치를 세운다."""


def _read_json(path):
    return json.load(io.open(path, encoding='utf-8'))


def load(root=None):
    """자리표가 읽는 데이터 묶음. 생성기가 한 번 읽어 모든 글에 넘긴다."""
    root = root or ROOT
    core = io.open(os.path.join(root, 'data-core.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'const ADV=(\{.*?\});', core, re.S).group(1))
    trend = _read_json(os.path.join(root, 'data-trend.json'))['ADV']
    rest = _read_json(os.path.join(root, 'data-rest.json'))['STATS']
    sgg = (_read_json(os.path.join(root, 'data-sgg.json'))['ADV'].get('weekly') or {}).get('sgg') or {}
    # 주간은 **trend** 쪽을 쓴다. data-core.js 에는 홈이 쓰는 최신 1주만 실려 있어, core 로는 '최근 8주' 표가
    # 한 줄짜리가 된다(2026-10-27 확인). 같은 원천의 같은 값이고 길이만 다르다.
    weekly_long = trend.get('weekly') or adv.get('weekly') or {}
    return {'sido': adv.get('sido') or {}, 'weekly': weekly_long,
            'occupancy': trend.get('occupancy') or {}, 'stats': rest,
            'sgg': sgg, 'sgg_names': _sgg_names(root)}


def _sgg_names(root):
    """시군구 코드 → 이름표(SGG_QNAME). 홈이 TOP 10·지도에 쓰는 그 표를 그대로 쓴다 — 이름이 갈리지 않게."""
    import home_src as HS
    m = re.search(r'const SGG_QNAME=(\{.*?\});', HS.home_source(root))
    if not m:
        raise TableError('홈에서 시군구 이름표(SGG_QNAME)를 찾지 못했다')
    return json.loads(m.group(1))


def _zones(data):
    return {z['z']: z for z in (data['sido'].get('zones') or [])}


def region_key(data, name):
    """화면 이름(광주·전남)과 내부 키(전남광주)를 모두 받아 내부 키로 돌려준다."""
    import sido_zones as SZ
    if name in SZ.ORDER:
        return name
    key = SZ.key_of(name)
    if key in SZ.ORDER:
        return key
    raise TableError('모르는 지역이다: %r' % name)


def num(v):
    if v is None:
        raise TableError('값이 비었다')
    return format(int(round(v)), ',')


def pct(v, digits=2):
    """변동률 표기. 소수 둘째 자리는 사이트 정본(make_weekly_page.pv2 = 홈 JS pv2r)을 그대로 쓴다.

    ⚠️ 부호는 **표시값** 으로 정한다. 원값 부호를 쓰면 -0.0012 가 '-0.00%' 로 나가 글자와 뜻이 어긋난다
       (사이트가 같은 이유로 pv2r 를 쓴다).
    """
    if v is None:
        raise TableError('값이 비었다')
    if digits == 2:
        import make_weekly_page as MW
        return MW.pv2(v)
    r = round(v, digits) + 0.0
    return ('+' if r > 0 else '') + ('%%.%df' % digits) % r


def _series_rows(block, key):
    """{'regions','rows'} 꼴에서 지역 열을 뽑는다 → [(기간, 값, 예정인가)]"""
    regs = block.get('regions') or []
    if key not in regs:
        raise TableError('%s 자료에 지역 %r 이 없다' % (block.get('note') or '', key))
    i = regs.index(key)
    out = []
    for r in block.get('rows') or []:
        v = (r.get('v') or [])
        out.append((r.get('p'), v[i] if i < len(v) else None, bool(r.get('e'))))
    return out


# ── 종류별 ──────────────────────────────────────────────────────────────────
def moveins(data, key, year=None):
    """입주물량. year 가 있으면 분기별, 없으면 연도별 합계. (머리, 행들, 각주)"""
    rows = _series_rows(data['occupancy'], key)
    if not rows:
        raise TableError('입주물량 자료가 비었다')
    if year:
        got = [(p, v, e) for p, v, e in rows if str(p).startswith(str(year))]
        if not got:
            raise TableError('입주물량에 %s년 자료가 없다(%s)' % (year, key))
        body = [[p, num(v), '예정' if e else '실적'] for p, v, e in got]
        tot = sum(v for _, v, _ in got if v is not None)
        body.append(['합계', num(tot), '예정 포함' if any(e for _, _, e in got) else '실적'])
        return ['분기', '세대', '구분'], body, '국토교통부 준공 실적 · 앞으로의 분기는 착공 실적에서 추정'
    by = {}
    for p, v, e in rows:
        y = str(p)[:4]
        a, kind = by.get(y, (0, '실적'))
        by[y] = (a + (v or 0), '예정' if e else kind)
    body = [[y, num(t), kind] for y, (t, kind) in sorted(by.items())]
    return ['연도', '세대', '구분'], body, '국토교통부 준공 실적 · 앞으로의 분기는 착공 실적에서 추정'


def supply(data, key):
    z = _zones(data).get(key)
    if not z:
        raise TableError('공급 판정에 지역 %r 이 없다' % key)
    import sido_zones as SZ
    H = data['sido'].get('H')
    body = [['분기 적정물량', num(z.get('ref')) + '호'],
            ['앞으로 %d분기 지어질 물량' % H, num(z.get('fut')) + '세대'],
            ['지난 재고(적정 대비)', num(z.get('inow')) + '세대'],
            ['누적 과부족', z.get('ctxt') or (num(z.get('dtot')) + '세대')],
            ['판정', SZ.GRADE_LABS[z['grade']] if hasattr(SZ, 'GRADE_LABS') else z['grade']]]
    return ['항목', '값'], body, '기준 %s · 국토교통부 준공·착공 실적' % (data['sido'].get('Ltxt') or data['sido'].get('L'))


def stats(data, name, key):
    if name not in STATS_SERIES:
        raise TableError('자리표가 모르는 계열이다: %r (쓸 수 있는 것: %s)' % (name, ', '.join(STATS_SERIES)))
    d = data['stats'].get(name) or {}
    ser = (d.get('series') or {}).get(key)
    dates = d.get('dates') or []
    if not ser or not dates:
        raise TableError('%s 자료에 지역 %r 이 없다' % (name, key))
    pairs = [(p, v) for p, v in zip(dates, ser)][-STATS_PERIODS:]
    unit = d.get('unit') or ''
    body = [[p, (pct(v, 1) if '%' in unit else num(v))] for p, v in pairs if v is not None]
    if not body:
        raise TableError('%s %s 에 값이 하나도 없다' % (name, key))
    return ['기간', '%s(%s)' % (name, unit) if unit else name], body, d.get('source') or ''


def sgg_codes(data, name):
    """도시·구 이름 → [(코드, 이름표)]. '부천' 처럼 구가 여럿이면 그 구를 모두 돌려준다(이름표 순서).

    ⚠️ 도시 한 줄 값을 만들지 않는다. 주간 시세는 지수 변동률이라 구를 평균 내면 원천이 발표하지 않은 수가
       된다(저장소 데이터 원칙). 도시 글에는 구별 표를 싣는다.
    """
    q = data.get('sgg_names') or {}
    exact = [(c, n) for c, n in q.items() if n == name]
    if exact:
        return exact
    pre = [(c, n) for c, n in q.items() if n.startswith(name + ' ')]
    return sorted(pre, key=lambda x: x[1])


def weekly_sgg(data, name):
    """시군구 주간 변동률. 구가 여럿인 도시는 **구별 최신 주** 한 줄씩."""
    S = data.get('sgg') or {}
    codes, rows = S.get('codes') or [], S.get('rows') or []
    got = [(c, n) for c, n in sgg_codes(data, name) if c in codes]
    if not got or not rows:
        raise TableError('주간 시세에 시군구 %r 이 없다' % name)
    last = rows[-1]
    body = []
    for c, n in got:
        i = codes.index(c)
        ma = (last.get('ma') or [None] * len(codes))[i]
        je = (last.get('je') or [None] * len(codes))[i]
        if ma is None and je is None:
            continue
        body.append([n, pct(ma) + '%' if ma is not None else '·',
                     pct(je) + '%' if je is not None else '·'])
    if not body:
        raise TableError('주간 시세 %s 에 값이 하나도 없다' % name)
    return (['지역', '매매', '전세'], body,
            '한국부동산원 주간 아파트가격동향 · %s 조사 · 전주 대비 변동률' % last.get('p'))


def weekly(data, key):
    W = data['weekly']
    regs = W.get('regions') or []
    if key not in regs:
        raise TableError('주간 시세에 지역 %r 이 없다' % key)
    i = regs.index(key)
    rows = (W.get('rows') or [])[-WEEKLY_WEEKS:]
    body = []
    for r in rows:
        ma = (r.get('ma') or [None] * len(regs))[i]
        je = (r.get('je') or [None] * len(regs))[i]
        if ma is None and je is None:
            continue
        body.append([r.get('p'), pct(ma) + '%' if ma is not None else '·',
                     pct(je) + '%' if je is not None else '·'])
    if not body:
        raise TableError('주간 시세 %s 에 값이 하나도 없다' % key)
    return ['조사 기준일', '매매', '전세'], body, '한국부동산원 주간 아파트가격동향 · 전주 대비 변동률'


# ── 자리표 해석 ─────────────────────────────────────────────────────────────
def table(data, kind, args):
    """(머리, 행들, 각주)"""
    if kind == 'moveins':
        if not 1 <= len(args) <= 2:
            raise TableError('moveins 자리표는 지역[:연도] 꼴이다')
        return moveins(data, region_key(data, args[0]), args[1] if len(args) > 1 else None)
    if kind == 'supply':
        if len(args) != 1:
            raise TableError('supply 자리표는 지역 하나를 받는다')
        return supply(data, region_key(data, args[0]))
    if kind == 'stats':
        if len(args) != 2:
            raise TableError('stats 자리표는 계열:지역 꼴이다')
        return stats(data, args[0], region_key(data, args[1]))
    if kind == 'weekly':
        if len(args) != 1:
            raise TableError('weekly 자리표는 지역 하나를 받는다')
        # 시도가 먼저다 — '서울'은 시도이고 '서울 강남구'는 시군구다. 시도가 아닐 때만 시군구로 본다.
        import sido_zones as SZ
        if args[0] in SZ.ORDER or SZ.key_of(args[0]) in SZ.ORDER:
            return weekly(data, region_key(data, args[0]))
        if sgg_codes(data, args[0]):
            return weekly_sgg(data, args[0])
        return weekly(data, region_key(data, args[0]))
    raise TableError('모르는 자리표 종류다: %r (쓸 수 있는 것: moveins, supply, stats, weekly)' % kind)


def value(data, kind, args):
    """문장 안에 넣는 한 값. 표의 '대표 값'과 같은 수를 쓴다."""
    head, body, _ = table(data, kind, args)
    if kind == 'moveins':
        row = body[-1]                      # 연도 표는 합계, 연도별 표는 마지막 해
        return row[1] + '세대'
    if kind == 'supply':
        return dict((r[0], r[1]) for r in body)['누적 과부족']
    if kind == 'stats':
        unit = head[1]
        return body[-1][1] + ('%' if '%' in unit else '호')
    if kind == 'weekly':
        return body[-1][1]                  # 최신 주 매매 변동률
    raise TableError('값으로 쓸 수 없는 자리표다: %r' % kind)
