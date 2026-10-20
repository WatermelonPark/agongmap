# -*- coding: utf-8 -*-
"""blog_similarity 반복률 점검의 계열·실패 처리(2026-10-18 전수리뷰 BL1-10·BL1-11).

- BL1-10: 도시 입주물량 편은 지역 편과 같은 '지역별 아파트 공급' 카테고리에 실린다(2026-09-30 대표 결정). report 가
  카테고리로만 묶으면 지역 편 사이에 낀 도시 편과 견줘 지역 편끼리의 반복을 놓친다 — 같은 계열(series_of)끼리 견준다.
- BL1-11: RSS 를 못 읽으면 '반복 없음'(종료 0)이 아니라 재지 않았다고 찍고 2 를 낸다. --draft 의 카테고리 이름은 정본
  (close_published_issues.KIND_TO_CATEGORY)에서 읽는다. 초안 칸은 여는 태그 뒤부터 잘라 썸네일 자리 표시자가 분모에 들지 않는다.

픽스처: 네트워크 없이 만든 합성 발행 글(10-13 청주·10-16 대구 도시 편이 지역 편 사이에 나간 실제 순서의 모양)과 합성 초안 파일.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import blog_similarity as B  # noqa: E402
import close_published_issues as CP  # noqa: E402

ZONE = CP.KIND_TO_CATEGORY['지역 공급']
BASE = ['부산은 앞으로 3년 동안 적정물량보다 12,000세대가 모자라는 흐름입니다.',
        '부산 미분양은 분기 적정물량의 0.4배 수준이라 시장이 소화하고 있습니다.',
        '부산 착공은 지난해보다 21% 줄어 입주 공백이 더 길어질 수 있습니다.']


def _post(date, title, paras):
    return dict(date=date, cat=ZONE, title=title, paras=paras)


def _four():
    return [_post('2026-10-10', '2027년 부산 아파트 공급물량 전망, 모자랍니다', BASE),
            _post('2026-10-13', '청주 아파트 입주물량, 2027년까지', ['청주 도시 편은 문장 틀이 전혀 다른 글로 적었습니다.']),
            _post('2026-10-16', '대구 아파트 입주물량, 내년 바닥', ['대구 도시 편도 지역 편과는 다른 이야기를 하는 글입니다.']),
            _post('2026-10-21', '2027년 경남 아파트 공급물량 전망, 모자랍니다', [p.replace('부산', '경남') for p in BASE])]


def test_report_compares_zone_posts_with_zone_posts(capsys):
    """지역 편 → 도시 편 둘 → 지역 편(앞 지역 편의 이름만 바꾼 글) 순서에서 report 의 최악 반복률이 경고를 넘는다.
    변이(확인): series_of 가 카테고리만 돌려주게(도시 편 구분 삭제) 하면 경남 편을 대구 도시 편과 견줘 0% 가 되어 빨개진다."""
    worst = B.report(_four())
    assert worst > B.WARN, capsys.readouterr().out
    assert B.series_of(_four()[1]) != B.series_of(_four()[0])


def test_unreadable_rss_is_not_a_pass(monkeypatch, tmp_path, capsys):
    """RSS 를 못 읽으면(close_published_issues.fetch_posts 가 None) 기본 실행·--draft 모두 종료 2 와 '재지 않았다' 줄.
    변이(확인): fetch_posts 가 None 을 빈 목록으로 바꾸던 옛 `or []` 로 되돌리면 0 이 나와 빨개진다."""
    monkeypatch.setattr(CP, 'fetch_posts', lambda: None)
    d = tmp_path / 'd.html'
    d.write_text('<div id="b2"><p>문장 하나입니다.</p></div></div>', encoding='utf-8')
    assert B.main([]) == 2
    assert B.main(['--draft', str(d)]) == 2
    assert '재지 않았다' in capsys.readouterr().out


def test_draft_check_reads_the_canonical_category_and_skips_the_placeholder(monkeypatch, tmp_path):
    """--draft 는 정본 카테고리 이름으로 직전 지역 편을 고르고(도시 편은 건너뜀), 칸의 여는 태그 뒤부터 잘라 자리 표시자를
    세지 않는다 — 이름만 바뀐 같은 글이면 100%.
    변이(확인): cats 를 손 이름('지역별 아파트 공급')으로 되돌리면 정본 이름을 바꾼 이 픽스처에서 견줄 글이 없어 빨개지고, 자르는
    시작을 s.index('id="b2"') 로 되돌리면 첫 문단에 'id="b2">' 가 붙어 자리 표시자가 분모에 들어 빨개진다.
    픽스처: 정본 카테고리 이름을 바꾼 상태(이름 변경의 모양) + 지역 편·도시 편 발행 글 + 썸네일 자리 표시자가 맨 앞인 초안 칸."""
    renamed = '지역 아파트 공급 리포트'
    monkeypatch.setitem(CP.KIND_TO_CATEGORY, '지역 공급', renamed)
    posts = [dict(p, cat=renamed) for p in _four()[:3]]
    d = tmp_path / 'd.html'
    d.write_text('<div class="box"><div id="b2" class="copy"><p>[여기에 썸네일 이미지를 넣어 주세요 첫 이미지가 대표]</p>'
                 + ''.join('<p>%s</p>' % x.replace('부산', '경남') for x in BASE) + '</div></div>', encoding='utf-8')
    rows = B.check_draft(str(d), posts)
    assert rows and rows[0][2] == 1.0 and '부산' in rows[0][3], rows
