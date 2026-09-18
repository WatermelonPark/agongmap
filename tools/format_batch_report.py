# -*- coding: utf-8 -*-
"""배치 단계 기록(_batch_report.txt)을 **받는 사람의 말**로 된 알림 본문으로 바꾼다.

왜 따로 떼어냈나. 문구 조립을 워크플로 셸에 두면 시험할 방법이 없다. 이 저장소가
반복해서 당한 게 '안 도는 방어선'이라, 사람에게 닿는 마지막 1미터도 시험 가능한
자리에 둔다(tools/tests/test_batch_report.py).

원칙 세 가지 (PM 요청서 2026-09-12).
  1. 첫 줄이 결론, 둘째 줄이 할 일. 기계 안에서 무슨 일이 있었나가 아니라
     '내 사이트는 괜찮은가, 내가 뭘 해야 하나'를 먼저 적는다.
  2. 정상이면 확인된 항목을 나열하지 않는다. 읽을 것이 없어야 정상이다.
  3. 실패는 반대로 **무엇이 안 됐는지 이름을 밝힌다.** '일부 단계 실패'는 알림이 아니다.

⚠️ 메일 발송 스위치는 멘션이 아니라 **이슈 코멘트 그 자체**다(2026-09-17 실측).
   한 번이라도 멘션되거나 담당자로 지정된 사람은 그 이슈를 구독한 상태가 되어,
   이후 코멘트는 멘션이 없어도 전부 메일로 간다. 2026-09-12 에 정상 회차의 멘션을
   뗐지만 메일은 매 회차 그대로 갔다(받은 메일 꼬리: "because you were mentioned").
   그래서 build() 가 돌려주는 '멘션 여부'는 곧 **코멘트를 남길지 여부**다. 워크플로는
   이 값이 참일 때만 이슈에 쓰고, 거짓이면 화면 요약(Step Summary)에만 남긴다:
     실패했을 때 · 점검 이상일 때 · 월요일 회차(살아 있다는 신호) · 기준월 장기 뒤처짐
   침묵이 곧 정상을 뜻하게 만드는 것이 목적이다.

⚠️ 단계별 상세를 지우는 대상은 **메일 본문**뿐이다. 실행 로그 링크는 항상 남기고,
   화면 요약(GITHUB_STEP_SUMMARY)에는 원본 기록을 그대로 붙인다 — 세션이 파고들
   입구가 없어지면 안 된다.

사용:
    python tools/format_batch_report.py _batch_report.txt \
        --kst "2026-09-12 21:52" --run-url URL --owner NAME [--weekday 0]
"""
import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import month_lag as ML  # noqa: E402  (뒤처짐 표시와 기준 개월을 한 곳에서 가져온다)

# 상태 표시 → 심각도. 기록의 각 줄은 이 중 하나로 시작한다(rep() 호출부 참조).
BAD = '❌'
WARN = '⚠️'
OK = '✅'
SKIP = '➖'


def _month_day(s):
    """'2026-09-07' → '9월 7일'. 못 읽으면 원문 그대로."""
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', s.strip())
    return '%d월 %d일' % (int(m.group(2)), int(m.group(3))) if m else s.strip()


def _year_month(s):
    """'2026-07' / '2026.07' → '2026년 7월'."""
    m = re.match(r'^(\d{4})[-.](\d{2})$', s.strip())
    return '%s년 %d월' % (m.group(1), int(m.group(2))) if m else s.strip()


def _quarter(s):
    """'2026Q2' → '2026년 2분기'."""
    m = re.match(r'^(\d{4})Q([1-4])$', s.strip())
    return '%s년 %s분기' % (m.group(1), m.group(2)) if m else s.strip()


