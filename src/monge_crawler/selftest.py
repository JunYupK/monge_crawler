from monge_crawler.parser import parse_article_list, parse_article_body


def run_selftest(config, *, http_get) -> dict:
    board = config["board_url"]
    report = {"list": {"ok": False}, "article": {"ok": False}, "image": {"ok": False}}

    # NOTE: 실제 엔드포인트는 운영자 PC의 첫 실행에서 확정한다. 아래 URL은 대표 형태다.
    parts = board.rstrip("/").split("/")
    cafe_id = parts[parts.index("cafes") + 1]
    menu_id = parts[parts.index("menus") + 1]
    list_url = ("https://apis.naver.com/cafe-web/cafe2/ArticleListV2.json"
                f"?search.clubid={cafe_id}&search.menuid={menu_id}"
                f"&search.page=1&search.perPage={config.get('page_size', 15)}")
    try:
        r = http_get(list_url, headers={"Referer": board})
        r.raise_for_status()
        posts = parse_article_list(r.json(), board)
        report["list"] = {"ok": True, "count": len(posts)}
    except Exception as exc:  # noqa: BLE001
        report["list"] = {"ok": False, "error": str(exc)}
        return report

    if not posts:
        return report
    try:
        ar = http_get(posts[0].url, headers={"Referer": board})
        ar.raise_for_status()
        text, images = parse_article_body(ar.text)
        report["article"] = {"ok": True, "text_len": len(text), "images": len(images)}
    except Exception as exc:  # noqa: BLE001
        report["article"] = {"ok": False, "error": str(exc)}
    return report
