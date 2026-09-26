# -*- coding: utf-8 -*-
"""한국 시각(KST) 기준 '오늘' — 생성기가 페이지·sitemap 에 찍는 날짜의 단일 출처.

배치 러너는 TZ=UTC 다. `datetime.date.today()` 는 00:00~09:00 KST(15:00~24:00 UTC)에 전날을 준다.
목요일 1차 배치(예약 22:00 UTC)·재시도·자정 넘은 수동 실행이 그 창에 들어간다. 2026-09-23 부터
/cycle/ 는 KST 로 날짜를 찍었는데 /zone/·허브·홈·/weekly/ 는 UTC 날짜를 찍어, 한 커밋 안에서
두 날짜가 하루 어긋났다(2026-09-26 데이터 감사). 날짜를 찍는 생성기는 여기서만 오늘을 읽는다.

한국은 일광 절약 시간이 없으므로 고정 +9 시간이다. zoneinfo 는 윈도우에 tzdata 가 없으면 죽어서 쓰지 않는다.
표준 라이브러리만 쓴다(배치의 생성기 단계는 pip 설치 전에 돈다).
"""
import datetime

KST = datetime.timezone(datetime.timedelta(hours=9), 'KST')


def today(now=None):
    """오늘 날짜(KST). now 는 시험용 — 시간대가 붙은 datetime 을 넘기면 그 순간의 KST 날짜를 준다."""
    now = now if now is not None else datetime.datetime.now(datetime.timezone.utc)
    return now.astimezone(KST).date()


def today_iso(now=None):
    return today(now).isoformat()
