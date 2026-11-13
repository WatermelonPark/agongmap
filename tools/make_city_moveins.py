# -*- coding: utf-8 -*-
"""도시(시군구) 입주물량을 `tools/data/city_moveins.json` 으로 모은다 — 콘텐츠 자리표의 원천(백로그 50).

왜: 사이트 데이터(data-*.json)의 입주물량은 **시도** 단위다. 도시 편·GTX·단지 글은 부천·고양·분당처럼
시군구를 말하는데, 그 숫자를 원고에 손으로 적으면 글이 쓴 날에 멈춘다. 그래서 수집 도구(city_movein)가
뽑는 도시별 물량을 한 파일에 모아 두고, 자리표가 그 파일을 읽는다(대표·총괄 결정 2026-10-27, 1번 안).

무엇을 담나(도시마다)
  sido·start·occ_max   어느 시도에서 뽑았나, 어느 달부터 세나, 부동산원 목록의 끝 달
  as_of                그 도시의 목록을 받은 날(표 각주가 '조사' 로 적는다)
  pop·pop_prd·need     인구와 그 기준월, 한 해 적정 입주량(인구 ÷ 2.5 × 2% — 산식의 정본은 movein_need)
  by_year·by_year_gu   연도별 세대, 연도별 구별 세대
  rows                 단지 목록(입주월·이름·구·세대·자료 출처)

갱신
    python tools/make_city_moveins.py --fetch              원천을 새로 받아 전부 갱신(매일 배치 — 키 필요)
    python tools/make_city_moveins.py --fetch --new-only   파일에 없는 도시만 받는다(원고 발행 — 키 필요)
    python tools/make_city_moveins.py                      캐시(tools/cache/city)만으로 다시 만든다
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
import movein_need as MN       # noqa: E402  (적정 입주량 산식의 정본 — 도시 글 생성기도 같은 파일을 읽는다)
import sido_zones as SZ        # noqa: E402  (시도 목록)
import weekly_moves as WM      # noqa: E402  (시군구 코드 접두 → 시도 정본 SGG_PREFIX)
import home_src as HS          # noqa: E402  (시군구 이름표 SGG_QNAME)
import kst as KST              # noqa: E402

OUT = os.path.join(ROOT, 'tools', 'data', 'city_moveins.json')


def _read(path):
    """있으면 읽고, 없거나 깨졌으면 None. 기존 값을 살릴지 판단하는 데만 쓴다."""
    try:
        return json.loads(io.open(path, encoding='utf-8').read())
    except (IOError, OSError, ValueError):
        return None


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
        # 판정 단위로 접는다(weekly_moves.sgg_zone — 광주·전남 시군구는 통합 단위 '전남광주'). 예전엔 접두 표의 원천 시도 이름
        # ('전남'·'광주')을 그대로 돌려줘 sido_zones.ORDER 에 없는 키가 됐다: 순천·광주 북구 글의 '지역 공급 리포트' 링크와
        # /zone/전남광주/ 글 묶음이 빠지고 허브 지역 칩이 두 줄로 갈렸다(2026-11-13 전수 리뷰 — 첫 광주·전남 원고에서 드러날 결함).
        z = WM.sgg_zone(c)
        if z:
            return z
    return None


def collectable(city, names=None):
    """도시 자료(입주 예정·인구)를 받을 수 있는 이름인가 — **시 이름 하나**('수원'·'남양주'·'청주')만이다.

    구 이름('성남 분당구')이나 이름표의 구분 앞말이 붙은 이름('경기 광주')은 시군구 이름표에는 있지만 수집기가 인구 행을
    찾지 못한다(KOSIS 행은 '성남시'·'광주시'). 예전엔 그런 이름이 원고에 하나 있으면 수집이 KeyError 로 끝나 **모든 도시**의
    갱신이 멈췄고, 검사기는 '기다리면 들어온다'고 했다(2026-11-13 전수 리뷰).
    """
    return bool(city) and ' ' not in city and sido_of(city, names) is not None


def placeholder_cities(text):
    """글자에서 **도시 자료가 필요한 자리표**의 첫 인자를 뽑는다.

    도시 이름이 첫 인자로 오는 종류를 모두 본다(table·v·chart 세 접두 다). 종류의 정본은
    content_tables.CITY_KINDS 다 — 2026-10-29 여기에 chart·need 를 빠뜨려, 그 둘만 쓰는 글의 도시는
    영영 수집되지 않을 뻔했다(율곡 원고가 moveins 도 써서 가려져 있었다).
    """
    import re
    import content_tables as _CT
    pat = re.compile(r'\{\{(?:table|v|chart):(?:%s):([^:}]+)' % '|'.join(_CT.CITY_KINDS))
    return [m.strip() for m in pat.findall(text or '')]


def cities_from_content(root=ROOT):
    """원고가 말하는 도시 → {도시: 시도}. 시도를 모르는 도시는 경고하고 건너뛴다.

    두 곳에서 모은다: 프런트매터 `region`(도시 편)과 본문 자리표의 첫 인자(GTX·단지 편은 region 이 시도이고
    자리표만 도시를 쓴다 — 2026-10-27 첫 19편이 그랬다).
    """
    names = sgg_names(root)
    out, unknown = {}, []
    for sec, slug, path in CM.posts(root):
        try:
            meta, body = CM.read(path, sec, slug)
        except CM.ContentError:
            continue
        cands = [(meta.get('region') or '').strip()]
        cands += placeholder_cities(body + ' ' + (meta.get('summary') or ''))
        for f in meta.get('faq') or []:
            cands += placeholder_cities((f.get('q') or '') + ' ' + (f.get('a') or ''))
        for city in cands:
            if not city or city in out or city in SZ.ORDER or SZ.key_of(city) in SZ.ORDER:
                continue
            sido = sido_of(city, names)
            if sido and collectable(city, names):
                out[city] = sido
            elif city not in unknown:
                unknown.append(city)
    for c in unknown:
        sys.stderr.write('⚠️ 도시 자료를 받을 수 없는 이름이라 건너뛴다: %s (%s)\n'
                         % (c, '시 이름 하나로 적을 것 — 구 이름·구분 앞말은 받지 못한다' if sido_of(c, names)
                            else '홈 시군구 이름표에 없다'))
    return out


def metro_cities(names=None):
    """시도 키이면서 곧 한 도시인 곳(서울·부산·대구·인천·대전·울산·세종) → {이름: 시도 키}. 원고가 없어도 늘 받는다.

    왜 원고를 기다리지 않나. 광역시 글은 단지 목록을 **보고** 써야 하는데(어느 구에 몰리나), 이 수집은 원고가 말하는 도시만
    받아 왔고 시도 키와 같은 이름은 일부러 건너뛰었다(cities_from_content). 키가 없는 세션은 원천을 미리 볼 수 없으니 자료가
    먼저 들어와 있어야 한다(2026-11-13 대표 결정 '광역시 6곳 글'). 이 묶음의 숫자 가운데 글이 쓰는 것은 단지 목록·몰리는 달·
    인구뿐이다 — 적정물량·해마다 입주는 시도 값을 쓴다(content_tables.city 의 주의).

    ⚠️ 이름을 손으로 적지 않는다. 원천 주소의 시도 전체 이름이 하나뿐이고 그것이 '…시'(광역시·특별시·특별자치시)인 키다.
    광주광역시는 판정 단위가 광주·전남 통합이라 빠진다 — 그 도시는 시 이름 원고로 받는다(시도 키가 아니므로 평소 길이다).
    """
    names = names if names is not None else sgg_names()
    out = {}
    for k in SZ.ORDER:
        full = CMV.full_names(k)
        if len(full) == 1 and full[0].endswith('시') and collectable(k, names) and sido_of(k, names) == k:
            out[k] = k
    return out


def cities_wanted(root=ROOT):
    """받을 도시 전부 → {도시: 시도} — 원고가 말하는 도시 + 광역시. 수집(main)과 싣기(adopt)가 같은 목록을 쓴다."""
    out = cities_from_content(root)
    out.update(metro_cities(sgg_names(root)))
    return out


def list_start(today_ym, root=ROOT):
    """목록을 어느 달부터 둘까 — 이번 달, 그러나 **원고가 고정한 가장 이른 창의 1월**보다 늦지 않게.

    원고의 도시 3년 창은 작성 연도 다음 해부터다(content_tables.for_post, 2026-11-13 대표 결정). 예전처럼 늘 이번 달부터 받으면
    2027년 6월에는 2027년 1~5월 단지가 목록에서 빠져, 2026년에 쓴 글의 '2027년 입주' 합계가 달마다 줄었다. 지금(2026-11)은 가장
    이른 창이 2027-01 이라 이번 달이 그대로 시작이다 — 아직 오지 않은 해를 위해 지난 달을 당겨 받지 않는다.
    """
    firsts = []
    for sec, slug, path in CM.posts(root):
        try:
            meta, _body = CM.read(path, sec, slug)
        except CM.ContentError:
            continue
        d = str(meta.get('date') or '')
        if d[:4].isdigit():
            firsts.append(int(d[:4]) + 1)
    if not firsts:
        return today_ym
    return min(today_ym, '%04d-01' % min(firsts))


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
        'sido': sido, 'start': start, 'occ_max': m['occ_max'], 'as_of': KST.today_iso(),
        'pop': pop, 'pop_prd': prd,
        'need': MN.need(pop),
        'need_note': MN.note(),
        'by_year': by_year, 'by_year_gu': by_year_gu,
        'rows': [{'ym': r['ym'], 'name': r['name'], 'gu': r.get('gu') or '', 'n': r['n'],
                  'kind': r.get('kind') or '', 'src': r.get('src') or ''} for r in m['rows']],
    }


def build(cities, start, fetch=False, keep=None):
    """도시마다 숫자를 모아 한 묶음으로. keep 에 있는 도시는 그 값을 그대로 쓴다(받지 않는다).

    keep 은 '새 도시만 받는' 길에 쓴다 — 원고가 올라오는 길(발행 워크플로)은 글이 말하는 도시가 파일에
    없을 때 그 도시만 받아 넣고, 이미 있는 도시의 값은 매일 배치의 주기를 따르게 둔다. 그래야 원고 한 편
    때문에 열세 도시를 다시 받지 않고, 글이 올라온 날에 다른 글의 숫자가 따라 바뀌지도 않는다.
    """
    keep = keep or {}
    out, done = {}, set()
    old = (_read(OUT) or {}).get('cities') or {}
    for city, sido in sorted(cities.items()):
        if city in keep:
            out[city] = keep[city]
            continue
        if fetch and sido not in done:
            CMV.fetch(sido)          # 시도 하나당 한 번만 받는다(원천은 시도 단위 캐시)
            done.add(sido)
        try:
            out[city] = city_facts(city, sido, start)
        except (IOError, OSError):
            raise                    # 원천 캐시가 없다 — main 이 파일을 그대로 두는 갈래다
        except Exception as e:       # noqa: BLE001 — 한 도시의 탈(인구 행 없음·빈 목록)이 나머지 도시의 갱신을 막지 않게 가둔다
            sys.stderr.write('⚠️ 도시 자료를 만들지 못해 건너뛴다: %s (%s: %s)\n' % (city, type(e).__name__, e))
            if city in old:
                out[city] = old[city]          # 지난 값이 있으면 그대로 둔다(글이 갑자기 건너뛰어지지 않게)
    return {'start': start, 'source': '한국부동산원 입주예정물량정보 · 청약홈 분양정보 · KOSIS 주민등록인구',
            'cities': out}


def adopt(fresh_path, out=None, wanted=None):
    """수집 잡이 받아 온 파일(fresh_path)을 저장소 파일에 **도시 단위로** 합쳐 쓴다 → (쓴 도시 수, 지킨 도시 이름들).

    배치의 커밋 잡이 쓴다. 수집 잡은 그 잡이 시작한 때의 원고에 있던 도시만 받는다. 그 사이 새 도시 원고가 병합되면 발행
    워크플로가 그 도시를 저장소 파일에 더해 커밋하는데, 커밋 잡이 수집 잡의 파일을 통째로 덮어쓰면 그 도시가 사라져 방금
    발행된 글이 다음 배치까지 목록에서 빠졌다(2026-11-13 전수 리뷰). 그래서 받아 온 파일에 없는 도시 가운데 **지금 원고가
    쓰는 도시**는 저장소 값을 지킨다. 원고가 더는 쓰지 않는 도시는 받아 온 파일을 따라 빠진다.
    받아 온 파일을 못 읽으면 아무것도 쓰지 않는다(None) — 부르는 쪽이 저장소 파일을 그대로 둔다.
    """
    out = out or OUT
    fresh = _read(fresh_path)
    if not fresh or not isinstance(fresh.get('cities'), dict):
        return None
    have = (_read(out) or {}).get('cities') or {}
    wanted = cities_wanted() if wanted is None else wanted
    kept = sorted(c for c in have if c not in fresh['cities'] and c in wanted)
    for c in kept:
        fresh['cities'][c] = have[c]
    text = json.dumps(fresh, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, 'w', encoding='utf-8', newline='\n').write(text)
    return len(fresh['cities']), kept


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if '--adopt' in argv:
        got = adopt(argv[argv.index('--adopt') + 1])
        if got is None:
            print('city moveins: 받아 온 파일을 읽지 못했다 — 저장소 파일을 그대로 둔다')
            return 1
        print('city moveins: 받아 온 파일을 싣는다(%d개 도시%s)'
              % (got[0], ' · 수집 뒤에 발행된 %s 는 저장소 값을 지킨다' % ', '.join(got[1]) if got[1] else ''))
        return 0
    cities = cities_wanted()
    if not cities:
        print('city moveins: 받을 도시가 없다(원고의 시군구도 광역시도) — 아무것도 바꾸지 않는다')
        return 0
    start = list_start(KST.today_iso()[:7])
    fetch = '--fetch' in argv
    new_only = '--new-only' in argv
    if fetch and not os.environ.get('DATA_GO_KR_KEY'):
        print('city moveins: DATA_GO_KR_KEY 가 없어 수집을 건너뛴다(캐시로 다시 만든다)')
        fetch = False
    keep = {}
    if new_only:
        # 이미 파일에 있는 도시는 그 값을 그대로 둔다. 새 region 이 들어온 글만 받아 넣는 길이다.
        have = (_read(OUT) or {}).get('cities') or {}
        keep = {c: v for c, v in have.items() if c in cities}
        fresh = [c for c in cities if c not in keep]
        if not fresh:
            print('city moveins: 새 도시가 없다 (%d개 그대로)' % len(keep))
            return 0
        print('city moveins: 새 도시 %s 만 받는다(나머지 %d개는 그대로)' % (', '.join(sorted(fresh)), len(keep)))
        start = (_read(OUT) or {}).get('start') or start   # 기준월도 기존 파일을 따른다(섞이지 않게)
    try:
        body = build(cities, start, fetch=fetch, keep=keep)
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
