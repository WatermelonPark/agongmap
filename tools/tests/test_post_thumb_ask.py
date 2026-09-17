# -*- coding: utf-8 -*-
"""지역 편의 썸네일과 댓글 유도문 (2026-09-17 사용자 결정).

유입의 90%가 홈피드인데 대표 이미지가 12편 내내 사이트 캡처였다. 썸네일은 그 지역
가격 곡선을 배경에 깔고 가운데에 키 메시지를 얹는다. 메시지의 숫자(고점 대비 %)와
아랫줄(순부족·판정)은 **데이터에서 그대로** 나와야 한다 — 그림이 본문과 다른 말을
하면 클릭은 벌어도 신뢰를 잃는다.

변이 확인(실제로 깨뜨려 봄):
  - thumb_sub의 `>= 0`을 `<= 0`으로 → test_sub_sign_without_ctxt 빨강
  - thumb_message의 `curve[2] <= -3` 조건을 지움 → test_message_at_peak_does_not_claim_a_fall 빨강
  - ask_cta 인덱스를 0으로 고정 → test_ask_rotates_by_seq 빨강
픽스처: 지수 계열은 sts['매매지수']의 모양(dates에 잠정 표시 'p)'가 붙는 것 포함)을,
r은 ADV.sido.zones 한 줄에서 썸네일이 읽는 키(z·tot·grade·ctxt)만 재현한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import make_naver_post as P  # noqa: E402


def _sts(vals):
    dates = ['%d.%02d' % (2016 + i // 12, i % 12 + 1) for i in range(len(vals))]
    dates[-1] += ' p)'
    return {'매매지수': {'dates': dates, 'series': {'세종': vals}}}


FALL = [100 + i for i in range(40)] + [140 - i for i in range(1, 36)]   # 고점 139 → 105
RISE = [100 + i for i in range(60)]


def test_message_states_the_fall_from_the_index():
    c = P._thumb_curve(_sts(FALL), '세종')
    assert round(c[2]) == -24
    assert P.thumb_message('세종', c)[0] == '세종, 고점에서 -24%'


def test_message_at_peak_does_not_claim_a_fall():
    msg = P.thumb_message('세종', P._thumb_curve(_sts(RISE), '세종'))
    assert '고점에서' not in msg[0] and '최고가' in msg[0]


def test_sub_prefers_site_text_and_keeps_sign():
    r = {'z': '세종', 'tot': 907, 'grade': 'g1', 'ctxt': '907세대 부족 · 3년 필요량의 13%'}
    assert P.thumb_sub(r, 3).startswith('907세대 부족 · 3년 필요량의 13%')


def test_sub_sign_without_ctxt():
    assert '부족' in P.thumb_sub({'z': '세종', 'tot': 907, 'grade': 'g1'}, 3)
    assert '과잉' in P.thumb_sub({'z': '세종', 'tot': -907, 'grade': 'g1'}, 3)


def test_thumb_renders_even_without_series(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    rel = P.thumb_zone({'z': '세종', 'tot': 907, 'grade': 'g1'}, '2026년', 3, sts={})
    assert Image.open(os.path.join(P.ROOT, rel)).size == (1200, 900)


def test_thumb_msg_arg():
    assert P._thumb_msg_arg(['x', '--thumb-msg', '첫 줄|*둘째 줄*']) == ['첫 줄', '*둘째 줄*']
    assert P._thumb_msg_arg(['x']) is None


def test_ask_rotates_by_seq():
    got = [P.ask_cta('세종', s) for s in range(1, len(P.ASK_CTA) + 1)]
    assert len(set(got)) == len(P.ASK_CTA), '회차가 달라도 같은 문장이 나간다'
    assert P.ask_cta('세종', 1) == P.ask_cta('세종', 1 + len(P.ASK_CTA))


def test_ask_never_says_free_consulting():
    # 면책과 부딪히고 광고 문구로 읽힌다 — 사용자와 합의한 선.
    assert not any('무료' in t or '상담' in t for t in P.ASK_CTA)
