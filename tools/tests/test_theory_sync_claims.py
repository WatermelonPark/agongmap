# -*- coding: utf-8 -*-
"""사이클 3편이 못 박은 문장은 데이터가 받쳐 줄 때만 나가야 한다 (2026-09-16 리뷰 16번).

3편은 제목에 "N개 시도에서 예외가 없었습니다"를, 본문에 "서울은 왜 다른가" 절을 갖고
있다. 곳 수와 값은 사이트 D.sync에서 읽지만 **'예외가 없다'와 '서울'은 글자로 박혀**
있었다. 재산정으로 한 곳이 음수가 되거나 최저 지역이 바뀌면, 아무것도 빨개지지 않은
채 거짓 제목과 남의 값을 서울 이름으로 단 글이 만들어진다.

변이 확인(실제로 깨뜨려 봄):
  - check_sync_claims의 `<= 0`을 `< -1`로 → test_negative_region_stops_generation 빨강
  - 최저 지역 비교를 지우면 → test_other_lowest_region_stops_generation 빨강
  - render에서 가드 호출을 지우면 → test_render_runs_the_guard_for_episode_3 빨강
픽스처: D.sync 한 줄의 모양({region, corr, sudo}) 그대로. '대구가 최저'와 '한 곳이 음수'는
재산정에서 실제로 나올 수 있는 두 상태다(2026-09-12 재산정 때 서울 0.58→0.55, 곳 수 15→14).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import make_theory_post as T  # noqa: E402


def _rows(**over):
    base = {'대구': 0.82, '부산': 0.80, '경기': 0.70, '서울': 0.55}
    base.update(over)
    return sorted(({'region': k, 'corr': v, 'sudo': k in ('서울', '경기')}
                   for k, v in base.items()), key=lambda x: -x['corr'])


def test_live_data_still_supports_the_published_claims():
    T.check_sync_claims()          # 지금 데이터에서는 출력이 바뀌지 않아야 한다


def test_negative_region_stops_generation():
    with pytest.raises(SystemExit) as e:
        T.check_sync_claims(_rows(부산=-0.10))
    assert '부산' in str(e.value) and '예외가 없었습니다' in str(e.value)


def test_other_lowest_region_stops_generation():
    with pytest.raises(SystemExit) as e:
        T.check_sync_claims(_rows(대구=0.30))
    assert '대구' in str(e.value)


def test_render_runs_the_guard_for_episode_3(monkeypatch):
    monkeypatch.setattr(T, 'CYCLE_SYNC', _rows(대구=0.30))
    post = next(p for p in T.POSTS if p['n'] == 3)
    with pytest.raises(SystemExit):
        T.render(post)


def test_table_bolds_the_lowest_region_not_a_literal(monkeypatch):
    # 변이: sync_table의 굵은 글씨 조건을 nm == '서울'로 되돌리면 빨개진다.
    monkeypatch.setattr(T, 'CYCLE_SYNC', _rows(대구=0.30))
    html = T.sync_table()
    assert '<b>대구</b>' in html and '<b>서울</b>' not in html
