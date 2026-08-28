from datetime import date
from monge_crawler.models import Post
from monge_crawler.dateutil import period_bounds


def filter_posts(posts: list[Post], start: date, end: date) -> list[Post]:
    lo, hi = period_bounds(start, end)
    seen: set[str] = set()
    out: list[Post] = []
    for p in posts:
        if p.is_notice:
            continue
        if not (lo <= p.created_at <= hi):
            continue
        if p.post_id in seen:
            continue
        seen.add(p.post_id)
        out.append(p)
    return out
