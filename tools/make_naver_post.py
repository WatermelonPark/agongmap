# -*- coding: utf-8 -*-
"""네이버 블로그 초안 생성 — drafts/naver-<주차>.html

네이버 블로그는 개인 블로그용 글쓰기 API가 없어 완전 자동화가 불가능하다.
그래서 '붙여넣기만 하면 되는 초안'을 매주 만들어 두는 반자동 방식을 쓴다.

만들어지는 초안 2건:
  ① 주간 시세 + 아공맵 해설  — 속보성, 매주 내용이 바뀐다
  ② 지역 심층 리포트         — 매주 한 곳씩 순회(모두 돌면 처음부터)

사용법:
  python tools/make_naver_post.py      # drafts/naver-<주차>.html 생성
  브라우저로 열고 → [복사] 버튼 → 스마트에디터에 붙여넣기 → 이미지 끌어놓기 → 발행

깃발:
  --week N          N주 전 회차의 시세 글만 만든다(지역 편 없음, 0=최신)
  --thumb-msg "첫 줄|*둘째 줄*"
                    지역 편 썸네일 문구를 정해 drafts/thumb-<지역>.png 를 새로 만든다(*…* 줄은 강조색)
  --force           손본 초안(naver-<주차>.html)도 덮는다. 썸네일은 건드리지 않는다
  --force-thumb     문구 없이도 썸네일을 기본 문구로 다시 만든다(--thumb-msg 로 만든 맞춤 썸네일이 덮인다).
                    2026-10-05 전까지는 --force 하나가 초안·썸네일을 같이 덮었다 — 지금은 둘을 따로 준다
  --open            만든 초안을 브라우저로 연다
  --no-shortcut     바탕화면 바로가기를 만들지 않는다(윈도우에서만 만든다)
  -h, --help        이 설명을 찍는다
손본 초안은 덮지 않고 .new.html(그것도 손댔으면 .new2.html …)에 새 초안을 쓴다 — 판별은 draft_edited.

drafts/ 는 .gitignore 대상이다(사이트에 공개될 초안이 아니라 로컬 작업물).

⚠️ 이 생성기는 **사이트와 같은 말을 해야 한다.** 블로그가 사이트에 없는 산식을
설명하면, "계산법을 전부 공개한다"는 아공맵의 신뢰 근거가 그 자리에서 무너진다.
그래서 지평·등급 라벨·지역 수를 문자로 박지 않고 sido_zones의 상수를 읽는다.
2026-08-06 시도 재편(생활권 44곳 → 시도 20곳, 인허가 4년 → 착공 3년)으로 한 번
전면 재작성했다. 다음에 모델이 바뀌면 '설명 구조'가 그대로인지부터 확인할 것.
"""
import io, os, re, sys, json, base64, datetime, hashlib, subprocess
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sido_pages as M  # noqa: E402  (load 재사용)
import sido_zones as SZ      # noqa: E402  (zone_order·GRADE_LABS·상수)
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import make_weekly_page as MW  # noqa: E402  (주간 변동률 반올림 정본 pv2 — 사이트 pv2 와 같다)
import weekly_moves as WM  # noqa: E402  (방향 표지·시군구 순위 이동 정본 — 홈 마케팅 검수 B7)
import close_published_issues as CP  # noqa: E402  (RSS·카테고리 이름의 정본)
import make_indicator_pages as I  # noqa: E402  (전세가율 기준월 정본 jeonse_ref_index — /jeonse-ratio/·/cycle/ 와 같은 달)
import rebuild_cycle_analysis as RC  # noqa: E402  (지수 기준 단절 판정의 정본 index_breaks — 4편·사이클 도구와 같은 규칙)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'drafts')
STATE = os.path.join(OUT, '.rotation.json')


def write_draft(path, html):
    """초안을 **다 만든 뒤에** 쓴다. 호출하는 쪽은 render()의 결과를 넘긴다.

    ⚠️ 쓰기 모드로 연 파일 객체에 곧바로 render 결과를 write 하는 한 줄짜리로 쓰지 말 것
    (test_draft_not_truncated 가 그 모양을 막는다). 파일이 먼저 열려 0바이트가 된 뒤에
    render 가 돈다 — 생성 가드(SystemExit)나 예외가 나면 사람이 채운 해석 문단이 든 기존 초안이
    빈 파일로 남는다. drafts/ 는 gitignore 라 되돌릴 데가 없다(2026-09-18 리뷰에서 3편 가드로 재현:
    18,140바이트 → 0). 임시 파일에 쓰고 바꿔치기하므로 쓰는 도중 죽어도 기존 파일은 그대로다.
    """
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    os.replace(tmp, path)


# ---------------------------------------------------------- 손본 초안 지키기
# drafts/ 는 gitignore 라 덮어쓰면 되돌릴 데가 없다(2026-08-14 주간 초안, 2026-09-18 이론 3편). 그래서 생성기가 쓴
# 초안 끝에 본문의 지문(sha256)을 남긴다. 다음에 돌릴 때 지문이 맞으면 생성기가 쓴 그대로이니 덮고, 어긋나면 사람이
# 고친 것이니 덮지 않는다. 지문이 없는 옛 초안은 자리 표시자로 판별한다(draft_edited).
DRAFT_STAMP = '<!--agongmap-draft sha256=%s-->'
_STAMP_RX = re.compile(r'\n?<!--agongmap-draft sha256=([0-9a-f]{64})-->\s*\Z')


def stamp_draft(html):
    """render 결과 끝에 지문을 붙인다. write_draft 에 넘기기 직전에 부른다."""
    return html + '\n' + DRAFT_STAMP % hashlib.sha256(html.encode('utf-8')).hexdigest() + '\n'


def draft_edited(old, fresh, placeholders=(), strict=False):
    """기존 초안 old 를 사람이 손댔나. fresh 는 지금 새로 만든 초안(지문을 붙이기 전 render 결과).

    - old 가 fresh 와 같으면 손대지 않았다.
    - 지문이 있으면 지문으로만 판별한다: 맞으면 생성기가 쓴 그대로, 어긋나면 손댔다(자리 표시자를 남긴 채 제목이나
      다른 문단만 고친 것도 잡는다).
    - 지문이 없으면(지문 이전에 만든 초안) fresh 에 있는 자리 표시자가 **하나라도** old 에 없으면 손댔다. 예전엔 주간 해석
      자리(INTERP)만 봐서, 지역 편 전망(OUTLOOK)만 채운 초안이 덮였다(2026-10-05 리뷰 D1). strict 면 본문이 fresh 와
      다르기만 해도(공백 차이는 빼고) 손댄 것으로 본다 — 이론 1~4편처럼 자리 표시자가 없는 초안(리뷰 D2).
    """
    m = _STAMP_RX.search(old)
    if m:
        body = old[:m.start()]
        return hashlib.sha256(body.encode('utf-8')).hexdigest() != m.group(1)
    norm = lambda t: re.sub(r'\s+', '', t)
    if norm(old) == norm(fresh):
        return False
    if any(ph[:20] in fresh and ph[:20] not in old for ph in placeholders):
        return True
    return bool(strict)


SIDE_MAX = 9


def side_path(path, fresh, placeholders=(), strict=False):
    """손본 초안 옆에 새 초안을 쓸 자리: .new.html, 그것도 손댔으면 .new2.html … 손대지 않았거나 없는 첫 자리.
    SIDE_MAX 자리가 모두 손본 초안이면 None — 호출하는 쪽이 멈춘다(어느 것도 덮지 않는다)."""
    for i in range(1, SIDE_MAX + 1):
        alt = path[:-5] + ('.new.html' if i == 1 else '.new%d.html' % i)
        if not os.path.exists(alt):
            return alt
        if not draft_edited(io.open(alt, encoding='utf-8').read(), fresh, placeholders, strict):
            return alt
    return None


# 바탕화면 바로가기(2026-09-27 대표 요청: "발행할 문서 html은 앞으로 바탕화면에 바로가기 아이콘").
# 초안 종류마다 이름이 고정된 바로가기 하나를 두고, 초안을 만들 때마다 가장 최근 초안을 가리키게 바꾼다.
# 회차마다 새 아이콘을 만들면 바탕화면에 쌓인다. 목요일 밤 예약 작업이 만든 초안도 같은 아이콘으로 열린다.
# 윈도우에서만 돈다(작업 스케줄러·로컬 세션). 실패해도 초안 생성은 계속된다 — 아이콘은 편의일 뿐이다.
# 시험 중에는 만들지 않는다(pytest 가 PYTEST_CURRENT_TEST 를 켠다). 임시 폴더 초안을 가리키는 아이콘이 생긴다.
SHORTCUTS = {'naver': '아공맵 블로그 초안 (주간·지역)', 'theory': '아공맵 블로그 초안 (사이클)'}
_LNK_PS = ("$d=[Environment]::GetFolderPath('Desktop');"
           "$f=Join-Path $d ($env:AGM_LNK_NAME+'.lnk');"
           "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($f);"
           "$s.TargetPath=$env:AGM_LNK_TARGET;$s.Description=$env:AGM_LNK_NAME;$s.Save();"
           "Write-Output $f")


def desktop_shortcut(path, name, run=None):
    """path 를 여는 바탕화면 바로가기 name.lnk 를 만들거나 새 대상으로 바꾼다. 만든 파일 경로 또는 None."""
    if os.name != 'nt' or '--no-shortcut' in sys.argv:
        return None
    if run is None:
        if 'PYTEST_CURRENT_TEST' in os.environ:
            return None
        run = subprocess.run
    # 이름·경로는 환경 변수로 넘긴다 — 명령 문자열에 한글·공백·따옴표를 끼워 넣으면 인용이 깨진다.
    env = dict(os.environ, AGM_LNK_NAME=name, AGM_LNK_TARGET=os.path.abspath(path))
    try:
        r = run(['powershell', '-NoProfile', '-NonInteractive', '-Command', _LNK_PS],
                env=env, capture_output=True, timeout=30)
    except Exception as e:
        print('  ⚠ 바탕화면 바로가기 생략 — %s' % e)
        return None
    if r.returncode != 0:
        print('  ⚠ 바탕화면 바로가기 생략 — PowerShell 종료 코드 %s' % r.returncode)
        return None
    return (r.stdout or b'').decode('utf-8', 'replace').strip() or name
SITE = 'https://www.agongmap.co.kr'


def site_link(path, campaign):
    """초안이 싣는 사이트 링크(href 값, & 는 &amp;) — 블로그 UTM 은 반드시 '#' **앞**(쿼리)에 둔다.

    2026-09-27 홈 마케팅 검수 A1: 주간 글의 '지도에서 직접 찾아보기'가 `/#stats-market?utm_…`로 나가,
    브라우저에는 쿼리가 비고 전부 해시가 됐다. GA 는 weekly_map 캠페인을 못 읽었고 홈 라우터도 화면을 못
    찾아 3년 공급 첫 화면에 떨어졌다(09-11·09-17 발행본). 발행 글은 고치지 않으므로 옛 모양은 사이트 머리
    스크립트가 받아 주고, 새 초안은 여기서 처음부터 `/?utm_…#stats-market`으로 만든다. 이 파일이 만드는
    초안의 사이트 링크는 이 함수를 거친다. 이론 초안(make_theory_post)은 해시 없는 링크를 손으로 적는데,
    어느 쪽이든 '?'가 '#' 앞에 오는지는 test_home_entry 의 초안 링크 검사가 본다.
    """
    base, hash_, frag = path.partition('#')
    return ('%s%s?utm_source=naver_blog&amp;utm_medium=social&amp;utm_campaign=%s%s%s'
            % (SITE, base, campaign, hash_, frag))


# 숫자·이스케이프는 사이트가 쓰는 정본을 그대로 가져다 쓴다. 여기 사본을 두면
# 발행 글과 사이트가 조용히 갈린다(2026-08-15 리뷰에서 둘 다 실제로 갈려 있었다):
#  · 옛 num은 int(round(...)) — 파이썬 기본은 은행가 반올림이라 정확히 x.5인 칸에서
#    사이트(M.rnd, half-up)와 1씩 어긋났다.
#  · 옛 esc는 큰따옴표를 안 막았는데 data-tag="%s"·value="%s" 속성 안에서 쓰였다.
#    값에 "가 섞이는 순간 속성이 그 자리에서 닫혀 태그 칩이 깨진다.
num = M.num
esc = M.esc
umx = M.umx        # 미분양 배수 표기도 정본을 쓴다 — 사이트와 자릿수가 갈리면 안 된다


def pct(v):
    """주간 변동률 표기. 사이트 pv2(절대값 half-up, 부호는 반올림 결과로)와 같은 값을 낸다.

    예전 '%+.2f'는 파이썬 반올림이라 사이트와 끝자리가 갈렸다 — -0.075 가 블로그 -0.07%,
    사이트 -0.08%(data.js 주간 칸 13,706개 중 58개, 2026-09-23 전체 점검). /weekly/ 가 백로그 15에서
    고친 방식 그대로 make_weekly_page.pv2 를 쓴다. 그 함수가 사이트 JS 와 같은지는
    test_weekly_page 가 node 로 본다.
    """
    if v is None:
        return '—'
    return MW.pv2(v) + '%'


def fixed2(v):
    """JS Number.prototype.toFixed(2) 와 같은 문자열. 홈이 toFixed(2)로 찍는 값을 블로그에 옮길 때 쓴다.

    toFixed 는 double 의 정확한 값에서 가까운 쪽으로, 정확히 가운데면 절대값이 큰 쪽으로 자른다.
    '%.2f'는 가운데에서 짝수 쪽이라 3.125 같은 값에서 갈린다(홈 3.13, '%.2f' 3.12).
    """
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(v).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def rent_yield(adv, sts, region='전국'):
    """월세수익률 = 전세가율(최신 비결측) / 100 × 전월세전환율. 홈 버블밴드(renderBubbleSec)의
    `lo=jr/100*cv` 와 같은 산식·같은 입력이다. 값이 없으면 None.

    예전 블로그는 문장에 '전세가율 × 전월세전환율'이라 써 놓고 전환율(5.37%)을 그대로 찍었다.
    같은 주 홈은 3.71%였고, 대출금리 4.48% 대비 판정이 정반대로 나갔다(2026-09-23 전체 점검).
    홈 산식과의 일치는 test_post_site_parity 가 node 로 홈 코드를 돌려 본다.
    """
    B = adv.get('bubble') or {}
    cv = (B.get('conv') or {}).get(region)
    # ⚠️ 전세가율 달은 홈 버블밴드(renderBubbleSec 의 latest — 지역마다 최신 비결측)와 같게 둔다. 이 절의 정본 화면은
    # 홈이다. 홈이 기준월 규칙(jeonse_ref_index)으로 바뀌면 여기도 _jeonse_at_ref 로 바꾼다(전수리뷰 #106, 홈 쪽 미결).
    s = (((sts or {}).get('전세가율') or {}).get('series') or {}).get(region) or []
    jr = next((v for v in reversed(s) if v is not None), None)
    if cv is None or jr is None:
        return None
    return jr / 100 * cv


def _jeonse_at_ref(sts, region='전국'):
    """전세가율 (기준월 값, 전월 값, 기준월) — 기준월은 사이트 정본 I.jeonse_ref_index(JEONSE_NEED 가 다 찬 마지막 달).

    예전엔 지역마다 '마지막 비결측 값'을 읽었다. 새 달이 일부 지역만 채워진 회차에 /jeonse-ratio/·/cycle/ 은 직전
    완비 달(2026.08)을 말하는데 블로그는 부분 달(2026.09) 값을 발행했다(전수리뷰 #106·#24 블로그 쪽). 없으면 None.
    """
    j = (sts or {}).get('전세가율') or {}
    if not j.get('dates') or not j.get('series'):
        return None
    try:
        i = I.jeonse_ref_index(j, I.JEONSE_NEED)
    except RuntimeError:
        return None
    s = j['series'].get(region) or []
    k = SZ.month_back(j['dates'], i, 1)
    if i >= len(s) or s[i] is None:
        return None
    prv = s[k] if k is not None and k < len(s) else None
    return s[i], prv, j['dates'][i]


def kdate(p):
    """'2026-07-13' -> '7월 13일' (블로그 본문에 ISO 날짜는 어색하다)."""
    y, m, d = p.split('-')
    return '%d월 %d일' % (int(m), int(d))


def batchim(w):
    """마지막 글자에 받침이 있나. 조사 선택은 전부 이걸로 갈린다."""
    c = ord(w[-1])
    return 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 != 0


def iga(w):
    """이/가 조사. 옛 지역명은 전부 '권'으로 끝나 '이' 고정이 맞았지만,
    시도명은 제주·경기처럼 받침 없는 이름이 있다('제주이' 오류, 2026-08-14 실측)."""
    return '이' if batchim(w) else '가'


def eunneun(w):
    """은/는 조사. iga()와 같은 사고가 한 군데 더 있었다 — ②는 16개 시도를
    순회하는데 '%s은'이 박여 있어 대구·광주·경기·제주에서 '대구은'이 된다.
    다음 순번이 대구라 발행 전에 잡았다(2026-08-15)."""
    return '은' if batchim(w) else '는'


# ---------------------------------------------------------------- 순회 상태
# 검색 수요가 실증된 지역을 앞에 세운다(2026-08-14 네이버 키워드도구 실측).
# 우리 주제(미분양·입주물량·공급·시세·전망) 월간 검색량 합계:
#   대구 6,580 · 부산 4,540 · 서울 3,200 · 경기 1,455 · 세종 1,390
#   광주 410 · 울산 35 · 인천 25 · 나머지 9개 시도 0
# 대구·부산이 압도적인 건 미분양이 실제로 심각해서다 — 그 지역 미분양 검색이
# 월 1천~3천이고, 우리는 그 수치와 "미분양이 쌓여 착공이 멈췄다"는 해석을
# 함께 갖고 있다. 순부족 절대값 순서로 돌면 이 지역들이 한참 뒤로 밀린다.
PRIORITY = ('서울', '대구', '부산', '경기', '세종', '전남광주')


ZONE_CAT = CP.KIND_TO_CATEGORY['지역 공급']   # 손으로 복제하면 한쪽만 고쳐질 때 발행 편수가 0 으로 세어진다(리뷰 09-18)


def _zone_of_title(title, names):
    """제목이 어느 지역 편인지. '<지역>(시|도)? 아파트|부동산' 이 **가장 앞에** 나오는 지역을 고른다.

    같은 길이 이름을 set 순회 순서로 맞추면 '부산 … 서울 아파트' 같은 제목이 실행마다 다른 지역으로
    세어졌고(PYTHONHASHSEED 에 좌우), '세종시 아파트' 처럼 접미사가 붙으면 못 셌다(리뷰 09-18 19번).
    '부동산'도 받는다: 제목 교대 실험 B안('2026 세종시 부동산 전망, …', 2026-09-27)은 '아파트'가
    앞머리에 없어서, 받지 않으면 발행한 세종 편을 못 세고 다음 회차에 세종을 또 고른다.
    검색 표기(SEARCH_NAME, 예: '광주·전남')로 쓴 제목도 그 지역으로 센다(2026-09-29).
    같은 카테고리에 싣는 도시 입주물량 편('2027년 서울 아파트 입주물량, …')은 지역 편이 아니다(CP.is_city_post).
    """
    if CP.is_city_post(title):
        return None
    best = None
    for nm in names:
        for form in dict.fromkeys((nm, SEARCH_NAME.get(nm, nm))):
            m = re.search(r'(?<![가-힣])%s(?:시|도|특별자치시|특별자치도)? (?:아파트|부동산)' % re.escape(form),
                          title or '')
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), nm)
    return best[1] if best else None


