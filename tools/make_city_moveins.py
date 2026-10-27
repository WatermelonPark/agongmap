# -*- coding: utf-8 -*-
"""도시(시군구) 입주물량을 `tools/data/city_moveins.json` 으로 모은다 — 콘텐츠 자리표의 원천(백로그 50).

왜: 사이트 데이터(data-*.json)의 입주물량은 **시도** 단위다. 도시 편·GTX·단지 글은 부천·고양·분당처럼
시군구를 말하는데, 그 숫자를 원고에 손으로 적으면 글이 쓴 날에 멈춘다. 그래서 수집 도구(city_movein)가
뽑는 도시별 물량을 한 파일에 모아 두고, 자리표가 그 파일을 읽는다(대표·총괄 결정 2026-10-27, 1번 안).

무엇을 담나(도시마다)
  sido·start·occ_max   어느 시도에서 뽑았나, 어느 달부터 세나, 부동산원 목록의 끝 달
  pop·pop_prd·need     인구와 그 기준월, 한 해 적정 입주량(인구 ÷ 2.5 × 2% — make_city_post 와 같은 상수)
  by_year·by_year_gu   연도별 세대, 연도별 구별 세대
  rows                 단지 목록(입주월·이름·구·세대·자료 출처)

갱신
    python tools/make_city_moveins.py --fetch     원천을 새로 받아 갱신(DATA_GO_KR_KEY·KOSIS_API_KEY 필요)
    python tools/make_city_moveins.py             캐시(tools/cache/city)만으로 다시 만든다
도시 목록은 `content/` 원고의 `region` 에서 읽는다 — 글이 늘면 그 도시가 자동으로 들어온다(손 목록 없음).
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import content_md as CM        # noqa: E402  (원고의 region)
import city_movein as CMV      # noqa: E402  (원천 수집·병합의 정본)
import make_city_post as MCP   # noqa: E402  (적정 입주량 상수 PER_HH·RATE)
import sido_zones as SZ        # noqa: E402  (시도 목록)
import weekly_moves as WM      # noqa: E402  (시군구 코드 접두 → 시도 정본 SGG_PREFIX)
import home_src as HS          # noqa: E402  (시군구 이름표 SGG_QNAME)
import kst as KST              # noqa: E402

OUT = os.path.join(ROOT, 'tools', 'data', 'city_moveins.json')


def sgg_names(root=ROOT):
    import re
    m = re.search(r'const SGG_QNAME=(\{.*?\});', HS.home_source(root))
    if not m:
        raise SystemExit('홈에서 시군구 이름표(SGG_QNAME)를 찾지 못했다')
    return json.loads(m.group(1))


def sido_of(city, names=None):
    """도시 이름 → 시도(사이트 키). 시군구 코드의 접두에서 읽는다(weekly_moves.SGG_PREFIX 가 정본).

    ⚠️ 도시→시도 표를 손으로 적지 않는다. 이름표에 그 도시가 없으면 None 을 돌려주고, 부르는 쪽이 알린다.
    """
    names = names if names is not None else sgg_names()
    hit = [c for c, n in names.items() if n == city or n.startswith(city + ' ')]
    for c in hit:
        for pre, sido in WM.SGG_PREFIX.items():
            if c.startswith(pre):
                return SZ.key_of(sido) if SZ.key_of(sido) in SZ.ORDER else sido
    return None


def cities_from_content(root=ROOT):
    """원고가 말하는 도시 → {도시: 시도}. 시도를 모르는 도시는 경고하고 건너뛴다.

    두 곳에서 모은다: 프런트매터 `region`(도시 편)과 본문 자리표의 첫 인자(GTX·단지 편은 region 이 시도이고
    자리표만 도시를 쓴다 — 2026-10-27 첫 19편이 그랬다).
    """
    import re
    names = sgg_names(root)
    out, unknown = {}, []
    want = re.compile(r'\{\{(?:table|v):(?:moveins|share|complexes):([^:}]+)')
    for sec, slug, path in CM.posts(root):
        try:
            meta, body = CM.read(path, sec, slug)
        except CM.ContentError:
            continue
        cands = [(meta.get('region') or '').strip()]
        cands += [m.strip() for m in want.findall(body + ' ' + (meta.get('summary') or ''))]
        for f in meta.get('faq') or []:
            cands += [m.strip() for m in want.findall((f.get('q') or '') + ' ' + (f.get('a') or ''))]
        for city in cands:
            if not city or city in out or city in SZ.ORDER or SZ.key_of(city) in SZ.ORDER:
                continue
            sido = sido_of(city, names)
            if sido:
                out[city] = sido
            elif city not in unknown:
                unknown.append(city)
    for c in unknown:
        sys.stderr.write('⚠️ 시도를 알 수 없는 도시라 건너뛴다: %s (홈 시군구 이름표에 없다)\n' % c)
    return out


def city_facts(city, sido, start):
    """한 도시의 입주물량 묶음. city_movein 의 병합 결과를 그대로 쓰고 숫자만 모은다."""
    raw = CMV.load(sido)
    m = CMV.merge(raw, city, start)
    pop, prd = CMV.population(raw, city)
    by_year, by_year_gu = {}, {}
    for r in m['rows']:
        y = r['ym'][:4]
        by_year[y] = by_year.get(y, 0) + r['n']
        by_year_gu.setdefault(y, {})
        gu = r.get('gu') or ''
        by_year_gu[y][gu] = by_year_gu[y].get(gu, 0) + r['n']
    return {
        'sido': sido, 'start': start, 'occ_max': m['occ_max'],
        'pop': pop, 'pop_prd': prd,
        'need': int(round(pop / MCP.PER_HH * MCP.RATE)),
        'need_note': '인구 ÷ %s × %d%%' % (MCP.PER_HH, int(MCP.RATE * 100)),
        'by_year': by_year, 'by_year_gu': by_year_gu,
        'rows': [{'ym': r['ym'], 'name': r['name'], 'gu': r.get('gu') or '', 'n': r['n'],
                  'kind': r.get('kind') or '', 'src': r.get('src') or ''} for r in m['rows']],
    }


def build(cities, start, fetch=False):
    out, done = {}, set()
    for city, sido in sorted(cities.items()):
        if fetch and sido not in done:
            CMV.fetch(sido)          # 시도 하나당 한 번만 받는다(원천은 시도 단위 캐시)
            done.add(sido)
        out[city] = city_facts(city, sido, start)
    return {'start': start, 'source': '한국부동산원 입주예정물량정보 · 청약홈 분양정보 · KOSIS 주민등록인구',
            'cities': out}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cities = cities_from_content()
    if not cities:
        print('city moveins: 원고에 시군구 region 이 없다 — 아무것도 바꾸지 않는다')
        return 0
    start = KST.today_iso()[:7]
    fetch = '--fetch' in argv
    if fetch and not os.environ.get('DATA_GO_KR_KEY'):
        print('city moveins: DATA_GO_KR_KEY 가 없어 수집을 건너뛴다(캐시로 다시 만든다)')
        fetch = False
    try:
        body = build(cities, start, fetch=fetch)
    except (IOError, OSError) as e:
        # 캐시가 없으면 그 도시는 못 만든다. 기존 파일을 지우지 않고 그대로 둔다 — 옛 값이라도 있는 쪽이 낫다.
        print('city moveins: 원천 캐시를 읽지 못했다(%s) — 파일을 그대로 둔다' % e)
        return 0
    text = json.dumps(body, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
    if old == text:
        print('city moveins: 변경 없음 (%d개 도시)' % len(cities))
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
    print('city moveins: %d개 도시 · %.0fKB' % (len(cities), len(text.encode('utf-8')) / 1024.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
