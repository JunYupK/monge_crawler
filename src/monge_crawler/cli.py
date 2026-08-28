import argparse
import logging
from datetime import date, datetime
from pathlib import Path


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="monge-crawler")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="지정 기간 수집 후 엑셀 생성")
    run.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    run.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    run.add_argument("--config", default="config.yaml")

    st = sub.add_parser("selftest", help="운영자 PC에서 실제 접근 점검")
    st.add_argument("--config", default="config.yaml")
    return parser


def _setup_logging(log_dir: str) -> Path:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(log_dir) / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"),
                  logging.StreamHandler()],
    )
    return log_path


def main(argv=None) -> int:
    import httpx
    from monge_crawler.config import load_config
    from monge_crawler.fetcher import fetch_posts
    from monge_crawler.exporter import export
    from monge_crawler.selftest import run_selftest

    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    log_path = _setup_logging(cfg.get("log_dir", "logs"))
    log = logging.getLogger("monge")

    headers = {"User-Agent": "Mozilla/5.0", "Referer": cfg["board_url"]}
    client = httpx.Client(headers=headers, timeout=30.0)

    if args.command == "selftest":
        report = run_selftest(cfg, http_get=lambda url, headers=None: client.get(url, headers=headers))
        log.info("selftest report: %s", report)
        print(report)
        return 0

    start, end = parse_date(args.date_from), parse_date(args.date_to)

    def _cafe_menu(url):
        parts = url.rstrip("/").split("/")
        return parts[parts.index("cafes") + 1], parts[parts.index("menus") + 1]

    cafe_id, menu_id = _cafe_menu(cfg["board_url"])

    def list_fn(page):
        url = ("https://apis.naver.com/cafe-web/cafe2/ArticleListV2.json"
               f"?search.clubid={cafe_id}&search.menuid={menu_id}"
               f"&search.page={page}&search.perPage={cfg.get('page_size', 15)}")
        return client.get(url).json()

    def article_fn(post_url):
        return client.get(post_url).text

    out_dir = cfg.get("output_dir", "output")
    out_path = Path(out_dir) / f"monge_{args.date_from}_{args.date_to}.xlsx"

    posts, errors = [], []
    try:
        posts, errors = fetch_posts(cfg, start, end, list_fn=list_fn,
                                    article_fn=article_fn, image_client=client, out_dir=out_dir)
    except Exception:
        log.exception("수집 중 오류 발생")
        if posts or errors:
            try:
                export(posts, errors, out_path)
                log.info("부분 결과 엑셀 저장: %s", out_path)
            except Exception:
                log.exception("부분 결과 엑셀 저장 실패")
        print(f"오류가 발생했습니다. 로그를 확인하세요: {log_path}")
        return 1

    try:
        export(posts, errors, out_path)
    except Exception:
        log.exception("엑셀 저장 중 오류 발생 (수집 %d건 / 실패 %d건)", len(posts), len(errors))
        print(f"오류가 발생했습니다. 로그를 확인하세요: {log_path}")
        return 1

    log.info("완료: 성공 %d건 / 실패 %d건 / 엑셀 %s / 로그 %s",
             len(posts), len(errors), out_path, log_path)
    print(f"성공 {len(posts)}건 / 실패 {len(errors)}건 / 엑셀: {out_path} / 로그: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
