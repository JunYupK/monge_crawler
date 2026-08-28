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
