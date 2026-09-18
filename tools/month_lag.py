# -*- coding: utf-8 -*-
"""월간 계열 중 기준월이 뒤처진 것을 배치 기록에 한 줄로 남긴다 (PM 요청 2026-09-16).

왜 필요한가. 미분양은 원천(R-ONE)이 광주·전남 행을 주지 않아 2026.06 에 묶여 있다.
그 달을 통째로 버리는 것은 의도된 동작이고, 신선도 점검도 배치와 **같은 완비 기준**을
쓰기 때문에 실패로 잡지 않는다. 즉 방어선이 스스로를 못 본다. 그동안은 사람이 주 1회
/monthly/ 를 눈으로 봐서 메웠다. 그 눈을 여기로 옮긴다.

알림 규칙(PM 조건).
  · 판정도 배포도 막지 않는다. 알리기만 한다.
  · 매 회차 반복하지 않는다 — 평소에는 월요일 회차에만 한 줄이다. 매일 오는 '괜찮다'는
    진짜 경보를 묻는다(2026-09-12 알림 원칙).
  · 뒤처짐이 ESCALATE_MONTHS 이상이면 매 회차 싣고 멘션을 붙인다. 그쯤이면 원천 사정이
    아니라 우리 대응이 필요하다는 신호로 본다.
  · 비교 대상을 숫자로 박지 않는다. 계열 목록에서 파생하므로 지표가 늘어도 따라온다.

무엇을 월간으로 보는가. 저장된 마지막 시점의 **모양**으로 가른다('2026.07' 은 월,
'2026Q2' 는 분기, '2024' 는 연간). 계열 목록에 월간 여부를 적은 자리가 없어서다.
모양으로 가르면 새 계열이 들어와도 따로 등록할 것이 없다.

MIN_MONTHS 를 2로 둔 이유. 원천 공표 시차 때문에 1개월 뒤처짐은 늘 몇 계열에 있다.
그것까지 알리면 줄이 길어져 읽히지 않는다.

사용:
    python tools/month_lag.py            # 뒤처짐이 없으면 아무것도 찍지 않는다
    python tools/month_lag.py --data data.js
"""
import argparse
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MIN_MONTHS = 2       # 이만큼 뒤처지면 알린다(월요일 회차)
ESCALATE_MONTHS = 3  # 이만큼이면 매 회차 알리고 멘션을 붙인다

# 계열별 정상 공표 시차(개월). "가장 빠른 계열 대비"로만 재면 원래 늦게 나오는 계열이 그대로
# 뒤처짐으로 잡힌다 — 인허가·착공·준공·규모별은 금리보다 약 2개월 늦게 나오는 것이 정상이라,
# 금리가 새 달로 넘어가는 매달 초마다 3개월 차이가 되어 매 회차 메일이 갔을 것이다(리뷰 2026-09-18).
# 허용 시차는 감시(check_freshness)와 **같은 상수**에서 파생한다 — 두 방어선이 다른 기준으로 재면
# 한쪽이 다른 쪽을 가린다(CLAUDE.md 데이터 원칙). 위 "가장 빠른 계열" 자체는 시차 0으로 본다.
import check_freshness as CF   # noqa: E402
import update_adv_data as U    # noqa: E402
SLOW_ALLOWANCE = max(0, int(round((CF.GRACE_BASIC - CF.GRACE_MONTHLY) / 30.0)))
SLOW_SERIES = frozenset(list(U.BASIC_CONF) + ['규모별'])   # 감시가 GRACE_BASIC 으로 보는 계열


def allowance(name):
    """그 계열의 정상 시차(개월). 뒤처짐은 이만큼을 뺀 '정상을 넘은 개월'로 잰다."""
    return SLOW_ALLOWANCE if name in SLOW_SERIES else 0

MARK = 'ℹ️'          # 실패·경고 표시가 아니다 — 형식기가 요일 규칙으로 싣는다
# 뒤에 붙는 잠정치 표시('2026.07 p)')는 허용하되, 일 단위('2026-09-07')는 받지 않는다.
# 주간 시세가 월간으로 섞이면 '최신 월'이 한 달 앞서 잡혀 모든 계열이 뒤처져 보인다.
_MONTH = re.compile(r'^(\d{4})[.\-](\d{1,2})(?:\s+\S+)?$')


