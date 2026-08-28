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


def test_fetch_does_not_stop_at_all_notice_page(tmp_path):
    """Regression test: all-notice page should not halt paging.

    Scenario: page 1 has only notices, page 2 has an in-period post,
    page 3 is all old. Must collect the in-period post from page 2.
    """
    def _list_page_all_notices_then_post(page):
        if page == 1:
            # Page 1: ALL notices, no non-notice posts
            return {"message": {"result": {"articleList": [
                {"articleId": 2001, "subject": "공지1", "writerNickname": "admin",
                 "writeDateTimestamp": _ts(2025, 9, 15), "noticeYn": "Y"},
                {"articleId": 2002, "subject": "공지2", "writerNickname": "admin",
                 "writeDateTimestamp": _ts(2025, 9, 14), "noticeYn": "Y"},
            ]}}}
        elif page == 2:
            # Page 2: in-period non-notice post
            return {"message": {"result": {"articleList": [
                {"articleId": 2003, "subject": "목표글", "writerNickname": "user",
                 "writeDateTimestamp": _ts(2025, 9, 13), "noticeYn": "N"},
            ]}}}
        else:
            # Page 3+: all old posts (trigger break)
            return {"message": {"result": {"articleList": [
                {"articleId": 2004, "subject": "구글", "writerNickname": "user",
                 "writeDateTimestamp": _ts(2025, 9, 1), "noticeYn": "N"},
            ]}}}

    cfg = {"board_url": "https://cafe.naver.com/f-e/cafes/30867744/menus/43",
           "page_size": 15, "request_delay_sec": 0}
    posts, errors = fetch_posts(cfg, date(2025, 9, 12), date(2025, 9, 16),
                                list_fn=_list_page_all_notices_then_post,
                                article_fn=_article,
                                image_client=_Client(), out_dir=tmp_path)
    ids = [p.post_id for p in posts]
    # Must contain the in-period post from page 2, not stopped at all-notice page 1
    assert ids == ["2003"], f"Expected ['2003'] but got {ids}"


def test_fetch_works_with_delay_absent(tmp_path):
    """request_delay_sec omitted (defaults to 0) → happy path still works, no real sleeping."""
    cfg = {"board_url": "https://cafe.naver.com/f-e/cafes/30867744/menus/43",
           "page_size": 15}
    posts, errors = fetch_posts(cfg, date(2025, 9, 12), date(2025, 9, 16),
                                list_fn=_list_page, article_fn=_article,
                                image_client=_Client(), out_dir=tmp_path)
    ids = [p.post_id for p in posts]
    assert ids == ["1002"]
    assert errors == []


def test_fetch_terminates_when_page_param_is_ignored(tmp_path):
    """list_fn always returns the same in-period post regardless of page (page param
    ignored by the endpoint). fetch_posts must not hang and must dedupe the result."""
    def _static_page(page):
        return {"message": {"result": {"articleList": [
            {"articleId": 3001, "subject": "고정글", "writerNickname": "user",
             "writeDateTimestamp": _ts(2025, 9, 13), "noticeYn": "N"},
        ]}}}

    cfg = {"board_url": "https://cafe.naver.com/f-e/cafes/30867744/menus/43",
           "page_size": 15, "request_delay_sec": 0, "max_pages": 3}
    posts, errors = fetch_posts(cfg, date(2025, 9, 12), date(2025, 9, 16),
                                list_fn=_static_page, article_fn=_article,
                                image_client=_Client(), out_dir=tmp_path)
    ids = [p.post_id for p in posts]
    assert ids == ["3001"]


def test_fetch_handles_list_stage_failure(tmp_path):
    """list_fn raising should not crash fetch_posts; it should record a FetchError
    with stage=='list' and stop paging, returning whatever was collected so far."""
    def _list_page_raises(page):
        raise ValueError("bad JSON / wrong keys")

    cfg = {"board_url": "https://cafe.naver.com/f-e/cafes/30867744/menus/43",
           "page_size": 15, "request_delay_sec": 0}
    posts, errors = fetch_posts(cfg, date(2025, 9, 12), date(2025, 9, 16),
                                list_fn=_list_page_raises, article_fn=_article,
                                image_client=_Client(), out_dir=tmp_path)
    assert posts == []
    assert len(errors) == 1
    assert errors[0].stage == "list"
    assert "bad JSON / wrong keys" in errors[0].reason
