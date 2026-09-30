# -*- coding: utf-8 -*-
"""'지난주와 무엇이 달라졌나'(홈 마케팅 검수 B7·RET-5, 2026-09-27) — 방향 표지와 시군구 순위 이동.

재현하는 실제 상태(09-26 라이브): 홈 코어에는 주간 한 주만 실려(split_data `rows[-1:]`) 주간 격자가 그 주 값만 그렸고,
'지난주와 무엇이 달라졌나'를 보여 줄 재료가 없었다. 블로그 초안은 '지난주 순위에서 몇 계단'을 말하는데(홈 TOP 10
캡처) 사이트의 다른 화면은 그 숫자를 몰랐다.

원칙: 표지·순위 이동은 파이썬 정본(tools/weekly_moves.py) 하나가 계산한다. 홈 JS 는 split_data 가 구운 ADV.weekly.moves 를
읽기만 하고, /weekly/ 타일·시군구 전체 표와 블로그 초안은 같은 함수를 부른다. 홈 통계 탭 TOP 10(home-app.js sggRanks)만
같은 순위를 JS 로 계산하므로(블로그가 캡처해 싣는 표) 그 일치를 실데이터로 node 대조한다.

표지 규칙(정본 weekly_moves 머리말): 방향은 **표시값**(pv2r) 부호 — 0.00 은 보합. 연속 3주 이상이면 'N주 연속 상승/하락',
이번 주만 방향이 바뀌었으면(하락·보합 → 상승) '상승 전환'/'하락 전환', 앞 회차 결측이면 전환이라 하지 않는다.

각 시험의 독스트링에 ① 무엇을 깨뜨리면 빨개지는지(실제로 변이를 넣어 확인) ② 픽스처가 재현하는 상태를 적었다.
실데이터는 두 구현의 일치로만 본다(값·날짜를 박지 않는다 — 데이터가 앞으로 가도 초록).
"""
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_naver_post as P  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_moves as WM  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# ── 합성 네 주: 지역마다 규칙의 한 갈래를 재현한다(오래된 주 → 최신 주) ─────────────────────────────
# 경계값은 사이트 반올림(half-up)에서 갈리는 값으로 둔다: 0.004 → '0.00'(보합), 0.005 → '+0.01'(상승), −0.005 → '−0.01'.
CASES = {
    '서울': ([0.05, 0.04, 0.03, 0.02], ('up', '4주 이상 연속 상승')),  # 보관 이력 첫 주까지 이어짐 → '이상'
    '경기': ([-0.02, 0.01, 0.02, 0.03], ('up', '3주 연속 상승')),      # 연속 3주 = 문턱
    '인천': ([-0.02, -0.01, 0.02, 0.03], None),                        # 2주 연속은 새 소식이 아니다
    '부산': ([0.01, 0.02, -0.01, 0.02], ('up', '상승 전환')),          # 하락 → 상승
    '대구': ([0.01, 0.02, 0.004, 0.02], ('up', '상승 전환')),          # 보합(표시 0.00) → 상승
    '대전': ([0.01, 0.02, 0.03, 0.004], None),                         # 이번 주 표시 0.00 = 보합, 원값은 +
    '세종': ([0.01, 0.02, 0.03, 0.005], ('up', '4주 이상 연속 상승')),  # 0.005 → +0.01 표시, 상승이다
    '울산': ([-0.01, -0.02, 0.01, -0.005], ('dn', '하락 전환')),       # −0.005 → −0.01 표시
    '전남광주': ([0.01, 0.01, None, 0.03], None),                       # 앞 회차 결측 → 전환이라 하지 않는다
    '충북': ([None, -0.02, -0.03, -0.04], ('dn', '3주 이상 연속 하락')),  # 첫 값 앞 결측 = 이력 밖 → 첫 값까지 닿아 '이상'
    '충남': ([0.02, 0.0, 0.01, 0.02], None),                           # 보합에서 연속이 끊긴다(2주)
    '제주': ([0.02, 0.03, 0.01, None], None),                          # 이번 주 결측
}
PS = ['2030-01-07', '2030-01-14', '2030-01-21', '2030-01-28']   # 실데이터와 겹치지 않는 먼 월요일


