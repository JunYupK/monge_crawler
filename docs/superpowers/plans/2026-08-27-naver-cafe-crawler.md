# 몽제 네이버 카페 크롤러 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> (스킬 이름에 `superpowers:` 접두사 없음 — 이 저장소는 프로젝트 스킬로 벤더링됨. `.claude/README.md` 참고.)

**Goal:** 운영자가 지정한 기간(등록일 기준)으로 지정 네이버 카페 게시판의 게시글을 수집해 본문·이미지(URL+다운로드)를 포함한 엑셀 파일로 산출하는 로컬 Python CLI를 만든다.

**Architecture:** 순수 파싱/필터/엑셀/이미지저장 로직은 네트워크 없이 픽스처 기반 TDD로 구현한다. 실제 네트워크 접근(내부 JSON API 엔드포인트·헤더·비로그인 열람 가능 여부·이미지 CDN Referer)은 미검증이므로, 파서를 "이미 받은 JSON/HTML을 입력받는 순수 함수"로 설계하고 네트워크 글루는 얇게 유지한다. 실제 엔드포인트 포착·정합은 운영자 PC에서 도는 `selftest`가 담당한다.

**Tech Stack:** Python 3.11+, `httpx`, `beautifulsoup4`+`lxml`, `openpyxl`, `PyYAML`, `argparse`, `pytest`. 브라우저 폴백(B안)은 `playwright`(선택, 후속).

**Spec:** `docs/superpowers/specs/2026-08-27-naver-cafe-crawler-design.md`

## Global Constraints

- Python **3.11+**. 표준 `datetime`/`dataclasses` 사용.
- **모든 자동화 테스트는 네트워크 없이** 통과해야 한다(픽스처 기반). 개발 환경은 egress 정책으로 `naver.com` 접근이 차단됨(403).
- 로그인/세션 기능은 **구현하지 않는다**(비로그인 수집 전제). 단 `fetcher`는 향후 쿠키 주입이 가능한 시그니처를 유지한다.
- 기간 경계: 등록일이 **`시작일 00:00:00 ~ 종료일 23:59:59.999999`** 범위(양끝 포함)에 드는 글만 수집.
- 공지·상단 고정글 제외. 게시글ID 기준 중복 제거(먼저 나온 것 유지).
- 이미지는 **URL 수집 + 파일 다운로드** 둘 다. 다운로드 실패는 글 단위로 격리하고 계속 진행.
- 산출 엑셀은 **`게시글` 시트 + `_errors` 시트** 2개.
- `output/`, `logs/` 는 런타임 산출물이며 git에 커밋하지 않는다.
- 대상 게시판 URL 예시(유사 이벤트, 실제 게시판은 미개설): `https://cafe.naver.com/f-e/cafes/30867744/menus/43`

---

## File Structure

- `requirements.txt` — 의존성 고정
- `config.yaml` — 게시판 URL, 페이지 크기, 요청 딜레이, 출력 경로
- `.gitignore` — `output/`, `logs/` 추가
- `src/monge_crawler/__init__.py`
- `src/monge_crawler/models.py` — `Post`, `FetchError` 데이터 모델
- `src/monge_crawler/config.py` — `config.yaml` 로더 + 게시판 URL 파싱(cafeId/menuId)
- `src/monge_crawler/dateutil.py` — 기간 경계 계산(순수)
- `src/monge_crawler/filter.py` — 경계 필터 + 공지 제외 + 중복 제거(순수)
- `src/monge_crawler/parser.py` — 목록 JSON → `Post[]`, 본문 HTML → (본문텍스트, 이미지URL[])(순수)
- `src/monge_crawler/image_downloader.py` — 이미지 다운로드 → 로컬 경로
- `src/monge_crawler/exporter.py` — `Post[]`+에러 → `.xlsx`
- `src/monge_crawler/fetcher.py` — 네트워크 글루(목록 순회·조기중단·본문 진입)
- `src/monge_crawler/selftest.py` — 운영자 PC용 실제 네트워크 점검
- `src/monge_crawler/cli.py` — `run` / `selftest` 진입점
- `tests/fixtures/` — 목록 JSON·본문 HTML 샘플
- `tests/test_*.py`
- `README.md`, `run.bat`, `run.command`

---

## Task 1: 프로젝트 스캐폴딩 + 데이터 모델

