# -*- coding: utf-8 -*-
"""AI 작성 고지(2026-11-18 대표 결정) — 작문이 들어간 페이지의 푸터에서 면책 바로 위 한 줄.

왜 이 시험이 있나. 글과 리포트 문장은 AI 가 쓰고 대표가 전편을 검수하지 못한다. 그래서 '본 콘텐츠는 AI가 생성한
저작물로 …'(site_nav.AI_NOTICE)를 싣는다. 대표 결정은 셋이다.
  ① 싣는 곳: 콘텐츠 글(/city/·/gtx/·/danji/·/column/ 의 글), 시도 리포트(/zone/<지역>/), /weekly/, /monthly/.
     싣지 않는 곳: 허브·섹션 목록(/zone/·/reports/·/city/ 등), 지표 두 쪽(/jeonse-ratio/·/moveins/), /cycle/, 손 페이지.
  ② 자리: 공용 푸터(site_nav.site_footer(src, ai=True)) 하나 — 면책 바로 위. 페이지마다 따로 두지 않는다.
  ③ 화면에만: 설명 메타·JSON-LD·RSS·llms 에는 넣지 않는다.
읽는 문장이라 글자는 site_nav.READ_PX(14px) 이상이다.

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - site_footer 가 ai 인자를 무시하면 → test_footer_switch, 그리고 구운 페이지 시험
  - site_footer 의 기본값을 ai=True 로 바꾸면 → test_footer_switch, test_lists_do_not_carry_it
  - AI_DISC 의 인라인 크기를 13px 로 내리면 → test_notice_is_reading_size
  - make_content_pages.build_page 의 fill 에서 ai=True 를 빼면 → test_generators_switch_it_on
  - make_sido_pages 리포트가 FOOT_REPORT 대신 FOOT 를 쓰면 → test_generators_switch_it_on
  - make_weekly_page.put_footer 나 make_monthly_page 의 fill 에서 ai=True 를 빼면 → test_generators_switch_it_on(주간)·
    test_baked_pages(월간)
  - _ld(Article description)에 고지를 붙이면 → test_notice_stays_off_machine_text
픽스처: tmp_path 에 쓴 원고 한 편(2026-11-05 양식)과 저장소의 실제 data-*.json, 그리고 저장소에 구워진 페이지
(CI 는 생성기를 먼저 돌린다 — 굽기 전 작업 트리에서는 구운 페이지 시험이 옛 산출물을 본다).
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
import make_indicator_pages as I   # noqa: E402
import make_sido_pages as SP       # noqa: E402
import make_weekly_page as MW      # noqa: E402
import sido_zones as SZ            # noqa: E402
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


def _post(tmp_path):
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True, exist_ok=True)
    p = d / 'test-post.md'
    p.write_text(FRONT, encoding='utf-8')
    meta, body = CM.read(str(p))
    data = CT.load()
    meta = CT.fill_meta(meta, data)
    page, _ = MC.build_page(meta, body, data)
    return meta, page


def _foot(page):
    m = re.search(r'<footer\b.*?</footer>', page, re.S)
    return m.group(0) if m else ''


def test_footer_switch():
    on, off = N.site_footer('국토교통부', ai=True), N.site_footer('국토교통부')
    assert on.count(N.AI_NOTICE) == 1 and N.AI_NOTICE not in off, 'ai=True 일 때만 고지가 한 번 실려야 한다'
    assert on.find(N.AI_NOTICE) < on.find(N.DISCLAIMER), '고지는 면책 바로 위에 있어야 한다'
    assert on.count(N.DISCLAIMER) == 1, '투자자문 면책은 그대로 한 번'


def test_notice_is_reading_size():
    m = re.search(r'font-size:\s*([\d.]+)px[^"]*"[^>]*>\s*' + re.escape(N.AI_NOTICE), N.AI_DISC)
    assert m and float(m.group(1)) >= N.READ_PX, '고지는 읽는 문장이라 READ_PX 이상이어야 한다'


def test_generators_switch_it_on(tmp_path):
    _, page = _post(tmp_path)
    assert N.AI_NOTICE in _foot(page), '콘텐츠 글의 푸터에 고지가 없다'
    assert N.AI_NOTICE in SP.FOOT_REPORT and N.AI_NOTICE not in SP.FOOT, '시도 리포트에만, 허브에는 없이'
    w = MW.put_footer('<footer><div class="wrap">옛 푸터</div></footer>')
    assert N.AI_NOTICE in w, '/weekly/ 푸터에 고지가 없다'
    assert N.AI_NOTICE not in I.fill(I.SHELL, src='국토교통부'), '지표 쪽(기본 fill)에는 싣지 않는다'


def test_lists_do_not_carry_it(tmp_path):
    meta, _ = _post(tmp_path)
    idx, _ = MC.build_index('city', [meta])
    assert N.AI_NOTICE not in idx, '섹션 목록 페이지에는 싣지 않는다'
    hub = MC.build_reports([meta])
    hub = hub[0] if isinstance(hub, tuple) else hub
    assert N.AI_NOTICE not in hub, '콘텐츠 허브에는 싣지 않는다'


def _machine_text(page):
    """화면 밖 글자 — JSON-LD 와 메타 content."""
    out = [json.dumps(json.loads(b), ensure_ascii=False)
           for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)]
    out += re.findall(r'<meta [^>]*content="([^"]*)"', page)
    return out


def test_notice_stays_off_machine_text(tmp_path):
    _, page = _post(tmp_path)
    assert not [t for t in _machine_text(page) if N.AI_NOTICE in t], 'JSON-LD·설명 메타에 고지가 실렸다'


def _read(rel):
    p = os.path.join(ROOT, rel)
    return io.open(p, encoding='utf-8').read() if os.path.exists(p) else None


def test_baked_pages():
    """구워진 페이지: 싣는 곳은 모두 푸터에 한 번, 싣지 않는 곳과 feed·llms 에는 없다."""
    want = [os.path.join(sec, slug, 'index.html') for sec, slug, _ in CM.built(ROOT)]
    want += [os.path.join('zone', z, 'index.html') for z in SZ.DISPLAY_ORDER]
    want += ['weekly/index.html', 'monthly/index.html']
    want = [r for r in want if os.path.exists(os.path.join(ROOT, r))]
    if not want:
        pytest.skip('구워진 페이지가 없다')
    for rel in want:
        page = _read(rel)
        assert page.count(N.AI_NOTICE) == 1 and N.AI_NOTICE in _foot(page), '%s: 푸터에 고지가 한 번 있어야 한다' % rel
        assert not [t for t in _machine_text(page) if N.AI_NOTICE in t], '%s: JSON-LD·메타에 고지가 실렸다' % rel
    nots = ['zone/index.html', 'reports/index.html', 'jeonse-ratio/index.html', 'moveins/index.html',
            'cycle/index.html', 'about/index.html', 'faq/index.html', 'privacy/index.html', '404.html',
            'feed.xml', 'llms.txt', 'llms-full.txt']
    nots += [os.path.join(sec, 'index.html') for sec in MC.SECTION_META]
    for rel in nots:
        page = _read(rel)
        if page is not None:
            assert N.AI_NOTICE not in page, '%s 에는 고지를 싣지 않는다' % rel