def _fixture():
    regs = list(SZ.DISPLAY_ORDER)
    rows = []
    for k, p in enumerate(PS):
        ma = [CASES[z][0][k] if z in CASES else 0.01 for z in regs]   # 나머지는 4주 연속 상승
        rows.append({'p': p, 'ma': ma, 'je': ma})
    return {'regions': regs, 'rows': rows}


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _wk_block(h):
    m = re.search(r'// <wk-release>[^\n]*\n(.*?)// </wk-release>', h, re.S)
    assert m, 'home-app.js 에서 <wk-release> 구간을 찾지 못했다'
    return m.group(1)


def test_open_streak_reaches_the_first_value_not_an_inner_gap():
    """'이상' 표지는 연속이 그 계열의 **첫 값**까지 닿을 때만 — 첫 값 앞 결측(늦게 생긴 시군구 코드)은 이력 밖이라 '이상',
    첫 값 뒤 결측에서 끊긴 연속은 그 앞에 값이 있었으니 '이상'이 아니다(2026-09-27 D4 검토).

    변이(각각 실제로 확인): opened 를 옛 정의(n == len(vals))로 되돌리면 첫 단정, '앞에 결측이 하나라도 있으면 이상'으로 느슨하게
    하면 둘째 단정이 빨개진다.
    픽스처: 실데이터 모양 — 이름표에 있는 시군구 11곳이 앞 145주 결측(화성 분구 등 새 코드), 그리고 중간 한 주 결측.
    """
    assert WM.tag([None, None, -0.02, -0.03, -0.04]) == ('dn', '3주 이상 연속 하락', 3, 1)
    assert WM.tag([-0.01, None, -0.02, -0.03, -0.04]) == ('dn', '3주 연속 하락', 3, 0)
    assert WM.opened([None] * 145 + [0.1] * 11, 11) == 1 and WM.opened([0.1] + [None] * 144 + [0.1] * 11, 11) == 0
    assert WM.opened([0.1, 0.1], 0) == 0


def test_tag_rule_on_every_branch():
    """표지 규칙의 갈래마다 기대한 표지가 나온다(파이썬 정본).

    변이(각각 실제로 확인): direction 이 표시값 대신 원값 부호를 쓰면(`r = v`) 대전(0.004)·대구·세종에서, STREAK_MIN 을
    2 로 내리면 인천에서, '이상' 판정을 끄면(opened 가 늘 0) 서울에서, '이상'을 보관 이력 전체 길이로만 판정하면(첫 값 앞 결측을
    이력으로 세면) 충북에서,
    전환에서 앞 회차 결측 검사를 빼면 전남광주에서, 보합→상승을 전환에서 빼면(앞 회차가 하락일 때만)
    대구에서 빨개진다.
    픽스처: 합성 네 주 — 지역마다 규칙의 한 갈래(연속 문턱·보합·결측·반올림 경계 0.004/0.005/−0.005).
    """
    W = _fixture()
    mv = WM.moves(W)
    assert mv['p'] == PS[-1] and mv['prev'] == PS[-2]
    for z, (_, want) in CASES.items():
        got = mv['tags'].get(z)
        assert (tuple(got[:2]) if got else None) == want, (z, got, want)
    # 한 줄 요약은 전환한 시도만, 표시 순서대로
    turned = [z for z in SZ.DISPLAY_ORDER if z in CASES and CASES[z][1] and CASES[z][1][1].endswith('전환')]
    assert [z for z, _ in mv['turned']] == turned
    assert mv['line'] == '지난주와 방향이 바뀐 곳: ' + ' · '.join(
        '%s %s' % (z, CASES[z][1][1]) for z in turned)
    assert WM.turned_line([]) == WM.LINE_NONE


