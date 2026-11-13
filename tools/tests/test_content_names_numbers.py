# -*- coding: utf-8 -*-
"""콘텐츠 자리표의 이름 풀기·숫자 표기 — 2026-11-13 전수 리뷰에서 확인한 것.

한 글 안에서 같은 이름이 자리표마다 다른 곳으로 풀리거나(광주), 사이트의 다른 화면과 다른 셈을 하거나(연속 주수),
수준 값에 변동률 부호가 붙거나(전세가율), 꼴이 어긋난 자리표가 글자 그대로 발행되던 자리를 고정한다.
"""
import io
import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import content_check as CC          # noqa: E402
import content_md as CM             # noqa: E402
import content_tables as CT         # noqa: E402
import make_city_moveins as MCM     # noqa: E402
import make_content_pages as MC     # noqa: E402
import sido_zones as SZ             # noqa: E402
import weekly_moves as WM           # noqa: E402

REAL = os.path.join(ROOT, 'content', 'city', 'suwon-2027-moveins.md')


@pytest.fixture(scope='module')
def data():
    return CT.load()


def _wk(vals, name='서울'):
    """시도 한 곳의 주간 매매 계열만 든 최소 데이터(오래된 주 → 최신 주)."""
    return {'weekly': {'regions': [name],
                       'rows': [{'p': '2026-%02d-%02d' % (1 + i // 4, 1 + 7 * (i % 4)), 'ma': [v]} for i, v in enumerate(vals)]}}


def test_gwangju_and_jeonnam_cities_fold_into_the_merged_zone():
    """광주·전남의 도시는 판정 단위 키(전남광주)로 접힌다 — 원천 시도 이름('전남'·'광주')이 그대로 나오지 않는다.

    왜: sido_of 가 접두 표의 원천 이름을 돌려줘 sido_zones.ORDER 에 없는 키가 됐다. 그 글은 '지역 공급 리포트' 링크와
        /zone/전남광주/ 의 글 묶음에서 빠지고 허브 지역 칩이 '광주'·'전남' 두 줄로 갈린다(첫 광주·전남 원고에서 드러날 결함).
    변이(실제로 확인): sido_of 를 `SZ.key_of(WM.SGG_PREFIX[...])` 로 되돌리면 '전남'·'광주'가 나와 빨개진다.
    픽스처: 홈의 실제 시군구 이름표 — 광주·전남에 든 모든 이름을 데이터에서 골라 돈다(이름을 박지 않는다).
    """
    import merge_regions as MR
    names = MCM.sgg_names()
    folded = [n for c, n in names.items() if WM.sgg_sido(c) in MR.SRC]
    assert len(folded) >= 2, '이름표에 광주·전남 시군구가 없다 — 픽스처가 비었다'
    for n in folded:
        city = n.split(' ')[0]
        assert MCM.sido_of(city, names) == MR.DST, (n, MCM.sido_of(city, names))
        assert MC.zone_of({'region': city}) == MR.DST, n
    for c, n in names.items():                       # 다른 곳은 그대로 판정 단위다
        z = MCM.sido_of(n, names)
        assert z is None or z in SZ.ORDER, (n, z)


def test_a_city_name_wins_over_a_district_tail():
    """'광주'는 광주광역시의 구들이다(시 이름 앞말) — 끝말이 같은 '경기 광주' 한 곳으로 풀리지 않는다.

    왜: 같은 이름이 입주물량 자리표·수집에서는 광주광역시인데 시세 자리표에서는 경기 광주시라, 한 글 안에서 입주는 광역시,
        시세는 경기 광주시가 됐다.
    변이(실제로 확인): sgg_codes 에서 끝말(tail) 갈래를 앞말(pre) 갈래보다 먼저 돌려주게 되돌리면 빨개진다.
    픽스처: 앞말과 끝말이 겹치는 이름('광주')이 든 합성 이름표 + 실제 이름표.
    """
    q = {'x1': '경기 광주', 'b1': '광주 북구', 'b2': '광주 남구', 'a1': '성남 분당구', 'a2': '성남 수정구', 'k1': '남양주'}
    d = {'sgg_names': q}
    assert CT.sgg_codes(d, '광주') == [('b2', '광주 남구'), ('b1', '광주 북구')]
    assert CT.sgg_codes(d, '경기 광주') == [('x1', '경기 광주')]
    assert CT.sgg_codes(d, '분당구') == [('a1', '성남 분당구')]
    assert [n for _c, n in CT.sgg_codes(d, '성남')] == ['성남 분당구', '성남 수정구']
    assert CT.sgg_codes(d, '남양주') == [('k1', '남양주')] and CT.sgg_codes(d, '없는곳') == []
    real = CT.load()
    got = CT.sgg_codes(real, '광주')
    assert got and all(n.startswith('광주 ') for _c, n in got), got


def test_level_values_carry_no_sign(data):
    """전세가율은 수준이다 — 표 칸과 값 자리표에 '+' 가 붙지 않는다.

    변이(실제로 확인): content_tables.stats 가 level 대신 pct(v, 1) 을 쓰면 '+52.3%' 가 나와 빨개진다.
    픽스처: 저장소의 실제 전세가율 계열(모든 판정 단위).
    """
    regs = [z for z in SZ.ORDER if z in (data['stats'].get('전세가율', {}).get('series') or {})]
    assert regs, '전세가율 계열이 없다'
    for z in regs:
        v = CT.value(data, 'stats', ['전세가율', z])
        assert v[0].isdigit() and v.endswith('%'), (z, v)
        _h, rows, _n = CT.table(data, 'stats', ['전세가율', z])
        assert all(r[1][0].isdigit() for r in rows), (z, rows[:2])
    assert CT.level(52.34) == '52.3' and CT.level(0.04) == '0.0' and CT.level(-0.04) == '0.0'


def test_streak_counts_like_the_weekly_canon(data):
    """연속 주수는 주간 정본(weekly_moves.streak·opened)의 셈이다 — 이력 첫 주까지 닿으면 '이상'을 붙인다.

    왜: 자리표가 따로 세어 '156주 연속 하락'이라고 잘라 말했다. /weekly/ 표와 시도 리포트는 같은 지역을 '156주 이상'이라 한다.
    변이(실제로 확인): streak 의 `' 이상' if WM.opened(...)` 를 빈 글자로 바꾸면 첫 단정이, 결측 주를 걸러 세게 되돌리면
          셋째 단정이 빨개진다.
    픽스처: 합성 계열 넷(끝까지 닿음·중간에 끊김·가운데 결측·보합)과 저장소의 실제 시도 주간 계열 전부.
    """
    assert CT.streak(_wk([0.1, 0.1, 0.1, 0.1, 0.1]), '서울').startswith('5주 이상 연속 상승(')
    assert CT.streak(_wk([-0.1, 0.1, 0.1, 0.1, 0.1]), '서울').startswith('4주 연속 상승(')
    assert CT.streak(_wk([0.1, None, 0.1, 0.1]), '서울').startswith('2주 연속 상승(')      # 결측 주에서 끊긴다(정본과 같다)
    assert CT.streak(_wk([0.1, 0.1, 0.001]), '서울').startswith('보합(')
    assert CT.streak(_wk([0.1, -0.1, -0.1]), '서울').startswith('2주 연속 하락(')
    W = data['weekly']
    for i, z in enumerate(W['regions']):
        if z not in SZ.ORDER:
            continue
        vals = [(r.get('ma') or [None] * len(W['regions']))[i] for r in W['rows']]
        while vals and vals[-1] is None:
            vals.pop()
        s = WM.streak(vals)
        got = CT.streak(data, z)
        want = '보합(' if not s else '%d주%s 연속 %s(' % (abs(s), ' 이상' if WM.opened(vals, abs(s)) else '',
                                                    '상승' if s > 0 else '하락')
        assert got.startswith(want), (z, got, want)


def test_misshapen_placeholders_are_not_published(data):
    """꼴이 어긋난 자리표는 글자 그대로 나가지 않고 TableError 다 — 한 줄 글·본문 둘 다.

    왜: '{{ v:need:수원 }}'·'{{value:…}}'·'{{V:…}}'·닫는 괄호 하나는 자리표 정규식에 걸리지 않아 그대로 발행됐다. 검사기와 게이트
        시험이 같은 정규식을 써서 아무도 잡지 못했다.
    변이(실제로 확인): fill_inline 에서 no_leftover 를 걷으면 첫 묶음이, fill_placeholders 에서 걷으면 둘째 묶음이 빨개진다.
    픽스처: 실제 작성 실수 네 꼴.
    """
    bad = ('앞 {{ v:need:수원 }} 뒤', '앞 {{value:need:수원}} 뒤', '앞 {{V:need:수원}} 뒤', '앞 {{v:need:수원} 뒤')
    for t in bad:
        with pytest.raises(CT.TableError):
            CT.fill_inline(t, data)
        with pytest.raises(CT.TableError):
            MC.fill_placeholders(t, data)
        with pytest.raises(CT.TableError):
            CT.fill_markdown(t, data)
    assert '{{' not in CT.fill_inline('수원의 한 해 적정물량은 {{v:need:수원}}입니다', data)


def test_front_matter_scalars_keep_inner_quotes_and_real_dates(tmp_path):
    """따옴표로 시작하고 끝나는 제목은 안쪽에 같은 따옴표가 있으면 벗기지 않고, 달력에 없는 날짜는 ContentError 다.

    변이(실제로 확인): _scalar 의 `v[0] not in v[1:-1]` 조건을 지우면 첫 단정이, validate 의 달력 검사를 지우면 끝 단정이 빨개진다.
    픽스처: 발언 검증 글의 제목 꼴('"…"는 말, 숫자는 "…"'), 실제 수원 원고의 date 를 없는 날로 바꾼 판.
    """
    assert CM._scalar('"집값 떨어진다"는 말, 숫자는 "아니다"') == '"집값 떨어진다"는 말, 숫자는 "아니다"'
    assert CM._scalar('"{{v:share:인천:2027}}"') == '{{v:share:인천:2027}}'
    assert CM._scalar("'한 줄'") == '한 줄' and CM._scalar('그냥 글') == '그냥 글'
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True)
    text = io.open(REAL, encoding='utf-8').read()
    line = next(ln for ln in text.split('\n') if ln.startswith('updated:'))
    p = d / os.path.basename(REAL)
    p.write_text(text.replace(line, 'updated: 2026-13-45', 1), encoding='utf-8')
    with pytest.raises(CM.ContentError) as e:
        CM.read(str(p))
    assert '달력에 없는' in str(e.value)


def test_attribute_quotes_are_escaped_in_images_and_links():
    """그림 대체글·링크 주소의 큰따옴표는 속성 안에서 &quot; 다 — 본문 글자의 따옴표는 그대로다.

    변이(실제로 확인): _inline 의 q(...) 를 걷으면 alt 속성이 가운데서 끊겨 빨개진다.
    픽스처: 발언을 따옴표로 옮긴 대체글(발언 검증 글에서 나올 꼴).
    """
    h = MC._inline('![그는 "오른다"고 했다](img/a.png) 그리고 "본문"')
    assert 'alt="그는 &quot;오른다&quot;고 했다"' in h and h.count('<img ') == 1, h
    assert '그리고 "본문"' in h
    assert MC._inline('[글](/city/a/)') == '<a href="/city/a/">글</a>'


def test_old_format_reads_get_the_same_shapes(tmp_path):
    """옛 양식(lenient)으로 읽어도 key 는 dict, city 는 목록이다 — 엄격 읽기와 같은 모양.

    왜: 옛 양식 경로는 모양을 고르지 않아 key 가 한 짝 목록인 채 자리표가 채워지지 않았고, `city: 수원` 한 줄은 글자 하나씩
        ('수','원') 도시로 읽혔다.
    변이(실제로 확인): validate 의 `shape_v2(meta)` 줄을 지우면 빨개진다.
    픽스처: 실제 수원 원고에서 audience 줄을 지워 옛 양식으로 떨어지게 하고 city 를 한 줄 값으로 바꾼 판.
    """
    text = io.open(REAL, encoding='utf-8').read()
    lines = text.split('\n')
    i = next(k for k, ln in enumerate(lines) if ln.startswith('city:'))
    j = next(k for k in range(i + 1, len(lines)) if not lines[k].startswith(' '))
    lines[i:j] = ['city: 수원']
    lines = [ln for ln in lines if not ln.startswith('audience:')]
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True)
    p = d / os.path.basename(REAL)
    p.write_text('\n'.join(lines), encoding='utf-8')
    with pytest.raises(CM.ContentError):
        CM.read(str(p))                                   # 엄격 읽기는 옛 양식이라 거부한다(픽스처 확인)
    meta, _body = CM.read(str(p), lenient=True)
    assert isinstance(meta['key'], dict) and meta['key'].get('value'), meta.get('key')
    assert meta['city'] == ['수원']


def test_only_a_plain_city_name_is_collectable(data, monkeypatch, tmp_path):
    """도시 자료는 시 이름 하나만 받는다 — 구 이름·구분 앞말이 붙은 이름은 '기다림'이 아니라 고칠 곳이고, 수집도 그 이름만 건너뛴다.

    왜: '성남 분당구'·'경기 광주'를 도시 자리표에 쓰면 검사기는 '기다리면 들어온다'고 했고, 수집은 인구 행을 못 찾아 KeyError 로
        끝나 **모든 도시**의 갱신이 멈췄다.
    변이(실제로 확인): collectable 의 `' ' not in city` 조건을 지우면 첫 묶음이, build 의 try/except 를 걷으면 끝 묶음이 빨개진다.
    픽스처: 실제 이름표에서 고른 구 이름 하나와 아직 받지 않은 시 이름 하나(데이터에서 고른다), 한 도시만 굽다 죽는 수집.
    """
    names = MCM.sgg_names()
    gu = next(n for n in names.values() if ' ' in n and MCM.sido_of(n, names))
    have = (data.get('cities') or {}).get('cities') or {}
    fresh = next(n for n in names.values() if ' ' not in n and MCM.sido_of(n, names) and n not in have)
    assert not MCM.collectable(gu, names) and MCM.collectable(fresh, names)
    with pytest.raises(CT.TableError) as e:
        CT.value(data, 'need', [gu])
    assert not isinstance(e.value, CT.Pending), '구 이름이 기다림으로 떨어진다 — 수집기는 그 이름을 영영 받지 못한다'
    with pytest.raises(CT.PendingCity):
        CT.value(data, 'need', [fresh])

    def facts(city, sido, start):
        if city == '나':
            raise KeyError(city)
        return {'city': city, 'new': True}

    out = tmp_path / 'city_moveins.json'
    out.write_text('{"start": "2026-11", "cities": {"나": {"city": "나", "old": true}}}', encoding='utf-8')
    monkeypatch.setattr(MCM, 'OUT', str(out))
    monkeypatch.setattr(MCM, 'city_facts', facts)
    got = MCM.build({'가': '경기', '나': '경기', '다': '경기'}, '2026-11')['cities']
    assert got == {'가': {'city': '가', 'new': True}, '나': {'city': '나', 'old': True}, '다': {'city': '다', 'new': True}}


def test_check_counts_a_pending_summary_as_waiting(tmp_path, data):
    """요약의 '아직 안 들어온 자료' 자리표는 본문과 같이 기다림(…)이다 — 고칠 곳(✗)이 아니다.

    변이(실제로 확인): content_check 의 summary·title 갈래에서 `except CT.Pending` 을 지우면 ✗ 로 세어 빨개진다.
    픽스처: 실제 수원 원고의 요약 끝에 아직 받지 않은 시(데이터에서 고른다)의 자리표를 붙인 판.
    """
    names = MCM.sgg_names()
    have = (data.get('cities') or {}).get('cities') or {}
    fresh = next(n for n in names.values() if ' ' not in n and MCM.sido_of(n, names) and n not in have)
    text = io.open(REAL, encoding='utf-8').read()
    line = next(ln for ln in text.split('\n') if ln.startswith('summary:'))
    d = tmp_path / 'content' / 'city'
    d.mkdir(parents=True)
    p = d / os.path.basename(REAL)
    p.write_text(text.replace(line, line.rstrip() + ' {{v:need:%s}}' % fresh, 1), encoding='utf-8')
    probs, waits, _rel = CC.check_post(str(p), data, root=str(tmp_path))
    assert not probs, probs
    assert any('summary' in why and fresh in why for _ln, why in waits), waits


def test_the_batch_keeps_a_city_published_after_its_fetch_started(tmp_path):
    """커밋 잡은 수집 잡이 받아 온 도시 자료를 **도시 단위로** 합친다 — 수집 뒤에 발행된 새 도시를 지우지 않는다.

    왜: 수집 잡은 그 잡이 시작한 때의 원고에 있던 도시만 받는다. 그 사이 새 도시 원고가 병합되면 발행 워크플로가 그 도시를
        저장소 파일에 더하는데, 커밋 잡이 받아 온 파일을 통째로 덮어써 그 도시가 사라졌다 — 방금 발행된 글이 다음 배치까지
        목록에서 빠진다.
    변이(실제로 확인): adopt 에서 `fresh['cities'][c] = have[c]` 줄을 지우면 새 도시가 빠져 빨개진다. 워크플로의 `--adopt` 줄을
          예전 `cp` 로 되돌리면 끝 단정이 빨개진다.
    픽스처: 저장소 파일에 도시 셋(가·나·새), 받아 온 파일에 둘(가·나 — 값이 새것). 원고는 가·새를 쓴다(나는 원고에서 빠졌다).
    """
    out = tmp_path / 'tools' / 'data' / 'city_moveins.json'
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps({'start': '2026-11', 'cities': {'가': {'n': 1}, '나': {'n': 1}, '새': {'n': 7}}}), encoding='utf-8')
    fresh = tmp_path / 'fresh.json'
    fresh.write_text(json.dumps({'start': '2026-11', 'source': 's', 'cities': {'가': {'n': 2}, '나': {'n': 2}}}), encoding='utf-8')
    n, kept = MCM.adopt(str(fresh), out=str(out), wanted={'가': '경기', '새': '경기'})
    got = json.loads(out.read_text(encoding='utf-8'))
    assert (n, kept) == (3, ['새'])
    assert got['cities'] == {'가': {'n': 2}, '나': {'n': 2}, '새': {'n': 7}}, got      # 받은 값이 이기고, 새 도시는 지킨다
    # 원고가 더는 쓰지 않는 도시는 받아 온 파일을 따라 빠진다
    out.write_text(json.dumps({'cities': {'가': {'n': 1}, '옛': {'n': 9}}}), encoding='utf-8')
    MCM.adopt(str(fresh), out=str(out), wanted={'가': '경기'})
    assert '옛' not in json.loads(out.read_text(encoding='utf-8'))['cities']
    # 받아 온 파일이 깨졌으면 저장소 파일을 건드리지 않는다
    fresh.write_text('{깨짐', encoding='utf-8')
    before = out.read_text(encoding='utf-8')
    assert MCM.adopt(str(fresh), out=str(out), wanted={}) is None and out.read_text(encoding='utf-8') == before
    wf = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    code = '\n'.join(ln for ln in wf.splitlines() if not ln.lstrip().startswith('#'))
    assert 'make_city_moveins.py --adopt "$SRC/tools/data/city_moveins.json"' in code, '커밋 잡이 도시 자료를 통째로 덮는다'
