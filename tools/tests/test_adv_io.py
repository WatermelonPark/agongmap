# -*- coding: utf-8 -*-
"""data.js 읽기·쓰기 정본(tools/adv_io.py, 백로그 61-A).

왜 이 시험이 있나. 같은 정규식이 도구 열 곳·시험 열다섯 곳에 조금씩 다른 꼴로 복제돼 있었다. 둘(/weekly/ 생성기·감시)은 끝
표식 없이 첫 `});` 에서 멈추는 꼴이라, 값 안에 그 글자가 든 날 JSON 이 잘렸을 것이다. 이제 모두 adv_io 를 거친다.

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - ADV_RE 를 옛 꼴 `/\\*ADV_DATA_START\\*/const ADV=(\\{.*?\\});`(끝 표식 없음)로 되돌리면
    → test_value_with_closing_text_is_not_cut, test_spaces_around_the_block
  - STATS_RE 가 표식을 요구하게 바꾸면(시험 픽스처는 표식 없이 `const STATS={};` 를 쓴다) → test_fixture_without_stats_marks
  - put 이 쓰는 JSON 모양을 바꾸면(예: ensure_ascii=True 로 한글을 \\u 로) → test_put_is_a_no_op_on_the_real_file
  - 도구나 시험에 data.js 읽기 정규식·표식 찾기를 다시 복제하면 → test_no_other_reader
픽스처: 저장소의 실제 data.js 와, 시험 픽스처가 쓰는 두 꼴(표식 안 공백, STATS 표식 없음)을 손으로 쓴 작은 글자.
"""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import adv_io as AIO  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def test_put_is_a_no_op_on_the_real_file():
    text = AIO.read_text()
    adv, stats = AIO.load()
    same = AIO.put(AIO.put(text, 'STATS', stats), 'ADV', adv) == text   # 수 MB 글자 — pytest 가 차이를 그리지 않게 참거짓만 본다
    assert same, '읽고 그대로 쓰면 data.js 가 한 글자도 바뀌지 않아야 한다'


def test_spaces_around_the_block():
    text = '/*ADV_DATA_START*/ const ADV={"a":1}; /*ADV_DATA_END*/\nconst STATS={"b":2};\n'
    assert AIO.adv_of(text) == {'a': 1} and AIO.stats_of(text) == {'b': 2}


def test_fixture_without_stats_marks():
    text = '/*ADV_DATA_START*/const ADV={};/*ADV_DATA_END*/\nconst STATS={"x":[1]};\n'
    assert AIO.stats_of(text) == {'x': [1]}


def test_value_with_closing_text_is_not_cut():
    """값 안의 '};' 에서 멈추지 않는다 — 끝 표식까지 읽는다(옛 꼴은 여기서 JSON 이 잘렸다)."""
    obj = {'note': 'var x = {a: 1};', 'n': 2}
    text = '/*ADV_DATA_START*/const ADV=%s;/*ADV_DATA_END*/' % json.dumps(obj, ensure_ascii=False)
    assert AIO.adv_of(text) == obj


def test_missing_block_is_an_error():
    with pytest.raises(ValueError):
        AIO.adv_of('const STATS={};')
    with pytest.raises(ValueError):
        AIO.stats_of('/*ADV_DATA_START*/const ADV={};/*ADV_DATA_END*/')


# 정본 밖의 '읽기' 흔적 — 정규식 원문 속 이스케이프된 표식, STATS 선언 정규식, 표식 글자를 find 로 찾는 꼴.
# 픽스처가 data.js 를 **쓰는** 글자('/*ADV_DATA_START*/ const ADV=%s; …')는 읽기가 아니라 걸리지 않는다.
READER = re.compile(r"ADV_DATA_START\\\*|const STATS\\s|\.find\(\s*'(?:/\*(?:ADV|STATS)_DATA_(?:START|END)\*/|const (?:ADV|STATS)=)'")


def test_no_other_reader():
    here = os.path.basename(__file__)
    bad = []
    for d in ('tools', os.path.join('tools', 'tests')):
        for name in sorted(os.listdir(os.path.join(ROOT, d))):
            if not name.endswith('.py') or name in ('adv_io.py', here):
                continue
            src = io.open(os.path.join(ROOT, d, name), encoding='utf-8').read()
            if READER.search(src):
                bad.append(os.path.join(d, name))
    assert not bad, 'data.js 를 adv_io 밖에서 따로 읽는다: %s' % bad
