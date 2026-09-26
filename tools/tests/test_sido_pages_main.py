# -*- coding: utf-8 -*-
"""make_sido_pages.main() 의 게이트와 파일 처리를 **실행해서** 본다(2026-09-23 전체 점검 시험 보강).

기존 시험은 build_page 같은 조각이나 저장소에 구워진 페이지만 봤다. 그래서 main() 안의 네 장치를
꺼도 전부 초록이었다:
  ① 준공·착공 끝 분기가 어긋난 회차(H ≠ lead)의 ABORT
  ② 통합으로 사라진 옛 주소(/zone/광주/·/zone/전남/)를 지우지 않고 안내 페이지로 바꾸는 것
  ③ 내용이 같으면 옛 페이지를 그대로 두는 keep_dates(안 그러면 20장 lastmod 가 매일 바뀐다)
  ④ 내용이 바뀌어도 최초 발행일(datePublished)을 물려받는 것

⚠️ 저장소에 쓰지 않는다. data.js·data-core.js·sitemap.xml 과 zone/광주·zone/전남 을 tmp 로 복사하고
   모듈의 ROOT·OUT·HOME_STAMP 를 그리로 돌린다. 날짜는 모듈의 _today() 를 가짜로 바꿔 정한다.
"""
import datetime
import io
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as P  # noqa: E402
import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DAY1, DAY2 = '2026-09-01', '2026-09-08'


def _set_today(monkeypatch, iso):
    # 생성기는 오늘을 P._today()(KST, tools/kst.py) 한 곳에서만 읽는다(2026-09-26 데이터 감사). 전에는 모듈의
    # datetime 을 가짜로 바꿨는데, 날짜 출처가 kst 로 옮겨 간 뒤에는 그 자리를 바꿔야 날짜가 정해진다.
    datetime.date.fromisoformat(iso)   # 형식 확인
    monkeypatch.setattr(P, '_today', lambda: iso)


@pytest.fixture
def site(tmp_path, monkeypatch):
    """저장소의 실제 입력과 실제 옛 주소 안내 페이지를 복사한 작업 사본."""
    for f in ('data.js', 'data-core.js', 'sitemap.xml'):
        shutil.copy(os.path.join(ROOT, f), str(tmp_path / f))
    out = tmp_path / 'zone'
    out.mkdir()
    for old in P.MERGED_INTO:
        src = os.path.join(ROOT, 'zone', old)
        if os.path.isdir(src):
            shutil.copytree(src, str(out / old))
        else:
            (out / old).mkdir()
    # 2026-08-06 재편 전 생활권 디렉터리 — 이건 지워져야 한다
    (out / '부산권').mkdir()
    (out / '부산권' / 'index.html').write_text('old', encoding='utf-8')
    monkeypatch.setattr(P, 'ROOT', str(tmp_path))
    monkeypatch.setattr(P, 'OUT', str(out))
    monkeypatch.setattr(P, 'HOME_STAMP', str(tmp_path / 'tools' / 'data' / '.home_stamp'))
    return tmp_path


def _read(p):
    return io.open(str(p), encoding='utf-8').read()


def _lastmods(root):
    x = _read(root / 'sitemap.xml')
    return dict(re.findall(r'<loc>[^<]*/zone/([^<]*)/</loc>\s*<lastmod>([^<]*)</lastmod>', x))


def _names():
    adv, _ = P.load()
    return [z['z'] for z in adv['sido']['zones']]


