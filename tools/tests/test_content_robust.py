# -*- coding: utf-8 -*-
"""원고 한 편의 탈이 생성기 전체(와 그날 데이터 커밋)를 세우지 않는다 — 2026-11-13 전수 리뷰.

검사기(content_check)가 OK 를 낸 원고 한 편이 생성기를 ① 끝나지 않게 하거나(표 머리가 아닌 '|' 줄) ② 예외로 끝냈다
(sources 항목이 '이름: 값' 꼴이라 짝으로 읽힘). 배치는 생성기가 실패하면 그날 데이터를 커밋하지 않고, 끝나지 않으면 잡 시간
상한까지 매달린다. 세 겹으로 막는다: 변환기는 반드시 끝나고, 꼴이 틀린 프런트매터는 ContentError 로 그 글만 건너뛰며,
그래도 난 예상 밖 예외는 생성기가 그 글에 가둔다. 검사기는 생성기의 '한 편 굽기'를 그대로 돌려 같은 탈을 미리 알린다.
"""
import io
import os
import subprocess
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import content_check as CC          # noqa: E402
import content_md as CM             # noqa: E402
import content_tables as CT         # noqa: E402
import make_content_pages as MC     # noqa: E402

REAL = os.path.join(ROOT, 'content', 'city', 'suwon-2027-moveins.md')
# 표가 되지 못하는 '|' 줄 네 꼴 — 실제 작성 세션이 내는 모양(구분 줄을 빠뜨림, 구분 줄 끝 파이프를 빠뜨림, 문단 가운데 낀 줄,
# 표 뒤 빈 줄 다음에 이어 쓴 행).
STRAY = ('| a | b |\n| 1 | 2 |\n',
         '| a | b |\n|---|---\n| 1 | 2 |\n',
         '글입니다.\n| x |\n글입니다.\n',
         '| a |\n|---|\n| 1 |\n\n| 2 |\n')


def _copy(tmp_path, edit):
    """실제 원고 한 편(수원)을 고쳐 tmp 의 content/city/ 에 둔다 → 경로."""
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True, exist_ok=True)
    text = edit(io.open(REAL, encoding='utf-8').read())
    p = d / os.path.basename(REAL)
    p.write_text(text, encoding='utf-8')
    return str(p)


