# -*- coding: utf-8 -*-
"""광역시 단지 목록 — 수집기는 광역시를 원고 없이도 받고, 글은 적정물량·해마다 입주를 시도 값으로 말한다.

2026-11-13 대표 결정: 시도 리포트(/zone/대구/)로 들어온 독자가 이어 읽을 광역시 글을 쓴다. 광역시는 도시이면서 곧 시도라
도시 산식(인구 ÷ 2.5 × 2%)을 쓰면 같은 지역을 리포트와 다른 숫자로 말하게 되므로(대구 20,000 대 약 18,900세대), 적정물량·
해마다 입주·비율은 시도 값을 쓰고 단지 목록·몰리는 달·인구만 도시 묶음에서 읽는다.
"""
import io
import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import city_movein as CMV           # noqa: E402
import content_tables as CT         # noqa: E402
import make_city_moveins as MCM     # noqa: E402
import sido_zones as SZ             # noqa: E402


@pytest.fixture(scope='module')
def data():
    return CT.load()


def _metro_key(data):
    """시도 판정 자료가 있는 광역시 하나 — 데이터에서 고른다(이름을 박지 않는다)."""
    zones = {z['z'] for z in (data['sido'].get('zones') or [])}
    return next(k for k in MCM.metro_cities() if k in zones)


def _city_record(city, n_by_year, need=1):
    """도시 묶음 한 벌 — 적정물량을 일부러 1세대로 둬, 도시 산식이 새면 비율이 터무니없이 커지게 한다."""
    rows = [{'ym': '%s-03' % y, 'name': '%s 단지 %s' % (city, y), 'gu': '가구' if i % 2 else '나구', 'n': n, 'kind': '분양',
             'src': '입주예정물량정보'} for i, (y, n) in enumerate(sorted(n_by_year.items()))]
    return {'sido': city, 'start': '2026-11', 'occ_max': '2029-06', 'as_of': '2026-11-13', 'pop': 2400000, 'pop_prd': '202610',
            'need': need, 'need_note': '인구 ÷ 2.5 × 2%', 'by_year': dict(n_by_year),
            'by_year_gu': {y: {'가구': n} for y, n in n_by_year.items()}, 'rows': rows}


def test_metro_cities_come_from_the_source_names_not_a_hand_list():
    """광역시 목록은 원천 주소의 시도 전체 이름이 '…시' 하나인 키다 — 도(경기)·통합 단위(광주·전남)·묶음(전국)은 빠진다.

    변이(실제로 확인): metro_cities 의 `full[0].endswith('시')` 를 지우면 경기·경북 같은 도가 '도시'로 들어와 빨개진다.
          `len(full) == 1` 만 지우면 초록이다 — 전남광주는 이름표에 '전남광주 …' 이름이 없어 sido_of 에서도 빠지기 때문이고,
          그 조건은 이름표가 통합 키로 바뀌는 날의 겹 막이로 둔다. 수집 목록에서 광역시를 빼면(cities_wanted 의 update) 끝 단정이
          빨개진다.
    픽스처: 실제 판정 단위 목록(sido_zones.ORDER)과 실제 시군구 이름표.
    """
    got = MCM.metro_cities()
    for k in SZ.ORDER:
        full = CMV.full_names(k)
        if len(full) == 1 and full[0].endswith('시'):
            assert got.get(k) == k, '%s(%s) 가 광역시 목록에서 빠졌다' % (k, full[0])
        else:
            assert k not in got, '%s 는 광역시가 아니다(%s)' % (k, ', '.join(full) or '원천 이름 없음')
    assert got, '광역시가 하나도 없다'
    wanted = MCM.cities_wanted()
    assert set(got) <= set(wanted), '수집 목록에 광역시가 빠졌다 — 원고가 없는 광역시는 영영 받지 못한다'
    assert set(MCM.cities_from_content()) <= set(wanted)


