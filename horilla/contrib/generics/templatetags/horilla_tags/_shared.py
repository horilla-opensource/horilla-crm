"""
Shared helpers for horilla_tags (no template register).
Used by datetime_filters, field_filters, display_tags, etc.
"""

# Standard library imports
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from horilla.contrib.utils.middlewares import _thread_local

# First party imports (Horilla)
from horilla.utils.jalali import format_gregorian_as_jalali, uses_jalali_calendar
from horilla.utils import timezone

# Third-party imports (Django)


def _get_request_user_company():
    """Get request, user, and company from thread-local. Used for format fallback."""
    request = getattr(_thread_local, "request", None)
    user = (
        request.user
        if request and hasattr(request, "user") and request.user.is_authenticated
        else None
    )
    company = None
    if request:
        company = getattr(request, "active_company", None)
    if not company and user:
        company = getattr(user, "company", None)
    return request, user, company


def format_datetime_value(value, user=None, company=None, convert_timezone=True):
    """
    Format a date, datetime, or time value using user's format, else company's.

    - datetime: optionally convert to user/company timezone, then format with
      date_time_format (user else company else default).
    - date: format with date_format (user else company else default).
    - time: format with time_format (user else company else default).

    Returns formatted string, or None if value is not date/datetime/time.
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        if convert_timezone:
            tz_str = (user and getattr(user, "time_zone", None)) or (
                company and getattr(company, "time_zone", None)
            )
            if tz_str:
                try:
                    user_tz = ZoneInfo(tz_str)
                    if timezone.is_naive(value):
                        value = timezone.make_aware(
                            value, timezone.get_default_timezone()
                        )
                    value = value.astimezone(user_tz)
                except Exception:
                    pass
        elif timezone.is_aware(value):
            value = timezone.localtime(value)
        fmt = "%Y-%m-%d %H:%M:%S"
        if user and getattr(user, "date_time_format", None):
            fmt = user.date_time_format
        elif company and getattr(company, "date_time_format", None):
            fmt = company.date_time_format
        if uses_jalali_calendar(user=user):
            try:
                return format_gregorian_as_jalali(value, fmt, user=user)
            except Exception:
                return format_gregorian_as_jalali(
                    value, "%Y-%m-%d %H:%M:%S", user=user
                )
        try:
            return value.strftime(fmt)
        except Exception:
            return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        fmt = "%Y-%m-%d"
        if user and getattr(user, "date_format", None):
            fmt = user.date_format
        elif company and getattr(company, "date_format", None):
            fmt = company.date_format
        if uses_jalali_calendar(user=user):
            try:
                return format_gregorian_as_jalali(value, fmt, user=user)
            except Exception:
                return format_gregorian_as_jalali(value, "%Y-%m-%d", user=user)
        try:
            return value.strftime(fmt)
        except Exception:
            return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        fmt = "%I:%M:%S %p"
        if user and getattr(user, "time_format", None):
            fmt = user.time_format
        elif company and getattr(company, "time_format", None):
            fmt = company.time_format
        try:
            return value.strftime(fmt)
        except Exception:
            return value.strftime("%I:%M:%S %p")
    return None


def display_fk(value):
    """Return the string representation of a related foreign-key value if available."""
    if hasattr(value, "__str__"):
        return str(value)
    return value