def test_merged_regions_keep_a_redirect_page_and_stale_dirs_go(site, monkeypatch):
    """/zone/광주/·/zone/전남/ 은 검색·블로그·카톡에 남은 색인 주소라 지우면 404 가 된다.
    main() 이 끝난 뒤에도 새 주소로 canonical·meta refresh 를 거는 안내 페이지가 있어야 한다.

    변이: main() 의 `_write_merged_stub(p, d, MERGED_INTO[d])` 를 `shutil.rmtree(p)` 로 바꾸면
          두 디렉터리가 사라져 빨개진다(실제로 바꿔 확인). 반대로 else 가지(rmtree)를 지우면 옛
          생활권 디렉터리가 남아 빨개진다(확인).
    픽스처: 저장소의 실제 입력(data.js 등)과 실제 zone/광주·zone/전남 안내 페이지, 그리고
            2026-08-06 재편 전의 생활권 디렉터리 하나(부산권).
    """
    _set_today(monkeypatch, DAY1)
    assert P.main() == 0
    for old, new in P.MERGED_INTO.items():
        fp = site / 'zone' / old / 'index.html'
        assert fp.exists(), '/zone/%s/ 가 사라졌다 — 색인된 주소가 404 가 된다' % old
        h = _read(fp)
        url = P.SITE + '/zone/' + P.urllib.parse.quote(new) + '/'
        assert '<link rel="canonical" href="%s">' % url in h, old
        assert 'http-equiv="refresh" content="3;url=%s"' % url in h, old
        assert 'noindex' not in h
    assert not (site / 'zone' / '부산권').exists(), '옛 생활권 디렉터리가 남았다'
    lm = _lastmods(site)
    assert not set(P.MERGED_INTO) & set(lm), '안내 페이지가 sitemap 에 들어갔다'
    assert set(lm) == set(P.urllib.parse.quote(z) for z in _names())


def test_unchanged_rerun_keeps_pages_and_lastmod(site, monkeypatch):
    """데이터가 그대로인 날 다시 돌려도 페이지 바이트와 sitemap lastmod 가 그대로여야 한다.
    안 그러면 20장이 날짜만 바뀐 채 매일 커밋되고 검색엔진엔 '매일 전부 갱신'이 간다.

    변이: keep_dates 첫머리에 `return new_html, today, True` 를 넣어 무력화하면 둘째 날 모든
          페이지의 날짜와 lastmod 가 바뀌어 빨개진다(실제로 바꿔 확인).
    픽스처: 같은 입력으로 9/1 과 9/8 에 두 번 돈 배치(그 사이 원천 갱신 없음).
    """
    names = _names()
    _set_today(monkeypatch, DAY1)
    P.main()
    first = {z: _read(site / 'zone' / z / 'index.html') for z in names}
    hub1 = _read(site / 'zone' / 'index.html')
    _set_today(monkeypatch, DAY2)
    P.main()
    for z in names:
        assert _read(site / 'zone' / z / 'index.html') == first[z], '%s 가 내용 변화 없이 다시 쓰였다' % z
    assert _read(site / 'zone' / 'index.html') == hub1
    lm = _lastmods(site)
    assert set(lm.values()) == {DAY1}, 'lastmod 가 내용 변화 없이 움직였다: %s' % sorted(set(lm.values()))


def test_changed_page_keeps_its_first_publish_date(site, monkeypatch):
    """내용이 바뀐 회차에는 dateModified 만 오늘이 되고 datePublished 는 처음 발행일을 물려받는다.
    안 그러면 8월에 색인된 페이지가 '어제 처음 발행, 수정 이력 없음' 이라고 선언한다(2026-08-07 감사).

    변이: keep_dates 의 datePublished 치환(`new_html = new_html.replace(...)`)을 지우면 둘째 날
          datePublished 가 오늘로 찍혀 빨개진다(실제로 바꿔 확인).
    픽스처: 9/1 에 발행된 페이지가 있고, 9/8 회차에 그 페이지 내용이 달라진 상태(옛 판 본문에
            표식 한 줄을 넣어 '예전 데이터로 구운 판'을 재현한다). 바뀐 페이지는 서울 한 장뿐이다.
    """
    _set_today(monkeypatch, DAY1)
    P.main()
    fp = site / 'zone' / '서울' / 'index.html'
    old = _read(fp)
    assert '"datePublished": "%s"' % DAY1 in old
    io.open(str(fp), 'w', encoding='utf-8', newline='\n').write(old.replace('</main>', '<p>옛 판</p></main>', 1))
    _set_today(monkeypatch, DAY2)
    P.main()
    new = _read(fp)
    assert '옛 판' not in new, '바뀐 내용이 반영되지 않았다'
    assert '"datePublished": "%s"' % DAY1 in new, '최초 발행일이 오늘로 덮였다'
    assert '"dateModified": "%s"' % DAY2 in new
    lm = _lastmods(site)
    assert lm[P.urllib.parse.quote('서울')] == DAY2
    assert lm[P.urllib.parse.quote('부산')] == DAY1, '안 바뀐 페이지의 lastmod 가 움직였다'