def _published_zone_posts(names):
    """발행된 지역 편을 {지역: {글 주소, ...}}로. RSS를 못 읽으면 None."""
    try:
        import close_published_issues as CP
        posts = CP.fetch_posts()
    except Exception:
        return None
    if not posts:
        # 빈 목록은 '아직 아무것도 안 냈다'가 아니라 '못 읽었다'로 본다 — 빈 피드로 1번 지역부터 다시
        # 시작하면 이미 낸 글을 또 만든다(리뷰 09-18 19번). 호출자가 저장해 둔 순회 기록으로 고른다.
        return None
    out = {}
    for p in posts:
        if p.get('cat') != ZONE_CAT or not p.get('url'):
            continue
        nm = _zone_of_title(p.get('title'), names)
        if nm:
            out.setdefault(nm, set()).add(p['url'])
    return out


def pick_zone(rows, published=None):
    """아직 안 다룬 지역 중 하나를 고른다 — PRIORITY 먼저, 그다음 |순부족| 순.

    **'다뤘다'의 기준은 실제 발행이다**(2026-09-17). 예전엔 초안을 저장할 때마다 순회
    기록을 한 칸 넘겼는데, 주간 글만 쓰려고 돌려도 지역 하나가 소비됐다 — 지역 편은
    격주라 매주 도는 생성기와 박자가 안 맞는다. 9/17에 세종이 그렇게 소비돼 손으로
    되돌렸다. 이제 블로그 RSS에서 발행된 지역 편을 세고, 파일(STATE)은 RSS에서
    밀려난 옛 글을 기억하는 **캐시**로만 쓴다(RSS는 최근 글만 준다). 지금 고른 지역은
    기록하지 않는다 — 발행되면 다음 실행 때 RSS가 알려 준다.

    한 바퀴 돌면 다음 바퀴: 지역마다 발행 편수를 세어, 가장 적게 나간 편수(lap)보다
    많이 나간 지역을 '이번 바퀴에 다뤘다'고 본다.
    ⚠️ 2026-08-06 재편으로 지역 이름이 전부 바뀌었다(생활권 → 시도). 현재 목록에 없는
    이름은 버린다.
    """
    names = {r['z'] for r in rows}
    seen = {}
    if os.path.exists(STATE):
        try:
            st = json.load(io.open(STATE, encoding='utf-8'))
            seen = {k: set(v) for k, v in (st.get('posts') or {}).items()}
            # 옛 형식 {"done": [...]} — 주소를 모르니 자리만 하나씩 채운다.
            for nm in st.get('done', []):
                seen.setdefault(nm, set()).add('legacy:' + nm)
        except Exception:
            seen = {}
    if published is None:
        published = _published_zone_posts(names)
    if published is None:
        print('  ⚠ 발행 목록(RSS)을 못 읽어 저장해 둔 순회 기록으로 고른다.')
        published = {}
    for nm, urls in published.items():
        if urls:                       # 실제 주소를 알게 되면 옛 자리표는 버린다
            seen[nm] = {u for u in seen.get(nm, set()) if not u.startswith('legacy:')} | urls
    seen = {k: v for k, v in seen.items() if k in names}

    def rank(r):
        # PRIORITY에 있으면 그 순서대로 앞에, 없으면 순부족 큰 순으로 뒤에
        try:
            return (0, PRIORITY.index(r['z']), 0)
        except ValueError:
            return (1, 0, -abs(r['tot']))
    pool = sorted(rows, key=rank)
    lap = min(len(seen.get(r['z'], ())) for r in pool)
    done = [r['z'] for r in pool if len(seen.get(r['z'], ())) > lap]
    pick = next(r for r in pool if r['z'] not in done)
    # seq 는 **누적 회차**다(전수리뷰 #80). 바퀴마다 1부터 다시 세면 두 바퀴째 서울 편이 1바퀴 서울 편과 같은
    # 캠페인(zone_deep_1)·같은 유도문·같은 제목 실험 팔을 받는다. 한 바퀴째 값은 예전(len(done)+1)과 같다 —
    # 이미 나간 글의 캠페인·팔과 어긋나지 않는다. 바퀴 안 순번은 (seq-1) % total + 1 이다.
    seq = lap * len(pool) + len(done) + 1

    def commit():
        if not os.path.isdir(OUT):
            os.makedirs(OUT)
        io.open(STATE, 'w', encoding='utf-8').write(json.dumps(
            {'posts': {k: sorted(v) for k, v in seen.items()}}, ensure_ascii=False))
    return pick, seq, len(pool), commit


# ---------------------------------------------------------- 로테이션·해석 자리
# 해석은 기계가 못 쓴다. 이 자리를 비워 둔 채 발행하면 시세 숫자만 나열한 글이
# 되어 블로그 톤(분석)에서 떨어진다. 눈에 띄라고 대괄호로 남긴다.
OUTLOOK_PLACEHOLDER = (
    '[여기에 전망을 3~5문장으로. 위 숫자를 다시 읊지 말고 <b>그래서 어떻게 될 것</b>'
    '인지 쓸 것.<br>'
    '① <b>결론을 첫 문장에.</b> "제 판단으로는, 이 지역은 지금 ○○ 구간입니다"처럼 '
    '한 줄로 못 박고 시작한다. 읽고 나서 방향이 안 읽히면 안 쓴 것과 같다.<br>'
    '② 근거는 그다음. 앞에 깔린 숫자(공급 비율·미분양·금리) 중 <b>가장 센 것 하나</b>를 '
    '고른다. 본문에 없는 시계열(전세가율 추이·착공 추이)을 파서 쓰면 더 세다.<br>'
    '③ <b>오른다/내린다를 말한다.</b> 시점만 유보하고, 그 유보는 마지막 한 문장으로 '
    '끝낸다. "정하지 못하는 건 시점입니다" 같은 말로 문단을 닫으면 변호사 글이 된다 — '
    '2026-09-01 사용자: "술에 술 탄 듯 물에 물 탄 듯 쓰면 어쩌자는 겨". 방향을 못 '
    '박은 전망은 안 쓴 것과 같다.]')


def _cd_change(sts):
    """CD 91일물의 1년 변화 — 전망 문단에 깔아 줄 재료.

    금리는 공급 순환을 덮어쓰는 외부 힘이라(/cycle/ 실측), 공급 얘기만 하고
    금리를 빼면 반쪽이다. 같은 달끼리 비교한다 — 월별 등락이 커서 인접 월과
    견주면 방향이 뒤집힌다.
    """
    r = (sts.get('금리') or {})
    ser = (r.get('series') or {}).get('CD(91일)') or []
    dates = r.get('dates') or []
    p = [(d, v) for d, v in zip(dates, ser) if v is not None]
    if len(p) < 13:
        return None
    cur = p[-1]
    try:
        y, m = int(cur[0][:4]) - 1, cur[0][5:7]
    except ValueError:
        return None
    prev = next((x for x in p if x[0][:4] == str(y) and x[0][5:7] == m), None)
    if not prev:
        return None
    return ('%.2f' % prev[1], '%.2f' % cur[1], '%+.2f' % (cur[1] - prev[1]))


def _tile_counts():
    """홈 시군구 지도가 실제로 그리는 타일 수. (서울 외 시군구, 서울 구).

    2026-09-12 리뷰: 발행 문구가 '187개 시군구와 서울 25개 구'라고 말했는데 실제
    타일은 182개(서울 25 + 그 외 157)였다. 사이트 어디에도 187이라는 수가 없어
    대조할 데가 없었고, 4주마다 한 번씩 그대로 발행됐다.

    타일은 `SGG_QNAME`에 이름이 있는 코드만 그려진다(index.html의 그리기 조건이
    `SGG_QNAME[c] && …`). 그래서 그 목록이 곧 타일 수다.
    """
    q = _sgg_names()
    seoul = sum(1 for n in q.values() if n.startswith('서울 '))
    return len(q) - seoul, seoul


def _sgg_names():
    """홈 시군구 이름표(SGG_QNAME) — 지도 타일·TOP 10·/weekly/ 시군구 표가 같은 표를 쓴다."""
    import json
    import re
    h = HS.home_source()
    m = re.search(r'SGG_QNAME\s*=\s*(\{.*?\})\s*;', h, re.S)
    if not m:
        raise RuntimeError('index.html에서 SGG_QNAME을 찾지 못했다 — 타일 수를 못 맞춘다')
    return json.loads(m.group(1))


def weekly_moves_sentences(W):
    """'지난주와 무엇이 달라졌나'(홈 마케팅 검수 B7·RET-5) — /weekly/ 표와 **같은 함수**(weekly_moves)의 결과를
    문장으로 옮긴다. 재료만 깔고 해석은 사람이 쓴다. (방향 문단, 순위 이동 문장) — 없으면 빈 문자열.

    순위 이동은 이 초안에 붙이는 상승 TOP 10 이미지(홈 통계 탭 표 캡처, home-app.js sggRanks)와 같은 규칙이다 —
    일치는 test_weekly_moves 가 node 로 본다.
    """
    # 이번 주에 새로 생긴 변화만 쓴다(weekly_moves.news). 오래된 연속을 매주 다시 쓰면 숫자만 1씩 느는 같은 문장이
    # 회차마다 나간다(CLAUDE.md '회차 간 반복 금지') — 긴 연속은 이정표(8·13·26·52주 …)에 닿은 주에만 쓴다.
    nw = WM.news(WM.moves(W) or {})
    lab = {WM.UP: '상승', WM.DN: '하락'}
    parts = []
    if nw['turned']:
        parts.append('지난주와 방향이 바뀐 곳은 %s입니다.'
                     % ' · '.join('<b>%s</b>(%s)' % (z, WM.TXT_TURN[k]) for z, k in nw['turned']))
    if nw['entered']:
        parts.append('새로 %d주 연속 흐름에 들어선 곳은 %s입니다.'
                     % (WM.STREAK_MIN, ' · '.join('%s(%s)' % (z, lab[k]) for z, k in nw['entered'])))
    if nw['milestone']:
        parts.append('이번 주로 %s을 채웠습니다.'
                     % ' · '.join('%s%s %s' % (z, eunneun(z), WM.TXT_STREAK[k] % n) for z, k, n in nw['milestone']))
    para = ('<p>%s</p>' % ' '.join(parts)) if parts else ''
    rank = ''
    S = W.get('sgg') or {}
    if len(S.get('rows') or []) > 1:
        q = _sgg_names()
        top = [(q[c], d) for c, _, r, d in WM.rank_moves(S, q)[:10] if d is not None and d > 0]
        if top:
            name, d = max(top, key=lambda x: x[1])   # 같은 폭이면 순위가 앞선 곳
            rank = ('<p>상승 TOP 10 가운데 지난주보다 순위가 가장 많이 뛴 곳은 <b>%s</b>(▲%d위)입니다.</p>' % (name, d))
    return para, rank


SGG_N, SEOUL_N = _tile_counts()


# 사이트 /cycle/ 고리②(전세→매매) 검증 결과의 정본. 숫자를 박지 않고 읽어 온다.
#
# ⚠️ 정본이 여기 있는 이유: make_theory_post 가 이 모듈을 import 하므로(CSS·복사 UI
# 재사용) 반대 방향으로 가져오면 순환 참조가 된다. 2026-09-12에 실제로 그렇게 돼서
# `python tools/make_naver_post.py` 가 ImportError 로 죽었다 — 테스트는 모듈을
# __main__ 으로 돌리지 않아 210개가 전부 통과하면서도 발행 도구가 못 돌았다.
def cycle_d():
    """`/cycle/` 의 정본 const D 전체(sync·link1_new·prose …). 이론 초안도 숫자를 여기서 읽는다(전수리뷰 #76·#77)."""
    p = os.path.join(ROOT, 'cycle', 'index.html')
    m = re.search(r'const D\s*=\s*(\{.*?\});',
                  io.open(p, encoding='utf-8').read(), re.S)
    if not m:
        raise RuntimeError('/cycle/ 에서 D 블록을 찾지 못했다 — 곳 수를 못 맞춘다')
    return json.loads(m.group(1))


def _cycle_sync():
    """`/cycle/` 의 const D 에서 sync 목록을 읽는다. [{region, corr, sudo}, …]

    2026-09-12 광주·전남 통합으로 15곳 → 14곳이 되고 값도 재산정됐다
    (평균 0.71→0.73, 서울 0.58→0.55). 사이트와 블로그가 다른 숫자를 말하면
    '계산법을 공개한다'는 근거가 그 자리에서 무너진다.
    """
    return sorted(cycle_d()['sync'], key=lambda r: -r['corr'])


CYCLE_SYNC = _cycle_sync()
CYCLE_SYNC_N = len(CYCLE_SYNC)


INTERP_PLACEHOLDER = (
    '[이번 주 데이터에서 눈에 띈 것을 2~4문장으로. 위 표의 숫자를 다시 읊지 말고 '
    '왜 그런지, 무엇을 시사하는지 쓸 것. 예: 특정 지역만 튀는 이유, 매매-전세 '
    '방향이 갈리는 곳, 몇 주째 이어지는 흐름.]')

# 사람이 채우는 자리 전부. 손본 초안 판별(draft_edited)이 이 가운데 새 초안에 있는 것을 하나라도 잃은 기존 초안을
# '손댔다'로 본다 — 자리를 새로 만들면 여기에 넣는다.
DRAFT_PLACEHOLDERS = (INTERP_PLACEHOLDER, OUTLOOK_PLACEHOLDER)

# ⑤ 더 보기 — 4주에 걸쳐 사이트의 다른 코너를 하나씩 소개한다.
MORE_ROTATION = [
    dict(h='이번 주 시세를 지도로 보려면',
         desc='시군구 %d곳과 서울 %d개 구의 매매·전세 변동률을 지도 한 장으로 '
              '볼 수 있습니다. 상승은 빨강, 하락은 파랑입니다.' % (SGG_N, SEOUL_N),
         # 시군구 지도는 홈 시세 화면에 있다. /weekly/ 에는 시도 격자·시군구 표만 있다(전수리뷰 #83).
         path='/#stats-market', label='시군구 지도 보기'),
    dict(h='우리 동네 공급은 어떤가',
         desc='시도별로 앞으로 3년간 들어올 물량과 필요한 양을 비교한 리포트가 있습니다. 지역을 골라 들어가 보세요.',
         path='/zone/', label='전국 시도별 공급'),
    dict(h='집값은 왜 도는가',
         # 곳 수는 사이트의 고리 검증 대상과 같아야 한다(CYCLE_SYNC_N).
         # 통합으로 15 → 14가 됐는데 이 문장만 15로 남아 4주마다 발행됐다.
         desc='공급 → 전세 → 매매 → 다시 공급으로 이어지는 순환의 6개 고리를, '
              '%d개 시도 20년 데이터로 검증한 리포트입니다.' % CYCLE_SYNC_N,
         path='/cycle/', label='「집값은 돌고 돈다」 읽기'),
    # 테스트가 셋인데 부린이 하나만 소개하고 있었다. "문항마다 국가 통계에
    # 근거한 해설"은 설명서 문구라 빼고, 종류를 보여준다(2026-09-07 사용자).
    # links가 있으면 desc 뒤에 링크를 여러 줄로 단다 — path/label 한 쌍으로는
    # 셋을 못 보여준다.
    dict(h='내 부동산 감각은 몇 점일까',
         desc='테스트가 세 가지입니다. 각 10문항, 5분이면 끝납니다.',
         links=[('/burini-test/', '부린이 테스트 — 내 감각은 몇 점인가'),
                ('/investor-test/', '투자자 테스트 — 통념을 뒤집을 준비가 됐나'),
                ('/redev-test/', '재건축·재개발 테스트 — 이 사업, 사업성이 있나')]),
]


# 4주 로테이션의 기준 월요일(ISO 2026-W01 첫날). 2026 년 안에서는 옛 식((ISO 주차-1) % 4)과 같은 순서를 낸다.
ROT_ANCHOR = datetime.date(2025, 12, 29)


