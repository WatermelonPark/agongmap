# -*- coding: utf-8 -*-
"""사이클 이론 5편(고리 ④ 착공 → 입주, 공사 기간이 늘어났다)의 숫자를 데이터에서 센다.

5편 본문(make_theory_post.POSTS n=5)의 %(키)s 자리는 render 가 채우는 링크·exp·nsido 를 빼고 전부 여기서
채운다. 사람이 센 수를 본문에 박지 않는다(CLAUDE.md 데이터 원칙). 계열은 사이트가 쓰는 것 그대로다:
sts['착공']·sts['준공'](국토교통부 주택건설 실적 중 아파트, 월별), adv['occupancy'](홈 공급표·/moveins/ 와 같은
분기 입주 추정: 과거는 준공 실적, 이후는 착공 × 전환율을 3년 뒤로), adv['sido'] 판정(zones 의 split·fut),
/cycle/ 의 정본 D(prose 의 lead_old·lead_new·lead_r).

공사 기간은 사이트 정본(D.prose)을 쓰고, 같은 계산 함수(rebuild_cycle_analysis.link45_leadtime)를 지금 데이터로
다시 돌려 정본과 같은지 assert 한다. 같은 대상을 재는 코드가 둘이 되지 않도록 시도별 시차도 그 모듈의 _roll12·
paired·corr 로 같은 방식(2018년 이후 착공분, 18~60개월)으로 잰다.

본문의 단정("두 해 만에 절반 아래로", "2019년 이후 가장 많았다", "3분의 1에도 못 미치는 곳은 …" 등)은 assert 로
고정한다. 데이터가 바뀌어 단정이 거짓이 되면 link4_numbers 가 Link4ClaimError 로 멈춘다 — 문장을 자동으로 갈아
끼우지 않는다(3편 check_sync_claims, 4편 theory_link3 와 같은 원칙: 그건 사람이 다시 쓸 글이다).

변이 확인(2026-09-27 검토 반영 후, 실제 2026.07 데이터를 복사해 한 값씩 바꿔 돌림 — 모두 Link4ClaimError 로 멈췄다):
대구 2023년 월 착공 5,000호 → dg_st, 2025년 전국 준공 40% 감소 → dn25(예전 시차 추정의 1.3배 미만),
occupancy 2027Q4 50,000 → fq_n(사이트 fut 합과 불일치), 2029Q1·Q2 추정을 80,000으로(fut 도 맞춰 올림) → h29p,
서울 fut/need 0.4 → fut_low, 2026년 착공 20% 감소 → st_ytd_up, D.prose lead_new 36 → lead_new(재계산 37과 불일치),
2024년 12월 전국 준공 절반 → lead_new(재계산 시차가 36으로 바뀜). 시차 계산이 ValueError 로 깨지면 그것도 Link4ClaimError 다.
픽스처는 따로 없다: 배치가 구운 실제 data.js·cycle/index.html 을 그대로 읽는다.
표준 라이브러리와 저장소 모듈만 쓴다.
"""
import inspect
import io
import json
import os
import re

import rebuild_cycle_analysis as RC
import sido_zones as SZ

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SZ.__file__)))   # tools/ 의 부모 = 저장소 뿌리


class Link4ClaimError(Exception):
    """5편 본문의 단정이 데이터와 어긋난다."""


def _won(n):
    return format(int(round(n)), ',')


def min_window(rows, start, n=4, col=0):
    """입주 계열(adv['occupancy']['rows'] — 과거는 준공 실적, 이후는 추정)에서 분기 start 부터 끝까지, 연속한 n 분기 합이
    가장 작은 구간 → (첫 분기, 끝 분기, 합). 합이 같으면 앞 구간.

    ⚠️ 추정 분기(EST)만 훑지 않는다. 바로 앞 문단의 '올해 입주'(OY)는 실적 두 분기 + 추정 두 분기를 더한 같은 계열인데,
    추정 분기만 훑으면 올해(215,877호·57%)보다 큰 2028년 1~4분기(231,328호·61%)가 '가장 적은 구간'으로 나와 두 문장이
    서로 어긋났다(2026-10-05 리뷰 D5, 2026.08 데이터). 그래서 OY 와 같은 계열을 올해 1분기부터 훑는다 — 사이트 정본
    (홈 공급표·/moveins/)도 실적과 추정을 한 계열로 잇는다.
    """
    rs = [r for r in rows if r['p'] >= start]
    if len(rs) < n:
        raise ValueError('%s 부터 %d분기가 안 된다' % (start, n))
    w = [(sum(r['v'][col] for r in rs[i:i + n]), i) for i in range(len(rs) - n + 1)]
    v, i = min(w)
    return rs[i]['p'], rs[i + n - 1]['p'], v