**Files:**
- Create: `requirements.txt`, `config.yaml`, `src/monge_crawler/__init__.py`, `src/monge_crawler/models.py`
- Modify: `.gitignore`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `Post(post_id:str, title:str, author:str, created_at:datetime, body_text:str="", image_urls:list[str]=[], image_paths:list[str]=[], url:str="", is_notice:bool=False)`
  - `FetchError(post_id:str, url:str, stage:str, reason:str, at:datetime)` — `stage ∈ {"list","article","image"}`

- [ ] **Step 1: `.gitignore`에 런타임 산출물 추가**

기존 `.gitignore` 끝에 추가:

```
output/
logs/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: `requirements.txt` 작성**

```
httpx>=0.27
beautifulsoup4>=4.12
lxml>=5.0
openpyxl>=3.1
PyYAML>=6.0
pytest>=8.0
```

- [ ] **Step 3: `config.yaml` 작성**

```yaml
# 대상 게시판 URL (개설 후 교체). 형식: https://cafe.naver.com/f-e/cafes/<cafeId>/menus/<menuId>
board_url: "https://cafe.naver.com/f-e/cafes/30867744/menus/43"
page_size: 15          # 목록 한 페이지 글 수
request_delay_sec: 0.5 # 요청 간 딜레이(예의상 rate limit)
output_dir: "output"
log_dir: "logs"
```

- [ ] **Step 4: `src/monge_crawler/__init__.py` 생성(빈 파일)**

- [ ] **Step 5: 실패 테스트 작성 — `tests/test_models.py`**

```python
from datetime import datetime
from monge_crawler.models import Post, FetchError


def test_post_defaults():
    p = Post(post_id="1", title="t", author="a", created_at=datetime(2025, 9, 12))
    assert p.body_text == ""
    assert p.image_urls == []
    assert p.image_paths == []
    assert p.is_notice is False


def test_post_lists_are_independent():
    a = Post(post_id="1", title="t", author="a", created_at=datetime(2025, 9, 12))
    b = Post(post_id="2", title="t", author="a", created_at=datetime(2025, 9, 12))
    a.image_urls.append("x")
    assert b.image_urls == []  # 기본 리스트가 공유되면 안 됨


def test_fetch_error_fields():
    e = FetchError(post_id="1", url="u", stage="image", reason="403", at=datetime(2025, 9, 12))
    assert e.stage == "image"
```

- [ ] **Step 6: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'monge_crawler.models'`

- [ ] **Step 7: `src/monge_crawler/models.py` 구현**

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Post:
    post_id: str
    title: str
    author: str
    created_at: datetime
    body_text: str = ""
    image_urls: list[str] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)
    url: str = ""
    is_notice: bool = False


@dataclass
class FetchError:
    post_id: str
    url: str
    stage: str  # "list" | "article" | "image"
    reason: str
    at: datetime
```

- [ ] **Step 8: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 9: 커밋**

```bash
git add .gitignore requirements.txt config.yaml src/monge_crawler/__init__.py src/monge_crawler/models.py tests/test_models.py
git commit -m "feat: project scaffolding and data models"
```

---

## Task 2: 기간 경계 유틸 (순수)

**Files:**
- Create: `src/monge_crawler/dateutil.py`
- Test: `tests/test_dateutil.py`

**Interfaces:**
- Consumes: (없음)
- Produces: `period_bounds(start: date, end: date) -> tuple[datetime, datetime]` — `(start 00:00:00.000000, end 23:59:59.999999)`

- [ ] **Step 1: 실패 테스트 작성 — `tests/test_dateutil.py`**

```python
from datetime import date, datetime
from monge_crawler.dateutil import period_bounds


def test_period_bounds_inclusive():
    lo, hi = period_bounds(date(2025, 9, 12), date(2025, 9, 16))
    assert lo == datetime(2025, 9, 12, 0, 0, 0, 0)
    assert hi == datetime(2025, 9, 16, 23, 59, 59, 999999)


def test_single_day():
    lo, hi = period_bounds(date(2025, 9, 12), date(2025, 9, 12))
    assert lo.date() == hi.date() == date(2025, 9, 12)
    assert hi.hour == 23 and hi.minute == 59
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_dateutil.py -v`
Expected: FAIL — module 없음

- [ ] **Step 3: `src/monge_crawler/dateutil.py` 구현**

```python
from datetime import date, datetime, time


