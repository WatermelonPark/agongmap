# -*- coding: utf-8 -*-
"""갱신된 data.js 를 읽어, 막지는 않되 사람이 알아야 할 것을 배치 기록 줄로 찍는다.

왜 따로 두나. 계산이 '값을 못 만들었다'고 None 을 돌려주는 자리는 화면에서 그 줄이
그냥 빠지는 것으로 끝난다. 틀린 값이 아니라 **없는 값**이라 어떤 검사에도 안 걸린다.
여기서 그런 자리를 모아 ⚠️ 줄로 올린다 — ⚠️ 줄이 있는 회차는 메일이 간다
(tools/format_batch_report.py).

지금 보는 것(리뷰 2026-09-16 8번, 백로그 16):
  · 인허가 신호(pbr)가 없는 지역. 인허가 누계가 쌓인 뒤의 빈 달은 그 달과 다음 달을
    떨어뜨리고, 24개월 창에 그 달이 있는 동안 permit_signal 이 None 이다. 그러면 리포트
    머리의 '3년 너머' 줄이 경고 없이 사라진다. 2026-09-17 현재 19곳 모두 값이 있으므로
    None 은 평상 상태가 아니다.

사용:  python tools/batch_notes.py [--data data.js]     # 알릴 것이 없으면 아무것도 안 찍는다
"""
import argparse
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


def sync_claim_lines():
    """사이클 3편이 못 박은 주장('전부 양수', '최저는 서울')이 지금 데이터와 어긋나면 ℹ️ 로 알린다.

    예전엔 이것이 pytest 게이트의 실데이터 단정이었다(test_theory_sync_claims). 재산정으로 최저 지역이
    바뀌면 "발행본은 고치지 않는다"는 결정과 맞물려 데이터 커밋이 막혔을 것이다(리뷰 09-18 19번).
    게이트는 코드 회귀만 막고, 데이터 상태는 여기서 알린다. 생성 가드(make_theory_post)는 그대로다.
    """
    try:
        import make_theory_post as T
        T.check_sync_claims()
    except SystemExit as e:
        return ['%s 사이클 3편 주장이 지금 데이터와 어긋남 — %s (발행본은 두고 재발행을 검토)'
                % (ML.MARK, str(e).replace('\n', ' ')[:140])]
    except Exception as e:   # 도구를 못 올리면 그것도 알린다 — 조용히 통과하지 않는다
        return ['%s 사이클 3편 검사 불가 — %s: %s' % (ML.MARK, type(e).__name__, str(e)[:100])]
    return []


def lines(adv):
    out = []
    gaps = permit_gaps(adv)
    if gaps:
        out.append("%s 인허가 신호 빠짐 — %s: 리포트의 '3년 너머' 줄이 빠진다(인허가 누계 결측 확인)"
                   % (WARN, ', '.join(gaps)))
    out.extend(sync_claim_lines())
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
    for ln in lines(adv):
        sys.stdout.write(ln + '\n')
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    raise SystemExit(main())
