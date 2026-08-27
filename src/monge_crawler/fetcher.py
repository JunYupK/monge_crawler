from datetime import date
from monge_crawler.dateutil import period_bounds
from monge_crawler.filter import filter_posts
from monge_crawler.parser import parse_article_list, parse_article_body
from monge_crawler.image_downloader import download_images


def fetch_posts(config, start: date, end: date, *, list_fn, article_fn,
                image_client, out_dir):
    lo, _hi = period_bounds(start, end)
    board_url = config["board_url"]
    collected = []
    errors = []
    page = 1
    while True:
        data = list_fn(page)
        page_posts = parse_article_list(data, board_url)
        if not page_posts:
            break
        # 최신순 전제: 이 페이지 글이 전부 하한 이전이면 이후 페이지도 그러하므로 중단
        if all(p.created_at < lo for p in page_posts if not p.is_notice):
            break
        for p in filter_posts(page_posts, start, end):
            try:
                p.body_text, p.image_urls = parse_article_body(article_fn(p.url))
            except Exception as exc:  # noqa: BLE001
                from datetime import datetime
                from monge_crawler.models import FetchError
                errors.append(FetchError(p.post_id, p.url, "article", str(exc), datetime.now()))
                continue
            paths, img_errors = download_images(p.image_urls, p.post_id, p.url,
                                                out_dir, image_client)
            p.image_paths = paths
            errors.extend(img_errors)
            collected.append(p)
        page += 1
    # 페이지 경계를 넘나든 중복 대비 최종 dedupe
    return filter_posts(collected, start, end), errors
