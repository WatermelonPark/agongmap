# -*- coding: utf-8 -*-
"""퀴즈 제도 문항의 기준일·검토 기한(2026-09-15 점검 후속 ⑧).

제도 문항(6·27 대책, 추진 중인 법 개정 등)은 시간이 지나면 틀린 답이 된다. 문항에 asof(기준일)와
review(검토 기한)를 달고, 기한이 지난 문항을 감시(check_freshness)가 경고(::warning::·잡 요약)로, 배치 기록이
ℹ️ 줄(batch_notes.quiz_review_lines — 월요일 확인 메일)로 올린다. 실패로 올리면 감시가 매일 빨개져 진짜 뒤처짐
경보가 묻힌다(2026-09-26 데이터 감사 #13).

⚠️ 날짜 비교는 pytest 게이트에 두지 않는다. 날짜만 지나도 데이터 배치 커밋이 막히기 때문이다.
   pytest 는 '제도 문항에 기한이 달려 있는가'만 보고, 기한 경과는 감시가 알린다.
"""
import datetime
import re

# 한 문항 = '{q:' 에서 다음 '{q:' 앞까지. 그 안에서 asof·review 를 **순서와 자리에 상관없이** 찾는다 — 예전 식은 asof 가 opts 바로
# 뒤, review 가 asof 바로 뒤일 때만 읽어, 다른 순서로 단 제도 문항은 조용히 빠졌다(감시는 0개일 때만 실패했다 — 전수리뷰 P 묶음 overflow).
Q = re.compile(r"\{q:'((?:[^'\\]|\\.)*)'")
ASOF = re.compile(r"\basof:'(\d{4}-\d{2}-\d{2})'")
REVIEW = re.compile(r"\breview:'(\d{4}-\d{2}-\d{2})'")


def _chunks(src):
    starts = [m for m in Q.finditer(src)]
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(src)
        yield m.group(1), src[m.end():end]


def items(src):
    """[(질문 텍스트, 기준일, 검토 기한)] — asof·review 를 둘 다 단 문항."""
    out = []
    for q, body in _chunks(src):
        a, r = ASOF.search(body), REVIEW.search(body)
        if a and r:
            out.append((re.sub(r'<[^>]+>', '', q), a.group(1), r.group(1)))
    return out


def half_tagged(src):
    """asof·review 가운데 하나만 단 문항의 질문 — 검토 기한 감시에서 빠지므로 감시가 실패로 알린다."""
    return [re.sub(r'<[^>]+>', '', q)[:40] for q, body in _chunks(src)
            if bool(ASOF.search(body)) != bool(REVIEW.search(body))]


def overdue(src, today):
    out = []
    for q, asof, review in items(src):
        if datetime.date.fromisoformat(review) <= today:
            out.append('퀴즈 제도 문항 검토 기한 %s 지남(기준일 %s): %s — 제도가 바뀌었는지 확인하고 '
                       '문항과 asof·review 를 고칠 것' % (review, asof, q[:40]))
    return out
