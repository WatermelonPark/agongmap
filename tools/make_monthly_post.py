#!/usr/bin/env python3
"""월간 시세 블로그 초안 생성기(한국부동산원 월간 아파트가격 동향 발표일에 사람이 돌린다).

쓰는 법: python tools/make_monthly_post.py [--out drafts/monthly-YYYY-MM] [--title "결론절"]
만드는 것(drafts/monthly-<YYYY-MM>/): thumb.png(+_370·_104), seoul-gu.png(서울 25개 구 막대), monthly-card.png
(배치가 구운 share/monthly-card.png 사본), body.html(본문, 자리 표시자는 이미지 넷과 해석 문단 하나), title.txt(제목 후보).

숫자는 /monthly/ 페이지를 굽는 make_monthly_page 의 함수(load·pv2·cum_month·trail12·month_label)와 같은 ADV·STATS 에서
읽는다. 여기서 산식을 새로 쓰지 않는다(사이트와 블로그가 다른 숫자를 말하면 안 된다). 2026-10-23 대표 지시
("월간 시세 생성기도 만들어")로 만들었고, 첫 글(2026년 9월분)을 손으로 쓴 구성을 그대로 옮겼다.
"""
import html as _html
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_monthly_page as MP   # noqa: E402
import sido_zones as SZ          # noqa: E402

SITE = MP.SITE
LOCAL_LIMIT = 0.1          # '지방은 한 달에 0.1%도 오르지 않았다'의 문턱(표시값 기준)
SEOUL = '서울'


def site_link(path, campaign):
    """블로그 UTM 은 '#' 앞(쿼리). make_naver_post.site_link 와 같은 꼴(&amp;)."""
    base, hash_, frag = path.partition('#')
    return ('%s%s?utm_source=naver_blog&amp;utm_medium=social&amp;utm_campaign=%s%s%s'
            % (SITE, base, campaign, hash_, frag))


def rv(v):
    """표시값(사이트 반올림 정본) — 부호·비교는 늘 이 값으로 한다."""
    return None if v is None else MP.MW.pv2r(v)


def pct(v):
    return MP.pv2(v) + '%'


def facts(adv, sts):
    """글에 쓰는 숫자 묶음. 모두 배치 값을 표시 자릿수로 반올림한 것."""
    mo = adv['monthly']
    regs, rows = mo['regions'], mo['rows']
    ri = {r: i for i, r in enumerate(regs)}
    last = rows[-1]
    ym = str(last['p'])
    col = lambda r, k, row=last: (row.get(k) or [None] * len(regs))[ri[r]]
    se = mo['seoul']
    srow = se['rows'][-1]
    if str(srow['p']) != ym:
        raise SystemExit('서울 구별 월간(%s)과 시도 월간(%s)의 달이 다르다 — 배치가 한쪽만 갱신됐는지 볼 것' % (srow['p'], ym))
    gu = sorted(((n, rv(v)) for n, v in zip(se['regions'], srow['ma']) if v is not None), key=lambda x: -x[1])
    up = [g for g in gu if g[1] > 0]
    down = sorted((g for g in gu if g[1] < 0), key=lambda g: g[1])     # 많이 내린 순
    f = dict(ym=ym, label=MP.month_label(ym), mon=int(ym[5:7]), gu=gu, up=up, down=down,
             over1=[g for g in up if g[1] >= 1])
    f['seoul'] = [(str(r['p']), rv(col(SEOUL, 'ma', r))) for r in rows[-4:]]
    f['seoul_je'] = rv(col(SEOUL, 'je'))
    f['seoul_wo'] = [(str(r['p']), rv(col(SEOUL, 'wo', r))) for r in rows[-2:]]
    f['cap'] = rv(col('수도권', 'ma'))
    f['local'] = [(str(r['p']), rv(col('지방', 'ma', r))) for r in rows]
    f['fall'] = sorted(((SZ.disp(r), rv(col(r, 'ma'))) for r in MP.ORDER
                        if r not in MP.AGG and r in ri and rv(col(r, 'ma')) is not None and rv(col(r, 'ma')) < 0),
                       key=lambda x: x[1])
    # 입주: /monthly/ 3절과 같은 행(끝난 분기 실적·진행 중인 분기 추정)
    occ = adv.get('occupancy') or {}
    orows, oregs = occ.get('rows') or [], occ.get('regions') or []
    fut = [r for r in orows if r.get('e')]
    f['occ'] = None
    if fut and SEOUL in oregs:
        nxt = fut[0]
        v = nxt['v'][oregs.index(SEOUL)]
        ref = (occ.get('ref') or {}).get(SEOUL)
        if v is not None and ref:
            f['occ'] = dict(q=SZ.quarter_text(nxt['p']), n=int(round(v)), share=int(round(v / ref * 100)), ref=ref)
    # 인허가: /monthly/ 2절과 같은 함수
    f['perm'] = None
    pm = sts.get('인허가')
    if pm:
        i, p = MP.last_idx(pm)
        cur, yr = MP.cum_month(pm, i), MP.trail12(sts, p)
        if cur.get(SEOUL) is not None and yr.get(SEOUL):
            f['perm'] = dict(label=MP.month_label(p), n=cur[SEOUL], y12=yr[SEOUL], share=cur[SEOUL] / yr[SEOUL])
    return f


