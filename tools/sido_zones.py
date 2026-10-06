# -*- coding: utf-8 -*-
"""시도(집계 3종 포함, 목록은 ORDER)의 공급 지표 — 국토부 준공·착공만으로 계산한다.

왜 이 모듈이 따로 있나: 2026-08-06 이전에는 미래 공급을 건축HUB **준공예정**으로
셌는데, 그건 인허가만 받고 삽을 안 뜬 계획이었다(2028년 입주예정 363,701세대 중
착공 0건 — 데이터 누락이 아니라 사실. 준공된 단지의 착공일 보유율은 연도별로 전부
100%다). 착공 기반 추정 대비 1.29~1.68배 과대였고, 그게 "서울이 균형으로 나온다"의
원인이었다. 설계 근거는 docs/superpowers/specs/2026-08-06-sido-supply-table-design.md.

핵심: **착공과 준공은 같은 통계표(국토부 주택건설실적)의 두 열**이라 정의가 일치하고
오차가 같은 방향으로 걸린다. 착공을 3년 뒤로 밀면 준공과 맞는다(전환율 0.958,
변동계수 0.138 — k=2는 0.208, k=4는 0.239로 더 흔들린다).

⚠️ KOSIS는 값 0을 '-'로 준다. 시리즈의 None은 결측이 아니라 **진짜 0**이다
(시도 합계 ÷ 전국이 모든 연도에서 정확히 1.00). 대구 2023년 하반기 착공 0은 사실
— 미분양이 쌓여 착공이 멈춘 것이다. 건너뛰지 말고 0으로 다뤄야 한다.
"""
# ── 적정물량(분기, 호) ──────────────────────────────────────────────────────
# 적정물량 기준표(시도별 분기 입주물량)의 상수. 국토부 스케일이라는 근거:
# 합계 연 380,000호 vs 국토부 아파트 준공 실적 평균(2011~2025) 연 325,816호 = 0.86배.
# 15년 평균이 적정의 86%면 만성적 소폭 부족 — 기준표의 전제와 맞는다.
#
# ⚠️ 상수로 **고정**한다. 서울·경기·인천은 기준표에 없어(수도권 50,000 하나뿐)
# 세대수 비중 37.3/51.0/11.7%로 나눈 값이고, 세종·제주도 표에 없어 13개 지역의
# 세대당 원단위(0.00388호/세대·분기)로 추정했다. 매 갱신마다 세대수로 다시 계산하면
# 잣대가 해마다 흔들린다 — 적정물량은 기준선이지 데이터가 아니다.
REF_Q = {
    '전국': 95000, '수도권': 50000, '지방': 45000,
    '서울': 18700, '경기': 25500, '인천': 5800,          # 수도권 50,000 분할(합 정확히 50,000)
    '부산': 6000, '울산': 2000, '경남': 6000, '대구': 5000, '경북': 5000,
    '전남광주': 5700, '대전': 2200, '충남': 3500, '충북': 2700,   # 광주 2,700 + 전남 3,000
    '전북': 2500, '강원': 2600,
    '세종': 600, '제주': 1200,                            # 추정치(백 단위 반올림)
}
# 기준표에 없어 추정한 값. 지역별 배지로는 **표시하지 않는다** — "세대수 비중으로
# 나눴다" 같은 내부 방법론이라 일반 독자가 못 읽는다(2026-08-08 사용자,
# make_sido_pages.build_page 참조). 공시는 홈 '산출 방법'의 적정물량 항목이
# 문장으로 맡는다. payload의 'est'는 sido_zones의 콘솔 표(`*추정`)가 쓴다.
# ⚠️ 여기 주석은 "화면에 표시할 것"이라고 적혀 있었으나 그런 화면은 없었다 —
# 지침으로 읽고 배지를 다시 만들지 말 것(2026-08-15 리뷰).
# ⚠️ 2026-09-10 광주·전남 통합. 국토부가 인허가·착공·준공을 2026.07분부터
# '전남광주' 하나로만 발표하기 시작해(시군구 계층도 없어 되살릴 수 없다) 판정
# 단위를 합쳤다. 적정물량은 두 지역 기준표 값의 합이다(2,700+3,000).
# 과거 시계열은 tools/merge_regions.py가 병합했다 — 물량은 합, 지수는
# 원천이 쓰는 가중치(광주 0.599)로 가중평균.
EST = {'서울', '경기', '인천', '세종', '제주'}
AGG = ('전국', '수도권', '지방')                          # 집계 3종(시도 순위에서 제외)
ORDER = list(REF_Q)                                       # 표의 열 순서

# 시도 목록을 **보여줄 때** 쓰는 고정 순서(2026-09-13 대표 결정).
# 부족 순이 아니라 사람들이 관심을 두는 순서다 — 부족한 곳이 지방·제주일 수 있는데 그곳이 곧
# 관심 지역은 아니다. 집계 3 → 수도권 → 광역시·세종 → 도. 대표가 바꾸면 여기만 고친다.
# ⚠️ ORDER 와 헷갈리지 말 것. ORDER 는 기준표·발표 원천의 순서라 /monthly/ 처럼 정부 표와
#    대조하는 화면이 그대로 쓴다. 순위를 말하는 곳(블로그 순위표)은 zone_order() 를 쓴다.
#    목록 표시(허브·'다른 지역' 격자·홈 표 모드)만 이것을 쓴다 — calc() 가 zones 를 이 순서로 낸다.
DISPLAY_ORDER = [
    '전국', '수도권', '지방',
    '서울', '경기', '인천',
    '부산', '대구', '대전', '세종', '울산', '전남광주',
    '충남', '충북', '경남', '경북', '전북', '강원', '제주',
]
# 손으로 적은 목록은 모델이 바뀌어도 따라오지 않는다(2026-09-10 광주·전남 통합). 어긋나면
# 여기서 바로 죽는다 — 조용히 한 지역이 목록에서 빠지는 것보다 낫다.
if sorted(DISPLAY_ORDER) != sorted(ORDER) or len(set(DISPLAY_ORDER)) != len(DISPLAY_ORDER):
    raise SystemExit('DISPLAY_ORDER 가 모델 지역과 다르다: %s'
                     % sorted(set(DISPLAY_ORDER) ^ set(ORDER)))

REGION = {z: ('수도권' if z in ('서울', '경기', '인천') else '지방') for z in REF_Q}
REGION.update({'전국': '전국', '수도권': '수도권', '지방': '지방'})

# ── 산식 상수 ───────────────────────────────────────────────────────────────
LEAD_Q = 12          # 착공 → 준공 12분기(3년). 실측 최적값.
CONV = 0.958         # 착공 대비 준공 전환율. 전국 연간 12개월 완비 연도 평균.
# CONV 를 잰 구간: 착공 CONV_START_FROM 년부터 CONV_YEARS 개 완비 연도(착공 y ↔ 준공 y+3, 연도별 비의 평균).
# 착공 계열이 2011.01 부터라 2011~2022 착공 12쌍이다. 문장('착공한 것의 96%가 … 2011년 이후 실측')과 시험
# (test_conv_text_follows_model 이 data-rest 로 다시 잰다)이 이 두 값을 읽는다(전수 리뷰 #111).
CONV_START_FROM = 2011
CONV_YEARS = 12
BACKLOG_WINDOW = 16  # 과거 재고 창 4년 (2026-08-02 사용자 결정, 앵커·상한 없음)
# ⚠️ 마지막 컷은 -0.5가 아니라 **0.0**이다(2026-08-02 변경). 향후 16분기 물가차감
# 실질 상승률이 비율 0에서 손익분기라서였다(0 아래 실질 -0.3~-1.2% · 0~0.5 +0.13% ·
# 0.5~1.0 +2.58% · 1.0+ +10.22%).
# ⚠️ 위 수치는 **옛 생활권 44곳 모델**로 잰 것이다. 2026-09-13 지금의 시도 모델로 다시
# 재면(tools/study_grade_bands.py, 16개 시도 × 2014Q3~2022Q2 512개) 0 미만 +0.25%,
# 0~0.25 -6.36%, 0.25~0.5 +1.54%, 0.5~1.0 +5.78%, 1.0+ +18.58%로 **0.0 손익분기가
# 재현되지 않는다**(갈림은 0.25 부근). 그래도 컷은 옮기지 않았다 — 옮길 방향을 받칠
# 근거가 없고 0.25~0.5에 든 지역이 없어 새 칸도 판정을 바꾸지 않는다(대표 결정,
# docs/2026-09-13-판정기준-결정.md). 위 목록의 수치를 컷의 현재 근거로 인용하지 말 것.
GRADE_CUTS = (1.5, 1.0, 0.5, 0.0)
GRADE_KEYS = ('g4', 'g3', 'g2', 'g1', 'g0')
# 창 너머 인허가 경고(pwarn)의 문턱. 1.0이 아니라 0.95인 게 핵심이다 —
# 수도권이 99.98%(실측)라 1.0으로 자르면 매달 켜졌다 꺼졌다 하고, 깜빡이는
# 경고는 읽는 사람이 그냥 무시한다. 리터럴로 흩어 두면 "정리" 커밋에 조용히
# 1.0으로 되돌아가므로 상수로 잠근다(test_pwarn_threshold_avoids_knife_edge).
PWARN_CUT = 0.95


