# -*- coding: utf-8 -*-
"""data.js에서 홈 화면이 실제로 쓰는 조각만 뽑아 data-core.js를 만든다.

배경: data.js 397KB를 모든 방문자가 매번 내려받는데, 홈이 실제로 쓰는 건
그중 일부다. 통계 탭을 열지 않는 방문자에게 주간 155주·기본통계 11계열을
보낼 이유가 없다.

전략은 '쪼개서 나눠 보내기'가 아니라 '핵심만 먼저 보내기'다.
  - data-core.js : 홈이 쓰는 것만. index.html이 즉시 로드.
  - data.js      : 그대로 둔다. 통계 탭을 열 때 fetch로 받아 core에 병합.
data.js를 손대지 않으므로 생활권 41장과 /cycle/은 아무 영향이 없다.

실행: python tools/split_data.py   (update_adv_data.py --update 뒤에)
"""
import io, json, os, re, sys

# 배치는 chcp 65001을 하지만 다른 경로로 불릴 수도 있다. 콘솔 인코딩 때문에
# 산출물을 다 만들고도 print에서 죽으면 배치가 exit 20으로 실패한다.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data.js')
OUT = os.path.join(ROOT, 'data-core.js')
REST = os.path.join(ROOT, 'data-rest.json')
TREND = os.path.join(ROOT, 'data-trend.json')
SGG = os.path.join(ROOT, 'data-sgg.json')
SIZE = os.path.join(ROOT, 'data-size.json')

# '규모별 동향'은 지표4×규모6 피벗이라 STATS 14계열 중 혼자 186KB(rest의 39%)다.
# 기본통계 세그먼트에서 그걸 실제로 누른 사람만 필요하므로 별도 지연 파일로 뺀다
# (2026-08-01: rest 408KB → 250KB). index.html ensureSizeStats()가 받아 채운다.
LAZY_STATS = ['규모별']
# 파일 → 그 파일이 싣는 계열. 감시(check_freshness)가 이걸로 조회 목록을 만든다 —
# 지연 파일이 늘면 여기만 늘리면 감시가 자동으로 따라온다(파일명 하드코딩 금지).
LAZY_FILES = {os.path.basename(SIZE): list(LAZY_STATS)}

# 시군구·서울구 전체 시계열은 '구를 실제로 고른 사람'만 필요하다. trend에 통째로
# 실으면 통계 탭을 여는 모든 방문자가 4배 큰 파일을 받는다(실측 91→418KB gzip).
# 그래서 최근 TREND_SGG_KEEP개만 trend에 남기고 전체는 data-sgg.json으로 뺀다.
TREND_SGG_KEEP = 12
NL = chr(10)

# 홈이 쓰는 STATS 계열.
# 준공·착공은 2026-08-06부터 core에 싣는다 — 공급·가격 통합표가 이 둘을 직접 그리고,
# 그게 홈의 주 컨텐츠다(합쳐 65KB). 대신 같은 날 permits의 HUB 파생분(done/sched/demol,
# 83KB)이 통째로 빠져 core는 오히려 가벼워졌다.
# ⚠️ 주택멸실·아파트멸실은 2026-08-07에 뺐다. 이중구현 미러가 사라지면서
# 브라우저 소비자가 0이 됐는데(index.html의 STATS['주택멸실']·['아파트멸실'] 참조
# 각 0건), 옛 주석이 '러닝재고가 직접 읽는다'고 적혀 있어 아무도 못 지웠다.
# 멸실은 이제 빌드 시점에 sido_zones가 data.js에서 읽어 점수에 녹인다.
# 기본통계 화면은 data-rest.json 사본을 쓰므로 손실 없다(동일 바이트 확인).
# ⚠️ 전세가율은 2026-09-27 에 뺐다(홈 마케팅 검수 B11·MOB-8 data-core 다이어트). 홈에서 읽는 곳은 통계 탭 버블밴드
# (renderBubbleSec, home-stats.js) 하나뿐인데, 그 화면은 어차피 data-rest.json(전세가율 원천 그대로 포함)을 받은 뒤에
# 그린다. /jeonse-ratio/ 생성기(make_indicator_pages.load)도 같은 날부터 data-rest.json 에서 읽는다.
CORE_STATS = ['준공', '착공']

