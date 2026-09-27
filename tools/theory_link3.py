# -*- coding: utf-8 -*-
"""사이클 이론 4편(고리 ③ 집값 상승 → 공급 증가, 땅이 있는 곳에서만)의 숫자를 데이터에서 센다.

4편 본문(make_theory_post.POSTS n=4)의 %(키)s 자리는 전부 여기서 채운다. 사람이 센 수를 본문에 박지 않는다
(CLAUDE.md 데이터 원칙). 계열은 사이트가 쓰는 것 그대로다: adv['permits'](국토교통부 아파트 인허가, 반기),
sts['매매지수'](한국부동산원 아파트 실거래가격지수), sts['미분양']·sts['착공']·sts['아파트멸실'],
adv['sido'] 판정(zones 의 split·pbr), /cycle/ 의 정본 D(고리 ③ 시도별 상관·lead_new).

본문의 단정("2007년 이후 가장 적었다", "두 배를 넘은 곳은 경북·전북" 등)은 assert 로 고정한다. 데이터가 바뀌어
단정이 거짓이 되면 link3_numbers 가 Link3ClaimError 로 멈추고, make_theory_post 가 초안 생성을 멈춘다 —
문장을 자동으로 갈아 끼우지 않는다(3편 check_sync_claims 와 같은 원칙: 그건 사람이 다시 쓸 글이다).
2026-09-27 마케팅 세션이 원고와 함께 만들고, 숫자 검증자가 식 69개를 독립적으로 다시 돌려 확인했다.
표준 라이브러리만 쓴다.
"""
import io
import json
import os
import re

import sido_zones as SZ

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Link3ClaimError(Exception):
    """4편 본문의 단정이 데이터와 어긋난다."""


