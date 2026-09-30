# -*- coding: utf-8 -*-
"""지표 페이지(/jeonse-ratio/·/moveins/)와 손 페이지 lastmod 의 전수 리뷰 수정(#16·#18·#20·#22·#23)을 고정한다.

각 시험 독스트링에 무엇을 깨뜨리면 빨개지는지(실제로 확인)와 픽스처가 재현하는 실제 상태를 적었다.
"""
import copy
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_sido_pages as P  # noqa: E402
import sido_zones as SZ  # noqa: E402

NEED = list(I.JEONSE_NEED) + ['수도권', '지방']


def _jeonse(cur, ago, ym='2026.05'):
    """전남광주만 cur(기준월)·ago(12개월 전)이고 나머지는 70.0 인 14개월 전세가율 계열."""
    y, m = int(ym[:4]), int(ym[5:])
    t = y * 12 + m - 1
    dates = ['%d.%02d' % ((t - k) // 12, (t - k) % 12 + 1) for k in range(13, -1, -1)]
    ser = {r: [70.0] * len(dates) for r in NEED}
    ser['전남광주'] = [ago] * len(dates)
    ser['전남광주'][-1] = cur
    return {'전세가율': {'dates': dates, 'series': ser}}


def _row(html, name):
    m = re.search(r'<tr><td>%s</td><td>([\d.]+)%%</td><td>([\d.]+)%%</td><td class="(\w+)">([^<]+)</td></tr>' % name, html)
    assert m, '%s 행을 못 찾았다' % name
    return float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)


def test_jeonse_change_is_the_difference_of_the_shown_values():
    """변화 칸 = 같은 줄에 찍힌 두 값의 차이고, 시도 리포트 카드도 같은 값·같은 부호(#16).

    재현하는 실제 상태: 전남광주(광주·전남 가중평균, 소수 둘째 자리) 2026.05 는 78.72 · 77.16 → 표 '78.7% | 77.2% | +1.6%p'
    (차 1.5), 2024.02 는 76.04 · 76.06 → /jeonse-ratio/ '-0.0%p' · 리포트 카드 '+0.0%p'.
    변이(실제로 확인): jeonse_delta 를 round(cur - ago, 1) 로 되돌리면 +1.6 이 나와 빨개진다. '+ 0.0' 을 빼면 '-0.0%p' 가
          나와 빨개진다. make_sido_pages.next_links 를 옛 식으로 되돌리면 카드 단정이 빨개진다.
    """
    for cur, ago in ((78.72, 77.16), (76.04, 76.06)):
        sts = _jeonse(cur, ago)
        html, _ = I.build_jeonse(sts)
        a, b, cls, cell = _row(html, '전남광주')
        want = round(a - b, 1) + 0.0
        assert cell == '%+.1f%%p' % want, (cur, ago, cell)
        assert not cell.startswith('-0.0'), cell
        assert cls == ('up' if want > 0 else 'dn' if want < 0 else 'mut')
        card = P.next_links('전남광주', None, sts)
        assert '1년 전 대비 %+.1f%%p' % want in card, card


def _publish(tmp_path, html, lm):
    fp = str(tmp_path / 'index.html')
    new, got, _ = P.keep_dates(html, P.read_old(fp), lm)
    io.open(fp, 'w', encoding='utf-8').write(new)
    return got, new


def test_indicator_date_is_the_day_the_content_changed(tmp_path):
    """/moveins/ dateModified·lastmod 는 내용이 바뀐 날(KST 오늘)이고, 날짜만 다른 재생성은 옛 판·옛 날짜를 둔다(#18).

    재현하는 실제 상태: 예전엔 데이터 기준월 1일(2026Q2 → '2026-06-01', 공개일 하한에 눌려 '2026-07-29')을 적어, 본문이 바뀐
    09-26·27 배치에도 lastmod 가 07-29 에 묶였고, /jeonse-ratio/ 는 09-28 에 '2026-08-01'(58일 전)로 올라갔다.
    변이(실제로 확인): build_moveins 가 today 대신 옛 mod_iso 를 넘기면 첫 단정이 빨개진다. (main 의 keep_dates 호출은 이
          시험이 부르지 않는다 — 아래 test_indicator_main_keeps_dates_across_same_content_runs 가 main 을 직접 돌려 본다.
          통합 검토에서 이 줄의 옛 설명 'main 에서 keep_dates 를 빼면 빨개진다'가 실제로는 초록임이 드러났다.)
    픽스처: 저장소 ADV.occupancy 로 세 번 굽는다 — 가짜 오늘 2031-03-03(처음) · 03-04(내용 같음) · 03-05(실적 한 칸이 바뀜).
    """
    adv, _ = P.load()
    html, lm = I.build_moveins(adv, '2031-03-03')
    got, page = _publish(tmp_path, html, lm)
    assert got == '2031-03-03' and P.ld_date(page) == '2031-03-03' and P.ld_date(page, 'datePublished') == I.PUBLISHED
    html, lm = I.build_moveins(adv, '2031-03-04')
    got, page = _publish(tmp_path, html, lm)
    assert got == '2031-03-03' and P.ld_date(page) == '2031-03-03', '내용이 같은데 날짜가 움직였다'
    a = copy.deepcopy(adv)
    row = [r for r in a['occupancy']['rows'] if not r.get('e')][-1]
    row['v'] = [None if v is None else v + 1000 for v in row['v']]
    html, lm = I.build_moveins(a, '2031-03-05')
    got, page = _publish(tmp_path, html, lm)
    assert got == '2031-03-05' and P.ld_date(page) == '2031-03-05'
    assert P.ld_date(page, 'datePublished') == I.PUBLISHED


def test_moveins_keeps_the_data_basis_on_screen():
    """dateModified 가 수정일이 된 뒤에도 화면에 데이터 시점('YYYY년 N분기까지 준공 실적')이 있다 — 감시(check_freshness)가
    /moveins/ 시점을 대조할 표지다(F 묶음이 dateModified 대신 이 문구를 읽는다)."""
    adv, _ = P.load()
    html, _ = I.build_moveins(adv, '2031-03-03')
    last = [r['p'] for r in adv['occupancy']['rows'] if not r.get('e')][-1]
    assert '%s년 %s분기까지 준공 실적' % (last[:4], last[5:]) in html


def _smallest_ref_region(adv):
    ref = adv['occupancy']['ref']
    return min((z for z in I.SIDO17 if ref.get(z)), key=lambda z: ref[z])


def test_moveins_sentence_rounds_like_the_table():
    """해설 문장의 충족률과 표 칸의 충족률이 같은 반올림(half-up)이다(#23).

    재현하는 실제 상태: 문장은 파이썬 round()(은행가)라 충족률이 정확히 x.5 면 표 '1% 충족' · 문장 '세종(0% 충족)'.
    적정량이 작은 세종(연 2,400)·제주(4,800)는 실적만으로 찬 해에 약 2% 확률로 이 경계에 닿는다.
    변이(실제로 확인): lo1p 를 round(lo1[1]) 로 되돌리면 빨개진다.
    픽스처: 저장소 ADV.occupancy 에서 적정량이 가장 작은 시도의 머리 해(Y) 합을 적정량의 0.5% 로 만든다(지역·연도를 박지 않는다).
    """
    adv, _ = P.load()
    a = copy.deepcopy(adv)
    o = a['occupancy']
    z = _smallest_ref_region(a)
    i = o['regions'].index(z)
    rf = o['ref'][z] * 4
    Y = str(int([r['p'] for r in o['rows'] if not r.get('e')][-1][:4]))
    ys = [r for r in o['rows'] if r['p'].startswith(Y)]
    for r in ys:
        r['v'][i] = 0
    ys[0]['v'][i] = rf / 200.0
    assert ys[0]['v'][i] / rf * 100 == 0.5, '픽스처가 정확히 0.5% 를 못 만들었다'
    html, _ = I.build_moveins(a)
    cell = re.search(r'<tr><td>%s</td>(?:<td>[^<]*</td>){4}<td class="\w+">(\d+)%% 충족</td></tr>' % z, html)
    sent = re.search(r'가장 덜 채운 곳은 <strong>%s\((\d+)%% 충족\)</strong>' % z, html)
    assert cell and sent, '표 행이나 문장을 못 찾았다'
    assert cell.group(1) == sent.group(1) == '1', (cell.group(1), sent.group(1))


def test_moveins_note_follows_model_constants(monkeypatch):
    """표 아래 주석·해설의 추정 지역·연수·문턱은 모델 상수에서 나온다(#20, 대표 결정 ③).

    재현하는 실제 상태: '서울·경기·인천과 세종·제주는 추정치', '착공 실적을 3년 뒤로 밀어', '지난 4년 쌓인 부족과 앞으로 3년',
    '70%를 밑돌면 … 130%를 넘으면'이 손 리터럴이라, SZ.EST·LEAD_Q·BACKLOG_WINDOW 를 바꿔도 문장이 그대로 남았다.
    변이(실제로 확인): 주석을 옛 리터럴로 되돌리면 바꾼 상수 단정이 빨개진다.
    픽스처: 저장소 ADV.occupancy + 상수만 바꾼 모델(LEAD_Q 16, 창 20, 추정 지역 서울·경기, 문턱 65/140).
    """
    adv, _ = P.load()
    base, _ = I.build_moveins(adv)
    assert '서울·경기·인천과 세종·제주는 추정치' in base
    monkeypatch.setattr(SZ, 'LEAD_Q', 16)
    monkeypatch.setattr(SZ, 'BACKLOG_WINDOW', 20)
    monkeypatch.setattr(SZ, 'EST', {'서울', '경기'})
    monkeypatch.setattr(SZ, 'OCC_LO_PCT', 65)
    monkeypatch.setattr(SZ, 'OCC_HI_PCT', 140)
    html, _ = I.build_moveins(adv)
    assert '착공 실적을 4년 뒤로 밀어' in html and '4년 뒤 준공' in html and '3년 뒤' not in html
    assert '지난 5년 쌓인 부족과 앞으로 4년' in html
    assert '서울·경기는 추정치' in html and '세종' not in re.search(r'[^.]*추정치', html).group(0)
    assert '65%를 밑돌면' in html and '140%를 넘으면' in html


def _git(cwd, *a, **env):
    e = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')
    e.update(env)
    subprocess.run(['git'] + list(a), cwd=cwd, check=True, capture_output=True, env=e)


def test_hand_page_lastmod_is_the_kst_day(tmp_path):
    """손 페이지 sitemap lastmod 는 커밋 시각의 KST 날짜다(#22).

    재현하는 실제 상태: faq/index.html 의 마지막 커밋 812a17d 는 2026-09-27 18:09:19 +0000(KST 09-28 03:09)인데 '%cs'(커미터
    시간대 날짜)로 읽어 lastmod 가 09-27 로 나갔다. 다른 생성기(/zone/·/monthly/·/cycle/)는 KST 날짜를 찍는다.
    변이(실제로 확인): hand_lastmods 를 '%cs' 로 되돌리면 '2026-09-27' 이 나와 빨개진다.
    """
    _git(str(tmp_path), 'init', '-q')
    (tmp_path / 'faq').mkdir()
    (tmp_path / 'faq' / 'index.html').write_text('faq', encoding='utf-8')
    _git(str(tmp_path), 'add', '.')
    when = '2026-09-27T18:09:19+0000'
    _git(str(tmp_path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'faq', '--date', when,
         GIT_COMMITTER_DATE=when)
    assert dict(I.hand_lastmods(str(tmp_path)))['/faq/'] == '2026-09-28'


def test_indicator_main_keeps_dates_across_same_content_runs(tmp_path, monkeypatch):
    """make_indicator_pages.main() 을 가짜 오늘 두 날로 돌리면, 내용이 같은 둘째 날에도 /jeonse-ratio/·/moveins/ 의
    dateModified 와 sitemap lastmod 는 첫날에 머문다(#18 — main 이 keep_dates 로 옛 판을 둔다).

    변이(실제로 확인): main 의 `html, lm, _ = SP.keep_dates(...)` 줄을 지우면 둘째 날 날짜가 03-04 로 움직여 빨개진다.
    픽스처: 저장소 data.js·data-rest.json·sitemap.xml·app.css 사본을 tmp ROOT 에 두고 손 페이지 lastmod(git 이력)는 뺀다.
    """
    import shutil
    for f in ('data.js', 'data-rest.json', 'sitemap.xml', 'app.css'):   # 생성기가 ROOT 에서 읽는 파일 전부
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', f), str(tmp_path / f))
    monkeypatch.setattr(I, 'ROOT', str(tmp_path))
    monkeypatch.setattr(I, 'hand_lastmods', lambda root=None: [])
    got = {}
    for day in ('2031-03-03', '2031-03-04'):
        monkeypatch.setattr(I.KST, 'today_iso', lambda d=day: d)
        I.main()
        sm = io.open(str(tmp_path / 'sitemap.xml'), encoding='utf-8').read()
        for sub in ('jeonse-ratio', 'moveins'):
            page = io.open(str(tmp_path / sub / 'index.html'), encoding='utf-8').read()
            lm = re.search(r'<loc>[^<]*/%s/</loc>\s*<lastmod>([^<]*)</lastmod>' % sub, sm).group(1)
            got.setdefault(sub, []).append((P.ld_date(page), lm))
    for sub, (first, second) in got.items():
        assert first == ('2031-03-03', '2031-03-03'), (sub, first)
        assert second == first, '%s: 내용이 같은데 날짜가 %s 로 움직였다' % (sub, second)
