/* 아공맵 홈 — 퀴즈(부린이·투자자·재건축) 화면 코드. 홈 마케팅 검수 B11·MOB-8(2026-09-27)에 home-app.js 에서 떼어 냈다.
   지도 첫 화면은 이 코드를 쓰지 않으므로 퀴즈를 열 때(#test-…·대결 링크·다시 풀기) home-app.js 의 loadPart('quiz')가
   '/home-quiz.js?v=<HOME_BUILD>' 로 받는다. 그 전에 불린 입구(PARTS.quiz.api)는 대기열에 있다가 이 파일이 오면 부른 순서대로
   돈다 — 여기의 최상위 function 선언이 전역의 대기 함수를 덮어쓴다. 입구 함수를 없애거나 이름을 바꾸면 PARTS 도 같이
   고친다(test_home_parts). 홈 스크립트의 전역(track·showView·toast·BLV·SHARE_URL_UTM 등)을 그대로 쓴다.
   ⚠️ 홈과 한 몸이다: sw.js 가 home-app.js 와 같은 규칙(network-first)으로 받고 같은 판 주소를 사전 캐시한다.
   판 표식으로 양방향 보호한다(주소의 ?v=판 + 아래 HOME_QUIZ_BUILD, home-app.js PARTS 주석).
   도구·시험은 이 파일을 직접 열지 말고 tools/home_src.py 의 home_source() 로 읽는다(홈 스크립트에 이어 붙어 온다). */
/* 판 표식 — home-app.js HOME_BUILD·sw.js VERSION 과 같은 값(test_home_build). 받은 뒤 홈이 견줘 다르면 한 번 새로고침한다
   (partBuildOk: 열어 둔 옛 판 탭이 배포 뒤 ?v=옛판 주소로 새 판 파일을 받는 경우). VERSION 을 올리면 여기도 같이. */
