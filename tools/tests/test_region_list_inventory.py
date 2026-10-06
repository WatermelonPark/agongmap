# -*- coding: utf-8 -*-
"""지역 목록을 **전수로 훑어** 분류되지 않은 것이 있으면 실패한다.

왜 또 만드나. test_region_lists.py 는 목록을 하나씩 이름으로 적어 검사한다. 그
방식은 **적어 둔 것만** 지키므로, 새 목록이 생기거나 내가 못 본 목록이 있으면 그냥
빠진다. 실제로 그렇게 됐다 — 2026-09-12 에 지역 누락 셋을 고치며 그 시험을 만들었는데
BUBBLE_REGIONS 를 빠뜨렸고, 리뷰 세션이 전남광주를 지우고 전체 시험을 돌려도 200개가
전부 통과하는 것을 보여 줬다. 버블밴드에서 그 지역이 라이브에서 빠져 있었다. 네 번째
누락이었다.

내 판정이 틀린 구조도 같이 남긴다. 파일 단위로 훑고 파일 하나를 통과시키면, 그 파일
안의 **다른 목록**을 안 보게 된다. update_adv_data.py 는 지역명이 가장 많이 나오는
파일이라 1위로 걸렸는데, _GJ_OLD 주석 하나를 읽고 '원천이 옛 이름으로 주니 정당하다'며
파일 전체를 넘겼다. BUBBLE_REGIONS 는 그 안에 있었다.

그래서 이 시험은 **식별자 단위**로 본다. 그리고 목록마다 시험을 붙이는 대신, 목록이
둘 중 하나로 분류돼 있는지만 확인한다.

  FULL    모델 전체를 담아야 하는 것 — 집합이 sido_zones 와 같아야 한다
  PARTIAL 의도적으로 일부만 담는 것 — 이유를 적어 두고 검사에서 뺀다

어느 쪽도 아닌 이름이 나오면 실패한다. 새 목록을 만든 사람이 '이건 전부인가 일부인가'를
한 번 답하게 하는 것이 목적이다. 답을 적는 비용은 한 줄이고, 안 적었을 때 치르는 값은
지역 하나가 화면에서 조용히 사라지는 것이다.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sido_zones as SZ  # noqa: E402

# ⚠️ normpath 필수. 정규화하지 않으면 모든 경로가 'tools/tests/../..' 로 시작해
# 아래 SKIP_DIR 의 'tools/tests/' 에 걸려 **전부 스킵**된다 — 스캐너가 빈 목록을
# 돌려주고 위 두 시험이 조용히 통과한다. 만들자마자 그렇게 됐고 자기 확인 시험이
# 잡았다(2026-09-12).
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
MODEL = set(SZ.ORDER)
SIDO = set(z for z in SZ.ORDER if z not in SZ.AGG)
OLD = {'광주', '전남'}

# 모델 전체를 담아야 하는 목록. 여기 있는 것은 집합 일치를 강제한다.
FULL = {
    'MATRIX_REGIONS': MODEL,   # 홈 PC 표 모드 (2026-09-12 전남광주 누락)
    'WEEKLY_REGIONS': MODEL,   # 주간 시세 수집
    'BUBBLE_REGIONS': MODEL,   # 버블밴드 (2026-09-12 누락, 리뷰 세션 발견)
    'SIDO17': SIDO,            # 지표 페이지 (이름은 이력상 17)
    'DISPLAY_ORDER': MODEL,    # 시도 목록 표시 순서 정본 (2026-09-13 대표 결정)
    # 홈 인허가 표. 지금은 DISPLAY_ORDER 에서 파생해 리터럴이 없어 스캔되지 않는다. 누가 다시
    # 손 목록으로 되돌리면 여기서 모델 전체와 대조된다(2026-09-23: 옛 REG15 파생이라 전남광주가 빠졌었다).
    'PERMIT_REGIONS': MODEL,
    # 아래 둘은 2026-10-05 스캐너가 dict·튜플 목록을 보게 되면서 처음 잡혔다(리뷰 E4). 둘 다 지금 모델 전체와 같다.
    'REF_Q': MODEL,            # 적정물량 기준표 — 모델 지역의 정본 자체(ORDER = list(REF_Q))
    'TILE': MODEL,             # 주간 공유 이미지(make_weekly_share) 타일 배치 — 집계 3곳 포함 모든 판정 단위가 한 칸씩
}

# 일부만 담는 것이 의도인 목록. 왜 일부인지를 값으로 적는다.
PARTIAL = {
    'AGG': '집계 3곳(전국·수도권·지방)',
    'CAP': '수도권 3곳',
    'SUDO': '수도권',
    'REG_AGG': '집계 행',
    'METRO': '사이클 분석의 광역시 묶음',
    'PROVINCE': '사이클 분석의 도 묶음',
    'PRIORITY': '발행 순서를 앞당길 지역(나머지는 순부족 순)',
    'ZONE_REGIONS': '사이클 차트에 세울 대표 4곳',
    'SUPPLY_SIDO': 'WEEKLY_REGIONS 에서 파생(리터럴만 세면 일부로 보인다)',
    # ── 2026-10-05 스캐너 확장(dict·set·튜플 목록·frozenset·new Set)으로 처음 잡힌 것(리뷰 E4) ──
    # 제품 코드는 바꾸지 않았다. 각각 왜 모델 전체와 대조하지 않는지를 적는다.
    'EST': '적정물량을 기준표에 없어 추정한 지역(서울·경기·인천·세종·제주)만',
    'REGION': 'REF_Q 에서 파생한 수도권·지방 사상(리터럴은 수도권 3곳과 집계 이름뿐)',
    'THUMB_GROUP': '시도 → 썸네일 권역 사상. 값에 권역 이름(수도권)이 섞이고 집계는 뺀다 — 시도 전부가 있는지는 '
                   'test_post_thumb_ask.test_every_zone_has_a_thumb_group 이 모델과 대조한다',
    'THUMB_PALETTES': '썸네일 권역 이름이 키(수도권·강원·제주가 지역명과 겹칠 뿐)',
    'WEEKLY_TABLE': '주간 글 주요 지역 표 — 일부만 싣는 것이 의도. 이름이 모델에 있는지는 '
                    'test_blog_tools_review.test_weekly_table_names_are_model_names',
    'CITY_TAG': '도 지역의 대표 도시 태그(광역시·특별자치시는 이름 자체가 도시)',
    'SMALL': '시도 지도에서 칸이 작은 광역시·세종(행정 시도 지형 기준이라 광주가 따로)',
    'NATION_TILE': '전국 시군구 지도 칸 — 원천(행정 시도·시군구) 지리 배치, 판정 단위로 접는 것은 sgg_zone',
    'SIDO_PREFIX': '원천 시군구 코드 머리 → 행정 시도 17곳(광주·전남 따로). 판정 단위로 접는 것은 sgg_zone·MERGED_INTO',
    'SGG_PREFIX': 'weekly_moves 의 원천 코드 머리 → 행정 시도 17곳(홈 sidoOf 의 거울). 접기는 sgg_zone',
    'SHORT': 'gen_sido_geo 의 원천 행정 시도 이름 줄임(지도 원천 도구)',
    'BUBBLE_SHORT': '원천(KOSIS) 행정 시도 전체 이름 → 줄임. 판정 단위 목록은 BUBBLE_REGIONS(FULL)',
    'SGG_QNAME': '시군구 코드 → 이름(경기 광주시·세종·제주가 시도명과 같을 뿐)',
    'QUIZSETS': '퀴즈 문항 본문(보기에 지역명이 나올 뿐)',
    'BASIC_REGMAP': 'KOSIS 집계 행 이름 → 집계 3곳',
    'AGG_NOTE': '집계 3곳의 설명 문구',
    'SUM_RULES': '집계 3곳의 합 검사 규칙',
    'MERGED_INTO': '광주·전남 → 전남광주 접기(옛 이름 사상)',
}

# ⚠️ drafts/ 와 logs/ 는 **gitignore 대상인 로컬 산출물**이다. 초안은 발행 직전마다
# 다시 만들어지고 사람이 손으로 고치기도 하므로, 훑으면 이 시험의 결과가 '지금 로컬에
# 어떤 초안이 있느냐'에 따라 흔들린다. 저장소의 코드를 보는 시험이 로컬 파일에 기대면
# 안 된다(2026-09-12 마케팅 세션 제보 — 그 세션에서 한 번 실패한 뒤 재현되지 않았다).
SKIP_DIR = ('zone/', 'monthly/', 'moveins/', 'jeonse-ratio/', 'weekly/', 'cycle/',
            'share/', 'docs/', 'tools/data/', 'tools/cache/', 'tools/tests/',
            'drafts/', 'logs/')
SKIP_FILE = ('data.js', 'data-core.js', 'sido-geo.js')

# 선언 머리: `NAME = ` 다음에 리터럴([ ( {) 또는 frozenset( · set( · tuple( · list( · dict( · new Set( 로 감싼 리터럴.
# 본문은 정규식으로 자르지 않고 괄호 깊이로 짝을 찾는다(_body). 예전 정규식은 `[^\]\)]` 로 첫 닫는 괄호에서 멈추고 `{` 를
# 받지 않아 dict·set 리터럴과 튜플 목록([('서울', …), …])·frozenset((…)) 을 보지 못했다(2026-10-05 리뷰 E4 —
# make_naver_post.THUMB_GROUP·WEEKLY_TABLE, sido_zones.EST, home-app.js SMALL, refresh_cycle_data.SUDO 가 빠져 있었다).
HEAD = re.compile(
    r'(?:const\s+|var\s+|let\s+)?\b([A-Z_][A-Z0-9_]{2,})\s*(?::[^=\n]{0,80})?=\s*'
    r'(?:new\s+Set\s*|frozenset\s*|set\s*|tuple\s*|list\s*|dict\s*)?([\[\(\{])')


def _body(s, i, py):
    """s[i] 의 여는 괄호와 짝인 닫는 괄호까지의 안쪽. 문자열(파이썬 삼중 따옴표 포함)·주석 안의 괄호는 세지 않는다.
    짝이 없으면 None."""
    depth, q, j, n = 0, None, i, len(s)
    while j < n:
        c = s[j]
        if q:
            if len(q) == 3:
                k = s.find(q, j)
                j = n if k < 0 else k + 3
                q = None
                continue
            if c == '\\':
                j += 2
                continue
            if c == q or (c == '\n' and q != '`'):
                q = None
        elif py and s.startswith(("'''", '"""'), j):
            q = s[j:j + 3]
            j += 3
            continue
        elif c in '\'"`':
            q = c
        elif (py and c == '#') or (not py and s.startswith('//', j)):
            k = s.find('\n', j)
            j = n if k < 0 else k
            continue
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return s[i + 1:j]
        j += 1
    return None


