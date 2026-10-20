# -*- coding: utf-8 -*-
"""GA 내부 트래픽 표식(백로그 48) — 모든 GA 페이지가 같은 조각(ga_tag.INTERNAL_SCRIPT)을 거쳐 config 를 부르는지 본다.

왜: 마케팅 지표(블로그발 세션·주요 이벤트)를 GA 로 재는데, IP 기준 내부 트래픽 규칙은 이동통신망 휴대폰을 거르지 못한다.
기기에 `?internal=on` 표식을 남기고 모든 페이지의 config 에 `traffic_type:'internal'` 을 실으면 GA 의 'Internal Traffic'
필터가 그 기기의 전송을 보고서에서 뺀다. 페이지 하나라도 조각을 빠뜨리면 그 페이지 방문만 다시 지표에 섞인다 —
손 페이지가 아홉 장이라 사람이 기억으로 막을 일이 아니다(test_ga_optout 와 같은 까닭).

무엇을 깨뜨리면 빨개지나(모두 실제로 확인):
  · 손 페이지 하나(about/index.html)에서 조각을 빼면, 또는 config 를 옛 `gtag('config','G-…')` 로 되돌리면
    test_every_ga_page_routes_config_through_the_flag 가 빨개진다.
  · 생성기 템플릿(make_sido_pages)에서 %(ga_int)s 를 빼면 생성 뒤 시도 리포트 20장이 같은 시험에서 빨개진다.
  · 조각의 'on' 갈래를 지우면 test_flag_switch_on_off 가, 홈 머리에서 조각을 ① 앞으로 옮기면 해시 속 ?internal=on 시험이 빨개진다.
  · 방침 1항 표에서 traffic_type 행을 지우면 test_privacy_lists_the_internal_flag 가 빨개진다.
픽스처: 저장소의 실제 HTML 전부(생성 페이지는 CI·배치가 생성기를 먼저 돌린 판)와, 조각을 node vm 에 올린 작은 브라우저 모형.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import ga_tag as GT  # noqa: E402
from test_ga_optout import _ga_pages  # noqa: E402  (GA 로더를 싣는 페이지 찾기 — 같은 목록)

RAW_CONFIG = re.compile(r"""gtag\(\s*['"]config['"]""")


def test_every_ga_page_routes_config_through_the_flag():
    pages = _ga_pages()
    assert len(pages) >= 30, 'GA 페이지를 거의 못 찾았다 — 대조가 헛돈다'
    bad = []
    for rel, html in pages:
        n = html.count(GT.INTERNAL_SCRIPT)
        calls = list(GT.CONFIG_CALL.finditer(html))
        raw = RAW_CONFIG.findall(html)
        if n != 1:
            bad.append('%s: 표식 조각 %d개(정확히 하나)' % (rel, n))
            continue
        if not calls or len(calls) != len(raw):
            bad.append('%s: config 호출 %d개 중 %d개만 읽힘' % (rel, len(raw), len(calls)))
            continue
        if html.index(GT.INTERNAL_SCRIPT) > calls[0].start():
            bad.append('%s: 표식 조각이 config 뒤에 있다' % rel)
        for m in calls:
            if m.group(1) != GT.GA_ID or not (m.group(2) or '').strip().startswith('gaCfg('):
                bad.append('%s: gaCfg 를 거치지 않는 config — %s' % (rel, m.group(0)))
    assert not bad, 'GA 내부 트래픽 표식이 어긋난 페이지(손 페이지는 tools/ga_tag.py 의 INTERNAL_SCRIPT 를 글자 그대로): %s' % bad


def _node(script):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    p = subprocess.run(['node', '-e', script], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


SWITCH = r'''
const vm = require('vm');
const out = [];
for (const c of %(cases)s) {
  const store = Object.assign({}, c.store);
  const ctx = {URLSearchParams, location: {search: c.search},
               localStorage: {getItem(k){return k in store ? store[k] : null;}, setItem(k,v){store[k]=String(v);}, removeItem(k){delete store[k];}}};
  vm.createContext(ctx);
  vm.runInContext(%(js)s, ctx);
  out.push({store, plain: vm.runInContext('gaCfg()', ctx), home: vm.runInContext('gaCfg({send_page_view:false})', ctx)});
}
process.stdout.write(JSON.stringify(out));
'''


def test_flag_switch_on_off():
    """`?internal=on` 은 표식을 남기고 그 뒤 config 에 traffic_type 을 싣는다. `?internal=off` 는 지운다. 표식 없는 기기는 아무것도 안 붙는다.
    픽스처: 표식 없는 기기·?internal=on·표식 있는 기기의 보통 방문·?internal=off 네 경우."""
    js = re.search(r'<script>(.*)</script>', GT.INTERNAL_SCRIPT, re.S).group(1)
    k = GT.INTERNAL_KEY
    cases = [{'search': '', 'store': {}}, {'search': '?internal=on', 'store': {}},
             {'search': '?utm_source=x', 'store': {k: '1'}}, {'search': '?internal=off', 'store': {k: '1'}}]
    o = _node(SWITCH % {'cases': json.dumps(cases), 'js': json.dumps(js)})
    assert o[0]['store'] == {} and o[0]['plain'] == {} and o[0]['home'] == {'send_page_view': False}
    assert o[1]['store'] == {k: '1'} and o[1]['plain'] == {'traffic_type': GT.TRAFFIC_TYPE}
    assert o[1]['home'] == {'send_page_view': False, 'traffic_type': GT.TRAFFIC_TYPE}
    assert o[2]['plain'] == {'traffic_type': GT.TRAFFIC_TYPE}
    assert o[3]['store'] == {} and o[3]['plain'] == {}


def test_home_config_carries_the_flag_even_from_a_hash_query():
    """홈은 해시 속 쿼리를 진짜 쿼리로 옮긴 ① 뒤에 표식을 읽는다 — 블로그 링크 꼴 '/#stats?internal=on' 도 먹는다.
    config 매개변수가 홈 수동 page_view·이벤트에 따라가므로 config 한 곳에 실리면 된다(send_page_view:false 는 그대로).
    픽스처: test_home_entry 의 머리 실행 모형(실제 index.html 머리 스크립트를 순서대로 돌린다)."""
    from test_home_entry import _run, SITE
    for start, store in ((SITE + '/?internal=on', {}), (SITE + '/#stats?internal=on', {}), (SITE + '/', {GT.INTERNAL_KEY: '1'})):
        got = _run(start, noHome=True, store=store)
        cfg = [q for q in got['queueAtHead'] if q[0] == 'config']
        assert len(cfg) == 1 and cfg[0][2] == {'send_page_view': False, 'traffic_type': GT.TRAFFIC_TYPE}, (start, cfg)
        assert got['store'].get(GT.INTERNAL_KEY) == '1'
    got = _run(SITE + '/?internal=off', noHome=True, store={GT.INTERNAL_KEY: '1'})
    cfg = [q for q in got['queueAtHead'] if q[0] == 'config']
    assert cfg[0][2] == {'send_page_view': False} and GT.INTERNAL_KEY not in got['store']


def test_put_converts_an_old_head_and_is_idempotent():
    """생성기 머리 맞추기(ga_tag.put — /weekly/ 뼈대가 부른다): 옛 머리(조각 없음·config 맨몸)를 정본 모양으로, 두 번 돌려도 같다.
    픽스처: 2026-10-19 까지의 /weekly/ 머리 꼴(손 뼈대의 여러 줄 config)."""
    old = ('<head>\n<script>if(1){}</script>\n<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>\n'
           "<script>\n  gtag('js', new Date());\n  gtag('config', '%s');\n</script>\n</head>" % (GT.GA_ID, GT.GA_ID))
    new = GT.put(old)
    assert new.count(GT.INTERNAL_SCRIPT) == 1 and new.index(GT.INTERNAL_SCRIPT) < new.index('googletagmanager')
    assert GT.config_call() in new and "gtag('config', '" not in new
    assert GT.put(new) == new
    assert GT.put('<head></head>') == '<head></head>'      # GA 없는 페이지는 그대로


def test_privacy_lists_the_internal_flag():
    """방침 1항 GA 전송 목록에 traffic_type 한 줄이 있고 값이 정본(TRAFFIC_TYPE)과 같다."""
    root = os.path.join(HERE, '..', '..')
    s = io.open(os.path.join(root, 'privacy', 'index.html'), encoding='utf-8').read()
    m = re.search(r'<tr data-cfg="traffic_type"><td><code>traffic_type</code></td><td><code>(\w+)</code></td>', s)
    assert m and m.group(1) == GT.TRAFFIC_TYPE, '방침 1항 표에 traffic_type 행이 없거나 값이 다르다'
    assert 'traffic_type' in GT.INTERNAL_SCRIPT
