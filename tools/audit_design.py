# -*- coding: utf-8 -*-
"""디자인 시스템 준수 감사 — 모든 페이지.

2026-07 감사에서 정한 규칙을 페이지마다 기계적으로 검사한다. 사람 눈으로
훑으면 index.html만 보고 끝나는데, 실제로 app.css를 쓰는 건 두 페이지뿐이고
나머지는 자기 CSS를 들고 있어 규칙이 닿지 않는다.

규칙(=agongmap-design-direction 메모리와 동일)
  1 폰트   Pretendard Variable을 실제로 로드하는가
  2 웨이트 800/900 금지 (합성 볼드로 굵기 위계가 소멸)
  3 조판   한글에 uppercase 금지, 양수 자간 .04em 초과 금지
  4 radius 데이터=0 / 터치=3px 두 값
  5 색     --gold/--accent 폐기, 웜 뉴트럴 금지, 데이터 색(빨강/파랑)은 보존
          (예외: 등급 스케일의 앰버 틴트 — 아래 DATA_TINTS 주석 참조)
  6 장식   장식용 그림자·그라디언트 금지

사용: python tools/audit_design.py
"""
import io, os, re, sys, glob

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 불러올 때 작업 디렉터리를 바꾸지 않는다 — apply_design 과 시험이 이 모듈의 상수를 가져다 쓴다.
SHARED = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()

# radius 허용 값 — 데이터=0 / 터치=3px(var(--r-touch)) 두 값, 그리고 모양 자체인 원형(50%).
# apply_design 이 같은 상수를 읽는다: 감사가 허용한 값을 적용 도구가 깨뜨리면 안 된다(전수리뷰 #88).
RADIUS_SHAPE = {'50%'}   # 범례 점 같은 원형 — 두 값 규칙의 대상이 아니다
RADIUS_OK = {'0', '0px', 'var(--r-touch)', '3px'} | RADIUS_SHAPE


# 데이터 스케일 틴트 예외 — 웜 뉴트럴 판정은 '넓은 면의 베이지'를 잡으라고 만든
# 것인데, 5등급 발산 스케일(빨강→앰버→중립→파랑)의 **앰버 단계 배경**은 정의상
# 채도가 낮은 웜 색이라 무슨 값을 골라도 걸린다. 개편이 걷어낸 건 페이지·카드를
# 덮던 베이지이지 62px 배지의 데이터 틴트가 아니므로 이 색만 통과시킨다.
# (짝인 글자색 #b9770e는 채도 171이라 애초에 안 걸린다 — 앰버 자체는 쟁점이 아니다.)
# ⚠️ 여기 새 색을 추가하기 전에: 넓은 면 배경으로 쓰이는 색이면 예외 대상이 아니다.
DATA_TINTS = {'faf3e7'}   # .sc-tier.g2 / .tag.g2 — 등급 '부족'


def warm_neutral(h):
    if h in DATA_TINTS:
        return False
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    chroma = max(r, g, b) - min(r, g, b)
    return chroma <= 32 and (g - b) >= (r - g) and r > b + 4 and 40 <= (0.299*r + 0.587*g + 0.114*b) <= 254


def audit(path):
    s = io.open(path, encoding='utf-8').read()
    uses_shared = 'app.css' in s
    css = SHARED + s if uses_shared else s          # 공유 CSS를 쓰면 함께 판정
    style = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', s, re.S))
    scope = css if uses_shared else (style or s)

    # 따옴표에서 멈춘다 — 세미콜론 없는 인라인 style="...border-radius:var(--r-touch)" 에서
    # 뒤따르는 마크업 꼬리를 값으로 읽던 오탐(전수리뷰 #89)
    radii = set(re.findall(r'border-radius:\s*([^;}\n"\']+)', scope))
    radii = {r.strip() for r in radii if r.strip() not in RADIUS_OK}
    hexes = {h.lower() for h in re.findall(r'#([0-9a-fA-F]{6})\b', s)}
    warms = sorted(h for h in hexes if warm_neutral(h))

    return {
        'shared': uses_shared,
        'font': ('Pretendard Variable' in s) or (uses_shared and 'Pretendard Variable' in SHARED),
        'fontlink': 'pretendardvariable' in s.lower(),
        'w800': len(re.findall(r'font-weight:\s*(?:800|900)\b', scope))
                + len(re.findall(r'font-weight="(?:800|900)"', s)),
        'upper': len(re.findall(r'text-transform:\s*uppercase', scope)),
        'track': len(re.findall(r'letter-spacing:\s*\.(?:0[5-9]|[1-9]\d*)em', scope)),
        'radii': sorted(radii),
        'gold': len(re.findall(r'--gold|--accent', scope)),
        'warm': warms,
        'shadow': len([x for x in re.findall(r'box-shadow:\s*([^;}\n]+)', scope)
                       if 'none' not in x and '0 0 0' not in x]),
        'grad': len(re.findall(r'linear-gradient', scope)),
        # 표 정렬: th와 td를 한 규칙으로 묶어 우측 정렬하면 헤더가 값처럼 붙어
        # 열과 어긋나 보인다. thead th 별도 지정이 없으면 위반으로 본다.
        'thalign': bool(re.search(r'th\s*,\s*td[^{]*\{[^{}]*text-align:\s*right', scope))
                   and not re.search(r'thead\s+th[^{]*\{[^{}]*text-align', scope),
    }


