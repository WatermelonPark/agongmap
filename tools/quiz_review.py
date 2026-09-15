# -*- coding: utf-8 -*-
"""퀴즈 제도 문항의 기준일·검토 기한(2026-09-15 점검 후속 ⑧).

제도 문항(6·27 대책, 추진 중인 법 개정 등)은 시간이 지나면 틀린 답이 된다. 문항에 asof(기준일)와
review(검토 기한)를 달고, 감시(check_freshness)가 기한이 지난 문항을 실패로 올린다.

⚠️ 날짜 비교는 pytest 게이트에 두지 않는다. 날짜만 지나도 데이터 배치 커밋이 막히기 때문이다.
   pytest 는 '제도 문항에 기한이 달려 있는가'만 보고, 기한 경과는 감시가 알린다.
"""
import datetime
import re

# opts 문자열에는 ']' 가 없다 — [^\]]* 로 한 문항 안에 가둔다(.*? 는 다음 문항까지 넘어간다).
ITEM = re.compile(r"\{q:'((?:[^'\\]|\\.)*)',\s*opts:\[[^\]]*\],\s*"
                  r"asof:'(\d{4}-\d{2}-\d{2})',\s*review:'(\d{4}-\d{2}-\d{2})',")


def items(src):
    """[(질문 텍스트, 기준일, 검토 기한)]"""
    return [(re.sub(r'<[^>]+>', '', q), asof, review) for q, asof, review in ITEM.findall(src)]


def overdue(src, today):
    out = []
    for q, asof, review in items(src):
        if datetime.date.fromisoformat(review) <= today:
            out.append('퀴즈 제도 문항 검토 기한 %s 지남(기준일 %s): %s — 제도가 바뀌었는지 확인하고 '
                       '문항과 asof·review 를 고칠 것' % (review, asof, q[:40]))
    return out
