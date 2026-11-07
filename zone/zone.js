/* 지역 페이지 표 동작 — make_sido_pages.zone_js()가 생성한다. 직접 고치지 말 것. */
(function(){
/* 안내 문구는 make_sido_pages.REFNOTE 정본을 그대로 실어 손으로 옮기지 않는다. */
var ZREFNOTE={"un": "미분양은 분양 후 아직 계약되지 않은 물량(공사 중 포함)입니다(국토교통부 월간 집계). 이미 착공·준공 물량에 들어 있어 순위 계산에 다시 넣으면 이중계산이라, 참고로만 보여줍니다.", "pm": "인허가는 \"짓겠다\"고 허가받은 단계의 물량입니다. 착공과 같은 흐름으로 움직이지만 허가 뒤 착공하지 않는 물량이 섞여 있고 입주까지의 시차가 일정하지 않아 참고로만 봅니다. 월별 들쭉날쭉이 커서 최근 12개월 합으로 묶어 연간 적정물량과 견주고, 순위 계산에는 착공만 씁니다."};
document.querySelectorAll(".ztb tfoot tr.zref").forEach(function(tr){
tr.addEventListener("click",function(){
var p=document.getElementById("zrefnote");if(!p)return;
var k=tr.getAttribute("data-ref");
if(!p.hidden&&p.dataset.k===k){p.hidden=true;}
else{p.dataset.k=k;p.textContent=ZREFNOTE[k]||"";p.hidden=false;
/* 탭한 행이 화면 맨 밑이면 설명이 폴드 아래 열린다(모바일) —
   nearest라 이미 보이면 안 움직인다. */
p.scrollIntoView({block:"nearest"});}
document.querySelectorAll(".ztb tfoot .rbtn").forEach(function(b){
var own=b.parentNode.parentNode.getAttribute("data-ref");
b.setAttribute("aria-expanded",(!p.hidden&&own===p.dataset.k)?"true":"false");});});});
/* 시세 지도 주간·월간(zone_map, 2026-10-10) — 단추(data-zm)와 같은 값의 묶음(.zm)만 보인다. 지도가 상자보다 넓을 때만
   '옆으로 밀어 전체 보기'를 켠다(홈 syncSwipe 와 같은 생각 — 숨은 묶음은 넓이가 0 이라 보일 때 다시 잰다). */
/* 밀어 보는 상자(분기표·지도 조각)의 가장자리 흐림 — /weekly/ 와 같은 MW.CUE_JS(2026-10-31 디자인 리뷰 2차). */
function cueBox(s){var w=s.parentNode;if(!w||!w.classList)return function(){};if(!w.classList.contains("cue")){w=document.createElement("div");w.className="cue";s.parentNode.insertBefore(w,s);w.appendChild(s);}function f(){if(!s.clientWidth)return;var r=s.scrollWidth-s.clientWidth-s.scrollLeft;w.classList.toggle("cue-r",r>2);w.classList.toggle("cue-l",s.scrollLeft>2);}s.addEventListener("scroll",f,{passive:true});window.addEventListener("resize",f);f();return f;}
var CUES=[];document.querySelectorAll(".ztb-scroll,.zwk .mm-scroll").forEach(function(s){CUES.push(cueBox(s));});
/* 표의 기본 화면을 맨 아래(미래 분기)로 — 공급을 보러 온 사람이 매번
   28행을 내리게 하지 않는다(2026-08-11 사용자). 과거는 올리면 된다.
   ⚠️ cueBox 가 상자를 .cue 로 감싼 **뒤**에 둔다 — 요소를 옮기면 scrollTop 이 0 으로 돌아가 데스크톱에서 2017~2020 행만
   보였다(2026-11-07 디자인 검수 reports-0, 10-31 회귀). */
document.querySelectorAll(".ztb-scroll").forEach(function(e){e.scrollTop=e.scrollHeight});
function zmSwipe(){document.querySelectorAll(".zwk .mm-scroll").forEach(function(s){var p=s.parentNode,n=(p&&p.classList&&p.classList.contains("cue"))?p:s,c=n.nextElementSibling,h=c&&c.querySelector(".zm-swipe");if(h)h.hidden=!(s.scrollWidth>s.clientWidth+1);});CUES.forEach(function(f){f();});}
document.querySelectorAll(".zm-seg button[data-zm]").forEach(function(b){b.addEventListener("click",function(){var k=b.getAttribute("data-zm");
document.querySelectorAll(".zm-seg button[data-zm]").forEach(function(x){var on=x===b;x.classList.toggle("on",on);x.setAttribute("aria-pressed",on?"true":"false");});
document.querySelectorAll(".zm[data-zm]").forEach(function(m){m.hidden=m.getAttribute("data-zm")!==k;});
zmSwipe();});});
zmSwipe();window.addEventListener("resize",zmSwipe);
/* 이 지역 글 — 앞 POSTS_CAP 편만 보이고 나머지는 단추로 편다(make_sido_pages.POSTS_SLOT, 2026-11-07 디자인 검수 reports-3). */
document.querySelectorAll(".zposts").forEach(function(sec){var g=sec.querySelector(".kgrid");if(!g||g.children.length<=4)return;var n=g.children.length;sec.classList.add("zp-cut");var b=document.createElement("button");b.type="button";b.className="zp-more";b.textContent="글 "+n+"편 모두 보기";b.addEventListener("click",function(){sec.classList.remove("zp-cut");b.remove();});g.parentNode.insertBefore(b,g.nextSibling);});
})();
