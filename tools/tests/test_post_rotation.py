# -*- coding: utf-8 -*-
"""지역 편 순번은 **실제 발행**을 따라간다 (2026-09-17).

예전엔 초안을 저장할 때마다 순회 기록이 한 칸 넘어갔다. 지역 편은 격주인데 생성기는
매주(주간 글 때문에) 돌아서, 주간 글만 쓴 주에 지역 하나가 조용히 소비됐다 — 9/17에
세종이 그렇게 건너뛰어질 뻔했다. 16주 순회에서 어떤 시도는 글이 한 번도 안 나간다.

변이 확인(실제로 깨뜨려 봄):
  - commit()이 지금 고른 지역을 seen에 넣게 바꾸면 → test_generating_twice_picks_the_same_zone 빨강
  - `> lap`을 `> 0`으로 바꾸면 → test_second_lap_starts_after_everyone_is_published 빨강
  - legacy 자리표를 지우지 않게 바꾸면 → test_legacy_state_is_not_double_counted 빨강
픽스처: rows는 pick_zone이 읽는 두 키(z·tot)만, published는 _published_zone_posts의
반환 모양({지역: {주소}})을 재현한다. STATE는 tmp_path로 돌려 실제 순회 기록을 안 건드린다.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import make_naver_post as P  # noqa: E402

ROWS = [{'z': z, 'tot': t} for z, t in
        (('서울', 300000), ('대구', 9000), ('부산', -4000), ('경기', 50000),
         ('세종', 907), ('전남광주', 52000), ('강원', 100))]


def _env(tmp_path, monkeypatch, state=None):
    monkeypatch.setattr(P, 'OUT', str(tmp_path))
    monkeypatch.setattr(P, 'STATE', str(tmp_path / '.rotation.json'))
    if state is not None:
        io.open(P.STATE, 'w', encoding='utf-8').write(json.dumps(state, ensure_ascii=False))


def _pub(*names):
    return {n: {'https://blog.example/%s' % n} for n in names}


def test_generating_twice_picks_the_same_zone(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    pub = _pub('서울', '대구', '부산', '경기')
    pick, seq, total, commit = P.pick_zone(ROWS, published=pub)
    commit()                                   # 주간 글만 쓰고 저장한 주
    again = P.pick_zone(ROWS, published=pub)
    assert (pick['z'], seq, total) == ('세종', 5, 7)
    assert again[0]['z'] == '세종', '발행하지 않았는데 순번이 넘어갔다'


def test_moves_on_once_the_post_is_published(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    pick = P.pick_zone(ROWS, published=_pub('서울', '대구', '부산', '경기', '세종'))[0]
    assert pick['z'] == '전남광주'


def test_cache_remembers_posts_that_fell_out_of_the_feed(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    P.pick_zone(ROWS, published=_pub('서울', '대구'))[3]()
    pick = P.pick_zone(ROWS, published=_pub('대구'))[0]      # 서울 글이 RSS에서 밀려남
    assert pick['z'] == '부산'


def test_legacy_state_is_not_double_counted(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, {'done': ['서울', '대구']})
    pick, seq, _, commit = P.pick_zone(ROWS, published=_pub('서울', '대구'))
    commit()
    saved = json.load(io.open(P.STATE, encoding='utf-8'))['posts']
    assert (pick['z'], seq) == ('부산', 3)
    assert all(len(v) == 1 for v in saved.values()), saved


def test_second_lap_starts_after_everyone_is_published(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    everyone = _pub(*[r['z'] for r in ROWS])
    pick, seq, _, _ = P.pick_zone(ROWS, published=everyone)
    assert (pick['z'], seq) == ('서울', 1)
    everyone['서울'].add('https://blog.example/서울-2')
    assert P.pick_zone(ROWS, published=everyone)[0]['z'] == '대구'


def test_unreadable_feed_falls_back_to_cache(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch, {'done': ['서울', '대구', '부산', '경기']})
    monkeypatch.setattr(P, '_published_zone_posts', lambda names: None)
    assert P.pick_zone(ROWS)[0]['z'] == '세종'