def month_of(v):
    """'2026.07', '2026-07', '2026.07 p)' → (2026, 7). 일·분기·연간·빈값이면 None.

    잠정치 표시가 붙어 오는 계열이 있어 뒤에 붙는 한 토막까지는 받아 준다. 'YYYY' 만
    있는 연간 계열, 'YYYYQn' 분기 계열, 'YYYY-MM-DD' 주간 계열은 여기서 걸러진다.
    """
    if not v:
        return None
    m = _MONTH.match(str(v).strip())
    if not m:
        return None
    mm = int(m.group(2))
    return (int(m.group(1)), mm) if 1 <= mm <= 12 else None


def _last(seq):
    return seq[-1] if seq else None


def monthly_months(adv, stats):
    """계열 이름 → (연, 월). 월 모양으로 끝나는 계열만 담는다.

    stats 는 {'dates': [...]} 꼴, ADV 는 {'rows': [{'p': 시점}]} 꼴이라 둘을 같이 훑는다.
    ADV.occupancy 처럼 앞날 예정이 섞인 계열은 분기라 모양에서 걸러진다.
    """
    out = {}
    for name, d in sorted((stats or {}).items()):
        ym = month_of(_last((d or {}).get('dates')))
        if ym:
            out[name] = ym
    for name, d in sorted((adv or {}).items()):
        rows = (d or {}).get('rows') if isinstance(d, dict) else None
        if not rows:
            continue
        ym = month_of(_last([r.get('p') for r in rows if isinstance(r, dict)]))
        if ym:
            out[name] = ym
    return out


def gap(a, b):
    """월 단위 차이. a 가 b 보다 이르면 양수."""
    return (b[0] - a[0]) * 12 + (b[1] - a[1])


def behind(months, min_months=MIN_MONTHS):
    """(가장 최신 시점, [(계열, 시점, 정상 시차를 넘은 개월), ...]). 뒤처짐이 큰 순.

    개월 수는 원래 늦게 나오는 계열(SLOW_SERIES)의 정상 시차를 뺀 값이다. 그래서 '3개월'은
    "정상보다 3개월 더 늦다"는 뜻이고, 형식기의 ESCALATE 판정도 그 뜻으로 본다.
    """
    if not months:
        return None, []
    newest = max(months.values())
    rows = [(n, ym, gap(ym, newest) - allowance(n)) for n, ym in months.items()]
    rows = [r for r in rows if r[2] >= min_months]
    rows.sort(key=lambda r: (-r[2], r[0]))
    return newest, rows


def _ym(t):
    return '%d.%02d' % t


def line(adv, stats, min_months=MIN_MONTHS):
    """배치 기록에 남길 한 줄. 뒤처진 계열이 없으면 None."""
    newest, rows = behind(monthly_months(adv, stats), min_months)
    if not rows:
        return None
    return '%s 월간 뒤처짐 %d개월 · %s · 최신 %s' % (
        MARK, rows[0][2],
        ' / '.join('%s %s' % (n, _ym(ym)) for n, ym, _ in rows),
        _ym(newest))


def load(path=None):
    """data.js 에서 ADV 와 STATS 를 읽는다. /monthly/ 생성기와 같은 방식이다."""
    src = io.open(path or os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(
        r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', src, re.S).group(1))
    sts = json.loads(re.search(
        r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', src, re.S).group(1))
    return adv, sts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', help='data.js 경로(기본: 저장소 루트)')
    a = ap.parse_args(argv)
    try:
        adv, sts = load(a.data)
    except Exception as e:
        # 알림용 곁가지다. 읽지 못해도 배치를 멈추지 않는다 — 대신 이유를 남긴다.
        sys.stderr.write('month_lag: 데이터를 읽지 못했다 (%s)\n' % e)
        return 0
    s = line(adv, sts)
    if s:
        sys.stdout.write(s + '\n')
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    raise SystemExit(main())