def KDAL(n):
    """달 수 → '두 달째'·'석 달째'·'넉 달째'·'5달째'."""
    return {2: '두 달째', 3: '석 달째', 4: '넉 달째'}.get(n, '%d달째' % n)


def trend_text(ser):
    """서울 매매 최근 달들 → '두 달째 상승폭이 줄었어요' 같은 한 문장(표시값 기준, 마지막 달부터 거꾸로 센다)."""
    vals = [v for _, v in ser if v is not None]
    if len(vals) < 2:
        return ''
    n, sign = 0, None
    for a, b in zip(reversed(vals[:-1]), reversed(vals[1:])):
        s = (b > a) - (b < a)
        if s == 0 or (sign is not None and s != sign):
            break
        sign = s; n += 1
    if not n:
        return '상승폭은 지난달과 같았어요.'
    word = {1: ''}.get(n, KDAL(n) + ' ')
    return '%s%s.' % (word, '상승폭이 줄었어요' if sign < 0 else '상승폭이 커졌어요')


def local_streak(local):
    """지방 매매가 표시값으로 LOCAL_LIMIT 아래(그리고 0 이상)인 달이 끝에서부터 몇 달 이어졌나."""
    n = 0
    for _, v in reversed(local):
        if v is None or not (0 <= v < LOCAL_LIMIT):
            break
        n += 1
    return n


def default_title(f):
    """'[한국부동산원] N월 월간 아파트가격 동향 | 결론절' — 결론절은 서울 구별 갈림이 있으면 그것, 없으면 서울·수도권 숫자."""
    head = '[한국부동산원] %d월 월간 아파트가격 동향' % f['mon']
    if f['down'] and len(f['down']) <= 3 and f['up']:
        names = '·'.join(n for n, _ in f['down'])
        tail = '%s만 내리고 서울 %d개 구는 올랐습니다' % (names, len(f['up']))
    else:
        tail = '서울 %s, 수도권 %s' % (pct(f['seoul'][-1][1]), pct(f['cap']))
    return '%s | %s' % (head, tail)


V_OPEN = ('%d월 서울 아파트값, 같은 서울 안에서 상승과 하락이 엇갈렸습니다.', '%d월 서울 아파트값은 구마다 등락이 갈렸습니다.',
          '%d월 서울 아파트값을 구별로 세워 보면 모양이 둘로 나뉩니다.')
V_Q = ('사시는 구는 %d월에 어느 쪽이었나요.', '%d월 숫자에서 우리 동네는 몇 번째쯤이던가요.',
       '%d월 표에서 먼저 찾아보신 구가 어디였나요.')


