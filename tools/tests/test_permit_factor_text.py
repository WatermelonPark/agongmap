# -*- coding: utf-8 -*-
"""인허가 부풀림을 '1.3~1.7배'로 말하지 않는다 (2026-09-13 정정).

'착공 기반 대비 1.29~1.68배 과대'는 2026-08-06 건축HUB 준공예정을 걷어낼 때 잰
수치다. 8/11에 KOSIS 인허가 설명으로 옮겨지면서 뜻이 바뀌어 리포트 19장·홈·소개
페이지·블로그 생성기에 퍼졌고, PM이 그 계수로 경기 인허가를 할인해 '대략 균형'이라는
오판까지 이어졌다. KOSIS 인허가를 누계를 풀어 직접 재면 같은 해 착공 대비 약 1.15배다.

HUB 이야기로서의 1.29~1.68은 사실이라 주석·설계 문서에서는 남는다. 여기서는
화면에 나가는 원본(생성기와 손으로 쓴 페이지)에 인허가 부풀림으로 다시 들어오는 것만 막는다.
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
HUB = re.compile(r'1\.3\s*[~–-]\s*1\.7\s*배')
SKIP_DIRS = ('docs', 'drafts', 'logs', 'node_modules', '.git', '.claude')


def _groups():
    """화면에 나가는 원본 세 묶음 — 손으로 적은 파일 목록을 두지 않는다(전수리뷰 T2-1).
    ① 홈(index.html·분할 스크립트 전부 — 입구 home_files) ② 저장소의 모든 .html(손 페이지·FAQ·퀴즈 랜딩과, CI·배치가 시험 앞에
    굽는 생성 페이지) 과 llms.txt·feed.xml ③ tools/ 의 파이썬(생성기·정본 문구 sido_zones.PERMIT_NATURE·블로그 도구, 시험 제외)."""
    home = [(f, t) for f, t in HS.home_files()]
    pages = []
    for path in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True) + \
            [os.path.join(ROOT, n) for n in ('llms.txt', 'feed.xml') if os.path.isfile(os.path.join(ROOT, n))]:
        rel = os.path.relpath(path, ROOT)
        if rel.split(os.sep)[0] in SKIP_DIRS:
            continue
        pages.append((rel, io.open(path, encoding='utf-8').read()))
    tools = [(os.path.relpath(p, ROOT), io.open(p, encoding='utf-8').read())
             for p in sorted(glob.glob(os.path.join(ROOT, 'tools', '*.py')))]
    return {'홈': home, '페이지': pages, '도구': tools}


def test_public_text_does_not_carry_the_hub_factor_as_permit_inflation():
    """화면에 나가는 모든 원본에 인허가 부풀림을 HUB 수치('1.3~1.7배')로 다시 쓰지 않는다.

    재현한 실제 상태(전수리뷰 T2-1): 손 목록 5개(index.html·소개·생성기 셋)만 봐서, 2026-09-16·09-27 분할로 홈 문구가 옮겨 간
    home-app.js·home-quiz.js·home-stats.js, 인허가 문단이 있는 FAQ, 정본 문구 SZ.PERMIT_NATURE(/monthly/·리포트에 나감)에
    '1.3~1.7배'를 넣어도 초록이었다.
    변이(실제로 확인): home-stats.js 끝에 '인허가는 착공 대비 1.3~1.7배 부풀려 있다' 문자열을, faq/index.html 에
    '<p>인허가는 착공보다 1.3~1.7배 많다</p>' 를, sido_zones.PERMIT_NATURE 앞에 '착공보다 1.3~1.7배 많고,' 를 넣으면 빨개진다.
    """
    groups = _groups()
    bad = []
    for name, files in groups.items():
        assert files, '%s 묶음에서 훑은 파일이 없다 — 이 시험이 헛돈다' % name
        for rel, src in files:
            for m in HUB.finditer(src):
                bad.append('%s: …%s…' % (rel, src[max(0, m.start() - 30):m.end() + 10].replace('\n', ' ')))
    assert any(rel.startswith('faq') for rel, _ in groups['페이지']), 'FAQ 를 훑지 않았다'
    assert {'home-stats.js', 'home-quiz.js'} <= {rel for rel, _ in groups['홈']}, '분할 홈 스크립트를 훑지 않았다'
    assert not bad, '인허가 부풀림을 HUB 수치로 말한다:\n' + '\n'.join(bad)