def period_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    lo = datetime.combine(start, time.min)               # 00:00:00.000000
    hi = datetime.combine(end, time(23, 59, 59, 999999))  # 23:59:59.999999
    return lo, hi
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_dateutil.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/monge_crawler/dateutil.py tests/test_dateutil.py
git commit -m "feat: period boundary util"
```

---

## Task 3: 필터 (경계 + 공지 제외 + 중복 제거, 순수)

**Files:**
- Create: `src/monge_crawler/filter.py`
- Test: `tests/test_filter.py`

**Interfaces:**
- Consumes: `Post` (Task 1), `period_bounds` (Task 2)
- Produces: `filter_posts(posts: list[Post], start: date, end: date) -> list[Post]`
  - 등록일이 `[start 00:00:00, end 23:59:59.999999]`에 드는 글만
  - `is_notice=True` 제외
  - `post_id` 기준 중복 제거(입력 순서상 먼저 나온 것 유지)
  - 반환 순서: 입력 순서 유지

- [ ] **Step 1: 실패 테스트 작성 — `tests/test_filter.py`**

```python
from datetime import date, datetime
from monge_crawler.models import Post
from monge_crawler.filter import filter_posts


def _p(pid, dt, notice=False):
    return Post(post_id=pid, title="t", author="a", created_at=dt, is_notice=notice)


def test_boundary_inclusive_start_and_end():
    posts = [
        _p("a", datetime(2025, 9, 12, 0, 0, 0)),        # 하한 정각 포함
        _p("b", datetime(2025, 9, 16, 23, 59, 59)),     # 상한 포함
        _p("c", datetime(2025, 9, 11, 23, 59, 59)),     # 하한 직전 배제
        _p("d", datetime(2025, 9, 17, 0, 0, 0)),        # 상한 직후 배제
    ]
    out = [p.post_id for p in filter_posts(posts, date(2025, 9, 12), date(2025, 9, 16))]
    assert out == ["a", "b"]


def test_excludes_notice():
    posts = [_p("a", datetime(2025, 9, 13), notice=True), _p("b", datetime(2025, 9, 13))]
    out = [p.post_id for p in filter_posts(posts, date(2025, 9, 12), date(2025, 9, 16))]
    assert out == ["b"]


def test_dedupe_keeps_first():
    posts = [_p("a", datetime(2025, 9, 13)), _p("a", datetime(2025, 9, 14))]
    out = filter_posts(posts, date(2025, 9, 12), date(2025, 9, 16))
    assert len(out) == 1 and out[0].created_at == datetime(2025, 9, 13)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_filter.py -v`
Expected: FAIL — module 없음

- [ ] **Step 3: `src/monge_crawler/filter.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_filter.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/monge_crawler/filter.py tests/test_filter.py
git commit -m "feat: post filter (boundary, notice, dedupe)"
```

---

## Task 4: 파서 (목록 JSON + 본문 HTML, 순수)

> **정합 주의:** 아래 픽스처는 네이버 `f-e` 카페 `ArticleListV2.json`의 **대표 형태**를 가정한 것으로 **미검증**이다. Task 8(`selftest`)이 운영자 PC에서 실제 응답을 `tests/fixtures/`로 포착한 뒤, 실제 키 이름이 다르면 이 파서와 픽스처를 그에 맞춰 수정한다. 파서를 순수 함수로 두는 이유가 이 정합을 네트워크 없이 하기 위함이다.

**Files:**
- Create: `src/monge_crawler/parser.py`, `tests/fixtures/article_list.json`, `tests/fixtures/article_body.html`
- Test: `tests/test_parser.py`

**Interfaces:**
- Consumes: `Post` (Task 1)
- Produces:
  - `parse_article_list(data: dict, board_url: str) -> list[Post]` — 메타만 채움(body/image 비움). `is_notice` 판정 포함. `url`은 게시글 페이지 URL로 구성.
  - `parse_article_body(html: str) -> tuple[str, list[str]]` — (본문 텍스트, 이미지 URL 목록)

- [ ] **Step 1: 픽스처 작성 — `tests/fixtures/article_list.json`**

```json
{
  "message": {
    "result": {
      "articleList": [
        {"articleId": 1001, "subject": "공지글", "writerNickname": "관리자",
         "writeDateTimestamp": 1757602800000, "noticeYn": "Y"},
        {"articleId": 1002, "subject": "일반글 A", "writerNickname": "홍길동",
         "writeDateTimestamp": 1757689200000, "noticeYn": "N"}
      ]
    }
  }
}
```

(참고: `1757689200000` ms = 2025-09-12 KST 근방. 테스트는 timestamp→datetime 변환만 검증하고 특정 시각을 하드코딩하지 않는다.)

- [ ] **Step 2: 픽스처 작성 — `tests/fixtures/article_body.html`**

```html
<div class="article_container">
  <p>첫 문단입니다.</p>
  <p>둘째 문단.</p>
  <img src="https://cafeptthumb-phinf.pstatic.net/img1.jpg" alt="">
  <img src="https://cafeptthumb-phinf.pstatic.net/img2.png">