def violations(a):
    """audit() 결과 → 위반 표지 목록. radius 는 규칙 밖 값이 한 종이라도 있으면 위반이다
    (예전 문턱 '>2'는 규칙 밖 값 두 종까지 통과시켰다, 전수리뷰 #89)."""
    flags = []
    nr = len(a['radii'])
    if not a['font']: flags.append('폰트')
    if a['w800']: flags.append('800×%d' % a['w800'])
    if a['upper']: flags.append('UP×%d' % a['upper'])
    if a['track']: flags.append('자간×%d' % a['track'])
    if nr: flags.append('radius%d종(%s)' % (nr, ', '.join(a['radii'])))
    if a['gold']: flags.append('금색×%d' % a['gold'])
    if a['warm']: flags.append('웜색%d종' % len(a['warm']))
    if a['shadow'] > 1: flags.append('그림자×%d' % a['shadow'])
    if a['thalign']: flags.append('표헤더우측정렬')
    return flags


def main():
    os.chdir(ROOT)
    # 검사 대상은 자동 발견한다. 하드코딩 목록이던 시절 investor-test·redev-test·
    # weekly·faq·지표 페이지 2종이 통째로 빠져 있었다(2026-08-01 발견) — 퀴즈 3종은
    # 같은 위반을 갖고 있었는데 burini-test만 잡혔다. 새 페이지를 만들 때마다 목록
    # 추가를 기억해야 하는 구조 자체가 함정이므로 없앤다.
    SKIP = {'docs', 'drafts', 'review', 'share', 'tools', 'icons', 'logs',
            'art_raw', 'node_modules'}   # 공개 페이지가 아닌 디렉터리
    def top(p):
        return p.replace('\\', '/').split('/')[0]
    pages = ['index.html', '404.html']
    pages += sorted(p for p in glob.glob('*/index.html') if top(p) not in SKIP)
    zones = sorted(glob.glob('zone/*/index.html'))
    if zones:
        pages.append(zones[0])          # 생활권 45장은 템플릿 산출물이라 대표 1장

    print('%-26s %-4s %-5s %-4s %-4s %-4s %-7s %-4s %-5s %s'
          % ('페이지', '공유', '폰트', '800', 'UP', '자간', 'radius', '금색', '웜색', '장식'))
    print('-' * 96)
    bad = []
    for p in pages:
        if not os.path.exists(p):
            continue
        a = audit(p)
        nr = len(a['radii'])
        flags = violations(a)
        print('%-26s %-4s %-5s %-4d %-4d %-4d %-7d %-4d %-5d %d'
              % (p[:26], 'O' if a['shared'] else '-', 'O' if a['font'] else 'X',
                 a['w800'], a['upper'], a['track'], nr, a['gold'], len(a['warm']), a['shadow']))
        if flags:
            bad.append((p, flags))

    print('-' * 96)
    if not bad:
        print('위반 없음')
    else:
        print('위반 요약')
        for p, f in bad:
            print('  %-26s %s' % (p[:26], ' · '.join(f)))
    if zones:
        print('\n지역 %d장은 tools/make_sido_pages.py 산출물 — 템플릿을 고치면 일괄 반영된다.' % len(zones))


if __name__ == '__main__':
    main()
