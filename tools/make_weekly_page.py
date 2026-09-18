# -*- coding: utf-8 -*-
"""/weekly/ 주간 시세 랜딩에 그 주의 답을 굽는다.

2026-09-15 고객 점검: 블로그에서 들어온 사람이 가장 먼저 닿는 페이지인데, 변동률이 스크립트로만
그려져 검색엔진과 카카오·네이버 링크 미리보기에 결론이 보이지 않았다. 답(시군구 TOP·서울 구)을
보려면 한 번 더 눌러야 했고, 광주·전남 타일은 판정 단위가 합쳐진 뒤에도 따로 나왔다.

페이지 뼈대(스타일·출처·더 둘러보기·네비)는 손으로 관리하고, 아래 자리만 이 도구가 채운다.
  <!--WK:HEAD-->   … <!--/WK:HEAD-->    기준일·결론 제목·시도 타일
  <!--WK:ANSWER--> … <!--/WK:ANSWER-->  시군구 상승·하락 TOP 3, 서울 구별 요약
  <meta name="description">, og:description, 'N개 시도' 문구

⚠️ 값은 전부 data.js 에서 온다. 시도 목록은 sido_zones.DISPLAY_ORDER, 시군구 이름은 index.html 의
   SGG_QNAME(홈 TOP 10 과 같은 표)을 쓴다. 반올림은 사이트 pv2r 와 같은 규칙이다 — 여기서 다르게
   반올림하면 같은 주 같은 지역이 홈과 이 페이지에서 끝자리가 갈린다.
⚠️ 전남광주 가격은 R-ONE 이 발표하는 통합 노드 값이다(update_adv_data 의 sido() 가 집는다).
   광주·전남을 우리가 합친 값이 아니다.

사용: python tools/make_weekly_page.py
"""
import datetime
import html
import io
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import sido_zones as SZ  # noqa: E402
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

PAGE = os.path.join(ROOT, 'weekly', 'index.html')
SIDO = [z for z in SZ.DISPLAY_ORDER if z not in SZ.AGG]


def load():
    s = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'/\*ADV_DATA_START\*/const ADV=(\{.*?\});', s, re.S).group(1))
    h = HS.home_source()
    m = re.search(r'const SGG_QNAME=(\{.*?\});', h)
    if not m:
        raise SystemExit('index.html 에서 SGG_QNAME 을 찾지 못했다 — 시군구 이름표 위치가 바뀌었는지 볼 것')
    return adv['weekly'], json.loads(m.group(1))


def pv2r(v):
    """사이트 pv2r 와 같다: 절대값을 소수 둘째에서 반올림(half-up)하고 부호를 붙인다."""
    if v is None:
        return None
    r = (-1 if v < 0 else 1) * math.floor(abs(v) * 100 + 0.5) / 100
    return r + 0.0


def pv2(v):
    r = pv2r(v)
    if r is None:
        return '·'
    return ('+' if r > 0 else '') + '%.2f' % r


def sign(v):
    r = pv2r(v)
    return 'up' if r and r > 0 else ('dn' if r and r < 0 else '')


def md(p):
    y, m, d = (int(x) for x in p.split('-'))
    return '%d/%d' % (m, d)


def pub(p):
    """조사기준일(월) → 발표일(목). make_weekly_share._pubdate 와 같은 규칙."""
    y, m, d = (int(x) for x in p.split('-'))
    return (datetime.date(y, m, d) + datetime.timedelta(days=3)).isoformat()


def tile(name, v, i):
    """홈 옛 라이브 미니맵과 같은 색 규칙 — 색도 표시값 기준."""
    a = min(.78, .10 + abs(v) * 2.4)
    rv = pv2r(v)
    bg = ('rgba(224,86,74,%.2f)' % a if rv > 0 else
          ('rgba(58,123,213,%.2f)' % a if rv < 0 else '#e9edeb'))
    # 글자는 항상 먹색 — 흰 글자는 연한 바탕(알파 .1~.78) 위에서 대비 2.2, 색 글자도 4.1 이었다(2026-09-18 오딧).
    # 방향은 바탕색이 이미 말한다. 보합 칸은 ink2(5.7).
    tc = '#131e24' if rv else '#4c5f66'
    return ('<div class="mm-tile" style="background:%s;animation-delay:%dms">'
            '<b style="color:%s">%s</b><span style="color:%s">%s%%</span></div>'
            % (bg, i * 22, tc, html.escape(name), tc, pv2(v)))


def counts(vals):
    up = sum(1 for v in vals if pv2r(v) > 0)
    dn = sum(1 for v in vals if pv2r(v) < 0)
    return up, dn, len(vals) - up - dn


def count_text(total_label, vals):
    up, dn, flat = counts(vals)
    parts = ['%d곳 상승' % up, '%d곳 하락' % dn] + (['%d곳 보합' % flat] if flat else [])
    return '%s 중 %s' % (total_label, ', '.join(parts))