def test_markdown_always_ends_on_pipe_lines_that_are_not_a_table():
    """표 머리가 아닌 '|' 줄이 있어도 markdown() 이 끝나고, 그 줄은 문단으로 나오며 stray 에 줄 번호가 담긴다.

    변이(실제로 확인): 문단 갈래를 예전처럼 `para = []` 로 시작해 첫 줄을 조건부로만 먹게 되돌리면 그 줄이 글에서 사라져
          빨개진다. 거기에 걸음 감시(`if i == last`)까지 지우면 끝나지 않아 시간 초과로 빨개진다(딴 프로세스에서 20초 상한으로
          본다 — 이 시험이 게이트를 매달지 않는다).
    픽스처: STRAY 네 꼴.
    """
    code = ('import sys; sys.path.insert(0, %r)\n'
            'import make_content_pages as M\n'
            'for t in %r:\n'
            '    st = []\n'
            '    h = M.markdown(t, st)\n'
            '    assert st, t\n'
            '    assert all(("<p>" + s) in h or s in h for _n, s in st), (t, h)\n'
            'print("ended")\n') % (os.path.join(ROOT, 'tools'), STRAY)
    try:
        r = subprocess.run([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=20)
    except subprocess.TimeoutExpired:
        pytest.fail("markdown() 이 표 머리가 아닌 '|' 줄에서 끝나지 않는다")
    assert r.returncode == 0 and 'ended' in r.stdout, r.stderr[-600:]
    st = []
    MC.markdown(STRAY[3], st)
    assert st == [(5, '| 2 |')], '제대로 된 표의 줄까지 셌거나 줄 번호가 틀리다: %r' % st


def test_check_tells_the_author_about_a_table_that_did_not_form(tmp_path):
    """검사기가 '표가 되지 못한 표 줄'을 고칠 곳(✗)으로 알린다 — 예전엔 OK 를 내고 생성기가 매달렸다.

    변이(실제로 확인): content_check.check_post 에서 stray 줄을 out 에 싣는 for 문을 지우면 빨개진다.
    픽스처: 실제 수원 원고 끝에 구분 줄 없는 표 두 줄을 붙인 판(리뷰의 재현 그대로).
    """
    data = CT.load()
    clean = _copy(tmp_path, lambda t: t)
    probs, _waits, _rel = CC.check_post(clean, data, root=str(tmp_path))
    assert not probs, '고치지 않은 실제 원고가 걸린다 — 픽스처가 깨졌다: %r' % probs
    bad = _copy(tmp_path, lambda t: t.rstrip('\n') + '\n\n| 구분 | 값\n| 가 | 1\n')
    probs, _waits, _rel = CC.check_post(bad, data, root=str(tmp_path))
    n = io.open(bad, encoding='utf-8').read().split('\n').index('| 구분 | 값') + 1
    assert [ln for ln, why in probs if '표 줄이 표가 되지 못했다' in why] == [n, n + 1], probs


def test_wrong_shaped_front_matter_is_a_content_error(tmp_path):
    """sources 항목이 '이름: 값' 꼴이거나 region 이 목록이면 ContentError 다 — 생성기는 그 글만 건너뛰고 검사기는 ✗ 로 알린다.

    왜: 파서는 목록 항목의 '이름: 값'을 짝으로 읽는다(faq 의 q·a). sources 에 그 꼴을 쓰면 글이 아닌 짝이 되어 생성기가
        html.escape(dict) 에서, region 목록은 .strip() 에서 예외로 끝났다.
    변이(실제로 확인): content_md.validate 의 sources 꼴 검사를 지우면 첫 단정이, region 검사를 지우면 둘째 단정이 빨개진다.
    픽스처: 실제 수원 원고의 sources 에 '- KOSIS: 주민등록인구현황' 한 줄을 더한 판, region 을 목록으로 바꾼 판.
    """
    data = CT.load()
    pair = _copy(tmp_path, lambda t: t.replace('sources:\n', 'sources:\n  - KOSIS: 주민등록인구현황\n', 1))
    with pytest.raises(CM.ContentError) as e:
        CM.read(pair)
    assert 'sources' in str(e.value)
    probs, _w, _r = CC.check_post(pair, data, root=str(tmp_path))
    assert probs and 'sources' in probs[0][1], probs
    text = io.open(REAL, encoding='utf-8').read()
    line = next(ln for ln in text.split('\n') if ln.startswith('region:'))
    lst = _copy(tmp_path, lambda t: t.replace(line, 'region:\n  - 수원\n  - 화성', 1))
    with pytest.raises(CM.ContentError) as e:
        CM.read(lst)
    assert 'region' in str(e.value)


def _three_posts(monkeypatch, tmp_path, boom):
    """글 셋(a·b·c)을 굽는 main() — b 를 굽다 boom 이 난다. 쓰기 자리는 tmp_path. → 구워진 slug 목록(끝 바퀴)."""
    posts = [('danji', {'slug': s, 'date': '2026-11-0%d' % i, 'updated': '2026-11-0%d' % i,
                         'section': 'danji', 'title': s}, 'body') for i, s in enumerate('abc', 1)]
    built = []

    def fake_build(meta, body, data, prev=None, nxt=None, others=None):
        if meta['slug'] == 'b':
            raise boom
        if others is not None:
            built.append(meta['slug'])
        return '<html></html>', '2026-11-01'

    monkeypatch.setattr(MC, 'ROOT', str(tmp_path))
    monkeypatch.setattr(MC, 'collect', lambda strict=False, old_format=None: (list(posts), []))
    monkeypatch.setattr(MC.CT, 'load', lambda: {})
    monkeypatch.setattr(MC.CT, 'fill_meta', lambda meta, data: meta)
    monkeypatch.setattr(MC.CT, 'check_lengths', lambda meta: meta)
    monkeypatch.setattr(MC, 'build_page', fake_build)
    monkeypatch.setattr(MC, 'build_index', lambda sec, metas: ('<html></html>', None))
    monkeypatch.setattr(MC, 'build_reports', lambda metas, data: ('<html></html>', None))
    monkeypatch.setattr(MC.SP, 'read_old', lambda fp: None)
    monkeypatch.setattr(MC.SP, 'keep_dates', lambda page, old, lm: (page, lm, False))
    monkeypatch.setattr(MC.I, 'update_sitemap', lambda entries: None)
    for name in ('write_home_recent', 'write_zone_posts', 'write_weekly_column', 'write_moveins_cities'):
        monkeypatch.setattr(MC, name, lambda metas: 0)
    return built


def test_an_unexpected_crash_in_one_post_stays_in_that_post(tmp_path, monkeypatch, capsys):
    """한 편을 굽다 난 예상 밖 예외(AttributeError 등)는 그 글만 건너뛰게 하고, 나머지는 굽고 0 으로 끝난다. --strict 는 멈춘다.

    변이(실제로 확인): main() 의 본문 바퀴에서 `except Exception` 갈래를 지우면 main() 이 AttributeError 로 끝나 빨개진다.
    픽스처: 같은 섹션 글 셋에서 가운데 b 만 build_page 가 AttributeError 를 낸다(실제 사례: html.escape 에 짝이 들어감).
    """
    built = _three_posts(monkeypatch, tmp_path, AttributeError("'dict' object has no attribute 'replace'"))
    assert MC.main() == 0
    assert built == ['a', 'c']
    assert not (tmp_path / 'danji' / 'b').exists()
    said = capsys.readouterr()
    assert 'danji/b.md' in (said.out + said.err) and 'AttributeError' in (said.out + said.err), '건너뛴 사유가 기록에 없다'
    with pytest.raises(AttributeError):
        MC.main(strict=True)


def test_check_runs_the_generators_own_build(tmp_path, monkeypatch):
    """검사기가 생성기의 build_page 를 그대로 돌려, 굽다 난 예외를 고칠 곳(✗)으로 알린다(검사 통과 = 생성기에서도 구워짐).

    변이(실제로 확인): content_check.check_post 의 '한 편 굽기' try 블록을 지우면 빨개진다.
    픽스처: 고치지 않은 실제 수원 원고 + build_page 가 RuntimeError 를 내는 생성기(다른 검사는 모두 통과하는 상태).
    """
    data = CT.load()
    p = _copy(tmp_path, lambda t: t)

    def boom(*a, **k):
        raise RuntimeError('굽다가 탈')

    monkeypatch.setattr(MC, 'build_page', boom)
    probs, _w, _r = CC.check_post(p, data, root=str(tmp_path))
    assert len(probs) == 1 and 'RuntimeError' in probs[0][1] and '굽다가 탈' in probs[0][1], probs