# 홈이 통째로 쓰는 ADV 키.
# ⚠️ occupancy·permits·bubble 은 2026-09-27 에 뺐다(B11 다이어트, 합쳐 약 15KB·gzip 약 7KB). 셋 다 통계 탭(투자지표·
# 버블밴드)만 읽고, 통계 화면은 data-trend.json(ADV 전체, permits 는 KEEP_PERMITS 만)을 받은 뒤에 돈다(home-app.js 의
# 분할 파일 대기열이 trend 를 함께 기다린다). 홈 첫 화면(지도·표·주간)은 sido·holidays·weekly·monthly·준공·착공만 읽는다.
CORE_ADV = ['sido', 'holidays']

# 통계 탭 파일(data-trend.json)이 싣는 ADV 키 — 이것도 **허용목록**이다. 예전엔 ADV 전체를 실어, 2026-08-06 시도 재편으로
# 폐기된 생활권 지표 aged30(홈·통계 탭 어디서도 읽지 않는다)이 통계 탭을 여는 모든 방문자에게 계속 실려 나갔다(전수 리뷰
# 묶음 T 제보). 통계 탭(home-stats.js)이 읽는 키만 둔다 — 새 지표를 통계 탭에 올리면 여기에 적는다.
TREND_ADV = ('sido', 'holidays', 'weekly', 'monthly', 'occupancy', 'permits', 'bubble')
# 코어(data-core.js)에만 싣는 최상위 키 — 통계 탭 파일에 없으므로 loadFullData 가 바꾸지 않는다(ADV.blog, B5 · ADV.fresh).
CORE_ONLY_ADV = ('blog', 'fresh')   # fresh: 모드 단추 N 배지(2026-10-08)

# ⚠️ 거부목록이 아니라 **허용목록**이다. 예전엔 뺄 키를 나열했더니 새로 생긴 키가
# 아무도 안 막아준 채 홈 페이로드로 새어 나갔다 — permits.city(150KB)로 data-core가
# 131KB -> 311KB가 됐고(2026-08-05), 생활권 시대 잔재 meas·fwd_far는 그 뒤로도
# 계속 실려 나갔다(2026-08-07 감사). 홈이 실제로 읽는 건 ref 하나(index.html의
# `ADV.permits.ref[region]`)이고 나머지는 표기용이다. 여기 없는 키는 자동으로 빠진다.
# permits 가 data-core 에서 빠진 뒤(2026-09-27 B11)에도 통계 탭 파일(data-trend.json)이 같은 규칙으로 싣는다.
KEEP_PERMITS = ('regions', 'ref', 'rows', 'note')

# 홈 통합표가 그리는 구간·지역. 적정물량 기준표와 같은 시작점(2017)이다.
TABLE_FROM = '2017.01'
TABLE_STATS = ('준공', '착공')
# 주간 '반영 대기' 판정 유예(일). 감시(check_freshness)와 같은 상수를 홈이 읽게 ADV.weekly.grace 로 싣는다
# (홈 마케팅 검수 A2, 2026-09-27). 홈 JS 가 9 를 따로 적으면 감시를 옮길 때 화면과 감시가 갈린다.
# weekly_release 는 표준 라이브러리만 쓰므로 sido_zones 처럼 없을 때를 대비하지 않는다 — 없으면 배치가 멈춰야 한다.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weekly_release import GRACE_WEEKLY  # noqa: E402

# 판정 모델(sido_zones)은 반드시 있어야 하는 의존이다 — weekly_release 처럼 없으면 배치가 멈춘다(전수 리뷰 #14). 예전엔
# 못 불러오면 지역 19곳을 손으로 옮긴 대체 목록으로 조용히 넘어가, 모델이 바뀐 뒤(2026-09-10 광주·전남 통합 같은)에는 홈
# 준공·착공 지역을 옛 목록으로 거르고 화면 문구(refresh_texts)도 건너뛴 코어를 실을 수 있었다. 표준 라이브러리만 쓴다.
import kst as _kst  # noqa: E402
import sido_zones as _SZ  # noqa: E402
TABLE_REGIONS = set(_SZ.ORDER)
# 이번 주 결론 한 줄(ADV.weekly.head, 홈 마케팅 검수 B1·IA-4). /weekly/ 제목과 같은 함수(make_weekly_page.conclusion)
# 에서 만들어 싣고 홈은 읽기만 한다. 생성기를 못 불러오면 head 없이 쪼갠다 — 홈은 head 가 없으면 띠를 데이터 없는
# 기본 문구로 두고 주간 h2 는 고정 질문으로 둔다(옛 캐시와 같은 동작). 게이트 시험이 head 가 실리는지 본다.
try:
    import make_weekly_page as _MW