def top3(items):
    """items [(이름, 값)] → (오른 곳 상위 3, 내린 곳 상위 3). 순서는 홈 TOP 10 과 같다.

    홈은 값 내림차순 정렬 뒤 앞 10개·뒤 10개를 뒤집어 쓴다(안정 정렬). 여기서도 같은 정렬을 쓰되,
    '하락'에는 실제로 내린 곳만 싣는다 — 모두 오른 주에 가장 덜 오른 곳을 '하락'이라 적지 않는다.
    """
    arr = sorted(items, key=lambda x: -x[1])
    up = [x for x in arr if pv2r(x[1]) > 0][:3]
    dn = [x for x in reversed(arr) if pv2r(x[1]) < 0][:3]
    return up, dn


def rank_list(title, cls, items, empty):
    lis = ''.join('<li><span class="nm">%s</span><b class="%s">%s%%</b></li>'
                  % (html.escape(n), sign(v), pv2(v)) for n, v in items)
    if not lis:
        lis = '<li class="none">%s</li>' % empty
    return '<div class="rk"><h3 class="%s">%s</h3><ol>%s</ol></div>' % (cls, title, lis)


def build(W, Q):
    regs = W['regions']
    miss = [z for z in SZ.DISPLAY_ORDER if z not in regs]
    if miss:
        raise SystemExit('주간 계열에 없는 지역: %s — 타일에서 그 지역이 조용히 빠진다' % ', '.join(miss))
    row = W['rows'][-1]
    p = row['p']
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', p or ''):
        raise SystemExit('주간 최신 회차 날짜 형식이 다르다: %r' % p)
    val = {r: row['ma'][i] for i, r in enumerate(regs)}
    sido = [(z, val[z]) for z in SIDO if val.get(z) is not None]
    if len(sido) < len(SIDO) // 2:
        raise SystemExit('시도 값이 %d곳뿐이다 — 반쯤 빈 결론을 굽지 않는다' % len(sido))
    nation = val.get('전국')
    survey, release = md(p), md(pub(p))
    datestr = '%s 조사 · %s 발표' % (survey, release)

    # ── 결론 한 줄: 절대 변동이 가장 큰 시도(동률이면 표시 순서가 앞선 곳)
    best = max(sido, key=lambda x: abs(pv2r(x[1])))
    up_s, dn_s = top3(sido)
    if pv2r(best[1]) == 0:
        h1 = '이번 주 아파트,<br>시도 모두 보합'
    else:
        h1 = ('이번 주 아파트,<br><em class="%s">%s %s%%</em> 가장 크게 %s'
              % (sign(best[1]), best[0], pv2(best[1]), '올랐다' if pv2r(best[1]) > 0 else '내렸다'))
    lead = ['전국 <b>%s%%</b>.' % pv2(nation) if nation is not None else '',
            '%s.' % count_text('시도 %d곳' % len(sido), [v for _, v in sido])]
    # 제목이 이미 말한 쪽은 되풀이하지 않고, 반대 방향 1위만 덧붙인다.
    other = dn_s if pv2r(best[1]) > 0 else up_s
    if other and pv2r(best[1]) != 0:
        lead.append('가장 많이 %s 곳은 %s %s%%다.'
                    % ('내린' if pv2r(best[1]) > 0 else '오른', other[0][0], pv2(other[0][1])))
    tiles = ''.join(tile(z, val[z], i) for i, z in enumerate(SZ.DISPLAY_ORDER) if val.get(z) is not None)
    head = '\n'.join([
        '  <p class="eyebrow">%s · 한국부동산원 주간 통계</p>' % datestr,
        '  <h1>%s</h1>' % h1,
        '  <p class="lead">%s</p>' % ' '.join(x for x in lead if x),
        '  <a class="minimap" href="/#stats-market" aria-label="이번 주 시도별 매매가격 변동률, 눌러서 시군구 상세 지도 보기">',
        '    <div class="mm-grid">%s</div>' % tiles,
        '    <div class="mm-cap"><span><i style="background:#e0564a"></i>상승</span>'
        '<span><i style="background:#3a7bd5"></i>하락</span><span>매매가격 전주 대비</span>'
        '<span class="go">시군구 상세 →</span></div>',
        '  </a>',
    ])

    # ── 시군구 TOP 3 (홈 TOP 10 과 같은 대상: SGG_QNAME 에 이름이 있고 값이 있는 곳)
    S = W['sgg']
    srow = S['rows'][-1]
    sgg = [(Q[c], srow['ma'][i]) for i, c in enumerate(S['codes'])
           if c in Q and i < len(srow['ma']) and srow['ma'][i] is not None]
    if len(sgg) < 10:
        raise SystemExit('시군구 값이 %d곳뿐이다 — TOP 3 를 굽지 않는다' % len(sgg))
    su, sd = top3(sgg)
    sgg_note = '매매가격 전주 대비 · 시군구 %d곳' % len(sgg)
    if srow['p'] != p:
        sgg_note += ' · %s 조사 기준' % md(srow['p'])

    # ── 서울 구별
    se = W['seoul']
    serow = se['rows'][-1]
    gu = [(g, serow['ma'][i]) for i, g in enumerate(se['regions'])
          if i < len(serow['ma']) and serow['ma'][i] is not None]
    gu_up, gu_dn = top3(gu)
    gu_text = count_text('서울 %d개 구' % len(gu), [v for _, v in gu]) + '.'
    if serow['p'] != p:
        gu_text += ' (%s 조사 기준)' % md(serow['p'])

    answer = '\n'.join([
        '<section class="ans"><div class="wrap">',
        '  <h2>시군구 상승·하락 TOP 3</h2>',
        '  <p class="sub">%s · %s</p>' % (sgg_note, datestr),
        '  <div class="rk2">%s%s</div>' % (
            rank_list('▲ 상승', 'up', su, '이번 주 오른 시군구가 없다'),
            rank_list('▼ 하락', 'dn', sd, '이번 주 내린 시군구가 없다')),
        '  <h2 class="h2-gap">서울 구별</h2>',
        '  <p class="sub">%s</p>' % gu_text,
        '  <div class="rk2">%s%s</div>' % (
            rank_list('▲ 상승', 'up', gu_up, '이번 주 오른 구가 없다'),
            rank_list('▼ 하락', 'dn', gu_dn, '이번 주 내린 구가 없다')),
        '  <a class="cta" href="/#stats-market">전체 TOP 10 · 시군구 지도 보기</a>',
        '  <div class="meta">주간·월간 · 매매·전세 · 무료 · 회원가입 없음</div>',
        '</div></section>',
    ])

    desc_bits = ['%s 기준 이번 주 아파트 매매가격은' % datestr]
    desc_bits.append(('전국 %s%%, ' % pv2(nation) if nation is not None else '')
                     + ('%s %s%%로 %s.' % (best[0], pv2(best[1]), '가장 크게 올랐다' if pv2r(best[1]) > 0 else '가장 크게 내렸다')
                        if pv2r(best[1]) != 0 else '시도 모두 보합이다.'))
    if su:
        desc_bits.append('시군구 상승 1위 %s %s%%%s.' % (su[0][0], pv2(su[0][1]),
                         (', 하락 1위 %s %s%%' % (sd[0][0], pv2(sd[0][1]))) if sd else ''))
    desc = ' '.join(desc_bits) + ' 한국부동산원 주간 통계로 전국 시군구·서울 구별 변동률을 본다.'
    og = '%s · 전국 %s%%, %s %s%%. 시군구·서울 구별 변동률 지도.' % (
        datestr, pv2(nation), best[0], pv2(best[1]))
    return head, answer, desc, og


