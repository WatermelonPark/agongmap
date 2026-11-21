# -*- coding: utf-8 -*-
"""카드 글꼴의 글자 표(cmap)를 JSON 으로 굽는다 — 사람이 돌린다.

왜: 배치(`update-cloud.yml`)에는 fonttools 가 없어 `make_content_cards._font_misses` 가 글자 검사를 **건너뛰었고**,
글꼴에 없는 글자가 든 두부(□) 카드가 그대로 커밋될 수 있었다(2026-11-13 전수 리뷰 잠복 결함, 백로그 59). 그래서
번들 글꼴의 cmap 을 한 번 구워 두고, fonttools 가 없는 곳은 그 표를 읽어 검사한다.

글꼴을 바꾸면 다시 돌린다: python tools/make_card_font_cmap.py   (fonttools 필요)
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import card_kit as CK  # noqa: E402


def main():
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        sys.exit('fonttools 가 필요하다: pip install fonttools')
    out = {}
    for name in sorted(set(CK.FONT_FILES.values())):
        path = os.path.join(CK.FONT_DIR, name)
        out[name] = sorted(TTFont(path).getBestCmap())
    dst = os.path.join(CK.TOOLS, 'data', 'card_font_cmap.json')
    io.open(dst, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('wrote %s %s' % (dst, {k: len(v) for k, v in out.items()}))


if __name__ == '__main__':
    main()
