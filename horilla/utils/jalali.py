"""
Jalali (Shamsi) calendar helpers for Persian-locale users.

Gregorian values are stored in the database; these utilities convert for
display and parse user-facing Jalali input when the Shamsi calendar is active.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import jdatetime
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import get_language

JALALI_DATE_FORMATS = (
    "%Y/%m/%d",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
)

JALALI_DATETIME_FORMATS = (
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
)


def normalize_language_code(language: str | None) -> str:
    """Return the primary language subtag (e.g. ``fa`` from ``fa-ir``)."""
    if not language:
        return ""
    return language.replace("_", "-").split("-")[0].lower()


def get_active_language(user: Any = None) -> str:
    """Return the active UI language (session, profile, or project default)."""
    return normalize_language_code(get_language())


def uses_jalali_calendar(user: Any = None, language: str | None = None) -> bool:
    """
    Return True when the UI should use the Shamsi calendar.

    Applies only to Persian (``fa``) users who have not opted into Gregorian.
    """
    lang = language or get_active_language(user)
    if lang != "fa":
        return False
    if user is None:
        return True
    system = getattr(user, "calendar_system", None) or "jalali"
    return system == "jalali"


def gregorian_to_jalali(value: date | datetime) -> jdatetime.date | jdatetime.datetime:
    """Convert a Gregorian date/datetime to its Jalali equivalent."""
    if isinstance(value, datetime):
        return jdatetime.datetime.fromgregorian(datetime=value)
    return jdatetime.date.fromgregorian(date=value)


def format_gregorian_as_jalali(
    value: date | datetime | time,
    fmt: str,
    *,
    user: Any = None,
) -> str:
    """Format a Gregorian value using Jalali calendar parts and the given strftime pattern."""
    if isinstance(value, datetime):
        jalali_value = jdatetime.datetime.fromgregorian(datetime=value)
        return jalali_value.strftime(fmt)
    if isinstance(value, date):
        jalali_value = jdatetime.date.fromgregorian(date=value)
        return jalali_value.strftime(fmt)
    return value.strftime(fmt)


def parse_jalali_date(value: str) -> date | None:
    """Parse a Jalali date string into a Gregorian ``date``."""
    if not value or not str(value).strip():
        return None
    value = str(value).strip()
    for fmt in JALALI_DATE_FORMATS:
        try:
            return jdatetime.date.strptime(value, fmt).togregorian()
        except ValueError:
            continue
    return parse_date(value)


def parse_jalali_datetime(value: str) -> datetime | None:
    """Parse a Jalali datetime string into a Gregorian ``datetime``."""
    if not value or not str(value).strip():
        return None
    value = str(value).strip().replace("T", " ")
    for fmt in JALALI_DATETIME_FORMATS:
        try:
            return jdatetime.datetime.strptime(value, fmt).togregorian()
        except ValueError:
            continue
    return parse_datetime(value)


def parse_user_date(value: str, *, user: Any = None) -> date | None:
    """Parse a date field value respecting the user's calendar preference."""
    if not value:
        return None
    if uses_jalali_calendar(user=user):
        parsed = parse_jalali_date(value)
        if parsed is not None:
            return parsed
    return parse_date(value)


def parse_user_datetime(value: str, *, user: Any = None) -> datetime | None:
    """Parse a datetime field value respecting the user's calendar preference."""
    if not value:
        return None
    normalized = str(value).strip()
    if uses_jalali_calendar(user=user):
        parsed = parse_jalali_datetime(normalized)
        if parsed is not None:
            return parsed
    return parse_datetime(normalized)
