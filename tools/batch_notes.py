# -*- coding: utf-8 -*-
"""갱신된 data.js 를 읽어, 막지는 않되 사람이 알아야 할 것을 배치 기록 줄로 찍는다.

왜 따로 두나. 계산이 '값을 못 만들었다'고 None 을 돌려주는 자리는 화면에서 그 줄이
그냥 빠지는 것으로 끝난다. 틀린 값이 아니라 **없는 값**이라 어떤 검사에도 안 걸린다.
여기서 그런 자리를 모아 ⚠️ 줄로 올린다 — ⚠️ 줄이 있는 회차는 메일이 간다
(tools/format_batch_report.py).

지금 보는 것(리뷰 2026-09-16 8번, 백로그 16):
  · 인허가 신호(pbr)가 없는 지역. 인허가 누계가 쌓인 뒤의 빈 달은 그 달과 다음 달을
    떨어뜨리고, 24개월 창에 그 달이 있는 동안 permit_signal 이 None 이다. 창의 끝은 계열 전체의
    마지막 달(sido_zones.permit_ref_month)이라 그 지역의 최신 달만 비어도 None 이다(전수리뷰 Z1-4 —
    예전엔 그 지역만 묵은 창을 '최근 2년'이라 말했다). 그러면 리포트 머리의 '3년 너머' 줄이 경고
    없이 사라진다. 2026-09-17 현재 19곳 모두 값이 있으므로 None 은 평상 상태가 아니다.
  · (main() 이 붙이는 ℹ️ 곁가지) 사이클 이론편 1~7편 전제가 지금 데이터와 어긋나거나 데이터 상태로 초안이 멈춘 편
    (theory_claim_lines — 초안 도구만 멈추고 게이트는 막지 않는다, 대표 결정 2026-10-18 D1), 퀴즈 제도 문항의 검토 기한
    경과(quiz_review_lines).

사용:  python tools/batch_notes.py [--data data.js]     # 알릴 것이 없으면 아무것도 안 찍는다
"""
import argparse
import re
import sys

import month_lag as ML

WARN = '⚠️'


def zones(adv):
    """판정 지역 목록. 읽는 자리를 한 곳에 둔다 — 시험이 이 함수로 실제 data.js 를 읽어,
    키가 바뀌어 지역을 하나도 못 읽는 상태(=늘 '빠짐 없음')를 잡는다."""
    return ((adv or {}).get('sido') or {}).get('zones') or []


def permit_gaps(adv):
    """인허가 신호가 비어 있는 지역 이름(표시 순서 그대로)."""
    return [z.get('z') for z in zones(adv) if z.get('pbr') is None]


_STOP_HEAD = re.compile(r'^[\d·]+편을 만들 수 없다 — ')
_STOP_TAIL = re.compile(r'\s*(?:\d편 )?문장을 먼저 고칠 것\.?$')