def basis_line(lines):
    """'채택 주간 … / 월간 … / 공급 …' 줄에서 사람이 읽는 기준 시점 문장을 만든다.

    이 값들은 정상일 때 유일하게 쓸모 있는 정보다 — 사이트가 '언제 기준'인지는
    받는 사람이 실제로 확인하고 싶어 하는 것이라, 정상 본문에도 남긴다.
    """
    for ln in lines:
        m = re.search(r'채택\s*주간\s*(\S+)\s*/\s*월간\s*(\S+)\s*/\s*공급\s*(\S+)', ln)
        if not m:
            continue
        wk, mo, sl = m.group(1), m.group(2), m.group(3)
        parts = []
        if wk not in ('-', '--'):
            parts.append('주간 시세 %s' % _month_day(wk))
        if mo not in ('-', '--'):
            parts.append('월간 통계 %s' % _year_month(mo))
        if sl not in ('-', '--'):
            parts.append('공급 %s' % _quarter(sl))
        return (' · '.join(parts) + ' 기준') if parts else ''
    return ''


# 내부 기록 → 받는 사람의 말. 앞에서부터 처음 걸리는 것을 쓴다.
# ⚠️ '무엇이' 안 됐는지가 남아야 한다. 뭉뚱그리면 알림이 아니라 소음이 된다.
PLAIN = (
    (r'러너 0/3 clean.*재시도로 낫지 않는',
     '통계청에서 데이터를 받아오지 못했습니다(3번 시도). 재시도로 낫는 종류가 아니라 '
     '바로 알립니다 — 접속 열쇠 만료나 코드 이상일 수 있습니다.'),
    (r'러너 0/3 clean.*자동 재시도',
     '통계청에서 데이터를 받아오지 못했습니다(3번 시도). 접속이 막힌 것으로 보이며 '
     '35분 뒤 다시 받습니다.'),
    (r'러너 0/3 clean.*소진',
     '통계청에서 데이터를 받아오지 못했습니다(재시도 3회 모두). 이번 회차는 갱신을 '
     '건너뛰고 다음 회차에 다시 받습니다.'),
    (r'산출물 복사 실패',
     '받아온 데이터가 불완전해 반영하지 않았습니다.'),
    (r'테스트 실패',
     '새 코드가 검사를 통과하지 못해 반영을 멈췄습니다. 숫자가 틀어진 데이터가 '
     '사이트에 올라가지 않도록 막은 것이지 고장 난 것이 아닙니다.'),
    (r'테스트 건너뜀',
     '검사 도구를 설치하지 못해 검사를 건너뛰었습니다(설비 문제).'),
    (r'인허가 신호 빠짐',
     "일부 지역 리포트에서 '3년 너머' 줄이 빠졌습니다. 인허가 원자료에 빈 달이 생겨 계산을 "
     '못 한 것으로, 나머지 수치와 판정은 그대로 정확합니다. 세션이 확인합니다.'),
    (r'공급 갱신 멈춤',
     '분양·미분양 통계를 새로 받지 못했습니다. 받아온 달이 모두 기준에 못 미쳐 버려졌는데, '
     '기준이 원천과 어긋났을 수 있어 세션이 확인합니다. 사이트 수치는 직전 그대로입니다.'),
    (r'지역페이지 실패', '시도별 공급 페이지를 다시 만들지 못했습니다.'),
    (r'지표페이지 실패', '입주물량·전세가율 페이지를 다시 만들지 못했습니다.'),
    (r'이달의 통계 실패', '이달의 통계 페이지를 다시 만들지 못했습니다.'),
    (r'사이클 리포트 실패', '사이클 리포트를 다시 만들지 못했습니다.'),
    (r'공유카드 실패',
     '공유용 이미지를 다시 만들지 못했습니다. 카카오·블로그에 옛 주차 그림이 '
     '보일 수 있습니다.'),
    (r'공유카드 건너뜀',
     '그림 도구가 없어 공유용 이미지를 건너뛰었습니다(설비 문제).'),
    (r'git add 실패|git commit 실패', '사이트에 반영하는 단계에서 실패했습니다.'),
    (r'푸시 3회 실패',
     '사이트 반영을 3번 시도했으나 실패해 이번 회차 결과가 유실됐습니다. '
     '누군가 같은 줄을 고쳤을 수 있습니다.'),
    (r'IndexNow 실패',
     '검색엔진에 새 내용을 알리지 못했습니다. 데이터는 정상이고 검색 반영만 늦어집니다.'),
    (r'감시가 \d+시간째 안 돌았|감시 실행 이력을 읽지 못',
     '점검 작업이 예정대로 돌지 않았습니다. 데이터가 뒤처져도 알아채지 못할 수 있습니다.'),
    (r'배치가 보고 지점 전에 중단',
     '배치가 도중에 멈춰 어디까지 됐는지 기록이 남지 않았습니다.'),
)