def put(s, name, body, nl):
    pat = re.compile(r'(<!--WK:%s-->)(.*?)(<!--/WK:%s-->)' % (name, name), re.S)
    n = len(pat.findall(s))
    if n != 1:
        raise SystemExit('weekly/index.html 에 WK:%s 표식이 %d개다 — 1개여야 한다' % (name, n))
    return pat.sub(lambda m: m.group(1) + nl + body.replace('\n', nl) + nl + m.group(3), s)


def put_meta(s, key, attr, text):
    pat = re.compile(r'(<meta %s="%s" content=")[^"]*(">)' % (key, re.escape(attr)))
    if len(pat.findall(s)) != 1:
        raise SystemExit('weekly/index.html 에서 %s 메타를 찾지 못했다' % attr)
    return pat.sub(lambda m: m.group(1) + html.escape(text, quote=True) + m.group(2), s)


def render(s, W, Q):
    nl = '\r\n' if '\r\n' in s else '\n'
    head, answer, desc, og = build(W, Q)
    s = put(s, 'HEAD', head, nl)
    s = put(s, 'ANSWER', answer, nl)
    s = put_meta(s, 'name', 'description', desc)
    s = put_meta(s, 'property', 'og:description', og)
    # 시도 수는 모델에서 센다(CLAUDE.md 데이터 원칙). '전국 16개 시도'가 통합 뒤에도 남는 종류의 결함.
    s = re.sub(r'(?<!\d)\d+개 시도', '%d개 시도' % len(SIDO), s)
    return s


def main():
    W, Q = load()
    s = io.open(PAGE, encoding='utf-8', newline='').read()
    out = render(s, W, Q)
    if out != s:
        io.open(PAGE, 'w', encoding='utf-8', newline='').write(out)
        print('wrote weekly/index.html (%s)' % W['rows'][-1]['p'])
    else:
        print('weekly/index.html 변경 없음 (%s)' % W['rows'][-1]['p'])


if __name__ == '__main__':
    main()
