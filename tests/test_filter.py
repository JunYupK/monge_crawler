from datetime import date, datetime
from monge_crawler.models import Post
from monge_crawler.filter import filter_posts


def _p(pid, dt, notice=False):
    return Post(post_id=pid, title="t", author="a", created_at=dt, is_notice=notice)


def test_boundary_inclusive_start_and_end():
    posts = [
        _p("a", datetime(2025, 9, 12, 0, 0, 0)),        # 하한 정각 포함
        _p("b", datetime(2025, 9, 16, 23, 59, 59)),     # 상한 포함
        _p("c", datetime(2025, 9, 11, 23, 59, 59)),     # 하한 직전 배제
        _p("d", datetime(2025, 9, 17, 0, 0, 0)),        # 상한 직후 배제
    ]
    out = [p.post_id for p in filter_posts(posts, date(2025, 9, 12), date(2025, 9, 16))]
    assert out == ["a", "b"]


def test_excludes_notice():
    posts = [_p("a", datetime(2025, 9, 13), notice=True), _p("b", datetime(2025, 9, 13))]
    out = [p.post_id for p in filter_posts(posts, date(2025, 9, 12), date(2025, 9, 16))]
    assert out == ["b"]


def test_dedupe_keeps_first():
    posts = [_p("a", datetime(2025, 9, 13)), _p("a", datetime(2025, 9, 14))]
    out = filter_posts(posts, date(2025, 9, 12), date(2025, 9, 16))
    assert len(out) == 1 and out[0].created_at == datetime(2025, 9, 13)