# 월간 계열 뒤처짐 알림(tools/month_lag.py 가 찍는 줄). 실패도 경고도 아니라 표시가 따로다.
LAG_LINE = re.compile(r'^\s*%s\s*월간 뒤처짐\s*(\d+)개월\s*·\s*(.+?)\s*·\s*최신\s*(\d{4}[.\-]\d{1,2})\s*$'
                      % re.escape(ML.MARK))


def lag_notice(lines):
    """뒤처짐 줄 → (사람이 읽는 문장, 가장 큰 뒤처짐 개월). 없으면 (None, 0).

    받는 사람에게 뜻이 있는 것은 계열 이름과 기준월뿐이다. 같은 달에 묶인 계열은 한
    덩어리로 적어 줄을 짧게 유지한다.
    """
    for ln in lines:
        m = LAG_LINE.match(ln)
        if not m:
            continue
        pairs = []
        for part in m.group(2).split('/'):
            bits = part.strip().rsplit(' ', 1)
            if len(bits) == 2:
                pairs.append((bits[1], bits[0]))
        by = []
        for ym, name in pairs:
            if by and by[-1][0] == ym:
                by[-1][1].append(name)
            else:
                by.append((ym, [name]))
        say = ' · '.join('%s가 %s 기준' % ('·'.join(names), _year_month(ym)) for ym, names in by)
        return ('%s입니다. 가장 최신 월간 통계는 %s입니다(%s개월 차이). 원천이 아직 그 달을 '
                '내놓지 않았다는 뜻이며, 사이트 수치는 그 기준월 그대로 정확합니다.'
                % (say, _year_month(m.group(3)), m.group(1))), int(m.group(1))
    return None, 0


def plain(line):
    """기록 한 줄 → 사람의 말. 대응이 없으면 표시만 떼고 원문을 쓴다."""
    body = line.lstrip(''.join((BAD, WARN, OK, SKIP))).strip()
    for pat, say in PLAIN:
        if re.search(pat, body):
            return say
    return body


def _short_date(kst):
    """'2026-09-17 18:33' → '9/17'. 못 읽으면 빈 문자열."""
    m = re.match(r'^\d{4}-(\d{2})-(\d{2})', (kst or '').strip())
    return '%d/%d' % (int(m.group(1)), int(m.group(2))) if m else ''


