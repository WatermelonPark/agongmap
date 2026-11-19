# -*- coding: utf-8 -*-
"""글 속 해석 문장의 전제(claims) — 데이터가 움직여 문장이 틀려지면 알린다(2026-11-19 대표 결정 '먼저 만들고 글 쓰기').

왜 이것이 있나. 글의 숫자는 자리표라 배치가 매일 새 값으로 채우지만, 그 숫자로 쓴 해석 문장('적정물량에 크게 못 미칩니다',
'매매와 전세가 함께 오른다')은 손 글자다. 데이터가 바뀌어 문장이 틀려져도 아무것도 알리지 않았다. 원고 프런트매터에 문장이 기대는
조건을 적어 두면, 배치 기록(batch_notes)과 원고 검사(content_check)가 지금 데이터로 다시 재어 어긋난 글을 알린다. 알림이지 게이트가
아니다 — 데이터가 앞으로 가도 그날 커밋을 막지 않는다(CLAUDE.md 데이터 원칙). 어긋난 글은 세션이 문장을 고친다.

꼴(프런트매터 — 따옴표로 감싼다. 감싸지 않으면 'share3:울산' 이 키:값 짝으로 읽힌다):
    claims:
      - "{{v:share3:울산}} < 70"                       # 수: <, <=, >, >= (자리표 글자의 첫 수를 읽는다 — '57%' → 57)
      - "{{v:share:인천:2027}} > {{v:share:인천:2028}}"  # 오른쪽도 자리표일 수 있다
      - "{{v:streak:울산}} ~ 상승"                      # 글자: ~ (들어 있다), !~ (들어 있지 않다)
자리표는 본문과 같은 v: 값 자리표다(content/README.md). 아직 자료가 없는 자리표(기다림)는 그 조건만 건너뛴다.
"""
import re

import content_tables as CT

CLAIM = re.compile(r'^\s*(\{\{v:[^}]+\}\})\s*(<=|>=|!~|<|>|~)\s*(.+?)\s*$')
NUM = re.compile(r'-?\d[\d,]*(?:\.\d+)?')


class ClaimError(Exception):
    """전제의 꼴이 틀렸거나 자리표를 채울 수 없다 — 원고를 고칠 일이다(검사기 ✗)."""


def _value(data, ph):
    m = CT.PH.fullmatch(ph.strip())
    if not m or m.group(1) != 'v':
        raise ClaimError('전제의 자리표는 {{v:…}} 하나다: %s' % ph)
    kind, args = CT._args(m)
    return CT.value(data, kind, args)


def _num(text, claim):
    m = NUM.search(text or '')
    if not m:
        raise ClaimError('수를 읽지 못했다(%r) — 수 비교는 수가 든 자리표에만: %s' % (text, claim))
    return float(m.group(0).replace(',', ''))


def judge(claim, data):
    """전제 하나 → (맞는가, 지금 값 글). 꼴이 틀리면 ClaimError, 자료를 기다리면 CT.Pending 을 그대로 올린다."""
    if not isinstance(claim, str):
        raise ClaimError('전제는 따옴표로 감싼 한 줄이다: %r' % (claim,))
    m = CLAIM.match(claim)
    if not m:
        raise ClaimError("전제 꼴은 '{{v:…}} 연산 값'(연산: < <= > >= ~ !~)이다: %s" % claim)
    lhs_ph, op, rhs = m.groups()
    try:
        lhs = _value(data, lhs_ph)
        rhs_text = _value(data, rhs) if rhs.startswith('{{') else rhs
    except CT.Pending:
        raise
    except CT.TableError as e:
        raise ClaimError('%s — %s' % (claim, e))
    if op in ('~', '!~'):
        ok = (rhs_text in lhs) == (op == '~')
    else:
        a, b = _num(lhs, claim), _num(rhs_text, claim)
        ok = {'<': a < b, '<=': a <= b, '>': a > b, '>=': a >= b}[op]
    now = lhs if not rhs.startswith('{{') else '%s · %s' % (lhs, rhs_text)
    return ok, now


def check(meta, data):
    """글 하나의 전제 → [(전제, 맞는가, 지금 값)] — 기다리는 전제는 뺀다. 꼴이 틀리면 ClaimError."""
    claims = meta.get('claims') or []
    if not isinstance(claims, list):
        raise ClaimError('claims 는 목록이다')
    data = CT.for_post(data, meta)      # 본문과 같은 창(도시 3년 창은 글의 작성 연도가 정한다)
    out = []
    for c in claims:
        try:
            ok, now = judge(c, data)
        except CT.Pending:
            continue
        out.append((c, ok, now))
    return out


def broken(meta, data):
    """어긋난 전제만 — [(전제, 지금 값)]."""
    return [(c, now) for c, ok, now in check(meta, data) if not ok]