def _grid_js(W, seen=None):
    """홈 주간 격자(renderWeeklyGrid)를 가짜 DOM·localStorage 에서 돌려 칸마다 (지역, 매매 표시, 표지, 도움말 주 수),
    머리 줄(지난 방문 이후 — 옛 '방향이 바뀐 곳' 줄이 되살아나면 moves 로 잡힌다), 렌더 뒤 저장된 wk_seen 을 돌려준다."""
    h = HS.home_source()
    names = ('pv2r', 'pv2', 'pvSign', '_syncHolidays', 'weeklyReleaseNow', 'pubDate', 'weeklyHead', 'applyWeeklyStatus',
             'weeklyMoves', 'weeklyShare', 'wkSinceText', 'wkShouldRemember', 'wkSeen', 'wkRemember', 'renderWeeklyGrid',
             'track', 'loadKakao')
    key = re.search(r"^const WK_SEEN_KEY='[^']+';", h, re.M)
    assert key, 'home-app.js 에서 WK_SEEN_KEY 를 찾지 못했다'
    return '\n'.join([_wk_block(h), key.group(0), 'let KAKAO_P=null,KAKAO_FAIL=false;function loadScript(){return Promise.resolve();}']
                     + [_js_func(h, n) for n in names] + [
        'globalThis.ADV={weekly:%s,holidays:[]};' % json.dumps(W, ensure_ascii=False),
        'const LS={};if(%s!==null)LS.wk_seen=%s;' % (json.dumps(seen), json.dumps(seen)),
        'globalThis.localStorage={getItem:k=>k in LS?LS[k]:null,setItem:(k,v)=>{LS[k]=String(v);}};',
        'const box={style:{},innerHTML:"",querySelector:()=>null};',
        'globalThis.document={getElementById:id=>id==="home-weekly-grid"?box:null};',
        'renderWeeklyGrid();',
        # 칸 = 이름 → 매매 → (표지) 뿐이다. 전세 줄(2026-09-28 에 뺐다)이나 다른 줄이 끼면 이 정규식이 칸을 못 읽어 빨개진다.
        'const cells=[...box.innerHTML.matchAll(/<div class="wc[^"]*"([^>]*)><b>([^<]+)<\\/b><span class="wc-ma">([^<]+)<\\/span>'
        '(?:<i class="wc-tag">([^<]+)<\\/i>)?<\\/div>/g)]'
        '.map(m=>[m[2],m[3],m[4]||null,((m[1].match(/title="최근 (\\d+)주/)||[])[1])||null]);',
        'const moves=(box.innerHTML.match(/<p class="wg-moves">([^<]*)<\\/p>/)||[])[1]||null;',
        'const since=(box.innerHTML.match(/<p class="wg-since">([^<]*)<\\/p>/)||[])[1]||null;',
        'process.stdout.write(JSON.stringify({cells,moves,since,seen:LS.wk_seen||null}));'])