def _decls(s, py):
    """(식별자, 리터럴 안쪽) — 지역 목록 후보 선언 전부."""
    for m in HEAD.finditer(s):
        b = _body(s, m.end() - 1, py)
        if b is not None:
            yield m.group(1), b


def _rel(p, root=ROOT):
    """저장소 루트 기준 상대 경로('/' 구분). 폴더 이름에 기대지 않는다 — 로컬은 aptweather,
    GitHub 러너는 /home/runner/work/agongmap/agongmap 이라, 이름을 찾아 자르면 클라우드에서
    SKIP_DIR 이 통째로 꺼진 채 zone/·cycle/ 까지 훑는다(2026-09-16 리뷰)."""
    return os.path.relpath(p, root).replace(os.sep, '/')


def _scan():
    """(파일, 식별자, 리터럴로 들어 있는 지역명 집합) 목록."""
    out = []
    skipped = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != '.git' and (not d.startswith('.') or d == '.github')]
        for fn in files:
            p = os.path.join(root, fn)
            rel = _rel(p)
            if not rel.endswith(('.py', '.html', '.js')):
                continue
            if any(rel.startswith(d) for d in SKIP_DIR) or os.path.basename(rel) in SKIP_FILE:
                skipped += 1
                continue
            try:
                s = io.open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            for name, body in _decls(s, rel.endswith('.py')):
                names = set(re.findall(r"['\"]([가-힣]{2,4})['\"]", body))
                if len(names & (MODEL | OLD)) >= 3:
                    out.append((rel, name, names))
    # 생성 페이지(zone/ 등)는 저장소에 늘 있으므로, 하나도 건너뛰지 않았다면 경로 자르기가
    # 틀려 스킵이 꺼진 것이다 — 그 상태의 초록불은 방어선이 아니다.
    assert skipped > 0, 'SKIP_DIR 이 한 파일도 건너뛰지 않았다 — 상대 경로 계산이 틀렸다'
    return out