def rot_index(p):
    """발표주차 기준 4주 로테이션 인덱스. 날짜에서 뽑으므로 상태 파일이 필요 없고,
    주간 발행을 건너뛰어도 순서가 어긋나지 않는다.

    ⚠️ ISO 주차(`isocalendar()[1]`)로 세지 않는다. 53주인 해(2026·2032·2037)에는 W53(2026-12-28)과 다음 해
    W01(2027-01-04)이 둘 다 0 이 되어 같은 '이번 주의 지표'가 두 주 연달아 나간다(회차 간 반복 금지 위반,
    2026-09-26 데이터 감사). write-reminder.yml 처럼 고정 월요일에서 지난 주 수로 센다."""
    y, m, d = (int(x) for x in p.split('-'))
    return ((datetime.date(y, m, d) - ROT_ANCHOR).days // 7) % 4


def _series_last(sts, key, region='전국'):
    """(최신값, 직전값, 기준월) — 데이터가 없으면 (None, None, None).

    ⚠️ 값과 날짜를 **같은 원소에서** 가져온다. 예전엔 값은 결측을 걸러낸 목록의
    끝에서, 날짜는 원본 목록의 끝에서 뽑았다. 꼬리가 None이면 지난달 값에 이번 달
    날짜가 붙어 "전국 미분양은 6만 7천 호입니다(2026.07 기준)"처럼 **발행 글이 틀린
    시점을 말한다.** 새 달 열은 merge_basic이 전 지역 None으로 먼저 만들고 받아온
    지역만 채우므로, 전국이 아직 안 온 달에 실제로 이 모양이 된다.
    """
    d = sts.get(key) or {}
    s = (d.get('series') or {}).get(region) or []
    dates = d.get('dates') or []
    idx = [i for i, v in enumerate(s) if v is not None and i < len(dates)]
    if len(idx) < 2 or not dates:
        return None, None, None
    i = idx[-1]
    # 직전값은 '결측을 건너뛴 앞 값'이 아니라 **바로 전 달** 값이다. 문장이 '전월'이라고 말하기 때문이다.
    # 보류된 달(미분양 2026.07)이 비면 두 달 전 값을 전월로 적게 된다(2026-09-26 데이터 감사 #17).
    # 전 달이 없으면 '전월 대비'를 쓸 수 없으므로 값이 하나뿐일 때처럼 섹션째 생략한다.
    j = SZ.month_back(dates, i, 1)
    if j is None or j >= len(s) or s[j] is None:
        return None, None, None
    return s[i], s[j], dates[i]


def extra_section(adv, sts, rot):
    """④ 이번 주의 다른 지표 — 4주 로테이션. 데이터가 없으면 섹션째 생략한다."""
    if rot == 0:
        # 기준월은 /jeonse-ratio/ 와 같은 정본 규칙(_jeonse_at_ref). 전월이 없으면 '전월 대비'를 못 쓰므로 생략한다.
        cur, prv, when = _jeonse_at_ref(sts) or (None, None, None)
        if cur is None or prv is None:
            return ''
        mv = '올랐습니다' if cur > prv else ('내렸습니다' if cur < prv else '보합입니다')
        return ('<h3>이번 주의 지표 — 전세가율</h3>'
                '<p>전국 전세가율은 <b>%.1f%%</b>입니다(%s 기준, 전월 %.1f%%에서 %s). '
                '매매가 대비 전세가의 비율로, 높아질수록 사는 값과 빌리는 값의 차이가 '
                '좁아져 매매 전환 압력이 커집니다.</p>' % (cur, when, prv, mv))
    if rot == 1:
        cur, prv, when = _series_last(sts, '미분양')
        if cur is None:
            return ''
        diff = cur - prv
        mv = ('%s세대 늘었습니다' % num(diff)) if diff > 0 else (
             ('%s세대 줄었습니다' % num(-diff)) if diff < 0 else '변동이 없습니다')
        return ('<h3>이번 주의 지표 — 미분양</h3>'
                '<p>전국 미분양은 <b>%s세대</b>입니다(%s 기준, 전월 대비 %s). '
                '미분양은 공급이 수요를 넘어선 흔적이라, 쌓이면 그 지역 분양가와 '
                '입주장 전세가에 먼저 반영됩니다.</p>' % (num(cur), when, mv))
    if rot == 2:
        # 값과 판정은 홈 버블밴드와 같은 산식·같은 경계를 쓴다(rent_yield 주석).
        # 홈은 loan<=lo 를 '매수 신호권'(이자가 임대수익보다 싸다)으로 본다.
        B = adv.get('bubble') or {}
        lo = rent_yield(adv, sts, '전국')
        loan = (B.get('loan') or {}).get('v')
        loan_p = (B.get('loan') or {}).get('p')
        if lo is None or loan is None:
            return ''
        judge = ('월세로 사는 비용이 대출 이자보다 비싼 상태' if loan <= lo
                 else '대출 이자가 월세보다 비싼 상태')
        return ('<h3>이번 주의 지표 — 월세수익률 vs 대출금리</h3>'
                '<p>전국 월세수익률(전세가율 × 전월세전환율)은 연 <b>%s%%</b>, '
                '주택담보대출 금리는 <b>%s%%</b>%s입니다. 지금은 %s입니다. '
                '어차피 어딘가에는 살아야 하므로, 이 차이는 실거주 매수를 '
                '검토할지 판단하는 출발점이 됩니다.</p>'
                # 금리는 월 단위로 늦게 나온다 — 몇 월 값인지 붙인다(전수리뷰 묶음 F 제안)
                % (fixed2(lo), fixed2(loan), ('(%s 기준)' % esc(loan_p)) if loan_p else '', judge))
    # ⚠️ ADV.aged30은 쓰지 않는다 — 2026-08-06 시도 재편 전의 생활권 키('서울권',
    # '경기남부권' …)가 그대로 남아 있어서, 사이트엔 없는 지역명이 블로그로 나간다
    # (2026-08-11 실측으로 확인). STATS['노후주택30년']이 시도 키로 살아 있다.
    N = sts.get('노후주택30년') or {}
    ser = N.get('series') or {}
    dates = N.get('dates') or []
    # 기준 해는 **모든 시도가 채워진 마지막 열**이고, 순위는 그 열 값끼리만 매긴다(전수리뷰 #114). 예전엔 지역마다
    # 결측을 거른 마지막 값을 쓰고 이름표는 dates[-1] 을 달아, 새 해 열이 한 지역만 채워진 회차에 작년 값들을
    # 올해 기준으로 묶었다(_series_last 가 막은 것과 같은 모양 — 병합은 새 열을 전 지역 None 으로 만든다).
    sido = {k: v or [] for k, v in ser.items() if k not in SZ.AGG}    # 전국·수도권·지방 집계는 순위에서 뺀다
    i = next((j for j in range(len(dates) - 1, -1, -1)
              if sido and all(j < len(v) and v[j] is not None for v in sido.values())), None)
    if i is None:
        return ''
    pairs = [(k, v[i]) for k, v in sido.items()]
    tops = sorted(pairs, key=lambda x: -x[1])[:3]
    return ('<h3>이번 주의 지표 — 30년 넘은 아파트</h3>'
            '<p>준공 30년이 지난 아파트가 가장 많은 곳은 %s입니다(%s년 기준). '
            '노후 재고는 재건축·재개발 압력이자 앞으로 헐릴 집이기도 해서, '
            '많이 쌓인 지역일수록 실제 공급이 통계보다 빠듯해질 수 있습니다.</p>'
            % (' · '.join('<b>%s %s세대</b>' % (esc(k), num(v)) for k, v in tops), dates[i]))


# ---------------------------------------------------------------- 초안 ①
# 주간 글 '주요 지역 변동률' 표에 싣는 지역. 순서는 싣는 순간 SZ.DISPLAY_ORDER 를 따르고, 이름이 모델에 있는지는
# test_weekly_table_names_are_model_names 가 본다(전수리뷰 #82).
WEEKLY_TABLE = frozenset(('전국', '수도권', '서울', '경기', '인천', '부산', '대구', '대전', '전남광주', '울산'))


def draft_weekly(adv, sts, shot=True):
    """shot=False 면 사이트 화면을 뜨지 않는다 — 지난 회차(--week N)는 운영 사이트가 지금 주 화면만 보여 주므로
    그 캡처를 붙이면 과거 글에 이번 주 지도·TOP 10 이 실린다(전수리뷰 #74)."""
    sgg = top10 = None
    sggerr = '--no-shot 로 건너뜀' if shot else '지난 회차라 사이트 캡처(지금 주 화면)를 건너뜀'
    if shot and '--no-shot' not in sys.argv:
        sgg, top10, sggerr = capture_weekly_map()
    if sgg:
        # 한 장짜리 지도는 맨 아래 범례("위 = 매매 · 아래 = 전세")까지 같이 잘려
        # 들어온다. 반 장일 때 필요했던 캡션 안내는 그래서 뺐다.
        sggnote = ('지도·표를 자동으로 떴습니다.<br>'
                   '<b>%s</b> → [전국 시군구 지도]<br>' % sgg
                   + ('<b>%s</b> → [상승·하락 TOP10]<br>' % top10 if top10 else '')
                   + '네이버는 외부 이미지 주소를 그대로 쓰지 않으므로 파일을 '
                   '직접 올려야 합니다.')
    else:
        sggnote = ('시군구 지도 없음 — %s. 본문의 자리 표시자를 지우거나 '
                   '%s/#stats-market 을 직접 캡처해 넣으세요.' % (sggerr, SITE))

    W = adv['weekly']
    p = W['rows'][-1]['p']
    rot = rot_index(p)
    extra_html = extra_section(adv, sts, rot)
    more = MORE_ROTATION[rot]
    reg, last = W['regions'], W['rows'][-1]
    prev = W['rows'][-2] if len(W['rows']) > 1 else None
    val = dict(zip(reg, zip(last['ma'], last['je'])))

    def g(name, i=0):
        return val.get(name, (None, None))[i]

    seoul = g('서울'), g('서울', 1)
    nat = g('전국'), g('전국', 1)

    # 시도만 추려 상승·하락 정렬(전국·수도권·지방 같은 집계 항목 제외).
    # 집계 이름은 SZ.AGG가 정본이다 — 여기에 사본을 두면 정본이 늘 때 이 글만
    # 옛 목록으로 남는다.
    # 상위·하위 3은 /weekly/ 와 **같은 함수**(MW.top3, 같은 시도 목록 MW.SIDO·같은 순서)로 뽑는다(전수리뷰 #84).
    # 예전 사본은 원천 순서로 늘어선 val 에서 정렬해, 반올림 전 값이 같은 두 곳의 순서(하락 쪽)가 /weekly/ 와 갈릴 수
    # 있었다. 부호는 표시값(pv2r)으로 가른다 — 원값 0.001 을 '오른 곳 0.00%'로 쓰지 않게(/weekly/ 와 같은 규칙).
    sido = [(k, val[k][0]) for k in MW.SIDO if k in val and val[k][0] is not None]
    up, dn = MW.top3(sido)

    # 서울 구별
    gu = []
    S = W.get('seoul') or {}
    if S.get('rows'):
        sr = S['rows'][-1]
        # ⚠️ `x[1] or -9`로 쓰면 안 된다 — 보합(0.00%)도 거짓값이라 하락한 구보다
        # 뒤로 밀린다. 결측(None)만 맨 뒤로 보내는 게 의도다.
        gu = MW.top3([(g, v) for g, v in zip(S['regions'], sr['ma']) if v is not None])[0]   # /weekly/ 서울 구별과 같은 함수

    # 검색어를 맨 앞에 둔다. 2026-08-14 네이버 검색 실측에서 이 자리를 차지한
    # 블로그 글이 '한국부동산원 주간동향｜8월 1주 전국 아파트 시세 분석' 형태였고,
    # 웹문서 1위도 부동산원 공식 '주간아파트가격동향'이다. 출처명이 검색어로
    # 같이 쓰인다는 뜻이라, 본문에만 있던 '한국부동산원'을 제목으로 끌어올렸다.
    #
    # 2026-09-12 형식 교체(사용자 결정): 앞은 이 장르의 관례, 뒤는 우리 결론절.
    # 실측으로 지금 매주 글을 올리는 블로그들이 전부 "[라벨] 기관명 주간…동향
    # (주차)" 꼴이었고, 그 자리를 오래 지키던 블로그(주간시장동향 47건)는 다섯 달
    # 째 멈춰 상위 10에서 사라졌다. 형식은 그쪽 고유물이 아니라 관례라 따라도
    # 위험이 없다. 다만 라벨만 있는 제목은 클릭이 안 된다 — 우리가 숫자 제목으로
    # 결론절 제목에 졌던 8/14 실측 그대로다. 그래서 '|' 뒤 결론절은 지킨다.
    # 주차는 관례대로 서수("둘째 주"). '아파트 시세'(수요가 확인된 말)는 제목에서
    # 빠지지만 본문 첫 문장과 태그에 남는다.
    #
    # 2026-09-17 라벨 교체(사용자 결정): '부동산 주간시장동향' → 부동산원 보도자료
    # 공식 이름 '주간 아파트가격 동향'. 옛 라벨에는 '아파트'가 없었고, 네이버
    # 자동완성 실측에서 '주간시장동향'은 제안어가 0개인 반면 '주간아파트'를 치면
    # 첫 제안이 '주간아파트가격동향'이었다(검색량 절대값은 우리 키로 못 잰다 —
    # 데이터랩·검색광고 API 모두 인증 불가). 사람이 실제로 치는 말로 라벨을 맞춘다.
    # 주차 서수는 weekly_release.week_label 하나에서 만든다 — /weekly/ title·머리줄과 같은 이름(홈 마케팅 검수 B4·SEO-4).
    # 라벨 말도 /weekly/ title 과 같은 상수(MW.TITLE_KW)다.
    title = '[한국부동산원] %s(%s) | 서울 %s 전국 %s' % (
        MW.TITLE_KW, MW.WR.week_label(p), pct(seoul[0]), pct(nat[0]))

    rowsHtml = ''
    for k in [z for z in SZ.DISPLAY_ORDER if z in WEEKLY_TABLE]:
        if k not in val:
            # 조용히 건너뛰지 않는다 — 지역 이름이 바뀌면(2026-09-10 광주·전남 통합) 그 행만 표에서 사라졌다(전수리뷰 #82)
            print('  ⚠ 주간 표 %s 행 생략 — 주간 계열에 그 이름이 없다(모델 지역 이름이 바뀌었는지 볼 것)' % k)
            continue
        m, j = val[k]
        if m is None:
            continue
        rowsHtml += ('<tr><td>%s</td><td style="text-align:right">%s</td>'
                     '<td style="text-align:right">%s</td></tr>') % (k, pct(m), pct(j))

    lead = ('한국부동산원이 발표한 <b>%s 기준</b> 주간 아파트 가격 동향입니다. '
            '전국 매매가는 전주 대비 <b>%s</b>, 서울은 <b>%s</b> 움직였습니다.'
            ) % (kdate(p), pct(nat[0]), pct(seoul[0]))

    body = []
    body.append('<p>%s</p>' % lead)
    body.append('<h3>주요 지역 변동률</h3>')
    body.append('<p>전주 대비 아파트 매매·전세 변동률입니다.</p>')
    body.append('<table border="1" cellspacing="0" cellpadding="6"><thead>'
                '<tr><th>지역</th><th>매매</th><th>전세</th></tr></thead>'
                '<tbody>%s</tbody></table>' % rowsHtml)
    # ⚠️ up/dn은 상위·하위 3개일 뿐 부호를 보장하지 않는다. 전 지역이 내린 주에
    # "가장 많이 오른 곳은 세종 -0.01%"라고 쓰면, 숫자가 검증 가능하다는 게 이
    # 채널의 유일한 밑천인데 그 자리에서 무너진다. 부호로 걸러 문장을 만든다.
    sent = []
    if up:
        sent.append('이번 주 가장 많이 오른 곳은 %s입니다.'
                    % ' · '.join('<b>%s %s</b>' % (k, pct(v)) for k, v in up))
    if dn:
        sent.append('%s%s는 내렸습니다.'
                    % ('반대로 ' if up else '',
                       ' · '.join('%s %s' % (k, pct(v)) for k, v in dn)))
    if not sent:
        sent.append('이번 주는 전 지역이 보합입니다.')
    body.append('<p>%s</p>' % ' '.join(sent))
    if gu:
        body.append('<p>서울 안에서는 %s 순으로 올랐습니다.</p>' %
                    ' · '.join('<b>%s %s</b>' % (k, pct(v)) for k, v in gu))
    # 지난주와 무엇이 달라졌나(B7) — 표지의 정본(weekly_moves)
    moves_p, rank_p = weekly_moves_sentences(W)
    if moves_p:
        body.append(moves_p)
    # 시도 타일 지도(share/weekly-map.png)를 넣던 자리다. 뺐다 — 그 값들은 바로
    # 위 표에 그대로 있어 중복이고, 시군구 지도가 훨씬 값어치 있다(2026-08-30
    # 사용자). 시도 지도는 /weekly/ og:image로는 계속 쓴다.
    #
    # 두 장으로 가르는 이유: 시군구 전부가 한 장에 들어가면 네이버 모바일에서
    # 타일 글씨가 안 읽힌다.
    body.append('<p>가장 많이 오르고 내린 곳을 순위로 보면 이렇습니다. '
                '맨 오른쪽은 <b>지난주 순위에서 몇 계단 움직였는지</b>입니다.</p>')
    body.append('<p>[여기에 상승·하락 TOP10 이미지를 넣어 주세요]</p>')
    if rank_p:
        body.append(rank_p)
    body.append('<p>시군구로 내려가 보면 같은 권역 안에서도 갈립니다.</p>')
    # 지도는 한 장으로 간다(2026-09-07 사용자: 둘로 잘리니 보기 안 좋다). 원래
    # 모바일 가독성 때문에 둘로 나눴던 것인데(3ea4781), 잘린 자리가 더 거슬린다.
    body.append('<p>[여기에 전국 시군구 지도 이미지를 넣어 주세요]</p>')
    body.append('<p>타일마다 위가 매매, 아래가 전세입니다. 붉을수록 오르고 '
                '푸를수록 내린 곳입니다.<br>👉 '
                '<a href="%s">지도에서 직접 찾아보기</a></p>'
                % site_link('/#stats-market', 'weekly_map'))

    # ── ② 해석 자리. 기계가 채울 수 없는 부분이라 비워 두고, 재료(위 표·순위)만
    # 앞에 깔아 둔다. 블로그 이웃들이 기대하는 건 숫자 나열이 아니라 해석이므로
    # 이 자리를 비운 채 발행하면 안 된다.
    body.append('<h3>이번 주 눈에 띈 것</h3>')
    body.append('<p>%s</p>' % INTERP_PLACEHOLDER)

    # ── ③ '공급으로 보면'(시도 순위표)은 뺐다(2026-09-07 사용자). 공급 판정은
    # 착공 실적으로 매기는데 그건 월 단위로 움직여서, 주간 글에 넣으면 매주
    # 제주가 1위인 같은 표가 나간다. 시의성이 없는 절이 매주 반복되는 셈이었다.
    # 공급 이야기는 격주 지역 편이 진다 — 주간 글은 시세와 그 주의 지표만 다룬다.

    # ── ④ 다른 지표(4주 로테이션). 매주 같은 각도만 보여주면 사이트의 폭이 안 드러난다.
    if extra_html:
        body.append(extra_html)

    # ── ⑤ 더 보기(4주 로테이션). 매번 같은 링크를 붙이면 무시당하므로 4주에 걸쳐
    # 사이트의 다른 코너를 하나씩 소개한다.
    body.append('<h3>%s</h3>' % more['h'])
    links = more.get('links') or [(more['path'], more['label'])]
    body.append('<p>%s%s</p>' % (
        more['desc'],
        ''.join('<br>👉 <a href="%s">%s</a>' % (site_link(path, 'weekly'), label)
                for path, label in links)))
    # ⚠️ 면책을 '권유하지 않습니다'로 쓰지 않는다. 본문이 방향을 분명히
    # 말하는데 말미에서 그걸 부인하면 글이 스스로를 무른다. 대신 **사실과
    # 견해를 가르고 책임 소재를 밝힌다** — 이 편이 더 정직하고 더 강하다.
    body.append('<p><i>※ 숫자는 한국부동산원·국토교통부·KOSIS·한국은행 공개 '
                '데이터를 가공한 것이고, <b>판단과 전망은 글쓴이 개인의 견해</b>'
                '입니다. 투자 결정과 그 결과는 읽는 분의 몫입니다.</i></p>')

    # 13개에서 5개로 줄였다(2026-08-14). 태그는 순위를 가르는 신호가 아니다 —
    # C-Rank(채널 주제 집중도)와 D.I.A.+(문서 품질)가 가른다. 개수보다 일관성이
    # 낫다: 매주 같은 5개를 쓰면 주제가 또렷해지고, 네이버 자동완성이 떠서
    # 입력도 빨라진다. 매주 13개를 손으로 넣는 건 그 값을 못 한다(사용자 지적).
    # 제목 라벨을 태그로도 받는다(2026-09-12 도입, 09-17 라벨 교체로 따라 바꿈) —
    # 제목에서 빠진 '아파트 시세'는 태그가 지키고, 제목 라벨은 태그에도
    # 있어야 검색 의도 둘을 다 덮는다. '부동산데이터'는 검색 의도가 없는 말이라 뺐다.
    # 2026-09-17 사용자 데이터랩 실측(월별 상대지수): 주간아파트가격동향 53~100,
    # 주간아파트동향 3~18, 주간아파트시세 0~3. 거의 안 찾는 '주간아파트시세'를
    # 두 번째로 많이 찾는 '주간아파트동향'으로 바꿨다. '아파트시세'는 '주간'이 없는
    # 일반 검색어라 남긴다.
    tags = ['주간아파트가격동향', '주간아파트동향', '아파트시세', '집값전망', '아공맵']
    return dict(title=title, body='\n'.join(body), tags=tags, kw='주간아파트가격동향',
                img=(sgg or None), imgnote=sggnote,
                # 본문 자리 표시자 순서대로(TOP10 → 지도). img_gallery 가 초안 안에 싣는다.
                imgs=[(top10, '상승·하락 TOP10'), (sgg, '전국 시군구 지도')])


# ---------------------------------------------------------------- 초안 ②
# 글 끝 유도문 — 회차마다 문장도 목적지도 바꾼다.
#
# 2026-09-01 사용자: "아예 심플하게 글 마지막에 짧게 아공맵 접속 유도를 넣는 걸로
# 하자, 그 문장 마저도 매번 똑같으면 안 되구". 본문 중간의 브랜드 소개를 전부
# 걷어낸 대신 남은 **단 하나의 문**이다. 같은 문장이 16주 내내 나가면 그 줄은
# 광고로 학습돼 통째로 건너뛰어진다.
#
# ⚠️ seq(회차 번호)로 고른다. 난수를 쓰면 연달아 같은 게 걸릴 수 있고, 초안을
# 다시 만들 때마다 문장이 바뀌어 검토한 것과 발행본이 어긋난다. 회차가 같으면
# 문장도 같다 — 이게 재현 가능한 유일한 방식이다.
#
# 목적지는 **항상 그 지역 리포트**다(2026-09-27 대표 승인, 조회수 조사 LINK-1). 예전에는
# 목적지도 9곳으로 돌렸는데("같은 곳으로만 보내면 이미 가 본 사람에게 두 번째부터 무의미"),
# 지역 편 독자의 약 90%가 홈피드로 처음 온 사람이라 그 전제가 맞지 않았다. 그 결과 경기 편은
# 사이트 링크가 글 끝 /cycle/ 하나뿐이었다. 지금은 문장만 돌리고, 문장마다 같은 리포트의
# 다른 칸(식·분기표·판정표·미분양)을 가리킨다. 캠페인에 회차를 붙여(zone_deep_<seq>) GA 에서
# 글마다 클릭을 가른다.
# ⚠️ 연도·곳 수를 박지 않는다 — 리포트가 보여주는 구간과 시도 수는 모델이 바뀌면 따라 바뀐다.
ZONE_CTA = (
    '이 숫자를 어떻게 냈는지, 적정물량 기준선부터 분기별 물량까지 리포트에 열어 뒀습니다.',
    '%s의 분기별 물량은 리포트에 그대로 있습니다.',
    '다른 시도와 나란히 놓고 보면 %s의 자리가 더 잘 보입니다. 판정표는 리포트 아래쪽에 있습니다.',
    '미분양이 얼마나 쌓였는지, 인허가가 얼마나 들어오는지도 리포트에서 함께 보입니다.',
    '%s에 그동안 얼마나 지었고 앞으로 얼마나 들어오는지 한 화면에 놓았습니다.',
)


# 시리즈 링크 — 직전 지역 편 1개 + 최신 주간 시세 1개.
#
# 2026-09-01 사용자 제안. 걷어낸 브랜드 소개("16개 시도를 같은 기준으로 보고
# 있습니다")가 하려던 일을 자랑 대신 **증거**로 한다 — 지난 글이 실제로 거기
# 있으면 시리즈라는 말이 필요 없다.
#
# 조합을 이렇게 고른 이유: 직전 지역 편은 시리즈 순서를 보이고, 주간 시세는
# **항상 최신 글**이라 링크가 저절로 신선하다. 둘 다 고정 목록이 아니라 회차가
# 지나도 2개로 유지된다.
SERIES_INTRO = (
    '같은 기준으로 본 다른 글입니다.',
    '이어서 볼 만한 글입니다.',
    '함께 보면 도움이 되는 글입니다.',
)


def _rot(seq, n, total=None):
    """회차 seq 에 돌릴 문장 번호(0..n-1). total(한 바퀴 지역 수)을 주면 바퀴마다 한 칸씩 밀어, 두 바퀴째 같은 지역에
    같은 문장이 다시 가지 않게 한다(전수리뷰 #80 — 문장 수 4가 바퀴 16의 약수라 ASK_CTA 가 지역에 고정됐다).
    한 바퀴째(seq <= total)와 total 을 안 줄 때는 예전 (seq-1) % n 과 같다."""
    if not total:
        return (seq - 1) % n
    return ((seq - 1) % total + (seq - 1) // total) % n


def series_links(nm, seq, total=None):
    """발행된 글에서 직전 지역 편·최신 주간 시세를 찾아 링크 블록을 만든다.

    ⚠️ RSS를 못 읽어도 초안 생성은 계속된다. 블로그가 잠깐 안 열린다고 그 주
    글을 못 쓰게 되면 본말전도다 — 링크만 빠지고 나머지는 그대로 나간다.

    ⚠️ 지금 쓰는 지역이 이미 발행돼 있으면(초안을 발행 뒤에 다시 만들 때)
    자기 자신을 걸게 된다. 제목이 이 지역 편이면(_zone_of_title — 발행 순회와 같은 판별) 건너뛴다. 예전엔
    `nm in 제목`이라 검색 표기로 쓴 제목('광주·전남 아파트')은 전남광주 편인데도 못 걸렀고, 다른 지역 편 제목에
    이 지역 이름이 곁들여 나오면('부산 …, 서울 아파트와 반대로') 그 글을 잘못 건너뛰었다.
    """
    zone_names = [z for z in SZ.ORDER if z not in SZ.AGG]
    try:
        import close_published_issues as CP
        posts = CP.fetch_posts()
    except Exception as e:
        print('  ⚠ 시리즈 링크 생략 — 발행 목록을 못 읽었습니다: %s' % e)
        return ''
    if posts is None:                 # fetch_posts는 읽기 실패를 None으로 알린다
        print('  ⚠ 시리즈 링크 생략 — 발행 목록을 못 읽었습니다(RSS).')
        return ''
    if not posts:
        print('  ⚠ 시리즈 링크 생략 — 발행된 글이 없습니다.')
        return ''

    def latest(cat, skip_self=False):
        for p in sorted(posts, key=lambda x: x['date'], reverse=True):
            if p['cat'] != cat or not p['url']:
                continue
            if skip_self and _zone_of_title(p['title'], zone_names) == nm:
                continue
            if CP.is_city_post(p['title']):      # 같은 카테고리의 도시 입주물량 편은 '같은 기준'의 글이 아니다
                continue
            return p
        return None

    # 카테고리 이름은 정본(CP.KIND_TO_CATEGORY)에서 — 손으로 복제하면 이름이 바뀔 때 링크가 조용히 빠진다(전수리뷰 #79)
    picks = [p for p in (latest(ZONE_CAT, skip_self=True),
                         latest(CP.KIND_TO_CATEGORY['주간 시세'])) if p]
    if not picks:
        return ''
    items = ''.join('<br>👉 <a href="%s">%s</a>' % (p['url'], esc(p['title']))
                    for p in picks)
    return '<p>%s%s</p>' % (SERIES_INTRO[_rot(seq, len(SERIES_INTRO), total)], items)


def cta(nm, seq, total=None):
    """글 끝 유도문 한 줄. 문장은 회차마다 바뀌고, 목적지는 늘 그 지역 리포트다. 캠페인은 누적 회차(seq)라 글마다 다르다."""
    txt = ZONE_CTA[_rot(seq, len(ZONE_CTA), total)]
    # 보이는 이름은 검색 표기(SEARCH_NAME, 예: '광주·전남'), 주소만 판정 단위 이름이다(2026-10-08 — 광주·전남 편
    # 초안의 소제목·링크에 내부 이름 '전남광주'가 그대로 나갔다).
    shown = esc(SEARCH_NAME.get(nm, nm))
    return ('<p>%s<br>👉 <a href="%s">%s 공급 리포트</a></p>'
            % (txt % shown if '%s' in txt else txt,
               site_link('/zone/%s/' % quote(nm), 'zone_deep_%d' % seq), shown))


# 지역 편 제목 앞머리 교대 실험(2026-09-27 대표 승인, 조회수 조사 SRCH-1).
# 지금 제목이 겨냥하는 '{지역} 아파트 공급물량'은 월 검색량이 집계 하한에도 못 미치고, 수요는
# '{지역} 부동산 전망' 쪽에 있다(08-14 키워드도구: 대구부동산전망 1,180/월). 대신 그 말은 경쟁 글이
# 훨씬 많다. 어느 쪽이 나은지는 재 봐야 안다 — 그래서 회차마다 번갈아 낸다.
# A안(기존): '2026년 세종 아파트 공급물량 전망, …'   B안: '2027년 세종시 부동산 전망, …'(09-29부터 두 안 모두 '년')
# B안도 결론절에 '공급물량'을 한 번 넣어 우리 주제어를 잃지 않는다. seq 1~4(서울·대구·부산·경기)는
# 이미 A안으로 나갔으므로 seq 5(세종)부터 B·A·B… 로 번갈아 간다. 판정은 blog_counter.py report 의
# D0~D3 초과 방문자와 naver_serp 추적 순위로 한다.
TITLE_ARM_FROM = 5
# 제목 연도는 '전망하는 해'다(2026-09-27 대표 결정). 10월부터는 다음 해를 쓴다. 09-27 블로그 검색 실측에서
# '2026 부동산 전망' 10,428건 대 '2027 부동산 전망' 459건이었고 2027 글이 매일 새로 올라오고 있었다 —
# 내년 전망 수요는 가을부터 커지는데 경쟁은 아직 적다. 지역 편이 말하는 '앞으로 3년'의 한가운데이기도 하다.
# 사이트 시도 리포트 제목(요청서 B4)도 같은 규칙을 쓴다.
OUTLOOK_NEXT_FROM_MONTH = SZ.OUTLOOK_NEXT_FROM_MONTH   # 규칙·상수의 정본은 sido_zones — 사이트 시도 리포트 제목과 한 함수
outlook_year = SZ.outlook_year                         # 주간 조사일 'YYYY-MM-DD' → 전망하는 해('2026'), 못 읽으면 ''
# 검색창에 사람들이 치는 표기(키워드도구 기준). 없는 지역은 그대로 쓴다.
SEARCH_NAME = {'세종': '세종시', '전남광주': '광주·전남'}
# 태그는 가운뎃점 없이 붙여 쓴다. 전남광주는 사람들이 '광주'로 찾는다(2026-09-29 대표 키워드도구 조회:
# 광주아파트 5,740·광주부동산 3,390·광주부동산전망 220 대 전남광주부동산 160·광주전남부동산 20 미만/월).
# 제목은 판정 범위(광주+전남)가 틀리지 않게 '광주·전남'으로 쓰고, 태그만 검색량이 큰 '광주'로 단다.
TAG_NAME = {'전남광주': '광주'}
# 도 단위 지역은 도 이름으로 거의 검색되지 않는다 — 사람들은 대표 도시 이름 + 아파트로 찾는다(2026-09-29 대표
# 키워드도구 조회, 월): 경남부동산전망 10 대 창원아파트 5,730, 충북아파트 70 대 청주아파트 11,310, 충남 천안아파트
# 7,800, 전북 전주아파트 6,060, 강원 원주아파트 6,940, 경북 포항아파트 3,360. 제목은 판정 범위가 도 전체라 도 이름을
# 두고, 태그 둘(부동산전망·아파트)만 대표 도시로 단다. 결론절에서 도시를 다룰지는 그 주 시군구 데이터로 정한다.
CITY_TAG = {'경남': '창원', '경북': '포항', '충남': '천안', '충북': '청주', '전북': '전주', '강원': '원주'}


def title_arm(seq, total=None):
    """제목 실험 팔. 한 바퀴째는 seq 5부터 B·A·B…(1~4는 이미 A로 나감). total 을 주면 두 바퀴째부터는 **바퀴 안
    순번의 팔을 바퀴마다 뒤집는다**(전수리뷰 #80). 그러지 않으면 지역마다 팔이 영원히 고정돼(서울·대구 A, 세종 B)
    A/B 차이가 지역 차이와 완전히 섞인다. 두 바퀴를 합치면 모든 지역이 A·B를 한 번씩 받는다."""
    k, lap = seq, 0
    if total and seq > total:
        k, lap = (seq - 1) % total + 1, (seq - 1) // total
    arm = 'B' if k >= TITLE_ARM_FROM and (k - TITLE_ARM_FROM) % 2 == 0 else 'A'
    return {'A': 'B', 'B': 'A'}[arm] if lap % 2 else arm


def zone_title(nm, yr, yrs, ask, seq, total=None):
    if title_arm(seq, total) == 'B':
        # 연도는 두 안 모두 '2027년'으로 쓴다(2026-09-29 대표 키워드도구: 2027년부동산전망 110 대 2027부동산전망
        # 120/월로 수요는 같고, 블로그 문서는 '2027년 부동산 전망' 5,019 대 '2027 부동산 전망' 165,931 로 33분의 1).
        # 두 안의 연도 표기가 달랐던 탓에 실험이 앞머리 말과 '년'을 섞어 비교하고 있었다.
        return '%s%s 부동산 전망, 앞으로 %d년 아파트 공급물량은 얼마나 %s' % (
            (yr + '년 ') if yr else '', SEARCH_NAME.get(nm, nm), yrs, ask)
    return '%s%s 아파트 공급물량 전망, 앞으로 %d년 얼마나 %s' % (
        (yr + '년 ') if yr else '', SEARCH_NAME.get(nm, nm), yrs, ask)


# 댓글 유도문 — 글 끝(면책 바로 앞) 한 줄. 2026-09-17 사용자 결정.
#
# 홈피드 랭커는 클릭 확률과 **체류·반응**을 같이 본다(네이버 2024.11 컨퍼런스 발표).
# 우리 유입의 90%가 홈피드라 댓글은 장식이 아니라 노출 신호다. 사용자는 매수·매도
# 고민과 단지 질문에 직접 답할 의향이 있다("내 경험도 쌓고"). '무료 상담'이라는
# 말은 쓰지 않는다 — 면책과 부딪히고 광고 문구로 읽힌다.
# ZONE_CTA와 같은 이유로 seq로 고른다: 난수면 검토본과 발행본이 어긋나고,
# 매번 같은 문장이면 회차 간 반복이 된다.
ASK_CTA = (
    '%s에서 매수나 매도를 고민 중이시라면 댓글로 상황을 남겨 주세요. '
    '아는 범위에서 제 생각을 답글로 적어 드리겠습니다.',
    '눈여겨보는 단지가 있으면 댓글에 이름을 적어 주세요. '
    '그 동네 공급이 어떤지 같이 따져 보겠습니다.',
    '지금 사야 할지 기다려야 할지, 팔아야 할지 고민되시면 댓글로 물어봐 주세요. '
    '제 생각을 솔직하게 말씀드리겠습니다.',
    '다음에 다뤘으면 하는 지역이나 궁금한 단지가 있으면 댓글로 알려 주세요. '
    '그 지역부터 먼저 다루겠습니다.',
)


def ask_cta(nm, seq, total=None):
    txt = ASK_CTA[_rot(seq, len(ASK_CTA), total)]
    return '<p>%s</p>' % (txt % esc(SEARCH_NAME.get(nm, nm)) if '%s' in txt else txt)


def _thumb_curve(sts, nm, since='2016.01'):
    """썸네일 배경에 깔 그 지역 매매가격지수. (점 목록, 고점 위치, 고점 대비 %) — 못 쓰면 None.

    계열이 끊겨 있으면(기준시점 변경 — 판정은 RC.index_breaks 정본) None 이다(전수리뷰 #72). 단절은 계열 전체의 일이라
    그 지역의 단절 폭이 작아도(대구 +4%) 옛 기준·새 기준이 섞인 것은 같다.
    2026-09-28 데이터는 2026.01 부터 새 기준(2026.06=100)이 옛 기준(2017.11=100) 끝에 붙어, 역대 최고가인 서울에
    '고점에서 -47%'와 절벽 곡선이 찍혔다. None 이면 문구는 기본값('<지역> 아파트')으로, 곡선은 빼고 그린다.

    ⚠️ 곡선은 `since`(2016.01)부터 그리지만 **고점은 계열 전체에서** 찾는다. 예전엔 그린 구간 안에서만 찾아 경북
    (실제 고점 2015.08)에 '고점에서 -12%'가 찍혔다 — 계열 전체 고점 대비로는 -15%다(2026-10-05 리뷰 D4). 고점이 그린
    구간 앞에 있으면 고점 위치는 None 이다.
    """
    st = (sts or {}).get('매매지수') or {}
    br = RC.index_breaks(sts or {}, ('매매지수',))
    if br:
        print('  ⚠ 썸네일 곡선·고점 문구 생략 — 매매지수 기준 단절: %s. 다음 클라우드 배치가 전 기간을 다시 받은 뒤 '
              'git pull 하고 다시 돌리면 곡선이 돌아온다.' % RC.break_message(br))
        return None
    ds = [x.split()[0] for x in st.get('dates', [])]    # '2026.07 p)' 같은 잠정 표시를 뗀다
    full = [(d, v) for d, v in zip(ds, (st.get('series') or {}).get(nm, [])) if v is not None]
    pts = [(d, v) for d, v in full if d >= since]
    if len(pts) < 24:
        return None
    peak = max(full, key=lambda x: x[1])
    ip = next((i for i, x in enumerate(pts) if x == peak), None)
    return pts, ip, (full[-1][1] / peak[1] - 1) * 100


# 기본 문구의 둘째 줄(질문). 시안 여섯 장 중 다섯이 "바닥은 지났을까"였다(2026-09-17
# 사용자: "반복되면 지루하다"). 기본값은 어디까지나 **안전망**이고, 발행 때는 그 글의
# 결론에 맞춘 문구를 --thumb-msg로 넣는다. 안전망이라도 같은 말이 이어지지 않게
# 지역 표시 순서로 돌린다(난수면 초안을 다시 만들 때 바뀐다).
THUMB_ASK_FALL = ('바닥은 지났을까', '지금 사도 될까', '다시 오를까', '언제쯤 돌아설까')
THUMB_ASK_PEAK = ('여기서 더 오를까', '지금 사면 늦은 걸까', '언제까지 오를까')


def thumb_pct(chg):
    """고점 대비 변화(%)의 썸네일 표시. 1% 이상은 정수('-15%'), 그 아래는 소수 한 자리('-0.4%').
    표시가 0 이면(고점과 같다) None — 그때만 '역대 최고가'라고 쓴다(thumb_message)."""
    a = abs(chg)
    txt = ('%.0f' % a) if a >= 0.95 else ('%.1f' % a)
    if float(txt) == 0:
        return None
    return '-%s%%' % txt


def thumb_message(nm, curve):
    """가운데 큰 글자의 기본값. `*...*`로 감싼 줄은 강조색으로 찍힌다.

    기본값은 데이터에서 나오는 사실 한 줄 + 독자가 품는 질문 한 줄이다. 없는 위기감을
    지어내지 않는다 — 발행 때 결론이 서면 `--thumb-msg "첫 줄|*둘째 줄*"`로 바꾼다.
    """
    order = list(SZ.DISPLAY_ORDER)
    k = order.index(nm) if nm in order else 0
    # '역대 최고가'는 지금 값이 계열 전체 고점과 **같을 때만**(표시 자릿수로 0) 사실이다. 예전엔 고점이 최근 3점 안이고
    # 하락이 3% 미만이면 그렇게 찍어, 고점 두 달 뒤 -2.9% 인 곳도 '지금이 역대 최고가'였다(2026-10-05 리뷰 D4; 그 앞의
    # 리뷰 09-18 19번은 2년 전 고점을 그렇게 부른 것). 하락 폭은 실제 값을 적는다 — 예전 `min(값, -1)` 은 -0.4% 를 '-1%'로
    # 부풀렸다.
    if curve:
        pct = thumb_pct(curve[2])
        if pct is None:
            return ['%s, 지금이 역대 최고가' % nm,
                    '*%s*' % THUMB_ASK_PEAK[k % len(THUMB_ASK_PEAK)]]
        return ['%s, 고점에서 %s' % (nm, pct),
                '*%s*' % THUMB_ASK_FALL[k % len(THUMB_ASK_FALL)]]
    return ['%s 아파트' % nm, '*앞으로 3년 공급은*']


# 썸네일 색은 **권역마다 고정**이다(2026-09-17 사용자 제안). 블로그가 앨범형이라 썸네일이
# 목록에 나란히 깔리는데, 색이 권역을 뜻하면 "영남 글은 살구색"처럼 색으로 글을 찾는다.
# 회차마다 색을 돌리던 첫 방식은 알록달록하기만 하고 뜻이 없었다.
# (바탕, 곡선 아래 면, 곡선, 강조 글자)
THUMB_PALETTES = {
    '수도권': ((240, 247, 250), (214, 232, 242), (140, 184, 214), (28, 100, 170)),   # 하늘
    '영남':   ((252, 246, 238), (248, 226, 214), (233, 164, 140), (200, 60, 40)),    # 살구
    '호남':   ((243, 249, 241), (219, 237, 216), (150, 200, 150), (30, 125, 70)),    # 연두
    '충청':   ((250, 246, 252), (234, 222, 244), (186, 160, 220), (110, 60, 170)),   # 연보라
    '강원':   ((240, 249, 247), (208, 236, 230), (120, 196, 184), (0, 120, 110)),    # 청록
    '제주':   ((253, 248, 232), (250, 234, 190), (232, 190, 96), (176, 112, 0)),     # 귤색
}
# ⚠️ 손으로 적은 목록이다. 판정 단위가 바뀌면(2026-09-10 광주·전남 통합처럼) 여기가
# 조용히 어긋나므로 test_every_zone_has_a_thumb_group이 모델의 시도 전부가 여기에
# 있는지 지킨다. 집계(전국·수도권·지방)는 지역 편을 쓰지 않으므로 넣지 않는다.
THUMB_GROUP = {
    '서울': '수도권', '경기': '수도권', '인천': '수도권',
    '부산': '영남', '대구': '영남', '울산': '영남', '경남': '영남', '경북': '영남',
    '전남광주': '호남', '전북': '호남',
    '대전': '충청', '세종': '충청', '충남': '충청', '충북': '충청',
    '강원': '강원', '제주': '제주',
}


THUMB_FONT = 104


def thumb_chip(nm, yr):
    """썸네일 위쪽 작은 글자. **지역 이름**을 꼭 넣는다 — 큰 글자(결론 문구)는 회차마다 바뀌고 지역 이름이 빠질 수 있어서,
    칩마저 '2027 아파트 공급 전망'이면 피드 카드만 보고는 어느 지역 글인지 알 수 없었다(10-08 광주·전남 초안, 대표 지적
    10-09). 연도는 제목과 같이 '2027년'으로 쓴다(09-29 대표 결정). 지역은 검색 표기(SEARCH_NAME)로."""
    return '%s%s 아파트 공급 전망' % ((yr + '년 ') if yr else '', SEARCH_NAME.get(nm, nm))


def thumb_zone(r, yr, yrs, sts=None, msg=None):
    """홈피드 카드용 대표 이미지 — drafts/thumb-<지역>.png (1200x900).

    2026-09-17 실측: 발행 12편의 대표 이미지가 전부 사이트 캡처였다. 글자가 빽빽해
    피드의 작은 카드에서는 아무것도 안 읽힌다. 피드에서 우리가 쥔 손잡이는 제목과
    썸네일 둘인데 썸네일은 한 번도 만든 적이 없었다.

    첫 시안(지역명+숫자 카드)은 사용자가 "AI 양산형"이라며 버렸다 — 글자만 갈아
    끼우는 틀이라 그렇다. 그래서 **그 지역의 실제 10년 가격 곡선을 배경에** 깐다.
    곡선은 지역마다 모양이 달라(세종은 절벽, 서울은 우상향) 찍어낸 카드로 안 보인다.
    그 위 가운데에 큰 글자로 키 메시지를 얹는다(사용자 제안) — 클릭은 메시지가 번다.

    ⚠️ 세로축은 0이 아니라 구간 최저에서 시작한다. 배경 그림이라 눈금을 안 찍고,
    숫자(고점 대비 %)는 지수에서 그대로 계산한 값만 쓴다.
    실패해도 초안은 나가야 하므로 호출부에서 예외를 잡는다.
    """
    from PIL import Image, ImageDraw
    import make_zone_cards as ZC
    Wd, Ht, K = 1200, 900, 2                      # K배로 그려 줄인다(곡선 계단 방지)
    nm = r['z']
    # 밝은 바탕. 블로그가 앨범형이라 썸네일이 목록에 나란히 깔리는데, 어두운 카드가
    # 이어지면 블로그 전체가 침침해진다(2026-09-17 사용자). 같은 색만 이어져도
    # 색은 권역마다 고정이다(THUMB_GROUP).
    BG, FILL, DIM, ACCENT = THUMB_PALETTES[THUMB_GROUP.get(nm, '수도권')]
    WHITE, SOFT = (19, 30, 36), (94, 111, 116)      # 본문 글자(먹색)·보조 글자
    img = Image.new('RGB', (Wd * K, Ht * K), BG)
    d = ImageDraw.Draw(img)
    F = lambda size, w='Bold': ZC.font(size * K, w)

    curve = _thumb_curve(sts, nm)
    if curve:
        pts = curve[0]
        lo, hi = min(v for _, v in pts), max(v for _, v in pts)
        x0, x1, yb, yt = 0, Wd, Ht - 40, 150
        xy = [((x0 + (x1 - x0) * i / (len(pts) - 1)) * K,
               (yb - (yb - yt) * (v - lo) / ((hi - lo) or 1)) * K)
              for i, (_, v) in enumerate(pts)]
        d.polygon(xy + [(x1 * K, Ht * K), (x0 * K, Ht * K)], fill=FILL)
        d.line(xy, fill=DIM, width=6 * K, joint='curve')

    chip = thumb_chip(nm, yr)
    d.text((Wd / 2 * K, 96 * K), chip, font=F(38), fill=SOFT, anchor='mm')

    lines = [x for x in (msg or thumb_message(nm, curve)) if x.strip()][:3]
    clean = [x.strip('*') for x in lines]
    # 글자 크기는 고정이다 — 앨범형 목록에 나란히 깔리므로 회차마다 크기가 들쭉날쭉하면
    # 지저분하다. THUMB_FONT는 가장 긴 기본 문구("전남광주, 고점에서 -15%")가 들어가는
    # 크기다. 넘치는 문구만 줄이고, 줄였다는 걸 알린다 — 문구를 줄이는 게 먼저다.
    size = min([THUMB_FONT * K] +
               [ZC.fit_width(c, (Wd - 120) * K, hi=THUMB_FONT * K, lo=60 * K).size
                for c in clean])
    if size < THUMB_FONT * K:
        print('  ⚠ 썸네일 문구가 길어 글자를 %dpx → %dpx로 줄였다. 한 줄 11자 안팎이 맞다.'
              % (THUMB_FONT, size // K))
    gap = int(size * 1.22)
    y = Ht / 2 * K - gap * (len(lines) - 1) / 2 + 10 * K
    fnt = ZC.font(size, 'Bold')
    for raw, c in zip(lines, clean):
        # 곡선 위에서도 읽히게 글자 뒤에 배경색 테두리를 두른다.
        d.text((Wd / 2 * K, y), c, font=fnt, anchor='mm', stroke_width=10 * K,
               stroke_fill=BG, fill=ACCENT if raw.startswith('*') else WHITE)
        y += gap

    # 아랫줄 요약("907세대 부족 · 3년 적정물량의 13% · 판정 균형")은 뺐다 — 피드 카드
    # 크기에서 안 읽히고, 처음 보는 사람은 뜻도 모른다(2026-09-17 사용자). 썸네일은
    # 키 메시지 하나만 말한다. 서명은 도메인이 아니라 이름 — 네이버 안에서는 주소가
    # 눌리지도 않고 광고처럼 읽힌다.
    d.text((Wd / 2 * K, (Ht - 78) * K), '아공맵', font=F(44), fill=WHITE,
           anchor='mm', stroke_width=6 * K, stroke_fill=BG)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'thumb-%s.png' % nm)
    if _keep_existing_thumb(path, msg):
        print('  ⚠ %s 는 이미 있어 그대로 뒀다(--thumb-msg 로 만든 것일 수 있다). 다시 만들려면 --force-thumb.'
              % os.path.basename(path))
        return os.path.relpath(path, ROOT)
    img.resize((Wd, Ht), Image.LANCZOS).save(path)
    return os.path.relpath(path, ROOT)


def _keep_existing_thumb(path, msg, argv=None):
    """문구 없이 다시 돌릴 때 기존 썸네일을 보존한다.

    발행 전까지 같은 지역이 계속 뽑히므로 금요일 주간 글 때문에 돌릴 때마다 --thumb-msg 로 만든
    맞춤 썸네일이 기본 문구로 덮였다(리뷰 09-18 19번). 문구를 줬거나 --force-thumb 면 새로 만든다.

    ⚠️ --force(초안 덮기)는 썸네일을 건드리지 않는다. 예전엔 한 깃발이 둘을 같이 했다 — 초안을 덮으려고 --force 를
    주면 --thumb-msg 로 만든 맞춤 썸네일까지 기본 문구로 덮였다(2026-10-05 리뷰 D1).
    """
    argv = sys.argv if argv is None else argv
    return msg is None and '--force-thumb' not in argv and os.path.exists(path)


def _thumb_msg_arg(argv):
    """--thumb-msg "첫 줄|*둘째 줄*" → ['첫 줄', '*둘째 줄*']"""
    if '--thumb-msg' in argv:
        i = argv.index('--thumb-msg')
        if i + 1 < len(argv):
            return [x.strip() for x in argv[i + 1].split('|')]
    return None


def draft_zone(adv, sts, r, seq, total):
    nm = r['z']
    # 순부족은 사이트 카드·리포트가 찍는 정수(배치가 구운 dtot)를 쓴다. 'tot'는 반올림 전
    # 값들로 계산돼 카드의 세 정수로 검산한 값과 1세대 갈린다(경기 50,578 vs 사이트 50,579 등
    # 4개 시도, 2026-09-23 전체 점검). M.disp_tot 가 사이트 쪽 정본이다.
    t = M.disp_tot(r, SZ.LEAD_Q)
    lack = t >= 0
    # '과잉하다'는 동사가 아니라 '얼마나 과잉할까'가 안 된다. 부족/과잉을
    # 대칭 서술어(모자라다/남다)로 갈라 쓴다.
    # '모자라다'가 아니라 '부족하다'를 쓴다(2026-09-28). 블덱스가 부산 편 제목의 '모자랍니다'를 키워드
    # '#모자'(월 3.8만, 모자 쇼핑)로 뽑았다 — 검색엔진이 제목을 오분석하면 엉뚱한 질의에 묶인다.
    ask = '부족할까' if lack else '남을까'
    state = '부족한' if lack else '남아도는'
    yrs = SZ.LEAD_Q // 4

    # '수급'은 우리가 쓰는 말이지 검색되는 말이 아니다. 2026-08-14 실측에서
    # 이 주제의 상위 글은 전부 '연도 + 지역 + 아파트 공급물량 + 전망' 형태였다
    # (1위 '2026년 부산 아파트 공급물량과 향후 부동산 시장 전망은').
    # '입주물량'이 검색량은 더 크지만 그건 분양 확정분을 뜻하는 말이라,
    # 착공 실적으로 추정하는 우리 숫자에 붙이면 기대와 다른 글이 된다.
    yr = outlook_year((adv.get('weekly', {}).get('rows') or [{}])[-1].get('p', ''))
    # 구분자는 쉼표다. 2026-08-15 실측에서 '전망' 성격의 글 상위권은 쉼표·물음표를
    # 쓰고 `|`는 안 쓴다 — `|`는 주간 시세 쪽 관행이다(한국부동산원 주간동향｜…).
    # 사이클 시리즈만 고치고 여기를 빠뜨렸던 걸 사용자가 잡았다.
    title = zone_title(nm, yr, yrs, ask, seq, total)

    body = []
    # 첫 이미지가 네이버의 대표 이미지(피드 카드 썸네일)가 된다 — 그래서 맨 앞이다.
    body.append('<p>[여기에 썸네일 이미지를 넣어 주세요 — 첫 이미지가 대표 이미지가 됩니다]</p>')
    # ⚠️ 도입의 "전국 N개 시도를 같은 기준으로 보고 있습니다. 이번에는 X 차례입니다"를
    # 뺐다(2026-09-01 사용자: "대구랑 중첩되는 내용, 특히 아공맵의 로직이나 소개 같은
    # 부분"). 회차마다 지역명만 갈리는 시리즈 안내였고, 검색으로 들어온 사람에게는
    # 그 지역 결론보다 먼저 읽히는 도구 설명이었다. 결론부터 시작한다.
    # 방법론 해명을 도입에 두지 않는다. 독자는 그 지역 전망을 보러 왔는데 두 번째
    # 문단부터 "왜 시도 단위인가"를 읽게 된다. 원자료 대조는 우리 차별점이라
    # 버리진 않고 '어떻게 계산했나'로 옮겼다. "시군구별 사정은 갈립니다"는
    # 시작하자마자 김을 빼는 반사적 헤지라 뺐다(2026-08-16 사용자 지적).
    # 소제목·첫 문장에 검색어를 둔다(2026-09-27 조회수 조사 SRCH-1). '결론부터'는 검색되지 않는
    # 말이었다. 우리 고유어 '적정 공급량'은 경쟁 글이 적고(부산 적정 공급량 5천 건대, 상위는 청약
    # 일정 목록) 첫 검색 유입도 이 말로 들어왔다(09-02 '부산 적정 공급량').
    body.append('<h3>%s 적정 공급량과 %d년 공급물량</h3>' % (esc(SEARCH_NAME.get(nm, nm)), yrs))
    # 판정 이름만 쓰면 '균형' 옆 '5만 세대 부족'이 반대로 읽힌다(2026-09-13 PM 요청).
    # 등급을 자르는 비율 문장을 사이트와 같은 함수로 붙인다 — 블로그가 따로 만들지 않는다.
    # 셈 한 줄(홈 마케팅 검수 B2·C4·TRUST-2, 2026-09-27). 순부족에는 앞으로 3년뿐 아니라 지난 4년 덜 지은 몫이
    # 더해져 있어 '적정물량 − 공급'으로는 검산이 안 된다. 사이트(홈 카드 ⓘ·산출 방법·시도 리포트 '숫자로 보면')와
    # 같은 함수·같은 정수로 적는다 — 블로그가 식을 따로 만들지 않는다(test_home_first_screen).
    # 판정 설명 문장도 같은 inow 로 갈래를 고른다 — 여유 지역에 '앞으로 3년 … 더 들어옵니다'라고 쓰면 바로 아래
    # 식(입주 추정 < 적정물량, 여유는 지난 4년 남은 재고)과 숫자로 부딪친다(인천, 검토 지적 TRUST-2④).
    need, fut, inow, _ = SZ.display_ints(r, SZ.LEAD_Q)
    body.append('<p>%s 아파트 공급물량을 적정 공급량과 견주면, 현재 '
                '<b>%s세대가 %s</b> 상태입니다. 판정은 <b>%s</b>입니다. %s.</p>' % (
                    esc(SEARCH_NAME.get(nm, nm)), num(abs(t)), state,
                    SZ.GRADE_LABS[r['grade']],
                    esc(SZ.ratio_text(r['ratio'], int(round(yrs * 4)), full=True, inow=inow))))
    body.append('<p>셈은 <b>%s</b>입니다.</p>'
                % esc(SZ.formula_text(SZ.LEAD_Q, SZ.BACKLOG_WINDOW, need, fut, inow)))
    # 캡처는 이 바로 뒤에 온다 — 앞 문장이 말한 숫자가 화면에 그대로 찍혀 있어
    # 글이 주장한 것을 곧바로 확인시켜 준다.
    body.append('<p>[여기에 리포트 캡처 이미지를 넣어 주세요]</p>')
    # ⚠️ 예전엔 캡처마다 "위 화면이 아공맵 X 리포트입니다. 지역만 바꾸면 17개
    # 시도를…" 하는 소개문 + 링크를 달았다. 이미지가 셋이라 브랜드 소개가 한 글에
    # 세 번 나갔고, 회차가 바뀌어도 문장이 같았다. 2026-09-01 사용자 지시로
    # 본문 중간의 소개문을 전부 걷고 유도는 글 끝 한 줄(cta())로 모았다.
    # 트레이드오프는 알고 간다 — 끝까지 읽은 사람만 링크를 본다.

    # ── 그 지역 이야기를 먼저. 방법론은 맨 뒤로.
    #
    # 예전엔 결론 바로 뒤에 '어떻게 계산했나' 5문단, 그 뒤에 '이 숫자의 한계'
    # 4문단이 왔다. 17주 내내 같은 방법론을 다시 읽히는 구조였고, 검색으로 처음
    # 온 사람에게는 지역 정보가 아니라 도구 설명이 먼저 왔다. 지역 리포트가
    # 아니라 아공맵 설명서로 읽힌다는 지적(2026-08-30 사용자).
    #
    # 새 순서: 결론 → 그 지역의 지금 → 전망 → 다른 지역 → 산식(압축) → 면책.
    shown = SEARCH_NAME.get(nm, nm)
    body.append('<h3>%s%s 지금 어떤 상태인가</h3>' % (esc(shown), eunneun(shown)))
    # 그 지역 시세부터. ②만 읽고 가는 사람도 있어서 ①에 있다고 생략하면 안 된다.
    W = adv.get('weekly') or {}
    try:
        i = (W.get('regions') or []).index(nm)
        cur, prv = W['rows'][-1], W['rows'][-2]
        ma, je = cur['ma'][i], cur['je'][i]
        pma = prv['ma'][i]
        if ma is not None:
            was = ('(전주 %s)' % pct(pma)) if pma is not None else ''
            body.append('<p>먼저 시세입니다. %s 기준 매매 <b>%s</b>%s, '
                        '전세 <b>%s</b>.</p>'
                        % (kdate(cur['p']), pct(ma), was, pct(je)))
    except (ValueError, IndexError, KeyError):
        pass
    if r.get('unsold'):
        if r.get('uwarn'):
            # 경고 문장은 M.unsold_warn 정본을 쓴다 — 사본을 두면 사이트와 갈린다.
            body.append('<p>%s%s %s</p>' % (esc(nm), eunneun(nm), M.unsold_warn(r)))
            body.append('<p>부족 판정과 어긋나 보이지만 모순이 아닙니다 — 미분양이 '
                        '쌓이면 건설사가 착공을 멈추고, 그래서 <b>앞으로 지을 물량이 '
                        '줄어듭니다.</b> 지금 남는 것과 %d년 뒤 모자라는 것은 다른 '
                        '이야기입니다.</p>' % yrs)
        else:
            body.append('<p>미분양은 <b>%s세대</b>입니다. 다 짓고도 팔리지 않은 재고라, '
                        '쌓이면 분양가와 입주장 전세가에 먼저 반영됩니다.</p>'
                        % num(r['unsold']))
    body.append('<p>분기별로 나눠 보면 이렇습니다. 칸 색이 짙을수록 그 분기에 '
                '들어올 물량이 적정선에 못 미친다는 뜻입니다.</p>')
    body.append('<p>[여기에 분기별 공급표 이미지를 넣어 주세요]</p>')

    # 모델이 그 지역과 구조적으로 안 맞는 경우의 공시 — 정본은 M.MODEL_LIMIT_NOTE.
    # 판정을 곧이곧대로 인용하면 안 되는 지역이 있다는 사실은 숨기지 않는다.
    limit = (getattr(M, 'MODEL_LIMIT_NOTE', {}) or {}).get(nm)
    if limit:
        body.append('<p><b>덧붙임</b> — %s</p>' % esc(limit.lstrip('⚠ ')))

    # ── 전망. 숫자는 기계가 깔고, 판단은 사람이 쓴다.
    #
    # 사실 나열만 하면 데이터 덤프에 그친다는 사용자 지적(2026-08-15). 다만
    # 판단을 기계가 쓰면 매주 같은 주장이 반복되고, 무엇보다 그건 저자의 몫이다.
    # 그래서 검증 가능한 재료(미분양 배수와 전국 순위, 금리 변화)만 깔아 두고
    # 결론 문단은 비운다.
    #
    # ⚠️ '역대 최저' 같은 표현을 쓰지 않는다. 서울 1,013호는 자기 25년 역사에선
    # 낮은 순 139/241로 중간쯤이다(2018.12엔 27호였다). 압도적인 건 **지역 간
    # 비교**다 — 그 층위를 섞으면 반박당한다.
    zs = (adv.get('sido') or {}).get('zones') or []
    ums = sorted((x for x in zs if not x.get('agg') and x.get('um') is not None),
                 key=lambda x: x['um'])
    mine = next((i for i, x in enumerate(ums) if x['z'] == nm), None)
    if mine is not None and r.get('um') is not None:
        body.append('<h3>그래서 어떻게 될 것인가</h3>')
        # 바로 다음 순위와 견주면 안 된다 — 서울 0.05 vs 세종 0.07이라 '1배 차이'가
        # 되어 뜻이 없다. 대척점(가장 높은 곳)과 견줘야 폭이 드러난다.
        # 조사는 붙이지 않는다 — '세종와도' 같은 오류를 원천에서 없앤다.
        cmp_txt = ''
        if mine == 0 and len(ums) > 1:
            top = ums[-1]
            cmp_txt = (' 가장 높은 %s(%s)의 <b>%d분의 1</b> 수준입니다.'
                       % (esc(top['z']), umx(top['um']),
                          round(top['um'] / max(r['um'], .01))))
        # 부족분 대비 비율이 가장 세게 읽힌다 — 서울은 31만 세대가 모자란데
        # 안 팔린 건 1천 호, 308분의 1이다. '역대 최저' 같은 시계열 주장과 달리
        # 반박할 구석이 없다(2026-08-15~16 사용자 지적으로 바로잡음).
        vs_tot = ''
        if t > 0 and r['unsold'] and r['unsold'] < t:
            vs_tot = (' 부족분 <b>%s세대의 %.1f%%</b>, %d분의 1입니다.'
                      % (num(t), r['unsold'] / t * 100, round(t / r['unsold'])))
        body.append('<p>그 미분양은%s</p>' % (vs_tot or
                    ' 부족분과 견주면 그리 크지 않습니다.'))
        # '견줘도'는 낮다는 뉘앙스라 제주(2.4배)에서 어긋난다. 중립으로 쓴다.
        # 시도 수를 박지 않는다 — 광주·전남이 '전남광주'로 합쳐져 16곳이 됐다
        # (2026-09-11 확인). 순회 pool 크기(total)를 그대로 쓴다.
        body.append('<p>분기 적정물량과 견주면 <b>%s</b>로 %d개 시도 가운데 '
                    '<b>낮은 순 %d번째</b>입니다.%s</p>'
                    % (umx(r['um']), total, mine + 1, cmp_txt))
        cd = _cd_change(sts)
        if cd:
            body.append('<p>여기에 금리가 걸립니다. CD 91일물이 1년 사이 '
                        '<b>%s%% → %s%%</b>로 %s%%p 움직였습니다.</p>' % cd)
        # ⚠️ 여기 있던 사이클 고리 설명 두 문단(2021 저금리 그래프 / "전세가 먼저
        # 오르고 그 전세가 매매를 민다")을 뺐다. 회차마다 글자까지 같았고, 그 고리는
        # 이미 전망 문단이 그 지역 숫자로 말한다(부산 편: 전세가율 29개월 연속 상승).
        # 이론을 다시 읊는 대신 그 지역 데이터로 보이는 쪽이 근거로도 세다.
        # 2026-09-01 사용자: "사이클 고리는 굳이 필요없을듯".
        body.append('<p>%s</p>' % OUTLOOK_PLACEHOLDER)

    body.append('<p>[여기에 %d개 시도 판정표 이미지를 넣어 주세요]</p>' % total)
    # ── 산식 3문단(적정물량 기준선 / 인허가 아니라 착공 / 멸실 미차감)을
    # 걷어냈다. 회차마다 글자까지 똑같이 나가던 자리다 — 2026-09-01 실측에서 부산 ②
    # 53문장 중 30문장이 대구와 뼈대가 같았고, 그 절반이 여기였다. 계산법 공개는
    # 아공맵의 신뢰 근거라 버리는 게 아니라 **사이트가 진다**. 블로그는 그 지역
    # 이야기만 하고, 산식이 궁금한 사람은 아래 유도문을 타고 리포트로 간다.
    sl = series_links(nm, seq, total)
    if sl:
        body.append(sl)
    body.append(cta(nm, seq, total))
    body.append(ask_cta(nm, seq, total))
    # ⚠️ 면책을 '권유하지 않습니다'로 쓰지 않는다. 본문이 방향을 분명히
    # 말하는데 말미에서 그걸 부인하면 글이 스스로를 무른다. 대신 **사실과
    # 견해를 가르고 책임 소재를 밝힌다** — 이 편이 더 정직하고 더 강하다.
    body.append('<p><i>※ 숫자는 한국부동산원·국토교통부·KOSIS·한국은행 공개 '
                '데이터를 가공한 것이고, <b>판단과 전망은 글쓴이 개인의 견해</b>'
                '입니다. 투자 결정과 그 결과는 읽는 분의 몫입니다.</i></p>')

    # 5개로 둔다(①과 같은 이유). '입주물량'은 넣지 않는다 — 분양 확정분을 뜻하는
    # 말이라 착공 추정인 우리 숫자와 어긋난다(제목에서 뺀 것과 같은 이유).
    # 2026-09-27 조회수 조사(SRCH-1): '아파트공급'·'집값전망' 같은 일반어 대신 그 지역의 검색어
    # 셋(공급물량·적정공급량·부동산전망)을 단다. 미분양 경고 지역은 '{지역}아파트' 자리에
    # '{지역}미분양'을 단다 — 그 지역 사람들이 실제로 찾는 말이다(대구 편 때 '미분양' 검색 열기).
    tn = TAG_NAME.get(nm, nm)
    city = CITY_TAG.get(nm, tn)
    tags = [tn + '아파트공급물량', tn + '적정공급량', city + '부동산전망',
            city + ('미분양' if r.get('uwarn') else '아파트'), '아공맵']
    shot, shots, err = (None, {}, '--no-shot 로 건너뜀')
    if '--no-shot' not in sys.argv:
        shot, shots, err = capture_zone(nm)
    thumb = None
    try:
        thumb = thumb_zone(r, yr, yrs, sts, _thumb_msg_arg(sys.argv))
    except Exception as e:    # 썸네일이 없어도 초안은 나간다
        print('  ⚠ 썸네일 생략 — %s: %s' % (type(e).__name__, e))
    if shot:
        lines = ['<b>%s</b> → [리포트 캡처]' % shot]
        if thumb:
            lines.insert(0, '<b>%s</b> → [썸네일] (글 맨 위, 대표 이미지로 지정)%s' % (
                thumb, '' if _thumb_msg_arg(sys.argv) else
                ' — ⚠ 문구가 기본값입니다. 결론이 서면 <code>--thumb-msg "첫 줄|*둘째 줄*"</code>로 다시 만드세요'))
        if shots.get('표'):
            lines.append('<b>%s</b> → [분기별 공급표]' % shots['표'])
        if shots.get('판정표'):
            lines.append('<b>%s</b> → [%d개 시도 판정표]' % (shots['판정표'], total))
        note = ('%s 화면을 자동으로 떴습니다.<br>%s<br>네이버는 외부 이미지 주소를 '
                '그대로 쓰지 않으므로 파일을 직접 올리고, 이미지마다 캡션을 달아 '
                '주세요.' % (nm, '<br>'.join(lines)))
    else:
        note = ('캡처 없음 — %s. 본문의 자리 표시자를 지우거나 직접 캡처해 '
                '넣으세요.' % err)
        if thumb:
            note += '<br><b>%s</b> → [썸네일] (글 맨 위, 대표 이미지로 지정)' % thumb
    return dict(title=title, body='\n'.join(body), tags=tags, img=shot,
                kw='%s 아파트 공급물량' % nm, imgnote=note,
                seq='%d / %d번째 지역%s · 제목 실험 %s안' % (
                    (seq - 1) % total + 1, total,
                    (' · %d바퀴째(누적 %d편째)' % ((seq - 1) // total + 1, seq)) if seq > total else '',
                    title_arm(seq, total)),
                # 본문 자리 표시자 순서대로. 썸네일은 글 맨 위(대표 이미지)다.
                imgs=[(thumb, '썸네일 · 글 맨 위, 대표 이미지'), (shot, '리포트 캡처'),
                      (shots.get('표'), '분기별 공급표'),
                      (shots.get('판정표'), '%d개 시도 판정표' % total)])


# ---------------------------------------------------------------- 렌더
CSS = """
body{font:15px/1.7 -apple-system,'Segoe UI','Malgun Gothic',sans-serif;
  max-width:820px;margin:0 auto;padding:24px 18px 80px;color:#1d2330;background:#f6f4ee}
h1{font-size:21px;margin:0 0 4px}
.hint{color:#6f6a5c;font-size:13.5px;margin:0 0 24px}
.draft{background:#fff;border:1px solid #dad5c9;border-radius:10px;
  padding:18px;margin:0 0 22px}
.draft>h2{font-size:16px;margin:0 0 14px;padding-bottom:10px;
  border-bottom:2px solid #3d4a8a;color:#3d4a8a}
.field{margin:0 0 16px}
.lab{display:flex;align-items:center;gap:8px;margin:0 0 6px}
.lab b{font-size:12.5px;color:#3d4a8a}
button{font:600 12px/1 inherit;padding:5px 11px;border:1px solid #3d4a8a;
  background:#3d4a8a;color:#fff;border-radius:6px;cursor:pointer}
button.done{background:#1f8a70;border-color:#1f8a70}
.box{border:1px solid #dad5c9;border-radius:7px;padding:12px 14px;background:#fcfbf8;overflow-x:auto}
.box.t{font-weight:700}
.box.g{color:#3d4a8a;font-size:13.5px}
.box table{border-collapse:collapse;margin:10px 0}
.box th,.box td{border:1px solid #cfc9b8;padding:5px 9px;font-size:14px}
.box th{background:#f1eee6}
.box h3{font-size:15.5px;margin:18px 0 6px}
.note{background:#fff8e6;border-left:3px solid #dca214;padding:9px 12px;
  font-size:13px;margin:10px 0 0;border-radius:0 6px 6px 0}
code{background:#f1eee6;padding:1px 5px;border-radius:4px;font-size:12.5px}
.rival{background:#f4f7f4;border:1px solid #d8e2d8;border-radius:6px;
  padding:10px 13px;margin:0 0 12px;font-size:13px}
.rival ol{margin:7px 0 6px;padding-left:20px}
.rival li{margin:3px 0;line-height:1.45}
.src{color:#7b8a7b;font-size:12px}
.tags{display:flex;flex-wrap:wrap;gap:6px}
button.tag{font:500 13px/1.35 inherit;padding:5px 10px;border:1px solid #cfd6e8;
  background:#fff;color:#3d4a8a;border-radius:14px}
button.tag.done{background:#1f8a70;border-color:#1f8a70;color:#fff}
.shots{margin:10px 0 0}
.shot{margin:0 0 14px;border:1px solid #dad5c9;border-radius:7px;background:#fcfbf8;padding:8px}
.shot img{display:block;max-width:100%;height:auto;margin:0 auto}
.shot figcaption{font-size:12.5px;color:#6f6a5c;margin:6px 2px 0}
"""

JS = """
// 클립보드에 '의미'만 싣는다.
//
// 두 가지를 한꺼번에 푼다(둘 다 2026-08-14 사용자 실측):
//  ① 붙여넣으면 문단이 줄줄이 붙는다 — 에디터가 <p> 사이 CSS 여백을 안 가져온다.
//     여백은 스타일이라 살아남지 못하므로, 빈 문단을 실제 노드로 끼운다.
//  ② 붙여넣으면 전부 볼드로 나온다 — 소스는 굵지 않다(실측 font-weight 400).
//     범위 선택 후 execCommand로 복사하면 Chrome이 계산된 스타일을 전부
//     인라인으로 박아 넣고, 스마트에디터가 그 뭉치를 제 방식대로 해석한다.
//     그래서 DOM을 복사시키지 않고 우리가 만든 HTML 문자열을 직접 쓴다.
//     class·id는 지운다(페이지 겉치레). td의 text-align은 우리가 쓴 것이라 남긴다.
function payload(el){
  var c=el.cloneNode(true);
  c.querySelectorAll('*').forEach(function(n){
    n.removeAttribute('class'); n.removeAttribute('id');
  });
  // 소스에서 접어 둔 줄바꿈을 지운다. 이론 시리즈 본문은 문단 안에 줄바꿈 문자가
  // 수십 개 들어 있는데, 주간 초안(문단 안 줄바꿈 문자 0개)은 붙여넣기가 멀쩡했고
  // 이론 초안만 줄바꿈이 안 먹는다는 보고가 있었다(2026-09-10). 편집기가
  // 문단 안 줄바꿈 문자를 어떻게 다루는지는 확인할 수 없으니, 클립보드로 나가는
  // HTML을 주간 초안과 같은 모양(문단 안 줄바꿈 문자 없음)으로 맞춘다.
  var w=document.createTreeWalker(c,NodeFilter.SHOW_TEXT,null,false), t, drop=[];
  while((t=w.nextNode())){
    if(t.parentNode&&t.parentNode.tagName==='PRE') continue;
    if(!t.nodeValue.trim()&&t.parentNode===c){drop.push(t);continue;} // 블록 사이 공백
    t.nodeValue=t.nodeValue.replace(/\\s*\\n\\s*/g,' ');
  }
  drop.forEach(function(n){n.parentNode.removeChild(n);});
  var kids=Array.prototype.slice.call(c.children);
  kids.forEach(function(k,i){
    if(i<kids.length-1){
      var gap=document.createElement('p');
      gap.appendChild(document.createElement('br'));
      c.insertBefore(gap,k.nextSibling);
    }
  });
  c.removeAttribute('class'); c.removeAttribute('id');
  c.style.position='fixed'; c.style.left='-9999px'; c.style.top='0';
  document.body.appendChild(c);
  // innerText는 문서에 붙어 있어야 나온다. 끼워 넣은 빈 문단 탓에 평문 쪽은
  // 빈 줄이 과하게 잡히므로 두 줄로 줄인다(html을 못 받는 편집기용 폴백).
  var out={html:c.innerHTML, text:c.innerText.replace(/\\n{3,}/g,'\\n\\n')};
  document.body.removeChild(c);
  return out;
}
function legacy(el){                              // 클립보드 API가 막힌 경우만
  var r=document.createRange(); r.selectNodeContents(el);
  var s=window.getSelection(); s.removeAllRanges(); s.addRange(r);
  try{document.execCommand('copy');}catch(e){}
  s.removeAllRanges();
}
// 태그는 서식이 필요 없다. 평문만 쓰면 어느 입력칸에 넣어도 그대로 들어간다.
function copyText(s,b){
  var ok=function(){
    var old=b.textContent;
    b.classList.add('done'); b.textContent='\\uBCF5\\uC0AC\\uB428';
    setTimeout(function(){b.textContent=old;b.classList.remove('done');},900);
  };
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(s).then(ok,function(){fallbackText(s);ok();});
  } else { fallbackText(s); ok(); }
}
function fallbackText(s){
  var t=document.createElement('textarea');
  t.value=s; t.style.position='fixed'; t.style.left='-9999px';
  document.body.appendChild(t); t.select();
  try{document.execCommand('copy');}catch(e){}
  document.body.removeChild(t);
}
document.querySelectorAll('button.tag').forEach(function(b){
  b.onclick=function(){copyText(b.dataset.tag,b);};
});
document.querySelectorAll('button[data-tags]').forEach(function(b){
  b.onclick=function(){copyText(b.dataset.tags,b);};
});
document.querySelectorAll('button[data-t]').forEach(function(b){
  b.onclick=function(){
    var el=document.getElementById(b.dataset.t);
    var ok=function(){
      b.textContent='\\uBCF5\\uC0AC\\uB428'; b.className='done';
      setTimeout(function(){b.textContent='\\uBCF5\\uC0AC';b.className='';},1500);
    };
    var p=payload(el);
    if(navigator.clipboard&&window.ClipboardItem){
      navigator.clipboard.write([new ClipboardItem({
        'text/html': new Blob([p.html],{type:'text/html'}),
        'text/plain': new Blob([p.text],{type:'text/plain'})
      })]).then(ok,function(){legacy(el);ok();});
    } else { legacy(el); ok(); }
  };
});
// 이미지 복사: 그림 데이터(image/png)만 싣는다. text/html 을 같이 실으면 스마트에디터가
// <img src="data:..."> 를 "허용되지 않는 형식의 이미지"로 빼 버린다(2026-09-27 사용자 실측).
// 캔버스로 다시 그려 PNG 로 만든다(클립보드 이미지는 PNG 만 받는다). Blob 대신 Promise 를
// 넘겨 clipboard.write 를 클릭 안에서 곧바로 부른다 — 비동기 뒤로 미루면 사용자 동작이 끊긴다.
document.querySelectorAll('button.imgcopy').forEach(function(b){
  b.onclick=function(){
    var img=b.parentNode.parentNode.querySelector('img'), old=b.textContent;
    var fail=function(){b.textContent='\\uBCF5\\uC0AC \\uC2E4\\uD328';};
    if(!(navigator.clipboard&&window.ClipboardItem)){fail();return;}
    var png=new Promise(function(res,rej){
      var c=document.createElement('canvas');
      c.width=img.naturalWidth; c.height=img.naturalHeight;
      c.getContext('2d').drawImage(img,0,0);
      c.toBlob(function(x){if(x)res(x);else rej();},'image/png');
    });
    navigator.clipboard.write([new ClipboardItem({'image/png':png})]).then(function(){
      b.textContent='\\uBCF5\\uC0AC\\uB428'; b.classList.add('done');
      setTimeout(function(){b.textContent=old;b.classList.remove('done');},1500);
    },fail);
  };
});
"""


CHROME_PATHS = (
    r'%s\Google\Chrome\Application\chrome.exe' % os.environ.get('ProgramFiles', ''),
    r'%s\Google\Chrome\Application\chrome.exe' % os.environ.get('ProgramFiles(x86)', ''),
    r'%s\Google\Chrome\Application\chrome.exe' % os.environ.get('LOCALAPPDATA', ''),
    r'%s\Microsoft\Edge\Application\msedge.exe' % os.environ.get('ProgramFiles(x86)', ''),
    r'%s\Microsoft\Edge\Application\msedge.exe' % os.environ.get('ProgramFiles', ''),
)

# 화면 크기. 높이 1100은 제목·판정·경고·'숫자로 보면' 카드까지 담기는 값이다
# (경고가 0~2줄로 지역마다 달라 여유를 뒀다). 하단 네비게이션은 position:fixed라
# 창 높이와 무관하게 항상 바닥에 깔리므로, 그 높이만큼 잘라낸다.
SHOT_W, SHOT_H, SHOT_SCALE = 1100, 3400, 2
NAV_CSS_H = 112


def find_chrome():
    for p in CHROME_PATHS:
        if p and os.path.exists(p):
            return p
    return None


# 리포트 머리 캡처 폭. 리포트는 1024px 부터 두 단(왼쪽 머리·오른쪽 본문)으로 바뀌어(2026-10 홈·리포트 개편), 1100 폭으로
# 찍으면 덩어리 자르기가 머리 끝을 못 찾고 페이지 전체가 한 장으로 들어갔다(10-08 광주·전남 초안, 대표 지적 10-09).
# 한 단으로 나오는 폭에서 찍는다 — 판정·결론 한 줄·'앞으로 해마다 들어올 입주' 막대까지가 첫 긴 덩어리다.
ZONE_HEAD_W = 1000


def capture_zone(z):
    """지역 리포트 화면을 떠서 초안에 넣을 이미지를 만든다.

    매주 사람이 브라우저를 열어 캡처하고 하단 네비게이션을 잘라내던 작업이다.
    16개 시도를 도는 시리즈라 16주 내내 반복된다 — 자동화할 값이 충분하다.

    합성 이미지를 그리지 않고 **실제 화면**을 뜨는 이유: 블로그 독자가 사이트를
    알아보게 하려는 것이다. 숫자만 필요하면 본문 표로 충분하다.

    Chrome이 없거나 실패하면 None을 돌려주고 초안은 그대로 나간다 —
    이미지 때문에 발행이 막히면 안 된다.
    """
    extra = {}
    exe = find_chrome()
    if not exe:
        return None, extra, 'Chrome/Edge를 찾지 못했습니다'
    out = os.path.join(OUT, 'capture-%s.png' % z)
    url = '%s/zone/%s/' % (SITE, quote(z))
    # ⚠️ 지난주 캡처를 먼저 지운다. drafts/는 gitignore라 파일이 계속 남는데,
    # exists()만 보면 크롬이 이번에 아무것도 못 써도 옛 파일이 성공으로 통과한다.
    # 그 결과가 "몇 주 전 화면을 발행 글에 끌어다 놓기"라 조용히 틀린다.
    try:
        if os.path.exists(out):
            os.remove(out)
    except OSError as e:
        return None, extra, '지난 캡처를 지우지 못했습니다: %s' % e
    try:
        proc = subprocess.run(
            [exe, '--headless=new', '--disable-gpu', '--hide-scrollbars',
             '--force-device-scale-factor=%d' % SHOT_SCALE,
             '--window-size=%d,%d' % (ZONE_HEAD_W, SHOT_H),
             '--screenshot=%s' % out, url],
            timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return None, extra, '캡처 실행 실패: %s' % e
    if proc.returncode != 0:
        return None, extra, '캡처 실패(크롬 종료코드 %s) — 네트워크·사이트 상태 확인' % proc.returncode
    if not os.path.exists(out):
        return None, extra, '캡처 파일이 생기지 않았습니다(네트워크 확인)'
    try:
        from PIL import Image
        full = Image.open(out).convert('RGB')
        w, h = full.size
        body = full.crop((0, 0, w, max(1, h - NAV_CSS_H * SHOT_SCALE)))
        body.crop((0, 0, w, _cut_after_cards(body))).save(out)

    except Exception as e:
        return os.path.relpath(out, ROOT), extra, '다듬기 실패(원본 그대로): %s' % e
    # 분기별 표와 다른 지역 판정표도 같이 뽑는다. 매주 손으로 자르면 결국 빠뜨린다(2026-08-16 사용자).
    # ⚠️ 화면 덩어리 순번이 아니라 **섹션 제목**으로 고른다(2026-09-27). 순번 방식(카드=1, 표=2, 다른
    # 지역=4)은 리포트에 '시세도 함께' 칸이 들어오자 한 칸 밀려, 세종 편 초안의 판정표 자리에 시세
    # 카드 두 칸이 찍혔다(대표가 발견). 리포트에는 칸이 계속 붙는다(시군구 주간 표 요청 D4).
    for kind, key in ZONE_SECTIONS.items():
        t = os.path.join(OUT, 'capture-%s-%s.png' % (z, kind))
        err = _shoot_section(exe, z, key, t)
        if err:
            print('  ⚠ [%s] 캡처 생략 — %s' % (kind, err))
            continue
        extra[kind] = os.path.relpath(t, ROOT)
    return os.path.relpath(out, ROOT), extra, None


# 캡처할 리포트 칸 → 그 섹션의 제목(h2)에 들어 있는 말. make_sido_pages.py 가 굽는 제목이다.
ZONE_SECTIONS = {'표': '분기별 공급', '판정표': '다른 지역'}


def _section_page(z, key):
    """저장소의 zone/<지역>/index.html 에서 제목에 key 가 든 섹션 하나만 떼어 캡처용 페이지로 만든다.

    머리말의 스타일·폰트·표 스크립트는 그대로 두고 GA 스크립트만 뺀다(캡처가 방문으로 잡히지 않게). 상대 주소가
    풀리도록 base 를 그 리포트 폴더로 둔다. 판정표 칸 아래의 '돌아가기' 링크 줄은 뺀다. 없으면 None.
    """
    f = os.path.join(ROOT, 'zone', z, 'index.html')
    if not os.path.exists(f):
        return None
    t = io.open(f, encoding='utf-8').read()
    m = re.search(r'<head>(.*?)</head>', t, re.S)
    # GA 스크립트만 뺀다(캡처가 방문으로 잡히지 않게). 표 동작 스크립트는 남긴다 — 분기별 표는 스크롤 상자라,
    # 그 스크립트가 최근·미래 분기 쪽으로 스크롤해 둬야 사이트와 같은 화면이 찍힌다.
    head = re.sub(r'<script\b[^>]*>(?:(?!</script>).)*?(?:gtag|googletagmanager|ga_off)(?:(?!</script>).)*</script>|<script[^>]*googletagmanager[^>]*></script>', '',
                  m.group(1) if m else '', flags=re.S)
    sec = next((s.group(0) for s in re.finditer(r'<section\b[^>]*>.*?</section>', t, re.S)
                if re.search(r'<h2[^>]*>[^<]*%s' % re.escape(key), s.group(0))), None)
    if not sec:
        return None
    sec = re.sub(r'<p\b[^>]*>\s*<a class="zback".*?</p>', '', sec, flags=re.S)
    # 사이트는 스타일을 루트 기준 주소(/app.css)로 부른다. 로컬 파일에서는 드라이브 루트로 풀리므로,
    # 기준 주소를 저장소 루트로 두고 '="/…'를 상대 주소로 바꾼다('="//…' 외부 주소는 그대로).
    head = re.sub(r'(=\s*")/(?!/)', r'\1', head)
    import urllib.request
    base = 'file:' + urllib.request.pathname2url(ROOT) + '/'
    return ('<!doctype html><html lang="ko"><head><base href="%s">%s'
            '<style>main{padding:20px 0}</style></head><body><main id="main">%s</main></body></html>'
            % (base, head, sec))


def _shoot_section(exe, z, key, out):
    """_section_page 를 헤드리스 크롬으로 찍고 배경 여백을 잘라 out 에 저장한다. 실패 사유 또는 None."""
    page = _section_page(z, key)
    if not page:
        return "리포트에서 '%s' 칸을 찾지 못했습니다" % key
    tmp = os.path.join(OUT, '_capture-section.html')
    try:
        if os.path.exists(out):
            os.remove(out)                   # 지난 캡처가 성공처럼 남지 않게(capture_zone 과 같은 이유)
        io.open(tmp, 'w', encoding='utf-8').write(page)
        import urllib.request
        subprocess.run([exe, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                        '--force-device-scale-factor=%d' % SHOT_SCALE,
                        '--window-size=%d,%d' % (SHOT_W, 2400), '--screenshot=%s' % out,
                        'file:' + urllib.request.pathname2url(tmp)],
                       timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(out):
            return '캡처 파일이 생기지 않았습니다'
        from PIL import Image, ImageChops
        im = Image.open(out).convert('RGB')
        bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
        box = ImageChops.difference(im, bg).point(lambda v: 255 if v > 12 else 0).getbbox()
        if not box:
            return '빈 화면이 찍혔습니다'
        pad = 12 * SHOT_SCALE
        im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                 min(im.size[0], box[2] + pad), min(im.size[1], box[3] + pad))).save(out)
        return None
    except Exception as e:
        return '%s: %s' % (type(e).__name__, e)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# /#stats-market 의 주간 상승·하락 TOP 10 과 시군구 타일 지도 — 매주 글에 넣는 두 장.
#
# 예전에는 운영 사이트를 통째로 한 장 찍고 **픽셀 오프셋**(지도 높이 3130, TOP10 은 지도 위 782)으로 잘랐다.
# 2026-10-05~06 홈 개편(지도 모드 셋·날짜 칩·좁은 폭에서 TOP10 두 표가 세로로 쌓임)으로 높이가 바뀌자, 10-08 초안의
# 'TOP10' 칸에는 경기 타일 지도 조각이, '지도' 칸에는 위가 잘리고 푸터가 붙은 그림이 들어갔다(대표 지적 10-09).
# 그래서 이제 **요소로** 찍는다: 저장소를 로컬 서버로 띄워 캡처용 홈 사본을 열고, 그 사본에 넣은 스크립트가 찍을 상자
# (`#week-map .map-rank` / `.map-scroll`) 하나만 보이게 한 뒤, 배경과 다른 영역만 잘라 낸다(지역 편 _shoot_section 과
# 같은 생각). 화면 배치가 또 바뀌어도 상자 이름만 같으면 따라간다. 상자를 못 찾으면 그림 없이 사유를 돌려준다.
WEEKLY_SHOTS = {'top10': '.map-rank', 'map': '.map-scroll'}
# 캡처용 사본에 넣는 스크립트. 상자가 그려질 때까지 기다렸다가 나머지를 모두 감춘다(visibility — 자리는 그대로라
# 상자 모양이 사이트와 같다). 끝내 못 찾으면 제목에 표지를 남겨 빈 그림이 성공으로 넘어가지 않게 한다.
_SHOT_JS = """<script>(function(){
var sel=(location.search.match(/[?&]sel=([^&]+)/)||[])[1];sel=sel&&decodeURIComponent(sel);
function go(n){var wm=document.getElementById('week-map'),el=wm&&wm.querySelector(sel);
 if(!el||!el.offsetHeight){if(n<200)return setTimeout(function(){go(n+1)},100);document.title='NO-SHOT';return;}
 el.classList.add('__shot');var st=document.createElement('style');
 st.textContent='body *{visibility:hidden!important;animation:none!important;transition:none!important}'
  +'.__shot,.__shot *{visibility:visible!important}';
 document.head.appendChild(st);window.scrollTo(0,0);document.title='SHOT-OK';}
window.addEventListener('load',function(){go(0)});})();</script>"""


def _weekly_shot_page():
    """index.html 사본 + 캡처 스크립트. drafts/(gitignore) 에 두고 저장소 루트를 서버로 띄워 연다 — 사이트가
    '/app.css'·'/data-core.js' 같은 루트 기준 주소를 쓰므로 file:// 로는 안 열린다."""
    t = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    if '</body>' not in t:
        return None
    return t.replace('</body>', _SHOT_JS + '</body>', 1)


def capture_weekly_map():
    """주간 상승·하락 TOP 10 한 장과 전국 시군구 지도 한 장을 떠서 (지도, TOP10, 사유)를 돌려준다.

    실패하면 앞 둘이 None — 이미지 때문에 초안 생성이 막히면 안 된다. 지난 회차의 잘린 그림이 성공처럼 남지 않게
    시작할 때 지운다.
    TOP10 을 넣는 이유: 순위와 **전주 대비 순위 변동**(▲18위)까지 나와서 표만으로 이야기가 된다(2026-08-30 사용자).
    지도는 한 장으로 넣는다(2026-09-07 사용자: 둘로 잘리니 보기 안 좋다).
    """
    exe = find_chrome()
    if not exe:
        return None, None, 'Chrome/Edge를 찾지 못했습니다'
    outs = {'map': os.path.join(OUT, 'weekly-sgg.png'), 'top10': os.path.join(OUT, 'weekly-top10.png')}
    for f in outs.values():
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            pass
    page = _weekly_shot_page()
    if not page:
        return None, None, 'index.html 에서 </body> 를 찾지 못했습니다'
    os.makedirs(OUT, exist_ok=True)
    tmp_html = os.path.join(OUT, '_capture-home.html')
    io.open(tmp_html, 'w', encoding='utf-8').write(page)
    import functools
    import http.server
    import socketserver
    import threading
    import urllib.parse

    class _Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=ROOT))
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    errs = {}
    try:
        from PIL import Image, ImageChops
        for key, sel in WEEKLY_SHOTS.items():
            out = outs[key]
            url = 'http://127.0.0.1:%d/drafts/_capture-home.html?sel=%s#stats-market' % (port, urllib.parse.quote(sel))
            raw = out + '.raw.png'
            try:
                subprocess.run(
                    [exe, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                     '--force-device-scale-factor=%d' % SHOT_SCALE, '--virtual-time-budget=15000',
                     # 캡처가 방문으로 잡히지 않게 GA 주소를 막는다(사본의 스크립트는 그대로 둔다).
                     '--host-resolver-rules=MAP www.googletagmanager.com ~NOTFOUND, MAP *.google-analytics.com ~NOTFOUND',
                     '--window-size=%d,%d' % (SHOT_W, SHOT_H), '--screenshot=%s' % raw, url],
                    timeout=150, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if not os.path.exists(raw):
                    errs[key] = '캡처 파일이 생기지 않았습니다'
                    continue
                im = Image.open(raw).convert('RGB')
                bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
                box = ImageChops.difference(im, bg).point(lambda v: 255 if v > 12 else 0).getbbox()
                # 거의 화면 전체가 남았다면 감추기가 안 된 것이다(상자를 못 찾음) — 그 그림은 쓰지 않는다.
                if not box or (box[3] - box[1]) > im.size[1] * 0.97:
                    errs[key] = "사이트에서 '%s' 상자를 찾지 못했습니다(화면 구조가 바뀌었을 수 있음)" % sel
                    continue
                pad = 12 * SHOT_SCALE
                im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                         min(im.size[0], box[2] + pad), min(im.size[1], box[3] + pad))).save(out)
            finally:
                try:
                    os.remove(raw)
                except OSError:
                    pass
    except Exception as e:
        return None, None, '캡처 실패: %s: %s' % (type(e).__name__, e)
    finally:
        srv.shutdown()
        srv.server_close()
        try:
            os.remove(tmp_html)
        except OSError:
            pass
    m = os.path.relpath(outs['map'], ROOT) if os.path.exists(outs['map']) else None
    t = os.path.relpath(outs['top10'], ROOT) if os.path.exists(outs['top10']) else None
    return m, t, ('; '.join('%s: %s' % kv for kv in errs.items()) or None)


def _blocks(im, gap=70, keep=60):
    """배경 여백으로 끊어 본 내용 덩어리 목록 [(시작, 끝, 높이)].

    지역 페이지는 덩어리 구조가 지역과 무관하게 규칙적이다(2026-08-16 실측,
    서울·대구·제주 대조):
        0) 머리말      경고 줄 수에 따라 373~444로 **여기만 달라진다**
        1) 숫자로 보면   584
        2) 분기별 공급 표 1246
        3) 어떻게 계산했나 577
        4) 다른 지역     704
    그래서 픽셀 좌표가 아니라 **순번**으로 잡으면 머리말 길이가 달라져도
    따라간다. 고정 좌표는 경기(경고 0줄)에서 이미 한 번 깨졌다.
    """
    w, h = im.size
    px = im.load()
    bg = px[5, 5]
    xs = list(range(0, w, max(1, w // 200)))

    def is_bg(y):
        return all(abs(px[x, y][0] - bg[0]) + abs(px[x, y][1] - bg[1])
                   + abs(px[x, y][2] - bg[2]) <= 24 for x in xs)

    flags = [is_bg(y) for y in range(h)]
    out, y = [], 0
    while y < h:
        if flags[y]:
            y += 1
            continue
        s = y
        while y < h:
            if flags[y]:
                g = y
                while g < h and flags[g]:
                    g += 1
                if g - y >= gap:
                    break
                y = g
            else:
                y += 1
        if y - s >= keep:
            out.append((s, y, y - s))
        y += 1
    return out


def _cut_after_cards(im):
    """'숫자로 보면' 카드 블록 바로 뒤에서 자를 y를 찾는다.

    고정 좌표로 자를 수 없다. 경고 문구가 지역마다 0~2줄이라 내용이 위아래로
    밀린다 — 경기(경고 없음)로 뜨면 아래 표가 중간에 잘렸다(2026-08-15 실측).

    카드를 색으로 찾을 수는 없다 — 카드 안쪽이 페이지 배경과 같은 색이고
    얇은 테두리로만 구분된다(실측). 대신 **덩어리 길이**로 찾는다. 머리말과
    경고는 짧게 끊기지만 카드 블록은 여백 없이 길게 이어진다.

    실측(폭 2200, 배율 2): 카드 블록 506px 연속, 머리말·경고 덩어리는 최대
    166px. 섹션 사이 여백 75px, 줄 사이 40px 안팎이라 70에서 갈린다.
    그래서 '450px 이상 이어진 첫 덩어리'가 카드 블록이고, 그 뒤에서 자른다.
    """
    w, h = im.size
    px = im.load()
    bg = px[5, 5]
    xs = list(range(0, w, max(1, w // 200)))
    GAP, BLOCK, PAD = 70, 450, 24

    def is_bg(y):
        return all(abs(px[x, y][0] - bg[0]) + abs(px[x, y][1] - bg[1])
                   + abs(px[x, y][2] - bg[2]) <= 24 for x in xs)

    flags = [is_bg(y) for y in range(h)]
    y = 0
    while y < h:
        if flags[y]:                       # 여백은 건너뛴다
            y += 1
            continue
        s = y
        while y < h:                       # 내용 덩어리의 끝을 찾는다
            if flags[y]:
                g = y
                while g < h and flags[g]:
                    g += 1
                if g - y >= GAP:           # 섹션 여백을 만났다 → 덩어리 끝
                    break
                y = g                      # 줄 사이 여백은 덩어리 안으로 본다
            else:
                y += 1
        if y - s >= BLOCK:
            return min(h, y + PAD)
        y += 1
    return h                               # 못 찾으면 건드리지 않는다


def rivals(keyword, n=5):
    """그 키워드로 지금 상위에 있는 블로그 글 제목을 가져온다.

    제목을 다듬는 순간에 정작 경쟁 글이 안 보인다는 게 지금까지의 병목이었다.
    브라우저를 따로 열어 검색하고 초안으로 돌아오는 왕복이 매주 반복된다.
    같은 화면에 붙여두면 (1) 어떤 각도가 이미 점령됐는지, (2) 우리 제목이
    상위 글과 너무 닮지 않았는지(유사문서)를 한눈에 본다.

    키가 없거나 네트워크가 막히면 조용히 건너뛴다 — 부가 정보 때문에
    초안 생성 자체가 실패하면 주객이 전도된다.
    """
    try:
        import naver_serp as NS
        d = NS._get('blog', keyword, display=n)
        return [(NS._clean(it.get('title', '')), NS._clean(it.get('bloggername', '')))
                for it in (d.get('items') or [])]
    except (Exception, SystemExit):
        # ⚠️ SystemExit을 같이 잡아야 한다 — naver_serp._get은 키가 없으면
        # SystemExit(BaseException)을 던지고, 그건 `except Exception`을 그냥
        # 통과한다. 키 없는 PC에서 초안 파일이 아예 안 생기던 원인이었다.
        # naver_serp.probe()는 반대로 일부러 다시 올려보내므로 거기는 그대로 둔다.
        return None


def rival_panel(keyword):
    rows = rivals(keyword)
    if rows is None:
        return ('<p class="note">🔍 <b>%s</b> 경쟁 글을 못 불러왔습니다. '
                'NAVER_CLIENT_ID/SECRET 환경변수를 확인하세요 '
                '(없어도 초안 자체는 정상입니다).</p>' % esc(keyword))
    if not rows:
        return '<p class="note">🔍 <b>%s</b> 상위 결과 없음.</p>' % esc(keyword)
    li = ''.join('<li>%s <span class="src">%s</span></li>' % (esc(t), esc(b))
                 for t, b in rows)
    return ('<div class="rival"><b>🔍 지금 “%s” 상위 글</b>'
            '<ol>%s</ol>'
            '<span class="src">제목이 이 중 하나와 닮았다면 바꾸세요 — '
            '유사문서로 묶이면 둘 다 손해입니다.</span></div>' % (esc(keyword), li))


# 발행 전 자가 점검 — 기억에 의존하지 않게 초안에 박아 둔다.
# 코드 주석에 외부 강의 화면 URL이 근거로 적혀 있던 사고가 있었다(2026-08-15
# 리뷰 지적). 원인은 악의가 아니라 '판단 근거를 밝히려는 선의'였고, 발행 글에도
# 같은 자리가 있다 — 어디서 봤는지를 적고 싶어지는 자리.
# 근거는 사실만 적으면 온전하다: 누구의 강의였는지 없이도 "인허가가 적정물량의
# 42%에 그쳤다"는 그 자체로 검증 가능하다.
SOURCE_CHECK = (
    '<p class="note"><b>발행 전 자가 점검</b><br>'
    '□ 특정 인물·강의·유료 콘텐츠를 출처로 적지 않았는가<br>'
    '□ 수치의 출처가 국토교통부·한국부동산원·한국은행 등 공개 원천으로만 '
    '표기됐는가</p>')


def field(lab, tid, html, cls=''):
    return ('<div class="field"><div class="lab"><b>%s</b>'
            '<button data-t="%s">복사</button></div>'
            '<div class="box %s" id="%s">%s</div></div>') % (lab, tid, cls, tid, html)


def tagfield(tags):
    """태그는 한 줄로 붙여넣으면 제대로 안 들어간다(2026-08-14 사용자 실측).

    네이버 태그 칸은 하나 넣고 Enter를 치는 구조라, 쉼표로 이어붙인 한 줄을
    붙이면 통째로 한 태그가 되거나 앞뒤 공백이 태그에 섞인다. 붙여넣기 동작을
    추측해 맞추는 대신, 칩을 눌러 하나씩 복사하게 만든다 — 에디터가 어떻게
    처리하든 결과가 같다. 전체 복사는 남기되 공백 없이 잇는다.
    """
    chips = ''.join('<button class="tag" data-tag="%s">%s</button>' % (esc(t), esc(t))
                    for t in tags)
    return ('<div class="field"><div class="lab"><b>태그 %d개</b>'
            '<button data-tags="%s">전체 복사</button>'
            '<span class="src">칩을 누르면 하나씩 복사됩니다</span></div>'
            '<div class="tags">%s</div></div>'
            % (len(tags), esc(','.join(tags)), chips))


IMG_MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


def _img_path(rel):
    """캡처 함수는 ROOT 기준 상대 경로('drafts\\x.png')를, 이론 초안은 drafts/ 안의
    파일명('x.png')을 넘긴다. 둘 다 받는다."""
    if os.path.isabs(rel):
        return rel if os.path.exists(rel) else None
    for base in (ROOT, OUT):
        c = os.path.join(base, rel)
        if os.path.exists(c):
            return c
    return None


def img_gallery(items):
    """이미지를 초안 HTML 안에 직접 싣는다(base64).

    2026-09-27 사용자: 초안에는 파일 이름만 적혀 있어 지도가 만들어졌는지도 안
    보였다. 초안 파일 하나만 다른 기기로 보내도 그림이 빠지지 않게, 경로 링크가
    아니라 데이터를 박는다.

    ⚠️ 복사 상자(field) 바깥에 둔다. 본문 복사에 data URI 이미지가 섞이면
    클립보드가 수 MB가 되고, 스마트에디터가 그것을 어떻게 받는지 확인할 수 없다.
    본문의 [여기에 … 이미지] 자리 표시자와 같은 이름을 캡션에 달아 자리를 맞춘다.
    items: [(경로 또는 None, 자리 이름)]. None 은 건너뛰고(캡처를 안 뜬 회차),
    경로가 있는데 파일이 없으면 그 사실을 적는다(조용히 빠지면 없는 줄 모른다).
    """
    cards = []
    for rel, label in items:
        if not rel:
            continue
        path = _img_path(rel)
        if not path:
            cards.append('<p class="note">⚠ [%s] 이미지 파일이 없습니다: <code>%s</code></p>'
                         % (esc(label), esc(rel)))
            continue
        mime = IMG_MIME.get(os.path.splitext(path)[1].lower(), 'image/png')
        with io.open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        # 브라우저의 오른쪽 클릭 '이미지 복사'·끌어 놓기는 <img src="data:…"> HTML 을 같이
        # 실어 보내고, 스마트에디터는 그것을 "허용되지 않는 형식의 이미지"로 뺀다(2026-09-27
        # 사용자 실측). 그래서 그림 데이터(image/png)만 싣는 버튼을 단다(JS 의 button.imgcopy).
        cards.append('<figure class="shot"><img src="data:%s;base64,%s" alt="%s">'
                     '<figcaption><button class="imgcopy">이미지 복사</button> '
                     '<b>[%s]</b> · 복사 후 에디터에 붙여넣기. 안 되면 drafts 폴더의 '
                     '<code>%s</code> 파일을 끌어 놓으세요</figcaption></figure>'
                     % (mime, data, esc(label), esc(label), esc(os.path.basename(path))))
    if not cards:
        return ''
    return '<div class="shots">%s</div>' % ''.join(cards)


def render(p, d1, d2):
    S = []
    S.append('<!doctype html><html lang="ko"><meta charset="utf-8">')
    S.append('<title>네이버 블로그 초안 — %s</title>' % p)
    S.append('<style>%s</style>' % CSS)
    S.append('<h1>네이버 블로그 초안 — %s 기준</h1>' % p)
    S.append('<p class="hint">[복사] → 스마트에디터에 붙여넣기 → 이미지 끌어놓기 → 발행. '
             '표·굵은 글씨는 붙여넣을 때 그대로 살아납니다.</p>')

    # d2는 --week(과거 회차 채우기)에서 None이다 — 그때는 시세 글만 만든다.
    pairs = [('① 주간 시세 + 아공맵 해설', d1)]
    if d2:
        pairs.append(('② 지역 심층 — %s' % d2.get('seq', ''), d2))
    for i, (head, d) in enumerate(pairs, 1):
        S.append('<section class="draft"><h2>%s</h2>' % head)
        S.append(rival_panel(d['kw']))
        S.append(field('제목', 't%d' % i, esc(d['title']), 't'))
        if i == 1:
            # 숫자를 기본값으로 두되(기계가 확실히 아는 값), 해석을 쓴 뒤에는
            # 결론절로 바꾸는 게 낫다. 검색결과는 30자쯤만 보여줘서 뒤쪽 숫자가
            # 잘리고, 무엇보다 +0.21%가 큰지 작은지는 들어와야 안다. 결론은
            # 클릭 전에도 뜻이 통한다 — 우리 제목으로 검색했을 때 1위였던 글이
            # 그 형태였다(2026-08-15).
            S.append('<p class="note">✍ 해석을 쓴 뒤 <code>|</code> 뒤를 <b>결론 한 줄</b>로 '
                     '바꾸세요. 예: <code>[한국부동산원] 주간 아파트가격 동향(9월 둘째 주) | '
                     '강남 3구가 모두 내렸고 22개 구는 올랐습니다</code>. 앞부분은 이 장르의 '
                     '관례라 그대로 두고, 숫자는 검색결과에서 잘리니 결론으로 바꿉니다.</p>')
        S.append(field('본문', 'b%d' % i, d['body']))
        # imgnote는 완결된 안내문이다. 예전엔 문장 안에 끼워 넣는 구조였는데,
        # 이미지가 여러 장이 되면서 문장이 깨졌다(2026-08-16).
        S.append('<p class="note">📎 %s</p>' % d['imgnote'])
        S.append(img_gallery(d.get('imgs') or []))
        # 태그는 맨 아래 — 본문·이미지를 다 넣은 뒤 발행 직전에 넣는 순서라서(2026-10-09 대표).
        S.append(tagfield(d['tags']))
        S.append('</section>')

    S.append('<p class="hint">같은 내용을 사이트·인스타와 똑같이 올리면 네이버가 '
             '유사문서로 볼 수 있습니다. 첫 두세 문장만이라도 직접 고쳐 쓰면 '
             '안전합니다.</p>')
    S.append(SOURCE_CHECK)
    S.append('<script>%s</script></html>' % JS)
    return '\n'.join(S)


def _week_back(argv):
    """--week N — N주 전 회차로 만든다(기본 0 = 최신).

    발행이 밀리면 지난 주차가 통째로 비는데, 생성기가 최신 회차만 만들 수 있으면
    그 구멍을 영영 못 메운다. 실제로 2주가 비었다(2026-08-30).
    시세 글은 그 주의 기록이라 뒤늦게라도 채워 두는 게 맞다 — 기록이 이어져야
    다음 주 글이 "지난주에 이렇게 썼는데"라고 이어받을 수 있다.

    ⚠️ N>0이면 지역 편은 만들지 않는다. 순회는 발행 순서를 따라가는 것이라
    과거 회차를 채운다고 한 칸 더 넘기면 어긋난다.
    """
    if '--week' not in argv:
        return 0
    i = argv.index('--week')
    try:
        return max(0, int(argv[i + 1]))
    except (IndexError, ValueError):
        raise SystemExit('--week 뒤에 숫자를 줄 것 (0=최신, 1=한 주 전)')


def _cut_weekly(adv, back):
    """--week N: 주간 계열을 N주 앞에서 자른 adv 사본. 시도 행(rows)만이 아니라 서울 구(seoul)·시군구(sgg) 행도
    **같은 조사일까지** 자른다(전수리뷰 #74). 예전엔 rows 만 잘라, 9/14 회차 글의 '서울 안에서는 …'과 'TOP 10 가운데
    순위가 가장 많이 뛴 곳'이 9/21 값을 실었다. 행 수가 아니라 날짜로 자르므로 계열 길이가 달라도 맞는다.

    ⚠️ 월간 지표(이번 주의 지표 절)는 자르지 않는다 — 그 주 발표일 이전 달로 제한할지는 정하지 않았다.
    """
    if not back:
        return adv
    W = adv['weekly']
    rows = W['rows'][:len(W['rows']) - back]
    cut = rows[-1]['p']
    W2 = dict(W, rows=rows)
    for k in ('seoul', 'sgg'):
        if (W.get(k) or {}).get('rows'):
            W2[k] = dict(W[k], rows=[r for r in W[k]['rows'] if r['p'] <= cut])
    return dict(adv, weekly=W2)


def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        print(__doc__)
        return 0
    adv, sts = M.load()
    # 점수는 배치가 구워 ADV.sido에 실어 둔 것을 그대로 읽는다 — 사이트 화면과
    # 같은 값을 써야 하므로 여기서 다시 계산하지 않는다.
    calc = (adv or {}).get('sido')
    if not calc or not calc.get('zones'):
        raise SystemExit('ADV.sido가 없다 — 배치(update_adv_data.py --seed-sido)를 먼저 돌릴 것')
    rows = calc['zones']

    back = _week_back(sys.argv)
    wrows = adv['weekly']['rows']
    if back >= len(wrows):
        raise SystemExit('주간 계열이 %d회차뿐이다 — --week %d 는 없다' % (len(wrows), back))
    adv = _cut_weekly(adv, back)
    p = adv['weekly']['rows'][-1]['p']

    d1 = draft_weekly(adv, sts, shot=not back)
    if back:
        # 과거 회차 채우기 — 시세 글만 만든다.
        d2 = None
        commit_rotation = lambda: None
    else:
        # 심층은 개별 시도만 순회한다(집계 3종 제외).
        pool = SZ.zone_order(rows)
        pick, seq, total, commit_rotation = pick_zone(pool)
        d2 = draft_zone(adv, sts, pick, seq, total)

    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    path = os.path.join(OUT, 'naver-%s.html' % p)
    html = render(p, d1, d2)   # 파일을 열기 전에 끝낸다(write_draft 주석)

    # 손댄 초안은 덮지 않는다. drafts/는 gitignore라 덮어쓰면 되돌릴 데가 없다
    # (2026-08-14에 실제로 날렸다 — 트랜스크립트에서 겨우 건졌다).
    # 판별은 draft_edited — 지문이 어긋나거나, 지문 없는 옛 초안에서 자리 표시자(주간 해석·지역 전망) 가운데 하나라도
    # 사라졌으면 사람이 손댄 것이다. 비켜 쓸 .new.html 도 손댔으면 그다음 자리(.new2.html …)에 쓴다(리뷰 D1).
    if os.path.exists(path) and '--force' not in sys.argv:
        old = io.open(path, encoding='utf-8').read()
        if draft_edited(old, html, DRAFT_PLACEHOLDERS):
            alt = side_path(path, html, DRAFT_PLACEHOLDERS)
            if alt is None:
                raise SystemExit('⚠ %s 와 비켜 쓸 자리 %d개(.new.html~.new%d.html)가 모두 손본 초안이다 — 아무것도 덮지 '
                                 '않았다. 필요 없는 것을 지우거나 --force 로 덮을 것.'
                                 % (os.path.basename(path), SIDE_MAX, SIDE_MAX))
            write_draft(alt, stamp_draft(html))
            desktop_shortcut(path, SHORTCUTS['naver'])   # 발행할 것은 손본 쪽이다
            print('⚠ %s 는 이미 손댄 흔적이 있어 그대로 뒀다.' % os.path.basename(path))
            print('  새 초안은 %s 에 썼다. 비교 후 필요한 것만 옮길 것.'
                  % os.path.relpath(alt, ROOT))
            print('  덮어쓰려면 --force(썸네일은 따로 --force-thumb).')
            # 순회는 소비하지 않는다 — 이 지역 글은 아직 안 나갔다.
            return 0

    write_draft(path, stamp_draft(html))
    if desktop_shortcut(path, SHORTCUTS['naver']):
        print('  바탕화면 바로가기: %s' % SHORTCUTS['naver'])
    commit_rotation()          # 발행이 확인된 지역 편만 캐시에 적는다(지금 고른 지역은 안 적는다)
    print('네이버 초안 생성: %s' % os.path.relpath(path, ROOT))
    print('  ① %s' % d1['title'])
    if d2:
        print('  ② %s  (%s)' % (d2['title'], d2['seq']))

    # 열지 않는다. 한 편을 쓰는 동안 여러 번 다시 만드는데 그때마다 창이 뜬다.
    # 볼 때는 --open 을 준다.
    if '--open' in sys.argv:
        try:
            import webbrowser
            webbrowser.open('file:///' + path.replace('\\', '/'))
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
