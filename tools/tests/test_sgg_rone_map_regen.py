# -*- coding: utf-8 -*-
"""시군구 매핑 재생성 도구(gen_sgg_rone_map)가 R-ONE 계층이 바뀐 뒤에도 현재 매핑을 그대로 다시 만드는지 본다(전수리뷰 A-9).

재현하는 실제 상태: R-ONE 이 광주·전남을 '전남광주>광주'·'전남광주>전남' 밑으로 옮긴 계층(update_adv_data 월간 수집 주석·
2026-08-07 감사). 예전 도구는 CLS_FULLNM 첫 토큰을 시도로 보고 깊이 1 행만 시도 레벨로 받아, 이 계층에서 광주·전남 시도 둘과
시군구 11개를 못 붙였다(합성 응답으로 재현 — 평평한 계층에서는 208개 일치). 인천 신설 4구처럼 현재 매핑에 없는 코드는 원천이
내면 '신규'로 잡혀야 한다(월간 매핑 공백, A-6). 주간 매핑(SGG_RONE_CLS_WK)도 같은 도구로 다시 만든다(옛 gen_map_wk.py 는 없었다).
픽스처: 실제 SGG_QNAME 이름과 현재 매핑 값으로 만든 R-ONE 최신 시점 응답 — 같은 이름의 다른 시도 구('부산>동구'), 경기 광주시
('경기>광주시'), 통합 지역 마디('전남광주'), 한 시점 앞의 옛 행(다른 CLS_ID)을 미끼로 둔다. 코드 목록은 그 일부로 줄인다.

변이(각각 실제로 확인):
  - build() 의 시도 판정을 예전처럼 `parts[0]` 으로 되돌리면 계층 응답 시험이 빨개진다(광주·전남 시군구 못 찾음).
  - 시도 행(top)을 예전처럼 깊이 1 행에서만 받으면 계층 응답 시험이 빨개진다(광주·전남 시도 레벨 없음).
  - main() 의 '현재에만' 쓰기 거부를 지우면 쓰기 거부 시험이 빨개진다.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import gen_sgg_rone_map as G   # noqa: E402
import update_adv_data as U    # noqa: E402
from merge_regions import DST  # noqa: E402

# 광주·전남 시도와 시군구 전부 + 이름이 겹치는 다른 시도 구·경기 광주시·인천 신설구 하나
CODES = (['a0', 'a7', 'a7010201', 'a8', 'a80404', 'a9', 'a903', 'a901', 'b1', 'b3', 'c5']
         + [c for c in U.SGG_CODES if c[:2] in ('b3', 'c5') and len(c) > 2])
SFX = {'a7010201': '구', 'a80404': '시', 'a903': '구', 'a901': '구'}


def _name(code, qn):
    """R-ONE CLS_NM — 홈 SGG_QNAME 의 마지막 토큰에 원천 접미사(시·군·구)를 붙인 모양."""
    leaf = qn[code].split(' ')[-1]
    return leaf if leaf.endswith(('시', '군', '구')) else leaf + ('군' if code == 'c506' else '시')


def _rows(kind, hier, cur, stamps):
    """R-ONE 최신 시점 응답(stamps[-1]) + 한 시점 앞 옛 행. hier 면 광주·전남이 통합 지역 밑에 있다."""
    qn = G.qname_map()
    up = (DST + '>') if hier else ''
    sido = {'a0': '전국', 'a7': '서울', 'a8': '경기', 'a9': '인천', 'b1': '부산',
            'b3': up + G.SIDO_PREFIX['b3'], 'c5': up + G.SIDO_PREFIX['c5']}
    path = {'a7010201': '서울>강북지역>동북권', 'a80404': '경기', 'a903': '인천', 'a901': '인천'}
    rows = [(sido[c], cur[c]) for c in sido]
    for c in CODES:
        if c in sido or c not in cur:
            continue
        parent = path.get(c) or sido[c[:2]]
        rows.append((parent + '>' + _name(c, qn), cur[c]))
    rows += [('부산>동구', 990001), ('경기>광주시>오포읍', 990002), (DST, 990003)]
    field = G.KINDS[kind][2]
    out = [{'CLS_FULLNM': f, 'CLS_NM': f.split('>')[-1], 'CLS_ID': cid, field: stamps[-1]} for f, cid in rows]
    out += [{'CLS_FULLNM': f, 'CLS_NM': f.split('>')[-1], 'CLS_ID': 880000 + i, field: stamps[0]}
            for i, (f, _) in enumerate(rows)]
    return out


def _setup(monkeypatch):
    monkeypatch.setattr(U, 'SGG_CODES', list(CODES))
    qn = G.qname_map()
    monkeypatch.setattr(G, 'qname_map', lambda: dict(qn))


@pytest.mark.parametrize('hier', [False, True])
def test_monthly_map_is_rebuilt_on_flat_and_merged_hierarchy(monkeypatch, hier):
    _setup(monkeypatch)
    # 픽스처는 '매핑에 아직 없는 시군구가 하나 있는' 상태를 **스스로 만든다**. 예전에는 실제 매핑에
    # a901(인천 제물포)이 없다는 데 기대고 있었는데, 2026-10-29 그 넷을 매핑에 더하자 전제가 깨져
    # 이 시험이 빨개졌다 — 시험은 저장소의 그날 상태가 아니라 재생성 도구의 동작을 보아야 한다.
    cur = {k: v for k, v in U.SGG_RONE_CLS.items() if k != 'a901'}
    assert 'a901' in CODES, '픽스처 전제: a901 은 KOSIS 코드 목록에 있다'
    want = {c: cur[c] for c in CODES if c in cur}
    built, miss = G.build('monthly', rows=_rows('monthly', hier, cur, ['202608', '202609']))
    assert built == want, '재생성이 현재 매핑과 다르다: %s' % sorted(set(built.items()) ^ set(want.items()))[:6]
    # 사유 문구는 구현 세부다(원천에 아예 없으면 'R-ONE 미수록', 시도 밑에서 못 찾으면 '… 못 찾음').
    # 중요한 것은 매핑에 없는 코드가 조용히 빠지지 않고 miss 로 올라온다는 것이다.
    assert [m[0] for m in miss] == ['a901'] and miss[0][2]
    # 원천이 신설구를 내기 시작하면 '신규'로 붙는다 — 저절로 매핑에 들어가지는 않는다(A-6)
    cur2 = dict(cur, a901=777001)
    built, miss = G.build('monthly', rows=_rows('monthly', hier, cur2, ['202608', '202609']))
    assert built.get('a901') == 777001 and not miss


def test_weekly_map_uses_the_same_tool(monkeypatch):
    _setup(monkeypatch)
    cur = dict(U.SGG_RONE_CLS_WK)
    want = {c: cur[c] for c in CODES}
    built, miss = G.build('weekly', rows=_rows('weekly', True, cur, ['2026-10-05', '2026-10-12']))
    assert built == want and not miss


def test_write_refuses_when_a_current_code_is_lost(monkeypatch, tmp_path):
    _setup(monkeypatch)
    cur = {c: v for c, v in U.SGG_RONE_CLS.items() if c in CODES}
    monkeypatch.setattr(U, 'SGG_RONE_CLS', dict(cur))                              # 대조 대상도 같은 코드로 줄인다
    rows = [r for r in _rows('monthly', True, cur, ['202608', '202609'])
            if not r['CLS_FULLNM'].endswith('>' + G.SIDO_PREFIX['b3'])]          # 광주 시도 행이 빠진 응답
    monkeypatch.setattr(G, 'rone_rows', lambda kind: rows)
    monkeypatch.setattr(G, 'HERE', str(tmp_path))
    with pytest.raises(SystemExit) as e:
        G.main(['--write'])
    assert 'b3' in str(e.value) and not (tmp_path / 'data').exists()
    # 다 붙으면 쓴다(저장소가 아니라 임시 폴더로)
    monkeypatch.setattr(G, 'rone_rows', lambda kind: _rows('monthly', True, cur, ['202608', '202609']))
    assert G.main(['--write']) == 0
    got = json.load(open(str(tmp_path / 'data' / 'sgg_rone_cls.json'), encoding='utf-8'))
    assert got == {c: cur[c] for c in CODES if c in cur}