def test_relative_path_does_not_depend_on_the_folder_name():
    cloud = '/home/runner/work/agongmap/agongmap'
    assert _rel(cloud + '/zone/서울/index.html', cloud) == 'zone/서울/index.html'
    assert _rel(os.path.join(ROOT, 'tools', 'x.py')) == 'tools/x.py'


def test_every_region_list_is_classified():
    """분류에 없는 지역 목록이 나타나면 멈춘다 — 전부인지 일부인지 한 번 답할 것."""
    unknown = sorted({(n, f) for f, n, _ in _scan() if n not in FULL and n not in PARTIAL})
    assert not unknown, (
        '분류되지 않은 지역 목록: %s\n'
        '  전체를 담아야 하면 FULL 에, 일부만 담는 것이 의도면 PARTIAL 에 이유와 함께 넣을 것.'
        % ', '.join('%s(%s)' % (n, f) for n, f in unknown))


def test_full_lists_match_the_model():
    """FULL 로 분류한 목록은 모델과 집합이 같아야 한다."""
    bad = []
    for f, n, names in _scan():
        if n not in FULL:
            continue
        want = FULL[n]
        got = names & (MODEL | OLD)
        if got != want:
            bad.append('%s(%s) 차이 %s' % (n, f, sorted(got ^ want)))
    assert not bad, '모델과 어긋난 목록: %s' % '; '.join(bad)


