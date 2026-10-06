# -*- coding: utf-8 -*-
"""주간 시장상황 공유용 PNG 생성 — 블로그·카페·인스타 배포용.

data.js의 ADV.weekly 최신 주차를 읽어 16개 시도 타일 지도를 그린다.
출력: share/weekly-map.png (매주 덮어씀 — /weekly/ og:image로도 사용. 파일 이름은 그대로 두고 /weekly/ 의
      og:image 주소에 카드 머리의 발표일을 ?v= 로 붙인다: make_weekly_page.share_version, 2026-09-27 A7.
      경로의 정본도 make_weekly_page.SHARE_REL 하나다 — og:image 주소가 그 경로를 가리킨다)

사용: python tools/make_weekly_share.py
"""
import io, os, re, json, sys
from PIL import Image, ImageDraw, PngImagePlugin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from make_beginner_cards import noto  # noqa: E402

def _pubdate(basis):
    """조사기준일(월요일 'YYYY-MM-DD') -> 부동산원 공표일(그 주 목요일).

    주간 아파트가격동향은 월요일 조사·목요일 공표라 +3일이면 맞는다. 공휴일이
    끼면 하루씩 밀리는 주가 있는데, 그건 원천 공표 일정이라 우리가 알 수 없다 —
    통상 일정으로 적고, 어긋나도 하루 차이라 신선도 판별에는 지장이 없다.

    ⚠️ 날짜 셈은 /weekly/ 생성기의 share_version 을 그대로 쓴다. 그 값이 /weekly/ og:image 주소의 판(?v=)이라,
       따로 셈하면 카드에 찍힌 발표일과 미리보기 주소의 판이 갈린다(2026-09-27 A7·VIRAL-2, test_weekly_share_version).
    """
    return _MW.share_version(basis)


INK = (22, 32, 58)
PAPER = (246, 244, 238)
MUTED = (111, 106, 92)
LINE = (218, 213, 201)
UP = (224, 86, 74)
DN = (58, 123, 213)

# ⚠️ 좌표는 지리 배치라 손으로 두지만, **담긴 지역 집합**은 모델과 같아야 한다.
# 한 곳이 빠지면 그 지역만 그림에서 사라지는데 이미지는 정상으로 보인다.
# index.html 의 TILE 과 같은 배치를 쓴다 — 두 곳이 어긋나면 같은 지도가 매체마다
# 달라 보인다(2026-09-12 에 홈만 옛 배치로 남아 실제로 그랬다).
TILE = [('전국', 0, 0), ('수도권', 1, 0), ('지방', 2, 0), ('제주', 3, 0),
        ('인천', 0, 1), ('서울', 1, 1), ('경기', 2, 1), ('강원', 3, 1),
        ('충남', 0, 2), ('세종', 1, 2), ('충북', 2, 2), ('경북', 3, 2),
        ('전북', 0, 3), ('대전', 1, 3), ('대구', 2, 3), ('울산', 3, 3),
        ('전남광주', 0, 4), ('경남', 2, 4), ('부산', 3, 4)]

import sido_zones as _SZ  # noqa: E402
import make_weekly_page as _MW  # noqa: E402  (주간 변동률 반올림 정본)
_MISSING = set(_SZ.ORDER) - set(t[0] for t in TILE)
if _MISSING:
    raise SystemExit('TILE에 빠진 지역: %s — 그 지역만 그림에서 사라진다'
                     % ', '.join(sorted(_MISSING)))


def load_weekly():
    c = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    i, j = c.find('/*ADV_DATA_START*/'), c.find('/*ADV_DATA_END*/')
    adv = json.loads(re.match(r'const ADV=(.*);$', c[i + 18:j], re.S).group(1))
    return adv['weekly']


def cell_bg(v, ref=0.4):
    # 색도 **표시값**으로 정한다 — 표시가 0.00인데 원값 부호로 칠하면
    # 같은 '0.00'이 세 색으로 갈린다(사이트 pvSign과 같은 규칙).
    v = pv2r(v)
    if v is None or v == 0:
        return (239, 234, 221)
    a = min(abs(v) / ref, 1.0)
    base = UP if v > 0 else DN
    # PAPER 위에 알파 합성한 값을 직접 계산
    al = 0.14 + 0.72 * a
    return tuple(round(b * al + p * (1 - al)) for b, p in zip(base, PAPER))


def pv2r(v):
    """표시 자릿수(소수 둘째)로 **먼저** 반올림한다 — 부호는 그 결과로 정한다.

    ⚠️ 원값의 부호를 쓰면 -0.0012가 '-0.00'이 되고 잉크까지 파랗게 나간다
    (부산 실측). 값은 0인데 글자와 색이 다른 말을 하는 상태다. 사이트 쪽
    정본(index.html의 pv2/pvSign)이 같은 이유로 이 순서를 쓴다 —
    2026-08-18에 JS만 고치고 이 파일을 놓쳐 카톡·네이버로 나가는 카드에만
    결함이 남아 있었다(2026-09-01 리뷰).
    """
    # 반올림 자체는 /weekly/ 의 정본(make_weekly_page.pv2r, 사이트 JS 와 node 로 대조됨)을 쓴다.
    # 파이썬 round()는 가운데 값에서 사이트 half-up 과 끝자리가 갈렸다(2026-09-23 전체 점검).
    return _MW.pv2r(v)