def test_metro_posts_speak_sido_numbers_and_list_complexes(data):
    """광역시 이름의 자리표: 적정물량·비율·해마다 입주는 시도 값, 단지 목록·몰리는 달·인구는 도시 묶음에서.

    변이(실제로 확인): content_tables.city 의 `if _is_zone(name): return None` 을 지우면 v:need·v:share 가 도시 산식
          (픽스처의 적정물량 1세대)으로 바뀌어 빨개진다. table complexes 갈래의 `listing` 을 `city` 로 되돌리면 단지 목록이
          기다림으로 떨어져 빨개진다. ratio 갈래의 시도 막이를 지우면 기다림(영영 구워지지 않는다)으로 떨어져 빨개진다.
    픽스처: 실제 데이터에 그 광역시의 도시 묶음(적정물량 1세대, 세 해 단지)을 끼운 판.
    """
    key = _metro_key(data)
    year = str(sorted(r[0] for r in CT.moveins(data, key)[1] if r[0] != '합계')[-1])
    plain = (CT.value(data, 'need', [key]), CT.value(data, 'share', [key, year]))
    d = dict(data)
    d['cities'] = {'start': '2026-11', 'cities': {key: _city_record(key, {'2027': 900, '2028': 1500, '2029': 300})}}
    assert (CT.value(d, 'need', [key]), CT.value(d, 'share', [key, year])) == plain, \
        '광역시 글의 적정물량·비율이 시도 리포트와 갈린다(도시 산식이 샜다)'
    assert CT.value(d, 'need', [key]) == CT.sido_need(d, key)
    head, body, note = CT.table(d, 'complexes', [key, '2028'])
    assert [r[-1] for r in body] == ['1,500'] and '단지' in head[1]
    assert CT.value(d, 'peak', [key]) == '2028년 3월 1,500세대'
    assert CT.value(d, 'pop', [key]).startswith('2,400,000명')
    with pytest.raises(CT.TableError) as e:
        CT.value(d, 'ratio', [key, '2028', '2027'])
    assert not isinstance(e.value, CT.Pending), 'ratio 가 기다림으로 떨어진다 — 광역시 묶음은 city() 가 읽지 않아 영영 구워지지 않는다'
    # 자료가 아직 없으면 단지 목록은 기다림이다(수집기가 광역시를 늘 받는다)
    d['cities'] = {'start': '2026-11', 'cities': {}}
    with pytest.raises(CT.PendingCity):
        CT.table(d, 'complexes', [key, '2028'])


def test_adopt_keeps_metro_cities_without_a_post(tmp_path, monkeypatch):
    """커밋 잡의 싣기(adopt)는 광역시를 '원고가 안 쓰는 도시'로 보고 지우지 않는다 — 수집과 같은 목록(cities_wanted)을 쓴다.

    변이(실제로 확인): adopt 의 기본 목록을 cities_from_content() 로 되돌리면 광역시가 빠져 빨개진다.
    픽스처: 저장소 파일에 광역시 하나, 받아 온 파일에는 그 광역시가 없는 회차(그 시도 수집만 실패한 날).
    """
    key = MCM.metro_cities()
    key = sorted(key)[0]
    out = tmp_path / 'city_moveins.json'
    out.write_text(json.dumps({'cities': {key: {'n': 1}}}), encoding='utf-8')
    fresh = tmp_path / 'fresh.json'
    fresh.write_text(json.dumps({'start': '2026-11', 'cities': {}}), encoding='utf-8')
    n, kept = MCM.adopt(str(fresh), out=str(out))
    assert kept == [key] and key in json.loads(out.read_text(encoding='utf-8'))['cities']


def test_nation_tables_are_fetched_once_per_run(tmp_path, monkeypatch):
    """시도를 여럿 받아도 전국 표(입주예정물량정보·주민등록인구)는 한 번만 받는다 — 수집 잡의 600초 상한 안에 들게.

    변이(실제로 확인): fetch 가 _occ_all 대신 예전처럼 매번 OCC_API 를 돌면 입주예정 호출이 시도 수만큼 늘어 빨개진다.
    픽스처: 원천 호출을 세는 가짜 _get(한 쪽짜리 응답)과 가짜 KOSIS, 임시 캐시 폴더.
    """
    calls = []

    def fake_get(url, params):
        calls.append(url)
        return {'data': [{'x': 1}], 'totalCount': 1, 'matchCount': 1}

    import update_adv_data as U
    monkeypatch.setattr(CMV, '_get', fake_get)
    monkeypatch.setattr(CMV, 'CACHE', str(tmp_path))
    monkeypatch.setattr(CMV, '_NATION', {})
    monkeypatch.setattr(U, 'kosis', lambda tbl: calls.append('kosis') or [])
    for sido in sorted(MCM.metro_cities())[:3]:
        CMV.fetch(sido)
    assert calls.count(CMV.OCC_API) == 1 and calls.count('kosis') == 1, calls
    assert calls.count(CMV.CH_API) == 3
