# -*- coding: utf-8 -*-
"""/cycle/ 리포트의 '현재 시세' 배열을 data.js에서 다시 만든다.

리포트는 서술형 문서라 대부분 고정 분석값이지만, **지수·전세가율처럼 계속 갱신되는
계열을 하드코딩해 둔 부분**이 있었다. 그게 세 번 연속 감사에 걸렸다:
  - 2026-08-08 jratio_level이 /jeonse-ratio/와 값·순위가 달랐다(서울 55.4 vs 52.3).
  - 같은 날 zones·rate_overlay의 지수 레벨이 --heal-basic 교정분(6,041셀)을 안 따라와
    수도권 2026Q1이 154.7 vs 통계 탭 157.8로 3.1포인트 어긋났다.
손으로 고치면 다음 갱신에 또 어긋나므로 생성기로 옮긴다.

⚠️ 지역 구성이 바뀌었다. 옛 배열은 생활권 4곳(수도권·부산권·대경권·대전권)인데
2026-08-06 재편으로 생활권이 폐기돼 부산권·대경권·대전권은 **재현할 수 없다**
(어느 시군을 묶었는지 정의가 사라졌다). 지금 데이터로 정직하게 표현할 수 있는
단위인 수도권·부산·대구·대전으로 바꾼다 — 리포트의 논지("수도권만 매매가 전세를
크게 따돌린다")는 그대로 성립한다.

사용: python tools/refresh_cycle_data.py
"""
import io
import json
import math
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sido_zones as SZ      # noqa: E402  (지역 정의의 정본 — 손 목록 금지)
import kst as KST            # noqa: E402  (오늘(KST) — 생성기가 찍는 날짜의 단일 출처)
import make_indicator_pages as I  # noqa: E402  (전세가율 기준월 규칙·sitemap — /jeonse-ratio/ 와 같은 규칙)
import robots_meta as RM     # noqa: E402  (검색 로봇 메타 정본 — 홈 마케팅 검수 D2)
import rebuild_cycle_analysis as RC  # noqa: E402  (지수 연속성 검사·페이지 데이터에서 채우는 본문 칸의 정본)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data.js')
PAGE = os.path.join(ROOT, 'cycle', 'index.html')

# 차트에 세울 지역. 옛 생활권 4곳을 대신한다(위 주석 참조).
ZONE_REGIONS = ['수도권', '부산', '대구', '대전']
# ⚠️ 손 목록을 두지 않는다. 2026-09-10 광주·전남 통합 때 이 목록이 옛 이름을
# 들고 있었고, 아래 build_jratio가 **모르는 지역을 조용히 건너뛰는** 구조라
# 전세가율 차트에서 전남광주가 통째로 빠진 채 배포됐다(2026-09-12 발견).
# 모델이 곧 목록이다.
SIDO = [z for z in SZ.ORDER if z not in SZ.AGG]
SUDO = {'서울', '경기', '인천'}
ZONES_FROM = 2006          # 옛 배열과 같은 시작점
OVERLAY_FROM = 2015        # 금리 오버레이 구간


def load_stats():
    c = io.open(DATA, encoding='utf-8').read()
    i = c.find('const STATS=')
    j = c.find('/*STATS_DATA_END*/')
    return json.loads(c[i + len('const STATS='):j].rstrip().rstrip(';'))