def pbr_pct(pbr):
    """3년 너머 참고 신호(pbr)를 화면 퍼센트 정수로 — 리포트 셋째 줄 '필요량의 N%'가 찍는 값."""
    return half_up(100 * pbr)      # 입주 ÷ 적정 퍼센트는 half_up 하나로(/moveins/ pct_shown·occ_level 과 같은 반올림, 2026-10-06 리뷰)


def pbr_thin(pbr):
    """신호가 문턱(PWARN_CUT) 아래인가 — **화면에 찍는 퍼센트 정수**로 견준다(전수리뷰 B3). 원값으로 견주면 0.9496 은
    '95%' 인데 '못 미칩니다'가 붙고 0.9504 는 '95%' 인데 안 붙어, 같은 숫자에 다른 말이 달렸다. 리포트 강조(split_text 의
    thin)와 홈·허브 경고(calc 의 pwarn)가 이 함수 하나를 쓴다."""
    return pbr_pct(pbr) < int(round(PWARN_CUT * 100))


# 라벨 사다리를 한 칸 올렸다(2026-08-15 PM 결정, docs/2026-08-15-등급컷-결정.md).
# ⚠️ GRADE_CUTS는 건드리지 않았다 — 컷은 가격 실측(밴드별 이후 16분기 실질
# 상승률)에 묶여 있고, 0.55 같은 값을 정당화할 근거가 "집계 3곳을 올리고 싶어서"
# 뿐이면 그건 근거가 아니다. 결함은 컷이 아니라 이름이었다: 0.60은 3년 필요량의
# 60%가 순부족인데 그 구간을 '다소 부족(심하진 않습니다)'이라 부르고 있었다.
GRADE_LABS = {'g4': '심각한 부족', 'g3': '매우 부족', 'g2': '부족',
              'g1': '균형', 'g0': '공급 여유'}


def need_mult(ratio, H=None):
    """순부족비 → '1년 적정물량의 몇 배'(소수 한 자리, 크기만). 모자란(남는) 집 ÷ 그 지역 1년 적정물량 = |비율| × 연수(H/4).

    2026-10-05 대표 결정(안 A′): 부족률 퍼센트는 100% 를 넘고(서울 +139%) 음수가 되며(인천 −19%), 같은 칸의 해마다 입주 신호등
    ('적정의 73%' — 클수록 좋음)과 뜻이 반대라 읽기 어려웠다. 기준을 '1년 적정물량' 하나로 맞춰 쌓인 부족은 몇 배, 그해 입주는
    몇 %로 단위를 가른다. '몇 년 치'로 쓰지 않은 까닭: '앞으로 3년'·'1년 차' 옆에서 '4.2년 치'가 기간으로 읽혔다.
    ⚠️ 반올림이 등급 컷(컷 × 연수 = 1.5·3·4.5배)을 넘지 않게 한다(전수 리뷰 #9 — 옛 ratio_pct 의 가드를 옮겼다). 컷 바로 아래 비율이
    '1.5배'로 찍히면 '1.5배에 못 미쳐 균형'과 부딪친다. 컷 아래 비율은 컷 − 0.1배에서 멈춘다.
    """
    H = LEAD_Q if H is None else H
    Y = H / 4.0
    m = half_up(abs(ratio) * Y * 10) / 10.0
    for c in GRADE_CUTS:
        cm = half_up(c * Y * 10) / 10.0
        if c > 0 and 0 < ratio < c and m >= cm:
            m = round(cm - 0.1, 1)
    return m


MULT_MIN = 0.1     # 이보다 작으면 방향을 말하지 않는다('거의 같음') — 소수 한 자리로 0.0배가 찍히는 자리


def mult_str(m):
    """배수 숫자 → 화면 글('4.2배'). 소수 한 자리를 늘 적는다(3.0배 — 컷 '3배'와 같은 값임을 범례가 말한다).
    0.1배에 못 미치면 '0.1배 미만'(2026-10-06 리뷰 — 충북 281세대가 '부족(필요량과 거의 같음)'으로 한 줄에 두 말을 했다)."""
    return '%.1f배' % m if m >= MULT_MIN else '%.1f배 미만' % MULT_MIN


def cut_mult(c, H=None):
    """등급 컷(비율) → 배수 글('1.5배'·'3배'·'4.5배'). 판정 규칙 문장·막대 범례·FAQ 가 이 함수 하나로 컷을 말한다."""
    H = LEAD_Q if H is None else H
    return '%g배' % (half_up(c * H / 4.0 * 10) / 10.0)


def ratio_text(ratio, H=None, full=False, inow=None, W=None):
    """순부족비를 사람 말로 옮긴다. 판정 배지 옆에 붙는다(2026-09-13 PM 요청 ①).

    발단: 경기 리포트가 판정은 '균형'인데 바로 아래 '누적 순부족 50,579세대'라
    반대로 읽혔다. 등급은 '앞으로 H분기 필요량 대비 누적 순부족의 비율'로 자르는데
    화면에는 그 비율이 없고 절대 세대수만 있었다. 비율을 같이 보여주면 왜 균형인지가
    한 줄로 설명된다.

    full=True(시도 리포트 판정 문장·블로그 지역 편)는 판정의 정의대로 **지난 W분기 재고까지 셈한** 문장이다
    (홈 마케팅 검수 B2·C4·TRUST-2, 2026-09-27). 예전 여유 문장 '앞으로 3년 필요량보다 19% 더 들어옵니다'는
    앞으로 3년만의 주장이었는데, 인천은 착공 기반 입주 추정(66,579)이 필요량(69,600)보다 적고 여유는 지난 4년
    남은 재고(16,258)에서 온다 — 바로 옆의 식(formula_text)과 숫자로 부딪쳤다. 부족 문장의 '누적 순부족'도
    09-13 고객 점검이 없앤 말이다. inow(지난 창 재고, 음수 = 모자람)를 주면 formula_text 와 같은 갈래
    ('덜 지은 몫'/'남은 재고')로 쓰고, 없으면 방향 없는 '재고까지 셈하면'으로 쓴다.
    짧은 문구(full=False, 허브 목록의 rtxt)는 비율만 말한다.

    ⚠️ 여기서만 만든다. 홈은 JS라 같은 문구를 거기서 또 만들면 이중 구현이 되고,
    이 프로젝트는 2026-08-06에 그런 미러를 전부 걷어냈다. calc()가 결과 행에
    'rtxt'로 구워 싣고 화면은 읽기만 한다.
    """
    # 기본값은 부를 때 모델 상수에서 읽는다(정의 때 굳히면 창·리드 상수를 바꾼 모듈에서 옛 연수가 남는다, 전수 리뷰 #19).
    H = LEAD_Q if H is None else H
    W = BACKLOG_WINDOW if W is None else W
    yrs = '%g년' % (H / 4.0)
    # 2026-10-05 대표 결정(안 A′): 쌓인 부족·여유를 '1년 적정물량의 N배'로 적는다(need_mult). 부족률 퍼센트는 100% 를 넘고 음수가
    # 되며 해마다 입주 신호등의 퍼센트와 뜻이 반대라 읽기 어려웠다. 주어(모자란 집·남는 집)와 기준(1년 적정물량)을 함께 밝힌다.
    m = need_mult(ratio, H)
    sign = 1 if ratio > 0 else (-1 if ratio < 0 else 0)   # 방향은 비율 부호 그대로(작으면 '0.1배 미만' — mult_str)
    if not full:
        if sign > 0:
            return '1년 적정물량의 %s 부족' % mult_str(m)     # 허브 목록·홈 요약 대체 문구 — 연수는 말하지 않는다
        if sign < 0:
            return '1년 적정물량의 %s 여유' % mult_str(m)
        return '필요량과 거의 같음'
    past = '지난 %g년' % (W / 4.0)
    if sign > 0:
        lead = ('%s 재고까지 셈하면' % past if inow is None else
                '%s 덜 지은 몫까지 더하면' % past if inow < 0 else
                '%s 남은 재고를 빼고도' % past)
        return '%s 앞으로 %s 모자란 집은 1년 적정물량의 %s입니다' % (lead, yrs, mult_str(m))
    if sign < 0:
        lead = ('%s 재고까지 셈하면' % past if inow is None else
                '%s 덜 지은 몫을 채우고도' % past if inow < 0 else
                '%s 남은 재고까지 더하면' % past)
        return '%s 앞으로 %s 남는 집이 1년 적정물량의 %s입니다' % (lead, yrs, mult_str(m))
    return '%s 재고까지 셈하면 앞으로 %s 필요량과 거의 같습니다' % (past, yrs)


def qidx(y, q):
    """(연, 분기) → 정수 인덱스. 분기 산술을 한 축에서 하려고 쓴다."""
    return y * 4 + q - 1


def qparts(i):
    return i // 4, i % 4 + 1


def qkey(i):
    y, q = qparts(i)
    return '%dQ%d' % (y, q)


# 제목 연도는 '전망하는 해'다(2026-09-27 대표 결정). 10월부터는 다음 해를 쓴다 — 내년 전망 검색 수요는 가을부터 커진다
# (09-27 블로그 검색 실측 '2026 부동산 전망' 10,428건 대 '2027' 459건). 근거·실험은 make_naver_post 지역 편 제목 주석.
OUTLOOK_NEXT_FROM_MONTH = 10


