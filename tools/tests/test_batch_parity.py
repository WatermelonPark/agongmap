# -*- coding: utf-8 -*-
"""로컬 배치와 클라우드 배치가 같은 생성기를 같은 순서로 돌리고 같은 산출물을 커밋하는지 고정한다(백로그 11).

2026-09-16 리뷰 10번: 로컬 러너(run_weekly_update.bat)가 make_monthly_page 를 부르지 않았고 git add 목록에
cycle 이 없었다. 그래서 로컬 배치가 고친 cycle/index.html 이 공유 작업 트리에 미커밋으로 남아 다른 세션의
푸시를 막았고, 로컬이 돌 때 /monthly/ 는 갱신되지 않았다. 두 파일이 같은 대상을 따로 적어 두어 생긴 일이다.

무엇을 깨뜨리면 빨개지나:
  - bat 에서 생성기 한 줄을 지우거나(예: make_monthly_page) 순서를 바꾸면 → 순서 시험
  - bat 의 git add / git diff 목록에서 대상 하나를 빼면(예: cycle) → 대상 시험
  - pytest 게이트를 커밋 뒤로 옮기거나 지우면 → 순서 시험(게이트도 한 단계로 센다)
  - 파서가 망가져 빈 목록을 읽으면 → 파서 자기 확인 시험(빈 목록끼리는 같아서 조용히 통과한다)
픽스처: 저장소의 실제 두 파일을 읽는다.
"""
import io
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
YML = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
BAT = os.path.join(ROOT, 'tools', 'run_weekly_update.bat')

# 클라우드에만 있는 보고용 도구 — 산출물을 만들지 않는다. 늘어나면 여기에 이유와 함께 적는다.
REPORT_ONLY = {'month_lag', 'batch_notes', 'format_batch_report'}


def _cloud_steps():
    out = []
    for line in io.open(YML, encoding='utf-8').read().splitlines():
        if line.strip().startswith('#'):
            continue
        if re.search(r'python3? -m pytest tools/tests', line):
            out.append('pytest')
            continue
        m = re.search(r'python3? tools/([a-z_]+)\.py', line)
        if m and m.group(1) not in REPORT_ONLY:
            out.append(m.group(1))
    return _dedupe(out)


def _bat_steps():
    out = []
    for line in io.open(BAT, encoding='utf-8').read().splitlines():
        t = line.strip()
        if t.lower().startswith('rem') or t.startswith('::'):
            continue
        if re.match(r'python -m pytest tools\\tests', t):
            out.append('pytest')
            continue
        m = re.match(r'python tools\\([a-z_]+)\.py', t)
        if m:
            out.append(m.group(1))
    return _dedupe(out)


def _dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _cloud_targets():
    m = re.search(r'TARGETS="([^"]+)"', io.open(YML, encoding='utf-8').read())
    assert m, 'update-cloud.yml 에서 TARGETS 를 찾지 못했다'
    return set(m.group(1).split())


def _bat_list(cmd):
    lines = [l.strip() for l in io.open(BAT, encoding='utf-8').read().splitlines() if l.strip().startswith(cmd + ' ')]
    assert len(lines) == 1, 'bat 에서 "%s" 줄이 %d개다' % (cmd, len(lines))
    return {t.replace('\\', '/') for t in lines[0][len(cmd):].split()}


def test_parsers_actually_read_the_steps():
    for name, steps in (('클라우드', _cloud_steps()), ('로컬', _bat_steps())):
        for must in ('update_adv_data', 'split_data', 'make_sido_pages', 'make_monthly_page', 'refresh_cycle_data', 'pytest'):
            assert must in steps, '%s 배치에서 %s 를 읽지 못했다 — 파서가 깨졌거나 단계가 빠졌다: %s' % (name, must, steps)


def test_local_runs_the_same_generators_in_the_same_order():
    cloud, local = _cloud_steps(), _bat_steps()
    assert local == cloud, '로컬 배치 순서가 클라우드와 다르다\n  클라우드: %s\n  로컬:     %s' % (cloud, local)


def test_local_commits_the_same_targets():
    cloud = _cloud_targets()
    assert {'monthly', 'cycle', 'weekly'} <= cloud, '클라우드 TARGETS 를 제대로 읽지 못했다: %s' % sorted(cloud)
    for cmd in ('git add', 'git diff --quiet'):
        local = _bat_list(cmd)
        assert local == cloud, '로컬 "%s" 대상이 클라우드 TARGETS 와 다르다 — 빠짐 %s, 더함 %s' % (
            cmd, sorted(cloud - local), sorted(local - cloud))