def test_home_grid_shows_the_python_tags_and_they_agree_with_the_displayed_sign():
    """홈 주간 격자는 배치가 구운 표지를 그대로 칸에 싣고, 표지의 방향은 그 칸에 찍힌 매매 숫자(JS pv2)의 부호와 같다 —
    JS·파이썬이 같은 결과를 낸다(0.00 칸에는 표지가 없다). 조사일이 다른 옛 표지(섞인 캐시)는 싣지 않는다.

    칸은 지역 이름·매매 값·표지뿐이다 — 전세 값 줄과 격자 위 '지난주와 방향이 바뀐 곳' 줄은 뺐다(2026-09-28 대표 결정 — 작은
    글씨 정리). 표지는 매매 숫자 바로 아래에 /weekly/ 타일과 같은 말('3주 연속 상승' — weekly_moves 문구 그대로)로 붙는다
    (전세 줄과 가르려고 붙였던 '매매' 앞말은 전세 줄과 함께 뺐다). 칸 도움말의 주 수는 배치가 싣는 ADV.weekly.recent 를 따른다
    (JS 에 4 를 적지 않는다).

    변이(각각 실제로 확인): weekly_moves.direction 이 원값 부호를 쓰면 '0.00'(대전)에 '상승' 표지가 붙어, 홈 cell 에서
    표지(`wc-tag`)를 빼면 표지 대조에서, 전세 줄(wc-je)을 되살리면 칸 읽기에서, 표지 앞에 '매매 '를 되살리면 표지 대조에서,
    '방향이 바뀐 곳' 줄(wg-moves)을 되살리면 moves 단정에서, 도움말 창을 slice(-4) 로 적으면 주 수 단정에서, weeklyMoves 의
    조사일 검사(`mv.p===row.p`)를 빼면 옛 표지 단정에서 빨개진다.
    픽스처: 위 합성 네 주 + split_data 가 싣는 모양(ADV.weekly.moves·recent — 창은 일부러 3주로 줄였다). 홈 격자 칸은 19개.
    """
    W = _fixture()
    WJ = dict(W, grace=9, moves=WM.moves(W), recent=3)
    out = _node(_grid_js(WJ))
    cells = {r: (txt, tag) for r, txt, tag, _ in out['cells']}
    assert set(cells) == set(W['regions']), '격자 칸을 다 읽지 못했다(칸에 다른 줄이 끼었나?): %s' % sorted(cells)
    assert {n for _, _, _, n in out['cells']} == {'3'}, '칸 도움말이 배치의 창(recent=3)을 따르지 않는다'
    want = WJ['moves']['tags']
    for r, (txt, tag) in cells.items():
        assert tag == (want[r][1] if r in want else None), (r, tag, want.get(r))
        shown = txt.replace('−', '-')
        if tag:
            assert shown[0] == ('+' if want[r][0] == 'up' else '-'), '표지 %s 인데 칸에는 %s' % (tag, txt)
        if shown in ('0.00', '·'):
            assert tag is None, (r, txt, tag)
    assert out['moves'] is None and 'wg-moves' not in HS.home_source(), "격자 위 '방향이 바뀐 곳' 줄이 되살아났다"
    stale = dict(WJ, moves=dict(WJ['moves'], p=PS[-2]))
    out = _node(_grid_js(stale))
    assert all(t is None for _, _, t, _ in out['cells']) and out['moves'] is None, '조사일이 다른 옛 표지를 실었다'


def test_seen_release_is_only_moved_forward():
    """wk_seen(지난 방문 발표일)은 더 새 발표일로만 바뀐다. 옛 data-core(서비스워커·브라우저 캐시)로 그린 화면이 이미 본 새
    발표일을 옛 날짜로 덮으면 다음 방문에 '새 발표'를 한 번 더 센다(3차 검토).

    변이(각각 실제로 확인): renderWeeklyGrid 가 조건 없이 wkRemember(rel.pub) 를 부르면 첫 단정, wkShouldRemember 가
    `seen<pub` 대신 `seen!==pub` 를 보면 첫 단정, 처음 온 기기(seen 없음)에 적지 않으면 셋째 단정이 빨개진다.
    픽스처: 합성 네 주(최신 조사 2030-01-28 → 발표 01-31)를 그리는 홈 격자와 가짜 localStorage.
    """
    W = _fixture()
    WJ = dict(W, grace=9, moves=WM.moves(W), recent=4)
    later = _node(_grid_js(WJ, seen='2030-02-07'))          # 더 새 발표를 이미 본 기기에 옛 판 화면
    assert later['seen'] == '2030-02-07' and later['since'] is None
    older = _node(_grid_js(WJ, seen='2030-01-24'))
    assert older['seen'] == '2030-01-31' and older['since'] == '지난 방문(1/24 발표) 이후 새 발표 1회'
    first = _node(_grid_js(WJ))
    assert first['seen'] == '2030-01-31' and first['since'] is None


