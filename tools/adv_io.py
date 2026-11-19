# -*- coding: utf-8 -*-
"""data.js 의 두 데이터 블록(ADV·STATS)을 읽고 쓰는 정본(백로그 61-A, 2026-11-19).

같은 정규식이 도구 열 곳에 조금씩 다른 꼴로 복제돼 있었다(2026-11-13 전수 리뷰). 두 곳(/weekly/ 생성기·감시)은 끝 표식 없이
첫 `});` 에서 멈추는 꼴이라, 값 안에 그 글자가 들어오는 날 JSON 이 잘린 채 읽혔을 것이다. 이제 모두 여기를 거친다.

  ADV   — `/*ADV_DATA_START*/ const ADV={…}; /*ADV_DATA_END*/` (시작·끝 표식 사이, 앞뒤 공백 허용)
  STATS — `const STATS={…};` 뒤에 주석·다음 선언·파일 끝. data.js 에서는 STATS 표식 사이에 있지만, 시험 픽스처는 표식 없이
          `const STATS={};` 만 쓰므로 표식에 기대지 않는다.

표준 라이브러리만 쓴다 — 감시(check_freshness)와 생성기는 설치 없이 돈다.
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(ROOT, 'data.js')

ADV_RE = re.compile(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', re.S)
STATS_RE = re.compile(r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', re.S)
_RE = {'ADV': ADV_RE, 'STATS': STATS_RE}


def read_text(path=None):
    return io.open(path or DATA_JS, encoding='utf-8').read()


def _match(text, name):
    m = _RE[name].search(text)
    if not m:
        raise ValueError('data.js 에서 %s 블록을 찾지 못했다' % name)
    return m


def adv_of(text):
    """data.js 글자 → ADV dict. 블록이 없으면 ValueError."""
    return json.loads(_match(text, 'ADV').group(1))


def stats_of(text):
    """data.js 글자 → STATS dict. 블록이 없으면 ValueError."""
    return json.loads(_match(text, 'STATS').group(1))


def load(path=None):
    """data.js → (ADV, STATS)."""
    text = read_text(path)
    return adv_of(text), stats_of(text)


def load_adv(path=None):
    return adv_of(read_text(path))


def put(text, name, obj):
    """text 의 name('ADV'·'STATS') 블록 값만 obj 의 압축 JSON 으로 바꾼 새 글자. 표식·선언·주석은 그대로 둔다."""
    m = _match(text, name)
    return text[:m.start(1)] + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + text[m.end(1):]