</div>
```

- [ ] **Step 3: 실패 테스트 작성 — `tests/test_parser.py`**

```python
import json
from pathlib import Path
from monge_crawler.parser import parse_article_list, parse_article_body

FIX = Path(__file__).parent / "fixtures"
BOARD = "https://cafe.naver.com/f-e/cafes/30867744/menus/43"


def test_parse_list_extracts_meta_and_flags_notice():
    data = json.loads((FIX / "article_list.json").read_text(encoding="utf-8"))
    posts = parse_article_list(data, BOARD)
    assert len(posts) == 2
    notice = next(p for p in posts if p.post_id == "1001")
    normal = next(p for p in posts if p.post_id == "1002")
    assert notice.is_notice is True
    assert normal.is_notice is False
    assert normal.title == "일반글 A"
    assert normal.author == "홍길동"
    assert normal.created_at.year == 2025
    assert "30867744" in normal.url and "1002" in normal.url


def test_parse_body_text_and_images():
    html = (FIX / "article_body.html").read_text(encoding="utf-8")
    text, images = parse_article_body(html)
    assert "첫 문단입니다." in text
    assert "둘째 문단." in text
    assert images == [
        "https://cafeptthumb-phinf.pstatic.net/img1.jpg",
        "https://cafeptthumb-phinf.pstatic.net/img2.png",
    ]
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_parser.py -v`
Expected: FAIL — module 없음

- [ ] **Step 5: `src/monge_crawler/parser.py` 구현**

```python
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup

KST = timezone(timedelta(hours=9))


def _cafe_id(board_url: str) -> str:
    # .../cafes/<cafeId>/menus/<menuId>
    parts = urlparse(board_url).path.strip("/").split("/")
    return parts[parts.index("cafes") + 1]


def parse_article_list(data: dict, board_url: str) -> list["object"]:
    from monge_crawler.models import Post
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
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_parser.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add src/monge_crawler/parser.py tests/fixtures/article_list.json tests/fixtures/article_body.html tests/test_parser.py
git commit -m "feat: article list/body parsers with fixtures"
```

---

## Task 5: 이미지 다운로더

**Files:**
- Create: `src/monge_crawler/image_downloader.py`
- Test: `tests/test_image_downloader.py`

**Interfaces:**
- Consumes: `FetchError` (Task 1)
- Produces: `download_images(image_urls: list[str], post_id: str, referer: str, out_dir: Path, client) -> tuple[list[str], list[FetchError]]`
  - 저장 경로: `out_dir/images/<post_id>/01.<ext>, 02.<ext> ...` (확장자는 URL에서 추출, 없으면 `.jpg`)
  - `client`는 `.get(url, headers=...)` 를 제공하는 객체(httpx.Client 호환) — 테스트에서 가짜 client 주입
  - Referer 헤더를 붙여 요청. 실패(예외/비200)는 `FetchError(stage="image")`로 수집하고 계속.
  - 반환: (저장된 로컬 경로 목록, 에러 목록)

- [ ] **Step 1: 실패 테스트 작성 — `tests/test_image_downloader.py`**

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_image_downloader.py -v`
Expected: FAIL — module 없음

- [ ] **Step 3: `src/monge_crawler/image_downloader.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_image_downloader.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/monge_crawler/image_downloader.py tests/test_image_downloader.py
git commit -m "feat: image downloader with per-image error isolation"
```

---

## Task 6: 엑셀 익스포터

