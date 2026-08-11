"""
Choice constants for various form fields and configuration options.

This module contains predefined choice tuples for languages, date/time formats,
currency formats, number grouping, months, days, and operators used throughout
the Horilla application.
"""

# Standard library imports
from zoneinfo import available_timezones

# Third-party imports
import pycountry

# Third-party imports (Django)
from django.utils.translation import gettext_lazy as _

TIMEZONE_CHOICES = sorted([(tz, tz) for tz in available_timezones()])


LANGUAGE_CHOICES = [
    ("en", _("English")),
    ("fr", _("French")),
    ("de", _("German")),
    ("es", _("Spanish")),
    ("it", _("Italian")),
    ("pt", _("Portuguese")),
]

CURRENCY_FORMAT_CHOICES = [
    ("western_format", "1,234,567"),
    ("european_format", "1.234.567"),
    ("scientific_format", "1 234 567"),
    ("indian_format", "12,34,567"),
]

CALENDAR_SYSTEM_CHOICES = [
    ("jalali", _("Shamsi (Jalali)")),
    ("gregorian", _("Gregorian")),
]

JALALI_DATE_FORMAT_CHOICES = [
    ("%Y/%m/%d", "۱۴۰۴/۰۵/۲۱ (YYYY/MM/DD)"),
    ("%Y-%m-%d", "۱۴۰۴-۰۵-۲۱ (YYYY-MM-DD)"),
    ("%d/%m/%Y", "۲۱/۰۵/۱۴۰۴ (DD/MM/YYYY)"),
    ("%d %B %Y", "۲۱ مرداد ۱۴۰۴"),
    ("%d %b %Y", "۲۱ مرد ۱۴۰۴"),
]

JALALI_DATETIME_FORMAT_CHOICES = [
    ("%Y/%m/%d %H:%M:%S", "۱۴۰۴/۰۵/۲۱ 13:45:00"),
    ("%Y/%m/%d %H:%M", "۱۴۰۴/۰۵/۲۱ 13:45"),
    ("%Y-%m-%d %H:%M:%S", "۱۴۰۴-۰۵-۲۱ 13:45:00"),
    ("%Y-%m-%dT%H:%M", "۱۴۰۴-۰۵-۲۱T13:45"),
    ("%d %B %Y %H:%M", "۲۱ مرداد ۱۴۰۴ 13:45"),
]

DATE_FORMAT_CHOICES = [
    ("%Y-%m-%d", "YYYY-MM-DD (2006-10-25)"),
    ("%m/%d/%Y", "MM/DD/YYYY (10/25/2006)"),
    ("%m/%d/%y", "MM/DD/YY (10/25/06)"),
    ("%b %d %Y", "Mon DD YYYY (Oct 25 2006)"),
    ("%b %d, %Y", "Mon DD, YYYY (Oct 25, 2006)"),
    ("%d %b %Y", "DD Mon YYYY (25 Oct 2006)"),
    ("%d %b, %Y", "DD Mon, YYYY (25 Oct, 2006)"),
    ("%B %d %Y", "Full Month DD YYYY (October 25 2006)"),
    ("%B %d, %Y", "Full Month DD, YYYY (October 25, 2006)"),
    ("%d %B %Y", "DD Full Month YYYY (25 October 2006)"),
    ("%d %B, %Y", "DD Full Month, YYYY (25 October, 2006)"),
]

DATETIME_FORMAT_CHOICES = [
    ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:MM:SS (2006-10-25 13:45:00)"),
    ("%Y-%m-%d %I:%M:%S %p", "YYYY-MM-DD HH:MM:SS AM/PM (2006-10-25 01:45:00 PM)"),
    ("%m/%d/%Y %H:%M", "MM/DD/YYYY HH:MM (10/25/2006 13:45)"),
    ("%d %b %Y %H:%M:%S", "DD Mon YYYY HH:MM:SS (25 Oct 2006 13:45:00)"),
    ("%d %B %Y %I:%M %p", "DD Full Month YYYY HH:MM AM/PM (25 October 2006 01:45 PM)"),
    ("%b %d, %Y %I:%M:%S %p", "Mon DD, YYYY HH:MM:SS AM/PM (Oct 25, 2006 01:45:00 PM)"),
    ("%d-%m-%Y %H:%M:%S", "DD-MM-YYYY HH:MM:SS (25-10-2006 13:45:00)"),
    ("%Y/%m/%d %H:%M:%S", "YYYY/MM/DD HH:MM:SS (2006/10/25 13:45:00)"),
    ("%Y-%m-%dT%H:%M:%S", "ISO 8601 (2006-10-25T13:45:00)"),
    ("%Y-%m-%d %H:%M:%S.%f", "YYYY-MM-DD HH:MM:SS.mmmmmm (2006-10-25 13:45:00.123456)"),
    (
        "%A, %d %B %Y %I:%M %p",
        "Full Weekday, DD Full Month YYYY HH:MM AM/PM (Wednesday, 25 October 2006 01:45 PM)",
    ),
]

