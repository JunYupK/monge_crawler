from datetime import date, datetime, time


def period_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    lo = datetime.combine(start, time.min)               # 00:00:00.000000
    hi = datetime.combine(end, time(23, 59, 59, 999999))  # 23:59:59.999999
    return lo, hi
