# -*- coding: utf-8 -*-
"""배치 0/3 전멸의 재시도 판정 — '시간이 바꿀 수 있는 실패'만 재시도한다.

재시도는 '35분 뒤 새 IP·새 시각이면 결과가 달라질 수 있다'는 가정 위에 서 있다.
시크릿 만료와 코드 크래시는 그 가정이 틀린 실패다 — 3회를 돌아도 똑같이 실패하고,
105분을 태우며 경보만 늦춘다. 감시가 결정론적 실패를 즉시 red로 보내는 것과 같은
원칙이다(check_freshness rc=2 → alert).

워크플로 셸 분기는 pytest가 실행할 수 없으므로, **판정의 뼈대(분류표와 안전
기본값)를 여기서 재현해 잠그고**, YAML에 그 뼈대가 실재하는지 함께 본다.
"""
import io
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
WF = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')

# 워크플로의 case 문과 같은 분류. 여기 없는 사유는 전부 '재시도'로 떨어진다.
DETERMINISTIC = ('nosecret', 'crash')


def decide(reasons):
    """True면 재시도, False면 즉시 red. 셸 분기와 같은 규칙."""
    words = [w for w in ' '.join(reasons).split() if w]
    if not words:
        return True                     # 사유를 못 읽으면 예전처럼 행동한다
    return any(w not in DETERMINISTIC for w in words)


def test_deterministic_failures_do_not_retry():
    assert decide(['nosecret'] * 3) is False
    assert decide(['crash'] * 3) is False
    assert decide(['nosecret', 'crash', 'crash']) is False


def test_transient_failures_still_retry():
    assert decide(['badip'] * 3) is True
    assert decide(['source'] * 3) is True


def test_one_healable_runner_is_enough_to_retry():
    """섞이면 재시도 쪽이다 — 하나라도 시간이 바꿀 여지가 있으면 그 여지를 쓴다."""
    assert decide(['badip', 'crash', 'crash']) is True


def test_unknown_reason_defaults_to_retrying():
    """판정 장치 자체가 고장났을 때(아티팩트 누락 등) 조용히 재시도를 꺼버리면,
    고칠 수 있었던 회차까지 같이 죽는다. 모르면 예전처럼 재시도한다."""
    assert decide([]) is True
    assert decide(['pending']) is True   # 갱신 스텝이 사유를 확정하기 전에 죽은 경우


def test_workflow_actually_carries_this_policy():
    """위 표는 워크플로의 거울일 뿐이다 — 셸에서 사라지면 여기만 초록으로 남는다."""
    y = io.open(WF, encoding='utf-8').read()
    assert 'reason-${{ matrix.n }}' in y, '러너가 사유를 안 올린다'
    # 커밋 잡은 러너별로 **이름을 지정해** 받는다. pattern 으로 받으면 결과가 1개인
    # 날에만 경로가 평평해져 간헐적으로 깨진다(2026-09-12 배치 사고, 백로그 7번).
    # matrix 에서 러너 목록을 읽어 대조하므로, 러너를 늘리고 스텝을 안 늘리면 여기서
    # 잡힌다 — 개수를 시험에 박아 두면 그 결합이 조용히 끊긴다.
    # ⚠️ PyYAML 을 쓰지 않는다. 배치 커밋 잡은 setup-python 3.12(hostedtoolcache)에 pytest·pillow 만
    #    깔아서, 러너 시스템 파이썬에 있던 yaml 이 없다 — 2026-09-23 커밋 잡을 3.12 로 고정한 뒤 이 줄
    #    하나가 ModuleNotFoundError 로 게이트를 막아 데이터 갱신이 5회 연속 멈췄다(09-24~26).
    #    matrix 의 `n: [1, 2, 3]` 한 줄만 읽으면 되므로 정규식으로 충분하다.
    m = re.search(r'matrix:\s*\n\s*n:\s*\[([^\]]*)\]', y)
    assert m, 'fetch 잡의 matrix n 목록을 못 찾았다'
    runners = [t.strip() for t in m.group(1).split(',') if t.strip()]
    assert len(runners) >= 2, '러너가 하나면 이중화가 아니다'
    for n in runners:
        assert re.search(r'name:\s*reason-%s(?![0-9])' % n, y), (
            '커밋 잡이 러너 %s 의 사유를 안 받는다' % n)
        assert re.search(r'name:\s*data-%s(?![0-9])' % n, y), (
            '커밋 잡이 러너 %s 의 산출물을 안 받는다' % n)
    assert not re.search(r'pattern:\s*(reason|data)-\*', y), (
        'pattern 방식으로 되돌아갔다 — 결과가 1개인 날 경로가 평평해져 깨진다')
    assert 'nosecret|crash' in y, '분류표가 셸에서 사라졌다'
    assert re.search(r'HEALABLE.*=.*0.*\n.*then', y) or 'HEALABLE" = "0"' in y
    # 결정론적 실패는 재시도가 아니라 red여야 한다 — need_retry로 새지 않는지.
    det = y.index('HEALABLE" = "0"')
    nxt = y.index('need_retry=true', det)
    assert 'exit 1' in y[det:nxt], '결정론적 실패가 red 없이 지나간다'