var HOME_QUIZ_BUILD='v164';
const QUIZSETS={
  beginner:{
    title:'부린이 테스트', emoji:'🐣',
    shareName:'부린이 테스트',
    Q:[
  {q:'압구정 현대아파트의 정비사업은 "OOO"이다. 빈칸에 들어갈 말은?',
   opts:['재개발','재건축'],
   answer:1,
   exp:'정답은 <b>재건축</b>. <b>재건축</b>은 도로·상하수도 같은 기반시설이 멀쩡한 곳에서 낡은 "건물"만 다시 짓는 것이고, <b>재개발</b>은 기반시설 자체가 열악한 "지역 전체"를 갈아엎는 것이다. 압구정처럼 인프라가 좋은 곳의 노후 아파트 정비는 재건축이다.'},

  {q:'대단지 아파트는 오늘 착공하면 보통 <b>2년 정도</b>면 입주(준공)한다. O일까 X일까?',
   opts:['X','O'],
   answer:0,
   exp:'정답은 <b>X</b>. 착공에서 준공까지 전국 평균이 <b>과거 28개월에서 최근 37개월</b>로 늘었다(3년 남짓). 고층화·공사비 급등 등으로 길어지는 흐름이다. "지금 공급 부족"과 "몇 년 뒤 입주"가 늘 어긋나는 이유다.'},

  {q:'주택을 담보로 대출받을 때, <b>집값 대비 빌릴 수 있는 최대 비율</b>을 가리키는 말은?',
   opts:['DSR','LTV'],
   answer:1,
   exp:'<b>LTV</b>(주택담보인정비율)는 집값 대비 대출 한도다 — 5억 집에 LTV 70%면 3.5억까지. 반면 <b>DSR</b>(총부채원리금상환비율)은 "내 소득 대비 매년 갚는 원리금" 비율로, 집값이 아니라 <b>갚을 능력</b>을 본다. 둘 다 통과해야 실제 대출이 나온다.'},

  {q:'투기과열지구로 지정되면 집을 사고팔 때 <b>지자체장의 허가</b>를 받아야 한다. O일까 X일까?',
   opts:['X','O'],
   answer:0,
   exp:'정답은 <b>X</b>. 허가를 받아야 하는 건 <b>토지거래허가구역</b>(토허제)에 대한 설명이다. <b>투기과열지구</b>는 대출(LTV)·청약·전매 등을 죄는 규제지역이지만, 매매 자체에 허가가 필요한 건 아니다. 둘은 자주 겹치지만 서로 다른 제도다.'},

  {q:'정부가 지원하는 대표적인 <b>저금리 주택담보대출</b> 상품의 이름은?',
   opts:['디딤돌 대출','사잇돌 대출'],
   answer:0,
   exp:'정답은 <b>디딤돌 대출</b>. 주택도시기금이 무주택 서민에게 내 집 마련 자금을 저금리로 빌려주는 정책 상품이다. <b>사잇돌 대출</b>은 서민금융진흥원이 보증하는 <b>중금리 신용대출</b>로, 주택 구입 자금과는 성격이 다르다.'},

  {q:'임차인은 기본 2년 거주 후 <b>계약갱신청구권</b>을 쓰면 최대 2년을 더 살 수 있다. O일까 X일까?',
   opts:['X','O'],
   answer:1,
   exp:'정답은 <b>O</b>. 주택임대차보호법상 임차인은 1회 갱신을 요구할 수 있어 <b>2+2년, 최대 4년</b> 거주가 보장된다. 갱신 시 임대료 인상은 5% 이내로 제한된다.'},

  {q:'재건축을 기대하고 낡고 불편한 집에서 버티며 실거주하는 전략을 뭐라 부를까?',
   opts:['몸테크','짠테크'],
   answer:0,
   exp:'정답은 <b>몸테크</b>. "몸(身)+재테크"의 합성어로, <b>몸이 고생하는 대신</b> 미래의 재건축·시세차익을 노리고 낡은 집에 직접 사는 전략이다. 반면 <b>짠테크</b>는 짠돌이처럼 소비를 아껴 돈을 모으는 절약 재테크를 뜻한다.'},

  {q:'집주인이 "내가 실거주하겠다"고 하면, 임차인은 계약갱신청구권을 쓰지 못하고 나가야 할 수 있다. O일까 X일까?',
   opts:['X','O'],
   answer:1,
   exp:'정답은 <b>O</b>. 집주인(또는 직계존비속)의 <b>실거주</b>는 갱신 거절의 정당한 사유다. 단, 거절해 놓고 실제로는 살지 않고 제3자에게 세를 놓으면 임차인은 손해배상을 청구할 수 있어, 집주인도 함부로 악용하긴 어렵다.'},

  {q:'규제지역에서 <b>생애최초</b> 주택 구입자는 일반 구매자보다 LTV를 더 많이(최대 70%) 받을 수 있다. O일까 X일까?',
   opts:['X','O'],
   asof:'2026-09-15', review:'2027-03-15',
   answer:1,
   exp:'정답은 <b>O</b>. 생애최초 구입자는 우대를 받아 규제지역에서도 <b>LTV 70%</b>가 적용된다(과거 80%에서 6·27 대책으로 하향). 다만 6개월 내 전입(실거주) 의무가 붙고, 주담대 한도 6억원 제한도 함께 적용된다.'},

  {q:'신용대출을 <b>1억원 넘게</b> 받으면 일정 기간 규제지역 내 주택 구입이 막힌다. O일까 X일까?',
   opts:['O','X'],
   asof:'2026-09-15', review:'2027-03-15',
   answer:0,
   exp:'정답은 <b>O</b>. 2025년 6·27 대책으로 <b>1억원 초과 신용대출</b>을 받으면 대출 실행일로부터 <b>1년간 규제지역 주택 구입이 금지</b>된다. 신용대출을 끌어다 집을 사는 우회로를 막기 위한 조치다. (신용대출 한도 자체도 연소득 이내로 제한됐다.)'},

  {q:'전세 계약 후 <b>전입신고</b>를 하고 이사까지 마쳤다. 보증금을 지킬 <b>대항력</b>이 생기는 시점은?',
   opts:['이사한 그날 0시','그 다음 날 0시'],
   asof:'2026-09-15', review:'2026-12-15',
   answer:1,
   exp:'정답은 <b>다음 날 0시</b>. 대항력은 "주택 인도 + 전입신고"를 마친 <b>다음 날 0시</b>에 생긴다. 이사한 그날 집주인이 근저당을 설정하면 은행이 순위에서 앞선다는 뜻이다. 잔금일과 같은 날 근저당이 잡히지 않는지 반드시 확인해야 하는 이유다. (확정일자는 대항력과 별개로 <b>우선변제권</b>을 준다.) 다만 2026년 3월 전세사기 방지 대책에서 대항력을 <b>전입신고 처리 즉시</b> 발생시키는 법 개정이 추진 중이다 — 아직 시행 전이라 현행법 기준 정답은 다음 날 0시다.'},

  {q:'전세보증금 반환보증에 가입하려면 <b>집주인의 동의</b>가 필요하다. O일까 X일까?',
   opts:['O','X'],
   answer:1,
   exp:'정답은 <b>X</b>. 예전엔 임대인 동의가 필요했지만 <b>2018년부터 폐지</b>돼, 이제 임차인이 혼자서 가입할 수 있다. 집주인 눈치 볼 필요 없이 보증금을 지킬 수 있으니, 전세라면 가입 여부부터 따져보는 게 좋다.'},

  {q:'청약 가점 <b>84점 만점</b>은 무엇으로 채워질까?',
   opts:['무주택 기간 · 부양가족 수 · 청약통장 가입 기간','소득 · 자산 · 거주 기간'],
   answer:0,
   exp:'정답은 <b>무주택 기간(32점) + 부양가족 수(35점) + 청약통장 가입 기간(17점)</b> = 84점. 가장 배점이 큰 건 <b>부양가족 수</b>다. 소득이나 자산은 가점 항목이 아니라 특별공급 자격에서 따진다.'},

  {q:'등기부등본에서 <b>근저당권</b>(집을 담보로 잡힌 빚)은 어디에 적혀 있을까?',
   opts:['갑구','을구'],
   answer:1,
   exp:'정답은 <b>을구</b>. <b>갑구</b>에는 소유권(누구 집인지, 압류·가압류)이, <b>을구</b>에는 소유권 이외의 권리(근저당권·전세권)가 적힌다. 전세 계약 전 을구의 근저당 금액과 내 보증금을 더한 값이 집값을 넘지 않는지 꼭 확인해야 한다.'},

  {q:'재건축 조합원이 새 아파트를 받을 권리를 뭐라 부를까?',
   opts:['입주권','분양권'],
   answer:0,
   exp:'정답은 <b>입주권</b>. 기존 집을 내놓은 <b>조합원</b>이 새 아파트를 받을 권리가 입주권이고, <b>청약에 당첨</b>돼 얻은 권리가 분양권이다. 둘은 취득세·양도세 계산과 주택 수 산정 방식이 서로 달라 실전에서 자주 헷갈린다.'},

  {q:'전세 만기가 다가오는데 집주인도 나도 아무 말이 없었다. 계약은 같은 조건으로 <b>자동 연장</b>된다. O일까 X일까?',
   opts:['X','O'],
   answer:1,
   exp:'정답은 <b>O</b>. 집주인이 만기 <b>6개월~2개월 전</b>에 아무 통보를 하지 않으면 <b>묵시적 갱신</b>이 되어 같은 조건으로 2년 연장된다. 이때는 계약갱신청구권을 쓴 것으로 치지 않고, 임차인은 언제든 해지를 통보할 수 있다(3개월 뒤 효력).'},

  {q:'전용 <b>84㎡</b>가 흔히 "34평"으로 불린다. 그 34평은 무엇을 기준으로 한 숫자일까?',
   opts:['전용면적','공급면적'],
   answer:1,
   exp:'정답은 <b>공급면적</b>. 84㎡는 순수한 <b>전용면적</b>(약 25평)이고, 여기에 계단·복도 같은 <b>주거공용면적</b>을 더한 공급면적이 약 112㎡, 즉 34평이다. 같은 34평이라도 단지마다 전용률이 달라 실제 쓰는 면적은 차이가 난다.'},

  {q:'6월 1일에 집을 팔았다. 그 해 <b>재산세</b>는 판 사람이 낸다. O일까 X일까?',
   opts:['O','X'],
   answer:1,
   exp:'정답은 <b>X</b>. 재산세·종부세 과세기준일은 <b>6월 1일</b>이고, 그날의 사실상 소유자가 1년치를 낸다. 소유권(취득)은 <b>잔금지급일</b>(또는 등기접수일 중 빠른 날)에 넘어가므로, 6월 1일에 잔금을 치렀다면 그날 소유자는 이미 <b>매수인</b> — 즉 <b>산 사람</b>이 낸다. 그래서 파는 쪽은 <b>5월 31일 이전</b>에, 사는 쪽은 <b>6월 2일 이후</b>에 잔금을 선호한다.'},

  {q:'분양가상한제 아파트는 시세보다 싸서 "로또 청약"으로 불린다. 그 대가로 붙는 조건은?',
   opts:['전매 제한 · 실거주 의무','장기보유특별공제 배제'],
   answer:0,
   exp:'정답은 <b>전매 제한과 실거주 의무</b>. 싸게 받은 만큼 일정 기간 팔 수 없고, 직접 살아야 한다. 시세차익만 챙기고 바로 파는 걸 막기 위한 장치다. <b>장기보유특별공제</b>는 보유·거주 기간에 따라 양도세를 깎아주는 제도로, 분양가상한제 주택이라고 배제되지 않는다 — 오히려 실거주 의무를 채우며 오래 보유하면 공제를 더 받는다.'},

  {q:'부동산 <b>중개보수</b>(복비)는 법에 정해진 <b>상한 금액을 넘겨</b> 받을 수 없다. O일까 X일까?',
   opts:['O','X'],
   answer:0,
   exp:'정답은 <b>O</b>. 법과 조례는 거래 금액 구간별로 <b>상한 요율</b>을 정해 두고, 이를 초과해 받는 것은 불법이다. 다만 정해진 건 어디까지나 <b>상한</b>이라 그 한도 안에서는 중개사와 협의해 낮출 수 있다 — 상한이 곧 정찰가는 아니다.'},
    ],
    grade:s=>BLV[Math.max(0,Math.min(10,s|0))]
  },
  investor:{
    title:'투자자 테스트', emoji:'🦅',
    shareName:'투자자 테스트',
    Q:[
  {q:'2026년 수도권처럼 <b>공급이 부족한</b> 상황에서, 정부가 규제로 매매 수요를 누르고 전세대출한도까지 조여 전세도 누르면 <b>월세</b>는?',
   opts:['상승','하락'],
   answer:0,
   exp:'정답은 <b>상승</b>. 사람은 매매든 전세든 월세든 <b>어딘가엔 살아야 한다.</b> 공급이 부족한 상태에서 매매·전세를 동시에 규제로 누르면, 갈 곳 잃은 실수요가 결국 <b>월세 시장으로 밀려난다.</b> 규제가 특정 시장을 눌러도 총 주거 수요 자체가 사라지는 건 아니라는 뜻이다.'},

  {q:'재건축·재개발이 외곽보다 <b>중심지·핵심지</b>에서 먼저 시작되는 이유는?',
   opts:['용적률','분양가'],
   answer:1,
   exp:'정답은 <b>분양가</b>. 핵심지는 <b>일반분양가를 높게 책정</b>할 수 있어, 전체 사업비에서 공사비가 차지하는 비중이 낮고 사업성이 좋다. 반면 외곽은 분양가가 낮아 공사비 부담이 상대적으로 커 사업성이 떨어진다. 사업성이 워낙 좋은 강남 같은 곳에서는 <b>일반분양 없이 조합원끼리 새로 짓는 1:1 재건축</b>도 진행된다.'},

  {q:'"투기과열지구 지정" 같은 규제가 시장에 남기는 효과로 가까운 것은?',
   opts:['단기엔 누르고 길게는 올린다','길게 봐도 집값을 누른다'],
   answer:0,
   exp:'단기에는 대출·청약·전매 제한으로 거래와 가격이 눌린다. 그러나 규제가 신규 공급과 정비사업을 위축시키면 몇 년 뒤 공급이 줄어, <b>상승 국면이 더 길어지는</b> 쪽으로 작동할 수 있다. 호재·악재는 보는 기간에 따라 갈린다.'},

  {q:'대출 금리는 매매가에만 영향을 주고 전월세에는 큰 영향이 없다. O일까 X일까?',
   opts:['O','X'],
   answer:1,
   exp:'정답은 <b>X</b>. <b>전세자금대출</b>이 보편화되면서 금리는 전세에도 직접 영향을 미친다. 금리가 오르면 전세대출 이자 부담이 커져 <b>전세 수요가 월세로 이동</b>하고, 전세가와 월세가 모두 흔들린다. 금리는 매매·전세·월세 전부를 덮는 변수다.'},

  {q:'다주택자 "취득세 중과"가 지역별로 남기는 효과로 가까운 것은?',
   opts:['모든 지역 같은 부담','핵심지는 쏠리고 외곽은 부담'],
   answer:1,
   exp:'여러 채 대신 <b>똘똘한 한 채</b>로 좁히게 만들어 수요가 핵심지로 모인다. 같은 규제가 핵심지 보유자에게는 버팀목, 지방·외곽 보유자에게는 부담으로 갈린다.'},

  {q:'전세가율이 오르면(매매가와 전세가 차이가 줄면), <b>갭투자</b>에 필요한 자기자본은 어떻게 될까?',
   opts:['줄어든다','늘어난다'],
   asof:'2026-09-15', review:'2027-03-15',
   answer:0,
   exp:'정답은 <b>줄어든다</b>. 갭투자는 매매가와 전세가의 "갭(차이)"만큼만 내 돈을 넣고 집을 사는 방식이다. 전세가율이 오를수록 갭이 작아져 적은 돈으로 가능해진다. 6·27 대책의 "소유권 이전 조건부 전세대출 금지"가 바로 이 갭투자를 겨냥한 규제다.'},

  {q:'광범위한 대출 규제(LTV·DSR 강화)는 <b>중장기적으로</b> 집값에 어떻게 작용할까?',
   opts:['살 돈 줄어 하락 압력','신규 공급 막아 상승 압력'],
   answer:1,
   exp:'대출 규제는 <b>단기적으론</b> 매수 수요를 눌러 하락 압력으로 작용한다. 하지만 재건축·재개발 <b>이주비 대출</b>, 신축 <b>중도금·잔금 대출</b>까지 함께 막히면서 분양과 신규 공급도 위축된다. 수요·공급을 동시에 조이는데, <b>공급 위축 효과가 더 오래 남아</b> 중장기적으로는 상승 압력이 된다.'},

  {q:'"집값이 오르면 공급(인허가)이 따라 는다"는 관계, <b>서울</b>에서는 어떻게 나타날까?',
   opts:['빈 땅이 없어 시차를 두고 나타남','집값이 오르면 당연히 즉각적으로 늘어남'],
   answer:0,
   exp:'서울은 <b>택지가 없어</b> 집값이 올라도 인허가가 곧바로 따라오지 못한다. 땅이 있는 충북·부산 등은 약 1년 시차를 두고 공급이 늘어나지만, 서울처럼 <b>빈 땅 자체가 없는 지역</b>은 그마저도 거의 작동하지 않을 만큼 관계가 약하다. 서울의 만성 공급 부족이 여기서 비롯된다.'},

  {q:'서울 아파트의 전세가율이 지방보다 <b>낮다</b>는 것은 무엇을 뜻할까?',
   opts:['실거주 수요 위주다','투자·기대 수요가 두껍다'],
   answer:1,
   exp:'전세가율(전세÷매매)이 <b>낮으면</b> 매매가가 전세보다 훨씬 높다는 뜻 — 거주 가치보다 <b>미래 상승 기대</b>에 더 많이 지불하는 투자 시장이다. 서울이 대표적. 반대로 전세가율이 높은 지방은 가격이 거주 가치에 수렴한 실거주 시장이다. 지금 수치는 <a href="/jeonse-ratio/">전세가율 페이지</a>에서 볼 수 있다.'},

  {q:'"부동산 슈퍼사이클"의 정체는?',
   opts:['80년대 말~90년대 초 대량 공급의 멸실 도래','베이비붐 세대의 은퇴와 인구절벽 시작'],
   answer:0,
   exp:'정답은 <b>멸실(재건축) 슈퍼사이클</b>. 1980년대 후반 올림픽 전후로 시작돼 <b>1기 신도시(분당·일산 등)로 이어진 대량 공급</b>이 <b>준공 40년 안팎</b>(물리적 노후·멸실 시점)에 도달하기 시작하는 때가 2028년이다. 법정 재건축 연한은 준공 후 30년이지만, 실제 멸실·재건축은 대체로 그보다 늦게 이뤄진다. 헐어야 할 노후 재고는 폭증하는데 멸실 속도는 못 따라가, 순공급이 장기간 제약된다.'},

  {q:'어떤 지역에 공급 부족이 닥쳤다. <b>대체로</b> 전세와 매매 중 무엇이 먼저 움직일까?',
   opts:['전세','매매'],
   answer:0,
   exp:'정답은 <b>전세</b>. 전세는 <b>지금 당장 살 집</b>이 필요한 실수요라 공급 부족에 즉각 반응한다. 매매는 기대·금리·규제가 섞여 한 박자 늦게 따라온다. 이 리포트의 고리①②가 바로 "공급 부족 → 전세 → 매매"의 순서다.'},

  {q:'오늘 <b>인허가</b>가 난 아파트, <b>입주 시점</b>을 지금 셀 수 있을까?',
   opts:['착공해야 셀 수 있다','허가 날짜로 셀 수 있다'],
   answer:0,
   exp:'정답은 <b>착공해야 셀 수 있다</b>. 인허가는 착공과 같은 흐름으로 움직이지만 <b>허가 뒤 착공하지 않는 물량</b>이 섞여 있고 착공 시점도 제각각이라, 입주까지의 시차가 일정하지 않다. 착공한 뒤부터는 잰 값이 있다. 전국 평균이 <b>과거 28개월에서 최근 37개월</b>이다. 그래서 공급을 판정할 때는 착공 실적을 쓰고 인허가는 참고로만 본다.'},

  {q:'전세가 <b>상승 중</b>일 때 입주 물량이 늘어나면, 전세 가격은 즉각 하락으로 반전한다. O일까 X일까?',
   opts:['O','X'],
   answer:1,
   exp:'정답은 <b>X</b>. 데이터로 보면 입주가 늘어도 <b>누적 재고 수준이 낮은</b> 구간에서는 전세가 오히려 분기당 <b>+1.88%</b> 올랐고, <b>누적 수준까지 높아졌을 때</b>에야 0.00%로 눌렸다. 물량의 <b>증가</b>만으로는 부족하고 쌓인 <b>수준</b>이 함께 높아야 꺾인다 — 그래서 반전은 즉각적이지 않고 시차를 두고 온다.'},

  {q:'사이클 <b>한 바퀴</b>가 도는 데 더 오래 걸리는 쪽은?',
   opts:['수도권','지방'],
   answer:0,
   exp:'정답은 <b>수도권</b>. 주기는 재본 값이 아니라 <b>각 단계의 시차를 더해 만들어진 값</b>이다 — 착공에서 입주까지 3년 남짓(최근 37개월), 입주 증가가 전세를 밀어내리기까지 반년~1년, 전세 하락이 매매로 옮아가는 데 1년 남짓. 여기에 수도권은 <b>유동성장</b>(전세는 내리는데 매매는 오르는 구간)이 1년~1년 반 더 붙지만 지방은 이 구간이 거의 없다. 그만큼 수도권의 한 국면이 길게 늘어진다. 다만 이건 <b>기준점이지 시계가 아니다</b> — 부양책·규제책이 개입하면 사이클은 늘어나고 줄어든다. 인과의 순서가 유지될 뿐, 햇수가 고정된 건 아니다.'},

  {q:'전세와 매매가 <b>가장 따로 노는</b>(동조성이 낮은) 지역은?',
   opts:['지방 광역시','서울'],
   answer:1,
   exp:'정답은 <b>서울</b>. 전세는 거주 가치를, 매매는 기대 가치를 반영한다. 서울은 <b>투자·기대 수요가 두꺼워</b> 매매가 전세와 무관하게 움직이는 구간이 길다. 반대로 지방은 둘이 거의 붙어 다닌다 — 가격이 거주 가치에 수렴하기 때문이다.'},

  {q:'이 리포트에서 <b>금리</b>는 사이클의 어디에 놓여 있을까?',
   opts:['사이클 바깥에서 순환 전체를 흔드는 외부 힘','전세와 매매를 잇는 고리의 하나'],
   answer:0,
   exp:'정답은 <b>사이클 바깥</b>. 공급→전세→매매→공급은 스스로 도는 <b>내부 순환</b>이고, 금리는 그 바깥에서 순환의 진폭과 속도를 바꾸는 <b>외부 변수</b>다. 2021년 초저금리가 사이클을 통째로 밀어올린 것이 대표적이다. 다만 <b>바깥에 있다는 게 무시해도 된다는 뜻은 아니다</b> — 전세가율×전환율(주거비 수익률)이 대출금리를 넘어서는 지점이 추세 상승의 출발선이고, 반대로 금리가 그 수익률을 크게 웃돌면 하락 국면으로 넘어간다. 미리 예측할 수는 없지만, 일단 움직이면 <b>전환점을 읽는 지표</b>가 된다.'},

  {q:'대규모 재건축 <b>이주</b>가 시작되면, 그 동네 전세는 단기적으로?',
   opts:['하락','상승'],
   answer:1,
   exp:'정답은 <b>상승</b>. 재건축은 새 집을 짓기 전에 먼저 <b>기존 집을 없앤다</b>(멸실). 쫓겨난 수천 세대가 인근 전세를 동시에 찾으면서 단기 전세난이 벌어진다. 공급을 늘리려는 행위가 <b>단기적으로는 공급을 줄이는</b> 역설이다.'},

  {q:'<b>준공 후 미분양</b>(악성 미분양)이 급증했다. 중장기적으로 이건 무슨 신호일까?',
   opts:['장기 침체가 확정된 신호','몇 년 뒤 공급 절벽의 씨앗'],
   answer:1,
   exp:'미분양이 쌓이면 건설사는 <b>신규 착공을 멈춘다.</b> 그 멈춤은 착공에서 준공까지 걸리는 3년 남짓(최근 37개월) 뒤에 입주 물량의 공백으로 돌아온다. 즉 지금의 미분양은 <b>몇 년 뒤 공급 절벽</b>을 예고하는 선행 지표다. 사이클이 바닥에서 반등하는 방아쇠가 대개 여기서 당겨진다.'},

  {q:'바닥을 기던 <b>전세가율</b>이 다시 오르기 시작했다. 매매 시장에는?',
   opts:['상승 압력이 쌓이고 있다','하락이 임박했다'],
   answer:0,
   exp:'전세가율이 오른다는 건 매매가는 그대로인데 <b>전세가 밀어올려지고 있다</b>는 뜻이다. 갭이 좁아질수록 매수 문턱이 낮아지고, 어느 순간 전세가 매매를 끌어올린다(고리②). 그래서 전세가율 반등은 매매 상승의 <b>선행 신호</b>로 읽힌다.'},

  {q:'<b>약 3년 뒤</b> 입주 물량을 가장 정확히 예고하는 지표는?',
   opts:['인허가 물량','착공 물량'],
   answer:1,
   exp:'정답은 <b>착공</b>. 인허가는 났어도 <b>사업성이 안 나오면 삽을 뜨지 않는다</b> — 인허가와 실제 공급 사이엔 이탈이 크다. 반면 착공은 돈이 들어간 뒤라 3년 남짓(최근 37개월) 뒤 준공으로 거의 그대로 이어진다. 입주 물량을 읽으려면 인허가가 아니라 착공을 봐야 한다.'},
    ],
    grade:s=>{
      if(s>=9)return{lv:'LV5',g:'지역별 공급 물량을 꿰고 있는 승부사',d:'규제의 이면도, 사이클의 역방향도 읽어냅니다. 입주물량 표를 머릿속에 펼쳐 두고 1년 뒤를 계산하는 경지. 이 리포트를 쓴 사람과 토론해도 됩니다.',emoji:'🏆'};
      if(s>=7)return{lv:'LV4',g:'무주택이어도 머릿속에선 이미 최소 다주택자',d:'공급과 전세가 어떻게 맞물리는지 분명히 이해합니다. 통념에 휘둘리지 않는 시야 — 실탄만 모이면 바로 움직일 사람.',emoji:'🔭'};
      if(s>=5)return{lv:'LV3',g:'집 사놓고 불안해서 밤에 잠 못 드는 단계',d:'감은 잡혔지만 확신이 없어 호가창을 자꾸 들여다보는 단계. 사이클의 큰 그림을 한 번 더 정독하면 밤잠이 편해집니다.',emoji:'🌙'};
      if(s>=3)return{lv:'LV2',g:'호재·악재 거꾸로 읽는 초보',d:'"규제=악재" 같은 통념에 아직 갇혀 있습니다. 괜찮아요, 이 리포트가 바로 그 통념을 깨려고 만들어졌으니까요.',emoji:'🧭'};
      return{lv:'LV1',g:'통념에 갇힌 부동산 왕초보',d:'"규제=악재, 입주=호재"부터 다시. 이 리포트가 바로 그 통념을 깨려고 만들어졌습니다. 정독하고 재도전!',emoji:'🌱'};
    }
  },
  calc:{
    title:'재건축·재개발 테스트', emoji:'🏗️',
    shareName:'재건축·재개발 테스트',
    Q:[
  {q:'매매가 <b>4억</b>, 대지지분 <b>10평</b>짜리 재건축 대상 아파트. <b>개발 전</b> 대지 1평의 가치는?',
   opts:['4,000만원','8,000만원'],
   answer:0,
   exp:'개발 전 가치 = <b>매매가 ÷ 대지지분</b>. 4억 ÷ 10평 = <b>평당 4,000만원</b>. 재건축 물건은 건물이 아니라 땅을 사는 것이므로, 모든 계산은 대지지분 1평 기준에서 시작한다.'},

  {q:'개발 전 매매가 <b>3억</b>, 대지지분 <b>10평</b>. 용적률 <b>300%</b>, 공사비 평당 <b>1,000만원</b>으로 개발 시 분양가는 평당 <b>3,000만원</b>. 이 조합원의 <b>기대수익</b>은?',
   opts:['3억','6억'],
   answer:0,
   exp:'개발 전 평당 가격 = 3억 ÷ 10평 = 3,000만원. 개발 후 평당 수익 = (3,000 − 1,000) × 3 = <b>6,000만원</b>. 기대수익 = <b>(개발 후 − 개발 전) × 대지지분</b> = (6,000 − 3,000) × 10평 = <b>3억</b>. 개발 후 전체(6억)가 아니라 지금 가격과의 <b>차이</b>만 내 몫이라는 점이 핵심이다.'},

  {q:'<b>개발 후</b> 용적률 <b>200%</b>로 짓는 재건축 단지에서 평당 공사비가 <b>1,000만원 → 1,500만원</b>으로 올랐다. 개발 후 대지 1평의 수익은 얼마나 줄어들까?',
   opts:['500만원','1,000만원'],
   answer:1,
   exp:'공사비 인상분 500만원에 <b>용적률 배수(×2)</b>가 곱해져 <b>1,000만원</b>이 줄어든다. 용적률이 높을수록 공사비 변동이 그대로 증폭돼 <b>걸린 금액이 커진다</b> — 요즘 재건축 단지들이 공사비 협상에 사활을 거는 이유다. 다만 마진(분양가 − 공사비)도 같은 배수로 커지므로 <b>"용적률이 높으면 공사비에 더 취약하다"는 뜻은 아니다.</b> 진짜 위험한 쪽은 마진이 얇아 조금만 올라도 개발 후 가치가 개발 전을 밑도는 단지다.'},

  {q:'개발 전 평당 <b>4,000만원</b> → 개발 후 평당 <b>6,000만원</b>으로 분명한 흑자인데, 대지지분이 <b>5평</b>뿐인 소형 평형 단지. 사업이 잘 안 굴러가는 이유는?',
   opts:['기대수익 절대액이 작아서','용적률이 낮아서'],
   answer:0,
   exp:'기대수익 = (6,000 − 4,000) × 5평 = <b>1억뿐</b>. 이주와 분담금, 수년의 리스크를 감수하기엔 남는 돈이 작아 조합원들이 움직이지 않는다. <b>평당 수익률이 아니라 수익 절대액</b>이 사업의 동력이다 — 소형·단일 평형 단지의 흔한 함정.'},

  {q:'매매가 <b>5억</b>, 대지지분 <b>10평</b>짜리 재건축 아파트. <b>개발 후</b> 용적률 <b>250%</b>로 짓고 공사비는 평당 <b>1,000만원</b>. 최소한 본전이 되려면 분양가는 평당 얼마 이상이어야 할까?',
   opts:['3,000만원','2,000만원'],
   answer:0,
   exp:'개발 전 평당 가격 = 5억 ÷ 10평 = <b>5,000만원</b>. (분양가 − 1,000) × 2.5 ≥ 5,000 → 분양가 − 1,000 ≥ 2,000 → 분양가 <b>3,000만원</b>. 5,000을 2.5로 나눈 뒤 공사비를 <b>다시 더해야</b> 한다는 걸 잊기 쉽다. 주변 신축 시세가 이보다 낮다면 그 단지는 아직 때가 아니다.'},

  {q:'개발 전 매매가 <b>6억</b>, 대지지분 <b>15평</b>. 용적률 <b>400%</b>, 공사비 평당 <b>1,500만원</b>으로 개발 시 분양가는 평당 <b>2,500만원</b>. 사업성은?',
   opts:['있다','없다'],
   answer:1,
   exp:'개발 전 평당 = 6억 ÷ 15평 = 4,000만원. 개발 후 = (2,500 − 1,500) × 4 = <b>4,000만원</b> — 개발 전과 <b>똑같다</b>. 남는 게 0이면 공사비가 조금만 올라도 적자로 뒤집히니, 이 물건만 놓고 보면 사업성이 없다. 다만 <b>동점이 곧 "별 볼 일 없는 곳"이라는 뜻은 아니다</b> — 정보가 열려 있고 관심이 많은 단지일수록 시세가 개발 후 가치를 쫓아 올라와 <b>늘 동점 근처</b>에 머문다. 그런 곳의 투자 근거는 지금의 차익이 아니라 <b>앞으로의 분양가 상승분 × 용적률 배수</b>다.'},

  {q:'A단지: 평당 차익 <b>1,000만원</b> × 지분 <b>20평</b>. B단지: 평당 차익 <b>3,000만원</b> × 지분 <b>5평</b>. 재건축 추진 동력이 더 큰 쪽은?',
   opts:['A단지','B단지'],
   answer:0,
   exp:'A = 1,000 × 20 = <b>2억</b>, B = 3,000 × 5 = <b>1.5억</b>. 평당 차익은 B가 3배지만, 조합원을 움직이는 건 <b>총 기대수익</b>이다. 재건축은 언제나 "평당"이 아니라 "내 몫 전체"로 판단한다.'},

  {q:'하락장이 끝나고 분양가가 <b>바닥에서 회복</b>되기 시작했다. 공사비는 전국 어디든 평당 <b>700만원</b>으로 거의 같다. 재건축 사업성이 <b>먼저</b> 살아나는 곳은?',
   opts:['분양가 평당 1,000만원인 곳','분양가 평당 800만원인 곳'],
   answer:0,
   exp:'공사비는 전국이 비슷하므로 사업성은 <b>(분양가 − 공사비) 마진</b>에서 갈린다. 1,000만원인 곳의 마진은 1,000 − 700 = <b>300</b>, 800만원인 곳은 800 − 700 = <b>100</b> — 3배 차이다. 분양가가 같이 회복돼도 마진이 두꺼운 비싼 동네가 훨씬 먼저 사업성 기준선을 넘는다 — 상승 전환기에 정비사업이 핵심지부터 다시 움직이는 이유다.'},

  {q:'전쟁·유가 급등 같은 인플레이션으로 평당 공사비가 전국적으로 <b>1,000 → 1,300만원</b>이 됐다. 사업성 타격이 더 큰 쪽은?',
   opts:['분양가 2,000만원 하급지','분양가 5,000만원 상급지'],
   answer:0,
   exp:'마진으로 비교하면: 하급지는 1,000 → <b>700(−30%)</b>, 상급지는 4,000 → <b>3,700(−7.5%)</b>. 같은 300만원 인상도 마진이 얇은 곳에는 치명적이다. 공사비 인플레 국면마다 하급지 정비사업이 줄줄이 멈추고, 사업성 회복도 그만큼 늦어지는 이유다.'},

  {q:'분양가가 전국적으로 <b>10%씩</b> 똑같이 올랐다. 평당 5,000만원 상급지는 <b>+500</b>, 평당 2,000만원 외곽은 <b>+200</b>. 재건축 사업성 개선 폭은?',
   opts:['같은 10%니 비슷하다','상급지가 훨씬 크다'],
   answer:1,
   exp:'사업성은 퍼센트가 아니라 (분양가 − 공사비) <b>절대액</b>으로 움직인다. 공사비는 그대로인데 마진이 +500 vs +200 — 상급지의 개선 폭이 2.5배다. 여기에 용적률 배수와 대지지분이 다시 곱해지니 격차는 더 벌어진다. 같은 상승률이라도 비싼 동네의 재건축이 먼저 굴러가는 구조적 이유.'},

  {q:'개발 전 평당 <b>4,000만원</b> → 개발 후 평당 <b>6,000만원</b>. 계산상 사업성은 충분한데, 시장 전체가 <b>하락장 초입</b>에 들어섰다. 판단은?',
   opts:['계산이 좋으니 진행해도 된다','사이클이 우선 — 계산은 다시 해야 한다'],
   m:1, k:1, answer:1,
   exp:'개발 후 가치는 <b>미래의 분양가</b>를 가정한 숫자다. 하락장에선 그 가정 자체가 무너진다 — 분양가가 내려앉으면 (분양가 − 공사비) 마진이 용적률 배수로 증폭되며 사업성이 통째로 뒤집힌다. <b>사업성 계산은 시장 사이클 판단을 대신하지 못한다.</b> 순서는 언제나 시장 먼저, 물건은 그다음이다.'},

  {q:'사업성 공식에 넣는 <b>분양가</b>는 어느 시점의 가격이어야 할까?',
   opts:['지금 주변 신축 시세','수년 뒤 실제 분양 시점의 가격'],
   m:1, answer:1,
   exp:'분양은 빨라야 수년 뒤다. 오늘 시세는 <b>출발점</b>일 뿐, 실제 사업성은 분양 시점의 가격이 결정한다. 그래서 같은 계산도 상승기엔 실제보다 박하게, 하락기엔 후하게 나온다. 오늘 숫자로 나온 사업성을 확정 수익처럼 믿으면 안 되는 이유다.'},

  {q:'조합설립부터 입주까지 정비사업은 보통 <b>10년 안팎</b>. 사이클이 <b>5년</b>인 지방에서 상승기 한복판에 재건축을 샀다면?',
   opts:['입주 시점엔 하락기일 수 있다','상승기에 샀으니 입주 때도 상승기다'],
   m:1, answer:0,
   exp:'10년이면 지방 사이클(약 5년)이 <b>한 바퀴를 돌고도 남는다</b>. 사업성 계산엔 이 시간이 들어있지 않다. 정비사업 투자는 물건의 사업성만이 아니라 <b>입주 시점이 사이클의 어디쯤일지</b>까지 계산에 넣어야 한다 — 특히 사이클이 짧은 지방에서는 <b>사업 진행이 빠른 곳</b>을 골라야 한다.'},

  {q:'계산상 사업성은 넉넉하다. 그런데 입주 예정 시점에 <b>인근 대규모 입주물량</b>이 겹친다. 어떻게 봐야 할까?',
   opts:['사업성이 좋으니 문제없다','물량이 분양가·전세가를 눌러 계산이 어긋날 수 있다'],
   m:1, answer:1,
   exp:'공급이 몰리면 전세가가 먼저 밀리고 분양가도 따라 눌린다. 공식의 (분양가 − 공사비) 마진이 얇아지며 사업성이 훼손된다. <b>물량 앞에 장사 없다</b> — 개별 단지 계산 전에 그 지역의 입주물량부터 확인하는 게 순서다.'},

  {q:'재개발 구역의 대지면적 <b>50,000㎡</b>, 용적률 <b>200%</b>. 30평형 기준 총세대수는 대략?',
   opts:['약 1,000세대','약 3,000세대'],
   answer:0,
   exp:'대지면적 × 용적률 = 총 분양면적 <b>100,000㎡</b>. 30평 ≈ 100㎡이니 <b>뒷자리 00만 지우면 약 1,000세대</b>다. 옛 재개발의 표준 평형 구성 2:6:2(대·중·소)의 가중평균이 딱 30평이라 성립하는 근사 — 설계도 없이 30초면 구역의 규모가 손에 잡힌다.'},

  {q:'총세대수 약 <b>3,000</b>으로 계산된 구역, 조합원이 <b>2,700명</b>이다. 먼저 봐야 할 숫자는?',
   opts:['총 3,000세대 — 대단지라 좋다','일반분양 300세대뿐 — 위험하다'],
   answer:1,
   exp:'조합원 2,700 대 일반분양 300(9:1)이면 <b>분담금이 무거워</b> 사업이 서기 어렵다. 실제로 조합원 1,800에 총세대 1,850 — 일반분양이 50뿐이라 사업이 못 가는 구역도 있다. 총세대수보다 <b>누구 몫이냐</b>가 먼저다. 다만 "수익은 일반분양에서만 나온다"고 보면 계산이 틀어진다 — <b>조합원 몫도 구축에서 신축이 되며 값이 오르고</b>, 그것 역시 엄연한 수익이다. 그래서 일반분양이 거의 없는 1:1 재건축도 사업성이 나올 수 있다.'},

  {q:'대지지분 <b>6평</b>짜리 빌라만 모인 구역. 용적률 300%를 받아도 1인당 분양면적은 <b>18평</b>. 상승장에서 가격이 오를까?',
   opts:['사업성이 없으니 안 오른다','상승장 후반엔 오른다 — 다만 리스크가 매우 높다'],
   m:1, answer:1,
   exp:'1인당 18평이면 조합원이 살 집으로도 빠듯해 <b>일반분양이 거의 없다</b>. 일반분양이 없어도 <b>구축과 신축의 평당 가격차가 공사비보다 크면</b> 사업은 성립하지만, 그건 아주 비싼 동네에서나 가능해 이런 구역 대부분은 사업성이 나오지 않는다. 그런데 상승장 후반이 되면 이런 구역까지 돈이 돌아 가격은 <b>오르긴 오른다</b>. 문제는 그 상승을 받쳐줄 펀더멘털이 없다는 것 — 장이 꺾이면 가장 먼저·가장 깊게 빠진다. <b>오르는 것과 안전한 것은 다르다.</b> 용적률보다 대지지분이 먼저다.'},
    ],
    grade:s=>{
      if(s>=9)return{lv:'LV5',g:'사업성이 한눈에 보이는 선수',d:'공식이 완전히 손에 붙었습니다. 매물 정보만 보면 사업성이 바로 나오는 단계 — 이제 임장 가서 대지지분부터 물어보세요.',emoji:'🏗️'};
      if(s>=7)return{lv:'LV4',g:'눈대중 견적이 되는 예비 조합원',d:'큰 틀은 정확합니다. 공사비 인상이 용적률 배수로 증폭되는 것 같은 디테일까지 다듬으면 완성.',emoji:'📐'};
      if(s>=5)return{lv:'LV3',g:'공식은 아는데 손이 느린 단계',d:'개발 전·후 비교의 뼈대는 잡았습니다. 재도전하며 숫자를 몇 번 굴려보면 손이 빨라집니다.',emoji:'✏️'};
      if(s>=3)return{lv:'LV2',g:'분담금 고지서에 놀랄 단계',d:'용적률과 공사비가 어디에 곱해지는지부터 다시. 해설을 정독하며 한 번 더 풀어보세요.',emoji:'📮'};
      return{lv:'LV1',g:'묻지마 재건축 매수 직전',d:'"낡으면 오른다"는 절반만 맞는 말. 개발 전·후 가치 비교부터 시작하면 헛돈 쓸 일이 없어집니다.',emoji:'🚧'};
    }
  }
};