**Files:**
- Create: `src/monge_crawler/exporter.py`
- Test: `tests/test_exporter.py`

**Interfaces:**
- Consumes: `Post`, `FetchError` (Task 1)
- Produces: `export(posts: list[Post], errors: list[FetchError], out_path: Path) -> Path`
  - `게시글` 시트 헤더: `번호, 게시글ID, 제목, 작성자, 등록일, 본문, 이미지 URL, 이미지 로컬경로, 게시글URL`
  - 다중 이미지: URL/경로를 `\n`(줄바꿈)으로 연결해 한 셀에
  - `_errors` 시트 헤더: `게시글ID, 게시글URL, 단계, 사유, 시각`
  - 등록일/시각은 `YYYY-MM-DD HH:MM:SS` 문자열

- [ ] **Step 1: 실패 테스트 작성 — `tests/test_exporter.py`**

```python
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook
from monge_crawler.models import Post, FetchError
from monge_crawler.exporter import export


def test_export_creates_two_sheets_with_data(tmp_path):
    posts = [Post(post_id="1002", title="일반글 A", author="홍길동",
                  created_at=datetime(2025, 9, 12, 10, 30, 0),
                  body_text="본문", image_urls=["u1", "u2"],
                  image_paths=["p1", "p2"], url="https://article/1002")]
    errors = [FetchError(post_id="1003", url="https://article/1003", stage="article",
                         reason="timeout", at=datetime(2025, 9, 12, 10, 31, 0))]
    out = export(posts, errors, tmp_path / "out.xlsx")
    assert Path(out).exists()

    wb = load_workbook(out)
    assert wb.sheetnames == ["게시글", "_errors"]

    ws = wb["게시글"]
    assert ws.cell(1, 1).value == "번호"
    assert ws.cell(2, 2).value == "1002"
    assert ws.cell(2, 5).value == "2025-09-12 10:30:00"
    assert ws.cell(2, 7).value == "u1\nu2"          # 이미지 URL
    assert ws.cell(2, 8).value == "p1\np2"          # 이미지 로컬경로

    es = wb["_errors"]
    assert es.cell(1, 1).value == "게시글ID"
    assert es.cell(2, 3).value == "article"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_exporter.py -v`
Expected: FAIL — module 없음

- [ ] **Step 3: `src/monge_crawler/exporter.py` 구현**

```python
from pathlib import Path
from openpyxl import Workbook

_FMT = "%Y-%m-%d %H:%M:%S"
_POST_HEADERS = ["번호", "게시글ID", "제목", "작성자", "등록일", "본문",
                 "이미지 URL", "이미지 로컬경로", "게시글URL"]
_ERR_HEADERS = ["게시글ID", "게시글URL", "단계", "사유", "시각"]


def export(posts, errors, out_path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    ws = wb.active
    ws.title = "게시글"
    ws.append(_POST_HEADERS)
    for i, p in enumerate(posts, start=1):
        ws.append([
            i, p.post_id, p.title, p.author,
            p.created_at.strftime(_FMT), p.body_text,
            "\n".join(p.image_urls), "\n".join(p.image_paths), p.url,
        ])

    es = wb.create_sheet("_errors")
    es.append(_ERR_HEADERS)
    for e in errors:
        es.append([e.post_id, e.url, e.stage, e.reason, e.at.strftime(_FMT)])

    wb.save(out_path)
    return out_path
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_exporter.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/monge_crawler/exporter.py tests/test_exporter.py
git commit -m "feat: xlsx exporter (posts + errors sheets)"
```

---

## Task 7: 설정 로더 + fetcher 오케스트레이션

> `fetcher`의 네트워크 경로는 개발 환경에서 실행 불가(naver 차단)하므로, **순회·조기중단·본문 진입 로직만** 가짜 client로 단위 테스트한다. 실제 엔드포인트 호출은 Task 8(`selftest`)에서 확인·정합한다.

**Files:**
- Create: `src/monge_crawler/config.py`, `src/monge_crawler/fetcher.py`
- Test: `tests/test_config.py`, `tests/test_fetcher.py`