except Exception as _e:               # noqa: BLE001 — 결론 한 줄 때문에 데이터 스플릿을 멈추지 않는다
    _MW = None
    print('⚠️ split_data: make_weekly_page 를 못 불러와 ADV.weekly.head 를 싣지 않는다 — %s' % _e, file=sys.stderr)


# 최신 주간 해설 글(ADV.blog, 홈 마케팅 검수 B5). 배치 fetch 잡이 이 스크립트 앞에서 blog_feed 로 RSS 를 읽어 둔 것을
# /weekly/ 와 같은 규칙(blog_feed.pick)으로 골라 싣는다. 홈 주간 구역이 읽기만 한다. 최상위 키라 통계 탭을 열어도
# (loadFullData 는 trend 에 있는 키만 바꾼다) 사라지지 않는다. 못 불러오거나 고를 글이 없으면 싣지 않는다 — 칸이 빠지기만.
try:
    import blog_feed as _BF
    import weekly_release as _WR
except Exception as _e:               # noqa: BLE001 — 블로그 칸 때문에 데이터 스플릿을 멈추지 않는다
    _BF = None
    print('⚠️ split_data: blog_feed 를 못 불러와 ADV.blog 를 싣지 않는다 — %s' % _e, file=sys.stderr)


def _blog(w):
    rows = (w or {}).get('rows') or []
    if _BF is None or not rows:
        return None
    try:
        return _BF.pick(_BF.read(), _WR.status(rows[-1]['p'])['pub'])
    except Exception as e:            # noqa: BLE001
        print('⚠️ split_data: 블로그 칸을 만들지 못했다 — %s' % e, file=sys.stderr)
        return None


def _weekly_head(w):
    if _MW is None:
        return None
    try:
        return _MW.head_payload(w)
    except Exception as e:            # noqa: BLE001
        print('⚠️ split_data: 주간 결론 한 줄을 만들지 못했다 — %s' % e, file=sys.stderr)
        return None


# 공유 내용(ADV.weekly.share, B8)은 /weekly/ 공유 버튼과 같은 함수(make_weekly_page.share_payload)에서 온다. 결론 한 줄
# (head)처럼 못 만들면 빼고 쪼갠다 — 홈은 없으면 공유 버튼 없이 그린다.
# 시도 방향 표지(ADV.weekly.moves)와 최근 4주(recent)는 더 싣지 않는다 — 홈 주간 구역의 시도 칸을 걷고 시군구 지도로 바꿔
# (2026-10-02 대표 요청) 읽는 곳이 없다. 표지는 /weekly/·블로그 초안이 weekly_moves 를 직접 불러 쓴다.


def _weekly_share(w):
    try:
        return (_MW and _MW.share_payload(w)) or None
    except Exception as e:            # noqa: BLE001
        print('⚠️ split_data: 주간 공유 내용을 만들지 못했다 — %s' % e, file=sys.stderr)
        return None


def _r4(a):
    """변동률 소수 4자리 — 원천(R-ONE 지수 전월비 환산)이 소수 넷째 자리까지라 값은 그대로이고 부동소수 꼬리만 자른다.

    예전엔 소수 2자리(round(v, 2) — 이진수 위의 half-even)로 실었는데, 홈이 그 값을 다시 pv2r(half-up)로 찍어 /monthly/
    (원값을 half-up)와 표시값이 갈렸다(전수리뷰 B1 — 2026-01 전국 0.345 → 홈 +0.34, /monthly/ +0.35). 화면 자리로
    반올림하는 일은 화면(pv2r)이 한 번만 한다.
    """
    return None if a is None else [None if v is None else round(v, 4) for v in a]


