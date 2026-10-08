# -*- coding: utf-8 -*-
"""홈 모드 단추(공급 현황·주간 시세·월간 시세)의 '새 데이터' N 배지(2026-10-08 대표 요청, B안).

규칙: 모드마다 최신 시점이 이 사이트에 처음 실린 날(KST)부터 ADV.fresh.days[모드] 일 동안(그날 포함 — 주간 4·월간 7·공급 14,
같은 날 대표 결정) 배지를 단다. 처음 FRESH_FORCE 일(그날과 다음 날)은 눌렀어도 단다. 방문자가 그 단추를
누르면(켜져 있는 '공급 현황'을 다시 눌러도) 그 시점을 기기에 기억해 지운다. 다음 시점이 들어오면 또 단다. 처음 실린 날은 배치가
split_data.fresh_marks 로 직전 data-core.js 의 ADV.fresh 에서 이어 받는다 — 기능을 처음 배포한 회차는 날을 비워 셋이 한꺼번에
'새것'이 되지 않는다.

재현하는 실제 상태: 2026-10-08 주간(조사일 10/5) 반영 — 주간만 시점이 바뀌고 공급(2026Q2)·월간(2026-08)은 그대로인 회차.
픽스처: 합성 직전 fresh(공급·월간은 옛 날, 주간은 지난주 시점)와 오늘 2026-10-08, 저장소 home-app.js 의 freshModes·seeFresh·
markFresh·mapMode 를 합성 DOM 에서 돌린다.

변이(각각 실제로 확인):
  · fresh_marks 에서 직전 값이 없을 때도 오늘로 찍으면(첫 회차) → 첫 회차 시험 빨강.
  · fresh_marks 에서 시점이 같을 때 오늘로 다시 찍으면(날을 이어 받지 않음) → 이어 받기 시험 빨강.
  · freshModes 의 `age<n` 을 `<=` 로 바꾸면, 모드별 일수 대신 한 값을 쓰면 → 기간 단정 빨강.
  · freshModes 가 기억한 시점(seen)을 보지 않으면 → 누른 뒤 단정 빨강.
  · freshModes 가 force 를 무시하면(첫 이틀에도 누른 기록으로 지움), force 를 3일로 늘리면 → 무조건 구간 단정 빨강.
  · mapMode 에서 seeFresh 를 `MAP_MODE===m` 검사 뒤로 옮기면 → 켜진 공급 단추를 눌러도 남아 빨강.
  · split_data.main 이 old_fresh(OUT) 대신 None 을 넘기면 → main 이어 받기 시험 빨강.
"""
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
import split_data as S  # noqa: E402

TODAY = '2026-10-08'
OLD = {'days': dict(S.FRESH_DAYS), 'supply': {'p': '2026Q2', 'd': '2026-08-29'}, 'weekly': {'p': '2026-09-28', 'd': '2026-10-01'},
       'monthly': {'p': '2026-08', 'd': '2026-09-17'}}
NOW = {'supply': '2026Q2', 'weekly': '2026-10-05', 'monthly': '2026-08'}


def test_first_run_marks_nothing_new():
    got = S.fresh_marks(NOW, None, TODAY)
    assert got == {'days': S.FRESH_DAYS, 'force': S.FRESH_FORCE, 'supply': {'p': '2026Q2', 'd': ''}, 'weekly': {'p': '2026-10-05', 'd': ''},
                   'monthly': {'p': '2026-08', 'd': ''}}, got


def test_only_the_mode_whose_period_moved_gets_today():
    got = S.fresh_marks(NOW, OLD, TODAY)
    assert got['weekly'] == {'p': '2026-10-05', 'd': TODAY}
    assert got['supply'] == OLD['supply'] and got['monthly'] == OLD['monthly']
    assert S.fresh_marks(dict(NOW, monthly=None), OLD, TODAY).get('monthly') is None   # 시점이 없는 모드는 싣지 않는다


