# -*- coding: utf-8 -*-
"""통계 시장동향의 전국 시군구 지도(drawNationMap) 글자가 화면에서 11px 아래로 내려가지 않는지 고정한다.

2026-09-18 오딧 1번이 모바일 글자 하한을 정했고 3차 작업(89d82f4)이 CSS 쪽을 11px 로 올렸지만, 이 지도는 SVG 라
남았다(백로그 24 잔여 "통계 지도 값 라벨 7~9px"). 게다가 viewBox 를 화면 폭에 맞춰 줄이므로 375px 에서는 0.88배로
그려져 실제 화면 글자는 값 7.9px·이름 6.1~7.9px 였다(2026-09-23 Chromium 실측). 12열 타일은 375px 에서 칸당
27px 라 11px 이름·값을 넣을 수 없어, 지도에 최소 폭을 주고 좁은 화면에서는 상자 안에서 옆으로 밀게 했다.

지도 함수는 브라우저 JS 라 홈 소스에서 꺼내 node 로 **실제로 돌리고**, 나온 SVG 에서
  ① 최소 폭 ÷ viewBox 폭 = 가장 작게 그려질 때의 배율, ② 각 <text> 의 font-size × 그 배율 ≥ 11px,
  ③ 이름 글자 폭(운영 글꼴 Pretendard 로 잰 값)이 타일 폭을 넘으면 textLength 로 눌러 담았는지
를 본다.

픽스처: 실제 NATION_TILE 배치(네 글자 이름 마산회원·마산합포 포함)와, 주간(매매·전세 2단)·월간(매매·전세·월세
3단) 두 모양의 값. 값은 실제 주간 폭(±0.01~±0.6%)과 같은 자릿수다.

무엇을 깨뜨리면 빨개지나(실제로 확인):
  - home-app.js 의 MAP_MIN_PX=11 을 9 로 → 최소 배율이 1.0 이 되어 ② 가 빨개진다.
  - SVG style 에서 min-width 를 빼면 → 최소 폭을 못 찾아 빨개진다.
  - 이름 글자 크기를 옛 식(nm.length>=4?7:(nm.length===3?8:9))으로 되돌리면 ② 가 빨개진다.
  - 네 글자 이름의 textLength 를 빼면 ③ 이 빨개진다.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
FLOOR_PX = 11      # app.css 첫머리 주석의 글자 하한(2026-09-18 오딧 1번)


def _func(src, name):
    """`function name(` 부터 짝이 맞는 닫는 중괄호까지."""
    a = src.find('function %s(' % name)
    assert a >= 0, '%s 를 홈 소스에서 찾지 못했다' % name
    i = src.index('{', a)
    depth = 0
    for j in range(i, len(src)):
        c = src[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[a:j + 1]
    raise AssertionError('%s 의 끝을 찾지 못했다' % name)


def _render(monthly):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    src = HS.home_source()
    tile = re.search(r'const NATION_TILE=\{.*?\};\n', src).group(0)
    fn = _func(src, 'drawNationMap')
    js = (tile +
          'var codes=NATION_TILE.t.map(function(t){return t[0]});\n'
          'var n=codes.length, vals=function(k){return codes.map(function(_,i){return ((i*37+k)%%120-60)/100})};\n'
          'var row={p:"2026-09-14",ma:vals(1),je:vals(2)}; if(%s)row.wo=vals(3);\n'
          'var S={codes:codes,rows:[row]};\n'
          'var TREND={week:{map:"m",unit:"%%"}}; function trendData(){return {sgg:S,rows:[{p:row.p}]}}\n'
          'function pv2(v){return v==null?"·":(v>0?"+":"")+v.toFixed(2)} function pvSign(v){return v==null?0:v}\n'
          'function mapColor(){return "#eee"} function mapDateChip(){return ""} function rankTables(){return ""}\n'
          'var HOST={innerHTML:"",querySelectorAll:function(){return []},querySelector:function(){return null}};\n'
          'var document={getElementById:function(){return HOST}};\n'
          '%s\n'
          'drawNationMap("week"); process.stdout.write(JSON.stringify(HOST.innerHTML));'
          % ('true' if monthly else 'false', fn))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


@pytest.mark.parametrize('monthly', [False, True], ids=['주간2단', '월간3단'])
def test_map_text_never_renders_below_the_floor(monthly):
    html = _render(monthly)
    svg = re.search(r'<svg[^>]*aria-label="전국 시군구 변동률 지도"[^>]*>', html)
    assert svg, '지도 SVG 를 찾지 못했다'
    vb_w = float(re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ', svg.group(0)).group(1))
    mw = re.search(r'min-width:([\d.]+)px', svg.group(0))
    assert mw, '지도에 최소 폭이 없다 — 좁은 화면에서 viewBox 가 줄며 글자가 %dpx 아래로 그려진다' % FLOOR_PX
    scale = float(mw.group(1)) / vb_w
    sizes = [float(x) for x in re.findall(r'<text[^>]*font-size="([\d.]+)"', html)]
    assert len(sizes) > 400, '지도 글자를 거의 찾지 못했다(%d) — 마크업이 바뀌었으면 이 시험도 고칠 것' % len(sizes)
    low = sorted({round(s * scale, 2) for s in sizes if s * scale < FLOOR_PX - 1e-6})
    assert not low, '가장 좁게 그려질 때(배율 %.3f) %dpx 아래 글자: %s' % (scale, FLOOR_PX, low)


def test_long_names_are_fitted_into_the_tile():
    ImageFont = pytest.importorskip('PIL.ImageFont')
    html = _render(False)
    tw = float(re.search(r'<g transform="translate\([^)]*\)"><rect width="([\d.]+)"', html).group(1))
    font = os.path.join(ROOT, 'tools', 'fonts', 'Pretendard-Bold.subset.ttf')   # 이름은 600 — Bold 로 넉넉하게 잰다
    over = []
    for attrs, name in re.findall(r'<text([^>]*)>([^<]+)</text>', html):
        if not re.search(r'[가-힣]', name):
            continue                                    # 값(숫자)은 5자 이내라 칸을 넘지 않는다
        fs = float(re.search(r'font-size="([\d.]+)"', attrs).group(1))
        w = ImageFont.truetype(font, 100).getlength(name) * fs / 100.0
        fitted = re.search(r'textLength="([\d.]+)"', attrs)
        if w > tw - 1 and not (fitted and float(fitted.group(1)) <= tw - 1):
            over.append('%s(%.1f > %.0f)' % (name, w, tw - 1))
    assert not over, '타일 폭을 넘는 이름(textLength 로 눌러 담을 것): %s' % sorted(set(over))
