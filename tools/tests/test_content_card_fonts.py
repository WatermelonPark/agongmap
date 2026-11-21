# -*- coding: utf-8 -*-
"""카드 글꼴 글자 검사가 fontTools 없이도 도는가 — 배치에는 fontTools 가 없다(백로그 59).

배치(update-cloud)는 `pip install pytest pillow` 만 깔고 카드 생성(make_content_cards)을 게이트 앞에서 돌린다.
예전엔 그 자리에서 fontTools 가 없어 글자 검사를 통째로 건너뛰었고, 글꼴에 없는 글자가 든 두부(□) 카드가
커밋될 수 있었다(2026-11-13 전수 리뷰 잠복 결함). 지금은 번들 글꼴의 cmap 을 구워 둔 표
(tools/data/card_font_cmap.json)를 fontTools 없이 읽는다. 표가 낡지 않았는지의 대조는 fonttools 를 까는
발행 워크플로가 맡는다(여기서는 그 스텝이 있는지 글자로 본다 — 게이트에는 fonttools 가 없어 건너뜀도 실패다).
"""
import io
import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
pytest.importorskip('PIL')
import card_kit as CK  # noqa: E402
import make_content_cards as CC  # noqa: E402

CMAP_JSON = os.path.join(ROOT, 'tools', 'data', 'card_font_cmap.json')


def _cmap():
    with io.open(CMAP_JSON, encoding='utf-8') as f:
        return json.load(f)


def _absent_char(cmap):
    """표에 없는 코드포인트 하나 — 글꼴이 바뀌어도 따라간다(픽스처를 박지 않는다)."""
    for c in range(0x2F800, 0x2FA20):
        if c not in cmap:
            return chr(c)
    raise AssertionError('글꼴 표에 없는 코드포인트를 찾지 못했다 — 범위를 넓힐 것')


def test_the_baked_cmap_is_read_when_fonttools_is_missing(monkeypatch):
    """fontTools 가 없는 배치에서도 카드 글꼴에 없는 글자를 잡는다 — 번들 글꼴의 cmap 을 구워 둔 표를 대신 읽는다.

    변이(실제로 확인): _bold_cmap 의 글꼴 표 갈래를 지워 옛 '건너뛴다(빈 목록)' 로 되돌리면 이 시험이 빨개진다.
    픽스처: 번들 글꼴의 cmap JSON 과, 그 표에 없는 코드포인트 하나(표를 읽어 고른다).
    """
    bold = CK.FONT_FILES['Bold']
    cmap = set(_cmap()[bold])
    absent = _absent_char(cmap)
    monkeypatch.setitem(sys.modules, 'fontTools', None)
    assert CC._font_misses('가나다') == []
    assert CC._font_misses('가' + absent + '나') == [absent]


def test_publish_workflow_checks_the_card_font_cmap():
    """발행 워크플로가 카드 글꼴 표를 번들 글꼴과 대조한다 — 배치에는 fonttools 가 없어 이 대조를 못 하므로,
    fonttools 를 까는 워크플로가 맡는다(백로그 59). 표가 낡으면 배치의 카드 글자 검사가 옛 글꼴 기준으로 돈다.

    변이(실제로 확인): 워크플로에서 이 확인 스텝을 지우면 빨개진다.
    픽스처: 저장소의 publish-content.yml — 글자로 읽는다(러너에서만 도는 셸이라 여기서 실행할 수 없다).
    """
    p = os.path.join(ROOT, '.github', 'workflows', 'publish-content.yml')
    t = io.open(p, encoding='utf-8').read()
    check = 'python tools/make_card_font_cmap.py --check'
    assert check in t, '글꼴 표를 대조하는 스텝이 없다'
    pip = t.index('pip install --quiet pytest pillow fonttools')
    at = t.index(check)
    cards = t.index('python tools/make_content_cards.py')
    assert pip < at < cards, '글꼴 표 대조가 도구 설치 뒤, 카드 생성 앞에 있어야 한다'
