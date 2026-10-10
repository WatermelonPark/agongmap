/* 지역 페이지 표 동작 — make_sido_pages.zone_js()가 생성한다. 직접 고치지 말 것. */
(function(){
/* 표의 기본 화면을 맨 아래(미래 분기)로 — 공급을 보러 온 사람이 매번
   28행을 내리게 하지 않는다(2026-08-11 사용자). 과거는 올리면 된다. */
document.querySelectorAll(".ztb-scroll").forEach(function(e){e.scrollTop=e.scrollHeight});
/* 안내 문구는 make_sido_pages.REFNOTE 정본을 그대로 실어 손으로 옮기지 않는다. */
var ZREFNOTE={"un": "미분양은 다 짓고도 팔리지 않아 남아 있는 집입니다(국토교통부 월간 집계). 이미 지어진 재고에 들어 있어 순위 계산에 다시 넣으면 이중계산이라, 참고로만 보여줍니다.", "pm": "인허가는 \"짓겠다\"고 허가받은 단계의 물량입니다. 착공과 같은 흐름으로 움직이지만 허가 뒤 착공하지 않는 물량이 섞여 있고 입주까지의 시차가 일정하지 않아 참고로만 봅니다. 월별 들쭉날쭉이 커서 최근 12개월 합으로 묶어 연간 적정물량과 견주고, 순위 계산에는 착공만 씁니다."};
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
function zmSwipe(){document.querySelectorAll(".zwk .mm-scroll").forEach(function(s){var c=s.nextElementSibling,h=c&&c.querySelector(".zm-swipe");if(h)h.hidden=!(s.scrollWidth>s.clientWidth+1);});}
document.querySelectorAll(".zm-seg button[data-zm]").forEach(function(b){b.addEventListener("click",function(){var k=b.getAttribute("data-zm");
document.querySelectorAll(".zm-seg button[data-zm]").forEach(function(x){var on=x===b;x.classList.toggle("on",on);x.setAttribute("aria-pressed",on?"true":"false");});
document.querySelectorAll(".zm[data-zm]").forEach(function(m){m.hidden=m.getAttribute("data-zm")!==k;});
zmSwipe();});});
zmSwipe();window.addEventListener("resize",zmSwipe);
})();
