from datetime import date, datetime
from monge_crawler.fetcher import fetch_posts


def _list_page(page):
    # page 1: 대상기간 글 1건 + 공지 1건 / page 2: 전부 기간 이전(→ 중단 유발)
    if page == 1:
        return {"message": {"result": {"articleList": [
            {"articleId": 1001, "subject": "공지", "writerNickname": "m",
             "writeDateTimestamp": _ts(2025, 9, 13), "noticeYn": "Y"},
            {"articleId": 1002, "subject": "A", "writerNickname": "홍",
             "writeDateTimestamp": _ts(2025, 9, 13), "noticeYn": "N"},
        ]}}}
    return {"message": {"result": {"articleList": [
        {"articleId": 900, "subject": "old", "writerNickname": "홍",
         "writeDateTimestamp": _ts(2025, 9, 1), "noticeYn": "N"},
    ]}}}


def _ts(y, m, d):
    from datetime import timezone, timedelta
    return int(datetime(y, m, d, 12, 0, tzinfo=timezone(timedelta(hours=9))).timestamp() * 1000)


def _article(url):
    return "<div><p>본문</p><img src='https://cdn/x.jpg'></div>"


class _Resp:
    content = b"x"
    status_code = 200
    def raise_for_status(self): pass


class _Client:
    def get(self, url, headers=None): return _Resp()


def test_fetch_stops_after_period_and_excludes_notice(tmp_path):
    cfg = {"board_url": "https://cafe.naver.com/f-e/cafes/30867744/menus/43",
           "page_size": 15, "request_delay_sec": 0}
    posts, errors = fetch_posts(cfg, date(2025, 9, 12), date(2025, 9, 16),
                                list_fn=_list_page, article_fn=_article,
                                image_client=_Client(), out_dir=tmp_path)
    ids = [p.post_id for p in posts]
    assert ids == ["1002"]                 # 공지 제외, 기간 내 1건
    assert posts[0].body_text == "본문"
    assert posts[0].image_paths            # 이미지 1장 다운로드됨