def test_since_last_visit_line():
    """지난 방문 이후 새 발표 수(RET-5 — localStorage 한 키). 처음 온 기기·같은 발표·잘못된 값·미래 값에는 줄이 없다.

    변이(각각 실제로 확인): 주 차이를 일 차이(/7 삭제)로 세면, `seen<r.pub` 검사와 `n>=1` 거름을 함께 빼면(같은 발표에
    '새 발표 0회', 미래 값에 '-1회') 빨개진다. 둘 중 하나만 빼면 남은 쪽이 막아 초록이다(이중 방어).
    픽스처: 발표일 2030-01-31(목) 기준 합성 발표 상태.
    """
    h = HS.home_source()
    js = '\n'.join([_wk_block(h), _js_func(h, 'wkSinceText'),
                    'const r={pub:"2030-01-31"};',
                    'process.stdout.write(JSON.stringify([null,"2030-01-31","2030-01-24","2030-01-10","x","2030-02-07"]'
                    '.map(s=>wkSinceText(s,r))));'])
    assert _node(js) == [None, None, '지난 방문(1/24 발표) 이후 새 발표 1회',
                         '지난 방문(1/10 발표) 이후 새 발표 3회', None, None]


def test_sgg_rank_moves_match_the_home_top10():
    """시군구 순위·이동(weekly_moves.rank_moves — /weekly/ 표·블로그 문장)이 홈 통계 탭 TOP 10(home-app.js sggRanks,
    블로그가 캡처해 싣는 표)과 같다. 매매·전세 둘 다, 실데이터 최신 두 주와 같은 값이 겹친 합성 주로 본다.

    변이(각각 실제로 확인): rank_moves 가 이동을 `rk - prev`(부호 반대)로 내면, sgg_ranks 가 표시값(pv2r)으로 정렬하면
    (같은 +0.05 가 여럿이라 순서가 갈린다) 빨개진다.
    픽스처: 저장소 data.js 의 ADV.weekly.sgg 최신 두 주(값은 두 구현의 일치로만 본다) + 같은 값 세 곳이 겹친 합성 주.
    """
    W, Q = MW.load()
    S = copy.deepcopy(W['sgg'])
    S['rows'] = S['rows'][-2:]
    tie = dict(S['rows'][-1], ma=[round(v, 2) if v is not None else None for v in S['rows'][-1]['ma']])
    h = HS.home_source()
    for label, SS in (('실데이터', S), ('반올림 겹침', dict(S, rows=[S['rows'][0], tie]))):
        for met in ('ma', 'je'):
            js = '\n'.join(['const SGG_QNAME=%s;' % json.dumps(Q, ensure_ascii=False), _js_func(h, 'sggRanks'),
                            'const S=%s;' % json.dumps(SS, ensure_ascii=False),
                            'const cr=sggRanks(S,S.rows[1],"%s"),pr=sggRanks(S,S.rows[0],"%s").rk;' % (met, met),
                            'process.stdout.write(JSON.stringify(cr.order.map(([c])=>[c,cr.rk[c],(c in pr)?pr[c]-cr.rk[c]:null])));'])
            site = _node(js)
            ours = [[c, r, d] for c, _, r, d in WM.rank_moves(SS, Q, met)]
            assert len(ours) > 10 and ours == site, '%s %s: 파이썬 %s… / 홈 %s…' % (label, met, ours[:5], site[:5])


