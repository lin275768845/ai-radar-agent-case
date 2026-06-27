from datetime import datetime
from zoneinfo import ZoneInfo

from ai_radar_agent.dates import previous_complete_day, window_for_date


def test_previous_complete_day_bjt():
    now = datetime(2026, 6, 1, 2, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    window = previous_complete_day(now, "Asia/Shanghai")
    assert window.date_str == "2026-05-31"
    assert window.start.hour == 0
    assert window.end.hour == 23


def test_window_for_date():
    window = window_for_date(datetime(2026, 6, 1).date(), "Asia/Shanghai")
    assert window.display_range.startswith("2026-06-01 00:00:00")