def fmt(v):
    r = pv2r(v)
    if r is None: return '·'
    return ('%+.2f' % r) if r != 0 else '0.00'


def summary_top3(regs, row):
    """카드 아래 요약 줄의 (상승 상위 3, 하락 상위 3) — [(시도, 원값)].

    /weekly/ 의 상위 3·결론(make_weekly_page.top3, 시도 목록 SIDO)을 그대로 부른다. 예전엔 여기서 따로
    반올림한 표시값(pv2r)으로 정렬하고 동률은 원천 순서, 하락은 그 역순으로 뽑아, 두 지역이 같은 값으로
    반올림되는 주에 원값으로 덜 움직인 곳이 카드에 오르고 더 움직인 곳이 빠졌다. 156주 가운데 43주에서
    카드와 /weekly/ 의 3곳이 갈렸고(2026-09-14 카드 '울산 +0.06', /weekly/ '전북'), 집계 목록도 따로 적었다
    (전수리뷰 #84). 일치는 test_weekly_share_top3 가 본다.
    """
    val = {r: row['ma'][i] for i, r in enumerate(regs) if i < len(row['ma'])}
    return _MW.top3([(z, val[z]) for z in _MW.SIDO if val.get(z) is not None])


def _week_back():
    """--week N — N주 전 회차로 그린다(기본 0 = 최신).

    발행이 밀리면 지난 주차 지도가 없어서 그 회차 글을 채울 수 없다. 실제로
    2주가 비었다(2026-08-30). 기록을 이어 붙이려면 과거 회차도 그릴 수 있어야 한다.

    ⚠️ N>0이면 **share/weekly-map.png를 덮지 않는다.** 그 파일은 /weekly/의
    og:image이자 감시가 신선도를 읽는 곳이라(PNG 메타 agongmap-basis), 옛 주차로
    덮으면 라이브 카드가 과거로 돌아가고 감시가 오경보를 낸다.
    """
    if '--week' not in sys.argv:
        return 0
    i = sys.argv.index('--week')
    try:
        return max(0, int(sys.argv[i + 1]))
    except (IndexError, ValueError):
        raise SystemExit('--week 뒤에 숫자를 줄 것 (0=최신, 1=한 주 전)')


