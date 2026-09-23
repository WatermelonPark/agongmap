# -*- coding: utf-8 -*-
"""알림 곁가지(month_lag·batch_notes·.fetch_failed)가 실제로 줄을 찍고 그 줄이 기록에 실리는지 본다.

리뷰 2026-09-18 20번: 두 CLI 가 아무것도 찍지 않아도, 워크플로의 `rep "$LAG"` 를 지워도 초록이었다.
`|| true` 와 rc=0 설계라 이 경로가 고장 나면 뒤처짐 알림이 영구히 조용해진다. 또 month_lag 가 찍는
줄 형식과 형식기가 읽는 형식 사이의 계약을 잇는 시험이 없었다(구분자를 바꿔도 초록).

깨뜨리면 빨개지는 것(각각 확인):
  - month_lag.main 이 출력을 안 하면 → cli 시험 · batch_notes.main 도 같다
  - 워크플로에서 `rep "$LAG"` 나 NOTES 루프의 rep 를 지우면 → 워크플로 시험
  - month_lag.line 의 구분자 ' / ' 를 바꾸면 → 계약 시험
  - .fetch_failed 를 업로드 목록이나 커밋 잡에서 빼면 → fetch_failed 시험
픽스처: 임시 data.js(ADV·STATS 최소 형태)로 두 CLI 를 실제 프로세스로 띄운다.
"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import format_batch_report as F  # noqa: E402
import month_lag as ML  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')


def _data_js(tmp_path, adv, stats):
    p = tmp_path / 'data.js'
    p.write_text('/*ADV_DATA_START*/ const ADV=%s; /*ADV_DATA_END*/\nconst STATS=%s;\n'
                 % (json.dumps(adv, ensure_ascii=False), json.dumps(stats, ensure_ascii=False)), encoding='utf-8')
    return str(p)


def _cli(name, data):
    p = subprocess.run([sys.executable, os.path.join(TOOLS, name), '--data', data],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    assert p.returncode == 0, p.stderr[-300:]
    return p.stdout


def test_month_lag_cli_prints_the_lag_line(tmp_path):
    data = _data_js(tmp_path, {'monthly': {'rows': [{'p': '2026.08'}]}},
                    {'미분양': {'dates': ['2026.05']}, '금리': {'dates': ['2026.08']}})
    out = _cli('month_lag.py', data)
    assert out.startswith(ML.MARK) and '미분양 2026.05' in out and '최신 2026.08' in out, out


def test_batch_notes_cli_prints_the_permit_gap_line(tmp_path):
    adv = {'sido': {'zones': [{'z': '서울', 'pbr': 1.0}, {'z': '제주', 'pbr': None}]}}
    out = _cli('batch_notes.py', _data_js(tmp_path, adv, {}))
    assert '인허가 신호 빠짐' in out and '제주' in out and '서울' not in out, out


def test_lag_line_is_readable_by_the_report_formatter():
    """month_lag 가 찍는 줄을 형식기가 그대로 읽어야 한다 — 두 파일 사이의 형식 계약."""
    stats = {'미분양': {'dates': ['2026.05']}, '분양': {'dates': ['2026.06']}, '금리': {'dates': ['2026.08']}}
    line = ML.line({}, stats)
    say, months = F.lag_notice([line])
    assert months == 3 and say and '2026년 8월' in say, (line, say)
    # 계열마다 제 기준월이 붙어야 한다 — 구분자가 바뀌면 두 계열이 한 덩어리로 읽혀 한쪽 달이 사라진다
    assert '미분양가 2026년 5월 기준' in say and '분양가 2026년 6월 기준' in say, say


def _code():
    yml = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    return '\n'.join(l for l in yml.splitlines() if not l.lstrip().startswith('#'))


def test_workflow_records_what_the_two_clis_print():
    code = _code()
    assert re.search(r'LAG=\$\(python3 tools/month_lag\.py', code) and 'rep "$LAG"' in code, 'month_lag 출력이 기록에 안 실린다'
    assert re.search(r'NOTES=\$\(python3 tools/batch_notes\.py', code) and 'rep "$LN"' in code, 'batch_notes 출력이 기록에 안 실린다'
    assert code.find('rep "$LAG"') < code.find('git add -A -- $TARGETS'), '기록이 커밋 판단 뒤에 온다'


def test_non_core_fetch_failures_reach_the_record():
    code = _code()
    up = code[code.find('name: 산출물 업로드'):code.find('commit:')]
    assert '.fetch_failed' in up, '원천 일부 실패 파일이 아티팩트에 안 실린다'
    assert '"$SRC/.fetch_failed"' in code and '원천 일부 실패' in code, '커밋 잡이 비핵심 실패를 기록하지 않는다'
    assert re.search(r'rep "%s 원천 일부 실패' % re.escape(ML.MARK), code), 'ℹ️ 줄이어야 한다 — ⚠️ 면 매 회차 메일이 간다'