def price_agg(mo):
    """홈 공급·가격 표의 분기·연 가격 변동 합 — {'q': {'2025Q2': {'ma': [...], 'je': [...], 'wo': [...]}}, 'y': {...}}.

    정본 sido_zones.price_periods(시도 리포트 분기 표와 같은 함수)가 **원값**으로 한 번 더한다(전수 리뷰 #110 — 홈이 소수
    둘째 자리로 반올림한 월값을 더해 표시값이 리포트와 칸의 5%에서 갈렸다). 달이 덜 찬 기간은 None(#15, 대표 결정 ⑧).
    배열 순서는 mo['regions']. 값은 **화면이 찍는 소수 첫째 자리**(half-up, 리포트 pct1 과 같은 반올림)로 싣는다 — 합을
    다른 자리로 반올림해 실으면 x.x5 경계에서 홈 Math.round 와 리포트가 다시 갈린다. 홈 tbAgg 는 이 값을 그대로 읽는다.
    """
    regs = mo.get('regions') or []
    out = {}
    for per in ('q', 'y'):
        got = _SZ.price_periods(mo, per)
        out[per] = {k: {f: [None if (got[k].get(r) is None or got[k][r][n] is None)
                            else _SZ.half_up(got[k][r][n] * 10) / 10.0 for r in regs]
                        for n, f in enumerate(_SZ.PRICE_FIELDS)}
                    for k in sorted(got) if k[:4] >= TABLE_FROM[:4]}
    return out


def occ_band():
    """입주물량 표 문턱(퍼센트) — 홈 통계 탭 occCls 가 읽는다. 정본 sido_zones.OCC_LO_PCT·OCC_HI_PCT(대표 결정 ③)."""
    return {'lo': _SZ.OCC_LO_PCT, 'hi': _SZ.OCC_HI_PCT}


def bake_lights(sido, stats):
    """홈 판정 카드의 해마다 입주 신호등(2026-10-05 대표 요청)을 싣는다 — 칸마다 yl(1·2·3년 차 [{n, p, k}])·ya(읽어 줄 글),
    판정 묶음에 ylg(범례 [[색 키, 구간, 이름]]). 값·문턱·이름은 모두 sido_zones(year_lights·lights_aria·light_legend) — 홈이
    문턱(70·130%)을 다시 적지 않는다. 판정(ADV.sido)과 STATS 시점이 같아야 하는 건 make_sido_pages 가 지킨다."""
    L = sido.get('L') or ''
    if not re.match(r'^\d{4}Q[1-4]$', L):
        return
    Lq = _SZ.qidx(int(L[:4]), int(L[-1]))
    for z in sido['zones']:
        yl = _SZ.year_lights(stats, z['z'], Lq, sido['H'])
        if yl:
            z['yl'] = yl
            z['ya'] = _SZ.lights_aria([{'n': y['n'], 'pct': y['p']} for y in yl])
    sido['ylg'] = [list(x) for x in _SZ.light_legend()]


# 홈 모드 단추의 '새 데이터' N 배지(2026-10-08 대표 요청, B안). 모드마다 최신 시점(공급 = 판정 분기 ADV.sido.L, 주간 = 마지막
# 조사일, 월간 = 마지막 달)과 그 시점이 **이 사이트에 처음 실린 날**(KST)을 ADV.fresh 로 싣는다. 홈은 그날부터 모드별 FRESH_DAYS 일
# 동안(그날 포함) 배지를 달고, 방문자가 그 단추를 누르면 그 기기에서는 지운다(home-app.js freshModes·seeFresh).
# '처음 실린 날'은 따로 파일을 두지 않고 직전 data-core.js 의 ADV.fresh 에서 이어 받는다 — 시점이 같으면 옛 날을 두고, 바뀌면
# 오늘. 직전 값이 없는 첫 회차(기능을 처음 배포한 날)는 날을 비워 배지를 달지 않는다(셋이 한꺼번에 '새것'이 되지 않게).
# 표시 기간은 들어오는 주기에 맞춘다(2026-10-08 대표 결정): 주간은 목요일 발표 → 일요일까지(주말 방문 포함), 월간은 한 주,
# 분기 공급은 두 주. 누르면 그 기기에서 바로 지우므로 길게 두어도 자주 오는 방문자에게 짐이 되지 않는다.
FRESH_DAYS = {'supply': 14, 'weekly': 4, 'monthly': 7}
# 처음 실린 날과 다음 날(2일)은 누른 기기에도 다시 단다 — 그 뒤부터 누르면 지운다(같은 날 대표 결정).
FRESH_FORCE = 2
FRESH_MODES = tuple(FRESH_DAYS)


