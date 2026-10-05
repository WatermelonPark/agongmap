# -*- coding: utf-8 -*-
"""홈(index.html)의 요약 구간과 검색 설명에 그 회차 숫자를 굽는다(홈 마케팅 검수 B3·SEO-1·MOB-5, 2026-09-27).

왜: 홈의 숫자와 판정은 전부 스크립트(home-app.js)가 data-core.js 를 받은 뒤에 그렸다. 정적 HTML 에는 방법론 문단만
남아, 스크립트를 돌리지 않는 검색 로봇·카카오·네이버 링크 미리보기에 현재 판정도 이번 주 숫자도 보이지 않았고(SEO-1),
느린 망에서는 첫 화면이 스크립트가 올 때까지 빈 상자였다(MOB-5). /weekly/ 가 2026-09-15 에 같은 결함을 표식 방식으로 고쳤다.

대표 확인(09-27): index.html 안 **표식 구간 하나**만 배치가 고쳐 쓴다. 이 도구가 바꾸는 곳은 딱 둘이다.
  ① <!--HOME_SUMMARY_START--> … <!--HOME_SUMMARY_END-->   전국 공급 판정 한 줄(기준 분기) + 발표일 박은 주간 한 줄(/weekly/ 링크)
  ② <meta name="description">·og:description·twitter:description 의 content 값   같은 숫자
그 밖은 한 글자도 바꾸지 않는다 — 여기서 스스로 확인하고(바뀌면 SystemExit), test_home_summary 가 고정한다. 홈은 손으로
쓰는 파일이라 표식 밖을 배치가 건드리면 사람의 수정과 봇의 커밋이 부딪힌다.

화면 중복이 없는 이유: 표식 구간은 #map-wrap **안**에 있다. 스크립트가 지도를 그리면(renderSidoMap 의 innerHTML) 이 요약은
같은 숫자를 싣는 판정 카드·지도로 통째로 바뀐다 — 요약이 곧 스크립트가 그릴 자리다. 스크립트가 못 돌면 요약이 남는다.
자리 높이는 app.css 의 #map-wrap:not([data-done]) 예약이 그대로 잡는다(예약이 :empty 였으면 요약이 들어간 순간 풀려
CLS 가 되돌아온다 — test_home_summary 가 본다).

값은 전부 data-core.js(홈이 실제로 읽는 파일)에서 읽는다. 판정 문구는 split_data 가 sido_zones 정본 함수로 구운 ctxt·Ltxt,
주간 결론은 ADV.weekly.head(/weekly/ 제목·홈 띠와 같은 문장), 발표일은 weekly_release, 반올림은 make_weekly_page.pv2 다.
여기서 새로 계산하지 않는다. 표준 라이브러리만 쓴다(배치의 생성기 단계는 pip 설치 전에 돈다).

사용: python tools/make_home_summary.py
"""
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import sido_zones as SZ  # noqa: E402  (등급 말 GRADE_LABS — 홈 배지 TB_GRADE 와 같은 값)
import weekly_release as WR  # noqa: E402  (발표일 — 홈 띠·/weekly/ 와 같은 규칙)
import make_weekly_page as MW  # noqa: E402  (변동률 반올림 pv2 — 사이트 pv2 와 같다)
import home_src as HS  # noqa: E402  (홈 파일 위치의 정본 — 이 도구는 스크립트가 아니라 마크업 파일을 쓴다)

PAGE = os.path.join(HS.ROOT, HS.HOME)
CORE = os.path.join(ROOT, 'data-core.js')
START, END = '<!--HOME_SUMMARY_START-->', '<!--HOME_SUMMARY_END-->'
# 숫자를 넣는 메타 셋. (속성 이름, 값)
METAS = (('name', 'description'), ('property', 'og:description'), ('name', 'twitter:description'))
_REGION = re.compile(re.escape(START) + r'(.*?)' + re.escape(END), re.S)


def _meta_pat(key, attr):
    return re.compile(r'(<meta %s="%s" content=")([^"]*)(">)' % (key, re.escape(attr)))


def load_core(path=None):
    s = io.open(path or CORE, encoding='utf-8').read()
    m = re.search(r'^const ADV=(\{.*\});$', s, re.M)
    if not m:
        raise SystemExit('data-core.js 에서 ADV 를 찾지 못했다 — split_data 출력 모양이 바뀌었는지 볼 것')
    return json.loads(m.group(1))


