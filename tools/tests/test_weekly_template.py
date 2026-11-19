# -*- coding: utf-8 -*-
"""/weekly/ 는 뼈대(tools/templates/weekly.html)에서 매 회차 새로 굽는다(백로그 61-D, 2026-11-19).

왜 이 시험이 있나. 예전 생성기는 지난 회차 산출물(weekly/index.html)을 다시 읽어 그 위에 고쳐 썼다. 산출물이 다음 회차의
입력이라 손 구간을 PR 로 고칠 길이 없었고(봇이 덮는다), 한 번 잘못 구운 글자가 회차마다 실려 갔다. 이제 입력은 뼈대와 데이터뿐이고,
지난 산출물에서는 해설 글 칸(WK:COLUMN — make_content_pages 가 채운다)의 내용만 옮긴다.

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - main() 이 다시 지난 산출물(PAGE)을 뼈대로 읽으면 → test_output_ignores_the_last_output
  - carry_column 을 빼면(해설 칸이 비어 나간다) → test_output_ignores_the_last_output
  - 뼈대의 데이터 자리(WK 구간·제목·설명 메타)에 지난 주 글자가 남으면 → test_skeleton_holds_no_data
픽스처: 저장소 뼈대와 실제 data.js, 그리고 tmp_path 에 쓴 '지난 산출물'(엉뚱한 글자와 해설 칸 하나를 담은 가짜).
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_weekly_page as M  # noqa: E402

SKEL = io.open(M.TEMPLATE, encoding='utf-8', newline='').read()


def test_skeleton_holds_no_data():
    for name in ('HEAD', 'ANSWER', 'SHARE', 'TABLE', 'COLUMN'):
        m = re.search(r'<!--WK:%s-->(.*?)<!--/WK:%s-->' % (name, name), SKEL, re.S)
        assert m and not m.group(1).strip(), '뼈대의 WK:%s 구간은 비어 있어야 한다(데이터는 render 가 채운다)' % name
    assert '<title></title>' in SKEL, '뼈대의 <title> 은 비어 있어야 한다'
    for attr in ('description', 'og:description', 'og:title', 'twitter:title', 'og:image', 'twitter:image'):
        m = re.search(r'<meta (?:name|property)="%s" content="([^"]*)">' % re.escape(attr), SKEL)
        assert m and m.group(1) == '', '뼈대의 %s 메타는 비어 있어야 한다' % attr


def test_output_ignores_the_last_output(tmp_path, monkeypatch):
    prev = ('<html><body>지난회차에만있던글자\n<!--WK:COLUMN-->\n<p>해설 칸 내용</p>\n<!--/WK:COLUMN-->\n'
            '</body></html>\n')
    page = tmp_path / 'index.html'
    page.write_text(prev, encoding='utf-8')
    monkeypatch.setattr(M, 'PAGE', str(page))
    M.main()
    out = page.read_text(encoding='utf-8')
    assert '지난회차에만있던글자' not in out, '지난 산출물을 뼈대로 다시 읽었다'
    assert '<p>해설 칸 내용</p>' in out, '해설 글 칸의 내용(make_content_pages 몫)이 옮겨지지 않았다'
    W, Q = M.load()
    assert out == M.carry_column(M.render(SKEL, W, Q), prev), '산출물은 뼈대 + 데이터 + 해설 칸으로만 정해져야 한다'
