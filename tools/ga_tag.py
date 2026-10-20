# -*- coding: utf-8 -*-
"""GA 내부 트래픽 표식의 정본(백로그 48, 2026-10-19 요청).

GA4 속성의 'Internal Traffic' 데이터 필터는 `traffic_type = internal` 인 전송을 보고서에서 뺀다. IP 규칙은 고정 IP 인 PC
만 거르고, 이동통신망 휴대폰은 IP 가 계속 바뀌어 걸러지지 않는다. 그래서 기기 쪽에 표식을 둔다:

  · `?internal=on` 으로 한 번 들어온 기기는 localStorage 에 표식(INTERNAL_KEY)을 남기고, `?internal=off` 로 지운다.
  · 모든 페이지의 `gtag('config', …)` 는 매개변수를 `gaCfg(…)` 로 감싸 부른다. 표식이 있으면 gaCfg 가 `traffic_type:'internal'`
    을 얹는다. config 매개변수는 그 태그로 나가는 page_view(자동·홈 수동)와 뒤따르는 이벤트에 함께 실린다.

표식 이름과 주소 값은 공개돼도 괜찮다(남이 쓰면 그 사람 접속이 보고서에서 빠질 뿐이다). IP 는 어디에도 적지 않는다.
`?ga_off=1`(기기 단위 전송 중단)과는 다른 장치다 — ga_off 는 아예 보내지 않고, internal 은 보내되 보고서에서 거른다.

이 조각(INTERNAL_SCRIPT)은 손 페이지에 글자 그대로 붙이고, 생성기는 이 모듈에서 읽어 굽는다. test_ga_internal 이 저장소의
모든 HTML 을 대조한다(조각이 정확히 하나, 첫 config 호출보다 앞, 모든 config 호출이 gaCfg 를 거침). 홈(index.html)은 해시 속
쿼리를 진짜 쿼리로 옮기는 ① 뒤에 둔다 — 해시 속 ?internal=on 도 먹게.
"""
import re

GA_ID = 'G-3FJNG6G1F3'
INTERNAL_KEY = 'ga_internal'
INTERNAL_PARAM = 'internal'
TRAFFIC_TYPE = 'internal'

INTERNAL_SCRIPT = (
    "<script>/* 내부 트래픽 표식(?internal=on|off) — 정본 tools/ga_tag.py */"
    "try{var _iq=new URLSearchParams(location.search).get('%(p)s');"
    "if(_iq==='on')localStorage.setItem('%(k)s','1');else if(_iq==='off')localStorage.removeItem('%(k)s');}catch(e){}"
    "function gaCfg(o){o=o||{};try{if(localStorage.getItem('%(k)s'))o.traffic_type='%(t)s';}catch(e){}return o;}</script>"
) % {'p': INTERNAL_PARAM, 'k': INTERNAL_KEY, 't': TRAFFIC_TYPE}

# gtag('config', 'G-…', <매개변수>) — 따옴표 둘 다, 띄어쓰기 자유
CONFIG_CALL = re.compile(r"""gtag\(\s*['"]config['"]\s*,\s*['"](G-[A-Z0-9]+)['"]\s*(?:,\s*([^;<]*?))?\)\s*;""")


def config_call(opts=''):
    """생성기가 굽는 config 호출 한 문장. opts 는 JS 객체 글자(예: '{send_page_view:false}')."""
    return "gtag('config','%s',gaCfg(%s));" % (GA_ID, opts)


def put(html):
    """생성 페이지 머리를 정본 모양으로 맞춘다 — 손 뼈대를 이어 쓰는 생성기(/weekly/)가 부른다.

    · INTERNAL_SCRIPT 가 없으면 gtag 로더(<script async src=…gtag/js…>) 바로 앞에 넣고, 낡은 판이면 바꾼다.
    · gaCfg 를 거치지 않는 config 호출을 config_call() 로 바꾼다.
    GA 를 싣지 않는 페이지는 그대로 돌려준다."""
    if 'googletagmanager.com/gtag/js' not in html:
        return html
    old = re.compile(r'<script>/\* 내부 트래픽 표식[^\n]*?</script>')
    if old.search(html):
        html = old.sub(lambda m: INTERNAL_SCRIPT, html, count=1)
    else:
        i = html.find('<script async src="https://www.googletagmanager.com/gtag/js')
        if i < 0:
            raise SystemExit('gtag 로더를 찾지 못해 내부 트래픽 표식을 넣을 자리가 없다')
        html = html[:i] + INTERNAL_SCRIPT + ('\r\n' if '\r\n' in html else '\n') + html[i:]

    def fix(m):
        arg = (m.group(2) or '').strip()
        if arg.startswith('gaCfg('):
            return m.group(0)
        return config_call(arg)
    return CONFIG_CALL.sub(fix, html)