def facts(adv):
    """홈 요약에 쓰는 값 — 모두 data-core 에 실린 그대로. 없는 조각은 None(그 줄·그 조각만 빠진다)."""
    out = {'nat': None, 'wk': None, 'n_sido': None}
    sido = adv.get('sido') or {}
    zones = sido.get('zones') or []
    H = sido.get('H') or SZ.LEAD_Q
    out['yrs'] = '%g년' % (H / 4.0)            # '3년' — 판정 창(H)에서 유도한다(손으로 적지 않는다)
    nat = next((z for z in zones if z.get('z') == '전국'), None)
    if zones:
        out['n_sido'] = len([z for z in zones if not z.get('agg')])
    if nat and nat.get('ctxt') and nat.get('grade') in SZ.GRADE_LABS:
        # 세대수만: cnum(2차 배포 뒤 split 이 싣는다), 옛 data-core 면 ctxt 첫 조각의 숫자 부분
        num = nat.get('cnum') or (nat['ctxt'].split(' · ')[0].rsplit(' ', 1)[0] if '세대' in nat['ctxt'] else '')
        # 비율 문장: rtxt(허브 목록과 같은 정본 문구 '부족분은 3년 필요량의 60%'). 세대수가 없을 때만 쓴다. 없으면 같은 정본 함수로.
        rtxt = nat.get('rtxt') or (SZ.ratio_text(nat['ratio'], H) if nat.get('ratio') is not None else '')
        out['nat'] = {'lab': SZ.GRADE_LABS[nat['grade']], 'ctxt': nat['ctxt'], 'num': num, 'rtxt': rtxt,
                      'basis': sido.get('Ltxt') or sido.get('L') or ''}
    w = adv.get('weekly') or {}
    rows = w.get('rows') or []
    if rows and re.match(r'^\d{4}-\d{2}-\d{2}$', rows[-1].get('p') or ''):
        row = rows[-1]
        regs, ma = w.get('regions') or [], row.get('ma') or []
        v = ma[regs.index('전국')] if '전국' in regs and regs.index('전국') < len(ma) else None
        hd = w.get('head')
        head = hd['text'] if (hd and hd.get('p') == row['p'] and hd.get('text')) else None   # 홈 JS weeklyHead 와 같은 조건
        # 설명 문장용 결론 — /weekly/ 제목·홈 띠와 같은 함수(conclusion)의 조각을 '경기 +0.23%로 가장 크게 올랐습니다'로 잇는다
        try:
            c = MW.conclusion(w)
        except Exception:                   # noqa: BLE001 — 설명 한 조각 때문에 홈 굽기를 멈추지 않는다
            c = None
        lead = None if c is None else (c['text'] if c['who'] is None else '%s %s로 %s' % (c['who'], c['val'], c['verb']))
        out['wk'] = {'pub': WR.md(WR.status(row['p'])['pub']), 'nation': None if v is None else MW.pv2(v) + '%',
                     'head': head, 'lead': lead}
    return out


def _wk_bits(wk):
    return [x for x in ('전국 ' + wk['nation'] if wk['nation'] else None, wk['head']) if x]


def _wk_sentence(wk):
    """'전국 +0.09% · 경기 +0.23%로 가장 크게 올랐습니다' — 전국 값·결론 가운데 있는 것만."""
    bits = [x for x in ('전국 ' + wk['nation'] if wk['nation'] else None, wk['lead']) if x]
    if not bits:
        return None
    s = ' · '.join(bits)
    return s if wk['lead'] else s + '입니다'


def region_html(f):
    """표식 구간 안에 넣을 마크업. 구울 것이 없으면 빈 문자열(표식만 남는다)."""
    rows = []
    if f['nat']:
        n = f['nat']
        rows.append('  <p class="hsum-s"><a href="/zone/전국/"><b>전국 아파트 공급 %s</b> · %s%s →</a></p>'
                    % (html.escape(n['lab']), html.escape(n['ctxt']),
                       (' · %s 기준' % html.escape(n['basis'])) if n['basis'] else ''))
    if f['wk'] and _wk_bits(f['wk']):
        rows.append('  <p class="hsum-w"><a href="/weekly/"><b>%s 발표 주간 아파트 매매가격</b> %s →</a></p>'
                    % (html.escape(f['wk']['pub']), html.escape(' · '.join(_wk_bits(f['wk'])))))
    if not rows:
        return ''
    return '\n'.join(['<div class="home-sum">'] + rows + ['</div>'])