/* 문항 풀에서 매 회차 10개를 뽑는다.
   시드를 주면 같은 문항·같은 순서가 재현된다 → 친구 대결은 동일 시험지로 겨룬다.
   시드를 생략하면 새 시드를 뽑는다 → 재도전할 때마다 문제가 달라진다. */
const QUIZ_LEN=10;
let curSeed=0;
function mulberry32(a){
  return function(){
    a=a+0x6D2B79F5|0;
    let t=Math.imul(a^a>>>15,1|a);
    t=t+Math.imul(t^t>>>7,61|t)^t;
    return ((t^t>>>14)>>>0)/4294967296;
  };
}
function drawQuiz(setKey,seed){
  curSeed=(seed==null)?(Math.floor(Math.random()*4294967296)>>>0):(seed>>>0);
  const rnd=mulberry32(curSeed);
  /* 보기 순서도 시드로 섞는다(2026-09-15 점검 후속 ⑧). 원본은 정답이 첫 보기에 몰려 있어(재건축 17문항 중 9)
     위치로 답이 보였다. ⚠️ 문항 선택과 **다른 난수열**을 쓴다 — 같은 rnd 를 이어 쓰면 옛 대결 링크(시드)가
     다른 문항을 뽑는다. 같은 시드면 이어 풀기·대결 상대도 같은 보기 순서를 본다. */
  const ornd=mulberry32((curSeed^0x9E3779B9)>>>0);
  /* O/X 문항은 섞지 않는다 — 관례대로 O 가 왼쪽. 원본 12문항 중 6개가 ['X','O'] 라 "X | O" 로 나갔다
     (2026-09-18 오딧 5번). 정답이 O 인 문항과 X 인 문항이 섞여 있어 위치가 답을 알려주지 않는다.
     난수는 한 번 소비해 뒤 문항의 보기 순서(이미 보낸 대결 링크)를 그대로 둔다. */
  const isOX=it=>it.opts.length===2&&it.opts.every(o=>o==='O'||o==='X');
  const shuffleOpts=items=>items.map(it=>{
    const idx=it.opts.map((_,i)=>i);
    if(isOX(it)){ ornd(); if(it.opts[0]!=='O')idx.reverse(); }
    else for(let i=idx.length-1;i>0;i--){const j=Math.floor(ornd()*(i+1));const t=idx[i];idx[i]=idx[j];idx[j]=t;}
    return Object.assign({},it,{opts:idx.map(i=>it.opts[i]),answer:idx.indexOf(it.answer)});
  });
  const shuf=a=>{for(let i=a.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));const t=a[i];a[i]=a[j];a[j]=t;}return a;};
  const pool=shuf(QUIZSETS[setKey].Q.slice());
  const n=Math.min(QUIZ_LEN,pool.length);
  const key=pool.find(x=>x.k), mkt=pool.filter(x=>x.m&&!x.k), rest=pool.filter(x=>!x.m);
  if(!key||mkt.length<2||rest.length<n-3)
    return shuffleOpts(pool.slice(0,n));
  /* 시장·계산의 한계 문항(m:1)은 매회 3개 보장 — 공식 문제만 10개 나오는 시험지를 차단.
     그중 핵심 문항(k:1, 사이클이 계산에 우선)은 매회 고정 출제 + 1~3번 고정 배치. */
  const pick=shuf(rest.slice(0,n-3).concat(mkt.slice(0,2)));
  pick.splice(Math.floor(rnd()*3),0,key);
  return shuffleOpts(pick);
}
let curSet='investor', QUIZ=drawQuiz('investor'), qIdx=0, qScore=0, qAnswered=false, qResults=[];
/* 진행 저장(2026-09-15 점검 후속 ③). 인앱 브라우저는 새로고침·뒤로 가기가 잦은데 그때마다
   처음부터 다시 풀게 해 이탈로 끝났다. 세트·시드·문항 번호·응답만 sessionStorage에 둔다 —
   시드가 같으면 같은 시험지가 재현된다(drawQuiz). 탭을 닫으면 사라지는 화면 상태다.
   ⚠️ 인앱 브라우저·사생활 보호 모드에서 저장소 접근이 예외를 던질 수 있어 전부 try로 감싼다. */
