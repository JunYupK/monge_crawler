from pathlib import Path
from monge_crawler.image_downloader import download_images


class FakeResp:
    def __init__(self, content=b"", status=200):
        self.content = content
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, mapping):
        self.mapping = mapping
        self.seen_headers = []
    def get(self, url, headers=None):
        self.seen_headers.append(headers)
        return self.mapping[url]


def test_downloads_ok_and_sets_referer(tmp_path):
    urls = ["https://cdn/img1.jpg", "https://cdn/img2.png"]
    client = FakeClient({urls[0]: FakeResp(b"a"), urls[1]: FakeResp(b"b")})
    paths, errors = download_images(urls, "1002", "https://ref/article", tmp_path, client)
    assert errors == []
    assert len(paths) == 2
    assert Path(paths[0]).exists() and Path(paths[1]).exists()
    assert paths[0].endswith("01.jpg") and paths[1].endswith("02.png")
    assert all(h.get("Referer") == "https://ref/article" for h in client.seen_headers)


def test_one_image_fails_others_continue(tmp_path):
    urls = ["https://cdn/ok.jpg", "https://cdn/bad.jpg"]
    client = FakeClient({urls[0]: FakeResp(b"a"), urls[1]: FakeResp(b"", 403)})
    paths, errors = download_images(urls, "1002", "https://ref/article", tmp_path, client)
    assert len(paths) == 1
    assert len(errors) == 1 and errors[0].stage == "image"
    assert "403" in errors[0].reason
