# -*- coding: utf-8 -*-
"""건너뛴 글의 옛 페이지가 라이브에 남지 않게 정리한다(백로그 59).

원고 한 편이 자리표를 못 채워 건너뛰면 예전에 구워 둔 `<섹션>/<slug>/index.html` 이 그대로 남아, 없는 원고의 페이지가
계속 서고 sitemap·목록과 어긋났다. 이번 회차에 구운 페이지는 건드리지 않고, 구운 것이 하나도 없는 회차에는 아무것도
지우지 않는다(데이터 탈로 콘텐츠를 통째로 날리지 않게).
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_content_pages as M  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _mk(root, rel, text='x'):
    p = os.path.join(str(root), *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, 'w', encoding='utf-8') as f:
        f.write(text)


def test_prune_removes_only_unbuilt_generated_pages(tmp_path, monkeypatch):
    """이번 회차에 굽지 않은 `<섹션>/<slug>/index.html` 만 지운다.

    변이(실제로 확인): prune_stale_pages 의 `if (sec, name) in built: continue` 를 지우면 이번에 구운 ok 페이지까지
          지워 빨개진다. index.html 이 없는 디렉터리 조건을 지우면 note 가 지워져 빨개진다.
    픽스처: 구운 city/ok, 건너뛴 city/skip, 페이지가 아닌 city/note(readme 만), 사라진 원고의 gtx/gone, 섹션 목록 파일.
    """
    monkeypatch.setattr(M, 'ROOT', str(tmp_path))
    _mk(tmp_path, 'city/ok/index.html')
    _mk(tmp_path, 'city/skip/index.html')
    _mk(tmp_path, 'city/note/readme.txt')
    _mk(tmp_path, 'gtx/gone/index.html')
    _mk(tmp_path, 'city/index.html')
    removed = M.prune_stale_pages({('city', 'ok')}, wrote=1)
    assert sorted(removed) == ['/city/skip/', '/gtx/gone/'], removed
    assert not os.path.exists(str(tmp_path / 'city' / 'skip'))
    assert not os.path.exists(str(tmp_path / 'gtx' / 'gone'))
    assert os.path.exists(str(tmp_path / 'city' / 'ok' / 'index.html'))
    assert os.path.exists(str(tmp_path / 'city' / 'note' / 'readme.txt'))
    assert os.path.exists(str(tmp_path / 'city' / 'index.html'))


def test_prune_does_nothing_when_no_page_was_baked(tmp_path, monkeypatch):
    """구운 것이 0편인 회차에는 아무것도 지우지 않는다 — 전부 건너뛴 날 콘텐츠 페이지를 통째로 날리면 안 된다.

    변이(실제로 확인): `if not wrote: return []` 를 지우면 이 시험이 빨개진다.
    """
    monkeypatch.setattr(M, 'ROOT', str(tmp_path))
    _mk(tmp_path, 'city/skip/index.html')
    assert M.prune_stale_pages(set(), wrote=0) == []
    assert os.path.exists(str(tmp_path / 'city' / 'skip' / 'index.html'))


def test_main_calls_the_prune_after_building():
    """생성기 main 이 실제로 이 정리를 부른다 — 함수만 있고 호출이 빠지면 같은 사고가 그대로 난다."""
    src = io.open(os.path.join(HERE, '..', 'make_content_pages.py'), encoding='utf-8').read()
    assert 'prune_stale_pages(written, wrote)' in src, 'main 이 옛 페이지 정리를 부르지 않는다'
