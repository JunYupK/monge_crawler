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
