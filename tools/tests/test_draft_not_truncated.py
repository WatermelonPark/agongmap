# -*- coding: utf-8 -*-
"""초안 생성이 도중에 멈춰도 기존 초안이 빈 파일이 되지 않는다(2026-09-18 리뷰 7번).

`io.open(path, 'w').write(render(...))` 는 파일을 먼저 열어 0바이트로 만든 뒤 render 를 돌린다.
이론 3편의 생성 가드(SystemExit)가 걸리자 사람이 해석 문단을 채워 둔 drafts/theory-03.html 이
18,140바이트에서 0바이트가 됐다. drafts/ 는 gitignore 라 되돌릴 데가 없다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - make_theory_post.main 을 `io.open(path,'w',...).write(render(post))` 로 되돌리면 → 보존 시험, 패턴 시험
  - make_naver_post.write_draft 가 임시 파일 없이 path 를 바로 열면 → 쓰는 도중 실패 시험
픽스처: tmp_path 안의 기존 초안(사람이 손댄 내용) + 생성 가드가 걸린 render. 저장소의 drafts/ 는 건드리지 않는다.
"""
import glob
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
HAND_WRITTEN = '<p>사람이 채운 해석 문단</p>'


def test_theory_guard_stop_keeps_the_existing_draft(tmp_path, monkeypatch):
    path = tmp_path / 'theory-03.html'
    path.write_text(HAND_WRITTEN, encoding='utf-8')
    monkeypatch.setattr(T, 'OUT', str(tmp_path))

    def guarded(post):
        raise SystemExit('생성 가드: 최저 지역이 서울이 아니다')
    monkeypatch.setattr(T, 'render', guarded)
    with pytest.raises(SystemExit):
        T.main(['3'])
    assert path.read_text(encoding='utf-8') == HAND_WRITTEN, '생성이 멈췄는데 기존 초안이 바뀌었다'


def test_write_draft_failure_midway_keeps_the_old_file(tmp_path, monkeypatch):
    path = tmp_path / 'naver-x.html'
    path.write_text(HAND_WRITTEN, encoding='utf-8')

    real_open = io.open

    def failing_open(p, *a, **kw):
        f = real_open(p, *a, **kw)
        if 'w' in (a[0] if a else kw.get('mode', '')):
            f.write('반쯤 쓴')
            f.close()
            raise IOError('디스크 오류')
        return f
    monkeypatch.setattr(P.io, 'open', failing_open)
    with pytest.raises(IOError):
        P.write_draft(str(path), '<p>새 초안</p>')
    monkeypatch.undo()
    assert path.read_text(encoding='utf-8') == HAND_WRITTEN, '쓰다 실패했는데 기존 초안이 깨졌다'


def test_write_draft_writes_and_leaves_no_temp(tmp_path):
    path = tmp_path / 'a.html'
    P.write_draft(str(path), '<p>새 초안</p>\n둘째 줄')
    assert path.read_bytes() == '<p>새 초안</p>\n둘째 줄'.encode('utf-8')   # newline='\n' 유지
    assert os.listdir(str(tmp_path)) == ['a.html']


def test_no_tool_opens_a_file_before_rendering_into_it():
    bad = []
    for p in glob.glob(os.path.join(TOOLS, '*.py')):
        s = io.open(p, encoding='utf-8').read()
        for m in re.finditer(r"open\([^()\n]*['\"]w['\"][^()\n]*\)\.write\(\s*render\(", s):
            bad.append('%s:%d' % (os.path.basename(p), s[:m.start()].count('\n') + 1))
    assert not bad, '파일을 연 뒤에 render 를 돌린다 — 멈추면 0바이트가 남는다: %s' % bad
