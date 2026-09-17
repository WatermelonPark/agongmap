# -*- coding: utf-8 -*-
"""지역 편의 썸네일과 댓글 유도문 (2026-09-17 사용자 결정).

유입의 90%가 홈피드인데 대표 이미지가 12편 내내 사이트 캡처였다. 썸네일은 본문
첫 문장과 **같은 값**(r['tot'])을 말해야 한다 — 부호를 거꾸로 읽으면 "모자랍니다"와
"남습니다"가 뒤집혀 글과 그림이 반대 말을 한다.

변이 확인(실제로 깨뜨려 봄): thumb_zone의 `lack = t >= 0`을 `t <= 0`으로 바꾸면
test_thumb_color_follows_sign이 빨개진다. ask_cta의 인덱스를 0으로 고정하면
test_ask_rotates_by_seq가 빨개진다.
픽스처: r은 ADV.sido.zones 한 줄에서 thumb_zone이 읽는 세 키(z·tot·grade)만 재현한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import make_naver_post as P  # noqa: E402
import make_zone_cards as ZC  # noqa: E402


def _thumb(tmp_path, monkeypatch, tot):
    from PIL import Image
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    rel = P.thumb_zone({'z': '세종', 'tot': tot, 'grade': 'g1'}, '2026년', 3)
    return Image.open(os.path.join(P.ROOT, rel)).convert('RGB')


def test_thumb_color_follows_sign(tmp_path, monkeypatch):
    lack = _thumb(tmp_path, monkeypatch, 907)
    assert lack.size == (1200, 900)
    assert ZC.RED in set(lack.crop((60, 440, 1140, 600)).getdata()), '부족인데 붉은 문장이 없다'
    over = _thumb(tmp_path, monkeypatch, -907)
    assert ZC.RED not in set(over.crop((60, 440, 1140, 600)).getdata()), '과잉인데 붉은 문장이 남았다'


def test_ask_rotates_by_seq():
    got = [P.ask_cta('세종', s) for s in range(1, len(P.ASK_CTA) + 1)]
    assert len(set(got)) == len(P.ASK_CTA), '회차가 달라도 같은 문장이 나간다'
    assert P.ask_cta('세종', 1) == P.ask_cta('세종', 1 + len(P.ASK_CTA))


def test_ask_never_says_free_consulting():
    # 면책과 부딪히고 광고 문구로 읽힌다 — 사용자와 합의한 선.
    assert not any('무료' in t or '상담' in t for t in P.ASK_CTA)