def test_scanner_actually_sees_the_known_lists():
    """스캐너가 죽으면 위 두 시험이 조용히 통과한다 — 아는 것을 실제로 잡는지 본다.

    정규식 하나 어긋나면 _scan() 이 빈 목록을 돌려주고, 그러면 '분류 안 된 것 없음'과
    '어긋난 것 없음'이 둘 다 참이 된다. 이 저장소가 가장 자주 당한 '안 도는 방어선'이
    정확히 그 모양이라, 스캐너 자신을 먼저 확인한다.

    변이(실제로 확인, 2026-10-05): HEAD 에서 `{` 를 빼거나 감싼 꼴(frozenset(·set(·new Set()을 빼면 아래 리터럴 모양별
    단정이 빨개진다. 분류 표에서 THUMB_GROUP 을 지우면 test_every_region_list_is_classified 가, make_weekly_share.TILE 에서
    한 지역을 지우면 test_full_lists_match_the_model 이 빨개진다.
    픽스처: 저장소의 실제 소스 전부.
    """
    seen = {(f, n) for f, n, _ in _scan()}
    names = {n for _, n in seen}
    for must in ('MATRIX_REGIONS', 'WEEKLY_REGIONS', 'BUBBLE_REGIONS', 'SIDO17'):
        assert must in names, '스캐너가 %s 를 놓쳤다 — 정규식이 깨졌을 수 있다' % must
    # 리터럴 모양마다 하나씩(2026-10-05 리뷰 E4): dict(THUMB_GROUP), frozenset((…))(WEEKLY_TABLE), set(EST),
    # JS var {…}(SMALL), set — 같은 이름 SUDO 의 튜플판(rebuild_cycle_analysis)과 따로 센다(refresh_cycle_data).
    for f, n in (('tools/make_naver_post.py', 'THUMB_GROUP'), ('tools/make_naver_post.py', 'WEEKLY_TABLE'),
                 ('tools/sido_zones.py', 'EST'), ('home-app.js', 'SMALL'), ('tools/refresh_cycle_data.py', 'SUDO')):
        assert (f, n) in seen, '스캐너가 %s(%s) 를 놓쳤다 — dict·set·frozenset 리터럴을 못 본다' % (n, f)


def test_decls_reads_nested_and_wrapped_literals():
    """괄호 깊이로 짝을 찾는지 합성 소스로 본다.

    변이(실제로 확인): HEAD 의 여는 괄호에서 `\\{` 를 빼면 dict·set·JS 객체가, 감싼 꼴(frozenset·new Set)을 빼면 그 둘이,
    _body 대신 옛 정규식처럼 첫 닫는 괄호에서 자르면 튜플 목록의 둘째 이름부터, 문자열 안 괄호를 세면 'A(' 다음이 빨개진다.
    픽스처: 저장소에 실제로 있는 선언 모양 — 튜플 목록, frozenset((…)), dict, set, JS new Set([…]), 문자열 안 괄호.
    """
    py = '''
TUP = [('서울', 1), ('부산', 2), ('대구', 3)]
FRZ = frozenset(('서울', '부산', '대구'))
DCT = {'서울': '수도권', '부산': '영남', '대구': '영남'}
SET = {'서울', '부산', '대구'}
STR = ['A(', '서울', '부산', ')', '대구']  # 닫는 괄호 ) 가 주석에도 있다
'''
    got = {n: set(re.findall(r"'([가-힣]{2,4})'", b)) for n, b in _decls(py, True)}
    want = {'서울', '부산', '대구'}
    for n in ('TUP', 'FRZ', 'DCT', 'SET', 'STR'):
        assert want <= got.get(n, set()), (n, got.get(n))
    js = "const NSET = new Set(['서울', '부산', '대구']);\nvar SMAP = {'서울': 1, '부산': 1, '대구': 1};"
    got = {n: set(re.findall(r"'([가-힣]{2,4})'", b)) for n, b in _decls(js, False)}
    assert want <= got.get('NSET', set()) and want <= got.get('SMAP', set()), got
