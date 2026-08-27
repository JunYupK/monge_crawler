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
