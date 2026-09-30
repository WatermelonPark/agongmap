# -*- coding: utf-8 -*-
"""split_data 는 판정 모델(sido_zones)을 반드시 불러오고, 지역 목록을 손으로 들고 있지 않다(전수 리뷰 #14).

재현하는 실제 상태: split_data 는 `try: import sido_zones … except Exception:` 뒤에 19개 지역을 손으로 옮긴 대체 목록을 두었다.
그 경로가 돌면(검증자가 sido_zones 첫 줄에 예외를 넣어 재현) 경고 없이 옛 목록으로 홈 준공·착공 지역을 거르고 화면 문구
(refresh_texts)도 건너뛴 코어를 실었다. 모델이 바뀌면(2026-09-10 광주·전남 통합 같은) 목록이 따라오지 않는다.
무엇을 깨뜨리면 빨개지나(실제로 확인): 손 대체 목록을 되살리면 지역 이름 단정이, sido_zones import 를 try/except 로 다시 감싸면
except 단정이 빨개진다. 픽스처는 없고 실제 소스를 ast 로 읽는다.
"""
import ast
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sido_zones as SZ  # noqa: E402
import split_data as S  # noqa: E402

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'split_data.py')
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def _tree():
    return ast.parse(io.open(SRC, encoding='utf-8').read())


def test_no_hand_region_list():
    names = set(SZ.ORDER) - {'전국'}       # '전국'은 문구에 흔한 말이라 뺀다(목록이면 다른 이름이 함께 걸린다)
    lits = [n.value for n in ast.walk(_tree()) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    bad = sorted(v for v in lits if v in names)
    assert not bad, 'split_data 에 지역 이름이 문자열로 박혀 있다: %s' % bad
    assert S.TABLE_REGIONS == set(SZ.ORDER)


def test_model_import_is_not_optional():
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Try):
            mods = [a.name for s in n.body if isinstance(s, (ast.Import, ast.ImportFrom))
                    for a in (s.names if isinstance(s, ast.Import) else [ast.alias(name=s.module or '')])]
            assert 'sido_zones' not in mods, 'sido_zones 를 불러오지 못해도 split_data 가 넘어간다 — 배치가 멈춰야 한다'


def _split_to(tmp_path):
    """저장소 data.js 사본에 split_data 를 돌려 (코어 ADV, trend ADV)를 돌려준다 — 저장소 파일에는 쓰지 않는다
    (test_home_first_screen 의 split 픽스처와 같은 방식). 커밋된 산출물이 옛 판이어도 지금 코드의 페이로드를 본다."""
    import shutil as _sh
    src = tmp_path / 'data.js'
    _sh.copyfile(os.path.join(_ROOT, 'data.js'), str(src))
    paths = {'SRC': src, 'OUT': tmp_path / 'data-core.js', 'REST': tmp_path / 'data-rest.json',
             'TREND': tmp_path / 'data-trend.json', 'SGG': tmp_path / 'data-sgg.json', 'SIZE': tmp_path / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    return core_adv, json.loads(paths['TREND'].read_text(encoding='utf-8'))['ADV']


def test_trend_file_ships_only_what_the_stats_tab_reads(tmp_path):
    """통계 탭 파일(data-trend.json)의 ADV 는 허용목록(TREND_ADV)만 싣는다 — 폐기된 지표 aged30 이 새지 않는다(묶음 T 제보).
    허용목록은 홈 스크립트가 실제로 읽는 ADV 키를 빠짐없이 덮어야 한다(코어에만 싣는 blog 는 뺀다 — trend 에 없으면
    loadFullData 가 그 키를 바꾸지 않는다).

    재현하는 실제 상태: split_data 가 trend 에 ADV 전체(strip_units(adv))를 실어, 2026-08-06 재편으로 폐기된 aged30(약 1.8KB)이
    통계 탭을 여는 모든 방문자에게 실려 나갔다.
    변이(실제로 확인): trend_adv 를 strip_units(adv) 로 되돌리면 aged30 단정이 빨개진다(시험이 사본에 split_data 를 돌린다). TREND_ADV 에서
    'bubble' 을 빼면 홈 읽기 대조가 빨개진다.
    """
    import home_src as HS
    _, trend = _split_to(tmp_path)
    assert set(trend) <= set(S.TREND_ADV), '허용목록 밖 키가 통계 탭 파일에 실렸다: %s' % sorted(set(trend) - set(S.TREND_ADV))
    assert 'aged30' not in trend
    read = set(re.findall(r'\bADV\.([A-Za-z_][A-Za-z0-9_]*)', ''.join(t for f, t in HS.home_files() if f.endswith('.js'))))
    missing = read - set(S.TREND_ADV) - set(S.CORE_ONLY_ADV)
    assert not missing, '홈 스크립트가 읽는데 통계 탭 파일에 없는 ADV 키: %s' % sorted(missing)
