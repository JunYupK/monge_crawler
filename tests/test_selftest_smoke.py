from monge_crawler.selftest import run_selftest


class _Resp:
    status_code = 200
    text = "<div><p>b</p></div>"
    content = b"x"
    def json(self):
        return {"message": {"result": {"articleList": [
            {"articleId": 1, "subject": "s", "writerNickname": "n",
             "writeDateTimestamp": 1757689200000, "noticeYn": "N"}]}}}
    def raise_for_status(self): pass


def test_selftest_reports_stages():
    cfg = {"board_url": "https://cafe.naver.com/f-e/cafes/30867744/menus/43",
           "page_size": 15}
    report = run_selftest(cfg, http_get=lambda url, headers=None: _Resp())
    assert report["list"]["ok"] is True
    assert report["article"]["ok"] is True
