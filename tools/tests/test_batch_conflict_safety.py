# -*- coding: utf-8 -*-
"""배치의 rebase 충돌 자동 해소는 **다시 구울 수 있는 생성물**만 덮는다(백로그 59).

예전엔 `index.html`·`cycle/index.html`만 예외로 두고 나머지 충돌은 우리(새 데이터) 쪽으로 해소했다. 그래서 수집 중
main 에 올라온 **data.js 손수정**(--heal-basic 이력 교정 등)이나 발행 런의 결과가 조용히 되돌아갈 수 있었다.
지금은 화이트리스트(생성 페이지·피드·지도·카드·data-*.json)만 자동 해소하고, 정본이 섞이면 멈춘다.
"""
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
YML = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')


def _t():
    return io.open(YML, encoding='utf-8').read()


def _safe():
    m = re.search(r"^\s+SAFE_ERE='(.+)'$", _t(), re.M)
    assert m, 'update-cloud.yml 에서 충돌 자동 해소 화이트리스트(SAFE_ERE)를 찾지 못했다'
    return re.compile(m.group(1))


def test_regenerable_outputs_are_auto_resolved():
    """다음 산출물 재생성이 같은 코드·원고로 다시 만드는 파일은 자동 해소해도 된다.

    변이(실제로 확인): 화이트리스트에서 생성 페이지 디렉터리 하나를 빼면 이 시험이 빨개진다.
    """
    safe = _safe()
    for p in ('zone/서울/index.html', 'weekly/index.html', 'monthly/index.html', 'moveins/index.html',
              'jeonse-ratio/index.html', 'city/x/index.html', 'gtx/y/index.html', 'danji/z/index.html',
              'column/w/index.html', 'reports/index.html', 'share/post-city-x.png',
              'feed.xml', 'llms.txt', 'llms-full.txt', 'sitemap.xml',
              'data-trend.json', 'data-size.json', 'data-rest.json'):
        assert safe.search(p), p


def test_source_of_truth_is_not_overwritten():
    """data.js·data-core.js·손 문장이 섞인 파일·원고·워크플로는 자동 해소 대상이 아니다.

    변이(실제로 확인): 화이트리스트에 data.js 를 넣으면 이 시험이 빨개진다.
    """
    safe = _safe()
    for p in ('data.js', 'data-core.js', 'index.html', 'cycle/index.html',
              'tools/data/city_moveins.json', 'tools/split_data.py', 'content/city/x.md',
              '.github/workflows/watchdog.yml'):
        assert not safe.search(p), p


def test_workflow_stops_on_unsafe_conflicts():
    """화이트리스트 밖 충돌이면 자동 해소하지 않고 멈춘다 — 되돌릴 수 없는 손수정을 덮지 않는다.

    변이(실제로 확인): 아래 두 줄(UNSAFE 계산·STOP="unsafe")을 지우면 이 시험이 빨개진다.
    """
    t = _t()
    assert 'UNSAFE=$(printf' in t, '충돌 파일을 화이트리스트로 거르는 계산이 없다'
    assert 'STOP="unsafe"' in t, '화이트리스트 밖 충돌에서 멈추지 않는다'
    assert '사람 손수정·정본(data.js 등)' in t, '멈춘 이유를 사람에게 알리지 않는다'