def link3_numbers(adv, sts):
    """4편 본문 자리 표시자 → 값(문자열). 단정이 깨지면 Link3ClaimError."""
    p = adv['permits']
    R = p['regions']
    SIDO = [rg for rg in R if rg not in SZ.AGG]
    JB = [rg for rg in SIDO if SZ.REGION[rg] == '지방']

    def A(rg, y):                     # 그해 아파트 인허가(반기 두 개 합)
        return sum(r['v'][R.index(rg)] or 0 for r in p['rows'] if r['p'][:4] == str(y))

    def H(rg, k):                     # 반기 값 한 칸('2026H1')
        return next(r['v'][R.index(rg)] for r in p['rows'] if r['p'] == k)

    mm = sts['매매지수']
    MD = [d.split()[0] for d in mm['dates']]      # '2026.07 p)' 같은 잠정 표시를 뗀다

    def X(rg, d):
        return mm['series'][rg][MD.index(d)]

    def G(rg):                        # 전국 동반 상승기(2019.06→2021.12) 매매지수 상승률 %
        return (X(rg, '2021.12') / X(rg, '2019.06') - 1) * 100

    def Q(rg):                        # 인허가 연평균 배수: 2018~19 → 2021~22(값에 1년 늦게 반응)
        return ((A(rg, 2021) + A(rg, 2022)) / 2) / ((A(rg, 2018) + A(rg, 2019)) / 2)

    D = json.loads(re.search(r'const D\s*=\s*(\{.*?\});', io.open(
        os.path.join(ROOT, 'cycle', 'index.html'), encoding='utf-8').read(), re.S).group(1))

    def Z(z):
        return next(x for x in adv['sido']['zones'] if x['z'] == z)

    def SP(z, i):                     # 판정 split 문장의 퍼센트
        return int(re.search(r'(\d+)%', Z(z)['split']['rows'][i][1]).group(1))

    c = sts['착공']

    def S(a, b):                      # 전국 아파트 착공 합(a~b년)
        return sum(v or 0 for d, v in zip(c['dates'], c['series']['전국']) if a <= int(d[:4]) <= b)

    def PA(a, b):                     # 전국 아파트 인허가 합(a~b년)
        return sum(A('전국', y) for y in range(a, b + 1))

    def _sudo_px():
        # [공통] 각 python은 def f(adv, sts): 의 본문이고 전역에 P(make_naver_post)와 json이 있어야 한다. 위치 슬라이스 대신 SIDO·JB를 sido_zones의 AGG·REGION으로 센다. 이 키: 수도권 아파트 실거래가격지수 상승률 2019.06→2021.12
        return '%.0f%%' % G('수도권')

    def _sudo_pm():
        # 수도권 아파트 인허가 감소율: 2018~19 연평균 → 2021~22 연평균
        return '%.0f%%' % ((1-Q('수도권'))*100)

    def _jb_px():
        # 지방 매매지수 상승률 2019.06→2021.12
        return '%.0f%%' % G('지방')

    def _jb_pm():
        # 지방 인허가 증가율: 2018~19 연평균 → 2021~22 연평균
        return '%.0f%%' % ((Q('지방')-1)*100)

    def _boom_n():
        # 상승기에 모두 오른 시도 수(nsido 대신 permits 시도를 직접 셈). 전제 두 가지를 assert로 고정: 모든 시도가 올랐고, 2022년 이후 시작한 30개월 구간에는 모든 시도가 10% 넘게 오른 적이 없다('가장 최근에 전국이 함께 오른 시기')
        assert all(G(rg)>0 for rg in SIDO)
        for a in range(MD.index('2022.01'), len(MD)-30):
            assert min(mm['series'][rg][a+30]/mm['series'][rg][a]-1 for rg in SIDO) < 0.10
        return str(len(SIDO))

    def _boom_min():
        # 상승기 시도별 매매지수 상승률의 최솟값(제주 19.3%)
        return '%.0f%%' % min(G(rg) for rg in SIDO)

    def _boom_table():
        # 상승기 시도별 매매가 상승률과 인허가 연평균(2018~19 → 2021~22) 변화 표. 수도권·지방 굵게, 서울·경기·인천, 지방 시도는 변화 큰 순(JB는 sido_zones에서 셈)
        rows=[('수도권',1),('지방',1),('서울',0),('경기',0),('인천',0)]
        rows+=[(rg,0) for rg in sorted(JB, key=lambda rg: -Q(rg))]
        def f(rg,b):
            pre=(A(rg,2018)+A(rg,2019))/2; post=(A(rg,2021)+A(rg,2022))/2
            c=lambda s: '<b>%s</b>'%s if b else s
            return '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (c(rg), c('+%.0f%%'%G(rg)), c(format(round(pre),',')), c(format(round(post),',')), c('%.2f배'%(post/pre)))
        return ('<table border="1" cellspacing="0" cellpadding="6"><thead><tr><th>지역</th><th>매매가 상승률<br>(2019.6→2021.12)</th><th>인허가 연평균<br>2018~2019</th><th>인허가 연평균<br>2021~2022</th><th>변화</th></tr></thead><tbody>' + ''.join(f(rg,b) for rg,b in rows) + '</tbody></table>')

    def _se_px():
        # 서울 매매지수 상승률 2019.06→2021.12
        return '%.0f%%' % G('서울')

    def _se_pm():
        # 서울 인허가 증가율 2018~19 → 2021~22 연평균
        return '%.0f%%' % ((Q('서울')-1)*100)

    def _ic_q():
        # 인천 인허가 배수(본문 '절반')
        return '%.1f배' % Q('인천')

    def _jb_sido_n():
        # 지방 시도 수(sido_zones.REGION에서 셈)
        return str(len(JB))

    def _jb_up_n():
        # 지방 시도 가운데 인허가 연평균이 늘어난 곳 수
        return str(sum(1 for rg in JB if Q(rg)>=1))

    def _gb_q():
        # 경북 인허가 배수. '두 배를 넘은 곳은 경북·전북'이라는 문장 전제를 assert로 고정
        assert {rg for rg in JB if Q(rg)>2}=={'경북','전북'}
        return '%.1f배' % Q('경북')

    def _jbk_q():
        # 전북 인허가 배수
        return '%.1f배' % Q('전북')

    def _jb_down():
        # 지방 시도 가운데 인허가가 줄어든 곳. 본문이 세 곳을 하나씩 설명하므로 목록이 바뀌면 assert로 멈춘다
        d=[rg for rg in JB if Q(rg)<1]
        assert set(d)=={'대구','세종','강원'}, d
        return '·'.join(d)

    def _gw_q():
        # 강원 인허가 배수. '대구와 강원은 앞선 상승기를 거치며 인허가를 2007년 이후 가장 많이 늘려 둔 뒤'(강원 2016년, 대구 2018년 최대)를 assert로 고정
        for rg in ('대구','강원'):
            assert max(range(2007,2026), key=lambda y: A(rg,y)) in range(2015,2019), rg
        return '%.1f배' % Q('강원')

    def _l3_k():
        # 사이트 고리③ 정본: 연결 강도를 잰 시도 수(세종·제주 제외)
        return str(len(D['link3_regional']))

    def _l3_n():
        # 사이트 고리③ 정본: 시도별 연간 관측 수(년)
        return D['prose']['l3_n']

    def _l3_top2():
        # 사이트 고리③ 정본: 연결이 가장 뚜렷한 두 곳
        return D['prose']['l3_top2']

    def _l3_se():
        # 사이트 고리③ 정본: 서울 상관계수
        return '%.2f' % next(x['r'] for x in D['link3_regional'] if x['region']=='서울')

    def _l3_gg():
        # 사이트 고리③ 정본: 경기 상관계수
        return '%.2f' % next(x['r'] for x in D['link3_regional'] if x['region']=='경기')

    def _dg_pk():
        # 대구 매매지수 정점 시점(2012.12~2016.11)
        s=mm['series']['대구']; pk=max(range(MD.index('2012.12'), MD.index('2016.12')), key=lambda i: s[i]); y,m=MD[pk].split('.'); return '%s년 %d월' % (y, int(m))

    def _dg_px():
        # 대구 매매지수 2012.12 → 정점 상승률
        s=mm['series']['대구']; i0=MD.index('2012.12'); pk=max(range(i0, MD.index('2016.12')), key=lambda i: s[i]); return '%.0f%%' % ((s[pk]/s[i0]-1)*100)

    def _dg_12():
        # 대구 아파트 인허가 2012년
        return format(A('대구',2012),',')

    def _dg_18():
        # 대구 아파트 인허가 2018년('2007년 이후 가장 많은 양' assert)
        assert max(range(2007,2026), key=lambda y: A('대구',y))==2018
        return format(A('대구',2018),',')

    def _dg_x():
        # 대구 인허가 2018/2012
        return '%.1f배' % (A('대구',2018)/A('대구',2012))

    def _dg_17():
        # 대구 인허가 2017년. '값이 꼭대기에서 내려온 뒤인 2017~2018년에 인허가가 가장 많이 나갔다'(두 해가 1·2위, 두 해 내내 지수가 2015.10 정점 아래)를 assert로 고정
        assert sorted(range(2007,2026), key=lambda y: -A('대구',y))[:2]==[2018,2017]
        s=mm['series']['대구']; pk=max(s[MD.index('2012.12'):MD.index('2016.12')])
        assert max(s[MD.index('2017.01'):MD.index('2018.12')+1]) < pk
        return format(A('대구',2017),',')

    def _dg_un21():
        # 대구 미분양 2021년 12월
        m=sts['미분양']; return format(int(m['series']['대구'][m['dates'].index('2021.12')]),',')

    def _dg_un22():
        # 대구 미분양 2022년 12월
        m=sts['미분양']; return format(int(m['series']['대구'][m['dates'].index('2022.12')]),',')

    def _dg_24():
        # 대구 인허가 2024년('2007년 이후 가장 적었고' assert)
        assert min(range(2007,2026), key=lambda y: A('대구',y))==2024
        return format(A('대구',2024),',')

    def _dg_2425():
        # 대구 인허가 2024+2025
        return format(A('대구',2024)+A('대구',2025),',')

    def _dg_1718():
        # 대구 인허가 2017+2018
        return format(A('대구',2017)+A('대구',2018),',')

    def _dg_frac():
        # 대구 2024~25 합이 2017~18 합의 몇 분의 1에도 못 미치나(내림)
        a=A('대구',2024)+A('대구',2025); b=A('대구',2017)+A('대구',2018); return '%d분의 1' % int(b//a)

    def _jb_pkm():
        # 지방 매매지수 정점 시점. 본문 '그 이듬해인 2022년'을 assert로 고정
        s=mm['series']['지방']; pk=max(range(MD.index('2019.01'), MD.index('2022.12')+1), key=lambda i: s[i]); y,m=MD[pk].split('.')
        assert y=='2021'
        return '%s년 %d월' % (y,int(m))

    def _jb_22():
        # 지방 인허가 2022년
        return format(A('지방',2022),',')

    def _jb_22since():
        # 지방 인허가가 2022년보다 많았던 마지막 해
        return str(max(y for y in range(2007,2022) if A('지방',y)>A('지방',2022)))

    def _se_tr():
        # 서울 매매지수 바닥 시점(2012~2014에서 계산, 박은 날짜 대체)
        s=mm['series']['서울']; tr=min(range(MD.index('2012.01'), MD.index('2014.12')), key=lambda i: s[i])
        y,m=MD[tr].split('.'); return '%s년 %d월' % (y,int(m))

    def _se_pk():
        # 서울 매매지수 지난 상승기 정점 시점. '지금은 지난 꼭대기를 넘어섰다'(최신 확정치 > 이 정점, 잠정치 p 제외)를 assert로 고정
        s=mm['series']['서울']; pk=max(range(MD.index('2019.01'), MD.index('2022.12')+1), key=lambda i: s[i])
        ci=[i for i,d in enumerate(mm['dates']) if 'p' not in d]
        assert s[ci[-1]] > s[pk]
        y,m=MD[pk].split('.'); return '%s년 %d월' % (y,int(m))

    def _se_x():
        # 서울 매매지수 바닥→지난 정점 배수(2.65)
        s=mm['series']['서울']; tr=min(range(MD.index('2012.01'), MD.index('2014.12')), key=lambda i: s[i]); pk=max(range(MD.index('2019.01'), MD.index('2022.12')+1), key=lambda i: s[i])
        return '%.1f배' % (s[pk]/s[tr])

    def _se_y0():
        # 서울 인허가 범위를 재기 시작한 해(바닥 이듬해)
        s=mm['series']['서울']; tr=min(range(MD.index('2012.01'), MD.index('2014.12')), key=lambda i: s[i])
        return str(int(MD[tr][:4])+1)

    def _se_min():
        # 서울 인허가 연간 최솟값(바닥 이듬해~2025)
        s=mm['series']['서울']; tr=min(range(MD.index('2012.01'), MD.index('2014.12')), key=lambda i: s[i])
        return format(min(A('서울',y) for y in range(int(MD[tr][:4])+1,2026)),',')

    def _se_max():
        # 서울 인허가 연간 최댓값(바닥 이듬해~2025)
        s=mm['series']['서울']; tr=min(range(MD.index('2012.01'), MD.index('2014.12')), key=lambda i: s[i])
        return format(max(A('서울',y) for y in range(int(MD[tr][:4])+1,2026)),',')

    def _se_2225():
        # 서울 인허가 2022~2025 연평균
        return format(round(sum(A('서울',y) for y in range(2022,2026))/4),',')

    def _se_avg():
        # 서울 인허가 2007~2025 연평균('2022~2025 연평균이 이보다 적다' assert)
        a=sum(A('서울',y) for y in range(2007,2026))/19
        assert sum(A('서울',y) for y in range(2022,2026))/4 < a
        return format(round(a),',')

    def _se_demol_y0():
        # 서울 멸실 비교 첫해(멸실 계열 마지막 해부터 10년)
        am=sts['아파트멸실']; return str(int(am['dates'][-1][:4])-9)

    def _se_demol_y1():
        # 서울 멸실 비교 끝해(멸실 계열은 연간이고 2024에서 끝남)
        am=sts['아파트멸실']; return str(int(am['dates'][-1][:4]))

    def _se_demol():
        # 서울 아파트 멸실 합 / 같은 기간 서울 아파트 인허가 합(10년)
        am=sts['아파트멸실']; y1=int(am['dates'][-1][:4]); ys=range(y1-9,y1+1)
        q=sum(am['series']['서울'][am['dates'].index(str(y))] or 0 for y in ys)/sum(A('서울',y) for y in ys)
        return '%.0f%%' % (q*100)

    def _se_demol_n():
        # 위 비율을 '허가 100호 가운데 N호'로 쓴 값
        am=sts['아파트멸실']; y1=int(am['dates'][-1][:4]); ys=range(y1-9,y1+1)
        q=sum(am['series']['서울'][am['dates'].index(str(y))] or 0 for y in ys)/sum(A('서울',y) for y in ys)
        return str(round(q*100))

    def _sd_25():
        # 수도권 인허가 2025년
        return format(A('수도권',2025),',')

    def _sd_avg():
        # 수도권 인허가 2007~2025 연평균
        return format(round(sum(A('수도권',y) for y in range(2007,2026))/19),',')

    def _jb_h1():
        # 지방 인허가 2026년 상반기
        return format(H('지방','2026H1'),',')

    def _jb_h1since():
        # 지방 상반기 인허가가 2026H1보다 적었던 마지막 해
        c=H('지방','2026H1'); return str(max(int(r['p'][:4]) for r in p['rows'] if r['p'].endswith('H1') and r['p']<'2026' and r['v'][R.index('지방')]<c))

    def _jb_roll():
        # 지방 최근 1년(2025H2+2026H1) 인허가
        return format(H('지방','2025H2')+H('지방','2026H1'),',')

    def _jb_rollpct():
        # 지방 최근 1년 / 2022년
        return '%.0f%%' % ((H('지방','2025H2')+H('지방','2026H1'))/A('지방',2022)*100)

    def _min2025():
        # 2025년 인허가가 2007년 이후 최저인 시도. 2025년 반기 값이 0이거나 비어 있는 시도(현재 세종, 원천 확인 전)는 이름을 박지 않고 규칙으로 제외한다. 본문은 전체 목록처럼 쓰지 않고 해당 시도 이름만 적는다
        z=[rg for rg in SIDO if any(not r['v'][R.index(rg)] for r in p['rows'] if r['p'][:4]=='2025')]
        return '·'.join(rg for rg in SIDO if rg not in z and min(range(2007,2026), key=lambda y: A(rg,y))==2025)

    def _sd_fut():
        # 사이트 판정 정본(adv['sido'] zones split): 수도권 앞으로 3년 들어올 물량 / 필요량
        assert Z('수도권')['split']['rows'][1][0]=='앞으로 3년'
        return '%d%%' % SP('수도권',1)

    def _jb_fut():
        # 사이트 판정 정본: 지방 앞으로 3년 / 필요량
        assert Z('지방')['split']['rows'][1][0]=='앞으로 3년'
        return '%d%%' % SP('지방',1)

    def _jb_pbr():
        # 사이트 판정 정본: 지방 최근 2년 인허가를 착공으로 환산한 값 / 필요량(3년 너머 참고치)
        return '%.0f%%' % (Z('지방')['pbr']*100)

    def _sd_past():
        # 사이트 판정 정본: 수도권 지난 4년 필요량보다 덜 지은 비율
        r=Z('수도권')['split']['rows'][0]
        assert r[0]=='지난 4년' and '덜' in r[1]
        return '%d%%' % SP('수도권',0)

    def _sd_pbr():
        # 사이트 판정 정본: 수도권 최근 2년 인허가를 착공으로 환산한 값 / 필요량(3년 너머 참고치)
        return '%.0f%%' % (Z('수도권')['pbr']*100)

    def _st_old():
        # 전국 아파트 착공 합 / 인허가 합, 2011~2021
        return '%.0f%%' % (S(2011,2021)/PA(2011,2021)*100)

    def _st_new():
        # 전국 아파트 착공 합 / 인허가 합, 2022~2025
        return '%.0f%%' % (S(2022,2025)/PA(2022,2025)*100)

    def _st_min_y():
        # 2011~2025 가운데 전국 아파트 착공이 가장 적었던 해
        return str(min(range(2011,2026), key=lambda y: S(y,y)))

    def _st_min_in():
        # 그 해 + 착공→준공 시차(사이트 정본 lead_new 개월, 년 내림)
        return str(min(range(2011,2026), key=lambda y: S(y,y)) + int(D['prose']['lead_new'])//12)

    def _lead_yr():
        # 마지막 인허가 반기의 연도 + 착공→준공 시차(년 내림)
        last=int(adv['permits']['rows'][-1]['p'][:4]); return str(last + int(D['prose']['lead_new'])//12)

    def _sens_sd():
        # 민감도: 2019~20 → 2022~23 연평균 배수(수도권). 방향이 같다는 문장을 assert로 고정
        F=lambda rg: ((A(rg,2022)+A(rg,2023))/2)/((A(rg,2019)+A(rg,2020))/2)
        assert F('수도권')<1 and F('지방')>1
        return '%.2f배' % F('수도권')

    def _sens_jb():
        # 민감도: 2019~20 → 2022~23(지방)
        F=lambda rg: ((A(rg,2022)+A(rg,2023))/2)/((A(rg,2019)+A(rg,2020))/2)
        return '%.2f배' % F('지방')

    def _sens_jb_early():
        # 민감도: 2017~18 → 2020~21(지방). 방향이 뒤집힌다는 문장을 assert로 고정
        F=lambda rg: ((A(rg,2020)+A(rg,2021))/2)/((A(rg,2017)+A(rg,2018))/2)
        assert F('지방')<1
        return '%.2f배' % F('지방')

    out = {}
    for k, f in sorted((k[1:], f) for k, f in locals().items() if k.startswith('_') and callable(f)):
        try:
            out[k] = f()
        except AssertionError as e:
            raise Link3ClaimError('4편 본문의 단정이 데이터와 어긋난다 — %s: %s' % (k, e))
    return out