**Interfaces:**
- Consumes: `Post`,`FetchError` (T1), `parse_article_list`,`parse_article_body` (T4), `download_images` (T5), `filter_posts` (T3)
- Produces:
  - `load_config(path) -> dict`
  - `fetch_posts(config: dict, start: date, end: date, *, list_fn, article_fn, image_client, out_dir) -> tuple[list[Post], list[FetchError]]`
    - `list_fn(page:int) -> dict` : 목록 페이지 원본 JSON 반환(주입 가능 → 네트워크 격리)
    - `article_fn(post_url:str) -> str` : 본문 HTML 반환(주입 가능)
    - 최신순 전제. 한 페이지 파싱 결과가 **모두 `start` 하한 이전**이면 순회 중단.
    - 각 페이지에서 `filter_posts`로 대상 글 선별 후 본문 진입·이미지 다운로드.

- [ ] **Step 1: 실패 테스트 작성 — `tests/test_config.py`**

```python
from pathlib import Path
from monge_crawler.config import load_config


def test_load_config(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("board_url: https://x\npage_size: 20\nrequest_delay_sec: 0\n"
                 "output_dir: output\nlog_dir: logs\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg["board_url"] == "https://x"
    assert cfg["page_size"] == 20
```

- [ ] **Step 2: 실패 테스트 작성 — `tests/test_fetcher.py`**

```python
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
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_config.py tests/test_fetcher.py -v`
Expected: FAIL — module 없음

- [ ] **Step 4: `src/monge_crawler/config.py` 구현**

```python
from pathlib import Path
import yaml


def load_config(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
```

- [ ] **Step 5: `src/monge_crawler/fetcher.py` 구현**

```python
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
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_config.py tests/test_fetcher.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add src/monge_crawler/config.py src/monge_crawler/fetcher.py tests/test_config.py tests/test_fetcher.py
git commit -m "feat: config loader and fetcher orchestration (network-injected)"
```

---

## Task 8: selftest (운영자 PC용 실제 네트워크 점검)

> 이 태스크의 산출 코드는 **개발 환경에서 실행하지 않는다**(naver 차단). 자동 테스트는 "임포트 가능 + 인자 파싱"만 검증하고, 실제 실행은 운영자 PC에서 수동으로 한다. 이 단계가 A안 성립·비로그인 열람·이미지 Referer 요구·실제 응답 키를 확정하고, 필요 시 Task 4 파서/픽스처를 정합한다.

**Files:**
- Create: `src/monge_crawler/selftest.py`
- Test: `tests/test_selftest_smoke.py`

**Interfaces:**
- Consumes: `config` (T7), `parse_article_list`,`parse_article_body` (T4)
- Produces: `run_selftest(config: dict, *, http_get) -> dict`
  - `http_get(url, headers) -> response(.json()/.text/.content/.status_code/.raise_for_status())` 주입
  - 목록 1페이지 요청 → 파싱 시도 → 글 1건 본문 요청 → 파싱 → 이미지 1장 다운로드 시도
  - 각 단계 성공/실패와 원본 일부를 담은 리포트 dict 반환. 실제 응답을 `tests/fixtures/`에 덤프하는 옵션 포함.

- [ ] **Step 1: 스모크 테스트 작성 — `tests/test_selftest_smoke.py`**

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_selftest_smoke.py -v`
Expected: FAIL — module 없음

- [ ] **Step 3: `src/monge_crawler/selftest.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_selftest_smoke.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/monge_crawler/selftest.py tests/test_selftest_smoke.py
git commit -m "feat: selftest scaffold for operator-PC network verification"
```

---

## Task 9: CLI 진입점 + 로깅 + httpx 글루

**Files:**
- Create: `src/monge_crawler/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: 전 태스크
- Produces:
  - `build_parser() -> argparse.ArgumentParser` — `run --from --to [--config]`, `selftest [--config]`
  - `parse_date(s: str) -> date` — `YYYY-MM-DD`
  - `main(argv=None) -> int`
  - 실행 시: 로그 파일 `logs/run_YYYYMMDD_HHMMSS.log`, 콘솔 요약, httpx 실제 client로 `list_fn/article_fn/http_get` 구성

- [ ] **Step 1: 실패 테스트 작성 — `tests/test_cli.py`**

