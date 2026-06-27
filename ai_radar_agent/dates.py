from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import TimeWindow


def previous_complete_day(now: datetime | None = None, tz_name: str = "Asia/Shanghai") -> TimeWindow:
    tz = ZoneInfo(tz_name)
    now_local = (now or datetime.now(tz)).astimezone(tz)
    target = now_local.date() - timedelta(days=1)
    return window_for_date(target, tz_name)


def window_for_date(target: date, tz_name: str = "Asia/Shanghai") -> TimeWindow:
    tz = ZoneInfo(tz_name)
    start = datetime.combine(target, time.min, tzinfo=tz)
    end = datetime.combine(target, time.max.replace(microsecond=0), tzinfo=tz)
    return TimeWindow(target_date=target, start=start, end=end, timezone=tz_name)