def link4_numbers(adv, sts):
    """5편 본문 자리 표시자 → 값(문자열). 단정이 깨지면 Link4ClaimError."""
    ST, DN = sts['착공'], sts['준공']

    def MON(key, rg):                 # 'YYYY.MM' → 월 값(잠정 표시 'p)'는 뗀다)
        c = sts[key]
        return {d.split()[0][:7]: (v or 0) for d, v in zip(c['dates'], c['series'][rg])}

    def Y(key, rg, y):                # 그해 합. 열두 달이 다 있어야 한다
        m = MON(key, rg)
        ks = ['%d.%02d' % (y, i) for i in range(1, 13)]
        assert all(k in m for k in ks), (key, rg, y)
        return sum(m[k] for k in ks)

    def HF(key, rg, y, h):            # 반기 합(h=1 상반기, 2 하반기)
        m = MON(key, rg)
        ks = ['%d.%02d' % (y, i) for i in (range(1, 7) if h == 1 else range(7, 13))]
        assert all(k in m for k in ks), (key, rg, y, h)
        return sum(m[k] for k in ks)

    last_m = max(MON('준공', '전국'))             # 준공 계열의 마지막 달
    assert last_m == max(MON('착공', '전국')), '착공·준공 마지막 달이 다르다'
    CUR_Y, CUR_M = int(last_m[:4]), int(last_m[5:7])
    if CUR_Y != 2026:                             # 본문 '지난해 하반기'(2025H2)·'올해'가 2026년 발행을 전제한다
        raise Link4ClaimError('5편 본문은 2026년 데이터를 전제한다(지난해 하반기=2025) — 지금 %s' % last_m)

    def YTD(key, rg, y):              # 그해 1월~CUR_M월 합
        m = MON(key, rg)
        return sum(m.get('%d.%02d' % (y, i), 0) for i in range(1, CUR_M + 1))

    D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});', io.open(
        os.path.join(ROOT, 'cycle', 'index.html'), encoding='utf-8').read(), re.S).group(1))
    PR = D['prose']

    try:
        _l4, LEAD = RC.link45_leadtime(sts)
    except (ValueError, KeyError) as e:
        raise Link4ClaimError('착공→준공 시차를 다시 잴 수 없다 — %s' % e)

    def LG(rg, lo='2018.01', hi='9999'):  # 시도 시차: 사이트 link45_leadtime 의 peak 와 같은 계산
        s = RC._roll12(ST['series'][rg], ST['dates'])
        d = RC._roll12(DN['series'][rg], DN['dates'])
        s = {k: v for k, v in s.items() if lo <= k < hi}
        c = [(RC.corr(*RC.paired(s, d, L, shift=RC._mshift))[0], L) for L in range(18, 61)]
        c = [x for x in c if x[0] == x[0]]
        return max(c)                 # (상관, 개월)

    O = adv['occupancy']
    OR = O['regions']
    SD = adv['sido']
    EST = [r for r in O['rows'] if r['p'] > SD['L']]   # 착공으로 추정한 앞으로의 분기

    def Z(z):
        return next(x for x in SD['zones'] if x['z'] == z)

    def FUT(z):                       # 판정 split 의 '앞으로 3년' 퍼센트(사이트 정본)
        r = Z(z)['split']['rows'][1]
        assert r[0] == '앞으로 3년', z
        return int(re.search(r'(\d+)%', r[1]).group(1))

    def FR(z):                        # 앞으로 3년 들어올 물량 / 적정물량 원값(정렬·문턱용, 반올림 전)
        return Z(z)['fut'] / Z(z)['need']

    SIDO = [z['z'] for z in SD['zones'] if not z.get('agg')]

    def OY(rg, y):                    # 입주 추정(과거 실적 + 이후 추정) 그해 네 분기 합
        rs = [r for r in O['rows'] if r['p'][:4] == str(y)]
        assert len(rs) == 4, (rg, y)
        return sum(r['v'][OR.index(rg)] for r in rs)

    def OLD25():
        st = MON('착공', '전국')
        L = int(PR['lead_old'])
        ks = []
        for i in range(1, 13):
            t = 2025 * 12 + i - 1 - L
            ks.append('%d.%02d' % (t // 12, t % 12 + 1))
        assert all(k in st for k in ks)
        return sum(st[k] for k in ks) * SD['conv']

    def MIN4():
        # 올해 1분기부터 끝까지(실적 + 추정) — '올해 입주'(OY)와 같은 계열. min_window docstring.
        return min_window(O['rows'], '%dQ1' % CUR_Y)

    # ---------- 공사 기간(고리 ④) ----------

    def _lead_old():
        # 사이트 정본 착공→준공 시차(2011~2017 착공분, 개월). 같은 함수로 지금 데이터에서 다시 잰 값과 같아야 한다
        assert str(LEAD['old_months']) == PR['lead_old'], (LEAD['old_months'], PR['lead_old'])
        return PR['lead_old']

    def _lead_new():
        # 사이트 정본 시차(2018년 이후 착공분). 재계산 일치 + '늘었다' 단정
        assert str(LEAD['new_months']) == PR['lead_new'], (LEAD['new_months'], PR['lead_new'])
        assert int(PR['lead_new']) > int(PR['lead_old'])
        return PR['lead_new']

    def _lead_old_y():
        # 사이트 정본 '2년 남짓'
        return PR['lead_old_y']

    def _lead_new_y():
        # 사이트 정본 '3년 남짓'. 본문 '앞으로 3년'·'3년 남짓 뒤' 계산이 이 값의 년 내림(3)을 전제
        assert int(PR['lead_new']) // 12 == SZ.LEAD_Q // 4 == SD['lead'] // 4, (PR['lead_new'], SZ.LEAD_Q, SD['lead'])
        return PR['lead_new_y']

    def _lead_gap():
        # 늘어난 개월 수(본문 '늘어난 9개월')
        return str(int(PR['lead_new']) - int(PR['lead_old']))

    def _lead_r():
        # 사이트 정본 착공→준공 전체 기간 상관. '여섯 고리 가운데 가장 단단하다'를 다른 고리 정본 값보다 크다로 고정
        v = float(PR['lead_r'])
        assert abs(LEAD['all_r'] - v) < 0.006
        others = [PR['l4_r'], PR['sync_mean'], PR['l3_mean'], PR['l6_mean'], PR['l1_r'], PR['rate_r']]
        assert all(v > abs(float(x.replace('−', '-'))) for x in others), others
        return PR['lead_r']

    def _nat_r():
        # 2018년 이후 착공분 전국 시차 상관(서울과 견주는 기준)
        return '%.2f' % LEAD['new_r']

    def _sd_old():
        # 수도권 시차 2011~2017 착공분
        return str(LG('수도권', '0000', '2018.01')[1])

    def _sd_new():
        # 수도권 시차 2018년 이후. '늘었다' assert
        assert LG('수도권')[1] > LG('수도권', '0000', '2018.01')[1]
        return str(LG('수도권')[1])

    def _jb_old():
        # 지방 시차 2011~2017 착공분
        return str(LG('지방', '0000', '2018.01')[1])

    def _jb_new():
        # 지방 시차 2018년 이후. '늘었다' assert
        assert LG('지방')[1] > LG('지방', '0000', '2018.01')[1]
        return str(LG('지방')[1])

    def _cn_lead():
        # 충남 시차(2018년 이후). '짧은 곳도 있다': 전국보다 짧고 맞물림이 단단(상관 0.8 이상). 택지 인과는 쓰지 않는다(세종 38개월 반례)
        r, L = LG('충남')
        assert L < LEAD['new_months'] and r >= 0.8, (r, L)
        return str(L)

    def _gb_lead():
        # 경북 시차(2018년 이후). 충남과 같은 단정
        r, L = LG('경북')
        assert L < LEAD['new_months'] and r >= 0.8, (r, L)
        return str(L)

    def _se_r():
        # 서울 착공→준공 상관(2018년 이후). '전국보다 훨씬 낮아 입주 시점을 가늠하기 어렵다' = 0.2 이상 낮다
        r = LG('서울')[0]
        assert r < LEAD['new_r'] - 0.2, (r, LEAD['new_r'])
        return '%.2f' % r

    # ---------- 늘어난 시차가 가린 것 ----------

    def _st21():
        # 전국 아파트 착공 2021년
        return _won(Y('착공', '전국', 2021))

    def _st22():
        # 전국 아파트 착공 2022년
        return _won(Y('착공', '전국', 2022))

    def _st23():
        # 전국 아파트 착공 2023년. '두 해 만에 절반 아래로'
        assert Y('착공', '전국', 2023) < Y('착공', '전국', 2021) / 2
        return _won(Y('착공', '전국', 2023))

    def _st_pk():
        # 차트 설명: 2011~2021년 가운데 전국 착공이 가장 많았던 해
        return str(max(range(2011, 2022), key=lambda y: Y('착공', '전국', y)))

    def _dn_pk():
        # 차트 설명: 2011~2021년 가운데 전국 준공이 가장 많았던 해. '착공 정점 뒤'(d > s)를 assert,
        # '2022년에 꺾인 착공은 3년 뒤 준공 감소로'(2025 준공 < 2024 준공)도 함께 고정
        s = max(range(2011, 2022), key=lambda y: Y('착공', '전국', y))
        d = max(range(2011, 2022), key=lambda y: Y('준공', '전국', y))
        assert d > s, (s, d)
        assert Y('착공', '전국', 2022) < Y('착공', '전국', 2021) and Y('준공', '전국', 2025) < Y('준공', '전국', 2024)
        return str(d)

    def _h1_24():
        # 전국 준공 2024년 상반기
        return _won(HF('준공', '전국', 2024, 1))

    def _h1_25():
        # 전국 준공 2025년 상반기. '한 해 전보다 많았다'
        assert HF('준공', '전국', 2025, 1) > HF('준공', '전국', 2024, 1)
        return _won(HF('준공', '전국', 2025, 1))

    def _h2_24():
        # 전국 준공 2024년 하반기
        return _won(HF('준공', '전국', 2024, 2))

    def _h2_25():
        # 전국 준공 2025년 하반기
        return _won(HF('준공', '전국', 2025, 2))

    def _h2_drop():
        # 2025 하반기 준공이 2024 하반기보다 적은 비율. 본문 '감소는 그다음에 왔다'를 30% 넘는 감소로 고정
        q = 1 - HF('준공', '전국', 2025, 2) / HF('준공', '전국', 2024, 2)
        assert q > 0.3, q
        return '%.0f%%' % (q * 100)

    # ---------- 지금 ----------

    def _roll_from():
        # 최근 12개월 시작 달
        t = CUR_Y * 12 + CUR_M - 1 - 11
        return '%d년 %d월' % (t // 12, t % 12 + 1)

    def _roll_to():
        # 최근 12개월 끝 달(준공 계열 마지막 달)
        return '%d년 %d월' % (CUR_Y, CUR_M)

    def _roll_now():
        # 전국 준공 최근 12개월 합
        return _won(RC._roll12(DN['series']['전국'], DN['dates'])[last_m])

    def _roll_prev():
        # 그 앞 12개월 합
        return _won(RC._roll12(DN['series']['전국'], DN['dates'])['%d.%02d' % (CUR_Y - 1, CUR_M)])

    def _roll_ratio():
        # 최근 12개월 / 그 앞 12개월. 본문 '감소가 지금 시작됐다'를 0.7 아래로 고정
        r = RC._roll12(DN['series']['전국'], DN['dates'])
        q = r[last_m] / r['%d.%02d' % (CUR_Y - 1, CUR_M)]
        assert q < 0.7, q
        return '%.0f%%' % (q * 100)

    def _ytd_m():
        # 올해 집계 마지막 달(월)
        return str(CUR_M)

    def _dn_ytd():
        # 올해 1~CUR_M월 전국 준공
        return _won(YTD('준공', '전국', CUR_Y))

    def _dn_ytd_since():
        # 올해 1~CUR_M월 준공보다 적었던 마지막 해('~년 이후 같은 기간 가운데 가장 적다')
        c = YTD('준공', '전국', CUR_Y)
        y = max(y for y in range(2011, CUR_Y) if YTD('준공', '전국', y) < c)
        assert all(YTD('준공', '전국', k) > c for k in range(y + 1, CUR_Y))
        return str(y)

    # ---------- 앞으로 3년 ----------

    def _ref_y():
        # 전국 연간 적정물량(분기 적정 × 4, 사이트 정본)
        return _won(O['ref']['전국'] * 4)

    def _ref_q():
        # 전국 분기 적정물량
        return _won(O['ref']['전국'])

    def _conv():
        # 착공→준공 전환율(사이트 정본)
        return '%.3f' % SD['conv']

    def _y26():
        # 입주 추정 2026년(실적 두 분기 + 추정 두 분기)
        return _won(OY('전국', 2026))

    def _y26p():
        # 2026년 / 연 적정. 본문 '세 해 모두 적정의 7할에 못 미친다'
        q = OY('전국', 2026) / (O['ref']['전국'] * 4)
        assert q < 0.7
        return '%.0f%%' % (q * 100)

    def _y27():
        # 입주 추정 2027년
        return _won(OY('전국', 2027))

    def _y27p():
        # 2027년 / 연 적정
        q = OY('전국', 2027) / (O['ref']['전국'] * 4)
        assert q < 0.7
        return '%.0f%%' % (q * 100)

    def _fq_n():
        # 추정 분기 수. 판정 창(H)과 같고, 합이 사이트 판정의 '앞으로 3년 들어올 물량'(전국 fut)과 같아야 한다
        assert len(EST) == SD['H']
        assert abs(sum(r['v'][0] for r in EST) - Z('전국')['fut']) < 1
        return str(len(EST))

    def _fq_below():
        # 추정 분기 가운데 분기 적정에 못 미치는 분기 수. '대부분'이 서도록 3분의 2 이상
        n = sum(1 for r in EST if r['v'][0] < O['ref']['전국'])
        assert n >= len(EST) * 2 / 3
        return str(n)

    def _st_ytd():
        # 올해 1~CUR_M월 전국 착공
        return _won(YTD('착공', '전국', CUR_Y))

    def _st_ytd_up():
        # 올해 착공이 한 해 전 같은 기간보다 늘어난 비율. '다시 늘고 있다' assert
        q = YTD('착공', '전국', CUR_Y) / YTD('착공', '전국', CUR_Y - 1) - 1
        assert q > 0, q
        return '%.0f%%' % (q * 100)

    def _arr_y():
        # 올해 착공분이 입주하기 시작하는 해: 올해 1월 + 사이트 시차
        t = CUR_Y * 12 + int(PR['lead_new'])
        return str(t // 12)

    def _fut_low_n():
        # 앞으로 3년 적정물량의 3분의 1에도 못 미치는 시도 수
        return str(sum(1 for z in SIDO if FR(z) < 1 / 3))

    def _dn25_old():
        # 예전 시차(lead_old 개월)로 셈한 2025년 준공: 그 시차만큼 앞선 12개월 착공 × 전환율
        return _won(OLD25())

    def _dn25():
        # 실제 2025년 전국 준공. '예전 시차라면 2025년에 드러났어야 했는데 실제는 훨씬 많았다' = 1.3배 넘게
        assert Y('준공', '전국', 2025) > OLD25() * 1.3, (Y('준공', '전국', 2025), OLD25())
        return _won(Y('준공', '전국', 2025))

    def _h29p():
        # 2029년 상반기(올해 늘어난 착공분이 입주하는 반기) 입주 추정 / 두 분기 적정. '그때도 적정의 7할 미만'
        ay = (CUR_Y * 12 + int(PR['lead_new'])) // 12          # 본문 arr_y 와 같은 해
        rs = [r for r in EST if r['p'] in ('%dQ1' % ay, '%dQ2' % ay)]
        assert len(rs) == 2, [r['p'] for r in rs]
        q = sum(r['v'][0] for r in rs) / (O['ref']['전국'] * 2)
        assert q < 0.7, q
        return '%.0f%%' % (q * 100)

    def _fq_min4():
        # 올해 1분기부터(실적 + 추정, OY 와 같은 계열 — min_window) 연속한 네 분기 가운데 가장 적은 구간의 이름.
        # 세 해 모두 7할 미만 단정(2028년)도 여기서 고정
        assert OY('전국', 2028) / (O['ref']['전국'] * 4) < 0.7
        a, b, _ = MIN4()
        return '%s년 %s분기~%s년 %s분기' % (a[:4], a[-1], b[:4], b[-1]) if a[:4] != b[:4] else '%s년 %s~%s분기' % (a[:4], a[-1], b[-1])

    def _fq_min4v():
        # 그 구간 합
        return _won(MIN4()[2])

    def _fq_min4p():
        # 그 구간 / 네 분기 적정
        return '%.0f%%' % (MIN4()[2] / (O['ref']['전국'] * 4) * 100)

    def _win_y():
        # 판정 창(앞으로 N년) = H 분기 / 4. 본문 '앞으로 N년'
        assert SD['H'] % 4 == 0
        return str(SD['H'] // 4)

    def _shift_y():
        # 입주 추정이 착공을 옮기는 햇수 = 모델 lead 분기 / 4(=LEAD_Q). 본문 '착공을 N년 뒤로'
        assert SD['lead'] == SZ.LEAD_Q and SD['lead'] % 4 == 0
        return str(SD['lead'] // 4)

    def _shift_q():
        # 같은 값의 분기 수(방법론 '분기 단위라 N분기로 옮겼다')
        return str(SD['lead'])

    def _lag_lo():
        # 시차 탐색 하한(개월). 사이트 계산 함수의 범위와 같아야 한다 — 소스에서 확인
        assert 'range(18, 61)' in inspect.getsource(RC.link45_leadtime)
        return '18'

    def _lag_hi():
        # 시차 탐색 상한(개월)
        assert 'range(18, 61)' in inspect.getsource(RC.link45_leadtime)
        return '60'

    def _fut_low():
        # 그 시도들(낮은 순). 본문이 서울을 따로 이어 쓰므로 서울 포함을 assert, 목록이 바뀌면 멈춘다
        lo = sorted([z for z in SIDO if FR(z) < 1 / 3], key=FR)
        assert set(lo) == {'대구', '제주', '서울', '경북'}, lo
        return ', '.join('%s %d%%' % (z, FUT(z)) for z in lo)

    def _fut_high():
        # 적정물량을 넘는 물량이 들어오는 시도. 목록이 바뀌면 멈춘다
        hi = sorted([z for z in SIDO if FR(z) > 1], key=lambda z: -FR(z))
        assert set(hi) == {'대전', '충남'}, hi
        return ', '.join('%s %d%%' % (z, FUT(z)) for z in hi)

    def _fut_high_names():
        # 6편 연결 문장용 이름만('대전·충남'). fut_high 와 같은 규칙
        return '·'.join(sorted([z for z in SIDO if FR(z) > 1], key=lambda z: -FR(z)))

    def _gg_fut():
        # 경기 앞으로 3년 / 적정물량. '서울과 달리 적정물량 가까이' = 80% 이상
        assert FUT('경기') >= 80
        return '%d%%' % FUT('경기')

    def _ic_fut():
        # 인천 앞으로 3년 / 적정물량
        assert FUT('인천') >= 80
        return '%d%%' % FUT('인천')

    def _dg_st():
        # 대구 착공 2023~2025 연평균. '미분양이 불어난 뒤 착공을 크게 줄였다' = 2016~2021 연평균의 절반 아래
        new = sum(Y('착공', '대구', y) for y in (2023, 2024, 2025)) / 3
        old = sum(Y('착공', '대구', y) for y in range(2016, 2022)) / 6
        assert new < old / 2, (new, old)
        return _won(new)

    def _dg_st_old():
        # 대구 착공 2016~2021 연평균
        return _won(sum(Y('착공', '대구', y) for y in range(2016, 2022)) / 6)

    out = {}
    for k, f in sorted((k[1:], f) for k, f in locals().items() if k.startswith('_') and callable(f)):
        try:
            out[k] = f()
        except (AssertionError, ValueError, StopIteration) as e:
            raise Link4ClaimError('5편 본문의 단정이 데이터와 어긋난다 — %s: %s' % (k, e))
    return out
