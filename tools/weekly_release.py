# -*- coding: utf-8 -*-
"""주간 발표 일정 — 조사일·발표일·다음 발표·지연 판정의 파이썬 정본(홈 마케팅 검수 A2, 2026-09-27).

같은 규칙을 세 곳이 쓴다.
  - 홈 주간 격자 머리줄과 통계 탭 rel-week : home-app.js 의 weeklyRelease()
  - /weekly/ 머리줄                          : make_weekly_page 가 이 모듈로 굽는다
  - 감시(check_freshness)                    : GRACE_WEEKLY 를 여기서 가져간다
JS 와 파이썬이 같은 날짜·같은 문장을 내는지는 tools/tests/test_weekly_release.py 가 node 로 대조한다.

규칙
  - 조사기준일 p 는 월요일, 발표는 그 주 목요일(p+3). 다음 발표는 다음 조사분의 목요일(p+10).
  - 지연: 감시는 조사기준일부터 GRACE_WEEKLY 일이 지나면(= 다음 목요일) 원천보다 늦은 값을 실패로 본다.
    감시는 그날 배치 **뒤에** 돌지만 화면은 발표 당일 아침에도 보이므로, 화면은 그 날(p+GRACE_WEEKLY+1)을
    휴일이면 영업일로 민 날이 **다 지나야** '반영 대기'로 적는다. 같은 상수를 split_data 가 ADV.weekly.grace 로
    실어 홈이 읽는다 — 홈이 9 를 따로 적으면 감시를 옮길 때 둘이 갈린다.
  - 연휴 주: 다음 발표 목요일이 든 주(월~목)에 공휴일이 끼면 날짜를 단정하지 않는다.
    2026 추석 실측: 9/21 조사분은 휴일인 9/24(목) 당일 R-ONE 에 올라왔다(09:10 KST 배치에는 없고 18:12 KST
    배치에는 있었다. 9/23 18:13 KST 배치에도 없었다). 앞당겨지지도, 옛 규칙(_bizDay)대로 다음 영업일 9/28(월)로
    밀리지도 않았다. 관측 한 번으로는 일반 규칙을 세울 수 없어, 날짜 대신 '연휴로 발표 일정이 바뀔 수 있습니다'를
    적는다. 지연 판정만은 늦게 나오는 쪽을 기준으로 삼아 연휴에 헛경보를 내지 않는다.
  - 연휴로 조사를 거른 주(전수리뷰 #10, 2026-09-30 대표 결정): 원천은 긴 연휴 주에 조사를 한 주 건너뛰기도 한다
    (data.js 실측: 2025-01-20 다음 조사분이 2025-02-03, 2025-09-29 다음이 2025-10-13). 건너뛸지는 관측으로 규칙을
    세울 수 없어(2026 설 2/16 은 월요일이 휴일인데도 조사했다) 공휴일 달력만 본다 — 연휴 주(hedge)면 지연 기준일을
    **한 주(WEEK) 늦춘다**. 대가로 연휴 주에 정말 늦으면 화면이 한 주 늦게 알린다(감시는 원천과 대조하므로 그대로다).

표준 라이브러리만 쓴다(배치의 생성기·감시 단계는 pip 설치 전에 돈다).
"""
import datetime

# 조사기준일부터 센 주간 정상 최대 나이(일). 감시 cron 과 짝이다 — watchdog.yml 의 schedule 주석을 볼 것.
# 감시를 배치 앞으로 옮기면 매주 목요일 오탐이 나니 그때는 10 으로 올린다(그러면 화면의 지연 표시도 하루 늦춰진다).
GRACE_WEEKLY = 9

SURVEY_WEEKDAY = 0  # 조사기준일은 월요일(date.weekday() 값)
PUB_OFFSET = 3     # 월요일 조사 → 목요일 발표
WEEK = 7
WEEKDAYS = '월화수목금토일'   # date.weekday() 순서


def pub_weekday():
    """평상 주의 발표 요일 한 글자('목'). 날짜 없이 요일만 말하는 자리(/llms.txt 갱신 주기 문장)가 쓴다."""
    return WEEKDAYS[(SURVEY_WEEKDAY + PUB_OFFSET) % WEEK]


HOLD = '연휴로 발표 일정이 바뀔 수 있습니다'
WAIT = '이번 주 발표분 반영 대기'