def body(f, title, k=None):
    k = f['mon'] % 3 if k is None else k
    B = ['<p>[여기에 이미지 thumb.png 를 넣어 주세요. 첫 이미지가 대표 이미지가 됩니다]</p>']
    top, bot = f['gu'][:2], f['gu'][-2:][::-1]
    B.append('<p>%s</p>' % (V_OPEN[k] % f['mon']))
    B.append('<p>%s.<br>%s.</p>' % (', '.join('%s %s' % (n, pct(v)) for n, v in top),
                                     ', '.join('%s %s' % (n, pct(v)) for n, v in bot)))
    if f['down']:
        lead = '서울 %d개 구 가운데 %d곳이 오르고, %s' % (len(f['gu']), len(f['up']),
                                                 ('%s만 내렸어요.' % '·'.join(n for n, _ in f['down']))
                                                 if len(f['down']) <= 3 else '%d곳이 내렸어요.' % len(f['down']))
    else:
        lead = '서울 %d개 구 가운데 내린 곳이 한 곳도 없었어요.' % len(f['gu'])
    B.append('<p><b>%s</b><br>한국부동산원 %d월 월간 통계입니다.</p>' % (lead, f['mon']))
    B.append('<p>[여기에 이미지 seoul-gu.png 를 넣어 주세요]</p>')

    s = f['seoul']
    B.append('<h3>서울 전체는 얼마나 올랐을까요</h3>')
    prev = ', '.join('%d월 %s' % (int(p[5:7]), pct(v)) for p, v in s[-3:-1])
    B.append('<p>%s.<br>%s에서 %s</p>' % (pct(s[-1][1]), prev, trend_text(s[-3:])))
    if f['over1']:
        B.append('<p>오른 %d개 구 가운데 %d곳은 1%%를 넘게 올랐고요.</p>' % (len(f['up']), len(f['over1'])))

    wo = f['seoul_wo']
    B.append('<h3>매매와 월세는 같은 방향이었을까요</h3>')
    B.append('<p>서울 월세는 %d월 %s, 전세는 %s.<br>%d월 월세는 %s였어요.</p>'
             % (f['mon'], pct(wo[-1][1]), pct(f['seoul_je']), int(wo[0][0][5:7]), pct(wo[0][1])))
    B.append('<p>[여기에 이번 달 해석을 2~3문장으로. 매매와 월세·전세가 같은 방향인지 갈리는지, 그래서 무엇을 시사하는지 쓰고 '
             '"제 판단으로는"으로 견해를 가른다. 마지막 문장은 굵게, 공급으로 묶는다]</p>')

    B.append('<h3>지방은 어땠을까요</h3>')
    B.append('<p>[여기에 이미지 monthly-card.png 를 넣어 주세요]</p>')
    ls = local_streak(f['local'])
    line = '수도권 %s, 지방 %s.' % (pct(f['cap']), pct(f['local'][-1][1]))
    if ls >= 2:
        line += '<br>지방은 %s 한 달에 %.1f%%도 오르지 않았어요.' % (KDAL(ls), LOCAL_LIMIT)
    B.append('<p>%s</p>' % line)
    if f['fall']:
        B.append('<p>%s은 내렸습니다.</p>' % ', '.join('%s(%s)' % (n, pct(v)) for n, v in f['fall'][:3]))

    if f['occ'] or f['perm']:
        B.append('<h3>앞으로 서울 입주 물량은</h3>')
        if f['occ']:
            o = f['occ']
            B.append('<p>%s 서울 입주는 착공으로 추정하면 %s세대.<br>한 분기 적정물량의 %d%%예요.</p>'
                     % (o['q'], '{:,}'.format(o['n']), o['share']))
        if f['perm']:
            p = f['perm']
            B.append('<p>%s 서울 인허가는 %s세대, 최근 12개월 합은 %s세대입니다.<br>인허가가 입주가 되려면 착공하고도 3년이 걸려요.</p>'
                     % (p['label'], MP.num(p['n']), MP.num(p['y12'])))

    B.append('<p>이달의 시도별 매매·전세·인허가·입주·미분양은 아공맵 월간 페이지에 한 장으로 모아 뒀어요.<br>👉 '
             '<a href="%s">이달의 아파트 공급 통계</a></p>' % site_link('/monthly/', 'monthly_%s' % f['ym'].replace('-', '_')))
    B.append('<p>%s</p>' % (V_Q[k] % f['mon']))
    src = '시세는 한국부동산원 전국주택가격동향조사(월간 아파트 매매·전세·월세가격지수 전월 대비, %s)' % f['label']
    if f['perm']:
        src += ', 인허가는 국토교통부 주택건설 인허가실적(%s)' % f['perm']['label']
    if f['occ']:
        src += ', 입주는 국토교통부 준공·착공 실적과 아공맵 입주 추정(착공을 3년 뒤로 밀어 셈)'
    B.append('<p>%s입니다. 해석은 제 개인 의견이며 투자자문이 아닙니다.</p>' % src)
    return ('<!doctype html><meta charset=utf-8><title>%s</title><body style="max-width:700px;margin:20px auto;font-size:16px">\n'
            % _html.escape(title)) + '\n'.join(B) + '\n</body>\n'