def headline(raw, kst, weekday):
    """메일 제목이 될 한 줄. **제목만 보고 열지 말지 정할 수 있어야 한다**(2026-09-17 대표).

    GitHub 이슈 코멘트 메일의 제목은 그 시점의 이슈 제목이다. 그래서 코멘트를 남기기
    직전에 이슈 제목을 이 문장으로 바꾼다. 모든 제목은 같은 세 토막으로 읽힌다:
      무슨 일인가 · 사이트는 괜찮은가 · 내가 할 일이 있는가
    색 동그라미가 맨 앞이라 받은편지함 목록에서 색만 봐도 된다(🔴 실패, 🟡 확인 중, 🟢 정상).
    """
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    bad = any(ln.lstrip().startswith(BAD) for ln in lines)
    warn = any(ln.lstrip().startswith(WARN) for ln in lines)
    _, lag_months = lag_notice(lines)
    day = _short_date(kst)
    tail = (' (%s)' % day) if day else ''
    nothing = any(ln.lstrip().startswith(SKIP) for ln in lines)
    if bad:
        # 재시도 대기(시도 1·2)와 최종 실패는 제목이 달라야 한다 — 같으면 스로틀 날 같은 제목이
        # 서너 통 오고 어느 것이 마지막인지 모른다(리뷰 2026-09-18 20번).
        if all(re.search(r'러너 0/3 clean.*자동 재시도', ln) for ln in lines if ln.lstrip().startswith(BAD)):
            return '🔴 갱신 실패 · 35분 뒤 자동 재시도 · 하실 일 없음' + tail
        return '🔴 데이터 갱신 실패 · 사이트는 정상 · 하실 일 없음' + tail
    if warn:
        n = sum(1 for ln in lines if ln.lstrip().startswith(WARN))
        what = '확인할 것 %d건' % n if n > 1 else '곁가지 하나 확인 중'
        if nothing:   # 갱신이 없었던 회차에 "갱신됨"이라고 하면 안 된다
            return '🟡 갱신 없음 · %s · 하실 일 없음%s' % (what, tail)
        return '🟡 데이터는 갱신됨 · %s · 하실 일 없음%s' % (what, tail)
    if lag_months >= ML.ESCALATE_MONTHS:
        return '🟡 일부 통계가 %d개월째 옛 기준 · 세션이 검토 중 · 하실 일 없음%s' % (lag_months, tail)
    if weekday == 0:
        return '🟢 주간 확인 · 데이터 정상 · 하실 일 없음' + tail
    return '🟢 데이터 정상 · 하실 일 없음' + tail


def mention_preview(bad, warn, weekday, lag_hard):
    """이 회차가 코멘트(=메일)를 남기는가. build() 끝의 mention 과 같은 식이다."""
    return bool(bad or warn) or weekday == 0 or lag_hard


