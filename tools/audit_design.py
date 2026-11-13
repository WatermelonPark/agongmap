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


# 한글에 해로운 조판 둘 — 감사(audit)와 적용(apply_design)이 **같은 눈**으로 본다. 예전엔 두 도구가 정규식을 따로 적어, 감사는
# `text-transform: uppercase`(쌍점 뒤 빈칸)를 세는데 적용은 못 고쳤고, 자간은 둘 다 '.05em' 꼴만 잡아 '0.08em'·'1em'·'.045em'
# 을 놓쳤다(2026-11-13 전수 리뷰).
TRACK_MAX = 0.04                 # 이보다 넓은 자간(em)은 위반 — 한글은 자간을 벌리면 낱말 경계가 흐려진다
TRACK_RE = re.compile(r'letter-spacing:\s*(-?(?:\d+\.?\d*|\.\d+))em')
UPPER_RE = re.compile(r'text-transform:\s*uppercase')


def wide_tracking(css):
    """TRACK_MAX 보다 넓은 자간 선언의 값들(em)."""
    return [float(v) for v in TRACK_RE.findall(css) if float(v) > TRACK_MAX]


def _shadows(css):
    """(선택자, box-shadow 값) — 규칙마다 첫 선언. 규칙을 한 번에 훑고 본문에서 찾는다.

    예전 식(`([^{}]*)\\{[^{}]*?box-shadow:…`)은 그림자가 없는 규칙마다 선택자 자리의 모든 시작점에서 다시 훑어, 중괄호 없는 긴
    글(HTML 본문) 뒤에 규칙이 오는 페이지에서 문서 길이의 제곱으로 느렸다 — 시도 리포트 한 장에 13초, 이 감사를 부르는 시험
    하나가 24초로 게이트에서 셋째로 느렸다(2026-11-13 전수 리뷰).
    """
    out = []
    for sel, body in _rules(css):
        b = re.search(r'box-shadow:\s*([^;}\n]+)', body)
        if b:
            out.append((sel, b.group(1)))
    return out


def _rules(css):
    """(선택자, 본문) — 안쪽에 중괄호가 없는 `선택자{본문}` 덩어리를 차례로. 중괄호 자리만 한 번 훑어 **문서 길이에 비례**한다.

    정규식 `([^{}]*)\\{([^{}]*)\\}` 도 같은 덩어리를 찾지만, 중괄호 없는 긴 글이 `}` 로 끝나는 자리(스크립트·JSON 이 든 페이지)
    에서 시작점마다 다시 훑어 제곱으로 느리다(/cycle/ 한 장에 8초).
    """
    start, open_at = 0, None
    for m in re.finditer(r'[{}]', css):
        i = m.start()
        if css[i] == '{':
            sel_from, open_at = start, i          # 선택자는 직전 중괄호 바로 뒤부터다
        elif open_at is not None:
            yield css[sel_from:open_at], css[open_at + 1:i]
            open_at = None
        start = i + 1


def audit(path):
    """한 페이지(.html) 또는 공유 시트 하나(.css)를 감사한다.

    .css 는 파일 전체가 규칙이라 그대로 본다 — 공유 판정('app.css' 글자)을 끄고, 폰트 칸은 대상이 아니다(페이지가 본다).
    데스크톱 틀 desk.css 는 2026-10-06부터 모든 탭바 페이지가 싣는데 감사가 읽지 않아 이름표의 font-weight:800 이 드러나지
    않았다(전수리뷰 P-7). 페이지 scope 에 합치지 않고 main() 이 한 줄로 따로 감사한다 — 합치면 같은 요소(.bottomnav)의
    그림자 재정의가 페이지마다 두 번 세어져 헛경보가 난다."""
    s = io.open(path, encoding='utf-8').read()
    is_css = path.endswith('.css')
    uses_shared = (not is_css) and 'app.css' in s
    css = SHARED + s if uses_shared else s          # 공유 CSS를 쓰면 함께 판정
    style = ''.join(re.findall(r'<style[^>]*>(.*?)</style>', s, re.S))
    scope = s if is_css else (css if uses_shared else (style or s))

    # 따옴표에서 멈춘다 — 세미콜론 없는 인라인 style="...border-radius:var(--r-touch)" 에서
    # 뒤따르는 마크업 꼬리를 값으로 읽던 오탐(전수리뷰 #89)
    radii = set(re.findall(r'border-radius:\s*([^;}\n"\']+)', scope))
    radii = {r.strip() for r in radii if r.strip() not in RADIUS_OK}
    hexes = {h.lower() for h in re.findall(r'#([0-9a-fA-F]{6})\b', s)}
    warms = sorted(h for h in hexes if warm_neutral(h))

    return {
        'shared': uses_shared,
        'font': is_css or ('Pretendard Variable' in s) or (uses_shared and 'Pretendard Variable' in SHARED),
        'fontlink': 'pretendardvariable' in s.lower(),
        'w800': len(re.findall(r'font-weight:\s*(?:800|900)\b', scope))
                + len(re.findall(r'font-weight="(?:800|900)"', s)),
        'upper': len(UPPER_RE.findall(scope)),
        'track': len(wide_tracking(scope)),
        'radii': sorted(radii),
        'gold': len(re.findall(r'--gold|--accent', scope)),
        'warm': warms,
        # 장식 그림자만 센다 — inset(정렬 열 밑줄·속 빈 고리)과 화면 위에 떠 있는 고정 요소(하단 탭바·데스크톱 위 내비·설치 알림)의
        # 그림자는 '떠 있음'을 알리는 기능이라 뺀다(2026-11-12 디자인 마감 점검: 홈·/cycle/·리포트의 '그림자×4' 가 넷 다 이것이었다).
        'shadow': len([x for sel, x in _shadows(scope)
                       if 'none' not in x and '0 0 0' not in x and 'inset' not in x
                       and not re.search(FLOATING, sel)]),
        'grad': len(re.findall(r'linear-gradient', scope)),
        # 표 정렬: th와 td를 한 규칙으로 묶어 우측 정렬하면 헤더가 값처럼 붙어
        # 열과 어긋나 보인다. thead th 별도 지정이 없으면 위반으로 본다.
        'thalign': bool(re.search(r'th\s*,\s*td[^{]*\{[^{}]*text-align:\s*right', scope))
                   and not re.search(r'thead\s+th[^{]*\{[^{}]*text-align', scope),
    }


# 화면 위에 떠 있는 고정 요소 — 그림자가 기능이다(위 'shadow' 주석).
FLOATING = r'\.bottomnav|\.inst\b'


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
        pages.append(zones[0])          # 시도 리포트는 템플릿(make_sido_pages) 산출물이라 대표 1장
    pages.append('desk.css')            # 모든 탭바 페이지가 싣는 데스크톱 틀(1024px 이상) — 시트 한 줄로 따로 본다(전수리뷰 P-7)

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
        print('\n시도 리포트 %d장은 tools/make_sido_pages.py 산출물 — 템플릿을 고치면 일괄 반영된다.' % len(zones))


if __name__ == '__main__':
    main()
