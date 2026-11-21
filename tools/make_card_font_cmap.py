# -*- coding: utf-8 -*-
"""카드 글꼴의 글자 표(cmap)를 JSON 으로 굽고, 표가 번들 글꼴과 같은지 확인한다 — 사람이 돌린다.

왜: 배치(`update-cloud.yml`)에는 fonttools 가 없어 `make_content_cards._font_misses` 가 글자 검사를 **건너뛰었고**,
글꼴에 없는 글자가 든 두부(□) 카드가 그대로 커밋될 수 있었다(2026-11-13 전수 리뷰 잠복 결함, 백로그 59). 그래서
번들 글꼴의 cmap 을 한 번 구워 두고, fonttools 가 없는 곳은 그 표를 읽어 검사한다.

글꼴을 바꾸면 다시 돌린다.
    python tools/make_card_font_cmap.py           표를 다시 굽는다
    python tools/make_card_font_cmap.py --check   표가 번들 글꼴과 같은지만 본다(다르면 종료 1)
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import card_kit as CK  # noqa: E402

DST = os.path.join(CK.TOOLS, 'data', 'card_font_cmap.json')


def _font_cmaps():
    from fontTools.ttLib import TTFont
    out = {}
    for name in sorted(set(CK.FONT_FILES.values())):
        out[name] = sorted(TTFont(os.path.join(CK.FONT_DIR, name)).getBestCmap())
    return out


def main(argv):
    try:
        from fontTools.ttLib import TTFont  # noqa: F401
    except ImportError:
        sys.exit('fonttools 가 필요하다: pip install fonttools')
    cur = _font_cmaps()
    if '--check' in argv:
        try:
            with io.open(DST, encoding='utf-8') as f:
                baked = json.load(f)
        except (OSError, ValueError) as e:
            sys.exit('글꼴 표를 읽지 못했다: %s (%s) — make_card_font_cmap.py 로 다시 구울 것' % (DST, e))
        bad = []
        for name in sorted(cur):
            a, b = set(baked.get(name) or []), set(cur[name])
            if a != b:
                bad.append('%s: 표 %d자 / 글꼴 %d자 (차이 예 %s)'
                           % (name, len(a), len(b), [(hex(c), chr(c)) for c in sorted(b ^ a)[:5]]))
        if bad:
            sys.exit('카드 글꼴 표가 번들 글꼴과 다르다 — python tools/make_card_font_cmap.py 로 다시 구울 것:\n  '
                     + '\n  '.join(bad))
        print('ok — 카드 글꼴 표가 번들 글꼴과 같다')
        return
    io.open(DST, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(cur, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('wrote %s %s' % (DST, {k: len(v) for k, v in cur.items()}))


if __name__ == '__main__':
    main(sys.argv[1:])
