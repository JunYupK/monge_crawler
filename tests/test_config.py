from pathlib import Path
from monge_crawler.config import load_config


def test_load_config(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("board_url: https://x\npage_size: 20\nrequest_delay_sec: 0\n"
                 "output_dir: output\nlog_dir: logs\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg["board_url"] == "https://x"
    assert cfg["page_size"] == 20
