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
            'sgg': sgg, 'sgg_names': _sgg_names(root), 'cities': _city_moveins(root)}


def _city_moveins(root):
    """도시(시군구) 입주물량 — tools/data/city_moveins.json. 없으면 빈 묶음(시도 자리표는 그대로 돈다)."""
    p = os.path.join(root, 'tools', 'data', 'city_moveins.json')
    return _read_json(p) if os.path.exists(p) else {}


def _sgg_names(root):
    """시군구 코드 → 이름표(SGG_QNAME). 홈이 TOP 10·지도에 쓰는 그 표를 그대로 쓴다 — 이름이 갈리지 않게."""
    import home_src as HS
    m = re.search(r'const SGG_QNAME=(\{.*?\});', HS.home_source(root))
    if not m:
        raise TableError('홈에서 시군구 이름표(SGG_QNAME)를 찾지 못했다')
    return json.loads(m.group(1))


def _zones(data):
    return {z['z']: z for z in (data['sido'].get('zones') or [])}


def city(data, name):
    """도시(시군구) 입주물량 묶음 — tools/data/city_moveins.json. 없으면 None."""
    return ((data.get('cities') or {}).get('cities') or {}).get(name)


def _city_years(f, year=None):
    by = {y: n for y, n in (f.get('by_year') or {}).items()}
    if year:
        if str(year) not in by:
            raise TableError('그 도시의 %s년 입주 예정이 자료에 없다(%s)' % (year, _upto(f)))
        return {str(year): by[str(year)]}
    return by


SRC_CITY = '한국부동산원 입주예정물량정보 · 청약홈 분양정보'


def _upto(f):
    """'2028년 6월 입주분까지 공개된 목록(2026-10-27 조사)' — 목록이 어디까지 담고 있고 언제 받았는지.

    예전에는 '2028-06 목록 기준' 이라고만 적었는데, 읽는 사람이 '2028년 6월에 만든 목록' 으로 오해한다
    (총괄 제보 2026-10-27). 그 달은 **목록에 실린 마지막 입주월**이고, 목록을 받은 날은 따로 있다.
    """
    ym = f.get('occ_max') or ''
    out = ('%s년 %d월 입주분까지 공개된 목록' % (ym[:4], int(ym[5:7]))) if len(ym) >= 7 else '공개된 목록'
    return out + ('(%s 조사)' % f['as_of'] if f.get('as_of') else '')


def _city_note(f, tail=None):
    return ' · '.join([SRC_CITY, _upto(f)] + ([tail] if tail else []))


def _eun(word):
    """'은/는' 을 붙인다 — 받침이 있으면 '은'(의정부는·춘천은). 표 각주가 도시 이름을 말할 때 쓴다."""
    c = word[-1]
    return word + ('은' if '가' <= c <= '힣' and (ord(c) - 0xAC00) % 28 else '는')