def ym(label):
    """'2026.06' / '2026.06 p)' → (2026, 6). 연간 라벨이면 None."""
    m = re.match(r'^(\d{4})\.(\d{1,2})', str(label).strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def quarterly(D, region, y_from, nd=1):
    """{연.분기(2026.25 형식): 그 분기 평균}. 값이 하나도 없는 분기는 넣지 않는다.

    nd 는 소수 자릿수다. 지수·전세가율은 1, CD금리는 원천(한국은행)이 소수 둘째 자리로 발표하므로 2 로 부른다
    (전수 리뷰 #30: 여기서 첫째 자리로 반올림한 뒤 build_overlay 가 round(…, 2) 를 해 2026Q3 2.94 가 2.9 로 실렸다).
    """
    ser = (D.get('series') or {}).get(region)
    if not ser:
        return {}
    acc = {}
    for k, lab in enumerate(D['dates']):
        p = ym(lab)
        if not p or p[0] < y_from:
            continue
        v = ser[k]
        if v is None:
            continue
        t = p[0] + (p[1] - 1) // 3 * 0.25
        acc.setdefault(t, []).append(v)
    # ⚠️ math.fsum 을 쓴다. 파이썬 3.12 부터 내장 sum() 이 실수에 보정 합산을 해서 3.11 과 끝자리가 갈린다.
    #    .x5 경계에서 반올림이 뒤집혀(수도권 2011Q1 87.8↔87.9 등 세 칸) 개발 컨테이너(3.11)와 배치(3.12)가
    #    같은 data.js 로 다른 값을 굽고, 커밋마다 그 세 칸이 번갈아 바뀌었다(2026-08-08~09-18). fsum 은
    #    정확히 반올림한 합이라 판에 상관없이 같고, 배치(3.12)가 굽던 값과도 같다(2026-09-26 데이터 감사).
    return {t: round(math.fsum(a) / len(a), nd) for t, a in acc.items()}


def hold_index_breaks(S):
    """매매·전세지수에 기준 단절이 있으면 그 달부터를 빼고 돌려준다(대표 결정 09-30 ①: 재수집 전까지 그 계열 갱신 보류).

    원천이 기준시점을 바꿨는데(2017.11=100 → 2026.06=100) 수집이 최근 여덟 달만 새 기준으로 덮어써, 2026-09-28
    배치가 수도권 매매 154.6 → 96.6 같은 가짜 폭락을 차트에 실었다(전수 리뷰 #61). 두 기준의 값을 비율로 이어
    붙이지 않는다(원천 값 가공 금지) — 단절 앞의 옛 기준 구간만 그리고, 전 기간 재수집으로 단절이 사라지면 저절로
    전 구간이 다시 실린다. 단절 판정은 사이클 재산정과 같은 함수(RC.index_breaks)다.
    """
    out = dict(S)
    for key in RC.INDEX_KEYS:
        cut = RC.first_break(S, key)
        if not cut:
            continue
        blk = S[key]
        k0 = blk['dates'].index(cut)
        out[key] = dict(blk, series={r: list(v[:k0]) + [None] * (len(v) - k0) for r, v in blk['series'].items()})
        print('  ⚠️ %s 기준 단절(%s부터) — 전 기간 재수집 전까지 그 달부터는 싣지 않는다: %s'
              % (key, cut, RC.break_message(RC.index_breaks(S, (key,)))))
    return out


def index_basis(D):
    """지수 계열 unit 의 기준시점('2017.11'·'2026.06'). 표기가 없으면 None. 재수집(update_adv_data.refetch_basic_full)이
    unit 을 새 기준으로 고쳐 쓰고, 보류한 계열은 옛 unit 그대로다."""
    m = re.search(r'(\d{4}\.\d{2})=100', (D or {}).get('unit') or '')
    return m.group(1) if m else None


def index_bases_agree(S):
    """매매·전세지수가 같은 기준시점인가. 둘은 zones·rate_overlay 에서 한 y축('지수')에 겹쳐 그려진다.

    수집은 계열마다 따로 재수집·보류한다(update_basic). 매매만 재수집에 성공하면 매매는 2026.06=100, 전세는
    2017.11=100 인 채로 같은 축에 올라, 수도권 2021Q4 매매 106.8 · 전세 128.7 처럼 '매매가 전세를 크게 이탈해
    솟구쳤다'는 캡션과 반대 그림이 나왔다(통합 검토). 원천 값을 비율로 맞추지 않는다(대표 결정 ① — 연결계수 금지).
    """
    return len({index_basis(S.get(k)) for k in RC.INDEX_KEYS}) <= 1


def build_zones(S):
    ma, je = S['매매지수'], S['전세지수']
    out = {}
    for rg in ZONE_REGIONS:
        qm = quarterly(ma, rg, ZONES_FROM)
        qj = quarterly(je, rg, ZONES_FROM)
        ts = sorted(qm)
        if not ts:
            print('  ⚠️ %s: 매매지수 없음 — 건너뜀' % rg)
            continue
        # 전세지수는 2014년부터라 그 이전은 null(옛 배열과 같은 모양)
        out[rg] = {'t': ts,
                   'maemae': [qm[t] for t in ts],
                   'jeonse': [qj.get(t) for t in ts]}
    return out


def build_overlay(S):
    ma = quarterly(S['매매지수'], '수도권', OVERLAY_FROM)
    je = quarterly(S['전세지수'], '수도권', OVERLAY_FROM)
    jr = quarterly(S['전세가율'], '수도권', OVERLAY_FROM)
    rt = quarterly(S['금리'], 'CD(91일)', OVERLAY_FROM, nd=2)
    ts = sorted(t for t in ma if t in rt)
    return {'t': ts,
            'maemae': [ma[t] for t in ts],
            'jeonse': [je.get(t) for t in ts],
            'rate': [rt[t] for t in ts],
            'jratio': [jr.get(t) for t in ts]}


def build_jratio(S):
    """전세가율 최신월 기준 시도 스펙트럼 + 수도권·지방 평균."""
    D = S['전세가율']
    # 계열에 아예 없는 지역은 목록이 낡았다는 신호다 — 조용히 빠뜨리지 않는다.
    gone = [r for r in SIDO if not D['series'].get(r)]
    if gone:
        raise RuntimeError('전세가율에 없는 지역: %s (모델과 저장분이 어긋났다)'
                           % ', '.join(gone))
    # 기준월은 /jeonse-ratio/·시도 리포트와 같은 규칙·같은 필요 지역(JEONSE_NEED = 전국 + 시도)으로 고른다.
    # dates[-1] 을 그대로 읽으면 원천이 행을 바꾼 달에 0 나누기·풀이 문장 RuntimeError 로 배치가 멈췄다
    # (2026-09-26 데이터 감사). 전에는 시도만 봐서 전국만 빈 달에 /cycle/ 과 /jeonse-ratio/ 의 기준월이 한 달
    # 갈렸다(전수 리뷰 #24·#106) — 서로 링크된 화면이 다른 달을 말하지 않게 한 정본을 쓴다.
    k = I.jeonse_ref_index(D, I.JEONSE_NEED)
    rows = [(r, D['series'][r][k]) for r in SIDO
            if D['series'][r][k] is not None]
    rows.sort(key=lambda x: x[1])
    lvl = [{'region': r, 'val': round(v, 1), 'sudo': r in SUDO,
            'type': '투자성' if v < 60 else ('중간' if v < 73 else '실거주성')}
           for r, v in rows]
    sudo = [v for r, v in rows if r in SUDO]
    jib = [v for r, v in rows if r not in SUDO]
    return lvl, round(math.fsum(sudo) / len(sudo), 1), round(math.fsum(jib) / len(jib), 1), D['dates'][k]


# 사이클 본문의 전세가율 풀이 칸(2026-09-15 콘텐츠 세션 제안). 전세가율은 이 배치가 매일
# 갈아끼우므로 칸도 여기서 채운다 — 사이클 재산정(rebuild_cycle_analysis)은 손으로 돌릴 때만
# 도니, 그쪽 prose로 만들면 다음 날 차트와 문장이 어긋난다. 재산정은 jr_ 키를 보존한다.
# jr_prd 는 차트 캡션의 기준월이다(백로그 17, 2026-09-17). 캡션에 손으로 적어 둔
# '2026.06 기준'이 값이 07로 넘어간 뒤에도 그대로 남아 있었다.
JR_KEYS = ('jr_seoul', 'jr_jnl', 'jr_mid', 'jr_prd')


def jratio_prose(lvl, prd):
    """전세가율 풀이 문장과 차트 캡션의 칸 값. 문장이 이름으로 부르는 지역에서만 뽑는다.

    prd 는 build_jratio 가 값을 읽은 바로 그 달이다. 값과 기준월을 같은 호출에서 받아야
    둘이 어긋나지 않는다.
    """
    if not re.match(r'^\d{4}\.\d{2}$', str(prd or '')):
        raise RuntimeError('전세가율 기준월을 읽지 못했다: %r' % (prd,))
    by = {x['region']: x['val'] for x in lvl}
    need = ('서울', '전남광주', '대구', '대전')
    gone = [r for r in need if r not in by]
    if gone:
        raise RuntimeError('전세가율 풀이 문장의 지역이 차트에 없다: %s' % ', '.join(gone))
    lo, hi = sorted((by['대구'], by['대전']))
    # '70%대'는 두 곳 값의 십의 자리(반올림 전 값의 내림)가 같을 때만 참이다. 갈리면 범위로 쓴다.
    # 반올림한 정수로 십 단위를 보면 69.6 이 '70%대'가 되고 70.9·79.6 이 '71~80%'가 됐다(전수 리뷰 #25).
    # 정수는 사이트 규칙(half-up, SZ.half_up)으로 만든다 — 파이썬 round() 는 52.5 를 52 로 내린다.
    if int(math.floor(lo)) // 10 == int(math.floor(hi)) // 10:
        mid = '%d%%대' % (int(math.floor(lo)) // 10 * 10)
    else:
        mid = '%d~%d%%' % (SZ.half_up(lo), SZ.half_up(hi))
    return {'jr_seoul': '%d' % SZ.half_up(by['서울']),
            'jr_jnl': '%d' % SZ.half_up(by['전남광주']),
            'jr_mid': mid,
            'jr_prd': SZ.month_text(prd)}   # 캡션은 읽는 자리 — '2026년 8월'(날짜 두 단계, 백로그 36-1)


# 참고 ④(멸실) 절 '왜 이것이 사슬과 겹치면 위험한가'의 서울 멸실 칸(전수리뷰 D3, 대표 결정 2026-10-05). 손으로 적은
# '2016~24년 준공 35만 호 중 멸실이 26.6만 호(76%)를 상쇄 … 2015~17년은 재고가 순감소'는 아파트 준공(STATS.준공)과
# **주택 전체** 멸실(STATS.주택멸실 — 단독·다세대 포함)을 견준 값이었다. 아파트끼리(STATS.아파트멸실 ÷ STATS.준공) 견주면
# 20% 안팎이고, 아파트는 어느 해도 멸실이 준공을 넘지 않았다. 그래서 비율은 아파트끼리로 쓰고, 주택 전체 멸실은 따로
# 이름을 달아 보조 지표로 적는다. 블로그 이론편(theory_link3._se_demol — 아파트 멸실 ÷ 아파트 인허가)도 같은 아파트
# 멸실 계열을 분자로 쓴다. 창은 멸실 계열의 마지막 해에서 DEMOL_YEARS 해(옛 문장의 2016~24 와 같은 길이)이고,
# 그 창에 준공이 열두 달 다 찬 해만 있어야 한다 — 모자라면 한 해씩 앞으로 당긴다(새 해 멸실이 준공보다 먼저 와도
# 배치를 멈추지 않는다).
DEMOL_YEARS = 9
DEMOL_REGION = '서울'
DM_KEYS = ('dm_span', 'dm_done', 'dm_apt', 'dm_apt_pct', 'dm_net_pct', 'dm_all')


def _man1(v):
    """호 → 만 호 소수 첫째 자리 글자(half-up). 69,969 → '7.0'."""
    return '%.1f' % (SZ.half_up(v / 1000.0) / 10.0)


def demol_prose(S, region=DEMOL_REGION, years=DEMOL_YEARS):
    """서울 아파트 준공 대비 아파트 멸실(비율)과 주택 전체 멸실(보조) 칸. 셀 수 없으면 RuntimeError."""
    am, hm, jg = S.get('아파트멸실'), S.get('주택멸실'), S.get('준공')
    if not (am and hm and jg):
        raise RuntimeError('멸실 칸의 재료(아파트멸실·주택멸실·준공)가 없다')

    def yearly(D):
        return {int(d[:4]): v for d, v in zip(D['dates'], D['series'].get(region) or []) if v is not None}
    apt, allh = yearly(am), yearly(hm)
    done, months = {}, {}
    for d, v in zip(jg['dates'], jg['series'].get(region) or []):
        p = ym(d)
        if p and v is not None:
            done[p[0]] = done.get(p[0], 0) + v
            months[p[0]] = months.get(p[0], 0) + 1
    if not apt or not allh:
        raise RuntimeError('%s 멸실 계열이 비었다' % region)
    y1 = min(max(apt), max(allh))
    while y1 - years + 1 >= min(apt):
        ys = range(y1 - years + 1, y1 + 1)
        if all(y in apt and y in allh and months.get(y) == 12 for y in ys):
            a, h, c = (sum(D[y] for y in ys) for D in (apt, allh, done))
            pct = SZ.half_up(100.0 * a / c)
            return {'dm_span': '%d~%d' % (ys[0], ys[-1]), 'dm_done': str(RC._man(c)), 'dm_apt': _man1(a),
                    'dm_apt_pct': str(pct), 'dm_net_pct': str(100 - pct), 'dm_all': _man1(h)}
        y1 -= 1
    raise RuntimeError('%s 멸실·준공이 %d년 내내 함께 찬 창이 없다' % (region, years))


def fill_spans(page, values):
    """본문의 <span data-d="키">를 values로 채운다. 칸이 하나도 없으면 멈춘다."""
    for k, v in values.items():
        pat = '<span data-d="%s">' % k
        if pat not in page:
            raise RuntimeError('사이클 본문에 %s 칸이 없다' % k)
        page = re.sub(r'<span data-d="%s">[^<]*</span>' % re.escape(k),
                      lambda m, v=v, k=k: '<span data-d="%s">%s</span>' % (k, v), page)
    return page


def splice(page, key, value):
    """const D={...} 안의 "key": <값> 하나를 통째로 갈아 끼운다."""
    i = page.find('"%s": ' % key)
    assert i >= 0, '%s 키를 못 찾음' % key
    start = i + len('"%s": ' % key)
    dec = json.JSONDecoder()
    _, end = dec.raw_decode(page[start:])
    return page[:start] + json.dumps(value, ensure_ascii=False) + page[start + end:]


def _strip_date(page):
    return re.sub(r'"dateModified":\s*"[^"]*"', '"dateModified": ""', page, count=1)


def _today_kst():
    # make_sido_pages 와 같은 출처(kst.py)를 쓴다. 따로 계산하면 한 배치 커밋 안에서 /cycle/ 과 /zone/·홈의
    # 날짜가 갈린다(2026-09-26 데이터 감사). 옛 utcnow() 는 3.12 에서 DeprecationWarning 도 냈다.
    return KST.today_iso()


def main():
    S = load_stats()
    page = io.open(PAGE, encoding='utf-8').read()

    SI = hold_index_breaks(S)
    if index_bases_agree(S):
        zones = build_zones(SI)
        overlay = build_overlay(SI)
    else:
        # 한 계열만 새 기준이면 두 지수를 겹친 차트는 어제 판을 둔다 — 다른 계열의 재수집이 끝나 기준이 같아지면 다시 굽는다.
        prev = json.loads(re.search(r'const D=(\{.*?\});\n', page, re.S).group(1))
        zones, overlay = prev['zones'], prev['rate_overlay']
        print('  ⚠️ 매매·전세지수 기준시점이 다르다(%s) — zones·rate_overlay 는 어제 판을 둔다(재수집 보류 중인 계열이 복구되면 다시 굽는다)'
              % ', '.join('%s %s' % (k, index_basis(S.get(k))) for k in RC.INDEX_KEYS))
    lvl, sudo_mean, jib_mean, prd = build_jratio(S)

    page = splice(page, 'zones', zones)
    page = splice(page, 'rate_overlay', overlay)
    page = splice(page, 'jratio_level', lvl)
    # 전세가율 풀이 칸 — 차트와 같은 값으로 D.prose와 본문을 함께 갱신한다
    m = re.search(r'const D=(\{.*?\});\n', page, re.S)
    cur = json.loads(m.group(1))
    prose = dict(cur.get('prose') or {})
    jr = jratio_prose(lvl, prd)
    # 같은 페이지 차트 데이터에서 바로 나오는 칸(종합 절 상·하위 지역, 멸실 절 수·연도, 자료 기간 — 전수 리뷰
    # #62·#66·#69). 손으로 적어 두면 차트와 문장이 갈렸다.
    jr.update(RC.page_prose(cur))
    jr.update(demol_prose(S))   # 참고 ④ 서울 멸실 칸 — data.js 의 아파트 준공·멸실에서(전수리뷰 D3)
    prose.update(jr)
    page = splice(page, 'prose', prose)
    page = fill_spans(page, jr)
    # 수도권·지방 평균은 페이지 어디서도 읽지 않아 D에서 뺐다. 배치 로그로는
    # 계속 남겨 두는 편이 갱신 결과를 눈으로 확인하는 데 쓸모가 있다.

    # 데이터 칸이 실제로 바뀐 회차에만 JSON-LD dateModified 와 sitemap lastmod 를 오늘(KST)로 올린다.
    # 둘 다 07-19·07-16 에 멈춰 있었다 — 매달 값이 바뀌는데 검색엔진엔 두 달째 그대로라고 말했다
    # (2026-09-23 점검, 백로그 29). 안 바뀐 날 날짜만 바꾸면 매일 커밋이 생기므로 비교 뒤에만 올린다.
    # 검색 로봇 메타(D2): 서술은 손 문서지만 <head> 한 줄은 여기서 넣는다(없을 때만). 비교는 옛 판에도 같은 줄을 넣은 뒤에
    # 한다 — 메타 한 줄 때문에 데이터가 그대로인 날 dateModified·sitemap lastmod 가 오늘로 올라가지 않게.
    page = RM.ensure(page)
    old = io.open(PAGE, encoding='utf-8').read()
    if _strip_date(page) != _strip_date(RM.ensure(old)):
        today = _today_kst()
        page = re.sub(r'("dateModified":\s*")[^"]*(")', r'\g<1>%s\g<2>' % today, page, count=1)
        I.bump_sitemap([('/cycle/', today)])
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(page)
    z0 = zones[ZONE_REGIONS[0]]
    print('cycle 갱신 (전세가율 기준 %s)' % prd)
    print('  zones      : %s · %d분기 (%.2f ~ %.2f)'
          % (' / '.join(zones), len(z0['t']), z0['t'][0], z0['t'][-1]))
    print('             수도권 매매 끝 %s · 전세 끝 %s' % (z0['maemae'][-1], z0['jeonse'][-1]))
    print('  rate_overlay: %d분기, 매매 끝 %s · 금리 끝 %s'
          % (len(overlay['t']), overlay['maemae'][-1], overlay['rate'][-1]))
    print('  jratio_level: %d개 시도, 수도권 평균 %s · 지방 평균 %s'
          % (len(lvl), sudo_mean, jib_mean))


if __name__ == '__main__':
    main()
