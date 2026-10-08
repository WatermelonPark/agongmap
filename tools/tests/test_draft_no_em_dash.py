# -*- coding: utf-8 -*-
"""블로그에 그대로 나가는 생성기 고정 문구에 엠대시(—)를 쓰지 않는다(한국어 지침). 10-09 점검에서 주간 초안 소제목
'이번 주의 지표 — 전세가율'과 이론 초안 링크 글자 '우리 동네 공급은 어떤가 — 시도별 리포트'가 발행본에 실렸다.
무엇을 깨뜨리면 빨개지나(실제로 확인): 소제목을 '이번 주의 지표 — %s' 로, 링크 글자를 옛 문구로 되돌리면 빨개진다.
픽스처: 생성기 소스 문자열(코드 주석의 엠대시는 대상이 아니므로 h3 와 link( 글자만 본다).
"""
import io
import os
import re

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _src(name):
    return io.open(os.path.join(TOOLS, name), encoding='utf-8').read()


def test_weekly_indicator_headings_have_no_em_dash():
    hs = re.findall(r"<h3>이번 주의 지표[^<]*</h3>", _src('make_naver_post.py'))
    assert hs and not [h for h in hs if '—' in h], hs


def test_theory_link_texts_have_no_em_dash():
    texts = re.findall(r"link\('([^']*)'", _src('make_theory_post.py'))
    assert texts and not [t for t in texts if '—' in t], texts