def fresh_periods(core_adv):
    """모드별 최신 시점 — 홈 지도 세 모드가 그리는 값의 시점과 같다."""
    w = (core_adv.get('weekly') or {}).get('rows') or []
    m = (core_adv.get('monthly') or {}).get('rows') or []
    return {'supply': (core_adv.get('sido') or {}).get('L'),
            'weekly': w[-1]['p'] if w else None,
            'monthly': m[-1]['p'] if m else None}


def old_fresh(path):
    """직전 data-core.js 의 ADV.fresh. 파일이 없으면(첫 회차) None, 있는데 못 읽으면 **멈춘다** — 조용히 None 으로 넘기면
    배지가 매 회차 첫 회차처럼 비워져 영영 안 뜨는데 아무것도 빨개지지 않는다(2026-10-08 리뷰). 읽기는 홈 요약과 같은
    함수(make_home_summary.load_core — 모양이 바뀌면 SystemExit)."""
    if not os.path.exists(path):
        return None
    from make_home_summary import load_core   # 순환 없음(make_home_summary 는 split_data 를 들이지 않는다) — 지연 import 는 가져오기 비용
    f = load_core(path).get('fresh')
    return f if isinstance(f, dict) else None


def fresh_marks(periods, old, today):
    """{'days': {모드: 일수}, 'force': 일수, 모드: {'p': 시점, 'd': 처음 실린 날 또는 ''}} — 시점이 없는 모드는 뺀다."""
    out = {'days': dict(FRESH_DAYS), 'force': FRESH_FORCE}
    for m in FRESH_MODES:
        p = periods.get(m)
        if not p:
            continue
        prev = (old or {}).get(m) if isinstance((old or {}).get(m), dict) else None
        if prev is None:
            d = ''                                  # 첫 회차·새 모드 — 언제 실렸는지 모르니 새것이라 하지 않는다
        elif prev.get('p') == p:
            d = prev.get('d') or ''
        elif p > str(prev.get('p') or ''):
            d = today                               # 앞으로 간 시점만 새것이다(같은 모드 안에서는 글자 비교가 시간 순)
        else:
            d = ''                                  # 뒤로 간 시점(기준변경 보류·원천 철회)은 새것이 아니다 — 돌아오면 또 세지 않는다
        out[m] = {'p': p, 'd': d}
    return out