def outlook_year(p):
    """주간 조사일 'YYYY-MM-DD' → 제목에 쓸 '전망하는 해' 문자열('2026'). 읽을 수 없으면 ''(제목에서 연도를 뺀다).

    사이트 시도 리포트 제목(make_sido_pages.page_title)과 블로그 지역 편 제목(make_naver_post.draft_zone)이 **이 함수
    하나**로 연도를 쓴다(요청서 B4, 2026-09-27 대표 결정). 날짜는 두 곳 모두 ADV.weekly 최신 행의 조사일이다.
    """
    try:
        y, m = int(p[:4]), int(p[5:7])
    except (TypeError, ValueError):
        return ''
    return str(y + 1 if m >= OUTLOOK_NEXT_FROM_MONTH else y)


def latest_survey(adv):
    """ADV.weekly 최신 행의 조사일('YYYY-MM-DD'), 없으면 '' — outlook_year 의 입력(사이트·블로그 같은 원천)."""
    rows = ((adv or {}).get('weekly') or {}).get('rows') or []
    return (rows[-1] or {}).get('p', '') if rows else ''


def qlabel(i, per='q'):
    """기간 표기 — 월 '17.1' / 분기 '17Q4' / 연 '2017' (2026-08-06 확정)."""
    y, q = qparts(i)
    if per == 'y':
        return str(y)
    return '%02dQ%d' % (y % 100, q)


def mlabel(y, m):
    return '%02d.%d' % (y % 100, m)