const QSAVE='agong_quiz', QDONE='agong_quiz_done';
let qChoices=[], qReplay=false;
function qSave(){try{sessionStorage.setItem(QSAVE,JSON.stringify({set:curSet,seed:curSeed,idx:qIdx,ch:qChoices}));}catch(e){}}
function qLoad(){try{return JSON.parse(sessionStorage.getItem(QSAVE)||'null');}catch(e){return null;}}
function qClear(){try{sessionStorage.removeItem(QSAVE);}catch(e){}}
function qDone(set){try{return (sessionStorage.getItem(QDONE)||'').split(',').indexOf(set)>=0;}catch(e){return false;}}
function qMarkDone(set){try{if(!qDone(set))sessionStorage.setItem(QDONE,((sessionStorage.getItem(QDONE)||'')+','+set).replace(/^,/,''));}catch(e){}}
function startQuiz(setKey,seed,fromHash){
  if(setKey){curSet=setKey;}
  /* 뒤로가기가 테스트 목록으로 돌아오려면 여기서 한 칸을 쌓아야 한다.
     해시로 들어온 경우(fromHash)는 이미 그 상태에 있으므로 쌓지 않는다. */
  if(!fromHash&&curSet){
    const want='#test-'+curSet;
    if(location.hash!==want)history.pushState(null,'',want);
  }
  /* 이어 풀기 — 같은 세트의 저장이 있고, 시드를 따로 받지 않았거나(해시·탭 진입) 같은 시드(대결
     링크 새로고침)일 때만. 다시 풀기·재도전은 결과 화면에서 저장을 지운 뒤라 여기 걸리지 않는다.
     ⚠️ 한 문항도 답하지 않은 저장은 이어 풀기가 아니다 — 해시로 열기만 해도 빈 저장이 생겨,
     그걸 resume 으로 세면 옛 quiz_start 처럼 수치가 부푼다(2026-09-15 브라우저 확인에서 발견). */
  const sv=qLoad();
  const resume=!!(sv&&sv.set===curSet&&Array.isArray(sv.ch)&&sv.ch.length>0&&Number.isInteger(sv.idx)&&
    sv.idx>=0&&sv.idx<QUIZ_LEN&&(seed==null||(seed>>>0)===sv.seed));
  QUIZ=drawQuiz(curSet,resume?sv.seed:seed);
  qIdx=0;qScore=0;qResults=[];qChoices=[];
  /* start_type: new(처음)·retry(이 탭에서 이미 끝낸 세트를 다시)·resume(이어 풀기).
     예전엔 새로고침·다시 풀기도 전부 시작으로 잡혀 이탈률이 부풀어 보였다. */
  track('quiz_start',{quiz_type:curSet,start_type:resume?'resume':(qDone(curSet)?'retry':'new')});
  document.getElementById('quiz-intro').style.display='none';
  document.getElementById('quiz-result').style.display='none';
  document.getElementById('quiz-play').style.display='';
  renderChalBar();
  if(resume){
    qReplay=true;
    const okChoice=(c,i)=>Number.isInteger(c)&&i<QUIZ.length&&c>=0&&c<QUIZ[i].opts.length;
    for(let i=0;i<sv.idx;i++){
      if(!okChoice(sv.ch[i],i))break;
      qChoices[i]=sv.ch[i];
      const ok=sv.ch[i]===QUIZ[i].answer;
      if(ok)qScore++;
      qResults.push(ok);
      qIdx=i+1;
    }
    renderQ();
    if(qIdx===sv.idx&&okChoice(sv.ch[qIdx],qIdx))answerQ(sv.ch[qIdx]);
    qReplay=false;
  }else{
    renderQ();
  }
  qSave();
}
function backToPick(fromHash){
  /* 풀던 중이면 확인을 받는다(점검 후속 ③) — 버튼 한 번에 진행이 사라졌다.
     뒤로 가기(fromHash)는 묻지 않고 저장도 남긴다: 앞으로 가기·재진입에서 이어 풀게 한다. */
  const playing=document.getElementById('quiz-play').style.display!=='none'&&(qIdx>0||qAnswered);
  if(!fromHash&&playing&&!confirm('테스트를 그만둘까요? 지금까지 푼 문항은 사라집니다.'))return;
  if(!fromHash)qClear();
  document.getElementById('quiz-play').style.display='none';
  document.getElementById('quiz-result').style.display='none';
  document.getElementById('quiz-intro').style.display='';
  window.scrollTo(0,0);
  if(!fromHash&&location.hash!=='#test')history.pushState(null,'','#test');
}
function renderQ(){
  qAnswered=false;
  const item=QUIZ[qIdx];
  document.getElementById('qbar').style.width=((qIdx)/QUIZ.length*100)+'%';
  document.getElementById('qcount').textContent=`${QUIZSETS[curSet].title} · ${qIdx+1} / ${QUIZ.length}`;
  const card=document.getElementById('qcard');
  card.innerHTML=`
    <button class="qback" onclick="backToPick()">← 테스트 선택</button>
    <div class="qq">${item.q}</div>
    <div class="qopts qopts-lr">${item.opts.map((o,i)=>
      `<button class="qopt" onclick="answerQ(${i})">${o}</button>`).join('')}</div>
    <div class="qexp" id="qexp"></div>
    <button class="qnext" id="qnext" onclick="nextQ()">${qIdx===QUIZ.length-1?'결과 보기 →':'다음 문제 →'}</button>`;
}
function answerQ(choice){
  if(qAnswered)return; qAnswered=true;
  const item=QUIZ[qIdx];
  const opts=document.querySelectorAll('.qopt');
  const correct=item.answer;
  if(choice===correct)qScore++;
  qResults.push(choice===correct);
  qChoices[qIdx]=choice;
  opts.forEach((o,i)=>{
    o.style.pointerEvents='none';
    if(i===correct){o.classList.add('correct');o.innerHTML+='<span class="mark">○</span>';}
    else if(i===choice){o.classList.add('wrong');o.innerHTML+='<span class="mark">✕</span>';}
    else o.classList.add('dim');
  });
  const exp=document.getElementById('qexp');
  const ok=choice===correct;
  exp.innerHTML=`<div class="ehead ${ok?'o':'x'}">${ok?'○ 정답!':'✕ 아쉬워요'}</div><p>${item.exp}</p>`+
    (item.asof?`<p class="qasof">제도 기준일 ${item.asof.replace(/-/g,'.')} · 이후 바뀌었을 수 있습니다</p>`:'');
  exp.classList.add('show');
  document.getElementById('qnext').classList.add('show');
  qSave();
  if(qReplay)return;   // 이어 풀기 복원 중에는 측정·스크롤을 하지 않는다
  track('quiz_answer',{quiz_type:curSet,idx:qIdx+1,correct:ok});
  setTimeout(()=>{document.getElementById('qnext').scrollIntoView({behavior:scrollBehavior(),block:'center'});},150);
}
function nextQ(){
  qIdx++;
  if(qIdx>=QUIZ.length){showResult();return;}
  renderQ();
  qSave();
  window.scrollTo(0,0);
}
function gradeOf(s){return QUIZSETS[curSet].grade(s);}
function nextStepHTML(){
  if(curSet==='beginner'){
    return `<div class="nextstep">
      <div class="ns-kicker">다음 단계</div>
      <div class="ns-title">기초는 됐다. 이제 통념을 뒤집을 차례</div>
      <p class="ns-desc">투자자 테스트는 <b>호재를 악재로, 악재를 호재로</b> 읽어야 풀린다. 규제·금리·수급의 진짜 게임을 확인해보자.</p>
      <a class="ns-btn" href="/#score" onclick="track('next_step',{from:'beginner',to:'map'});tbView('map')">🗺️ 우리 지역 공급, 지도에서 확인하기 →</a>
      <button class="ns-btn ghost" onclick="track('next_step',{from:'beginner',to:'investor'});goQuiz('investor')">🦅 투자자 테스트 도전하기</button>
      <a class="ns-btn ghost" href="/cycle/" onclick="track('next_step',{from:'beginner',to:'report'})">📑 아파트 사이클 리포트 읽기</a>
    </div>`;
  }
  if(curSet==='calc'){
    return `<div class="nextstep">
      <div class="ns-kicker">다음 단계</div>
      <div class="ns-title">계산보다 먼저 볼 것은 시장이다</div>
      <p class="ns-desc">공식이 손에 익었다면, 이제 그 계산을 통째로 뒤집을 수 있는 변수를 보자. <b>입주물량과 사이클</b> — 사업성 판단의 순서는 언제나 시장이 먼저다.</p>
      <a class="ns-btn" href="/#score" onclick="track('next_step',{from:'calc',to:'map'});tbView('map')">🗺️ 우리 지역 공급, 지도에서 확인하기 →</a>
      <button class="ns-btn ghost" onclick="track('next_step',{from:'calc',to:'adv'});goStats('adv')">📈 투자지표에서 입주물량·인허가 확인</button>
      <a class="ns-btn ghost" href="/cycle/" onclick="track('next_step',{from:'calc',to:'report'})">📑 아파트 사이클 리포트 읽기</a>
    </div>`;
  }
  return `<div class="nextstep">
    <div class="ns-kicker">다음 단계</div>
    <div class="ns-title">이 문제들, 감으로 낸 게 아니다</div>
    <p class="ns-desc">10문항은 <b>아파트 사이클</b>의 고리에서 나왔다. 전세가 왜 먼저 오르는지, 서울은 왜 집값이 올라도 공급이 안 늘어나는지 이어서 읽어 보자.</p>
    <a class="ns-btn" href="/#score" onclick="track('next_step',{from:'investor',to:'map'});tbView('map')">🗺️ 우리 지역 공급, 지도에서 확인하기 →</a>
    <a class="ns-btn ghost" href="/cycle/" onclick="track('next_step',{from:'investor',to:'report'})">📑 아파트 사이클 리포트 읽기</a>
    <button class="ns-btn ghost" onclick="track('next_step',{from:'investor',to:'stats'});showView('stats')">📊 국가기관 원자료 직접 보기</button>
  </div>`;
}
/* 결과 화면에서 정오 점을 누르면 그 문항을 다시 본다(2026-09-15 점검 후속 ⑧). 틀린 문항을 되짚을 길이 없었다. */
function dotExpHTML(i){
  const it=QUIZ[i]; if(!it)return '';
  const mine=qChoices[i], ok=mine===it.answer;
  return `<div class="rx-head ${ok?'o':'x'}">${i+1}번 · ${ok?'○ 정답':'✕ 오답'}</div><div class="rx-q">${it.q}</div>`+
    (mine!=null&&!ok?`<div class="rx-mine">내 답: ${it.opts[mine]}</div>`:'')+
    `<div class="rx-ans">정답: ${it.opts[it.answer]}</div><p>${it.exp}</p>`;
}
function showDotExp(i){
  const box=document.getElementById('rc-exp'); if(!box)return;
  const same=!box.hidden&&box.dataset.i===String(i);
  document.querySelectorAll('.rc-dot').forEach((d,j)=>d.setAttribute('aria-expanded',String(!same&&j===i)));
  if(same){box.hidden=true;return;}
  box.dataset.i=String(i); box.innerHTML=dotExpHTML(i); box.hidden=false;
  track('quiz_review',{quiz_type:curSet,idx:i+1});
}
function showResult(){
  track('quiz_complete',{quiz_type:curSet,score:qScore});
  qClear();qMarkDone(curSet);
  loadKakao().catch(()=>{});   // 결과 화면에 공유 버튼이 뜬다 — 누르기 전에 받아 둔다
  if(CHALLENGE&&CHALLENGE.set===curSet){
    track('challenge_result',{quiz_type:curSet,score:qScore,friend_score:CHALLENGE.score,
      outcome:qScore>CHALLENGE.score?'win':(qScore<CHALLENGE.score?'lose':'draw')});
  }
  document.getElementById('qbar').style.width='100%';
  document.getElementById('quiz-play').style.display='none';
  const r=document.getElementById('quiz-result');
  r.style.display='';
  const gr=gradeOf(qScore);
  const dots=qResults.map((ok,i)=>`<button type="button" class="rc-dot ${ok?'ok':'no'}" aria-expanded="false" aria-label="${i+1}번 ${ok?'정답':'오답'}, 해설 보기" onclick="showDotExp(${i})"></button>`).join('');
  r.innerHTML=`
    <div class="qresult">
      ${versusHTML()}
      
      <div class="rcard">
        <div class="rc-head">${QUIZSETS[curSet].title}</div>
        <div class="rc-emoji">${gr.emoji}</div>
        <div class="rc-score">${qScore}<small>/${QUIZ.length}</small></div>
        <div class="rc-dots rc-dots-btn">${dots}</div>
        <div class="rc-hint">점을 누르면 그 문항 해설이 열립니다</div>
        <div><span class="rc-lv">${gr.lv}</span></div>
        <div class="rc-grade">${gr.g}</div>
        <div class="rc-desc">${gr.d}</div>
        <div class="rc-foot">agongmap.co.kr · 아공맵</div>
      </div>
      <div class="rc-exp" id="rc-exp" hidden></div>
      <div class="qshare-box">
        <h4>${CHALLENGE&&CHALLENGE.set===curSet?'친구에게 되받아치기 🔥':'친구는 몇 점일까? 🔥'}</h4>
        <div class="qshare-btns">
          <button class="qshare-btn primary" onclick="shareResult()"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#191919" d="M12 3C6.48 3 2 6.54 2 10.9c0 2.8 1.86 5.26 4.66 6.66-.15.52-.97 3.36-1 3.58 0 0-.02.17.09.24.11.07.24.02.24.02.32-.04 3.66-2.4 4.24-2.81.57.08 1.16.13 1.77.13 5.52 0 10-3.54 10-7.9S17.52 3 12 3z"/></svg>카카오톡으로 공유하기</button>
        </div>
      </div>
      ${nextStepHTML()}
      <button class="qretry" onclick="startQuiz()">다시 풀기</button>
      <button class="qback" style="display:block;margin:14px auto 0" onclick="backToPick()">← 다른 테스트 풀어보기</button>
    </div>`;
  window.scrollTo(0,0);
}
/* ===== 친구 대결 (서버 없이 URL 파라미터로) ===== */
let CHALLENGE=null;
function readChallenge(){
  try{
    const p=new URLSearchParams(location.search);
    const sc=parseInt(p.get('c'),10), st=p.get('s'), sq=p.get('q');
    if(!Number.isInteger(sc)||sc<0||sc>QUIZ_LEN)return null;   // 상한은 문항 수에서(리뷰 15번)
    if(st!=='beginner'&&st!=='investor'&&st!=='calc')return null;
    let seed=null;
    if(sq&&/^[0-9a-z]{1,7}$/.test(sq)){
      const v=parseInt(sq,36);
      if(Number.isInteger(v)&&v>=0&&v<=4294967295)seed=v;
    }
    return{score:sc,set:st,seed:seed};
  }catch(e){}
  return null;
}
/* 같은 대결 링크를 이 탭에서 처음 여는가. 새로고침·이어 풀기로 다시 열 때마다 challenge_accepted 가
   다시 찍혀 수락 수가 부풀었다(리뷰 15번). 저장소가 막힌 브라우저에서는 매번 처음으로 본다 — 빠뜨리는 쪽보다 낫다. */
