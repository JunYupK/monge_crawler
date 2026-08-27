from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from monge_crawler.models import FetchError


def _ext(url: str) -> str:
    name = urlparse(url).path.rsplit("/", 1)[-1]
    if "." in name:
        return "." + name.rsplit(".", 1)[-1].split("?")[0].lower()
    return ".jpg"


def download_images(image_urls, post_id, referer, out_dir, client):
    dest = Path(out_dir) / "images" / post_id
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    errors: list[FetchError] = []
    for i, url in enumerate(image_urls, start=1):
        try:
            resp = client.get(url, headers={"Referer": referer})
            resp.raise_for_status()
            fpath = dest / f"{i:02d}{_ext(url)}"
            fpath.write_bytes(resp.content)
            paths.append(str(fpath))
        except Exception as exc:  # noqa: BLE001 - 격리하고 계속
            errors.append(FetchError(post_id=post_id, url=url, stage="image",
                                     reason=str(exc), at=datetime.now()))
    return paths, errors
