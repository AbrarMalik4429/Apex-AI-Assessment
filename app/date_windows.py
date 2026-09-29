"""Calendar calculations for recurring-slot searches."""

from calendar import monthrange
from datetime import date, timedelta


def add_months(day: date, months: int) -> date:
    month_index = day.year * 12 + day.month - 1 + months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def default_window_end(start: date, today: date, horizon_days: int) -> date:
    return min(start + timedelta(days=13), today + timedelta(days=horizon_days))