function challengeFirstSeen(ch){
  const key=ch.set+':'+ch.score+':'+(ch.seed==null?'':ch.seed);
  try{
    if(sessionStorage.getItem('agong_chal_seen')===key)return false;
    sessionStorage.setItem('agong_chal_seen',key);
  }catch(e){}
  return true;
}
/* 대결 링크로 부팅했을 때(home-app.js boot 가 chalInURL 로 모양을 보고 퀴즈 화면을 띄운 뒤 부른다). 값이 틀린 링크
   (점수 상한 초과 등)는 대결이 아니므로 평소 라우팅으로 돌려보낸다. 수락 이벤트는 같은 링크를 이 탭에서 처음 열 때 한 번. */
function bootChallenge(){
  CHALLENGE=readChallenge();
  if(!CHALLENGE){applyHash();return;}
  if(challengeFirstSeen(CHALLENGE))track('challenge_accepted',{quiz_type:CHALLENGE.set,friend_score:CHALLENGE.score,
    same_paper:CHALLENGE.seed!=null});
  startQuiz(CHALLENGE.set,CHALLENGE.seed);
}
/* 세트 → 랜딩 주소. 점수별 공유 페이지(/{주소}/{점수}/, tools/make_quiz_share_pages.py)가 이 표를 읽는다.
   카카오 말고 링크 복사·밴드·문자로 보내도 미리보기에 점수가 보이게 한다(2026-09-15 점검 후속 ⑧). */
