# -*- coding: utf-8 -*-
"""갱신이 멈춘 것을 시점만으로는 못 잡는다.

2026-09-08~12 실사고: 배치의 완비 기준이 원천에 없는 이름(`기타광역시`·`기타지방`)을
요구해 받은 달을 **전부** 버렸다. 저장분은 멈춘 채 남았는데 원천도 새 달을 내지
않아 시점은 계속 같았고, 감시는 닷새 내내 초록이었다. 기준을 고친 것과 별개로,
같은 모양의 정지가 다른 이유로 또 생길 수 있으니 두 자리를 지킨다.

① 배치: 받은 달을 전부 버리면 개별 달의 결측이 아니라 기준이 틀린 것이다.
② 감시: 시점이 같아도 그 달의 시도 합이 원천과 같은지 본다.

지역 이름은 여기에 적지 않고 `SUPPLY_SIDO`에서 가져온다 — 픽스처에 모델을 박으면
지역이 바뀔 때 이 시험이 배치를 막는다(2026-09-11에 실제로 그랬다).
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import update_adv_data as U  # noqa: E402
import check_freshness as C  # noqa: E402


def _months(n=2):
    """완비된 달 n개. 값은 지역마다 1로 둬서 시도 합이 곧 지역 수가 되게 한다."""
    return {(2026, 6 - i): {r: 1.0 for r in U.SUPPLY_SIDO} for i in range(n)}


def test_all_dropped_is_announced(capsys):
    """전부 버려지는 것은 평범한 제외와 다르게 보여야 한다."""
    U._drop_incomplete(_months(), set(U.SUPPLY_SIDO) | {'있을 수 없는 이름'}, '분양')
    out = capsys.readouterr().out
    assert '전부 버렸다' in out, '모든 달을 버렸는데 평범한 제외 줄만 찍혔다'
    assert '::warning::' in out, '워크플로 로그에서 눈에 띄지 않는다'


def test_normal_drop_stays_quiet(capsys):
    """한 달만 빠지는 것은 정상 동작이라 경고까지 올리지 않는다."""
    got = _months()
    ym = max(got)
    got[ym].pop(U.SUPPLY_SIDO[0])
    kept = U._drop_incomplete(got, set(U.SUPPLY_SIDO), '분양')
    out = capsys.readouterr().out
    assert len(kept) == 1, '멀쩡한 달까지 버렸다'
    assert '전부 버렸다' not in out and '::warning::' not in out


def _series(dates, per_region):
    return {'dates': list(dates),
            'series': {r: [per_region] * len(dates) for r in U.SUPPLY_SIDO}}


def test_value_check_passes_when_totals_agree(monkeypatch, capsys):
    n = len(U.SUPPLY_SIDO)
    monkeypatch.setitem(C._COMPLETE_CACHE, ('T', '202605'), ('202606', float(n)))
    assert C.check_supply_value('분양', _series(['2026.05', '2026.06'], 1.0),
                                'T', '202605') is None


def test_value_check_catches_a_frozen_series(monkeypatch):
    """시점은 같은데 값이 다르면 잡아야 한다 — 조용한 정지가 이 모양이다."""
    n = len(U.SUPPLY_SIDO)
    monkeypatch.setitem(C._COMPLETE_CACHE, ('T', '202605'), ('202606', float(n) + 500))
    why = C.check_supply_value('분양', _series(['2026.05', '2026.06'], 1.0),
                               'T', '202605')
    assert why and '값이 다르다' in why, '시도 합이 어긋났는데 통과시켰다'


def test_value_check_is_silent_when_the_month_is_missing(monkeypatch):
    """저장분에 그 달이 아예 없으면 나이 검사 몫이다. 여기서 두 번 세지 않는다."""
    monkeypatch.setitem(C._COMPLETE_CACHE, ('T', '202605'), ('202607', 1.0))
    assert C.check_supply_value('분양', _series(['2026.05', '2026.06'], 1.0),
                                'T', '202605') is None


def test_value_check_survives_a_fetch_failure(monkeypatch):
    """조회 실패는 check()가 SKIPPED로 분류한다. 여기서 또 실패를 세면 게이트 산수가 틀어진다."""
    def boom(*a, **k):
        raise RuntimeError('원천 응답 없음')
    monkeypatch.setattr(C, 'rone_latest_complete', boom)
    assert C.check_supply_value('분양', _series(['2026.06'], 1.0), 'T', '202605') is None


def test_watchdog_reuses_the_lookup_instead_of_calling_twice():
    """값 대조 때문에 원천 호출이 늘면 감시 타임아웃 예산이 어긋난다."""
    src = io.open(os.path.join(os.path.dirname(__file__), '..', 'check_freshness.py'),
                  encoding='utf-8').read()
    assert '_COMPLETE_CACHE' in src, '조회 결과를 재사용하지 않는다'
    assert 'want_total' in src, '합계를 같은 조회에서 받지 않는다'



# ── 멈춤이 사람에게 닿는가 (백로그 14, 2026-09-17) ──────────────────────────
# 위 시험은 stdout 글자만 본다. 그런데 그 글자는 러너 로그 안에 있을 뿐이고 회차는 ✅로
# 끝났다. 2026-09-08~12 에 닷새를 지나친 이유가 그것이다. 여기서는 멈춤이 파일 → 배치
# 기록의 ⚠️ 줄 → 메일까지 이어지는지를 본다.

def test_all_dropped_is_recorded_for_the_report(tmp_path):
    """받은 달을 전부 버리면 그 계열 이름이 .supply_stalled 에 남는다.

    변이: _drop_incomplete 의 `SUPPLY_STALLED.append(name)` 을 지우면 빨개진다.
    픽스처: 완비 기준에 원천이 결코 주지 않는 이름이 하나 섞인 상태 — 2026-09-08~12 에
            '기타광역시'·'기타지방'이 기준에 들어가 모든 달이 불완비로 판정된 것과 같은 모양이다.
    """
    del U.SUPPLY_STALLED[:]
    U._drop_incomplete(_months(), set(U.SUPPLY_SIDO) | {'있을 수 없는 이름'}, '분양')
    assert U.SUPPLY_STALLED == ['분양']
    path = U.write_supply_stalled(str(tmp_path))
    assert io.open(path, encoding='utf-8').read() == '분양'


def test_normal_drop_leaves_an_empty_record(tmp_path):
    """최신 한 달만 불완비인 것은 평상 동작이다(지금의 미분양 2026.07 이 그렇다) — 알리지 않는다.

    변이: 기록 조건을 `if had and not fetched` 에서 `if had` 로 넓히면 빨개진다.
    픽스처: 두 달 중 최신 달에서만 한 지역이 빠진 상태.
    """
    del U.SUPPLY_STALLED[:]
    got = _months()
    got[max(got)].pop(U.SUPPLY_SIDO[0])
    U._drop_incomplete(got, set(U.SUPPLY_SIDO), '미분양')
    assert U.SUPPLY_STALLED == []
    path = U.write_supply_stalled(str(tmp_path))
    assert io.open(path, encoding='utf-8').read() == '', '멈춘 것이 없으면 빈 파일이어야 옛 기록이 안 남는다'


def test_each_run_counts_afresh(monkeypatch):
    """앞 회차의 멈춤 기록이 다음 호출에 남지 않는다.

    변이: update_supply 첫머리의 `del SUPPLY_STALLED[:]` 를 지우면 빨개진다.
    픽스처: 직전 호출이 멈춤을 기록해 둔 상태에서, 원천이 빈 응답을 주는 회차.
    """
    U.SUPPLY_STALLED.append('분양')
    monkeypatch.setattr(U, '_fetch_supply_one', lambda *a, **k: {})
    U.update_supply({})
    assert U.SUPPLY_STALLED == []


def test_stall_reaches_the_mail():
    """워크플로가 그 파일을 ⚠️ 줄로 올리고, 알림이 그것을 사람 말로 바꿔 메일을 보낸다.

    변이: 워크플로의 `rep "⚠️ 공급 갱신 멈춤` 줄을 지우거나, 아티팩트 목록에서
          .supply_stalled 를 빼면 빨개진다(러너의 파일이 커밋 잡에 닿지 않는다).
    픽스처: 나머지는 전부 정상인 수요일 회차에 멈춤 줄 하나가 더해진 기록.
    """
    import format_batch_report as F
    root = os.path.join(os.path.dirname(__file__), '..', '..')
    wf = io.open(os.path.join(root, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    code = '\n'.join(ln for ln in wf.splitlines() if not ln.lstrip().startswith('#'))
    assert re.search(r'path: \|[^#]*?\.supply_stalled', code, re.S), '러너가 멈춤 기록을 올리지 않는다'
    m = re.search(r'if \[ -s "\$SRC/\.supply_stalled" \]; then\s*\n\s*rep "(⚠️ 공급 갱신 멈춤[^"]*)"', code)
    assert m, '커밋 잡이 멈춤 기록을 배치 알림에 올리지 않는다'
    raw = ('✅ 러너 3/3 clean · 채택 주간 2026-09-14 / 월간 2026-08 / 공급 2026Q2\n'
           + m.group(1).replace('$(cat "$SRC/.supply_stalled")', '분양,미분양') + '\n')
    body, mail = F.build(raw, '2026-09-17 18:33', 'u', 'O', 2)
    assert mail is True, '멈춤이 있는 회차인데 메일이 가지 않는다'
    assert '분양·미분양 통계를 새로 받지 못했습니다' in body
    assert '완비 기준' not in body and 'supply' not in body, '내부 용어가 본문에 샜다'
