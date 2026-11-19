# -*- coding: utf-8 -*-
"""글 속 해석 문장의 전제(claims, tools/content_claims.py — 2026-11-19 대표 결정 '먼저 만들고 글 쓰기').

왜 이 시험이 있나. 글의 숫자는 자리표라 매일 새 값으로 바뀌지만 해석 문장은 손 글자다. 전제가 어긋나면 배치 기록에 ℹ️ 한 줄,
원고 검사에 ※ 한 줄이 나와야 하고(게이트는 막지 않는다 — 데이터가 앞으로 가도 그날 커밋은 나간다), 꼴이 틀린 전제는 원고 검사의
✗(발행 멈춤)여야 한다. 저장소의 모든 글 전제는 꼴이 맞아야 한다 — 참·거짓은 시험하지 않는다(데이터가 움직인다).

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - judge 의 '<' 와 '>' 를 맞바꾸면 → test_numeric_and_text_ops
  - '!~' 를 '~' 와 같게 다루면 → test_numeric_and_text_ops
  - check 가 기다림(Pending)을 건너뛰지 않고 올리면 → test_pending_claims_are_skipped
  - batch_notes 에서 ('글 전제', content_claim_lines) 를 빼거나 어긋남을 줄로 내지 않으면 → test_batch_line_for_a_broken_claim
  - content_check.check_post 가 꼴 오류를 ✗ 로 세지 않으면 → test_checker_blocks_a_malformed_claim
픽스처: 저장소의 실제 data(값과 무관하게 늘 참·거짓인 전제 — 적정물량 > 0, '세대' 가 들어 있다), tmp_path 에 쓴 원고 한 편.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import batch_notes as BN      # noqa: E402
import content_check as CK    # noqa: E402
import content_claims as CC   # noqa: E402
import content_md as CM       # noqa: E402
import content_tables as CT   # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DATA = CT.load()

FRONT = """---
title: 시험용 글 제목
summary: 시험이 쓰는 요약입니다. 마흔 자를 넘기도록 한 문단으로 적고, 답변 블록에 그대로 실립니다.
date: 2026-11-01
updated: 2026-11-01
section: city
region: 울산
tldr:
  - 첫째 줄 결론입니다
  - 둘째 줄 근거입니다
  - 셋째 줄 전망입니다
audience: 울산 실수요자
key:
  - label: 시험용 숫자
    value: "12"
city:
  - 울산
topic: moveins
claims:
%s
---

## 머리글

문단입니다.
"""


def _post(tmp_path, claims):
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'test-claim.md'
    p.write_text(FRONT % '\n'.join('  - "%s"' % c for c in claims), encoding='utf-8')
    return str(p)


def test_numeric_and_text_ops():
    j = lambda c: CC.judge(c, DATA)[0]
    assert j('{{v:need:울산}} > 0') and not j('{{v:need:울산}} < 0')
    assert j('{{v:need:울산}} >= {{v:need:울산}}') and not j('{{v:need:울산}} > {{v:need:울산}}')
    assert j('{{v:need:울산}} ~ 세대') and not j('{{v:need:울산}} !~ 세대')


def test_malformed_claims_raise():
    for bad in ('{{v:need:울산}}', '{{table:moveins:울산}} > 0', '{{v:need:울산}} == 3', '{{v:need:울산}} > 세대'):
        with pytest.raises(CC.ClaimError):
            CC.judge(bad, DATA)


def test_pending_claims_are_skipped():
    """아직 받지 않은 도시를 가리키는 전제는 건너뛴다(기다림) — 원고는 올려도 되고, 자료가 들어온 회차부터 잰다."""
    import make_city_moveins as MCM
    cand = [c for c in ('포항', '김해', '양산', '익산', '군산', '아산', '경산') if MCM.collectable(c) and not CT.city(DATA, c)]
    if not cand:
        pytest.skip('받지 않은 도시 후보가 없다')
    meta = {'section': 'city', 'date': '2026-11-01', 'claims': ['{{v:share3:%s}} < 1000' % cand[0]]}
    assert CC.check(meta, DATA) == []


def test_batch_line_for_a_broken_claim(tmp_path, monkeypatch):
    p = _post(tmp_path, ['{{v:need:울산}} < 0', '{{v:need:울산}} > 0'])
    monkeypatch.setattr(CM, 'built', lambda root, section=None: [('city', 'test-claim', p)])
    got = BN.content_claim_lines(ROOT)
    assert len(got) == 1 and got[0].startswith('ℹ️ 글 전제 어긋남 — city/test-claim:') and '< 0' in got[0], got
    assert '> 0' not in got[0], '맞는 전제까지 알렸다'
    src = open(BN.__file__, encoding='utf-8').read()
    assert "('글 전제', content_claim_lines)" in src, 'batch_notes.main 이 글 전제 줄을 싣지 않는다'


def test_checker_blocks_a_malformed_claim(tmp_path):
    p = _post(tmp_path, ['{{v:need:울산}} 크다'])
    problems, _w, _r = CK.check_post(p, DATA, root=str(tmp_path))
    assert any('전제(claims)' in why for _ln, why in problems), problems
    ok = _post(tmp_path, ['{{v:need:울산}} < 0'])
    notes = CK.claim_notes(ok, 'city', 'test-claim', open(ok, encoding='utf-8').read(), DATA)
    assert notes and '어긋난다' in notes[0][1], '어긋난 전제가 ※ 로 나오지 않는다'
    problems, _w, _r = CK.check_post(ok, DATA, root=str(tmp_path))
    assert not any('전제' in why for _ln, why in problems), '어긋남은 발행을 막지 않는다(✗ 가 아니다)'


def test_every_post_claim_is_well_formed():
    """저장소 원고의 전제는 모두 꼴이 맞고 채울 수 있다(참·거짓은 보지 않는다 — 어긋남은 배치 기록의 몫)."""
    for sec, slug, path in CM.posts(ROOT):
        meta = CM.read(path, sec, slug, lenient=True)[0]
        try:
            CC.check(meta, DATA)
        except CC.ClaimError as e:
            raise AssertionError('%s/%s: %s' % (sec, slug, e))
