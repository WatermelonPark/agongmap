# -*- coding: utf-8 -*-
"""다음 분기 데이터가 들어온 회차를 미리 돌려 본다 — 생성기와 게이트가 그 데이터에서도 통과하는가
(2026-09-26 데이터 감사).

왜 필요한가: 배치 게이트(pytest)는 커밋 잡에서 **방금 받은 새 데이터**로 돈다. 그런데 그 데이터는 게이트를
통과해야 main 에 들어오므로, main 의 pytest 는 늘 옛 데이터로만 초록이다. 새 데이터에서만 빨개지는 시험은
미리 볼 길이 없다. 실제로 test_sido_pages_main 이 착공 자름을 '2026.03' 으로 박아 두어, 2026.09 준공·착공이
들어오는 날(L=2026Q3) H=10 이 되어 게이트가 빨개질 참이었다. 생성기 다섯 개는 모두 성공하고 게이트만
빨개져 그날 데이터 커밋 전체(주간 시세·월간·지역 페이지)가 막히고, 분기마다 되풀이된다(감사 #0 — 09-24~26
yaml 로 5회 막힌 사고와 같은 모양). 그래서 배치 한 회차를 한 분기 앞당겨 흉내 낸다.

무엇을 하나(저장소에는 쓰지 않는다 — 전부 tmp_path 사본에서 한다):
  1. 저장소 파일을 tmp 로 복사한다(git 이 추적하는 파일 + 무시되지 않은 새 파일, .git 은 뺀다).
  2. 사본 data.js 를 전진시킨다.
     - 준공·착공: 다음 분기(L+1)가 끝나는 달까지. 지역마다 12개월 전 값을 되풀이하므로 전국=Σ시도,
       수도권=서울+경기+인천 이 그대로다(원천이 새 분기를 낸 날의 모양).
     - 주간 시세: 한 주(시도·시군구·서울 구 모두). 월간 시세: 한 달. 보관 길이는 배치 상한(CONF) 그대로.
     - 매매·전세지수·금리: 매매는 다음 분기 첫 달(잠정 'p)'), 전세는 한 달 늦게, 금리는 매매와 같은 달까지(_advance_indices).
  3. 배치처럼 ADV.sido·occupancy 를 다시 굽고(update_adv_data --seed-sido — --update 와 같은 sido_zones.calc·
     supply_rows), split_data 를 돈다.
  4. 커밋 잡이 게이트 앞에서 돌리는 생성기(update-cloud.yml 에서 읽는다)를 사본에서 돌린다 — 전부 rc=0.
  5. 사본에서 pytest 게이트를 그대로 돈다(이 파일만 뺀다) — 전부 통과.

안쪽 게이트는 배치 게이트와 같은 조건으로 돈다 — 건너뜀도 실패다(GITHUB_ACTIONS=true, AGONGMAP_ALLOW_SKIP 없음). 전진한
데이터에서만 건너뛰는 시험은 그날 배치 게이트에서 실패로 데이터 커밋을 막기 때문이다. 사본에는 .git 이 없어 판정할 수 없는
sw.js 이력 시험 하나(NO_GIT_TEST)만 골라 뺀다 — 그 시험은 바깥 게이트에서 제대로 돈다. 예전엔 안쪽 게이트에
AGONGMAP_ALLOW_SKIP=1 을 통째로 줘 모든 건너뜀이 rc=0 으로 지나갔다(전수리뷰 T1-4). 사본 안의 git 이 저장소를 찾아 올라가지
않게 GIT_CEILING_DIRECTORIES 를 둔다.

⚠️ 배치 커밋 잡(update-cloud.yml 의 commit 잡, GITHUB_JOB=commit) 안에서는 이 전진 시험을 돌리지 않는다.
   이건 **다음 분기** 문제를 미리 보는 시험이라, 배치 게이트에서 빨개지면 오늘 받은 멀쩡한 데이터까지 막는다 —
   미래의 정지를 오늘로 당기는 거짓 차단이 된다(이 감사가 없애려는 바로 그 모양). 개발 세션·로컬의 pytest 에서는
   돌고 빨개진다(시험·생성기를 고치는 사람이 먼저 본다). 배치 밖 CI 에서는 ci-tests.yml 의 매일 예약 실행(22:17 KST,
   main 위 새 데이터)이 이 시험을 실패로 돌린다 — 데이터 커밋을 막지 않고 다음 분기 정지를 실패 알림 메일로 먼저 알린다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - test_sido_pages_main 의 착공 자름을 옛 '2026.03'·'H=11' 로 되돌리면 안쪽 게이트가
    'assert 10 == (12 - 1)' 로 빨개져 이 시험이 빨개진다(감사 #0 재현).
  - 전진 단계(_advance_supply)를 건너뛰면 픽스처 자기 확인('L 이 한 분기 나아가지 않았다')이 빨개진다.
  - commit_job_generators 가 빈 목록을 돌려주면 파서 자기 확인 시험이 빨개진다.
  - 배치 잡 가드(_in_batch_gate)를 지우면 test_forward_check_never_gates_the_batch_commit 이 빨개진다.
  - 7편 가드 link7_values 가 끝 칸 전세 None 을 그대로 비교하던 판(전수리뷰 BL2-1 고치기 전)에서는 지수 전진(_advance_indices)
    단계가 실데이터 시험 넷(test_theory_post7·test_theory_guards 하나씩, test_home_entry 둘)을 TypeError 로 빨갛게 해 이 시험이
    빨개진다. 확인은 옛 link7_values 를 되살리고, 그 판에서 혼자 빨개지는 합성 시험 둘(test_theory_post7 의 끝 칸·빈 분기)을 뺀
    사본으로 했다 — 같은 사본에서 전진 단계만 빼면 초록이라, 이 단계 없이는 그 정지를 못 봤다.
  - 사본에서만 건너뛰는 시험(저장소 뿌리에 .git 이 없으면 pytest.skip)을 하나 넣으면 안쪽 게이트가 '건너뜀이 실패다'로
    빨개져 이 시험이 빨개진다. 안쪽 env 에 AGONGMAP_ALLOW_SKIP=1 을 되살리면 같은 상태에서 초록이 된다(T1-4).
  - 지수 전진의 자기 확인(_short_of)을 '목표 달과 같아야'로 되돌리면 달 초에 금리가 매매보다 두 달 앞선 날 헛되이 빨개진다 —
    test_index_advance_makes_the_next_quarter_first_month_shape 가 합성 STATS 로 본다(이 큰 시험은 그날 데이터에서만 드러난다).
픽스처: 저장소의 실제 data.js 를 한 분기(준공·착공)·한 주·한 달 앞당긴 것. 실행 시간 약 3분(안쪽 게이트가 대부분 — 2026-10 실측).
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import warnings

import pytest

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import sido_zones as SZ  # noqa: E402
import update_adv_data as U  # noqa: E402  data.js 읽기·쓰기와 보관 상한(CONF)의 정본

YML = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
GATE = 'python3 -m pytest tools/tests'
BATCH_JOB = 'commit'      # update-cloud.yml 의 커밋 잡 키 = 그 잡의 GITHUB_JOB. 파서와 가드가 같이 쓴다
SELF = os.path.basename(os.path.abspath(__file__))
# 사본(.git 없음)에서 판정할 수 없어 안쪽 게이트에서 빼는 유일한 시험 — git 이력의 sw.js 최대 버전을 읽는다.
NO_GIT_TEST = 'tools/tests/test_sw_version.py::test_sw_version_never_goes_below_the_highest_ever_shipped'


def _in_batch_gate():
    """배치 커밋 잡의 게이트 안에서 도는가 — 거기서는 전진 시험이 오늘 데이터를 막지 않게 빠진다."""
    return bool(os.environ.get('GITHUB_ACTIONS')) and os.environ.get('GITHUB_JOB') == BATCH_JOB


def commit_job_generators():
    """update-cloud.yml 커밋 잡이 게이트 **앞**에서 부르는 tools/*.py — 손으로 적지 않는다."""
    text = io.open(YML, encoding='utf-8').read()
    job = text[text.index('\n  %s:\n' % BATCH_JOB):]
    out = []
    for line in job.splitlines():
        s = line.strip()
        if s.startswith('#'):
            continue
        if GATE in s:
            return out
        m = re.search(r'python3? tools/([a-z_]+)\.py', s)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    raise AssertionError('update-cloud.yml 커밋 잡에서 pytest 게이트를 찾지 못했다')


def _copy_repo(dst):
    """추적 파일 + 무시되지 않은 새 파일만 복사한다(.gitignore 된 벌크 원본·캐시·다른 워크트리는 뺀다)."""
    try:
        out = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                             cwd=ROOT, capture_output=True, timeout=60)
        files = [f for f in out.stdout.decode('utf-8', 'replace').split('\0') if f] if out.returncode == 0 else []
    except Exception:
        files = []
    if not files:   # git 이 없는 환경 — 무거운 로컬 전용 폴더만 빼고 통째로
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
            '.git', '.claude', '__pycache__', 'drafts', 'logs', 'cache', '.pytest_cache'))
        return
    for f in files:
        src = os.path.join(ROOT, f)
        if not os.path.isfile(src):
            continue   # 작업 트리에서 지운 추적 파일
        d = os.path.join(dst, f)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(src, d)


def _next_month(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return y, m


def _advance_supply(stats):
    """준공·착공을 다음 분기(L+1) 끝 달까지 채운다. 새 L 인덱스를 돌려준다."""
    L = SZ.last_full_quarter(stats, '준공')
    y, q = SZ.qparts(L + 1)
    target = '%d.%02d' % (y, q * 3)
    for key in ('준공', '착공'):
        s = stats[key]
        n = len(s['dates'])
        for v in s['series'].values():
            v.extend([None] * (n - len(v)))      # 계열 길이를 날짜에 맞춘 뒤 붙인다
        while s['dates'][-1][:7] < target:
            s['dates'].append('%d.%02d' % _next_month(s['dates'][-1]))
            for v in s['series'].values():
                v.append(v[-12])                 # 같은 달 작년 값 — 지역 합 항등식이 그대로다
    return L + 1


def _advance_indices(stats):
    """매매·전세지수·금리를 원천이 새 분기 첫 달을 낸 날의 모양으로 민다 — 매매는 다음 분기 첫 달(잠정 'p)'), 전세는 한 달 늦게,
    금리는 매매와 같은 달까지. 값은 끝 두 달의 흐름을 이어 붙인다(끝 값을 되풀이하면 전월=전전월이 되어 '잠정 증감률 기준 달'
    시험의 픽스처 전제가 깨진다). 전세가 한 달 늦게 실리는 창(매 분기 첫 달분이 실린 날부터 한 달)에 /cycle/ rate_overlay 끝
    분기의 전세가 비는 모양을 미리 본다(전수리뷰 BL2-1 — 7편 가드 TypeError)."""
    mm = stats['매매지수']['dates'][-1]
    y, m = int(mm[:4]), int(mm[5:7])
    q_first = ((m - 1) // 3 + 1) * 3 + 1
    ty, tm = (y + 1, q_first - 12) if q_first > 12 else (y, q_first)
    targets = {'매매지수': (ty, tm), '전세지수': (ty, tm - 1) if tm > 1 else (ty - 1, 12), '금리': (ty, tm)}
    for key, (yy, mo) in targets.items():
        s = stats[key]
        n = len(s['dates'])
        for v in s['series'].values():
            v.extend([None] * (n - len(v)))
        s['dates'] = [d.replace(' p)', '') for d in s['dates']]
        target = '%d.%02d' % (yy, mo)
        while s['dates'][-1][:7] < target:
            s['dates'].append('%d.%02d' % _next_month(s['dates'][-1]))
            for v in s['series'].values():
                a, b = v[-2], v[-1]
                v.append(None if b is None else round(b + (b - a if a is not None else 0), 2 if key == '금리' else 3))
        if key == '매매지수':
            s['dates'][-1] += ' p)'
    return targets


def _short_of(stats, targets):
    """_advance_indices 뒤 목표 달에 못 미친 계열. 목표보다 **앞선** 계열은 그대로 둔다 — 금리(ECOS)는 다음 달 초에 실리고 매매는 그
    달 말에 실려, 매매 발표가 며칠 밀린 달 초에는 금리가 매매보다 두 달 앞선다(매매가 분기 끝 달이면 목표 달보다 한 달 앞)."""
    return [k for k, (y, m) in targets.items() if stats[k]['dates'][-1][:7] < '%d.%02d' % (y, m)]


def _advance_rows(block, step, keep):
    rows = block['rows']
    new = json.loads(json.dumps(rows[-1]))
    new['p'] = step(rows[-1]['p'])
    block['rows'] = (rows + [new])[-keep:]


def _next_week(p):
    return (datetime.date(*(int(x) for x in p.split('-'))) + datetime.timedelta(days=7)).isoformat()


def _next_month_dash(p):
    return '%d-%02d' % _next_month(p)


def _advance_prices(adv):
    for key, step, hist in (('weekly', _next_week, 'weeks_hist'), ('monthly', _next_month_dash, 'months_hist')):
        blk = adv[key]
        _advance_rows(blk, step, U.CONF[key][hist])
        for sub in ('sgg', 'seoul'):
            if (blk.get(sub) or {}).get('rows'):
                _advance_rows(blk[sub], step, U.CONF[key]['sgg_hist'])
    return adv['weekly']['rows'][-1]['p'], adv['monthly']['rows'][-1]['p']


def _run(args, cwd, env, timeout=300):
    p = subprocess.run([sys.executable, '-B'] + args, cwd=cwd, env=env, capture_output=True,
                       timeout=timeout, encoding='utf-8', errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def _tail(out, n=40):
    lines = out.splitlines()
    keep = [ln for ln in lines if ln.startswith(('FAILED', 'ERROR', 'E   '))][:30]
    return '\n'.join(keep + ['...'] + lines[-n:])


def test_parser_reads_the_commit_job_generators():
    """목록 파생이 헛돌면 아래 시험이 생성기를 하나도 안 돌리고 초록이 된다 — 빈 목록을 막는다.

    변이: commit_job_generators 가 [] 를 돌려주면 빨개진다(확인). 커밋 잡 키가 바뀌어 BATCH_JOB 과
          어긋나면 index 에서 ValueError 로 빨개진다 — 그때는 배치 가드도 함께 고쳐야 한다.
    픽스처: 저장소의 실제 update-cloud.yml.
    """
    gens = commit_job_generators()
    assert len(gens) >= 5 and 'make_sido_pages' in gens and 'refresh_cycle_data' in gens, gens
    assert 'split_data' not in gens and 'update_adv_data' not in gens, '수집 잡의 도구가 섞였다: %s' % gens


def test_index_advance_makes_the_next_quarter_first_month_shape():
    """지수 전진(_advance_indices)은 원천이 새 분기 첫 달을 낸 날의 모양을 만든다 — 매매는 다음 분기 첫 달(잠정 'p)', 옛 꼬리표는
    뗀다), 전세는 한 달 늦게, 금리는 매매와 같은 달까지. 이미 목표보다 앞선 계열(달 초의 금리)은 그대로 두고, 아래 큰 시험의 자기
    확인(_short_of)도 그것을 '못 미침'으로 치지 않는다.

    재현하는 실제 상태: 금리(ECOS)는 다음 달 초에, 매매는 그 달 말에 실린다(저장소 이력 — 08-28 매매 2026.07 p)·금리 2026.07,
    09-01 금리 2026.08). 매매 발표가 며칠 밀린 달 초에는 매매가 분기 끝 달(2026.09 p))에 머문 채 금리가 2026.11 이라 목표 달(2026.10)
    보다 앞선다 — 예전 자기 확인은 금리가 목표 달과 '같아야' 한다고 봐, 그런 날 매일 예약 CI 의 전진 시험을 데이터 결함 없이
    빨갛게 할 참이었다. 해 넘김(매매 2026.12 p) → 2027.01)도 본다.
    변이(각각 실제로 확인): _short_of 의 판정을 '목표 달과 다르면'(!=)으로 바꾸면 둘째 경우가, 전세 목표의 `tm - 1` 을 `tm` 으로
          바꾸거나 해 넘김의 `y + 1` 을 `y` 로 바꾸면 첫째 경우가 빨개진다.
    픽스처: 합성 STATS 두 벌(지역 하나, 값은 달마다 1씩 올라 끝 두 달 흐름을 잇는지 보인다). 실데이터를 읽지 않는다.
    """
    def st(mm, je, rt):
        def s(dates, base):
            return {'dates': list(dates), 'series': {'전국': [base + i for i in range(len(dates))]}}
        return {'매매지수': s(mm, 100.0), '전세지수': s(je, 90.0), '금리': s(rt, 3.0)}
    a = st(['2026.10', '2026.11', '2026.12 p)'], ['2026.10', '2026.11'], ['2026.11', '2026.12'])   # 해 넘김
    t = _advance_indices(a)
    assert t == {'매매지수': (2027, 1), '전세지수': (2026, 12), '금리': (2027, 1)}, t
    assert a['매매지수']['dates'][-2:] == ['2026.12', '2027.01 p)'] and a['매매지수']['series']['전국'][-1] == 103.0, a['매매지수']
    assert a['전세지수']['dates'][-1] == '2026.12' and a['금리']['dates'][-1] == '2027.01' and not _short_of(a, t)
    b = st(['2026.08', '2026.09 p)'], ['2026.07', '2026.08'], ['2026.10', '2026.11'])   # 달 초 — 금리가 매매보다 두 달 앞
    t = _advance_indices(b)
    assert t['금리'] == (2026, 10) and b['금리']['dates'] == ['2026.10', '2026.11'], b['금리']
    assert b['매매지수']['dates'][-1] == '2026.10 p)' and b['전세지수']['dates'][-1] == '2026.09', (b['매매지수'], b['전세지수'])
    assert not _short_of(b, t), _short_of(b, t)


def test_forward_check_never_gates_the_batch_commit(tmp_path, monkeypatch):
    """배치 커밋 잡(GITHUB_JOB=commit)에서는 전진 시험이 아무것도 하지 않고 경고만 남긴다.

    변이: test_generators_and_gate_pass_on_next_quarter_data 첫머리의 `if _in_batch_gate():` 가드를 지우면
          사본 복사(_copy_repo)가 불려 빨개진다(실제로 확인).
    픽스처: 커밋 잡의 환경 변수 두 개(GITHUB_ACTIONS·GITHUB_JOB). 사본 복사는 불리면 바로 실패하게 바꿔 둔다.
    """
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    monkeypatch.setenv('GITHUB_JOB', BATCH_JOB)

    def boom(dst):
        raise AssertionError('배치 게이트 안에서 전진 시험이 돌았다 — 다음 분기 문제로 오늘 데이터 커밋을 막는다')
    monkeypatch.setattr(sys.modules[__name__], '_copy_repo', boom)
    with pytest.warns(UserWarning):
        test_generators_and_gate_pass_on_next_quarter_data(tmp_path, monkeypatch)


def test_generators_and_gate_pass_on_next_quarter_data(tmp_path, monkeypatch):
    if _in_batch_gate():
        warnings.warn('배치 커밋 잡에서는 다음 분기 전진 시험을 돌리지 않는다(오늘 데이터 커밋을 막지 않게) — '
                      '개발 세션의 pytest 에서 돈다')
        return
    repo = tmp_path / 'repo'
    _copy_repo(str(repo))
    data = str(repo / 'data.js')
    monkeypatch.setattr(U, 'DATA', data)          # U 의 읽기·쓰기를 사본으로 돌린다

    stats = U.read_current_stats()
    old_L = SZ.last_full_quarter(stats, '준공')
    new_L = _advance_supply(stats)
    idx = _advance_indices(stats)
    U.write_stats(stats)
    _, _, _, adv = U.read_current_adv()
    old_w, old_m = adv['weekly']['rows'][-1]['p'], adv['monthly']['rows'][-1]['p']
    new_w, new_m = _advance_prices(adv)
    U.write_adv(adv)

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GIT_CEILING_DIRECTORIES=str(tmp_path))
    for step in (['tools/update_adv_data.py', '--seed-sido'], ['tools/split_data.py']):
        rc, out = _run(step, str(repo), env)
        assert rc == 0, '%s 실패(rc=%d)\n%s' % (' '.join(step), rc, out[-3000:])

    # 픽스처 자기 확인 — 전진이 실제로 일어났고 점수가 그 데이터로 다시 구워졌다.
    _, _, _, adv2 = U.read_current_adv()
    assert adv2['sido']['L'] == SZ.qkey(new_L) and new_L == old_L + 1, \
        'L 이 한 분기 나아가지 않았다: %s → %s' % (SZ.qkey(old_L), adv2['sido']['L'])
    assert adv2['sido']['H'] == SZ.LEAD_Q, '전진한 사본이 H≠lead 다 — 준공·착공을 같은 달까지 채우지 못했다'
    assert new_w > old_w and new_m > old_m
    st2 = U.read_current_stats()
    assert not _short_of(st2, idx) and st2['매매지수']['dates'][-1].endswith(' p)'), \
        '매매·전세지수·금리가 새 분기 첫 달 모양(전세 한 달 늦음)으로 나아가지 않았다: %s' % _short_of(st2, idx)

    bad = []
    for g in commit_job_generators():
        rc, out = _run(['tools/%s.py' % g], str(repo), env)
        if rc != 0:
            bad.append('%s rc=%d\n%s' % (g, rc, out[-2000:]))
    assert not bad, '다음 분기 데이터에서 생성기가 실패한다 — 그날 배치가 커밋을 멈춘다:\n' + '\n'.join(bad)

    # 생성기가 사본을 구웠는지(저장소가 아니라) — 새 분기·새 주차가 페이지에 실렸다.
    def page(*p):
        return io.open(os.path.join(str(repo), *p), encoding='utf-8').read()
    assert '%s 실적' % SZ.quarter_short(SZ.qkey(new_L)) in page('monthly', 'index.html'), '/monthly/ 가 새 분기로 구워지지 않았다'   # 좁은 표 머리 '26Q3 실적'(날짜 두 단계)
    y, m, d = (int(x) for x in new_w.split('-'))
    assert '%d/%d 조사' % (m, d) in page('weekly', 'index.html'), '/weekly/ 가 새 주차로 구워지지 않았다'
    stale = [z['z'] for z in adv2['sido']['zones']
             if SZ.quarter_text(SZ.qkey(new_L)) not in page('zone', z['z'], 'index.html')]
    assert not stale, '/zone/ 이 새 분기로 구워지지 않았다: %s' % stale

    # 안쪽 게이트도 건너뜀=실패(배치 게이트와 같은 조건). 바깥이 로컬이어도 그렇게 돌도록 GITHUB_ACTIONS 를 켜고 ALLOW_SKIP 은
    # 지운다 — .git 이 없어 판정할 수 없는 NO_GIT_TEST 하나만 골라 뺀다(T1-4).
    genv = {k: v for k, v in env.items() if k != 'AGONGMAP_ALLOW_SKIP'}
    genv['GITHUB_ACTIONS'] = 'true'
    rc, out = _run(['-m', 'pytest', 'tools/tests', '-q', '-p', 'no:cacheprovider',
                    '--ignore', 'tools/tests/' + SELF, '--deselect', NO_GIT_TEST,
                    '--basetemp', str(tmp_path / 'inner')],
                   str(repo), genv, timeout=600)
    assert rc == 0, ('다음 분기(준공·착공 %s, 주간 %s, 월간 %s) 데이터에서 게이트가 빨개진다 — 그날 배치가 '
                     '데이터 커밋 전체를 멈춘다. 실데이터의 날짜·값을 박은 시험인지 볼 것:\n%s'
                     % (SZ.qkey(new_L), new_w, new_m, _tail(out)))