def _series(stats, key, region):
    """월별 시리즈 → {분기 인덱스: (합, 월 수)}.

    None은 0으로 센다(위 ⚠️ 참조). 월 수를 같이 돌려주는 건 마지막 분기가
    덜 찼는지 판별하기 위해서다 — 덜 찬 분기를 실적으로 쓰면 그 지역만
    공급이 낮게 잡혀 부족이 부풀려진다.
    """
    s = (stats.get(key) or {})
    ser = (s.get('series') or {}).get(region)
    if ser is None:
        return {}
    out = {}
    for dt, v in zip(s.get('dates') or [], ser):
        y, m = int(dt[:4]), int(dt[5:7])
        i = qidx(y, (m - 1) // 3 + 1)
        a, n = out.get(i, (0, 0))
        out[i] = (a + (v or 0), n + 1)
    return out


def quarterly(stats, key, region, full_only=True):
    """{분기 인덱스: 값}. full_only면 3개월이 다 찬 분기만."""
    return {i: a for i, (a, n) in _series(stats, key, region).items()
            if not full_only or n == 3}


def has_any(stats, key, region):
    """그 지역 시리즈에 None 아닌 값이 하나라도 있나.

    ⚠️ quarterly()가 비어 있지 않다는 것만으로는 부족하다. 전 기간이 None이어도
    _series는 (0, 3)을 만들어 분기 키가 생기므로 `if not dn` 가드를 통과하고,
    그 지역은 준공 0 = 완전 공급절벽으로 계산돼 **순위 1위로 올라온다**.
    KOSIS 지역명 개편(강원특별자치도·전북특별자치도 전례)으로 merge_basic의
    지역 필터에 걸려 그 지역만 계속 None으로 append되면 실제로 도달한다
    (2026-08-07 감사). 진짜 0(대구 2023년 하반기 착공)과는 구분해야 한다 —
    그건 값이 0이 아니라 KOSIS가 '-'로 준 것이고 여기서는 None이 아니다.
    """
    ser = ((stats.get(key) or {}).get('series') or {}).get(region)
    return any(v is not None for v in (ser or []))


def last_full_quarter(stats, key='준공', region='전국'):
    q = quarterly(stats, key, region)
    return max(q) if q else None


def demol_q(stats, region):
    """{연도: 분기당 아파트 멸실}과 폴백값. 원자료가 시도 연간이라 4로 나눈다.

    ⚠️ '주택멸실'(계)을 쓰면 안 된다 — 단독이 절반이라 아파트 재고에서 과대 차감된다.
    ⚠️ 예전엔 **최신 1개 연도**를 재고창 16분기 전체에 썼다. 창(2022Q3~2026Q2) 중
    10분기는 실측이 있는데도 버린 것이라, 광주처럼 2024년이 0이면 2022년 2,796호가
    통째로 사라지고 경남은 1.0 컷 바로 옆에서 등급이 뒤집혔다(2026-08-07 감사).
    연도가 맞으면 그 해 값을, 없으면 가장 가까운 해 값을 쓴다.
    """
    s = stats.get('아파트멸실') or {}
    ser = (s.get('series') or {}).get(region) or []
    dates = s.get('dates') or []
    by = {}
    for d, v in zip(dates, ser):
        if v is not None:
            by[int(str(d)[:4])] = v / 4.0
    return by


def demol_of(by, year):
    """그 해 멸실. 없으면 가장 가까운 연도(미래는 최신, 과거는 최초)로 채운다."""
    if not by:
        return 0.0
    if year in by:
        return by[year]
    return by[min(by, key=lambda y: (abs(y - year), y))]


def unsold_latest(stats, region):
    """가장 최근 미분양 호수와 그 시점. (호수, 'YYYY.MM') — 없으면 (None, None).

    미분양은 **순위 산식에 넣지 않는다**(결과값이라 재고에서 차감하면 부호가
    반대고 이중계상된다 — 기존 원칙). 여기서 뽑는 건 화면에 같이 놓을 맥락이다:
    판정이 '부족'인데 미분양이 쌓인 곳은 지을 데가 없어서가 아니라 안 팔려서
    안 짓는 것일 수 있다.
    """
    s = stats.get('미분양') or {}
    ser = (s.get('series') or {}).get(region) or []
    dates = s.get('dates') or []
    for i in range(len(ser) - 1, -1, -1):
        if ser[i] is not None:
            return ser[i], (dates[i] if i < len(dates) else None)
    return None, None


def permit_trail12(stats, region):
    """최근 12개월 인허가 합. (호, 'YYYY.MM') — 계산 불가면 (None, None).

    인허가는 **순위 산식에 넣지 않는다**(삽을 안 뜬 계획이 섞여 같은 해 착공보다
    약 1.15배 많고 해마다 0.54~1.20 사이로 흔들린다 — 2012~2025 전국 실측, 누계를
    월별로 풀어서 잰 값). '1.29~1.68배'라고 적혀 있던 건 건축HUB 준공예정의 수치였다
    (2026-09-13 정정). 여기서 뽑는 건 화면에 같이 놓을
    **창 너머 신호**다: 판정은 앞으로 3년(착공이 닿는 데까지)을 보는데, 인허가는
    착공 전 단계의 물량이라 판정 창(착공 기반 3년) 밖의 공급을 미리 보여준다. 등급은 '부족'인데
    시장에서는 '역대급 부족'이라 말하는 온도차가 정확히 이 창 차이였다(2026-08-11
    사용자 — 등급은 실측 앵커라 두고, 부족한 시야를 이 줄이 나른다).

    ⚠️ 인허가 계열은 '호 (연내 누계)' — 1월마다 리셋된다. 최근 12개월은 permit_monthly(누계를 월별로 푼 값, 연초 null =
    진짜 0)의 최근 12개월 합이다. 예전엔 여기서 누계 셋(올해 최신·작년 12월·작년 같은 달)을 따로 읽으며 연초 null 을
    결측으로 봐서, 전년 같은 달이 null 이면 값이 사라지고(대구·충북·세종 2025.01) 최신 달이 null 이면 그 지역만 전년
    1~12월로 물러나 기간이 섞였다(대구 2024.01 → '2023.12', 전수 리뷰 #11). 같은 null 을 한 파일의 두 함수가 다르게
    쟀던 것이다 — 이제 permit_monthly 하나만 잰다.
    기준 달은 계열 전체에서 값이 있는 마지막 달(지역마다 따로 정하지 않는다). 그 달부터 12개월 중 하나라도
    permit_monthly 에 없으면 None 을 돌려주고 줄을 접는다(반쪽 계산으로 오탐을 내지 않는다).
    """
    s = stats.get('인허가') or {}
    dates = s.get('dates') or []
    series = (s.get('series') or {}).values()
    ref = None
    for i in range(len(dates) - 1, -1, -1):
        if any(i < len(v) and v[i] is not None for v in series):
            ref = i
            break
    if ref is None or region not in (s.get('series') or {}):
        return None, None
    mon = permit_monthly(stats, region)
    ym = dates[ref]
    t = int(ym[:4]) * 12 + int(ym[5:7]) - 1
    keys = ['%d.%02d' % ((t - k) // 12, (t - k) % 12 + 1) for k in range(12)]
    if any(k not in mon for k in keys):
        return None, None
    return sum(mon[k] for k in keys), ym


# 기간 정본(2026-09-15 점검후속 ③). 페이지마다 인허가→입주가 "3~4년"·"4~6년"·"3년"으로
# 갈리고 착공→준공이 "27개월"·"28개월"·"3년 반"으로 갈렸다. 전국 12개월 이동합끼리의
# 시차상관(tools/rebuild_cycle_analysis.py의 link45 분석, 인허가는 누계를 풀어서)으로 정했다:
#   인허가 → 착공  시차 0개월에서 가장 강하다(r 0.76) — 전국 집계로는 같은 시기에 움직인다
#   착공 → 준공   2018년 전 28개월 → 2018년 이후 37개월(전체 32개월)
# ⚠️ 인허가 → 입주 기간은 정본에 두지 않는다(2026-09-15 PM 반대 의견 수용). 전국 집계의
# 시차 0은 두 총량이 같은 국면에 함께 움직인다는 뜻이지 사업 단위 시차가 아니고, 착공÷인허가
# 0.87로 허가 뒤 착공하지 않는 물량도 늘 있다. 한때 '약 3년'으로 박았다가 되돌렸다 — 측정하지
# 않은 사업 단위 시차를 단정하는 것이었고, 리포트의 '앞으로 3년'(착공 기반)·'3년 너머'(인허가)
# 줄 구분과도 부딪쳤다. 인허가는 기간 대신 PERMIT_NATURE의 성격으로 쓴다.
# 2018년 이후 인허가→준공 73개월은 표본이 30개뿐이라 쓰지 않았다.
# 재산정 결과가 바뀌면 test_period_constants_follow_the_analysis가 잡는다.
START_DONE_MONTHS_OLD = 28
START_DONE_MONTHS_NEW = 37
# 인허가의 성격(어미 앞까지). 쓰는 쪽이 '아'·'습니다'·'다'를 붙인다.
PERMIT_NATURE = '착공과 같은 흐름으로 움직이지만 허가 뒤 착공하지 않는 물량이 섞여 있고 입주까지의 시차가 일정하지 않'


def quarter_text(key):
    """'2026Q2' → '2026년 2분기'. 판정 기준 시점을 사람 말로."""
    import re
    m = re.match(r'(\d{4})Q([1-4])$', key or '')
    return ('%s년 %s분기' % (m.group(1), m.group(2))) if m else (key or '')


def half_up(v):
    """JS Math.round와 같은 half-up. 화면 정수는 이걸로 만든다(make_sido_pages.rnd와 같다)."""
    import math
    return int(math.floor(float(v) + 0.5))


def month_back(dates, i, k):
    """dates[i] 에서 정확히 k달 앞 시점의 인덱스. 그 달 칸이 계열에 없으면 None.

    ⚠️ '전월'·'1년 전'을 인덱스 차(i-1, i-12)로 잡지 않는다. 배치는 불완비한 달을 보류한다
       (update_adv_data._drop_incomplete — 미분양 2026.07). 그 달이 끝내 안 채워진 채 다음 달이
       들어오면 dates 에 그 달 칸이 없어 i-1 이 두 달 전이 되고, '전월 대비'에 두 달 치 변화가
       실린다(2026-09-26 데이터 감사 #17). 라벨('2026.07', '2026.07 p)')로 달을 세어 찾는다.
    """
    import re

    def ym(s):
        m = re.match(r'^(\d{4})[.\-/]\s*(\d{1,2})', str(s).strip())
        return int(m.group(1)) * 12 + int(m.group(2)) - 1 if m else None
    if not 0 <= i < len(dates):
        return None
    t = ym(dates[i])
    if t is None:
        return None
    for j in range(i - 1, -1, -1):
        if ym(dates[j]) == t - k:
            return j
    return None


def card_parts(dtot, ratio, H=None):
    """홈·허브 카드의 세 조각: ('686,396세대', '부족', '1년 적정물량의 1.8배')(2026-10-05 안 A′ — 아래 퍼센트 이력은 옛 표기다).

    2026-10-05 대표 요청: '…60%만큼'은 말이 중간에 끊겨 보였고 무엇의 60%인지가 흐렸다. 이 60%는 앞의 세대수(부족분)가
    3년 필요량의 몇 %인지다 — 이어 붙일 때 세대수 뒤 괄호로 묶어(card_text) '686,396세대 부족(3년 필요량의 60%)'로 쓴다.

    예전엔 '−686,396세대 · 3년 필요량의 60% 부족'이라 배지('부족') 옆에 음수 부호가
    또 붙어 이중 부정으로 읽혔다(2026-09-15 점검후속 ⑤). 부호 대신 부족·여유를 말로 쓰고
    비율은 크기만 적는다 — 그 결정의 목적(부호 이중 부정 제거)은 그대로다.
    2026-09-27(홈 마케팅 검수 B2·HERO-4)에는 '필요량의 60%만 지어진다'로 읽히지 않게 비율 뒤에 '만큼'을 붙였는데,
    10-05 에 그 자리를 세대수 뒤 괄호로 바꿨다(위). 비율 조각만 떼어 쓰는 자리(홈 카드 셋째 줄)는 바로 위 세대수 줄에 붙는다.
    조각으로 나눈 것은 모바일 카드가 세대수만 한 줄에 싣기 때문이다(MOB-7 — '전국 [부족]' / '686,396세대').
    화면은 읽기만 한다. 순부족이 0이면 세대수·방향이 비고 비율 조각만 남는다.
    """
    # 기본값은 부를 때 모델 상수에서 읽는다(정의 때 굳히면 창·리드 상수를 바꾼 모듈에서 옛 연수가 남는다, 전수 리뷰 #19).
    H = LEAD_Q if H is None else H
    yrs = '%g년' % (H / 4.0)
    m = need_mult(ratio, H)         # 판정 문구와 같은 배수(컷을 넘지 않는 반올림)
    # 2026-10-05 안 A′: 괄호 안은 앞 세대수가 1년 적정물량의 몇 배인지다('686,396세대 부족(1년 적정물량의 1.8배)')
    share = '1년 적정물량의 %s' % mult_str(m) if ratio else ratio_text(ratio, H)
    if dtot > 0:
        return '%s세대' % format(dtot, ','), '부족', share
    if dtot < 0:
        return '%s세대' % format(-dtot, ','), '여유', share
    return '', '', share


def card_text(dtot, ratio, H=None):
    """홈·허브 카드의 한 줄: '686,396세대 부족(1년 적정물량의 1.8배)'(card_parts 를 잇는다 — 괄호 안이 앞 세대수가 1년 적정물량의
    몇 배인지다, 2026-10-05 안 A′). 순부족이 0이면 비율 조각만. 여기서만 만들어 결과 행 'ctxt'로 굽고 화면은 읽기만 한다."""
    # 기본값은 부를 때 모델 상수에서 읽는다(정의 때 굳히면 창·리드 상수를 바꾼 모듈에서 옛 연수가 남는다, 전수 리뷰 #19).
    H = LEAD_Q if H is None else H
    num, dirw, share = card_parts(dtot, ratio, H)
    return '%s %s(%s)' % (num, dirw, share) if num else share


# ── 부족 세대수의 식(홈 마케팅 검수 B2·C4, TRUST-2, 2026-09-27) ───────────────────────
# 카드의 686,396 은 '앞으로 3년 필요량 − 착공 기반 입주 추정'(425,873)이 아니다. 지난 4년 덜 지은 몫(260,523)이
# 더해진 값인데 홈에는 그 말이 없어 홈 재료만으로는 검산이 안 됐다. 식의 이름은 여기 하나에서 만들고
# 홈 산출 방법(손으로 쓴 index.html — 시험이 이 문구와 대조)·홈 카드 ⓘ(split_data 가 구운 ftxt)·시도 리포트의
# '숫자로 보면' 식(make_sido_pages)·블로그 지역 편(make_naver_post)이 같이 쓴다.
def formula_text(H=None, W=None, need=None, fut=None, inow=None):
    """'3년 필요량 − 착공 기반 입주 추정 + 지난 4년 쌓인 부족'. 숫자를 주면 각 항 뒤에 붙인다.

    inow 는 지난 창의 재고(준공 − 멸실 − 적정의 합, 음수 = 모자람). 모자라면 '쌓인 부족'을 더하고, 남으면
    '남은 재고'를 뺀다 — 음수 재고를 빼는 이중 부호를 읽는 사람에게 넘기지 않는다(점검후속 ⑤). 숫자 없이
    부르면(일반식) 모자란 쪽으로 적는다 — 식의 뜻을 설명하는 자리라 흔한 경우를 쓴다.
    """
    # 기본값은 부를 때 모델 상수에서 읽는다(정의 때 굳히면 창·리드 상수를 바꾼 모듈에서 옛 연수가 남는다, 전수 리뷰 #19).
    H = LEAD_Q if H is None else H
    W = BACKLOG_WINDOW if W is None else W
    ahead, past = '%g년' % (H / 4.0), '%g년' % (W / 4.0)

    def n(v):
        return '' if v is None else ' ' + format(abs(v), ',')
    tail = (('+ 지난 %s 쌓인 부족' % past) if (inow is None or inow < 0)
            else ('− 지난 %s 남은 재고' % past))
    return '%s 필요량%s − 착공 기반 입주 추정%s %s%s' % (ahead, n(need), n(fut), tail, n(inow))


def display_ints(row, H):
    """화면이 찍는 정수 넷(필요량·입주 추정·지난 재고·순부족) — 서로 검산된다.
    make_sido_pages 의 카드(rnd = half_up)와 같은 정수다. dtot 가 없으면(옛 행) 같은 식으로 센다."""
    need, fut, inow = half_up(row['ref']) * H, half_up(row['fut']), half_up(row['inow'])
    tot = row['dtot'] if 'dtot' in row else need - fut - inow
    return need, fut, inow, tot


def zone_texts(row, H):
    """한 판정 단위의 화면 문구 — 결과 행에 구워 싣는 필드들. 화면(JS)은 읽기만 한다.
      ctxt  '686,396세대 부족(1년 적정물량의 1.8배)'        (허브·지도 이름표·데스크톱 카드)
      cnum  '686,396세대'                            (카드 둘째 줄 — 모바일은 이것만)
      cdir  '부족' | '여유' | ''                      (넓은 화면 카드에서 세대수 뒤에)
      cpct  '1년 적정물량의 1.8배'
      ftxt  '3년 필요량 1,140,000 − 착공 기반 입주 추정 714,127 + 지난 4년 쌓인 부족 260,523 = 686,396세대 부족'
            (홈 카드 ⓘ '어떻게 계산했나' 한 줄, C4①)
    """
    need, fut, inow, tot = display_ints(row, H)
    cnum, cdir, cpct = card_parts(tot, row['ratio'], H)
    eq = formula_text(H, BACKLOG_WINDOW, need, fut, inow)
    return {'ctxt': card_text(tot, row['ratio'], H), 'cnum': cnum, 'cdir': cdir, 'cpct': cpct,
            'ftxt': '%s = %s' % (eq, ('%s %s' % (cnum, cdir)) if cnum else '0세대')}


# 홈 첫 화면에서 뺀 문구 필드(2026-09-28 대표 결정 — 작은 글씨 정리): 카드 아래 분포 한 줄(dist)·여유 지역 이름(dist_g0)·
# 공급 범례 뜻 한 줄(ktxt). 읽는 곳이 홈뿐이라 함수째 지웠다. data.js 의 ADV.sido 는 다음 배치가 점수를 다시 쓸 때까지 옛
# 필드를 싣고 있으므로 다시 구울 때 걷어 낸다 — 홈 코어(data-core)에 죽은 글자가 실리지 않게.
RETIRED_TEXTS = ('dist', 'dist_g0', 'ktxt')


def yearly_supply(stats, z, L, H=None):
    """앞으로 H분기를 네 분기씩 묶은 해마다의 '착공 기반 입주 추정 ÷ 적정물량'(%) — 2026-10-05 대표 요청('지금보다 1년·2년·3년
    뒤가 중요하다'). 판정(calc 의 fut·ratio)과 **같은 식**(착공 i−LEAD_Q 분기 × CONV)을 해마다 나눈 것이라 세 해의 입주 추정
    합이 calc 의 fut 와 같다(test_zone_outlook). 판정은 바꾸지 않는다 — 3년 합계로 균형인 경기도 1년 차가 73%로 모자라다는 것을
    보여 주려는 보조 표시다. H 가 4의 배수가 아니면 마지막 묶음은 남은 분기만으로 센다(적정도 그 분기 수만큼).
    반환: [{'n': 1, 'from': '2026Q3', 'to': '2027Q2', 'pct': 73}, ...]. 착공 자료가 없으면 빈 목록."""
    H = LEAD_Q if H is None else H
    st = quarterly(stats, '착공', z)
    ref = REF_Q.get(z)
    if not st or not ref:
        return []
    qs = list(range(L + 1, L + H + 1))
    out = []
    for k in range(0, len(qs), 4):
        g = qs[k:k + 4]
        f = sum(st.get(i - LEAD_Q, 0) * CONV for i in g)
        out.append({'n': k // 4 + 1, 'from': qkey(g[0]), 'to': qkey(g[-1]),
                    'pct': half_up(100.0 * f / (ref * len(g)))})   # 반올림은 occ_level 계약과 같은 half_up
    return out


def refresh_texts(sido):
    """저장된 판정(ADV.sido)의 화면 문구를 **지금의 함수**로 다시 굽는다(제자리). 숫자는 건드리지 않는다.

    ⚠️ 왜: 문구 함수(card_text 등)를 고친 PR 이 병합되어도 data.js 의 ADV.sido 는 다음 배치의 update_adv_data 가
    점수를 다시 쓸 때까지 옛 문구를 싣는다. split_data(홈 data-core)와 make_sido_pages(허브·리포트)는 이 함수로
    읽을 때마다 다시 구워, 화면이 늘 정본 함수의 문장을 말하게 한다. 새 필드가 없는 옛 행도 여기서 채워진다.
    """
    H = sido['H']
    for z in sido.get('zones') or []:
        z.update(zone_texts(z, H))
        if z.get('ratio') is not None:   # 비율 문구(rtxt)도 calc 가 굽지만 문구를 고친 PR 뒤엔 옛 말이 남는다(2026-10-05 표기 변경)
            z['rtxt'] = ratio_text(z['ratio'], H)
    for k in RETIRED_TEXTS:
        sido.pop(k, None)
    return sido


PERMIT_WIN = 24          # 3년 너머 신호의 창. 12월을 두 번 담아 한 해의 이례를 반으로 줄인다
PDEC_WIN = 12            # 12월 몫(pdec)을 재는 창 — 최근 이만큼의 달 가운데 12월 한 달의 비중


def win_years(months):
    """달 수 → 화면 말('24' → '2년'). 창 상수를 바꾸면 문장도 따라온다(전수리뷰 B7 — '최근 2년'이 손으로 적혀 있었다)."""
    return '%g년' % (months / 12.0)


# ⚠️ CONV_FROM 은 **착공 ÷ 인허가**(permit_start_conv)를 재는 첫 해다(인허가 누계가 2012년부터 온전하다). 착공 → 3년 뒤
# 준공 전환율 CONV(0.958)의 측정 구간이 아니다 — 그건 CONV_START_FROM·CONV_YEARS 다(전수 리뷰 #111). 한때 시도 리포트·홈이
# '96%가 … 2012년 이후 실측'이라고 이 상수를 읽었는데, 2012년부터 재면 94%다.
CONV_FROM = 2012


def permit_monthly(stats, region):
    """인허가 연내 누계 → 월별 호수 {'YYYY.MM': 호}.

    ⚠️ 저장된 인허가는 '호 (연내 누계)'다. 월 값을 그대로 더하면 약 6배로 부푼다
    (/monthly/ 표와 2026-09-13 분석이 이 함정에 걸렸다). 1월은 누계가 곧 그 달이고,
    나머지 달은 전월 누계와의 차다. 전월이 비면 그 달은 만들지 않는다.
    """
    s = stats.get('인허가') or {}
    ser = (s.get('series') or {}).get(region) or []
    # ⚠️ 빈 값: KOSIS의 null은 진짜 0이다. 인허가 누계에서 null은 전부 연초(그해 앞서
    # 쌓인 누계가 없는 달)에 있었다(2026-09-15 전수: 99개 중 99개). 이걸 건너뛰면 다음
    # 달의 전월 누계가 없어 그해가 통째로 빠진다 — 사이클 고리3 표본이 18 → 16으로
    # 줄고, 착공 전환율도 그 해를 잃었다. 그래서 그해 앞선 누계가 없을 때의 null은 0으로
    # 본다. 누계가 쌓인 뒤의 null은 0으로 보면 누계가 줄어드는 음수가 생기므로 건너뛴다.
    cum = {}
    seen = {}
    for d, v in zip(s.get('dates') or [], ser):
        k, y = d[:7], d[:4]
        if v is None:
            if not seen.get(y):
                cum[k] = 0.0
            continue
        cum[k] = v
        if v:
            seen[y] = True
    out = {}
    for k, v in cum.items():
        y, m = int(k[:4]), int(k[5:7])
        if m == 1:
            out[k] = v
            continue
        p = cum.get('%d.%02d' % (y, m - 1))
        if p is not None:
            out[k] = v - p
    return out


def permit_start_conv(stats, region):
    """같은 해 착공 ÷ 인허가 — 그 지역에서 허가 물량이 실제로 삽을 뜨는 비율.

    CONV_FROM부터 인허가 12월 누계와 착공 12개월이 모두 있는 완비 연도를 합쳐 잰다.
    해마다 크게 흔들리므로(전국 0.54~1.20) 연도별 값이 아니라 합계의 비율을 쓴다.
    """
    ps = stats.get('인허가') or {}
    cum = {d[:7]: v for d, v in zip(ps.get('dates') or [],
                                    (ps.get('series') or {}).get(region) or []) if v is not None}
    ss = stats.get('착공') or {}
    st = {d[:7]: v for d, v in zip(ss.get('dates') or [],
                                   (ss.get('series') or {}).get(region) or [])}
    tp = ts = 0.0
    y = CONV_FROM
    while ('%d.12' % y) in cum:
        months = ['%d.%02d' % (y, m) for m in range(1, 13)]
        if all(k in st for k in months):
            tp += cum['%d.12' % y]
            ts += sum((st[k] or 0.0) for k in months)
        y += 1
    return (ts / tp) if tp else None


def conv_measured(stats, region='전국', start=None, years=None):
    """착공 → LEAD_Q 분기 뒤 준공 전환율을 데이터로 다시 잰다 — CONV 가 그 구간(start 부터 years 쌍)의 값인지 대조용.

    착공 y 년과 준공 y+LEAD_Q/4 년이 둘 다 12개월 찬 쌍을 start 부터 years 개 모아 연도별 비(준공 ÷ 착공)의 평균을 낸다.
    쌍이 years 개가 안 되면 None. 창을 years 개로 묶어 두므로 데이터가 앞으로 가도(새 완비 연도) 값이 움직이지 않는다.
    """
    start = CONV_START_FROM if start is None else start
    years = CONV_YEARS if years is None else years

    def yearly(key):
        out = {}
        for y, (a, n) in ((qparts(i)[0], v) for i, v in _series(stats, key, region).items()):
            a0, n0 = out.get(y, (0, 0))
            out[y] = (a0 + a, n0 + n)
        return {y: a for y, (a, n) in out.items() if n == 12}
    st, dn = yearly('착공'), yearly('준공')
    lag = LEAD_Q // 4
    pairs = [dn[y + lag] / st[y] for y in sorted(st) if y >= start and y + lag in dn and st[y]][:years]
    return (sum(pairs) / len(pairs)) if len(pairs) == years else None


def permit_over_start_pct(stats, region='전국', step=5):
    """'인허가는 같은 해 착공보다 N%쯤 많다'의 N — permit_start_conv(착공 ÷ 인허가)의 역수에서 step 단위로 반올림.

    시도 리포트 '어떻게 계산했나'가 이 값을 굽고, 손 페이지(홈 산출 방법·소개·FAQ)의 같은 문장은 시험이 이 값과 대조한다
    (전수 리뷰 #112 — '15%쯤'이 네 곳에 박혀 있었다). 잴 수 없으면 None(문장이 그 구절을 뺀다).
    """
    c = permit_start_conv(stats, region)
    if not c:
        return None
    return step * half_up((1.0 / c - 1.0) * 100.0 / step)


# ── 입주물량 적정 대비 문턱(2026-09-30 대표 결정 ③, 전수 리뷰 #60·#113) ─────────────────────────
# 홈 통계 탭 입주물량 표(home-stats.js occCls)는 '적정 이상 = 파랑, 60% 이하 = 빨강', /moveins/ 는 '70% 미만 = 부족,
# 130% 초과 = 과잉'으로 같은 대상(입주물량 ÷ 적정물량)을 다르게 칠했다. 하나로 통일한다 — /moveins/ 의 값.
# 판정은 **표시하는 정수 퍼센트**(half_up)로 한다: 69.6% 를 '70%'로 찍으면서 '70% 미만' 색을 칠하지 않게.
# 홈은 split_data 가 ADV.occupancy.band 로 실어 준 이 두 값을 읽는다(JS 에 숫자를 따로 적지 않는다).
OCC_LO_PCT = 70      # 이 미만 = 부족(전세부터 조여드는 구간)
OCC_HI_PCT = 130     # 이 초과 = 과잉(입주장이 전세를 누르는 구간)


def occ_level(shown_pct):
    """표시 정수 퍼센트 → -1(부족)·0·+1(과잉)."""
    if shown_pct < OCC_LO_PCT:
        return -1
    if shown_pct > OCC_HI_PCT:
        return 1
    return 0


# ── 해마다 입주 신호등(2026-10-05 대표 요청 — '부족·균형 태그보다 동그라미 신호등 3개로 3년을 한눈에') ──────────────────────
# 동그라미 하나가 한 해(yearly_supply 의 1·2·3년 차)이고 색은 위 입주물량 문턱(occ_level)으로 가른다(대표 결정 — 70%·130% 안).
# 판정 등급 컷(1년 적정물량의 1.5배)을 빌리지 않는다: 판정은 지난 4년 덜 지은 몫까지 더한 3년 합계라 해마다의 입주와 다른 양이다.
# 지역 허브·시도 리포트(make_sido_pages)와 홈 판정 카드(split_data 가 year_lights·lights_aria·light_legend 를 실어 줌)가
# 이 한 곳을 읽는다 — 홈 스크립트에 문턱·이름을 다시 적지 않는다.
# 이름은 판정 낱말(부족·균형·여유)과 겹치지 않게 '적음·보통·많음'이다(2026-10-06 대표 결정 — 리뷰에서 경기 한 칸이 글로는 '부족',
# 신호등은 '적정', 막대는 '균형'으로 세 낱말이 겹쳐 읽혔다). 신호등은 판정이 아니라 그해 들어올 입주의 많고 적음이다.
LIGHT = {-1: ('lo', '적음'), 0: ('ok', '보통'), 1: ('hi', '많음')}


def light_of(pct):
    """표시 정수 퍼센트 → (색 키, 이름)."""
    return LIGHT[occ_level(pct)]


def light_rng():
    """색 키 → 문턱 구간 글('70% 미만'·'70~130%'·'130% 초과')."""
    return {'lo': '%d%% 미만' % OCC_LO_PCT, 'ok': '%d~%d%%' % (OCC_LO_PCT, OCC_HI_PCT), 'hi': '%d%% 초과' % OCC_HI_PCT}


def light_legend():
    """범례 항목 [(색 키, 구간, 이름)] — 낮은 쪽부터."""
    rng = light_rng()
    return [(k, rng[k], lab) for k, lab in (LIGHT[-1], LIGHT[0], LIGHT[1])]


LIGHT_CAP = '%s년 차 입주(1년 적정물량 대비)'   # 범례 머리(허브·홈) — %s 는 '1·2·3'


def lights_aria(yrs):
    """읽어 줄 글 — 숫자를 앞에 두고 짧게('해마다 입주(1년 적정물량 대비): 1년 차 37% 적음, …'). 2026-10-06 리뷰: 옛 글은
    '1년 적정물량의'를 세 번 되풀이해 링크 이름이 130자가 넘었다."""
    return '해마다 입주(1년 적정물량 대비): ' + ', '.join('%d년 차 %d%% %s' % (y['n'], y['pct'], light_of(y['pct'])[1])
                                                    for y in yrs)


def year_lights(stats, z, L, H=None):
    """홈 카드용 압축형 [{'n': 1, 'p': 61, 'k': 'lo'}, …] — yearly_supply 와 같은 값."""
    return [{'n': y['n'], 'p': y['pct'], 'k': light_of(y['pct'])[0]} for y in yearly_supply(stats, z, L, H)]


# ── 가격 변동률의 기간 합(전수 리뷰 #15·#110) ─────────────────────────────────────────────────
PRICE_FIELDS = ('ma', 'je', 'wo')
PERIOD_MONTHS = {'q': 3, 'y': 12}


def period_key(y, m, per):
    """(연, 월) → 기간 이름. 'q' = '2025Q2', 'y' = '2025'."""
    return ('%dQ%d' % (y, (m - 1) // 3 + 1)) if per == 'q' else str(y)


def price_periods(monthly, per='q'):
    """ADV.monthly(월별 매매·전세·월세 변동률) → {기간 이름: {지역: [매매, 전세, 월세]}} — 원값의 단순 합.

    ⚠️ 기간의 달이 **다 찬 항목만** 합을 낸다(분기 3달, 연 12달). 예전 시도 리포트(price_quarters)와 홈(tbAgg)은 값이 있는
    달만 더해, 전남광주 2025Q2 는 4·5월 두 달 합(-0.5%)이 분기 변동률처럼 찍히고 색이 칠해졌다(6월 결측). 연 보기의 2025년도
    1~5월 합이었다(대표 결정 ⑧: 달이 덜 찬 해는 '–'). 모자라면 그 항목은 None, 세 항목이 모두 None 이면 지역 키를 두지 않는다.
    ⚠️ 원값으로 한 번만 더한다. 홈은 소수 둘째 자리로 반올림한 월값을 더해 표시값이 리포트와 칸의 5%에서 갈렸다(#110).
    split_data 가 이 결과를 홈에 실어 주고 시도 리포트도 같은 함수를 읽는다.
    """
    need = PERIOD_MONTHS[per]
    regs = (monthly or {}).get('regions') or []
    acc = {}
    for r in (monthly or {}).get('rows') or []:
        y, m = int(r['p'][:4]), int(r['p'][5:7])
        cur = acc.setdefault(period_key(y, m, per), {})
        for k, reg in enumerate(regs):
            for n, f in enumerate(PRICE_FIELDS):
                vals = r.get(f) or []
                v = vals[k] if k < len(vals) else None
                if v is None:
                    continue
                a = cur.setdefault(reg, [[0.0, 0], [0.0, 0], [0.0, 0]])
                a[n][0] += v
                a[n][1] += 1
    out = {}
    for key, regsum in acc.items():
        for reg, a in regsum.items():
            vals = [s if c == need else None for s, c in a]
            if any(v is not None for v in vals):
                out.setdefault(key, {})[reg] = vals
    return out


def permit_signal(stats, region, ref_q):
    """3년 너머 참고 신호. 판정 산식에는 넣지 않는다.

    값 = 최근 PERMIT_WIN개월 인허가의 연평균 × 착공 전환율 ÷ 연 필요량.
    12월 몫 = 최근 12개월 인허가 중 12월 한 달의 비중. 이례 여부를 가르는 문턱은
    두지 않고 숫자만 보여준다(2026-09-13 대표 결정).
    돌려주는 값: {'pbr', 'pdec', 'pconv'} — 계산할 수 없으면 None.
    """
    mon = permit_monthly(stats, region)
    ks = sorted(mon)
    conv = permit_start_conv(stats, region)
    if len(ks) < PERMIT_WIN or not conv or not ref_q:
        return None
    # 창이 중간에 비면(월 결측) 연평균이 줄어 얇게 잡힌다 — 연속된 달만 쓴다
    last = ks[-1]
    ly, lm = int(last[:4]), int(last[5:7])
    want = []
    for i in range(PERMIT_WIN):
        t = ly * 12 + lm - 1 - i
        want.append('%d.%02d' % (t // 12, t % 12 + 1))
    if any(k not in mon for k in want):
        return None
    yearly = sum(mon[k] for k in want) * 12.0 / PERMIT_WIN
    last12 = want[:PDEC_WIN]
    p12 = sum(mon[k] for k in last12)
    dec = sum(mon[k] for k in last12 if k.endswith('.12'))
    return {'pbr': yearly * conv / (ref_q * 4.0),
            'pdec': (dec / p12) if p12 > 0 else None,
            'pconv': conv}


def split_text(inow, fut, need, ref, sig, est, H=None, W=None):
    """리포트 머리의 세 줄(지난 4년·앞으로 3년·3년 너머)과 추정 안내. 숫자만 쓴다.

    대표 판정 한 줄이 서로 다른 세 방향을 뭉갠다(경기: 지난 4년 거의 균형, 앞으로
    3년 12% 부족, 3년 너머 필요량 이상). 단계 말(충분·부족)을 붙이면 근거 없는
    문턱이 새로 생기므로 숫자만 적는다(2026-09-13 대표 결정 A안).
    ⚠️ 여기서만 만든다. calc()가 결과 행에 'split'으로 구워 싣고 화면은 읽기만 한다.
    """
    # 기본값은 부를 때 모델 상수에서 읽는다(정의 때 굳히면 창·리드 상수를 바꾼 모듈에서 옛 연수가 남는다, 전수 리뷰 #19).
    H = LEAD_Q if H is None else H
    W = BACKLOG_WINDOW if W is None else W
    past = '%g년' % (W / 4.0)
    ahead = '%g년' % (H / 4.0)
    now = int(round(100.0 * inow / (ref * W))) if ref else 0
    if now <= -1:
        l1 = '필요량보다 %d%% 덜 지었습니다' % -now
    elif now >= 1:
        l1 = '필요량보다 %d%% 더 지었습니다' % now
    else:
        l1 = '필요량만큼 지었습니다'
    l2 = '필요량의 %d%%가 들어옵니다' % int(round(100.0 * fut / need)) if need else None
    l3 = dec = None
    thin = False
    if sig:
        l3 = '최근 %s 인허가를 착공으로 환산하면 필요량의 %d%%입니다' % (win_years(PERMIT_WIN), pbr_pct(sig['pbr']))
        if sig.get('pdec') is not None:
            dec = '최근 %s 인허가 중 12월 한 달이 %d%%입니다' % (win_years(PDEC_WIN), int(round(100 * sig['pdec'])))
        thin = pbr_thin(sig['pbr'])
    return {
        'rows': [('지난 %s' % past, l1), ('앞으로 %s' % ahead, l2)],
        'ref': ('%s 너머' % ahead, l3, dec, thin) if l3 else None,
        'ref_note': '인허가에는 실제로 착공하지 않는 계획이 섞여 있어 참고로만 봅니다. 판정에는 넣지 않습니다.',
        'est_note': ('이 지역은 기준표에 없어 적정물량을 추정했습니다.' if est else None),
    }


def grade(ratio):
    c = GRADE_CUTS
    if ratio >= c[0]: return 'g4'
    if ratio >= c[1]: return 'g3'
    if ratio >= c[2]: return 'g2'
    if ratio >= c[3]: return 'g1'
    return 'g0'


def calc(stats):
    """ORDER 전 지역(시도+집계)의 누적 순부족.

        I_now = Σ_{최근 16분기} (준공 − 멸실 − 적정)
        미래공급 = Σ_{k} 착공(k − 12분기) × 0.958
        누적순부족 = 적정 × H − 미래공급 − I_now

    ⚠️ 창의 기준점은 '오늘'이 아니라 **준공 실적의 마지막 완결 분기(L)** 다.
    오늘을 쓰면 아직 안 끝난 분기의 준공이 0으로 들어가 재고가 한 분기치 적정만큼
    깎인다. L을 쓰면 과거는 실적으로만, 미래는 L+1부터로 깔끔하게 갈린다.

    H는 착공 자료가 닿는 데까지 — 착공 마지막 분기 S에 대해 H = S + 12 − L.
    지금은 정확히 12분기(3년)이고, 분기가 지날 때마다 유지된다.
    """
    L = last_full_quarter(stats, '준공', '전국')
    S = last_full_quarter(stats, '착공', '전국')
    if L is None or S is None:
        raise ValueError('준공·착공 시리즈가 비어 있다')
    H = S + LEAD_Q - L
    # ⚠️ H는 데이터 가용성에서 유도된다. 착공표(DT_MLTM_5387)가 준공표보다 한 달만
    # 늦게 들어와도 S가 한 분기 밀려 H=11이 되고, 재고창은 16분기 고정이라 더 작은
    # need로 나뉘어 **실공급 변화 0인데 전 지역 ratio가 통째로 올라간다**
    # (2026-08-07 감사). H가 정상값(LEAD_Q)과 다르면 드러낸다.
    if H != LEAD_Q:
        import sys as _s
        print('⚠️ sido_zones: 미래 시야가 %d분기다(정상 %d) — 착공 %s vs 준공 %s. '
              '재고창은 16분기 고정이라 need만 줄어 전 지역 비율이 함께 움직인다.'
              % (H, LEAD_Q, qkey(S), qkey(L)), file=_s.stderr)
    if H <= 0:
        raise ValueError('미래 시야가 0 이하다 (착공 %s, 준공 %s)' % (qkey(S), qkey(L)))
    out, missing = [], []
    un_prd = None
    for z in ORDER:
        ref = REF_Q[z]
        dn = quarterly(stats, '준공', z)
        st = quarterly(stats, '착공', z)
        if not dn or not st or not has_any(stats, '준공', z) or not has_any(stats, '착공', z):
            # ⚠️ 조용히 넘기면 그 지역이 표·페이지·sitemap에서 통째로 사라진다.
            # update_adv_data의 sido 가드가 '지역 수 감소'를 잡지만, 왜 줄었는지는
            # 여기서만 알 수 있다. 이 프로젝트에서 조용한 소거로 세 번 사고가 났다.
            missing.append(z)
            continue
        dby = demol_q(stats, z)
        inow = sum(dn.get(i, 0) - demol_of(dby, qparts(i)[0]) - ref
                   for i in range(L - BACKLOG_WINDOW + 1, L + 1))
        fut = sum(st.get(i - LEAD_Q, 0) * CONV for i in range(L + 1, L + H + 1))
        need = ref * H
        tot = need - fut - inow
        ratio = tot / need if need else 0.0
        # 등급은 **저장되는 비율**(소수 넷째 자리)로 매긴다 — 반올림 전 값으로 매기면 0.49996 이 'g1'인데 저장값 0.5 는
        # grade() 로 'g2'라, 저장된 ratio·grade 짝이 어긋난다(전수 리뷰 #9).
        g = grade(round(ratio, 4))
        un, un_p = unsold_latest(stats, z)
        if un_p:
            un_prd = un_p
        # 미분양이 분기 적정물량의 몇 배인가. 판정이 '부족' 쪽인데 이 값이 1을
        # 넘으면 두 신호가 어긋난 것 — 화면에 ⚠로 드러낸다.
        #
        # ⚠️ 등급을 이 값으로 깎지 않는다(2026-08-15 마케팅 요청 #3 검토 결론).
        # "제주는 부족 1위인데 미분양도 1위 아니냐"는 물음은 타당하지만, 감쇠가
        # 판정을 낫게 하는지는 별개다. 17시도 × 20년 월별 패널(n≈3,600)로 쟀다:
        #   미분양(지역 평균 대비) vs 이전 12개월 가격변동  r = -0.31
        #   미분양               vs 이전 24개월 가격변동  r = -0.32
        #   미분양               vs 이후 12개월 가격변동  r = -0.07
        #   미분양               vs 이후 24개월 가격변동  r = +0.07
        # 미분양은 **이미 벌어진 하락의 흉터**지 앞으로의 신호가 아니다. 뒤를 보는
        # 상관은 뚜렷한데 앞을 보는 상관은 0이고, 24개월에선 부호가 뒤집힌다.
        # 3년 앞 공급을 재는 등급에 이걸 섞으면 지나간 가격을 미래 판정에 넣는 것이다.
        # (현 시점 단면만 보면 r=-0.42까지 나오는데, 그게 바로 이 후행성의 그림자다 —
        #  '예측력'으로 오독하기 쉬운 자리라 수치를 남긴다.)
        # 대신 어긋남은 uwarn으로 드러낸다 — 숨기지 않되 순위는 건드리지 않는다.
        um = (un / float(ref)) if (un is not None and ref) else None
        # 표 아래 '인허가 1년' 참고 행은 여전히 최근 12개월 원값(pm12·pmr)을 보여준다.
        pm, _ = permit_trail12(stats, z)
        pmr = (pm / float(ref * 4)) if (pm is not None and ref) else None
        # 3년 너머 참고 신호(2026-09-13 대표 결정): 최근 24개월 연평균 × 착공 전환율.
        # 12개월 원값은 한 해의 이례적 12월에 기대고(경기 2024년 60%·2025년 48%),
        # 창 길이에 따라 판단이 뒤집혔다(울산 12개월 124% vs 24개월 82%).
        # pwarn은 이제 이 값으로 켠다. 경고 박스가 아니라 참고 줄의 강조라, 문턱
        # 0.95 경계(인천 94%)에서 달마다 깜빡이는 것은 감수한다(대표 결정).
        sig = permit_signal(stats, z, ref)
        split = split_text(inow, fut, need, ref, sig, z in EST, H)
        out.append({
            'z': z, 'region': REGION[z], 'agg': z in AGG, 'est': z in EST,
            'ref': ref, 'inow': round(inow), 'fut': round(fut), 'need': need,
            'tot': round(tot), 'ratio': round(ratio, 4), 'grade': g,
            # 저장되는 ratio(소수 넷째 자리)로 만든다. 반올림 전 값으로 만들면 배수 경계(0.1배)에서
            # 화면의 문구와 저장된 숫자가 한 칸 어긋날 수 있다.
            'rtxt': ratio_text(round(ratio, 4), H),
            # 화면에 찍는 순부족 정수(카드의 적정·공급·재고 정수로 검산되는 값). 카드 문구는 refresh_texts 가 붙인다.
            # 저장되는 fut·inow(round 결과)와 같은 정수로 만든다 — 반올림 전 값으로 하면
            # 리포트 카드의 세 정수로 검산한 값과 1세대 어긋난다(경기 50,578 vs 50,579).
            'dtot': half_up(ref) * H - round(fut) - round(inow),
            'unsold': (None if un is None else round(un)),
            'um': (None if um is None else round(um, 3)),
            'uwarn': bool(um is not None and um >= 1.0 and g in ('g4', 'g3', 'g2')),
            'pm12': (None if pm is None else round(pm)),
            'pmr': (None if pmr is None else round(pmr, 3)),
            'pbr': (None if sig is None else round(sig['pbr'], 3)),
            'pdec': (None if (sig is None or sig['pdec'] is None) else round(sig['pdec'], 3)),
            'pconv': (None if sig is None else round(sig['pconv'], 3)),
            'pwarn': bool(sig is not None and pbr_thin(sig['pbr'])),   # 리포트 강조(thin)와 같은 함수(B3)
            'split': split,
        })
    # ── 집계 항등식 자가검사 ────────────────────────────────────────────────
    # 부분 결측은 missing 가드에 안 걸린다. 한 지역의 특정 월만 None이면 그 지역만
    # 공급이 낮게 잡히는데 지역 수는 그대로라 아무도 모른다. 전국은 별도 시리즈라
    # 영향을 안 받으므로, Σ시도와 전국을 대조하면 그 어긋남이 드러난다
    # (2026-08-07 감사에서 경기 3개월 None으로 11,698호 차이를 실측).
    warn = []
    byz = {x['z']: x for x in out}

    def _cmp(label, ssum, nat, k):
        if nat and abs(ssum - nat) > max(50, abs(nat) * 0.001):
            warn.append('%s %s: 합 %s vs %s (차 %s)'
                        % (label, k, format(int(ssum), ','), format(int(nat), ','),
                           format(int(ssum - nat), ',')))
    if '전국' in byz:
        for k in ('inow', 'fut', 'tot'):
            _cmp('전국', sum(byz[z][k] for z in ORDER if z not in AGG and z in byz),
                 byz['전국'][k], k)
    # ⚠️ 집계행 자체(수도권·지방)도 대조해야 한다. Σ는 시도만 도니까 '수도권' 열의
    # 착공이 통째로 빠져도 위 검사는 통과한다 — 실측으로 fut가 143,419호 어긋나고
    # tot가 41% 틀린 채 무경고 배포됐다(2026-08-07 감사).
    CAP = ('서울', '경기', '인천')
    if '수도권' in byz and all(z in byz for z in CAP):
        for k in ('inow', 'fut', 'tot'):
            _cmp('수도권', sum(byz[z][k] for z in CAP), byz['수도권'][k], k)
    if '지방' in byz and '전국' in byz and '수도권' in byz:
        for k in ('inow', 'fut', 'tot'):
            _cmp('지방', byz['전국'][k] - byz['수도권'][k], byz['지방'][k], k)
    if warn:
        import sys as _s
        _msg = ('sido_zones: 집계 항등식이 깨졌다 — 어느 지역의 시리즈에 부분 결측이 '
                '있을 수 있다(전국은 별도 시리즈라 영향을 안 받는다).')
        print('⚠️ ' + _msg + chr(10) + '  ' + (chr(10) + '  ').join(warn),
              file=_s.stderr)
    if missing:
        import sys as _s
        print('⚠️ sido_zones: 준공·착공 시리즈가 없어 빠진 지역 %d곳 — %s '
              '(STATS 부분 응답 의심. 이 지역들은 표·페이지·sitemap에서 사라진다)'
              % (len(missing), ', '.join(missing)), file=_s.stderr)
    # 화면 문구(ctxt·cnum·cdir·cpct·ftxt)는 refresh_texts 한 곳에서 붙인다 — split_data·make_sido_pages 가 읽을 때
    # 다시 굽는 것과 같은 함수다.
    return refresh_texts({'L': qkey(L), 'S': qkey(S), 'H': H,
            'lead': LEAD_Q, 'conv': CONV, 'window': BACKLOG_WINDOW,
            'unsold_prd': un_prd, 'missing': missing, 'agg_warn': warn, 'Ltxt': quarter_text(qkey(L)), 'zones': sorted(out, key=lambda x: DISPLAY_ORDER.index(x['z']))})


def supply_rows(stats):
    """통계 탭 '입주물량'과 /moveins/가 쓸 분기 시계열 — **홈 표와 같은 소스**.

    ⚠️ 2026-08-07까지 이 자리는 odcloud 입주예정(ADV.occupancy)이었다. 그래서
    같은 서울 2027Q2를 홈은 2,107세대, 통계 탭은 1,073세대로 보여줬고(2배),
    기준선도 적정물량(REF_Q)·적정밴드(band)·ref 셋이 공존해 제주가 동시에
    '매우 부족'이자 '밴드 상단 초과'였다(2026-08-07 감사). 소스를 하나로 합친다.

    과거는 준공 실적, 미래는 착공을 LEAD_Q분기 뒤로 밀어 ×CONV. e=1이 미래 표시.
    """
    L = last_full_quarter(stats, '준공', '전국')
    S = last_full_quarter(stats, '착공', '전국')
    if L is None or S is None:
        return None
    regs = [z for z in ORDER]
    dn = {z: quarterly(stats, '준공', z) for z in regs}
    st = {z: quarterly(stats, '착공', z) for z in regs}
    start = qidx(2017, 1)
    rows = []
    for i in range(start, S + LEAD_Q + 1):
        fut = i > L
        v = []
        for z in regs:
            if fut:
                # ⚠️ 분기마다 반올림하면 소비자가 그걸 다시 더해 홈과 갈린다 —
                # '2026년 전국 입주물량'이 /moveins/ 215,875 · 통계 탭 215,876 ·
                # 홈 215,877로 셋이 달랐다(2026-08-08 감사). 표시 직전에 한 번만
                # 반올림하도록 소수 한 자리로 넘긴다(페이로드 영향은 무시할 수준).
                # ⚠️ 자리수를 줄이면 x.5로 굳어 **이중 반올림**이 된다 —
                # 1자리로 뒀더니 36529.498 → 36529.5 → 화면 36,530으로 홈(36,529)과
                # 갈렸다(2026-08-08 감사, 1,000칸 중 11칸). 3자리면 그 경계가 안 생긴다.
                v.append(round(st[z].get(i - LEAD_Q, 0) * CONV, 3))
            else:
                v.append(dn[z].get(i, 0))
        r = {'p': qkey(i), 'v': v}
        if fut:
            r['e'] = 1
        rows.append(r)
    return {'regions': regs, 'rows': rows, 'ref': dict(REF_Q),
            'note': ('분기별 아파트 공급 — 과거는 국토교통부 준공 실적, '
                     '%s 이후는 착공 실적을 %d년 뒤로 밀어 추정(전환율 %.3f). '
                     '기준선은 분기 적정물량이며 홈 공급표와 같은 값이다.'
                     % (qkey(L + 1), LEAD_Q // 4, CONV))}


def zone_order(rows):
    """등급 내림차순 → 같은 등급 안에서는 순부족 큰 순. 집계 3종은 제외.

    ⚠️ 홈과 지역 페이지가 같은 순서를 써야 한다. 예전에 홈은 ratio로, 페이지는
    등급으로 정렬해 44곳 중 38곳의 순위가 어긋난 적이 있다(2026-08-03).
    """
    r = [x for x in rows if not x.get('agg')]
    return sorted(r, key=lambda x: (GRADE_KEYS.index(x['grade']), -x['tot']))


def _load_stats(path=None):
    import io, json, os
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'data-rest.json')
    return json.load(io.open(path, encoding='utf-8'))['STATS']


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    r = calc(_load_stats())
    print('실적 끝 %s · 착공 끝 %s · 미래 %d분기(%.1f년)'
          % (r['L'], r['S'], r['H'], r['H'] / 4.0))
    print()
    print('%-6s %11s %10s %10s %7s  %s' % ('지역', '누적순부족', '과거재고', '미래공급', '수요대비', '판정'))
    for x in [y for y in r['zones'] if y['agg']] + zone_order(r['zones']):
        print('%-6s %11s %10s %10s %7.2f  %s%s'
              % (x['z'], format(x['tot'], ','), format(x['inow'], ','), format(x['fut'], ','),
                 x['ratio'], GRADE_LABS[x['grade']], ' *추정' if x['est'] else ''))