def test_home_core_carries_only_the_moves_fields_the_home_reads():
    """홈 코어(ADV.weekly.moves)에는 홈이 읽는 필드(조사일 p·칸 표지 tags)만 싣는다. '방향이 바뀐 곳' 한 줄(line)·전환 목록
    (turned)·앞 회차(prev)는 홈 격자 머리 줄을 뺀 뒤(2026-09-28 대표 결정 — 작은 글씨 정리) 읽는 곳이 /weekly/ 와 블로그
    초안뿐이고, 둘은 weekly_moves.moves 를 직접 부른다. 홈이 읽는 필드는 홈 스크립트의 `mv.필드` 에서 센다(손 목록과 대조).

    변이(각각 실제로 확인): split_data._home_moves 가 moves 전체를 그대로 싣으면 첫 단정이, 홈 격자에 mv.line 줄을 되살리면
          셋째 단정이 빨개진다.
    픽스처: 위 합성 네 주(전환·연속 표지가 모두 있는 주 — line·turned 가 비지 않는다).
    """
    import split_data as S
    W = _fixture()
    full, home = WM.moves(W), S._home_moves(W)
    assert set(home) == set(S.HOME_MOVES) and all(home[k] == full[k] for k in S.HOME_MOVES), home
    assert full['turned'] and full['line'] != WM.LINE_NONE, '픽스처에 전환이 없으면 뺀 필드를 가리지 못한다'
    h = HS.home_source()
    used = set(re.findall(r'\bmv\.(\w+)', _js_func(h, 'weeklyMoves') + _js_func(h, 'renderWeeklyGrid')))
    assert used == set(S.HOME_MOVES), '홈이 읽는 방향 표지 필드(%s)와 코어에 싣는 필드(%s)가 다르다' % (used, S.HOME_MOVES)


def test_weekly_page_tiles_and_table_use_the_same_moves():
    """/weekly/ 타일 표지·'방향이 바뀐 곳' 한 줄·시군구 전체 표가 weekly_moves 의 결과를 그대로 싣는다.

    변이(각각 실제로 확인): make_weekly_page.build 가 tile 에 표지를 넘기지 않으면 첫 단정, table_html 이 순위 대신 계열 순서
    (codes)로 줄을 세우면 표 단정, move_text 가 부호를 뒤집으면 이동 단정이 빨개진다.
    픽스처: 합성 네 주(시도) + 저장소 data.js 시군구 최신 두 주(표는 두 구현의 일치로만 본다).
    """
    Wr, Q = MW.load()
    W = _fixture()
    W['sgg'] = dict(Wr['sgg'], rows=Wr['sgg']['rows'][-2:])
    W['seoul'] = Wr['seoul']
    W['holidays'] = []
    head = MW.build(W, Q)[0]
    tiles = re.findall(r'<div class="mm-tile"[^>]*><b[^>]*>([^<]+)</b><span[^>]*>[^<]*</span>'
                       r'(?:<i class="mm-tag"[^>]*>([^<]+)</i>)?</div>', head)
    mv = WM.moves(W)
    assert len(tiles) == len([z for z in SZ.DISPLAY_ORDER if W['rows'][-1]['ma'][W['regions'].index(z)] is not None])
    for name, tag in tiles:
        assert (tag or None) == (mv['tags'][name][1] if name in mv['tags'] else None), (name, tag)
    assert '<p class="mm-moves">%s</p>' % mv['line'] in head
    table = MW.table_html(W, Q)
    rows = re.findall(r'<tr><th scope="row">([^<]+)</th><td[^>]*>([^<]+)</td><td[^>]*>[^<]*</td>'
                      r'<td>(\d+)</td><td data-v="(-?\d*)">([^<]+)</td></tr>', table)
    want = WM.rank_moves(W['sgg'], Q)
    mark = lambda d: 'NEW' if d is None else ('▲%d' % d if d > 0 else ('▼%d' % -d if d < 0 else '–'))   # 홈 dcell 모양
    assert [(n, v, int(r), dv, t) for n, v, r, dv, t in rows] == [
        (Q[c], MW.pv2(v), r, '' if d is None else str(d), mark(d)) for c, v, r, d in want]
    assert 'id="utable"' in table and 'data-num' in table
    # RET-7 한 줄은 가는 곳(시도 목록 /zone/)과 같은 말을 한다('이 지역'이라 적지 않는다 — 3차 검토)
    assert '<a href="/zone/">시도별 공급 판정 보기 →</a>' in table and '이 지역' not in table


