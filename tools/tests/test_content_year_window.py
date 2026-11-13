# -*- coding: utf-8 -*-
"""도시 글의 3년 창은 글의 작성 연도가 정한다 — 해가 바뀌어도 글이 말하는 해·숫자가 그대로다(2026-11-13 대표 결정 '글이 연도를 고정').

예전 창은 수집 목록의 기준월을 따라 굴렀다. 2027-01-01 첫 배치에서 창이 2028~2030 으로 넘어가 2030 년분이 아직 없는 글(전주·
원주·gtx-b-bucheon)이 기다림으로 빠지고, 그 글을 전제하는 시험 넷이 빨개져 그날 데이터 커밋이 멈출 참이었다(전수 리뷰 T1).
"""
import copy
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import content_md as CM             # noqa: E402
import content_tables as CT         # noqa: E402
import make_city_moveins as MCM     # noqa: E402
import make_content_pages as MC     # noqa: E402


@pytest.fixture(scope='module')
def data():
    return CT.load()


def _rolled(data):
    """새해 첫 배치의 저장 모양 — 수집 기준월이 다음 해 1월로 넘어가고, 그보다 앞 해의 단지는 목록에서 빠진다."""
    d = copy.deepcopy(data)
    c = d.get('cities') or {}
    y = int((c.get('start') or '2026-01')[:4]) + 1
    c['start'] = '%d-01' % y
    for f in (c.get('cities') or {}).values():
        f['by_year'] = {k: v for k, v in (f.get('by_year') or {}).items() if int(k) >= y}
        f['by_year_gu'] = {k: v for k, v in (f.get('by_year_gu') or {}).items() if int(k) >= y}
        f['rows'] = [r for r in (f.get('rows') or []) if int(r['ym'][:4]) >= y]
    return d


def _outcome(meta, body, data):
    """한 편이 창에 기대어 말하는 것 — 구워지는가(기다림·탈이면 그 이름), 제목·요약, 본문 값 자리표, 그림 카드·3년 줄.

    표 전체는 견주지 않는다 — 새해 목록에서 지난해 단지가 빠지면 '연도별' 표의 첫 줄이 빠지는 것은 창과 무관한 원천의 사정이다.
    """
    try:
        m = CT.fill_meta(meta, data)
        MC.build_page(m, body, data)
    except CT.Pending:
        return '기다림'
    except Exception as e:      # noqa: BLE001
        return type(e).__name__
    d = CT.for_post(data, meta)
    got = [m['title'], m['summary']]
    for kind, inner in CT.PH.findall(body):
        parts = [x.strip() for x in inner.split(':')]
        if kind == 'v':
            got.append(CT.value(d, parts[0], parts[1:]))
        elif kind == 'chart' and parts[0] == 'moveins':
            spec = CT.chart(d, parts[0], parts[1:])
            got.append((spec.get('cards'), spec.get('foot')))
    return tuple(got)


def test_new_year_batch_keeps_every_post_and_its_numbers(data):
    """새해 첫 배치(기준월이 다음 해 1월)에도 모든 글이 지금과 **같은 제목·요약·본문 숫자**로 구워진다.

    변이(실제로 확인): content_tables.for_post 가 data 를 그대로 돌려주면(예전처럼 창이 기준월을 따라 구르면) 3년 합계를 쓰는 글의
          숫자가 바뀌거나 기다림으로 빠져 빨개진다. make_content_pages.build_page 의 for_post 줄만 지워도 본문 쪽이 빨개진다.
    픽스처: 실제 원고 전부와 실제 데이터, 그리고 그 데이터를 새해 첫 배치 모양으로 민 판(_rolled — 기준월 다음 해 1월, 앞 해 단지 빠짐).
    """
    rolled = _rolled(data)
    changed = []
    for sec, slug, path in CM.posts(ROOT):
        try:
            meta, body = CM.read(path, sec, slug)
        except CM.ContentError:
            continue
        now, then = _outcome(meta, body, data), _outcome(meta, body, rolled)
        if now != then and not isinstance(now, str):
            changed.append('%s/%s: %s' % (sec, slug, then if isinstance(then, str) else '숫자가 바뀜'))
    assert not changed, '해가 바뀌자 달라지는 글:\n' + '\n'.join(changed)


def test_a_listed_year_without_complexes_is_zero_not_waiting():
    """목록이 그 해를 끝까지 덮는데(occ_max 가 그 뒤 해) 단지가 없으면 그 해는 0 이다 — 기다림으로 글을 세우지 않는다.

    변이(실제로 확인): city_moveins3_n 의 `_listed` 갈래를 지우면 기다림(PendingYear)으로 떨어져 빨개진다. _city_years 의 같은
          갈래를 지우면 v:share 가 TableError 로 빨개진다.
    픽스처: 2027·2029 에만 단지가 있고 목록 끝이 2030-06 인 도시(가운데 해가 빈 실제 모양 — 안산 2028).
    """
    f = {'by_year': {'2027': 500, '2029': 700}, 'need': 1000, 'occ_max': '2030-06'}
    d = {'from_year': 2027}
    assert CT.city_moveins3_n(d, f, '가') == 1200
    assert CT.city_share(d, f, '2028') == '0%'
    f['occ_max'] = '2028-06'      # 목록이 2029 를 다 덮지 못하면 그 해는 기다린다
    with pytest.raises(CT.PendingYear):
        CT.city_moveins3_n(d, dict(f, by_year={'2027': 500}), '가')


def test_the_list_starts_no_later_than_the_earliest_post_window(tmp_path, monkeypatch):
    """수집 목록의 시작 달은 이번 달이되, 원고가 고정한 가장 이른 창의 1월보다 늦지 않다.

    변이(실제로 확인): make_city_moveins.main 이 예전처럼 이번 달(today)을 시작으로 쓰면, 또는 list_start 의 min 을 today 로 바꾸면
          2027년 중의 회차에 '2027-06' 이 나와 빨개진다(2026년에 쓴 글의 2027년 합계가 달마다 줄어든다).
    픽스처: 2026년에 쓴 실제 원고 전부(가장 이른 창 2027).
    """
    first = min(int(str(CM.read(p, s, g)[0]['date'])[:4]) + 1 for s, g, p in CM.posts(ROOT))
    assert MCM.list_start('%d-06' % first) == '%d-01' % first
    assert MCM.list_start('%d-11' % (first - 1)) == '%d-11' % (first - 1)     # 창이 아직 오지 않았으면 이번 달 그대로