def images(f, out):
    """썸네일·서울 구별 막대(오른쪽 = 상승). pillow 만 쓴다."""
    import make_zone_cards as ZC
    from PIL import Image, ImageDraw
    S = 2
    P = lambda v: int(round(v * S))
    F = lambda s, w='Bold': ZC.font(P(s), w)
    BG, INK, MUTE, RED, BLUE, LINE = (250, 250, 248), (17, 17, 17), (112, 112, 108), (224, 32, 27), (30, 90, 170), (214, 214, 208)
    top, bot = f['gu'][0], f['gu'][-1]
    t = Image.new('RGB', (P(1080), P(1080)), BG); d = ImageDraw.Draw(t)
    d.text((P(60), P(80)), '%d월 서울 아파트값' % f['mon'], font=F(84), fill=INK)
    d.text((P(60), P(200)), '상승·하락 엇갈렸습니다' if f['down'] else '25개 구가 모두 올랐습니다', font=F(64), fill=INK)
    d.text((P(60), P(350)), top[0], font=F(60), fill=MUTE)
    d.text((P(60), P(600)), pct(top[1]), font=F(170), fill=RED if top[1] >= 0 else BLUE, anchor='ls')
    d.text((P(60), P(640)), bot[0], font=F(60), fill=MUTE)
    d.text((P(60), P(880)), pct(bot[1]), font=F(170), fill=RED if bot[1] > 0 else BLUE, anchor='ls')
    d.text((P(60), P(1018)), '한국부동산원 월간 아파트 매매 전월 대비', font=F(28, 'Medium'), fill=MUTE, anchor='ls')
    d.text((P(1020), P(1022)), '아공맵', font=F(44), fill=INK, anchor='rs')
    o = t.resize((1080, 1080), Image.LANCZOS); o.save(os.path.join(out, 'thumb.png'))
    o.resize((370, 370), Image.LANCZOS).save(os.path.join(out, 'thumb_370.png'))
    o.resize((104, 104), Image.LANCZOS).save(os.path.join(out, 'thumb_104.png'))
    gu = f['gu']
    H = 120 + 44 * len(gu) + 70
    img = Image.new('RGB', (P(1080), P(H)), BG); d = ImageDraw.Draw(img)
    d.text((P(40), P(36)), '%s 서울 구별 아파트 매매 변동률' % f['label'], font=F(34), fill=INK)
    mx = max(abs(v) for _, v in gu) or 1
    x0, half, y = 560, 380, 110
    d.line([P(x0), P(y - 10), P(x0), P(y + 44 * len(gu))], fill=LINE, width=P(2))
    for n, v in gu:
        w = half * abs(v) / mx
        c = RED if v > 0 else BLUE if v < 0 else MUTE
        d.rectangle([P(x0 if v >= 0 else x0 - w), P(y + 6), P(x0 + w if v >= 0 else x0), P(y + 34)], fill=c)
        d.text((P(x0 - 12 if v >= 0 else x0 - w - 12), P(y + 20)), n, font=F(24, 'Medium'), fill=INK, anchor='rm')
        d.text((P(x0 + w + 10 if v >= 0 else x0 + 10), P(y + 20)), pct(v), font=F(22), fill=c, anchor='lm')
        y += 44
    d.text((P(40), P(H - 34)), '한국부동산원 월간 아파트 매매가격지수 전월 대비(%)', font=F(20, 'Medium'), fill=MUTE)
    img.resize((1080, H), Image.LANCZOS).save(os.path.join(out, 'seoul-gu.png'))
    card = os.path.join(ROOT, MP.SHARE_REL)
    if os.path.exists(card):
        shutil.copy(card, os.path.join(out, 'monthly-card.png'))


def build(out=None, title=None, adv_sts=None, draw=True):
    adv, sts = adv_sts or MP.load()
    f = facts(adv, sts)
    out = out or os.path.join(ROOT, 'drafts', 'monthly-%s' % f['ym'])
    os.makedirs(out, exist_ok=True)
    t = default_title(f) if not title else '[한국부동산원] %d월 월간 아파트가격 동향 | %s' % (f['mon'], title)
    io.open(os.path.join(out, 'body.html'), 'w', encoding='utf-8').write(body(f, t))
    io.open(os.path.join(out, 'title.txt'), 'w', encoding='utf-8').write(t + '\n')
    if draw:
        images(f, out)
    return f, t, out


def main(argv):
    out = argv[argv.index('--out') + 1] if '--out' in argv else None
    title = argv[argv.index('--title') + 1] if '--title' in argv else None
    f, t, out = build(out, title)
    print('월간 초안: %s\n  제목: %s\n  남은 자리: 해석 문단 1, 이미지 4' % (out, t))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