def test_news_is_only_what_changed_this_week():
    """블로그가 쓰는 '이번 주 새 변화'(weekly_moves.news): 전환, 연속 STREAK_MIN 주에 막 들어선 곳, 연속이 이정표(MILESTONES)에
    막 닿은 곳만. 이정표가 아닌 긴 연속(매주 1씩 느는 85→86주)과 이력 끝까지 닿은 '이상' 연속, 집계는 싣지 않는다
    (CLAUDE.md '회차 간 반복 금지' — 3차 검토).

    변이(각각 실제로 확인): milestone 거름을 빼면(연속 3주 이상 전부) 둘째 단정, '이상' 연속을 빼지 않으면 인천이 들어와
    둘째 단정, entered 가 `>= STREAK_MIN` 을 보면 첫째 단정, 집계를 빼지 않으면 전국이 들어와 빨개진다.
    픽스처: 표지 모양(ADV.weekly.moves.tags)을 손으로 만든 한 주 — 서울 8주(이정표), 경기 9주(이정표 다음 주), 인천
    8주 이상(이력 끝), 부산 3주(새 연속), 대구 4주, 울산 하락 전환, 전국 8주(집계).
    """
    mv = {'tags': {'서울': ['up', '8주 연속 상승', 8, 0], '경기': ['up', '9주 연속 상승', 9, 0],
                   '인천': ['up', '8주 이상 연속 상승', 8, 1], '부산': ['dn', '3주 연속 하락', 3, 0],
                   '대구': ['up', '4주 연속 상승', 4, 0], '울산': ['dn', '하락 전환', 1, 0],
                   '전국': ['up', '8주 연속 상승', 8, 0]}}
    nw = WM.news(mv)
    assert nw['turned'] == [('울산', 'dn')] and nw['entered'] == [('부산', 'dn')]
    assert nw['milestone'] == [('서울', 'up', 8)]
    assert 8 in WM.MILESTONES and 9 not in WM.MILESTONES and 4 not in WM.MILESTONES


def test_blog_draft_says_the_same_moves():
    """블로그 주간 초안은 이번 주 새 변화(weekly_moves.news)와 '순위가 가장 많이 뛴 곳'만 싣고, 사이트와 같은 함수의 값이다.
    매주 되풀이되는 긴 연속('서울 85주 연속 상승' 류)은 싣지 않는다.

    변이(각각 실제로 확인): weekly_moves_sentences 가 전환 지역을 따로 걸러 대구를 빠뜨리면, news 대신 연속 표지 전부를
    문장으로 옮기면(옛 '흐름이 가장 길게 이어진 곳') 빨개진다.
    픽스처: 합성 네 주(시도 — 전환 셋, 새 3주 연속 둘, 4주 '이상' 연속 여럿) + 저장소 시군구 최신 두 주.
    """
    Wr, Q = MW.load()
    W = _fixture()
    W['sgg'] = dict(Wr['sgg'], rows=Wr['sgg']['rows'][-2:])
    para, rank = P.weekly_moves_sentences(W)
    mv = WM.moves(W)
    nw = WM.news(mv)
    assert nw['turned'] and nw['entered'], '픽스처가 전환·새 연속을 담아야 한다'
    for z, k in nw['turned']:
        assert '<b>%s</b>(%s)' % (z, WM.TXT_TURN[k]) in para, (z, para)
    assert '새로 %d주 연속 흐름에 들어선 곳은 %s입니다.' % (WM.STREAK_MIN, ' · '.join(
        '%s(%s)' % (z, '상승' if k == WM.UP else '하락') for z, k in nw['entered'])) in para, para
    assert '이상 연속' not in para and '흐름이 가장 길게' not in para, para
    top = [(Q[c], d) for c, _, r, d in WM.rank_moves(W['sgg'], Q)[:10] if d is not None and d > 0]
    if top:
        name, d = max(top, key=lambda x: x[1])
        assert rank == '<p>상승 TOP 10 가운데 지난주보다 순위가 가장 많이 뛴 곳은 <b>%s</b>(▲%d위)입니다.</p>' % (name, d)
    else:
        assert rank == ''


