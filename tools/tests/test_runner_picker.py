# -*- coding: utf-8 -*-
"""커밋 잡의 러너 산출물 고르기(update-cloud.yml)를 **그 셸 그대로** 돌려 본다(2026-09-26 데이터 감사 #5).

착공 호출만 죽은 러너는 준공만 새 분기라 ADV.sido 의 시야가 H = lead − 1 인데 rc=0·clean 으로 올라온다. 그 산출물은
make_sido_pages 가 ABORT 해 그날 커밋 전체(주간·월간 시세 포함)를 막는다. 예전 고르기는 weekly·monthly·sidoL 만
견줘 셋이 같으면 번호가 앞선 러너가 이겼다 — 어긋난 러너가 1번이면 정합한 2번을 두고 그것을 골랐다.

워크플로 파일에서 고르기 반복문을 잘라 bash -e(워크플로 기본 셸과 같은 옵션)로 tmp 안에서 돌린다. 산출물은 저장소의
실제 data-core.js 를 읽어 ADV.sido 의 L·S·H 만 바꾼 사본이다(저장소 파일은 읽기만 한다). 원천 호출 없음.
"""
import io
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
WF = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
CORE = os.path.join(ROOT, 'data-core.js')
# ADV.sido 의 네 키. 고르기의 grep 과 같은 모양으로 찾는다(각각 data-core.js 에 한 번씩 있다).
KEYS = {'L': r'"L":"(\d{4})Q([1-4])"', 'S': r'"S":"\d{4}Q[1-4]"', 'H': r'"H":(\d+)', 'lead': r'"lead":(\d+)'}


def _picker():
    """update-cloud.yml 에서 산출물 고르기 반복문(SRC=""; BEST="" … done)을 그대로 잘라 온다."""
    lines = io.open(WF, encoding='utf-8').read().split('\n')
    start = next(i for i, ln in enumerate(lines) if ln.strip().startswith('SRC=""; BEST=""'))
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == 'done')
    ind = len(lines[start]) - len(lines[start].lstrip())
    body = '\n'.join(ln[ind:] for ln in lines[start:end + 1])
    return body + '\necho "PICK=$SRC"\n'


def _q(y, q, d):
    k = y * 4 + (q - 1) + d
    return '%dQ%d' % (k // 4, k % 4 + 1)


def _saved():
    src = io.open(CORE, encoding='utf-8').read()
    for k, rx in KEYS.items():
        assert len(re.findall(rx, src)) == 1, (
            'data-core.js 에서 ADV.sido 의 "%s" 를 하나로 못 찾았다 — 고르기의 grep 도 못 본다' % k)
    m = re.search(KEYS['L'], src)
    return src, int(m.group(1)), int(m.group(2)), int(re.search(KEYS['lead'], src).group(1))


def _core(L, S, H):
    src = _saved()[0]
    src = re.sub(KEYS['L'], '"L":"%s"' % L, src)
    src = re.sub(KEYS['S'], '"S":"%s"' % S, src)
    return re.sub(KEYS['H'], '"H":%d' % H, src)


def _pick(tmp_path, arts):
    for n, body in enumerate(arts, 1):
        d = tmp_path / '_art' / ('data-%d' % n)
        d.mkdir(parents=True)
        (d / 'data-core.js').write_text(body, encoding='utf-8')
    out = subprocess.run(['bash', '-e', '-c', _picker()], cwd=str(tmp_path),
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return re.search(r'PICK=_art/data-(\d)', out.stdout).group(1)


@pytest.mark.skipif(not shutil.which('bash'), reason='bash 없음(워크플로 러너에는 있다)')
def test_picker_prefers_the_runner_whose_supply_horizon_is_consistent(tmp_path):
    """주간·월간이 같으면 시야가 맞는(H == lead) 산출물을 고른다 — 순서가 어떻든, 어긋난 쪽의 실적 분기가 더 새것이어도.
    둘 다 맞으면 예전처럼 실적 분기(sidoL)가 새것인 쪽이다.

    변이: 고르기의 `elif … [ "$hok" \\> "$BESTHOK" ]; then newer=1` 줄을 지우고 다음 줄의 `[ "$hok" = "$BESTHOK" ] &&` 를
          지우면(예전 고르기) 첫 경우가 1번을 골라 빨개진다(확인). 시야 비교를 sidoL 비교 **뒤**로 옮기면 셋째 경우가
          어긋난 쪽(새 분기)을 골라 빨개진다(확인).
    픽스처: 저장소 data-core.js 사본 둘. 어긋난 쪽 = 실적 L 만 다음 분기·착공 S 는 그대로·H = lead − 1(감사 재현값 H=11),
            정합한 쪽 = L·S 모두 다음 분기·H = lead(착공까지 받은 러너) 또는 저장분 그대로(H = lead).
    """
    _, y, q, lead = _saved()
    cur, nxt = _q(y, q, 0), _q(y, q, 1)
    bad = _core(nxt, cur, lead - 1)
    good_new = _core(nxt, nxt, lead)
    good_old = _core(cur, cur, lead)
    assert _pick(tmp_path / 'a', [bad, good_new]) == '2', '어긋난 1번을 골랐다 — make_sido_pages 가 ABORT 한다'
    assert _pick(tmp_path / 'b', [good_new, bad]) == '1'
    assert _pick(tmp_path / 'c', [bad, good_old]) == '2', '실적 분기가 새것이라고 어긋난 산출물을 골랐다'
    assert _pick(tmp_path / 'd', [good_old, good_new]) == '2', '정합한 둘 중에는 실적 분기가 새것인 쪽이다'
