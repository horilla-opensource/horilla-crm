from django.utils.translation import gettext_lazy as _

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
    ("sunday", _("Sunday")),
    ("monday", _("Monday")),
    ("tuesday", _("Tuesday")),
    ("wednesday", _("Wednesday")),
    ("thursday", _("Thursday")),
    ("friday", _("Friday")),
    ("saturday", _("Saturday")),
]

OPERATOR_CHOICES = [
    ("equals", _("Equals")),
    ("not_equals", _("Not Equals")),
    ("contains", _("Contains")),
    ("not_contains", _("Does Not Contain")),
    ("starts_with", "Starts With"),
    ("ends_with", _("Ends With")),
    ("greater_than", _("Greater Than")),
    ("greater_than_equal", _("Greater Than or Equal")),
    ("less_than", _("Less Than")),
    ("less_than_equal", _("Less Than or Equal")),
    ("is_empty", _("Is Empty")),
    ("is_not_empty", _("Is Not Empty")),
]
