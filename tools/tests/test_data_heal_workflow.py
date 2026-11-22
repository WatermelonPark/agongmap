# -*- coding: utf-8 -*-
"""키가 필요한 1회성 교정을 Actions 수동 실행으로 돌리는 워크플로(`data-heal.yml`)의 계약(백로그 51·52·53·54 후속).

왜: `--heal-annual`·`--heal-price`·등급 재현·원천 표 탐색은 정기 배치에 없고 키가 필요하다. 저장소 시크릿은 이미
있으므로(Settings → Secrets) 수동 워크플로가 그 시크릿으로 돌린다. 데이터를 커밋하는 작업은 ① 배치와 같은 생성기
순서, ② `GITHUB_ACTIONS=1` pytest 게이트, ③ 커밋 화이트리스트를 모두 지나야 한다. 이 시험은 그 계약이 빠지지
않게 본다.
"""
import io
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
WF = os.path.join(ROOT, '.github', 'workflows', 'data-heal.yml')


def _t():
    return io.open(WF, encoding='utf-8').read()


def test_dispatches_only_manually_with_the_four_jobs():
    """수동 실행 전용이고, 네 작업과 네 시크릿이 모두 실려 있다.

    변이(실제로 확인): RONE_API_KEY 줄을 지우면 이 시험이 빨개진다.
    """
    t = _t()
    assert 'workflow_dispatch:' in t and 'schedule:' not in t, '수동 실행 전용이 아니다'
    assert 'contents: write' in t, '커밋·푸시 권한이 없다'
    assert 'runs-on: ubuntu-24.04' in t, '러너 판 고정이 아니다'
    for job in ('heal-annual-보급률', 'heal-price', 'study-grade-bands', 'discover-규모별'):
        assert job in t, job
    for k in ('KOSIS_API_KEY', 'RONE_API_KEY', 'ECOS_API_KEY', 'DATA_GO_KR_KEY'):
        assert 'secrets.%s' % k in t, k


def test_gate_runs_before_commit_and_only_after_changes():
    """커밋 앞에 배치와 같은 생성기 순서와 게이트가 있고, 바뀐 것이 없으면 건너뛴다.

    변이(실제로 확인): pytest 줄을 지우면 이 시험이 빨개진다(게이트 없이 데이터가 커밋된다).
    """
    t = _t()
    i_gate = t.index('GITHUB_ACTIONS=1 python3 -m pytest tools/tests -q')
    i_commit = t.index('git commit -m')
    assert i_gate < i_commit, '게이트가 커밋 뒤에 있다'
    assert "if: inputs.job == 'heal-annual-보급률' || inputs.job == 'heal-price'" in t
    assert '바뀐 파일 없음 — 게이트를 건너뛴다' in t, '바뀐 것이 없어도 생성기를 돌린다'
    for g in ('make_city_moveins', 'split_data', 'make_sido_pages', 'make_indicator_pages', 'make_monthly_page',
              'make_weekly_page', 'make_home_summary', 'refresh_cycle_data', 'make_content_pages', 'make_feed',
              'make_llms_txt'):
        assert g in t, g


def test_commit_is_limited_to_generated_and_data_paths():
    """커밋 화이트리스트 밖 파일이 섞이면 멈춘다 — 손 페이지·도구·문서를 실수로 싣지 않는다.

    변이(실제로 확인): `grep -Ev` 화이트리스트 줄을 지우면 이 시험이 빨개진다(정규식을 못 읽는다).
    """
    t = _t()
    line = next((l for l in t.splitlines() if 'BAD=$(grep -Ev' in l), '')
    assert line, '커밋 화이트리스트 없이 git add -A 를 한다'
    assert '커밋 화이트리스트 밖 파일이 섞였다' in t
    pat = re.compile(line.split("'")[1])
    for p in ('data.js', 'data-core.js', 'data-trend.json', 'zone/서울/index.html', 'weekly/index.html',
              'city/x/index.html', 'feed.xml', 'sitemap.xml', 'tools/data/city_moveins.json', 'share/post-city-x.png'):
        assert pat.match(p), p
    for p in ('docs/2026-09-09-유지보수-백로그.md', 'tools/update_adv_data.py', 'content/city/x.md',
              '.github/workflows/data-heal.yml', 'tools/tests/test_x.py'):
        assert not pat.match(p), p


def test_read_only_jobs_must_not_touch_the_repo():
    """등급 재현·표 탐색은 읽기만 한다 — 저장소가 바뀌면 실패한다(산출물을 실수로 커밋하지 않는다)."""
    assert '보기 전용 작업인데 저장소 파일이 바뀌었다' in _t()