NUMBER_GROUPING_CHOICES = [
    ("0", _("No Grouping")),
    ("3,0", "1,000; 1,000,000"),
    ("3,2,0", "1,00,00,000 (Indian Style)"),
    ("4,0", "10,000; 100,000,000"),
]

TIME_FORMAT_CHOICES = [
    ("%H:%M:%S", "HH:MM:SS (13:45:00)"),
    ("%I:%M:%S %p", "HH:MM:SS AM/PM (01:45:00 PM)"),
    ("%H:%M", "HH:MM (13:45)"),
    ("%I:%M %p", "HH:MM AM/PM (01:45 PM)"),
    ("%H", "HH (13)"),
    ("%I", "HH (01)"),
    ("%M:%S", "MM:SS (45:00)"),
    ("%S", "SS (00)"),
    ("%p", "AM/PM (PM)"),
    ("%H:%M:%S.%f", "HH:MM:SS.mmmmmm (13:45:00.123456)"),
]

MONTH_CHOICES = [
    ("january", _("January")),
    ("february", _("February")),
    ("march", _("March")),
    ("april", _("April")),
    ("may", _("May")),
    ("june", _("June")),
    ("july", _("July")),
    ("august", _("August")),
    ("september", _("September")),
    ("october", _("October")),
    ("november", _("November")),
    ("december", _("December")),
]

DAY_CHOICES = [
    ("sun", "Sunday"),
    ("mon", "Monday"),
    ("tue", "Tuesday"),
    ("wed", "Wednesday"),
    ("thu", "Thursday"),
    ("fri", "Friday"),
    ("sat", "Saturday"),
]

# Mon→Sun order for business hours, shifts, and per-day TimeField prefixes.
# (``DAY_CHOICES`` is Sunday-first for legacy pickers — keep these separate.)
WEEK_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

DAY_LABELS = {
    "mon": _("Monday"),
    "tue": _("Tuesday"),
    "wed": _("Wednesday"),
    "thu": _("Thursday"),
    "fri": _("Friday"),
    "sat": _("Saturday"),
    "sun": _("Sunday"),
}

# BusinessHour.timing_type and ShiftHour.timing_type
TIMING_CHOICES = [
    ("same", _("Same Hour Every Day")),
    ("different", _("Different Hour Per Day")),
]

# Short weekday code → TimeField name prefix (``mon`` → ``monday`` for ``monday_start``)
SHORT_TO_DAY_PREFIX = {
    "mon": "monday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}

OPERATOR_CHOICES = [
    ("exact", _("Equals")),
    ("ne", _("Not Equals")),
    ("icontains", _("Contains")),
    ("not_contains", _("Does Not Contain")),
    ("istartswith", _("Starts With")),
    ("iendswith", _("Ends With")),
    ("gt", _("Greater Than")),
    ("gte", _("Greater Than or Equal")),
    ("lt", _("Less Than")),
    ("lte", _("Less Than or Equal")),
    ("isnull", _("Is Empty")),
    ("isnotnull", _("Is Not Empty")),
    ("between", _("Between")),
]

# IMPORTANT: Order matters — do not change the order of these lists
DISPLAYABLE_FIELD_TYPES = [
    "CharField",
    "TextField",
    "BooleanField",
    "DateField",
    "DateTimeField",
    "TimeField",
    "EmailField",
    "URLField",
]

TABLE_FALLBACK_FIELD_TYPES = [
    "CharField",
    "TextField",
    "EmailField",
]

FIELD_TYPE_MAP = {
    "CharField": "text",
    "TextField": "text",
    "BooleanField": "boolean",
    "IntegerField": "number",
    "FloatField": "float",
    "DecimalField": "decimal",
    "ForeignKey": "foreignkey",
    "DateField": "date",
    "DateTimeField": "datetime",
}

BLOCKED_EXTENSIONS = {
    ".sqlite3",
    ".py",
    ".env",
    ".key",
    ".pem",
    ".ini",
    ".conf",
}


def get_subdivision_choices(country_code):
    """Return (code, name) subdivision choices for a given ISO country code."""
    try:
        subdivisions = list(
            pycountry.subdivisions.get(country_code=country_code.upper())
        )
        return [(sub.code, sub.name) for sub in subdivisions]
    except Exception:
        return []