const QUIZ_SLUG={beginner:'burini-test',investor:'investor-test',calc:'redev-test'};
function challengeURL(){
  // 세트별 랜딩이 파라미터를 홈으로 넘겨준다(OG는 세트별 퀴즈 카드로 뜨게).
  // 세 랜딩 모두 ?c=&s= 대결 파라미터를 홈으로 리다이렉트하므로 라우팅은 동일하다.
  const slug=QUIZ_SLUG[curSet]||'burini-test';
  return `https://www.agongmap.co.kr/${slug}/${qScore}/?c=${qScore}&s=${curSet}&q=${curSeed.toString(36)}&utm_source=quiz_challenge&utm_medium=viral&utm_campaign=${curSet}`;
}
function renderChalBar(){
  const b=document.getElementById('chal-bar');
  if(!b)return;
  if(CHALLENGE&&CHALLENGE.set===curSet){
    b.style.display='';
    b.innerHTML=`🔥 친구가 <b>${CHALLENGE.score}점</b>으로 도전장을 보냈습니다 — 넘어보세요`;
  }else{b.style.display='none';}
}
function versusHTML(){
  if(!CHALLENGE||CHALLENGE.set!==curSet)return '';
  const mine=qScore,theirs=CHALLENGE.score,d=Math.abs(mine-theirs);
  const st=mine>theirs?'win':(mine<theirs?'lose':'draw');
  const verdict=st==='win'?`${d}점 차로 이겼습니다 🎉`
    :st==='lose'?`${d}점 차로 졌습니다 😤`:'무승부입니다 🤝';
  const cta=st==='win'
    ?'<div class="vs-next">이제 친구에게 되받아치세요 ↓</div>'
    :`<button class="vs-btn" onclick="track('challenge_retry',{quiz_type:curSet});startQuiz(curSet,CHALLENGE.seed)">다시 도전하기</button>`;
  return `<div class="versus ${st}">
      <div class="vs-head">친구의 도전</div>
      <div class="vs-row">
        <div class="vs-side"><div class="vs-lab">나</div><div class="vs-score">${mine}</div></div>
        <div class="vs-mid">VS</div>
        <div class="vs-side"><div class="vs-lab">친구</div><div class="vs-score">${theirs}</div></div>
      </div>
      <div class="vs-verdict">${verdict}</div>
      ${cta}
    </div>`;
}
function shareTaunt(s){
  if(curSet==='beginner')return BLV[Math.max(0,Math.min(10,s|0))].taunt;
  if(s>=9)return '이걸 다 맞히네… 혹시 업자세요?';
  if(s>=7)return '머릿속엔 이미 다주택자시네요';
  if(s>=5)return '감은 있어요. 계약은 아직 이르지만';
  if(s>=3)return '부동산 뉴스, 헤드라인만 보셨죠?';
  return '호재를 악재로 읽고 계시네요';
}
function shareTxt(){
  const gr=gradeOf(qScore),name=QUIZSETS[curSet].shareName;
  return `${gr.emoji} 내 점수 ${qScore}/10 — ${name}\n${shareTaunt(qScore)}\n\n내 점수 넘어봐 👇\n${challengeURL()}`;
}
function shareResult(){
  if(needKakao(shareResult))return;
  const gr=gradeOf(qScore),name=QUIZSETS[curSet].shareName;
  const url=challengeURL();
  track('share',{content_type:'quiz_result',method:kakaoReady()?'kakao':(navigator.share?'os_share':'copy'),quiz_type:curSet,score:qScore});
  track('challenge_sent',{quiz_type:curSet,score:qScore});
  if(kakaoReady()){
    try{kakaoFeed(`${gr.emoji} ${qScore}/10점 — ${name}`,
      `${shareTaunt(qScore)} · 내 점수 넘어봐`,
      `https://www.agongmap.co.kr/share/${curSet}-${qScore}.png`,
      url,'도전 받기');return;}
    catch(e){}
  }
  if(navigator.share){
    navigator.share({title:name,
      text:`${gr.emoji} 내 점수 ${qScore}/10 — ${name}. ${shareTaunt(qScore)} 넘어봐!`,
      url:url}).catch(e=>{if(e&&e.name!=='AbortError')copyText(shareTxt());});
  }else{copyText(shareTxt());}
}