```python
import pytest
from datetime import date
from monge_crawler.cli import build_parser, parse_date


def test_parse_date():
    assert parse_date("2025-09-12") == date(2025, 9, 12)


def test_run_args():
    ns = build_parser().parse_args(["run", "--from", "2025-09-12", "--to", "2025-09-16"])
    assert ns.command == "run"
    assert ns.date_from == "2025-09-12" and ns.date_to == "2025-09-16"


def test_selftest_args():
    ns = build_parser().parse_args(["selftest"])
    assert ns.command == "selftest"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `PYTHONPATH=src pytest tests/test_cli.py -v`
Expected: FAIL — module 없음

- [ ] **Step 3: `src/monge_crawler/cli.py` 구현**

```python
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
    posts, errors = fetch_posts(cfg, start, end, list_fn=list_fn,
                                article_fn=article_fn, image_client=client, out_dir=out_dir)
    out_path = Path(out_dir) / f"monge_{args.date_from}_{args.date_to}.xlsx"
    export(posts, errors, out_path)

    log.info("완료: 성공 %d건 / 실패 %d건 / 엑셀 %s / 로그 %s",
             len(posts), len(errors), out_path, log_path)
    print(f"성공 {len(posts)}건 / 실패 {len(errors)}건 / 엑셀: {out_path} / 로그: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src pytest tests/test_cli.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 전체 테스트 확인**

Run: `PYTHONPATH=src pytest -v`
Expected: 전체 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/monge_crawler/cli.py tests/test_cli.py
git commit -m "feat: CLI entrypoint with logging and httpx glue"
```

---

## Task 10: 운영자 문서 + 실행 래퍼

**Files:**
- Create: `README.md`, `run.bat`, `run.command`

**Interfaces:**
- Consumes: 전체
- Produces: (문서/스크립트만)

- [ ] **Step 1: `README.md` 작성**

다음 내용을 포함:
- 설치: `pip install -r requirements.txt`
- 첫 점검(운영자 PC): `PYTHONPATH=src python -m monge_crawler.cli selftest` — 목록/본문/이미지 접근 확인. 실패 시 실제 API 응답을 확인해 `parser.py`/픽스처 정합.
- 수집: `PYTHONPATH=src python -m monge_crawler.cli run --from 2025-09-12 --to 2025-09-16`
- 산출물 위치: `output/monge_<from>_<to>.xlsx`, `output/images/<글ID>/`, 로그 `logs/`
- **로그인 안내(현재 불필요, 향후):** 게시판이 회원 전용으로 바뀌면 로그인 세션 확보 단계가 필요. 그때 `fetcher`에 쿠키 주입.
- 스케줄 배치: Windows 작업 스케줄러 / cron 등록 예시(각 1개).

- [ ] **Step 2: `run.command`(Mac) 작성**

```bash
#!/usr/bin/env bash
cd "$(dirname "$0")"
PYTHONPATH=src python3 -m monge_crawler.cli "$@"
```

- [ ] **Step 3: `run.bat`(Windows) 작성**

```bat
@echo off
cd /d %~dp0
set PYTHONPATH=src
python -m monge_crawler.cli %*
```

- [ ] **Step 4: 실행 권한 부여 + 커밋**

```bash
chmod +x run.command
git add README.md run.bat run.command
git commit -m "docs: operator README and run wrappers"
```

---

## Self-Review

**1. Spec coverage:**
- 목록 자동수집 → T4/T7 · 본문 진입 → T4/T7 · 항목(제목/본문/이미지URL/이미지파일/작성자/등록일/ID/URL) → T1/T4/T5/T6 · 수동실행+스케줄 → T9/T10 · 엑셀(게시글+에러) → T6 · 오류로그 → T5/T7/T9 · 단일기간 경계 → T2/T3 · 비로그인(+향후 로그인 문서화) → 전반/T10 · 이미지 다운로드 → T5 · A/B안 판정·정합 → T8. 누락 없음.
- B안(Playwright) 실제 구현은 T8 결과가 "A안 불가"로 나올 때 착수하는 후속으로 둔다(스펙의 폴백 명시와 일치). 계획 범위에서는 A안 경로를 완성한다.

**2. Placeholder scan:** 코드 스텝은 실제 코드 포함. "적절한 처리" 류 없음. 미검증 API 정합은 T4/T8에 명시적 절차로 분리(플레이스홀더 아님).

**3. Type consistency:** `Post`/`FetchError` 필드, `fetch_posts`의 `list_fn/article_fn/image_client/out_dir`, `download_images` 시그니처, `export`/`load_config`/`run_selftest` 시그니처가 태스크 간 일치.