def meta_texts(f):
    """(description, og·twitter description). 숫자가 하나도 없으면 None — 메타를 그대로 둔다.

    문장은 정본 카드 문구(ctxt — 세대수가 없으면 비율 문구 rtxt)를 쓴다(2026-10-05):
      '2026년 2분기 기준 전국 아파트 공급은 686,396세대 부족(3년 필요량의 60%)입니다. 9/24 발표 주간 아파트 매매가격은
       전국 +0.09% · 경기 +0.23%로 가장 크게 올랐습니다. 국토교통부 착공·준공 실적으로 16개 시도의 3년 공급을 …'
    """
    wk = _wk_sentence(f['wk']) if f['wk'] else None
    n = f['nat'] if (f['nat'] and f['nat']['rtxt']) else None
    if not n and not wk:
        return None
    d, o = [], []
    if n:
        basis = ('%s 기준 ' % n['basis']) if n['basis'] else ''
        # 2026-10-05: 세대수와 비율을 정본 카드 문구(ctxt '686,396세대 부족(3년 필요량의 60%)')로 쓴다 — 괄호 안이 무엇의
        # 몇 %인지 말한다. 옛 '3년 필요량의 60% 부족(686,396세대)'은 공급률(40% 공급?)로도 읽혔다(대표 요청).
        body = n['ctxt'] if n['num'] else n['rtxt']
        sent = '%s전국 아파트 공급은 %s입니다.' % (basis, body)
        d.append(sent.replace('거의 같음입니다.', '거의 같습니다.'))
        o.append('%s전국 아파트 공급 %s.' % (basis, body))
    if wk:
        d.append('%s 발표 주간 아파트 매매가격은 %s.' % (f['wk']['pub'], wk))
        o.append('%s 발표 주간 매매 %s.' % (f['wk']['pub'], ('전국 ' + f['wk']['nation']) if f['wk']['nation'] else wk))
    k = ('%d개 시도' % f['n_sido']) if f['n_sido'] else '시도별'
    d.append('국토교통부 착공·준공 실적으로 %s의 %s 공급을 판정하고, 한국부동산원 주간 시세를 지도로 봅니다.' % (k, f['yrs']))
    o.append('%s %s 공급 판정과 주간 시세 지도, 국가 통계 기반.' % (k, f['yrs']))
    return ' '.join(d), ' '.join(o)


def outside(s):
    """표식 구간 안과 세 메타의 값을 비운 나머지 — 이 도구가 바꾸면 안 되는 부분."""
    s = _REGION.sub(START + END, s)   # (안의 줄바꿈까지 비운다 — 구간 안은 전부 이 도구의 몫이다)
    for key, attr in METAS:
        s = _meta_pat(key, attr).sub(lambda m: m.group(1) + m.group(3), s)
    return s


def render(s, adv):
    nl = '\r\n' if '\r\n' in s else '\n'
    if s.count(START) != 1 or s.count(END) != 1 or len(_REGION.findall(s)) != 1:
        raise SystemExit('index.html 에 HOME_SUMMARY 표식 쌍이 하나가 아니다(시작 %d · 끝 %d)'
                         % (s.count(START), s.count(END)))
    for key, attr in METAS:
        if len(_meta_pat(key, attr).findall(s)) != 1:
            raise SystemExit('index.html 에서 %s 메타를 하나로 찾지 못했다' % attr)
    f = facts(adv)
    body = region_html(f)
    # 표식은 제 줄에 있다 — 두 표식 줄 사이에 줄을 끼우기만 한다(비었으면 줄바꿈 하나). 앞뒤 줄은 건드리지 않는다.
    inner = nl + ((body.replace('\n', nl) + nl) if body else '')
    out = _REGION.sub(lambda m: START + inner + END, s)
    mt = meta_texts(f)
    if mt:
        vals = {'description': mt[0], 'og:description': mt[1], 'twitter:description': mt[1]}
        for key, attr in METAS:
            out = _meta_pat(key, attr).sub(
                lambda m, v=vals[attr]: m.group(1) + html.escape(v, quote=True) + m.group(3), out)
    if outside(out) != outside(s):
        raise SystemExit('홈 요약 생성기가 표식 밖을 바꿨다 — 쓰지 않는다')
    return out


def main():
    s = io.open(PAGE, encoding='utf-8', newline='').read()
    out = render(s, load_core())
    if out != s:
        io.open(PAGE, 'w', encoding='utf-8', newline='').write(out)
        print('wrote index.html 요약 구간')
    else:
        print('index.html 요약 구간 변경 없음')


if __name__ == '__main__':
    main()