def main():
    W = load_weekly()
    back = _week_back()
    if back >= len(W['rows']):
        raise SystemExit('주간 계열이 %d회차뿐이다 — --week %d 는 없다'
                         % (len(W['rows']), back))
    regs, row = W['regions'], W['rows'][-1 - back]
    val = {r: row['ma'][i] for i, r in enumerate(regs)}
    je = {r: row['je'][i] for i, r in enumerate(regs)}

    IW, IH = _MW.SHARE_SIZE   # 크기 정본 — /weekly/ 공유 버튼의 카카오 피드가 같은 비율로 싣는다(B8)
    img = Image.new('RGB', (IW, IH), PAPER)
    d = ImageDraw.Draw(img)

    # 헤더
    d.text((IW // 2, 66), '이번 주 아파트 시세 지도', font=noto(46), fill=INK, anchor='mm')
    # 조사기준일(월)이 아니라 **발표일(목)**을 적는다(2026-08-06 사용자).
    # 둘 다 사실이지만 발표일 하나로 충분하다 — 사람들이 '몇 월 며칠 발표된
    # 주간시세'로 인식하고, 카드가 멈추면 이 날짜가 안 움직여 신선도까지 드러난다
    # (실제로 2026-07-18 카드가 3주간 '이번 주'로 나갔다).
    # ⚠️ 오늘 날짜를 쓰지 않는다. 배치가 하루 늦게 돌면 발표일이 아닌 날을 발표일로
    # 적게 된다. 데이터의 조사기준일에서 유도해야 언제 구워도 같은 값이 나온다.
    pub = _pubdate(row['p'])   # 아래 PNG 메타(agongmap-pub)에도 같은 값을 심는다
    # 화면 글자는 읽는 꼴 '10/1'(날짜 두 단계, 백로그 36-1). 메타에는 기계가 읽는 ISO 날짜를 그대로 심는다.
    d.text((IW // 2, 122), '%s 발표 · 매매가격 전주 대비 변동률(%%)' % _SZ.day_text(pub),
           font=noto(24), fill=MUTED, anchor='mm')
    # 범례
    d.rounded_rectangle((IW // 2 - 190, 150, IW // 2 - 168, 172), 5, fill=UP)
    d.text((IW // 2 - 158, 161), '상승', font=noto(21), fill=INK, anchor='lm')
    d.rounded_rectangle((IW // 2 + 20, 150, IW // 2 + 42, 172), 5, fill=DN)
    d.text((IW // 2 + 52, 161), '하락', font=noto(21), fill=INK, anchor='lm')

    # 타일 지도 (4열)
    TW, TH, G = 196, 128, 14
    ox = (IW - 4 * TW - 3 * G) // 2
    oy = 205
    for name, x, y in TILE:
        px, py = ox + x * (TW + G), oy + y * (TH + G)
        v = val.get(name)
        d.rounded_rectangle((px, py, px + TW, py + TH), 16, fill=cell_bg(v), outline=LINE, width=2)
        d.text((px + TW // 2, py + 34), name, font=noto(30), fill=INK, anchor='mm')
        # 글자색도 표시값 기준(pv2r) — 원값으로 정하면 '0.00'이 빨강/파랑으로 갈린다
        rv = pv2r(v) or 0
        tc = (143, 35, 24) if rv > 0 else ((18, 60, 92) if rv < 0 else MUTED)
        d.text((px + TW // 2, py + 74), fmt(v), font=noto(31), fill=tc, anchor='mm')
        jv = je.get(name)
        rj = pv2r(jv) or 0
        d.text((px + TW // 2, py + 105), '전세 %s' % fmt(jv), font=noto(18),
               fill=(143, 35, 24) if rj > 0 else ((18, 60, 92) if rj < 0 else MUTED), anchor='mm')

    # 요약 한 줄 (상승·하락 상위) — /weekly/ 의 상위 3과 같은 함수(summary_top3 → make_weekly_page.top3)
    up3, dn3 = summary_top3(regs, row)
    sy = oy + 5 * TH + 4 * G + 34
    if up3:
        d.text((IW // 2, sy), '상승: ' + ' · '.join('%s %s' % (r, fmt(v)) for r, v in up3),
               font=noto(24), fill=(143, 35, 24), anchor='mm')
    if dn3:
        d.text((IW // 2, sy + 36), '하락: ' + ' · '.join('%s %s' % (r, fmt(v)) for r, v in dn3),
               font=noto(24), fill=(18, 60, 92), anchor='mm')

    # 푸터
    d.line((60, IH - 92, IW - 60, IH - 92), fill=LINE, width=2)
    d.text((IW // 2, IH - 62), 'agongmap.co.kr — 서울 구별·전국 시군구 상세 지도', font=noto(26), fill=INK, anchor='mm')
    d.text((IW // 2, IH - 30), '자료: 한국부동산원 R-ONE 전국주택가격동향조사 · 매주 목요일 자동 갱신', font=noto(18), fill=MUTED, anchor='mm')

    # 과거 회차는 라이브 카드를 건드리지 않도록 drafts/로 뺀다(위 docstring 참고).
    # 라이브 카드의 경로는 /weekly/ og:image 주소와 같은 정본(make_weekly_page.SHARE_REL)을 쓴다 — 따로 적으면
    # 한쪽만 바뀌었을 때 미리보기가 없는 파일을 가리킨다(2026-09-27 A7 검토 지적, test_weekly_share_version).
    out = (os.path.join(ROOT, *_MW.SHARE_REL.split('/')) if not back
           else os.path.join(ROOT, 'drafts', 'weekly-map-%s.png' % row['p']))
    # 조사기준일을 PNG 메타(tEXt)에 심는다 — 감시가 라이브 카드의 신선도를 읽을
    # 유일한 방법이다. 그림에서 날짜를 OCR할 수는 없고, 파일 해시로는 '배포가
    # 됐나'만 알지 '언제 주차인가'를 모른다. 2026-07-18 카드가 3주간 라이브에
    # 걸려 있었는데 아무 신호가 없던 이유가 이것이다(2026-08-06).
    meta = PngImagePlugin.PngInfo()
    meta.add_text('agongmap-basis', row['p'])
    # 카드 머리에 찍은 발표일. /weekly/ og:image 주소의 판(?v=)과 같아야 한다 — 시험이 그림을 읽을 수 없어 메타로 본다.
    meta.add_text('agongmap-pub', pub)
    img.save(out, 'PNG', pnginfo=meta)
    print('wrote %s (%s)' % (os.path.relpath(out, ROOT), row['p']))
    if not back:
        # 페이지·홈 데이터는 카드보다 먼저 구워져 지난 판(?v=)을 가리킨다 — 카드가 구워진 지금 판을 맞춘다(전수리뷰 #85).
        # 카드가 실패한 회차엔 여기까지 오지 않으므로 주소가 옛 판 그대로 남아 옛 그림과 같은 판을 말한다.
        for rel in _MW.restamp_share(ROOT):
            print('restamped %s (?v=%s)' % (rel, pub))


if __name__ == '__main__':
    main()