def _cut_start_one_quarter_before_done(stats):
    """착공을 준공 끝 분기(L)보다 한 분기 앞에서 자른다 — 어느 회차의 데이터든 H = LEAD_Q − 1.

    ⚠️ 자르는 달을 숫자로 박지 않는다. 예전엔 '2026.03' 으로 박아, L 이 2026Q2 인 동안만
       H=11 이었다. 2026.09 준공·착공이 들어와 L=2026Q3 이 되면 같은 자름이 H=10 을 만들어
       픽스처 단정이 빨개지고, 생성기는 다 성공했는데 배치 게이트가 그날 데이터 커밋 전체를
       막는다(2026-09-26 데이터 감사 #0 — 분기마다 되풀이된다).
    """
    L = SZ.last_full_quarter(stats, '준공')
    y, q = SZ.qparts(L - 1)
    cut = '%d.%02d' % (y, q * 3)
    st = stats['착공']
    keep = [i for i, d in enumerate(st['dates']) if d[:7] <= cut]
    st['dates'] = [st['dates'][i] for i in keep]
    st['series'] = {r: [v[i] for i in keep if i < len(v)] for r, v in st['series'].items()}
    return cut


def test_aborts_when_start_series_arrives_a_quarter_late(site, monkeypatch):
    """착공표가 한 분기 늦게 들어온 회차에는 H 가 LEAD_Q − 1 이 되어 전 지역 비율이 함께 움직인다.
    점수(ADV.sido)도 같은 상태로 다시 구웠다면 첫 게이트(L·H 비교)는 통과하므로, H ≠ lead
    게이트가 페이지를 굽기 전에 멈춰야 한다.

    변이: main() 의 `if _live['H'] != _live['lead']:` 를 `if False:` 로 바꾸면 SystemExit 없이
          20장이 구워져 빨개진다(실제로 바꿔 확인, 2026-09-26 자름을 데이터 기준으로 바꾼 뒤에도 확인).
    픽스처: 저장소 STATS 에서 착공만 준공 끝 분기(L)보다 한 분기 앞까지로 자른 것(2026-08-07
            '착공만 늦게 도착'), ADV.sido 는 그 STATS 로 --seed-sido 를 다시 돌린 것처럼 SZ.calc 로
            맞춘다. 자르는 달은 데이터에서 유도하므로 준공·착공이 2026Q3·Q4·2027Q1 로 나아가도
            같은 상태를 만든다(데이터를 한 분기씩 밀어 실제로 확인 — 감사 #0,
            test_gate_survives_next_period 가 그 전진을 매번 돌린다).
    """
    adv, stats = P.load()
    _cut_start_one_quarter_before_done(stats)
    adv['sido'] = SZ.calc(stats)
    assert adv['sido']['H'] == SZ.LEAD_Q - 1, '픽스처가 H ≠ lead 상태를 못 만들었다'
    monkeypatch.setattr(P, 'load', lambda: (adv, stats))
    _set_today(monkeypatch, DAY1)
    with pytest.raises(SystemExit) as e:
        P.main()
    assert 'ABORT' in str(e.value) and ('H=%d' % (SZ.LEAD_Q - 1)) in str(e.value)
    assert not (site / 'zone' / '서울').exists(), 'ABORT 전에 페이지를 썼다'
