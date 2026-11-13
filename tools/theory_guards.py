# -*- coding: utf-8 -*-
"""사이클 이론편(1~7편) 문장 전제 가드 — 발행본이 못 박은 전제가 지금 데이터와 맞는지 본다.

블로그 초안 도구(주간·지역·이론·도시·월간 초안과 검색 순위·유사도·방문 수 도구)는 2026-11-13 대표 결정('가드만 살리고
정리')으로 지웠다(코드는 git 이력에 있다). 그 가운데 살아 있는 코드가 읽는 것은 이 가드 하나다 — 배치 기록(batch_notes.theory_claim_lines)이 편마다
guard_values 를 돌려, 전제가 깨진 편을 ℹ️ 한 줄로 알린다(게이트는 막지 않는다, 대표 결정 2026-10-18 D1). 여기에는 그 셈과
멈춤 문구만 옮겼다 — 본문 HTML·링크는 없다. 멈춤 문구는 옮기기 전과 한 글자도 다르지 않다(batch_notes 가 _STOP_HEAD·_STOP_TAIL
로 머리·꼬리를 떼어 읽는다).

  1·2편 고리①(link1_values·permit_over_x), 3편 동조성(check_sync_claims), 4편 theory_link3, 5편 theory_link4,
  6편 link6_values, 7편 link7_values.

표준 라이브러리만 쓴다(배치·감시처럼 설치 없이 돈다 — ci-tests 의 설치 없이 도는 진입점 batch_notes 가 이 모듈을 부른다).
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sido_pages as M  # noqa: E402  (data.js 읽기 정본 M.load)
import rebuild_cycle_analysis as RC  # noqa: E402  (6편 반응 시차·유의 문턱·조사 받침의 정본)
import sido_zones as SZ      # noqa: E402
import theory_link3 as L3    # noqa: E402  (4편 숫자·단정)
import theory_link4 as L4    # noqa: E402  (5편 숫자·단정, 6편과 함께 쓰는 앞으로 입주 목록)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 가드를 돌리는 편 번호. 1·2편은 고리① 전제 하나를 함께 쓴다(batch_notes 가 같은 이유로 멈춘 이웃 편을 한 줄로 묶는다).
POSTS = (1, 2, 3, 4, 5, 6, 7)

# 이론편 본문에 보이는 지역 이름(정본 theory_link3.SEARCH_NAME — 화면 이름 정본 + '세종시'). 멈춤 문구 속 지역 이름(6편 '가장 강한
# 시도(…)')도 이 표다.
SEARCH_NAME = L3.SEARCH_NAME

# 문장 전제가 깨진 게 아니라 데이터 상태(입력 계열이 끊겼다·덜 찼다·칸을 못 읽는다)로 멈출 때 멈춤 문구에 넣는 말.
# 배치 기록(batch_notes.theory_claim_lines)이 이 말로 그 편을 '전제가 어긋남 — 발행본 재검토'가 아니라 '데이터 상태' 줄로 가른다 —
# 멈춤 문구와 판별이 이 상수 하나를 쓴다(4편 지수 기준 단절, 5편 착공·준공 끝 달 어긋남, 6편 판정 칸, 7편 금리 오버레이 빈 분기).
NOT_THE_TEXT = '문장 탓이 아니다'


def cycle_d():
    """`/cycle/` 의 정본 const D 전체(sync·link1_new·prose …). 가드는 숫자를 여기서 읽는다(전수리뷰 #76·#77)."""
    p = os.path.join(ROOT, 'cycle', 'index.html')
    m = re.search(r'const D\s*=\s*(\{.*?\});',
                  io.open(p, encoding='utf-8').read(), re.S)
    if not m:
        raise RuntimeError('/cycle/ 에서 D 블록을 찾지 못했다 — 곳 수를 못 맞춘다')
    return json.loads(m.group(1))


def _cycle_sync():
    """`/cycle/` 의 const D 에서 sync 목록을 읽는다(동조성 큰 순). [{region, corr, sudo}, …] — 숫자를 박지 않고 읽어 온다."""
    return sorted(cycle_d()['sync'], key=lambda r: -r['corr'])


# 사이트 /cycle/ 고리②(전세→매매) 검증 결과의 정본.
CYCLE_SYNC = _cycle_sync()
CYCLE_SYNC_N = len(CYCLE_SYNC)

SYNC_LOW_REGION = '서울'     # 3편 "서울은 왜 다른가" 절이 전제하는 최저 지역


def check_sync_claims(rows=None):
    """3편의 문장이 데이터와 맞는지 본다. 어긋나면 SystemExit 로 멈춘다(2026-09-16 리뷰 16번).

    3편은 두 가지를 문장으로 못 박고 있다.
      ① 제목·본문 "N개 시도에서 예외가 없었습니다" — 동조성이 **전부 양수**일 때만 참이다.
      ② "서울은 왜 다른가" 절 — 값은 최저 지역에서 읽는데 설명은 서울 고유의 논리(전세와 무관한 투자 수요)다. 재산정으로
         최저 지역이 바뀌면 다른 지역의 값을 서울 이름으로 말하게 된다.
    문장을 데이터에 맞춰 갈아 끼우지 않는다 — 최저가 대구라면 "왜 다른가"의 설명 자체가 틀린다. 사람이 다시 볼 일이다.
    """
    r = CYCLE_SYNC if rows is None else rows
    neg = [x['region'] for x in r if x['corr'] <= 0]
    if neg:
        raise SystemExit('3편을 만들 수 없다 — 동조성이 0 이하인 곳이 있다(%s). 제목과 본문의 '
                         '"예외가 없었습니다"가 거짓이 된다. 문장을 먼저 고칠 것.' % '·'.join(neg))
    low = min(r, key=lambda x: x['corr'])['region']
    if low != SYNC_LOW_REGION:
        raise SystemExit('3편을 만들 수 없다 — 동조성 최저 지역이 %s이 아니라 %s다. "서울은 왜 '
                         '다른가" 절은 서울 고유의 설명이라 그대로 쓸 수 없다. 절을 다시 쓸 것.'
                         % (SYNC_LOW_REGION, low))


def permit_over_x(sts):
    """1편 '인허가는 같은 해 착공보다 N배쯤 많고'의 N — 시도 리포트가 같은 사실을 굽는 정본 SZ.permit_over_start_pct('N%쯤')를 배수로
    쓴 것(15 → '1.15'). 잴 수 없으면 데이터 상태로 멈춘다."""
    pct = SZ.permit_over_start_pct(sts)
    if pct is None:
        raise SystemExit('1편을 만들 수 없다 — 전국 인허가·착공으로 인허가가 착공보다 얼마나 많은지 잴 수 없다. %s — 통계 계열이 찬 뒤 '
                         '다시 돌린다.' % NOT_THE_TEXT)
    if pct <= 0:
        # '착공보다 N배쯤 많고'는 인허가가 착공보다 많을 때만 참이다 — 0·음수면 '1배'·'0.9배쯤 많고'가 나간다
        raise SystemExit('1편을 만들 수 없다 — 전국 인허가가 착공보다 많지 않다(정본 %s%%) — 1편 문장의 전제가 깨졌다. %s'
                         % (pct, NOT_THE_TEXT))
    return ('%.2f' % (1 + pct / 100.0)).rstrip('0').rstrip('.')


def link1_values(D=None):
    """1·2편 고리① 숫자와 방향 문구 — /cycle/ 정본 D(prose·link1_new)에서 읽는다(전수리뷰 #76, 대표 결정 ⑥).

    숫자는 사이트가 찍는 문자열(prose.l1_lo·l1_hi) 그대로, 방향 문구는 그 두 값에서 고른다. 공급이 적은 구간이 많은 구간보다
    높지 않으면 1·2편의 전제가 무너지므로 멈춘다(3편 check_sync_claims 와 같은 원칙). l1_mid 는 2편 '가운데가 가장 높은 이유'
    절이 설 수 있는지(세 구간 가운데 '보통'이 가장 높은지)다 — 서지 않아도 멈추지 않는다(그 절을 빼면 되는 일, 전수리뷰 #76).
    """
    D = cycle_d() if D is None else D
    pr, rise = D['prose'], D['link1_new']['jeonse_rise']
    lo, hi = (float(pr[k].replace('−', '-')) for k in ('l1_lo', 'l1_hi'))
    if not rise[0] > rise[-1] or not lo > hi:
        raise SystemExit('1·2편을 만들 수 없다 — 고리① 전제(공급이 적은 분기의 전세 상승률 > 많은 분기)가 /cycle/ '
                         '정본과 어긋난다(%s). 문장을 먼저 고칠 것.' % ' · '.join('%g' % x for x in rise))
    if hi < 0:
        d = '하락으로 돌아섭니다.'
    elif hi == 0:
        d = '상승이 멈춥니다.'
    elif hi <= lo / 2:
        d = '절반 이하로 떨어집니다.'
    else:
        d = '상승 폭이 줄어듭니다.'
    mid_ok = rise[1] > rise[0] and rise[1] > rise[-1]
    return dict(l1_lo=pr['l1_lo'], l1_hi=pr['l1_hi'], l1_dir=d, l1_mid=mid_ok)


def link6_values(D, adv):
    """6편 숫자 — /cycle/ 정본(D.prose·D.link6_regional)과 앞으로 입주 목록(theory_link4.fut_lists — 5편과 같은 규칙)에서 읽는다.
    문장의 전제가 깨지면 멈춘다(3편 check_sync_claims 와 같은 원칙). 전제: ① 서울은 효과가 확인되지 않는다, ② 수도권으로 묶으면
    서울보다 강하다, ③ 광역시가 도보다 강하다, ④ 확인된 수도권 시도는 모두 한 분기 뒤 반응, ⑤ 가장 강한 시도가 앞으로 입주가
    적정물량을 넘는 곳이다, ⑥ 앞으로 입주가 적정물량을 넘는 시도가 있다, ⑦ 앞으로 입주가 적정물량의 3분의 1에도 못 미치는 시도가
    있다('가장 적은 곳은 …'), ⑧ 적정물량에 못 미치는 시도가 대부분이다('대부분 지역에서 적정물량에 못 미치는데요' — 5편 '대부분'과
    같은 문턱 L4.MOST).
    5편의 단정(link4_numbers — 약 60개)에는 묶지 않는다. 6편 본문이 5편에서 읽는 값은 앞으로 입주 목록 넷뿐이고, 5편은 발행본이라
    '5편 문장을 고치라'는 안내를 따를 수도 없다(전수리뷰 BL2-4)."""
    pr, rg = D['prose'], D['link6_regional']
    num = lambda s: float(s.replace('−', '-'))
    sig = [x for x in rg if x['sig']]
    sudo = [x for x in sig if x['zone'] == '수도권']
    top = sorted(rg, key=lambda x: x['r'])
    nm = lambda z: SEARCH_NAME.get(z, z)
    try:
        F = L4.fut_lists(adv, name=nm)
    except L4.Link4ClaimError as e:
        # 판정 칸(ADV.sido)을 못 읽는 회차 — 문장 탓이 아니다. 데이터 상태 줄로 가른다(대표 결정 2026-10-18 D1).
        raise SystemExit('6편을 만들 수 없다 — %s. %s — 판정 칸을 읽을 수 있는 데이터로 다시 돌린다.' % (e, NOT_THE_TEXT))
    high = F['hi']
    # 본문의 유의 문턱 '%(sig_pct)s%%'는 재산정 정본 RC.SIG_P 에서 읽는다(전수리뷰 BL2-14). D 는 p 를 싣지 않아(SHIP_FIELDS,
    # 전수리뷰 C-11) sig 가 지금 문턱으로 구운 것인지는 여기서 대조하지 않는다 — SIG_P 를 바꾸면 재산정(--write)으로 D 를 함께 굽는다.
    bad = []
    if any(x['region'] == '서울' and x['sig'] for x in rg):
        bad.append('서울이 유의로 나온다')
    if not num(pr['sudo_l6']) < num(pr['seoul_l6']):
        bad.append('수도권으로 묶어도 서울보다 강하지 않다')
    if not num(pr['l6_metro']) < num(pr['l6_prov']):
        bad.append('광역시가 도보다 강하지 않다')
    if not sudo or any(x['lag'] != 1 for x in sudo):
        bad.append('수도권 확인 시도가 없거나 같은 분기 반응 시도가 있다')
    if not high:
        bad.append('앞으로 입주가 적정물량을 넘는 시도가 없다')
    elif top[0]['region'] not in high:
        bad.append('가장 강한 시도(%s)가 앞으로 입주가 적정물량을 넘는 곳이 아니다' % nm(top[0]['region']))
    if not F['lo']:
        bad.append('앞으로 입주가 적정물량의 3분의 1에도 못 미치는 시도가 없다')
    if F['below'] < F['n'] * L4.MOST:
        bad.append('앞으로 입주가 적정물량에 못 미치는 시도가 대부분이 아니다(%d/%d곳)' % (F['below'], F['n']))
    if bad:
        raise SystemExit('6편을 만들 수 없다 — %s. 6편 문장을 먼저 고칠 것.' % ' · '.join(bad))
    eunneun = lambda w: w + ('은' if RC._jong(w) else '는')
    lag = RC.link6_lag_prose(rg)
    return dict(fut_high=F['fut_high'], fut_high_names=F['fut_high_names'], fut_low=F['fut_low'], win_y=F['win_y'],
                l6_total=pr['l6_total'], l6_sig=pr['l6_sig'], l6_metro=pr['l6_metro'], l6_prov=pr['l6_prov'],
                seoul_l6=pr['seoul_l6'], sudo_l6=pr['sudo_l6'], rate_r=pr['rate_r'], sig_pct='%d' % round(RC.SIG_P * 100),
                l6_top3='·'.join(nm(x['region']) for x in top[:3]), l6_top1=eunneun(nm(top[0]['region'])),
                l6_sudo_sig=eunneun('·'.join(nm(x['region']) for x in sudo)),
                # 지방 유의·즉시·한 분기 뒤 수는 /cycle/ 고리⑥ 캡션 칸(l6p_)과 같은 함수에서 센다(전수리뷰 C-3 — 사이트와 한 정본)
                l6_prov_sig=lag['l6p_sig'], l6_prov_now=lag['l6p_now'], l6_prov_late=lag['l6p_late'])


# 7편 금리 오버레이의 원천 계열(refresh_cycle_data.build_overlay 와 같은 계열·지역) — 분기가 석 달 다 찼는지 셀 때 쓴다
OVERLAY_SRC = (('매매지수', '수도권'), ('전세지수', '수도권'), ('금리', 'CD(91일)'))


def overlay_months(sts):
    """오버레이 원천 계열마다 값이 있는 마지막 달('YYYY.MM') — link7_values 가 석 달이 다 찬 분기까지만 쓰게 한다."""
    out = {}
    for key, rg in OVERLAY_SRC:
        b = sts[key]
        ser = b['series'][rg]
        out[key] = next(b['dates'][i].split()[0] for i in range(len(ser) - 1, -1, -1) if ser[i] is not None)
    return out


def _last_full_q(ym):
    """'YYYY.MM'까지 값이 있으면 석 달이 다 찬 마지막 분기(2026.25 꼴 — 오버레이 t 와 같은 꼴)."""
    y, m = int(ym[:4]), int(ym[5:7])
    return y + (m // 3 - 1) * 0.25 if m >= 3 else y - 0.25


def link7_values(D, months=None):
    """7편 숫자 — /cycle/ 정본 D.rate_overlay(수도권 분기 매매·전세 지수, CD금리)와 D.prose 에서 센다. 문장의 전제가 깨지면
    멈춘다. 전제: ① 금리 바닥 뒤 1년 매매 상승률이 전세의 3배 넘게 크다, ② 그 뒤 매매 정점이 전세 정점보다 먼저이고 낙폭도 크다,
    ③ 최근 금리 저점(최근 8분기) 이후 금리가 올랐는데 매매·전세가 모두 올랐다, ④ 금리–매매 상관이 음수다.

    매매·전세·금리가 모두 찬 분기만 쓴다. 전세지수는 매매보다 한 달 늦게 실려, 매매가 새 분기 첫 달(잠정)을 받은 날부터 한 달쯤
    오버레이 끝 분기의 전세가 비어 있다(refresh_cycle_data.build_overlay 는 매매·금리가 있는 분기를 고르고 전세는 je.get). 예전엔
    그 None 과 견주다 TypeError 로 죽었다(전수리뷰 BL2-1·C-1). 그래서 세 값이 다 찬 첫 분기~마지막 분기만 잘라 읽고, 그 사이에
    빈 분기가 있으면(분기 간격 'N분기 뒤'가 틀어진다) 문장 탓이 아닌 데이터 결함으로 멈춘다.

    months(overlay_months — 원천 계열마다 마지막 달)를 주면 석 달이 다 찬 분기까지만 쓴다. 오버레이 분기 값은 그 분기에 있는 달의
    평균이라, 매매 두 달·전세 한 달 평균인 끝 분기를 '지금'이라는 한 분기로 부르지 않게 한다(전수리뷰 overflow, 7편 '지금' 분기)."""
    r = D['rate_overlay']
    tmax = min(_last_full_q(v) for v in months.values()) if months else float('inf')
    full = [i for i in range(len(r['t'])) if None not in (r['maemae'][i], r['jeonse'][i], r['rate'][i]) and r['t'][i] <= tmax]
    if not full:
        raise SystemExit('7편을 만들 수 없다 — 금리 오버레이에 매매·전세·금리가 모두 찬 분기가 없다. %s — '
                         '/cycle/ 데이터가 찬 뒤 다시 돌린다.' % NOT_THE_TEXT)
    t, mm, je, rt = (list(r[k][full[0]:full[-1] + 1]) for k in ('t', 'maemae', 'jeonse', 'rate'))
    gap = [x for x, a, b, c in zip(t, mm, je, rt) if None in (a, b, c)]
    if gap:
        raise SystemExit('7편을 만들 수 없다 — 금리 오버레이 가운데 매매·전세·금리 가운데 하나가 빈 분기가 있다(%s). %s — '
                         '/cycle/ 데이터를 먼저 확인할 것.' % (', '.join('%g' % x for x in gap), NOT_THE_TEXT))
    q = lambda i: '%d년 %d분기' % (int(t[i]), int(round((t[i] % 1) * 4)) + 1)
    pct = lambda a, b: '%.0f%%' % abs((b / a - 1) * 100)      # 문장이 '올랐습니다·내렸습니다'로 방향을 말한다
    lo = min(range(len(rt)), key=lambda i: rt[i])                       # 금리 바닥(2020년 4분기)
    a1 = min(lo + 4, len(t) - 1)
    mm_pk = max(range(lo, len(t)), key=lambda i: mm[i] if t[i] < t[lo] + 3 else -1)
    je_pk = max(range(lo, len(t)), key=lambda i: je[i] if t[i] < t[lo] + 3 else -1)
    mm_lo = min(range(mm_pk, len(t)), key=lambda i: mm[i] if t[i] < t[mm_pk] + 2 else 1e9)
    je_lo = min(range(je_pk, len(t)), key=lambda i: je[i] if t[i] < t[je_pk] + 2 else 1e9)
    # 고금리 국면의 금리 정점 — '그사이'(매매 정점~매매·전세 바닥) 창 안에서만 찾는다. 창 없이 끝까지 찾으면 앞으로 더 높은 금리가
    # 실린 분기를 2022~23 문단에 붙인다(전수리뷰 BL2-12).
    hi = max(range(mm_pk, max(mm_lo, je_lo) + 1), key=lambda i: rt[i])
    rec = max(len(t) - 8, 0)
    nlo = min(range(rec, len(t)), key=lambda i: rt[i])                  # 최근 8분기 금리 저점
    end = len(t) - 1
    g = lambda a, b, s: s[b] / s[a] - 1
    bad = []
    if not g(lo, a1, mm) > 3 * g(lo, a1, je) > 0:
        bad.append('금리 바닥 뒤 1년 매매 상승률이 전세의 3배를 넘지 않는다')
    if not (mm_pk < je_pk and g(mm_pk, mm_lo, mm) < g(je_pk, je_lo, je) < 0):
        bad.append('고금리 국면에서 매매가 먼저·더 크게 꺾이지 않았다')
    if not (rt[end] > rt[nlo] and mm[end] > mm[nlo] and je[end] > je[nlo] and nlo < end):
        bad.append('최근 금리가 오르는 동안 매매·전세가 함께 오르지 않았다')
    if not D['prose']['rate_r'].startswith(('−', '-')):
        bad.append('금리–매매 상관이 음수가 아니다')
    if bad:
        raise SystemExit('7편을 만들 수 없다 — %s. 문장을 먼저 고칠 것.' % ' · '.join(bad))
    f2 = lambda v: ('%.2f' % v).rstrip('0').rstrip('.') if v < 1 else '%.2f' % v
    return dict(now_from=q(nlo), r_from='%.2f' % rt[nlo], now_to=q(end), r_to='%.2f' % rt[end],
                mm_now=pct(mm[nlo], mm[end]), je_now=pct(je[nlo], je[end]),
                low_q=q(lo), low_r=f2(rt[lo]), mm_21=pct(mm[lo], mm[a1]), je_21=pct(je[lo], je[a1]),
                mm_pk_q=q(mm_pk), mm_lo_q=q(mm_lo), mm_fall=pct(mm[mm_pk], mm[mm_lo]),
                je_pk_q=q(je_pk), je_fall=pct(je[je_pk], je[je_lo]),
                hi_q=q(hi), hi_r='%.2f' % rt[hi],
                rate_n=D['prose']['rate_n'], rate_r=D['prose']['rate_r'])


def guard_values(n, D=None, data=None):
    """n편 본문의 데이터 칸 — 편마다 문장 전제 가드를 지나야 나온다. 전제가 깨지면 SystemExit('N편을 만들 수 없다 — …').

    batch_notes.theory_claim_lines 가 이 함수 하나를 부른다. 대표 결정 2026-10-18 D1: 지금 데이터가 발행본의 전제와 어긋나면
    배치 게이트는 막지 않고 기록 줄(ℹ️)로 알린다. SystemExit 말고 다른 예외(TypeError·KeyError …)가 나면 코드 결함이다 — 가드가
    셈을 못 하고 죽었으니 고칠 곳은 가드다.
    D 는 /cycle/ 정본(없으면 읽는다), data 는 (adv, sts)(1·2·4~7편에서 쓰고, 없으면 M.load() 로 읽는다)."""
    D = cycle_d() if D is None else D

    def load():
        return M.load() if data is None else data
    if n in (1, 2):
        v = link1_values(D)
        v['permit_over'] = permit_over_x(load()[1])
        return v
    if n == 3:
        check_sync_claims()
        return {}
    if n == 4:
        # 4편 숫자는 데이터에서 센다. 단정이 깨지면 멈춘다(theory_link3 docstring).
        adv, sts = load()
        try:
            return L3.link3_numbers(adv, sts, D or None)
        except L3.Link3DataError as e:
            # 문장 탓이 아니다 — 입력 계열이 끊겼다(전수리뷰 #73). 글쓴이에게 맞는 문장을 고치라고 안내하지 않는다.
            raise SystemExit('4편을 만들 수 없다 — %s. %s — 다음 클라우드 배치가 전 기간을 새 기준으로 다시 받는다'
                             '(update_adv_data._basis_reason) — git pull 로 그 데이터를 받은 뒤 다시 돌린다. 로컬에서 '
                             '--heal-basic 으로 최근 달만 다시 받으면 단절이 다시 생긴다.' % (e, NOT_THE_TEXT))
        except L3.Link3ClaimError as e:
            raise SystemExit('4편을 만들 수 없다 — %s. 문장을 먼저 고칠 것.' % e)
    if n == 5:
        # 5편 숫자도 같은 원칙: 데이터에서 세고, 단정이 깨지면 멈춘다(theory_link4 docstring).
        adv, sts = load()
        try:
            return L4.link4_numbers(adv, sts, D or None)
        except L4.Link4DataError as e:
            # 문장 탓이 아니다 — 착공·준공 두 표 가운데 한쪽만 새 달을 받은 회차(전수리뷰 T3-6·BL2-3·T1-2). 4편 Link3DataError 와 같은 갈래.
            raise SystemExit('5편을 만들 수 없다 — %s. %s — 다음 클라우드 배치가 두 계열을 같은 달까지 받으면 풀린다'
                             '(git pull 로 받은 뒤 다시 돌린다).' % (e, NOT_THE_TEXT))
        except L4.Link4ClaimError as e:
            raise SystemExit('5편을 만들 수 없다 — %s. 문장을 먼저 고칠 것.' % e)
    if n == 6:
        adv, _ = load()
        return link6_values(D, adv)
    if n == 7:
        _, sts = load()
        return link7_values(D, overlay_months(sts))
    return {}
