from datetime import datetime
from zoneinfo import ZoneInfo

from app.application.clock import EGX_TIMEZONE, egx_today


def test_egx_timezone_is_the_named_cairo_zone():
    assert EGX_TIMEZONE == ZoneInfo("Africa/Cairo")


def test_egx_today_uses_cairo_calendar_date():
    assert egx_today() == datetime.now(EGX_TIMEZONE).date()
