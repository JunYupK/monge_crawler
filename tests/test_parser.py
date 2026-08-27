import json
from pathlib import Path
from monge_crawler.parser import parse_article_list, parse_article_body

FIX = Path(__file__).parent / "fixtures"
BOARD = "https://cafe.naver.com/f-e/cafes/30867744/menus/43"


def test_parse_list_extracts_meta_and_flags_notice():
    data = json.loads((FIX / "article_list.json").read_text(encoding="utf-8"))
    posts = parse_article_list(data, BOARD)
    assert len(posts) == 2
    notice = next(p for p in posts if p.post_id == "1001")
    normal = next(p for p in posts if p.post_id == "1002")
    assert notice.is_notice is True
    assert normal.is_notice is False
    assert normal.title == "일반글 A"
    assert normal.author == "홍길동"
    assert normal.created_at.year == 2025
    assert "30867744" in normal.url and "1002" in normal.url


def test_parse_body_text_and_images():
    html = (FIX / "article_body.html").read_text(encoding="utf-8")
    text, images = parse_article_body(html)
    assert "첫 문단입니다." in text
    assert "둘째 문단." in text
    assert images == [
        "https://cafeptthumb-phinf.pstatic.net/img1.jpg",
        "https://cafeptthumb-phinf.pstatic.net/img2.png",
    ]