def test_sort_script_keeps_zero_as_a_number():
    """공용 정렬 스크립트(make_indicator_pages.SORT_SCRIPT — /weekly/ 시군구 표·/moveins/·/jeonse-ratio/)가 0.00 을 값으로,
    data-v 가 있으면 그 값으로 정렬한다. 예전엔 `parseFloat(...)||-1e9` 라 0 이 '값 없음'으로 맨 끝에 섰다.

    변이(각각 실제로 확인): val 을 옛 `(parseFloat(...)||-1e9)` 로 되돌리면 첫 단정, data-v 를 읽지 않으면('▲3' → 3,
    '▼2' → 2) 둘째 단정이 빨개진다.
    픽스처: 칸 흉내(textContent·getAttribute) 여섯 개 — 주간 변동률 +0.12·0.00·−0.05, 이동 ▲3·▼2·NEW.
    """
    import make_indicator_pages as I
    m = re.search(r'  function val\(row,k,isNum\)\{.*?\n  \}', I.SORT_SCRIPT, re.S)
    assert m, 'SORT_SCRIPT 에서 val 을 찾지 못했다'
    js = m.group(0) + r'''
const cell=(t,v)=>({textContent:t,getAttribute:a=>a==='data-v'?(v===undefined?null:v):null});
const row=c=>({cells:[c]});
const a=['+0.12','0.00','-0.05'].map(t=>val(row(cell(t)),0,true));
const b=[['▲3','3'],['▼2','-2'],['NEW','']].map(([t,v])=>val(row(cell(t,v)),0,true));
process.stdout.write(JSON.stringify([a,b]));'''
    a, b = _node(js)
    assert a == [0.12, 0, -0.05], a
    assert b == [3, -2, -1e9], b


def test_cum_window_is_empty_when_the_base_week_was_skipped():
    """12주 누적 창의 기준 주(최신 − CUM_WEEKS 주)가 원천이 거른 주면 그 회차의 누적은 None 이다(전수리뷰 #12).

    거른 주의 변동은 다음 회차 값에 실린다. 기준 주가 없으면 창 첫 행('기준 주 +1주')이 '기준 주 −1주 → +1주' 두 주 치를 싣고
    들어와 누적이 13주(91일)를 덮는데 시도 리포트는 '12주'로 적는다. 창 안에서 거른 주(11행 = 12주)는 그대로 누적한다.
    무엇을 깨뜨리면 빨개지나(실제로 확인): cum_window 의 `if base not in ds: return None` 을 예전 식
    `if not any(d is not None and d <= base for d in ds): return None` 으로 되돌리면 첫 단정이 빨강(12행 91일 창).
    픽스처: 실데이터 2025-01-27·2025-10-06 거른 주의 12주 뒤 회차 모양을 먼 미래(2031년) 날짜로 재현 — 16주 가운데 최신 − 84일
    주 하나를 뺀다. 날짜는 CUM_WEEKS 에서 유도한다.
    """
    import datetime
    d0 = datetime.date(2031, 1, 6)
    ps = [(d0 + datetime.timedelta(days=7 * k)).isoformat() for k in range(WM.CUM_WEEKS + 4)]
    last = datetime.date.fromisoformat(ps[-1])
    base = (last - datetime.timedelta(days=7 * WM.CUM_WEEKS)).isoformat()
    rows = [{'p': p, 'ma': [1.0]} for p in ps if p != base]
    win = WM.cum_window(rows)
    assert win is None, '기준 주가 거른 주인데 %d행 창을 돌려줬다(%s 부터)' % (len(win), rows[win[0] - 1]['p'])
    # 한 주 뒤 회차(기준 주가 있는 평소 회차)는 12주 창이 돌아온다 — 거른 주는 기준 주 바로 앞이라 창 밖, 12행
    nxt = (last + datetime.timedelta(days=7)).isoformat()
    rows.append({'p': nxt, 'ma': [1.0]})
    win = WM.cum_window(rows)
    assert win is not None and len(win) == WM.CUM_WEEKS
    assert rows[win[0] - 1]['p'] == (datetime.date.fromisoformat(nxt) - datetime.timedelta(days=7 * WM.CUM_WEEKS)).isoformat()