def _d(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return datetime.date(y, m, d)


def _add(day, n):
    return day + datetime.timedelta(days=n)


def biz_day(day, holidays):
    """주말·공휴일이면 다음 영업일까지 민다. holidays 는 'YYYY-MM-DD' 집합."""
    while day.weekday() >= 5 or day.isoformat() in holidays:
        day = _add(day, 1)
    return day


def status(p, today=None, holidays=(), grace=GRACE_WEEKLY):
    """최신 조사기준일 p('YYYY-MM-DD') 의 발표 상태.

    today 는 KST 날짜(datetime.date, tools/kst.today()). None 이면 지연을 판정하지 않는다(정적 페이지를 구울 때).
    grace 가 None 이면 지연을 판정하지 않는다 — 홈에서 옛 캐시(data-core 에 grace 가 없을 때)와 같은 동작.
    """
    hs = set(holidays or ())
    b = _d(p)
    nxt = _add(b, WEEK + PUB_OFFSET)
    hedge = any(_add(nxt, -k).isoformat() in hs for k in range(PUB_OFFSET + 1))
    # 연휴 주는 원천이 조사를 거를 수 있어 기준일을 한 주 늦춘다(모듈 머리말, 대표 결정 ④). JS 거울: home-app.js <wk-release>
    due = biz_day(_add(b, grace + 1 + (WEEK if hedge else 0)), hs) if grace is not None else None
    stale = bool(today is not None and due is not None and today > due)
    return {'survey': p, 'pub': _add(b, PUB_OFFSET).isoformat(), 'next': nxt.isoformat(),
            'hedge': hedge, 'due': due.isoformat() if due else None, 'stale': stale}


def md(iso):
    d = _d(iso)
    return '%d/%d' % (d.month, d.day)


def next_text(st):
    """'다음 발표 10/1(목)' · 연휴 주 · 지연. 홈 JS wkNextText 와 같은 문장."""
    if st['stale']:
        return WAIT
    if st['hedge']:
        return HOLD
    return '다음 발표 %s(%s)' % (md(st['next']), WEEKDAYS[_d(st['next']).weekday()])


def pub_lead(st):
    """결론 문장 앞 발표일 머리말 — 평상 '9/24 발표', 늦은 주 '9/17 발표 기준'. 홈 JS wkPubLead 와 같은 문장.

    홈 첫 화면 띠 첫 줄·홈 주간 구역 h2(늦은 주)·/weekly/ 제목(늦은 주에 '이번 주'를 바꾸는 말)이 이 한 말을 쓴다
    (홈 마케팅 검수 B1·A2·MOB-1, 2026-09-27 검토 지적). 늦은 주에 '기준'을 붙여 그 값이 이번 주 것이 아님을 말한다.
    """
    return '%s 발표%s' % (md(st['pub']), ' 기준' if st['stale'] else '')


def when_text(st):
    """'9/14 조사 · 9/17 발표 · 다음 발표 10/1(목)'. 지연이면 '최근 반영: 9/17 발표 · 이번 주 발표분 반영 대기'.
    홈 JS wkWhenText 와 같은 문장."""
    if st['stale']:
        return '최근 반영: %s 발표 · %s' % (md(st['pub']), WAIT)
    return '%s 조사 · %s 발표 · %s' % (md(st['survey']), md(st['pub']), next_text(st))


# 주차 서수(홈 마케팅 검수 B4·SEO-4, 2026-09-27). 블로그 주간 글 제목 '주간 아파트가격 동향(9월 셋째 주)'과 /weekly/ 의
# title·머리줄이 **이 함수 하나**를 쓴다 — 블로그가 링크로 보내는 사이트 페이지가 같은 주를 다른 이름으로 부르지 않게.
# 규칙은 2026-09-12 블로그 제목 형식 그대로: 조사기준일(월)의 달, 그 날짜의 (일−1)//7 번째 주. 달력 주(1일이 든 주를
# 첫째 주로 세는 방식)와는 1일이 화~일요일인 달에 하루 이상 어긋날 수 있다 — 바꾸려면 여기 한 곳만 고치면 둘이 같이 바뀐다.
ORDINALS = ('첫째', '둘째', '셋째', '넷째', '다섯째')


def week_label(p, year=False):
    """조사기준일 p('YYYY-MM-DD') → '9월 셋째 주'(year=True 면 '2026년 9월 셋째 주')."""
    d = _d(p)
    s = '%d월 %s 주' % (d.month, ORDINALS[min((d.day - 1) // 7, len(ORDINALS) - 1)])
    return ('%d년 %s' % (d.year, s)) if year else s