def test_main_carries_the_first_day_from_the_previous_core(tmp_path, monkeypatch):
    """배치는 매일 split_data 를 돈다. 시점이 그대로인 날 다시 돌아도 처음 실린 날이 오늘로 밀리면 배지가 영영 3일 안에 머문다."""
    out = str(tmp_path / 'data-core.js')
    monkeypatch.setattr(S, 'OUT', out)
    for name in ('TREND', 'SGG', 'REST', 'SIZE'):
        monkeypatch.setattr(S, name, str(tmp_path / (name.lower() + '.json')))
    S.main()
    first = S.old_fresh(out)
    assert first and all(first[m]['d'] == '' for m in S.FRESH_MODES if m in first), first
    seeded = dict(first, weekly={'p': first['weekly']['p'], 'd': '2026-10-01'})
    t = io.open(out, encoding='utf-8').read()
    t = t.replace('"fresh":' + json.dumps(first, ensure_ascii=False, separators=(',', ':')),
                  '"fresh":' + json.dumps(seeded, ensure_ascii=False, separators=(',', ':')))
    io.open(out, 'w', encoding='utf-8').write(t)
    S.main()
    assert S.old_fresh(out)['weekly'] == {'p': first['weekly']['p'], 'd': '2026-10-01'}


def _fn(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i, depth = src.index('{', m.end()), 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _node(js):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8'))


HARNESS = r'''
%(fns)s
const MODE_SEEN_KEY='mode_seen';
var LS={}; function lsGet(k){return k in LS?LS[k]:null;} function lsSet(k,v){LS[k]=String(v);return true;}
var F=%(fresh)s;
var out={};
out.by={};
["2026-10-08","2026-10-09","2026-10-11","2026-10-12","2026-10-14","2026-10-15"].forEach(function(d){ out.by[d]=freshModes(F,_dn(d),{}); });
out.seen=freshModes(F,_dn("2026-10-08"),{weekly:"2026-10-05",supply:"2025Q4"});
out.seenBy={};
["2026-10-09","2026-10-10","2026-10-11"].forEach(function(d){ out.seenBy[d]=freshModes(F,_dn(d),{weekly:"2026-10-05",supply:"2025Q4"}); });
out.empty=freshModes({days:{weekly:4},weekly:{p:"2026-10-05",d:""}},_dn("2026-10-08"),{});
out.future=freshModes({days:{weekly:4},weekly:{p:"2026-10-05",d:"2026-10-09"}},_dn("2026-10-08"),{});
out.none=freshModes(null,_dn("2026-10-08"),{});
/* DOM: 단추 셋, 월간은 잠김 */
function btn(m,dis){ var kids=[]; return {m:m,disabled:dis,kids:kids,
  querySelector:function(){ return kids[0]||null; },
  insertAdjacentHTML:function(p,h){ var me=this; kids.push({h:h,remove:function(){ me.kids.splice(0,1); }}); }}; }
var B={supply:btn("supply",false),weekly:btn("weekly",false),monthly:btn("monthly",true)};
var document={querySelector:function(q){ var m=/data-m="(\w+)"\](\s*\.nb)?/.exec(q); var b=B[m[1]]; return m[2]?b.querySelector():b; },
  getElementById:function(){ return null; }};
var ADV={fresh:{days:F.days,force:F.force,supply:{p:"2026Q2",d:"2026-10-05"},weekly:{p:"2026-10-05",d:"2026-10-08"},monthly:{p:"2026-09",d:"2026-10-08"}}};
var MAP_MODE='supply', TB_VIEW='map';
function priceOk(){ return true; } function renderAggCards(){} function renderSidoMap(){} function track(){} function tbView(){}
var _kst=function(){ return {day:_dn("2026-10-08"),hour:12}; };
markFresh();
out.badges=Object.keys(B).filter(function(k){ return B[k].kids.length; });
out.html=B.weekly.kids[0]&&B.weekly.kids[0].h;
mapMode('supply');               // 켜져 있는 공급 단추를 다시 누른다
out.afterSupply=Object.keys(B).filter(function(k){ return B[k].kids.length; });
out.ls=JSON.parse(LS[MODE_SEEN_KEY]||'{}');
markFresh();                     // 다시 그려도(다음 방문) 공급은 달지 않는다
out.again=Object.keys(B).filter(function(k){ return B[k].kids.length; });
mapMode('weekly');               // 첫날인 주간을 누른다 — 화면에서는 지우지만
out.afterWeekly=Object.keys(B).filter(function(k){ return B[k].kids.length; });
markFresh();                     // 다시 그리면(새로고침) 첫날이라 또 단다
out.forced=Object.keys(B).filter(function(k){ return B[k].kids.length; });
process.stdout.write(JSON.stringify(out));
'''


def test_badge_window_seen_and_tap():
    src = HS.home_source()
    fns = '\n'.join(_fn(src, n) for n in ('_dn', 'freshModes', 'modeSeen', 'markFresh', 'seeFresh', 'mapMode'))
    assert S.FRESH_DAYS == {'supply': 14, 'weekly': 4, 'monthly': 7}   # 2026-10-08 대표 결정(주간 목→일, 월간 한 주, 분기 두 주)
    fresh = {'days': S.FRESH_DAYS, 'force': S.FRESH_FORCE, 'supply': {'p': '2026Q2', 'd': '2026-09-25'}, 'weekly': {'p': '2026-10-05', 'd': '2026-10-08'},
             'monthly': {'p': '2026-09', 'd': '2026-10-08'}}
    got = _node('var _DAY=864e5;\n' + HARNESS % {'fns': fns, 'fresh': json.dumps(fresh)})
    # 공급 9/25(14일째가 10/8), 주간·월간 10/8 — 그날 포함 공급 14·주간 4(목→일)·월간 7일
    assert got['by'] == {'2026-10-08': ['supply', 'weekly', 'monthly'], '2026-10-09': ['weekly', 'monthly'],
                         '2026-10-11': ['weekly', 'monthly'], '2026-10-12': ['monthly'], '2026-10-14': ['monthly'],
                         '2026-10-15': []}, got['by']
    assert got['seen'] == ['supply', 'weekly', 'monthly'], got['seen']   # 10/8 은 주간·월간 첫날 — 눌렀어도 단다
    # 주간을 누른 기기: 첫날·다음 날은 단다, 3일째(10/10)부터는 안 단다. 옛 시점을 누른 기록은 무시
    assert got['seenBy'] == {'2026-10-09': ['weekly', 'monthly'], '2026-10-10': ['monthly'], '2026-10-11': ['monthly']}, \
        got['seenBy']
    assert S.FRESH_FORCE == 2
    assert got['empty'] == [] and got['future'] == [] and got['none'] == []
    assert got['badges'] == ['supply', 'weekly'], got['badges']  # 잠긴 단추(월간)엔 달지 않는다
    assert 'aria-hidden="true">N<' in got['html'] and 'sr-only' in got['html']
    assert got['afterSupply'] == ['weekly'] and got['ls'] == {'supply': '2026Q2'}, (got['afterSupply'], got['ls'])
    assert got['again'] == ['weekly'], got['again']                # 공급은 4일째(10/5) — 누르면 다시 안 단다
    assert got['afterWeekly'] == [] and got['forced'] == ['weekly'], (got['afterWeekly'], got['forced'])


def test_badges_are_drawn_at_boot_after_the_buttons_are_locked():
    src = HS.home_source()
    i, j = src.index('\nrenderAggCards();'), src.index('\nmarkFresh();')
    assert i < j, 'markFresh 가 renderAggCards(못 쓰는 시세 단추 잠금) 앞에 돈다'
    css = io.open(os.path.join(HS.ROOT, 'app.css'), encoding='utf-8').read()
    rule = re.search(r'#sec-score \.map-mode \.nb\{([^}]*)\}', css).group(1)
    assert 'font-size:13px' in rule and 'top:-' in rule and 'left:-' in rule, rule   # B안: 테두리 위 좌상단
    assert '#sec-score .map-mode{overflow:visible}' in css