def test_exhausted_retries_turn_the_run_red():
    """재시도 3회를 다 쓰고도 0/3이면 red다. 예전엔 exit 0이라 워크플로가 초록으로
    끝났고 이슈 코멘트의 ❌만 남아 **실패 메일이 오지 않았다**(2026-08-15 사용자
    결정). 감시가 5시간 뒤 뒤처짐으로 잡아주긴 하지만, 그만큼 늦게 아는 것이다."""
    y = io.open(WF, encoding='utf-8').read()
    blk = y[y.index('시도 3/3 소진'):]
    end = blk.index('\n          fi')
    assert 'exit 1' in blk[:end], '재시도 소진이 초록으로 끝난다'


def test_pending_retry_must_not_turn_red():
    """반대로 '재시도 대기' 분기는 초록이어야 한다 — 아직 결론이 나지 않은 회차라 실패 메일을 보낼 일이 아니다
    (재시도까지 소진해야 red, 위 시험). retry 잡은 이제 !cancelled() 로 커밋 잡의 성패와 무관하게 돌지만
    (아래 시험), 대기 분기가 red 이면 재시도가 살려 낼 회차마다 실패 메일이 먼저 나간다."""
    y = io.open(WF, encoding='utf-8').read()
    blk = y[y.index('need_retry=true'):y.index('시도 3/3 소진')]
    assert 'exit 0' in blk, '재시도 대기 분기가 red 다 — 재시도가 살려 낼 회차마다 실패 메일이 나간다'


def _job_if(y, job):
    """워크플로의 잡 하나에서 잡 단위 `if:` 줄(들여쓰기 4칸)을 돌려준다."""
    seg = y[y.index('\n  %s:\n' % job) + 1:]
    nxt = re.search(r'\n  [A-Za-z_-]+:\n', seg)
    seg = seg[:nxt.start()] if nxt else seg
    m = re.search(r'^    if:\s*(.+)$', seg, re.M)
    return m.group(1).strip() if m else None


def test_retry_job_runs_after_failed_fetch_legs():
    """retry 잡 조건에 상태 함수 !cancelled() 가 있어야 한다(2026-10 리뷰 C1b). 상태 함수가 없는 잡 if 에는 암묵
    success() 가 붙고, 그건 앞선 잡 **전부**(commit 앞의 fetch 매트릭스까지)가 성공했을 때만 참이다. 재시도가 필요한
    날은 바로 fetch 러너가 실패한 날(0/3)이라 — commit 은 always() 로 돌아 need_retry=true 를 세워도 — retry 잡이
    늘 건너뛰어졌다. always() 가 아니라 !cancelled() 인 것은 사람이 런을 취소했을 때 재시도를 걸지 않으려는 것이다.

    변이(실제로 확인): retry 잡의 if 에서 `!cancelled() && ` 를 지우면(예전 조건) 빨개진다. `always() && ` 로 바꿔도
    빨개진다. need_retry 비교를 지워도 빨개진다.
    픽스처: update-cloud.yml 원문 — 잡 단위 if 줄을 잡 경계로 잘라 읽는다. commit 잡도 같은 이유로 always() 인지 본다.
    """
    y = io.open(WF, encoding='utf-8').read()
    cond = _job_if(y, 'retry')
    assert cond, 'retry 잡에 if 가 없다'
    assert re.fullmatch(r"\$\{\{\s*!cancelled\(\)\s*&&\s*needs\.commit\.outputs\.need_retry\s*==\s*'true'\s*\}\}",
                        cond), 'retry 잡 조건에 !cancelled() 가 없다 — fetch 러너가 실패한 날(재시도가 필요한 날) 건너뛴다: ' + cond
    assert _job_if(y, 'commit') == 'always()', 'commit 잡이 fetch 실패 날에 돌지 않는다 — need_retry 를 세울 잡이 없다'


def test_reason_is_uploaded_even_when_the_runner_fails():
    """실패한 러너의 사유가 정보다. clean 산출물처럼 성공 때만 올리면 0/3 회차엔
    판정 근거가 하나도 없다."""
    y = io.open(WF, encoding='utf-8').read()
    # ⚠️ '산출물 업로드'는 앞선 echo 줄에도 있다 — 스텝 경계는 '- name:'으로 잡는다.
    blk = y[y.index('- name: 실패 사유 업로드'):y.index('- name: 산출물 업로드')]
    assert blk.strip(), '스텝 순서가 바뀌었다 — 슬라이스가 비었다'
    assert 'if: always()' in blk, '사유 업로드가 성공 러너에만 걸려 있다'
