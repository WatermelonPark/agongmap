# -*- coding: utf-8 -*-
"""사이클 3편이 못 박은 문장은 데이터가 받쳐 줄 때만 나가야 한다 (2026-09-16 리뷰 16번).

3편은 제목에 "N개 시도에서 예외가 없었습니다"를, 본문에 "서울은 왜 다른가" 절을 갖고
있다. 곳 수와 값은 사이트 D.sync에서 읽지만 **'예외가 없다'와 '서울'은 글자로 박혀**
있었다. 재산정으로 한 곳이 음수가 되거나 최저 지역이 바뀌면, 아무것도 빨개지지 않은
채 거짓 제목과 남의 값을 서울 이름으로 단 글이 만들어진다.

가드는 theory_guards 에 있다(블로그 초안 도구는 2026-11-13 에 지웠다). 지금은 배치 기록 줄(batch_notes.theory_claim_lines)이 이
가드를 불러 3편 전제가 깨진 날 ℹ️ 줄로 알린다.

변이 확인(실제로 깨뜨려 봄):
  - check_sync_claims의 `<= 0`을 `< -1`로 → test_negative_region_stops_generation 빨강
  - 최저 지역 비교를 지우면 → test_other_lowest_region_stops_generation 빨강
  - guard_values 의 3편 갈래에서 check_sync_claims 호출을 지우면 → test_guard_runs_the_sync_check_for_episode_3 빨강
픽스처: D.sync 한 줄의 모양({region, corr, sudo}) 그대로. '대구가 최저'와 '한 곳이 음수'는
재산정에서 실제로 나올 수 있는 두 상태다(2026-09-12 재산정 때 서울 0.58→0.55, 곳 수 15→14).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import theory_guards as T  # noqa: E402


def _rows(**over):
    base = {'대구': 0.82, '부산': 0.80, '경기': 0.70, '서울': 0.55}
    base.update(over)
    return sorted(({'region': k, 'corr': v, 'sudo': k in ('서울', '경기')}
                   for k, v in base.items()), key=lambda x: -x['corr'])


# ⚠️ '지금 데이터가 주장을 받쳐 준다'는 실데이터 단정은 배치 게이트에 두지 않는다(CLAUDE.md 데이터 원칙,
#    리뷰 09-18 19번). 그 상태는 tools/batch_notes.py 가 ℹ️ 줄로 알린다(test_batch_notes 참조).


def test_negative_region_stops_generation():
    with pytest.raises(SystemExit) as e:
        T.check_sync_claims(_rows(부산=-0.10))
    assert '부산' in str(e.value) and '예외가 없었습니다' in str(e.value)


def test_other_lowest_region_stops_generation():
    with pytest.raises(SystemExit) as e:
        T.check_sync_claims(_rows(대구=0.30))
    assert '대구' in str(e.value)


def test_guard_runs_the_sync_check_for_episode_3(monkeypatch):
    monkeypatch.setattr(T, 'CYCLE_SYNC', _rows(대구=0.30))
    with pytest.raises(SystemExit) as e:
        T.guard_values(3, D={}, data=({}, {}))
    assert str(e.value).startswith('3편을 만들 수 없다 — ') and '대구' in str(e.value)
    monkeypatch.setattr(T, 'CYCLE_SYNC', _rows())
    assert T.guard_values(3, D={}, data=({}, {})) == {}
