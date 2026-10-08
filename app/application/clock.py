from datetime import date, datetime
from zoneinfo import ZoneInfo


EGX_TIMEZONE = ZoneInfo("Africa/Cairo")


def egx_today() -> date:
    """Return the current calendar date in the Egyptian Exchange timezone."""
    return datetime.now(EGX_TIMEZONE).date()
