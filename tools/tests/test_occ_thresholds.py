# -*- coding: utf-8 -*-
"""입주물량 '적정 대비' 문턱은 하나다 — 홈 통계 탭(home-stats.js occCls)과 /moveins/ 가 같은 정본(sido_zones.OCC_LO_PCT·
OCC_HI_PCT)을 읽는다(2026-09-30 대표 결정 ③, 전수 리뷰 #60·#113).

재현하는 실제 상태: occCls 는 '적정 이상 = 파랑(hi), 60% 이하 = 빨강(lo)', /moveins/ pct_cell 은 '70% 미만 = 부족(빨강),
130% 초과 = 과잉(파랑)'이었다. 충족률 65% 는 한 화면에서 빨강·다른 화면에서 무색, 110% 는 반대였다(실데이터 분기 칸 중
60~70% 54칸, 130% 초과 173칸이 두 화면에서 갈렸다).
무엇을 깨뜨리면 빨개지나(각각 실제로 확인): occCls 에 `v<=ref*0.6`·`v>=ref` 를 되돌리면 node 대조가, pct_cell 이 70 을 숫자로
다시 적고 정본을 65 로 바꾸면 /moveins/ 대조가, split_data 가 band 를 싣지 않으면 페이로드 단정이 빨개진다.
픽스처: 문턱 앞뒤 충족률(64.4·69.4·69.6·70·100·110·130·130.4·130.6·140%) — 표시 정수로 판정하는 경계(69.6 → 70%)를 포함.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sido_zones as SZ  # noqa: E402
import split_data as S  # noqa: E402
import make_indicator_pages as I  # noqa: E402
import home_src as HS  # noqa: E402

PCTS = (64.4, 69.4, 69.6, 70, 100, 110, 130, 130.4, 130.6, 140)
REF = 1000.0


def _occcls_src():
    src = dict(HS.home_files())['home-stats.js']
    i = src.index('function occCls(region,v){')
    depth, j = 0, src.index('{', i)
    while True:
        depth += (src[j] == '{') - (src[j] == '}')
        j += 1
        if depth == 0:
            return src[i:j]


def _moveins_cls(p):
    """/moveins/ 의 칸 색 규칙(표시 정수 pct_shown → SZ.occ_level, build_moveins.pct_cell 과 같은 두 함수) → 홈 이름
    (up = 부족 = lo, dn = 과잉 = hi). pct_cell 자체가 정본을 읽는지는 test_moveins_uses_the_canon 이 본다."""
    return {-1: 'lo', 1: 'hi', 0: ''}[SZ.occ_level(I.pct_shown(p / 100.0 * REF, REF))]


def test_home_occcls_matches_moveins():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    band = S.occ_band()
    assert band == {'lo': SZ.OCC_LO_PCT, 'hi': SZ.OCC_HI_PCT}
    js = ('var ADV={occupancy:{ref:{X:%s},band:%s}};\n%s\n'
          'process.stdout.write(JSON.stringify(%s.map(function(p){return occCls("X",p/100*%s);})));'
          % (REF, json.dumps(band), _occcls_src(), json.dumps(PCTS), REF))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    home = json.loads(p.stdout.decode('utf-8'))
    site = [_moveins_cls(x) for x in PCTS]
    assert home == site, dict(zip(PCTS, zip(home, site)))
    assert home.count('lo') == 2 and home.count('hi') == 2, home   # 64.4·69.4 부족, 130.6·140 과잉(130.4 는 130% — 과잉 아님)


def test_no_threshold_literals_in_occcls():
    code = _occcls_src().split('*/')[-1].replace('v/ref*100', '')     # 퍼센트 환산(×100)만 허용한다
    assert not re.search(r'\b(0?\.\d+|\d{2,3})\b', code), '홈 occCls 에 문턱 숫자가 박혔다: %s' % code


def test_moveins_uses_the_canon(monkeypatch):
    import make_sido_pages as P
    adv, _ = P.load()
    monkeypatch.setattr(SZ, 'OCC_LO_PCT', 10 ** 6)     # 모든 칸이 부족이 되는 문턱 — pct_cell 이 정본을 읽으면 표가 다 빨개진다
    monkeypatch.setattr(SZ, 'OCC_HI_PCT', 10 ** 7)
    html, _ = I.build_moveins(adv)
    cells = re.findall(r'<td class="(\w+)">[\d,]+% (적음|보통|많음)</td>', html)
    assert cells and set(cells) == {('up', '적음')}, cells   # 색과 낱말이 같은 정본에서 온다(백로그 36-2)


def _split_to(tmp_path):
    """저장소 data.js 사본에 split_data 를 돌려 (코어 ADV, trend ADV)를 돌려준다 — 저장소 파일에는 쓰지 않는다
    (test_home_first_screen 의 split 픽스처와 같은 방식). 커밋된 산출물이 옛 판이어도 지금 코드의 페이로드를 본다."""
    import shutil as _sh
    src = tmp_path / 'data.js'
    _sh.copyfile(os.path.join(ROOT, 'data.js'), str(src))
    paths = {'SRC': src, 'OUT': tmp_path / 'data-core.js', 'REST': tmp_path / 'data-rest.json',
             'TREND': tmp_path / 'data-trend.json', 'SGG': tmp_path / 'data-sgg.json', 'SIZE': tmp_path / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    return core_adv, json.loads(paths['TREND'].read_text(encoding='utf-8'))['ADV']


def test_trend_payload_carries_the_band(tmp_path):
    """변이(실제로 확인): split_data 가 occupancy 에 band 를 싣지 않으면 빨개진다."""
    _, trend = _split_to(tmp_path)
    assert trend['occupancy'].get('band') == S.occ_band(), '통계 탭 파일에 입주물량 문턱이 없다'