def main():
    src = io.open(SRC, encoding='utf-8').read()
    adv = json.loads(re.search(
        r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', src, re.S).group(1))
    stats = json.loads(re.search(r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', src, re.S).group(1))

    core_adv = {k: adv[k] for k in CORE_ADV if k in adv}

    def strip_units(a):
        """빌드 전용 키 제거. 단지 목록·시군 시계열은 지역 정적 페이지
        (make_zone_pages가 data.js를 직접 읽어 렌더) 전용이라 브라우저 페이로드가
        실어 나를 이유가 없다. 홈은 ADV.sido의 점수와 STATS 준공·착공만 쓴다."""
        a = dict(a)
        p = a.get('permits')
        if p:
            p = dict(p)
            p = {k: v for k, v in p.items() if k in KEEP_PERMITS}
            a['permits'] = p
        return a

    core_adv = strip_units(core_adv)
    # 판정 화면 문구(카드 ctxt·cnum·cdir·cpct, ⓘ 식 ftxt)는 지금의 정본 함수로 다시 굽는다(홈에서 뺀 옛 필드는 걷어 낸다). data.js 의 ADV.sido 는
    # 다음 배치가 점수를 다시 쓸 때까지 옛 문구를 싣는다 — 문구 함수를 고친 날 홈이 옛말을 하지 않게(B2·C4).
    # 숫자(dtot·ratio·grade)는 건드리지 않는다. adv['sido'] 와 같은 객체라 trend 쪽에도 같이 실린다.
    if (core_adv.get('sido') or {}).get('zones'):
        _SZ.refresh_texts(core_adv['sido'])
        bake_lights(core_adv['sido'], stats)

    # 히어로 배경 지도는 마지막 한 주만 쓴다(renderHeroMap: rows[rows.length-1]).
    # 전체 sgg는 59.7KB인데 그중 필요한 건 4.8KB뿐이다.
    w = adv.get('weekly') or {}
    sgg = w.get('sgg') or {}
    # 시도 rows와 sgg는 **따로 판정한다**. 예전에는 둘 다
    # `if sgg.get('rows')` 안에 있어서, 시군구 계열만 비어도 홈 배너까지
    # 통째로 사라졌다 — display:none이라 에러도 테스트 실패도 없이 조용히
    # 빈다(2026-09-01 리뷰). 배너(시도)와 히어로 지도(시군구)는 서로 다른
    # 입력이라, 한쪽이 비어도 다른 쪽은 그려야 한다.
    wk = {'regions': w.get('regions', []), 'grace': GRACE_WEEKLY}
    head = _weekly_head(w)
    share = _weekly_share(w)
    if w.get('rows'):
        wk['rows'] = w['rows'][-1:]   # 홈 띠·주간 구역 머리(발표 상태·결론)는 마지막 행만 읽는다
        if head:
            wk['head'] = head
        if share:
            wk['share'] = share
    if sgg.get('rows'):
        wk['sgg'] = {'codes': sgg.get('codes', []), 'rows': sgg['rows'][-1:]}
    if wk.get('rows') or wk.get('sgg'):
        core_adv['weekly'] = wk
    blog = _blog(w)
    if blog:
        core_adv['blog'] = blog

    # 홈 통합표가 쓰는 가격 변동률 — 매매·전세·월세만, 시도 20곳만.
    # 전체 monthly는 753.9KB(대부분 seoul 76.8 + sgg 617.1)라 통째로는 못 싣는다.
    # 통계 탭이 열리면 loadFullData가 전체로 덮어쓴다(상위 키 통째 교체라 안전).
    mo = adv.get('monthly') or {}
    if mo.get('rows'):
        core_adv['monthly'] = {
            'regions': mo.get('regions', []),
            'rows': [{'p': r['p'],
                      'ma': _r4(r.get('ma')), 'je': _r4(r.get('je')), 'wo': _r4(r.get('wo'))}
                     # ⚠️ monthly는 '2017-01', STATS는 '2017.01'로 구분자가 다르다.
                     # 그대로 비교하면 '-'(0x2D) < '.'(0x2E)라 2017년이 통째로 잘린다.
                     for r in mo['rows'] if r['p'].replace('-', '.') >= TABLE_FROM],
            'note': mo.get('note', ''),
            'agg': price_agg(mo),      # 분기·연 합(원값으로 한 번, #110) — 홈 tbAgg 가 읽는다
        }

    core_adv['fresh'] = fresh_marks(fresh_periods(core_adv), old_fresh(OUT), _kst.today_iso())

    core_stats = {k: stats[k] for k in CORE_STATS if k in stats}
    missing = [k for k in CORE_STATS if k not in stats]
    assert not missing, '홈이 쓰는 STATS 계열이 없다: %s' % missing
    # 준공·착공은 표가 그리는 구간(TABLE_FROM~)만, 표에 나오는 지역만 싣는다.
    # 전 구간 22개 지역이면 65KB인데 이렇게 자르면 절반 아래다. 점수(ADV.sido)는
    # 이미 계산돼 있으므로 홈이 옛 구간을 다시 읽을 일이 없다.
    for k in TABLE_STATS:
        s = core_stats.get(k)
        if not s:
            continue
        keep = [i for i, d in enumerate(s['dates']) if d >= TABLE_FROM]
        core_stats[k] = {
            'unit': s.get('unit'), 'source': s.get('source'),
            'dates': [s['dates'][i] for i in keep],
            'series': {r: [v[i] for i in keep] for r, v in s['series'].items() if r in TABLE_REGIONS},
        }

    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    body = (
        '/* 자동 생성 — tools/split_data.py. 직접 고치지 말 것.\n'
        '   홈 화면이 쓰는 조각만 담는다. 통계 탭을 열면 loadFullData()가\n'
        '   data-rest.json을 받아 이 전역에 Object.assign으로 채운다. */\n'
        'const ADV=%s;\n'
        'const STATS=%s;\n'
        'window.__DATA_CORE__=true;\n' % (dump(core_adv), dump(core_stats)))
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(body)

    # 나머지는 JSON으로 따로 낸다. 런타임에 data.js를 정규식으로 파싱하는 방식은
    # 선언 형태가 조금만 바뀌어도 조용히 깨지므로 쓰지 않는다.
    # 통계 탭에서 먼저 보이는 건 그래프(주간·월간)다. 기본통계 11계열(rest)도
    # 탭 진입 시 이어서 받지만, 그래프가 rest 크기를 기다리지 않도록 둘로 쪼갠다.
    trend_adv = strip_units({k: v for k, v in adv.items() if k in TREND_ADV})
    dropped = sorted(set(adv) - set(TREND_ADV))
    if dropped:
        print('  trend 에서 뺀 ADV 키(허용목록 밖): %s' % ', '.join(dropped))
    sgg_full = {}
    for k in ('weekly', 'monthly'):
        w = trend_adv.get(k)
        if not w:
            continue
        w = dict(w)
        keep = {}
        for part in ('sgg', 'seoul'):
            sec = w.get(part)
            if sec and sec.get('rows') and len(sec['rows']) > TREND_SGG_KEEP:
                keep[part] = sec                      # 전체는 지연 로드 파일로
                w[part] = dict(sec, rows=sec['rows'][-TREND_SGG_KEEP:])
        if keep:
            sgg_full[k] = keep
        if k == 'weekly':
            # 통계 탭을 열면 loadFullData 가 ADV.weekly 를 이 파일 것으로 통째로 바꾼다 — 여기에도 실어야
            # 그 뒤 rel-week·주간 격자가 유예를 잃지 않는다.
            w['grace'] = GRACE_WEEKLY
            if head:
                w['head'] = head   # 같은 이유 — 통계 탭을 연 뒤에도 홈 띠·주간 h2 가 결론을 잃지 않는다
            if share:
                w['share'] = share   # 같은 이유 — 주간 격자 공유 버튼(B8)
        if k == 'monthly':
            w['agg'] = price_agg(adv.get('monthly') or {})   # 통계 탭을 연 뒤(loadFullData 가 ADV.monthly 를 바꾼 뒤)에도 같은 합
        trend_adv[k] = w
    if trend_adv.get('occupancy'):
        trend_adv['occupancy'] = dict(trend_adv['occupancy'], band=occ_band())   # 통계 탭 입주물량 표 문턱(③)
    io.open(TREND, 'w', encoding='utf-8', newline=NL).write(
        dump({'ADV': trend_adv}))
    io.open(SGG, 'w', encoding='utf-8', newline=NL).write(dump({'ADV': sgg_full}))
    # rest에 ADV를 또 담으면 trend와 중복돼 총 전송량이 오히려 는다(399→629KB).
    # rest는 기본통계 계열만 담는다 — ADV는 trend가 이미 실어 보냈다.
    lazy_stats = {k: stats[k] for k in LAZY_STATS if k in stats}
    rest_stats = {k: v for k, v in stats.items() if k not in lazy_stats}
    io.open(REST, 'w', encoding='utf-8', newline='\n').write(dump({'STATS': rest_stats}))
    io.open(SIZE, 'w', encoding='utf-8', newline=NL).write(dump({'STATS': lazy_stats}))

    full = len(src)
    rest = os.path.getsize(REST)
    print('data.js        %7.1f KB  (그대로 유지 — 다른 소비자 보호)' % (full / 1024))
    print('data-core.js   %7.1f KB  (홈 즉시 로드, %.0f%% 절감)'
          % (len(body) / 1024, 100 * (1 - len(body) / full)))
    print('data-trend.json%7.1f KB  (그래프 — 통계 탭 진입 시)' % (os.path.getsize(TREND) / 1024))
    print('data-rest.json %7.1f KB  (기본통계 — 세그먼트 누를 때)' % (rest / 1024))
    print('data-sgg.json  %7.1f KB  (시군구 시계열 — 구를 고를 때만)' % (os.path.getsize(SGG) / 1024))
    print('  core ADV   :', ', '.join(core_adv))
    print('  core STATS :', ', '.join(core_stats))


if __name__ == '__main__':
    main()
