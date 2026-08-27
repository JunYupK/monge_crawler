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