def theory_claim_lines():
    """사이클 이론편(1~7편)이 못 박은 전제가 지금 데이터와 어긋나면 편마다 ℹ️ 한 줄로 알린다(대표 결정 2026-10-18 D1).

    전제가 깨진 편은 초안 도구(make_theory_post <편>)만 SystemExit 로 멈춘다 — 게이트 시험은 그 데이터 상태로 실패하지 않는다.
    대신 사람이 알아야 하니(발행본을 다시 볼지 정한다) 여기서 알린다. 검사는 초안 도구와 같은 함수(make_theory_post.guard_values —
    1·2편 고리①, 3편 동조성, 4편 theory_link3, 5편 theory_link4, 6편 link6_values, 7편 link7_values)를 지금 데이터로 돌린 것이다.
    같은 이유로 멈춘 이웃 편은 한 줄로 묶는다(1·2편은 고리① 전제 하나를 함께 쓴다). 가드가 SystemExit 말고 다른 예외로 죽으면 코드
    결함이라 그 편을 '검사 불가'로 적는다(도구·데이터를 못 올리면 '이론편 검사 불가' 한 줄). 옛 sync_claim_lines(3편만)를 접었다 —
    3편도 이 검사가 보므로 따로 두면 같은 줄이 두 번 나간다.
    문장 전제가 아니라 데이터 상태로 멈춘 편(멈춤 문구에 make_theory_post.NOT_THE_TEXT — 4편 지수 기준 단절, 5편 착공·준공 끝 달
    어긋남, 6편 판정 칸을 못 읽음, 7편 금리 오버레이 빈 분기)은 '전제가 어긋남 … 발행본 재검토'가 아니라 '데이터 상태' 줄로 적는다 —
    발행본을 다시 볼 일이 아니라 다음 배치에서 풀리는 일이다.
    ⚠️ lines(adv) 에 넣지 않는다(전수리뷰 #32·#94). 인자 adv 가 아니라 저장소 data.js·cycle/index.html 을 읽는다. lines() 를 부르는
       합성 픽스처 시험이 '줄이 정확히 몇 개'를 단정하므로, 안에 두면 데이터 상태가 바뀌는 날 무관한 시험이 빨개져 알림으로 돌린
       데이터 상태가 다시 게이트 실패가 된다. main() 이 따로 붙인다.
    """
    try:
        import make_theory_post as T
        D = T.P.cycle_d()
        data = T.M.load()
    except Exception as e:   # 도구·데이터를 못 올리면 그것도 알린다 — 조용히 통과하지 않는다
        return ['%s 사이클 이론편 검사 불가 — %s: %s' % (ML.MARK, type(e).__name__, str(e)[:100])]
    got = []                 # [(편 번호들, 'stop'|'data'|'crash', 글)] — 편 순서대로
    for post in T.POSTS:
        n = post['n']
        try:
            T.guard_values(n, D, data)
            continue
        except SystemExit as e:
            why = _STOP_TAIL.sub('', _STOP_HEAD.sub('', str(e).replace('\n', ' ')))
            kind = 'data' if T.NOT_THE_TEXT in why else 'stop'
        except Exception as e:
            kind, why = 'crash', '%s: %s' % (type(e).__name__, str(e).replace('\n', ' '))
        if got and got[-1][1:] == (kind, why):
            got[-1][0].append(n)
        else:
            got.append(([n], kind, why))
    out = []
    for ns, kind, why in got:
        tag = '·'.join(str(n) for n in ns)
        if kind == 'stop':
            out.append('%s 사이클 %s편 전제가 지금 데이터와 어긋남 — %s (초안 생성만 멈춤, 발행본 재검토)'
                       % (ML.MARK, tag, why[:160]))
        elif kind == 'data':
            out.append('%s 사이클 %s편 초안 생성 멈춤(데이터 상태, 발행본과 무관) — %s' % (ML.MARK, tag, why[:160]))
        else:
            out.append('%s 사이클 %s편 검사 불가 — %s' % (ML.MARK, tag, why[:120]))
    return out


def quiz_review_lines(today, src=None):
    """퀴즈 제도 문항의 검토 기한이 지났으면 ℹ️ 줄로 알린다. 형식기는 ℹ️ 줄을 월요일 확인 메일에 싣는다.

    감시(check_freshness)는 2026-09-26 부터 기한 경과를 실패가 아닌 경고(주석·잡 요약)로만 남긴다 — 실패로 두면
    첫 기한(2026-12-15)부터 감시가 매일 빨개져 진짜 뒤처짐 경보가 그 속에 묻힌다(데이터 감사 #13). 그런데 경고는
    누구에게도 메일로 가지 않으므로, 사람에게 닿는 통로를 여기 둔다. ℹ️ 라 매 회차 메일을 부르지 않는다.
    ⚠️ lines(adv) 에 넣지 않는다. lines() 를 부르는 시험이 '평소에는 한 줄도 없다'를 단정하므로, 넣으면 날짜가
       지나는 날 그 시험이 빨개져 게이트가 데이터 커밋을 막는다. main() 이 따로 붙인다.
    """
    try:
        import home_src as HS
        import quiz_review as QR
        qo = QR.overdue(HS.home_source() if src is None else src, today)
    except Exception as e:   # 알림 곁가지라 배치를 멈추지 않는다 — 못 본 것도 알린다
        return ['%s 퀴즈 검토 기한 검사 불가 — %s: %s' % (ML.MARK, type(e).__name__, str(e)[:100])]
    return ['%s %s' % (ML.MARK, q) for q in qo]


def lines(adv):
    """인자 adv 만 보고 찍을 줄. 저장소 파일·오늘 날짜를 읽는 곁가지(theory_claim_lines·quiz_review_lines)는 main() 이 붙인다."""
    out = []
    gaps = permit_gaps(adv)
    if gaps:
        out.append("%s 인허가 신호 빠짐 — %s: 리포트의 '3년 너머' 줄이 빠진다(인허가 누계 결측 확인)"
                   % (WARN, ', '.join(gaps)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', help='data.js 경로(기본: 저장소 루트)')
    a = ap.parse_args(argv)
    try:
        adv, _ = ML.load(a.data)
    except Exception as e:
        # 알림용 곁가지다. 읽지 못해도 배치를 멈추지 않는다 — 대신 이유를 남긴다.
        sys.stderr.write('batch_notes: 데이터를 읽지 못했다 (%s)\n' % e)
        return 0
    import kst
    for ln in lines(adv) + theory_claim_lines() + quiz_review_lines(kst.today()):
        sys.stdout.write(ln + '\n')
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    raise SystemExit(main())
