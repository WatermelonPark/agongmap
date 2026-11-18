# -*- coding: utf-8 -*-
"""AI 작성 고지(2026-11-18 대표 결정) — 글 페이지 본문 끝에만, 화면에만 한 번 싣는다.

왜 이 시험이 있나. 글은 AI 가 쓰고 대표가 전편을 검수하지 못한다. 그래서 글 페이지마다 '본 콘텐츠는 AI가
생성한 저작물로 …' 한 칸을 둔다(make_content_pages.AI_NOTICE). 대표 결정은 셋이다.
  ① 글 페이지(/city/·/gtx/·/danji/·/column/ 의 글)에만 — 섹션 목록·허브·데이터 페이지에는 싣지 않는다.
  ② 본문 끝, FAQ 뒤·'이전·다음 글' 앞(설명은 콘텐츠 아래 — CLAUDE.md 화면 설계 원칙).
  ③ 화면에만 — 설명 메타·JSON-LD·RSS(feed.xml)·llms-full.txt 에는 넣지 않는다.
읽는 문장이라 글자는 site_nav.READ_PX(14px) 이상이다.

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - build_page 의 본문 꼴 인자에서 AI_NOTICE_HTML 을 빼면 → test_post_page_carries_the_notice_once_after_the_faq
  - 고지를 FAQ 앞(src_html 앞)으로 옮기면 → 같은 시험(순서 검사)
  - EXTRA_CSS 의 .cai 를 13px 로 내리면 → test_notice_is_reading_size
  - 고지를 body_html(본문 마크다운 결과)에도 붙이면 두 번 실려 → test_post_page_carries_the_notice_once_after_the_faq
  - _ld 의 Article description 에 고지를 붙이면 → test_notice_stays_off_json_ld
  - build_index 나 build_reports 에 고지를 붙이면 → test_lists_do_not_carry_the_notice
픽스처: tmp_path 에 쓴 원고 한 편(test_content_pages 의 FRONT 와 같은 양식, FAQ 있음)과 저장소의 실제
data-*.json. 구운 파일 검사는 저장소에 실제로 구워진 글·feed·llms-full 을 읽는다(CI 는 생성기를 먼저 돌린다).
"""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import content_md as CM            # noqa: E402
import content_tables as CT        # noqa: E402
import make_content_pages as MC    # noqa: E402
import site_nav as N               # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

FRONT = """---
title: 시험용 글 제목
summary: 시험이 쓰는 요약입니다. 마흔 자를 넘기도록 한 문단으로 적고, 답변 블록에 그대로 실립니다.
date: 2026-10-20
updated: 2026-10-27
section: city
region: 인천
tldr:
  - 첫째 줄 결론입니다
  - 둘째 줄 근거입니다
  - 셋째 줄 전망입니다
audience: 2027년 인천 전세 시점을 재는 실수요자
key:
  - label: 시험용 숫자
    value: "12"
city:
  - 인천 연수구
topic: moveins
sources:
  - 국토교통부 주택건설실적통계(인허가·착공·준공)
faq:
  - q: 질문입니다
    a: 답변입니다
---

## 머리글

문단입니다.
"""


def _page(tmp_path):
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'test-post.md'
    p.write_text(FRONT, encoding='utf-8')
    meta, body = CM.read(str(p))
    data = CT.load()
    meta = CT.fill_meta(meta, data)
    page, _ = MC.build_page(meta, body, data)
    return meta, page


def test_post_page_carries_the_notice_once_after_the_faq(tmp_path):
    _, page = _page(tmp_path)
    assert page.count(MC.AI_NOTICE) == 1, 'AI 작성 고지가 글 페이지에 정확히 한 번 있어야 한다'
    i_faq, i_ai, i_nav = page.find('class="cfaq"'), page.find('class="cai"'), page.find('class="cnav"')
    assert -1 < i_faq < i_ai < i_nav, '고지는 FAQ 뒤, 이전·다음 글 앞(본문 끝)에 있어야 한다'
    assert '투자자문이 아닙니다' in page, '푸터 면책(투자자문 아님)은 그대로 남아야 한다'


def test_notice_is_reading_size():
    m = re.search(r'\.cai\{[^}]*font-size:([\d.]+)px', MC.EXTRA_CSS)
    assert m, '.cai 의 글자 크기 규칙이 없다'
    assert float(m.group(1)) >= N.READ_PX, '고지는 읽는 문장이라 READ_PX 이상이어야 한다'


def test_notice_stays_off_json_ld(tmp_path):
    """화면에만 — 구조화 데이터(articleBody·description)에는 싣지 않는다(대표 결정 ③)."""
    _, page = _page(tmp_path)
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        assert MC.AI_NOTICE not in json.dumps(json.loads(blob), ensure_ascii=False), 'JSON-LD 에 고지가 실렸다'
    for m in re.finditer(r'<meta [^>]*content="([^"]*)"', page):
        assert MC.AI_NOTICE not in m.group(1), '설명 메타에 고지가 실렸다'


def test_lists_do_not_carry_the_notice(tmp_path):
    meta, _ = _page(tmp_path)
    idx, _ = MC.build_index('city', [meta])
    assert MC.AI_NOTICE not in idx, '섹션 목록 페이지에는 고지를 싣지 않는다'
    hub = MC.build_reports([meta])
    hub = hub[0] if isinstance(hub, tuple) else hub
    assert MC.AI_NOTICE not in hub, '허브(/reports/)에는 고지를 싣지 않는다'


def test_baked_posts_carry_it_and_feeds_do_not():
    """저장소에 실제로 구워진 글은 모두 고지를 한 번씩 싣고, feed·llms-full 에는 없다."""
    posts = [os.path.join(ROOT, sec, slug, 'index.html') for sec, slug, _ in CM.built(ROOT)]
    posts = [f for f in posts if os.path.exists(f)]
    if not posts:
        pytest.skip('구워진 글이 없다')
    for f in posts:
        n = io.open(f, encoding='utf-8').read().count(MC.AI_NOTICE)
        assert n == 1, '%s: 고지가 %d번 있다' % (os.path.relpath(f, ROOT), n)
    for name in ('feed.xml', 'llms.txt', 'llms-full.txt'):
        f = os.path.join(ROOT, name)
        if os.path.exists(f):
            assert MC.AI_NOTICE not in io.open(f, encoding='utf-8').read(), '%s 에 고지가 실렸다' % name