def city_moveins(data, f, name, year=None):
    """도시 입주물량. 연도를 주면 그 해를 쪼개 보여 주고(구별, 구가 없는 시는 분기별), 없으면 연도별."""
    if year:
        gu = (f.get('by_year_gu') or {}).get(str(year)) or {}
        # 구가 갈리지 않는 시(의정부·김포처럼 자치구가 없는 곳)는 '(구 없음)' 한 줄 + 합계가 되어 읽을 것이
        # 없다(2026-10-27 라이브에서 그랬다). 그 해를 분기로 쪼개 같은 자리에 쓸모 있는 표를 낸다.
        if len([g for g in gu if g]) < 2:
            q = {}
            for r in (f.get('rows') or []):
                if r['ym'].startswith(str(year)):
                    q['%sQ%d' % (year, (int(r['ym'][5:7]) - 1) // 3 + 1)] = \
                        q.get('%sQ%d' % (year, (int(r['ym'][5:7]) - 1) // 3 + 1), 0) + r['n']
            if not q:
                raise TableError('%s년 %s 입주 예정이 자료에 없다' % (year, name))
            rows = [[k, num(v)] for k, v in sorted(q.items())]
            if len(rows) > 1:                     # 한 분기뿐이면 합계가 같은 수를 두 번 적는 것이 된다
                rows.append(['합계', num(sum(q.values()))])
            return (['분기', '세대'], rows,
                    _city_note(f, '%s 자치구가 없어 분기로 나눴다' % _eun(name)))
        rows = [[g or '구 미상', num(v)] for g, v in sorted(gu.items(), key=lambda x: -x[1])]
        tot = sum(gu.values())
        rows.append(['합계', num(tot)])
        return (['지역', '세대'], rows, _city_note(f))
    by = _city_years(f)
    rows = [[y, num(v), '%d%%' % int(round(v / float(f['need']) * 100))] for y, v in sorted(by.items())]
    return (['연도', '세대', '적정 대비'], rows,
            '한국부동산원 입주예정물량정보 · 청약홈 분양정보 · 적정 입주량 %s세대(%s, 인구 %s년 %d월)'
            % (num(f['need']), f.get('need_note') or '', f['pop_prd'][:4], int(f['pop_prd'][4:])))


def city_share(data, f, year):
    """그 해 입주 물량 ÷ 한 해 적정 입주량(%)."""
    by = _city_years(f, year)
    v = list(by.values())[0]
    return '%d%%' % int(round(v / float(f['need']) * 100))


def city_ratio(data, f, year, base):
    """두 해 물량의 비 — `{{v:ratio:의정부:2028:2027}}` → '19%'(2028년이 2027년의 몇 %인가).

    왜 여는가. '그다음 해에는 5분의 1로 줄어든다'·'두 배로 늘어난다' 같은 문장을 쓰려면 두 해를 견주어야
    하는데, 그러면 글이 두 숫자를 손으로 적게 된다(콘텐츠-도시 세션 요청 2026-10-27). 비만 자리표로
    받으면 글은 '5분의 1' 이라는 말만 쓰고 수치는 데이터가 채운다.
    """
    # 자료에 없는 해는 _city_years 가 먼저 막는다(어느 해가 없는지 말해 준다). 여기서 볼 것은 0 뿐이다.
    a = list(_city_years(f, year).values())[0]
    b = list(_city_years(f, base).values())[0]
    if not b:
        raise TableError('%s년 물량이 0이라 견줄 수 없다' % base)
    return '%d%%' % int(round(a / float(b) * 100))


def city_need(data, f):
    """한 해 적정 입주량. 원고가 '6,030세대' 를 손으로 적지 않게 연다 — 인구가 바뀌면 그 값도 바뀐다."""
    return num(f['need']) + '세대'


def city_pop(data, f):
    """인구와 그 기준월 — 적정 입주량을 설명하는 자리에 쓴다."""
    return '%s명(%s년 %d월 주민등록)' % (num(f['pop']), f['pop_prd'][:4], int(f['pop_prd'][4:]))


def city_peak(data, f, year=None):
    """입주가 가장 몰리는 달과 그 세대 수. 연도를 주면 그 해 안에서 고른다.

    단지 이름은 담지 않는다 — 데이터의 이름은 '…외가로주택정비사업' 처럼 길어 문장에 그대로 넣기 어렵다.
    글이 단지를 말할 때는 원고가 쓰고 숫자만 이 자리표로 받는다.
    """
    agg = {}
    for r in (f.get('rows') or []):
        if year and not r['ym'].startswith(str(year)):
            continue
        agg[r['ym']] = agg.get(r['ym'], 0) + r['n']
    if not agg:
        raise TableError('입주 예정 목록이 비었다%s' % (' (%s년)' % year if year else ''))
    ym, n = max(sorted(agg.items()), key=lambda x: x[1])
    return '%s년 %d월 %s세대' % (ym[:4], int(ym[5:7]), num(n))


def city_complexes(data, f, year=None):
    """단지 목록 표(입주월·단지·구·세대). 연도를 주면 그 해만."""
    rows = [r for r in (f.get('rows') or []) if not year or r['ym'].startswith(str(year))]
    if not rows:
        raise TableError('단지 목록이 비었다(%s년)' % year if year else '단지 목록이 비었다')
    if len({(r.get('gu') or '') for r in rows}) < 2:   # 구가 갈리지 않으면 그 열은 전부 같은 값이다
        return (['입주 예정', '단지', '세대'],
                [[r['ym'], r['name'], num(r['n'])] for r in rows], _city_note(f))
    body = [[r['ym'], r['name'], r.get('gu') or '구 미상', num(r['n'])] for r in rows]
    return (['입주 예정', '단지', '구', '세대'], body, _city_note(f))


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
    """도시·구 이름 → [(코드, 이름표)]. 받는 꼴은 셋이다(이름표는 홈 시군구 지도와 같은 SGG_QNAME).

      '고양 덕양구'  정확한 이름표 → 그 구 하나
      '덕양구'       구 이름만 → 그 구 하나(여러 시에 같은 구 이름이 있으면 모두)
      '고양'         시 이름 → 그 시의 구를 모두(이름표 순서)

    ⚠️ 도시 한 줄 값을 만들지 않는다. 주간 시세는 지수 변동률이라 구를 평균 내면 원천이 발표하지 않은 수가
       된다(저장소 데이터 원칙). 도시 글에는 구별 표를 싣는다.
    """
    q = data.get('sgg_names') or {}
    exact = [(c, n) for c, n in q.items() if n == name]
    if exact:
        return exact
    tail = [(c, n) for c, n in q.items() if n.rsplit(' ', 1)[-1] == name]   # '분당구' → '성남 분당구'
    if tail:
        return sorted(tail, key=lambda x: x[1])
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


def _weekly_series(data, name, kind='ma'):
    """[(조사일, 값)] — 시도면 ADV.weekly, 시군구면 sgg 계열. 연속 주수·구별 표가 같은 원천을 쓴다."""
    import sido_zones as SZ
    if name in SZ.ORDER or SZ.key_of(name) in SZ.ORDER:
        key = region_key(data, name)
        W = data['weekly']
        regs = W.get('regions') or []
        i = regs.index(key)
        return [(r.get('p'), (r.get(kind) or [None] * len(regs))[i]) for r in (W.get('rows') or [])]
    got = sgg_codes(data, name)
    if len(got) != 1:
        raise TableError('연속 주수는 한 지역만 받는다 — %r 는 %d곳이다(구 이름까지 적을 것)' % (name, len(got)))
    S = data.get('sgg') or {}
    codes = S.get('codes') or []
    c = got[0][0]
    if c not in codes:
        raise TableError('주간 시세에 %r 자료가 없다' % got[0][1])
    i = codes.index(c)
    return [(r.get('p'), (r.get(kind) or [None] * len(codes))[i]) for r in (S.get('rows') or [])]


def streak(data, name, what='매매'):
    """'42주 연속 상승(10월 19일 조사)' — 최신 주와 같은 방향이 이어진 주 수.

    ⚠️ 방향은 **표시값**(소수 둘째 자리 반올림) 기준이다. 화면의 '+0.00%' 를 상승으로 세면 글자와 뜻이 어긋난다.
       0.00 이 나오는 주에서 연속이 끊긴다 — 원천이 '보합'이라고 말한 주다.
    """
    kinds = {'매매': 'ma', '전세': 'je'}
    if what not in kinds:
        raise TableError('streak 은 매매 또는 전세다: %r' % what)
    import make_weekly_page as MW
    ser = [(p, v) for p, v in _weekly_series(data, name, kinds[what]) if v is not None]
    if not ser:
        raise TableError('%s %s 주간 값이 없다' % (name, what))
    last_p, last_v = ser[-1]
    sign = (1 if MW.pv2r(last_v) > 0 else (-1 if MW.pv2r(last_v) < 0 else 0))
    if sign == 0:
        return '보합(%s 조사)' % _kdate(last_p)
    n = 0
    for _, v in reversed(ser):
        r = MW.pv2r(v)
        if (r > 0) != (sign > 0) or r == 0:
            break
        n += 1
    return '%d주 연속 %s(%s 조사)' % (n, '상승' if sign > 0 else '하락', _kdate(last_p))


def _kdate(iso):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', str(iso) or '')
    return '%d월 %d일' % (int(m.group(2)), int(m.group(3))) if m else str(iso)


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
        f = city(data, args[0])
        if f:
            return city_moveins(data, f, args[0], args[1] if len(args) > 1 else None)
        return moveins(data, region_key(data, args[0]), args[1] if len(args) > 1 else None)
    if kind in ('share', 'need', 'pop', 'peak', 'ratio'):
        raise TableError('%s 는 표가 아니라 값이다 — {{v:%s:…}} 로 쓸 것' % (kind, kind))
    if kind == 'complexes':
        if not 1 <= len(args) <= 2:
            raise TableError('complexes 자리표는 도시[:연도] 꼴이다')
        f = city(data, args[0])
        if not f:
            raise TableError('%r 의 단지 목록이 없다 — 도시 자료(tools/data/city_moveins.json)에 없는 도시다' % args[0])
        return city_complexes(data, f, args[1] if len(args) > 1 else None)
    if kind == 'supply':
        if len(args) != 1:
            raise TableError('supply 자리표는 지역 하나를 받는다')
        return supply(data, region_key(data, args[0]))
    if kind == 'stats':
        if len(args) != 2:
            raise TableError('stats 자리표는 계열:지역 꼴이다')
        return stats(data, args[0], region_key(data, args[1]))
    if kind == 'streak':
        if not 1 <= len(args) <= 2:
            raise TableError('streak 자리표는 지역[:매매|전세] 꼴이다')
        raise TableError('streak 은 표가 아니라 값이다 — {{v:streak:...}} 로 쓸 것')
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
    raise TableError('모르는 자리표 종류다: %r (쓸 수 있는 것: moveins, supply, stats, weekly, complexes · 값 전용: v:share, v:streak, v:need, v:pop, v:peak, v:ratio)' % kind)


def value(data, kind, args):
    """문장 안에 넣는 한 값. 표의 '대표 값'과 같은 수를 쓴다."""
    if kind == 'streak':
        if not 1 <= len(args) <= 2:
            raise TableError('streak 자리표는 지역[:매매|전세] 꼴이다')
        return streak(data, args[0], args[1] if len(args) > 1 else '매매')
    if kind in ('need', 'pop', 'peak', 'ratio'):
        want = {'need': (1, 1), 'pop': (1, 1), 'peak': (1, 2), 'ratio': (3, 3)}[kind]
        if not want[0] <= len(args) <= want[1]:
            raise TableError('%s 자리표는 도시%s 꼴이다' % (kind, {'peak': '[:연도]', 'ratio': ':연도:견줄 연도'}.get(kind, '')))
        f = city(data, args[0])
        if not f:
            raise TableError('%r 는 도시 자료(tools/data/city_moveins.json)에 없다' % args[0])
        if kind == 'need':
            return city_need(data, f)
        if kind == 'pop':
            return city_pop(data, f)
        if kind == 'ratio':
            return city_ratio(data, f, args[1], args[2])
        return city_peak(data, f, args[1] if len(args) > 1 else None)
    if kind == 'share':
        if len(args) != 2:
            raise TableError('share 자리표는 도시:연도 꼴이다')
        f = city(data, args[0])
        if not f:
            raise TableError('%r 의 적정 대비 비율을 낼 자료가 없다(도시 자료에 없는 도시다)' % args[0])
        return city_share(data, f, args[1])
    if kind == 'moveins' and args and city(data, args[0]):
        f = city(data, args[0])
        by = _city_years(f, args[1]) if len(args) > 1 else _city_years(f)
        return num(sum(by.values())) + '세대'
    if kind == 'weekly' and args and sgg_codes(data, args[0]):
        import sido_zones as SZ
        if not (args[0] in SZ.ORDER or SZ.key_of(args[0]) in SZ.ORDER):
            # 시군구 한 곳이면 최신 주 매매 변동률. 구가 여럿이면 어느 구인지 알 수 없다.
            got = sgg_codes(data, args[0])
            if len(got) != 1:
                raise TableError('%r 는 %d곳이다 — 구 이름까지 적을 것(예: 고양 덕양구)' % (args[0], len(got)))
            ser = [v for _, v in _weekly_series(data, args[0], 'ma') if v is not None]
            if not ser:
                raise TableError('주간 시세 %s 에 값이 없다' % args[0])
            return pct(ser[-1]) + '%'
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


# ── 자리표 치환의 한 입구 ───────────────────────────────────────────────────
# 왜 여기에 모았나. 요약과 FAQ 는 페이지에만 실리지 않는다 — OG·JSON-LD·섹션 목록·feed.xml·llms.txt 가
# 같은 글을 가져다 쓴다. 생성기마다 따로 치환하면 어느 한 곳이 빠진 채 '{{v:...}}' 가 그대로 발행된다.
# 2026-10-27 첫 19편에서 실제로 그랬다(페이지 7곳·feed 19건·llms 9건). 그래서 원고를 읽는 생성기는
# 모두 fill_meta 를 통과시키고, 본문을 글자로 내보내는 쪽은 fill_markdown 을 쓴다.
PH = re.compile(r'\{\{(table|v):([^}]+)\}\}')


def _args(m):
    parts = [p.strip() for p in m.group(2).split(':')]
    if not parts or not parts[0]:
        raise TableError('자리표가 비었다: %s' % m.group(0))
    return parts[0], parts[1:]


def fill_inline(text, data):
    """한 줄 글(제목·요약·FAQ)의 자리표를 채운다. 표 자리표는 한 줄에 들어갈 수 없으므로 거부한다."""
    def sub(m):
        kind, args = _args(m)
        if m.group(1) == 'table':
            raise TableError('표 자리표는 본문에만 쓴다(제목·요약·FAQ 는 한 줄이다): %s' % m.group(0))
        return value(data, kind, args)
    return PH.sub(sub, text or '')


def fill_meta(meta, data):
    """프런트매터의 글에 자리표를 채워 **새 dict** 로 돌려준다. 실패하면 TableError 를 올린다."""
    out = dict(meta)
    for k in ('title', 'summary'):
        if isinstance(out.get(k), str):
            out[k] = fill_inline(out[k], data)
    faq = out.get('faq')
    if isinstance(faq, list):
        out['faq'] = [dict((kk, fill_inline(vv, data) if isinstance(vv, str) else vv)
                           for kk, vv in f.items()) if isinstance(f, dict) else f for f in faq]
    return out


def md_table(head, rows, note=None):
    """표를 마크다운 파이프 표로. llms-full.txt 처럼 HTML 이 아닌 글자로 내보내는 곳이 쓴다."""
    out = ['| %s |' % ' | '.join(head), '| %s |' % ' | '.join('---' for _ in head)]
    out += ['| %s |' % ' | '.join(r) for r in rows]
    if note:
        out.append('')
        out.append(note)
    return '\n'.join(out)


def fill_markdown(body, data):
    """본문 마크다운의 자리표를 채운다 — 값은 그대로, 표는 마크다운 표로 바꾼다."""
    def sub(m):
        kind, args = _args(m)
        if m.group(1) == 'v':
            return value(data, kind, args)
        return '\n' + md_table(*table(data, kind, args)) + '\n'
    return PH.sub(sub, body or '')
