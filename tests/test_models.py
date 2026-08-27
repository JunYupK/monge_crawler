from datetime import datetime
from monge_crawler.models import Post, FetchError


def test_post_defaults():
    p = Post(post_id="1", title="t", author="a", created_at=datetime(2025, 9, 12))
    assert p.body_text == ""
    assert p.image_urls == []
    assert p.image_paths == []
    assert p.is_notice is False


def test_post_lists_are_independent():
    a = Post(post_id="1", title="t", author="a", created_at=datetime(2025, 9, 12))
    b = Post(post_id="2", title="t", author="a", created_at=datetime(2025, 9, 12))
    a.image_urls.append("x")
    assert b.image_urls == []  # 기본 리스트가 공유되면 안 됨


def test_fetch_error_fields():
    e = FetchError(post_id="1", url="u", stage="image", reason="403", at=datetime(2025, 9, 12))
    assert e.stage == "image"