def build(raw, kst, run_url, owner, weekday):
    """기록 전문 → (본문, 멘션여부).

    weekday: 0=월 … 6=일. 월요일 회차 한 번은 정상이어도 멘션을 붙여 '살아 있다'를
    알린다. 침묵이 길어지면 사람은 도는지 의심하게 되고, 그건 침묵의 값을 떨어뜨린다.
    """
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    bad = [ln for ln in lines if ln.lstrip().startswith(BAD)]
    warn = [ln for ln in lines if ln.lstrip().startswith(WARN)]
    nothing = any(ln.lstrip().startswith(SKIP) for ln in lines)
    basis = basis_line(lines)
    # 월간 뒤처짐은 평소 월요일 회차에만 싣는다. 매 회차 반복하면 '괜찮다'가 쌓여
    # 진짜 경보를 묻는다(PM 조건 2026-09-16). 오래 끌면 그때는 매번 싣고 멘션한다.
    lag_say, lag_months = lag_notice(lines)
    lag_hard = lag_months >= ML.ESCALATE_MONTHS
    if lag_say and not (lag_hard or weekday == 0):
        lag_say = None

    out = []
    if bad:
        out.append('### ⚠️ 데이터 갱신 중단 · %s' % kst)
        out.append('')
        out.append('**사이트는 정상입니다.** 다만 새 데이터가 반영되지 않아 이전 '
                   '시점 그대로입니다.')
        out.append('')
        out.append('**하실 일: 없습니다.** 세션에서 원인을 확인하고 고칩니다. '
                   '사흘 넘게 이 메일이 계속 오면 그때 알려 주세요.')
        out.append('')
        out.append('**무슨 일인가:**')
        for ln in bad:
            out.append('- %s' % plain(ln))
        for ln in warn:
            out.append('- %s' % plain(ln))
    elif warn:
        if nothing:
            out.append('### ⚠️ 갱신은 없었고 확인할 것이 있습니다 · %s' % kst)
            out.append('')
            out.append('**원천 통계가 그대로라 바뀐 내용이 없습니다.** 아래 항목을 세션이 확인합니다.')
        else:
            out.append('### ⚠️ 데이터 갱신은 됐지만 확인할 것이 있습니다 · %s' % kst)
            out.append('')
            out.append('**사이트는 최신 데이터로 갱신됐습니다.** %s'
                       % ('곁가지 하나가 제대로 되지 않았습니다.' if len(warn) == 1
                          else '확인할 것이 %d건 있습니다.' % len(warn)))
        out.append('')
        out.append('**하실 일: 없습니다.** 세션에서 확인합니다.')
        out.append('')
        out.append('**무슨 일인가:**')
        for ln in warn:
            out.append('- %s' % plain(ln))
        if basis:
            out.append('')
            out.append(basis)
    elif lag_hard:
        # 제목(🟡 옛 기준)과 본문 머리가 다른 말을 하면 안 된다(리뷰 2026-09-18 20번).
        out.append('### 🟡 데이터 갱신은 정상 · 일부 통계가 %d개월째 옛 기준 · %s' % (lag_months, kst))
        out.append('')
        out.append('사이트는 최신 데이터로 갱신됐습니다. 하실 일 없습니다.')
    else:
        out.append('### ✅ 데이터 갱신 정상 · %s' % kst)
        out.append('')
        if nothing:
            out.append('원천 통계가 그대로라 바뀐 내용이 없습니다. 사이트는 최신 '
                       '상태입니다. 하실 일 없습니다.')
        else:
            out.append('사이트가 최신 데이터로 갱신됐습니다. 하실 일 없습니다.')
        if basis:
            out.append('')
            out.append(basis)

    # ℹ️ 로 시작하지만 뒤처짐 줄이 아닌 것(비핵심 원천 실패 등)은 '참고'로 싣는다. 메일을 부르지 않는다.
    info = [ln for ln in lines if ln.lstrip().startswith(ML.MARK) and not LAG_LINE.match(ln)]
    if info and (mention_preview(bad, warn, weekday, lag_hard)):
        out.append('')
        out.append('**참고:**')
        for ln in info:
            out.append('- %s' % plain(ln.lstrip().lstrip(ML.MARK).strip()))

    if lag_say:
        out.append('')
        out.append('**기준월이 뒤처진 통계:** %s' % lag_say)
        if lag_hard:
            out.append('')
            out.append('**하실 일: 없습니다.** 다만 이만큼 길어진 것은 원천 사정만으로 '
                       '보기 어려워, 세션이 대안을 검토해 알려 드립니다.')

    mention = bool(bad or warn) or weekday == 0 or lag_hard
    if mention and weekday == 0 and not (bad or warn):
        out.append('')
        out.append('(월요일 확인 메일입니다. 이상이 있을 때만 메일이 가고, 평소에는 '
                   '조용합니다.)')
    out.append('')
    tail = '[실행 로그](%s)' % run_url
    if mention:
        tail += ' · @%s' % owner
    out.append(tail)
    return '\n'.join(out) + '\n', mention


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('report')
    ap.add_argument('--kst', required=True)
    ap.add_argument('--run-url', required=True)
    ap.add_argument('--owner', required=True)
    ap.add_argument('--weekday', type=int, required=True, help='0=월 … 6=일')
    ap.add_argument('--meta', help='첫 줄에 메일 여부(1/0), 둘째 줄에 제목을 적을 파일')
    a = ap.parse_args(argv)
    raw = io.open(a.report, encoding='utf-8', errors='replace').read()
    body, mention = build(raw, a.kst, a.run_url, a.owner, a.weekday)
    if a.meta:
        # 워크플로가 읽는다: 메일을 보낼 회차인가(=이슈에 코멘트를 남길 것인가)와 그 제목.
        io.open(a.meta, 'w', encoding='utf-8', newline='\n').write(
            '%d\n%s\n' % (1 if mention else 0, headline(raw, a.kst, a.weekday)))
    sys.stdout.write(body)
    return 0


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    raise SystemExit(main())
