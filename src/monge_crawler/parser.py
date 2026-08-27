from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from monge_crawler.models import Post

KST = timezone(timedelta(hours=9))


def _cafe_id(board_url: str) -> str:
    # .../cafes/<cafeId>/menus/<menuId>
    parts = urlparse(board_url).path.strip("/").split("/")
    return parts[parts.index("cafes") + 1]


def parse_article_list(data: dict, board_url: str) -> list[Post]:
    cafe_id = _cafe_id(board_url)
    articles = data["message"]["result"]["articleList"]
    posts: list[Post] = []
    for a in articles:
        ts = a["writeDateTimestamp"] / 1000
        created = datetime.fromtimestamp(ts, tz=KST).replace(tzinfo=None)
        pid = str(a["articleId"])
        posts.append(Post(
            post_id=pid,
            title=a.get("subject", ""),
            author=a.get("writerNickname", ""),
            created_at=created,
            url=f"https://cafe.naver.com/f-e/cafes/{cafe_id}/articles/{pid}",
            is_notice=(a.get("noticeYn") == "Y"),
        ))
    return posts


def parse_article_body(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator="\n", strip=True)
    images = [img["src"] for img in soup.find_all("img") if img.get("src")]
    return text, images
