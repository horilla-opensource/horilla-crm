"""
Template tags and filters for Horilla templates.

This module provides Django template filters and helper functions used across Horilla
templates, including attribute lookups, formatting utilities, and rendering helpers.
"""

# Standard library imports
import json as json_module
import logging
import re
from datetime import date, datetime, time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Third-party imports
import pytz
from dateutil import parser as dateutil_parser
from django import template
from django.apps import apps
from django.db import models
from django.db.models import Manager, QuerySet
from django.forms import BaseForm
from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Horilla application imports
from horilla.auth.models import User
from horilla.menu.sub_section_menu import get_sub_section_menu
from horilla.registry.asset_registry import get_registered_html, get_registered_js
from horilla_core.models import MultipleCurrency
from horilla_core.utils import get_currency_display_value
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)

register = template.Library()


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
                    user_tz = pytz.timezone(tz_str)
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


@register.filter
def user_datetime_format(value):
    """
    Format a date, datetime, or time using the request user's format,
    falling back to company format. Use in templates: {{ value|user_datetime_format }}

    Returns formatted string for date/datetime/time; passes through other values.
    """
    _, user, company = _get_request_user_company()
    result = format_datetime_value(
        value, user=user, company=company, convert_timezone=True
    )
    return result if result is not None else value


@register.filter
def user_datetime_format_display(value):
    """
    Same as user_datetime_format but also accepts pre-formatted date/datetime
    strings (e.g. from auditlog changes_display_dict). Parses the string and
    re-formats with the user's format. Use in history "updated" section so
    dates match the rest of the page: {{ value|user_datetime_format_display }}
    """
    _, user, company = _get_request_user_company()
    result = format_datetime_value(
        value, user=user, company=company, convert_timezone=True
    )
    if result is not None:
        return result
    # Parse pre-formatted date/datetime strings and re-format with user format
    if (
        isinstance(value, str)
        and value
        and value not in ("--", "None", "none")
        and dateutil_parser
    ):
        try:
            parsed = dateutil_parser.parse(value)
            if isinstance(parsed, datetime) and timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
            result = format_datetime_value(
                parsed, user=user, company=company, convert_timezone=True
            )
            if result is not None:
                return result
        except (ValueError, TypeError):
            pass
    return value


@register.filter
def get_field(obj, field_path):
    """
    Dot-lookup via __ (double underscore), including nested relations,
    supports callables and Manager/QuerySet (takes first related object).
    If the final field is a declared currency field on its model (CURRENCY_FIELDS),
    uses get_currency_display_value(parent_obj, final_field_name, user).
    """
    try:
        current = obj
        parent = None
        parts = field_path.split("__")

        for part in parts:
            parent = current  # keep track of the parent object before resolving part
            current = getattr(current, part)
            if isinstance(current, (Manager, QuerySet)):
                current = current.first()
                if not current:
                    return ""
            elif callable(current):
                current = current()

        _request, user, company = _get_request_user_company()
        final_field_name = parts[-1] if parts else None

        if (
            parent is not None
            and hasattr(parent.__class__, "CURRENCY_FIELDS")
            and final_field_name in getattr(parent.__class__, "CURRENCY_FIELDS", [])
        ):
            return get_currency_display_value(parent, final_field_name, user)

        # Date/Time formatting via shared helper (user else company format)
        formatted = format_datetime_value(
            current, user=user, company=company, convert_timezone=False
        )
        if formatted is not None:
            return formatted

        if isinstance(current, bool):
            return _("Yes") if current else _("No")

        if parent is not None and final_field_name:
            try:
                field = parent._meta.get_field(final_field_name)
                if hasattr(field, "choices") and field.choices:
                    display_method = f"get_{final_field_name}_display"
                    if hasattr(parent, display_method):
                        return getattr(parent, display_method)()
            except Exception:
                pass

        return str(current) if current is not None else ""
    except Exception:
        return ""


@register.filter(name="format")
def format(string: str, instance: object):
    """
    Formats a string by replacing placeholders with attributes from an instance
    get methods from model.
    """
    string = force_str(string)
    attr_placeholder_regex = r"{([^}]*)}"
    attr_placeholders = re.findall(attr_placeholder_regex, string)

    if not attr_placeholders:
        return string

    format_context = {}
    for attr_placeholder in attr_placeholders:
        attrs = attr_placeholder.split("__")
        value = instance
        for attr in attrs:
            value = getattr(value, attr, "")
            if callable(value):
                value = value()
            if hasattr(value, "__str__"):
                value = str(value)
            if value is not None:
                format_context[attr_placeholder] = value

    return string.format(**format_context)


@register.filter
def get_class_name(instance):
    """Return the full path of the class name for an instance."""
    if not instance:
        return ""
    module = instance.__class__.__module__
    class_name = instance.__class__.__name__
    return f"{module}.{class_name}"


@register.filter
def get_item(dictionary, key):
    """
    Return the value for `key` from `dictionary`.

    If `dictionary` is None, returns None. Converts `key` to string when
    performing the lookup to be tolerant of numeric keys supplied from templates.
    """
    if dictionary is None:
        return None
    return dictionary.get(str(key))


@register.filter
def get_item_form(dictionary, key):
    """Get item from dictionary using key"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def join_comma(value):
    """Join list items with comma"""
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return value


@register.filter
def get_steps(dictionary, key):
    """
    Get an item from a dictionary using a key
    Usage: {{ step_titles|get_item:current_step }}
    """
    key_name = f"step{key}"
    return dictionary.get(key_name, "")


@register.filter
def render_action_button(action, obj):
    """
    Render an action button for use in templates.

    `action` is a mapping that may contain keys like 'src', 'icon', 'action',
    'attrs', and styling options. Returns a marked-safe HTML string for the
    appropriate button representation (image, icon, or text).
    """
    attrs = format(action.get("attrs", ""), obj).strip()
    tooltip = _(action.get("action", ""))

    if "src" in action:
        img_class = action.get("img_class", "")
        src = action.get("src", "")
        static_url = static(src)
        classes = img_class.split()
        size_classes = [c for c in classes if c.startswith("w-") or c.startswith("h-")]
        other_classes = [c for c in classes if c not in size_classes]
        image_class = " ".join(other_classes)

        return mark_safe(
            f"""
                <button {attrs} class='group relative w-10 h-7 bg-dark-25 flex-1 flex justify-center border-r border-r-[white] hover:bg-dark-50 transition duration-300 items-center'>
                    <img src="{static_url}" alt="{tooltip}" width="16" class="{image_class}" />
                    <div class="min-w-max z-40 absolute h-auto py-[3px] px-[15px] right-[40px] top-0 bg-[#000000] text-[.7rem] rounded-[5px] text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                        <p>{tooltip}</p>
                    </div>
                </button>
        """
        )

    if "icon" in action:
        icon_name = action.get("icon", "")
        icon_class = action.get("icon_class", "")
        button_class = action.get("class", "")
        return mark_safe(
            f'<button class="w-10 h-7 bg-dark-25 flex-1 flex justify-center border-r border-r-[white] hover:bg-dark-50 transition duration-300 items-center" {attrs} title="{tooltip}">'
            f'<i class="{icon_name} {icon_class}"></i>'
            f"</button>"
        )

    # else:
    button_class = action.get("class", "")
    return mark_safe(
        f'<button class="{button_class}" {attrs} title="{tooltip}">{tooltip}</button>'
    )


@register.filter
def getattribute(obj, attr):
    """Return attribute value from `obj` or empty string if missing."""
    return getattr(obj, attr, "")


@register.filter
def has_value(query_dict, key):
    """
    Returns True if the key exists in query_dict and has a non-empty value.
    """
    return bool(query_dict.get(key, ""))


@register.filter
def get_range(value):
    """
    Generate a range from 1 to value
    Usage: {% for i in total_steps|get_range %}
    """
    return range(1, int(value) + 1)


@register.filter
def get_fields_for_step(form, step):
    """
    Returns form fields for the given step
    """
    if not isinstance(form, BaseForm):
        return []

    if hasattr(form, "get_fields_for_step"):
        return form.get_fields_for_step(step)

    if hasattr(form, "step_fields") and step in form.step_fields:
        return [form[field] for field in form.step_fields[step] if field in form.fields]

    return form.visible_fields()


@register.filter
def json(value):
    """Serialize a Python value to a JSON string for templates."""
    return json.dumps(value)


@register.filter
def lookup(dictionary, key):
    """Return dictionary[key] or an empty dict if not present."""
    return dictionary.get(key, {})


@register.filter
def get_field_value(obj, field_name):
    """
    Enhanced template filter to get field values with proper display for different field types
    """
    try:
        field = next((f for f in obj._meta.get_fields() if f.name == field_name), None)
        if not field:
            return getattr(obj, field_name, "")

        value = getattr(obj, field_name)

        if isinstance(field, models.ManyToManyField):
            return (
                ", ".join(str(item) for item in value.all()) if value.exists() else ""
            )

        if isinstance(field, models.ForeignKey):
            return str(value) if value else ""

        # Handle Choice fields - show display value
        if hasattr(field, "choices") and field.choices:
            display_method = getattr(obj, f"get_{field_name}_display", None)
            if display_method:
                return display_method()
            return str(value) if value else ""

        # Handle Boolean fields
        if isinstance(field, models.BooleanField):
            if value is True:
                return "Yes"
            if value is False:
                return "No"
            return ""

        # Handle Date/DateTime fields
        if isinstance(field, models.DateTimeField):
            return value.strftime("%Y-%m-%d %H:%M") if value else ""
        if isinstance(field, models.DateField):
            return value.strftime("%Y-%m-%d") if value else ""

        # Handle Decimal fields
        if isinstance(field, models.DecimalField):
            return f"{value:.2f}" if value is not None else ""

        # Default case
        return str(value) if value is not None else ""

    except Exception:
        return str(getattr(obj, field_name, ""))


@register.filter
def get_field_display_value(obj, field_name):
    """
    Get the display value specifically for showing in readonly fields
    This is an alias for get_field_value for backward compatibility
    """
    return get_field_value(obj, field_name)


@register.filter
def extract_class(value):
    """Extract the class attribute value from a string of HTML attributes."""
    match = re.search(r'class="([^"]*)"', value)
    return match.group(1) if match else ""


@register.filter
def extract_style(value):
    """Extract the style attribute value from a string of HTML attributes."""
    match = re.search(r'style="([^"]*)"', value)
    return match.group(1) if match else ""


@register.filter
def strip_class_style(value):
    """Remove class and style attributes from a string of HTML attributes."""
    value = re.sub(r'\s*class="[^"]*"', "", value)
    value = re.sub(r'\s*style="[^"]*"', "", value)
    return " ".join(value.split())


@register.filter
def get_related_objects(obj, field_name):
    """
    Get related objects for a field
    """
    try:
        related_manager = getattr(obj, field_name)
        if hasattr(related_manager, "all"):
            return related_manager.all()
        return []
    except Exception:
        return []


@register.filter
def model_name(obj):
    """
    Get model name from object
    """
    return obj.__class__.__name__


@register.filter
def model_verbose_name(obj):
    """
    Get model verbose name
    """
    return obj._meta.verbose_name


@register.filter
def model_verbose_name_plural(obj):
    """
    Get model verbose name plural
    """
    return obj._meta.verbose_name_plural


@register.simple_tag
def get_field_display(obj, field_name):
    """
    Get display value for any field type
    """
    try:
        field = obj._meta.get_field(field_name)
        value = getattr(obj, field_name)

        if hasattr(field, "choices") and field.choices:
            display_method = getattr(obj, f"get_{field_name}_display", None)
            if display_method:
                return display_method()

        if isinstance(field, models.ForeignKey) and value:
            return str(value)

        if isinstance(field, models.DateTimeField) and value:
            return value.strftime("%d/%m/%Y %H:%M")

        if isinstance(field, models.DateField) and value:
            return value.strftime("%d/%m/%Y")

        return str(value) if value is not None else ""
    except Exception:
        return str(getattr(obj, field_name, ""))


@register.filter
def can_add_related(related_list, obj):
    """
    Check if user can add related objects
    """
    # Add your permission logic here
    return related_list.get("can_add", True)


@register.filter
def get_add_url(obj, related_list):
    """
    Get URL for adding new related object
    """
    add_url = related_list.get("add_url", "")
    if add_url:
        try:
            return reverse(add_url) + f"?{obj._meta.model_name}={obj.pk}"
        except Exception:
            return add_url
    return ""


@register.filter
def get_view_all_url(obj, related_list):
    """
    Get URL for viewing all related objects
    """
    view_all_url = related_list.get("view_all_url", "")
    if view_all_url:
        try:
            return reverse(view_all_url) + f"?{obj._meta.model_name}={obj.pk}"
        except Exception:
            return view_all_url
    return ""


@register.simple_tag
def safe_url(viewname, *args, **kwargs):
    """Safely reverse a view name; return '#' if reversing the URL fails."""
    try:
        return reverse(viewname, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "#"


@register.filter
def sanitize_id(value):
    """
    Sanitize a string to make it a valid HTML id by replacing spaces and special characters
    with hyphens and removing invalid characters.
    """
    value = str(value)
    value = re.sub(r"[\s/&\\]+", "-", value)
    value = re.sub(r"[^\w-]", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


@register.filter
def verbose_name(obj, field_name):
    """
    Returns the verbose name for a model field.
    Usage: {{ object|verbose_name:"field_name" }}
    """
    try:
        return obj._meta.get_field(field_name).verbose_name
    except Exception:
        return field_name.replace("_", " ").title()


def display_fk(value):
    """Return the string representation of a related foreign-key value if available."""
    if hasattr(value, "__str__"):
        return str(value)
    return value


numeric_test = re.compile(r"^\d+$")


@register.filter
def is_image_file(filename):
    """
    Django template filter to check if a given filename is an image file.
    """
    return filename.lower().endswith((".png", ".jpg", ".jpeg", ".svg"))


@register.filter
def to_json(value):
    """Serialize a Python value to JSON for use in templates."""
    return json_module.dumps(value, ensure_ascii=False)


@register.simple_tag(takes_context=True)
def render_field_with_name(context, form, field_name, row_id=None, selected_value=None):
    """
    Custom template tag to render form field with modified name and id attributes.
    Usage: {% render_field_with_name form field_name row_id selected_value %}
    """
    # Check if we have pre-generated value widget HTML (for automations and other apps)
    if field_name == "value" and row_id is not None:
        value_widget_html_key = f"value_widget_html_{row_id}"
        value_widget_html = context.get(value_widget_html_key)
        if value_widget_html:
            return mark_safe(value_widget_html)
        # If value widget HTML not found, fall back to default text input
        # This ensures the value field always appears
        if not form or field_name not in form.fields:
            return mark_safe(
                f'<input type="text" '
                f'name="value_{row_id}" '
                f'id="id_value_{row_id}" '
                f'class="text-color-820 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600" '
                f'placeholder="Enter Value">'
            )

    if form and field_name in form.fields:
        field = form[field_name]
        field_html = str(field)

        if row_id:
            field_html = field_html.replace(
                f'name="{field_name}"', f'name="{field_name}_{row_id}"'
            )

            field_html = re.sub(
                rf'id="id_{field_name}(_\d*)?"',
                f'id="id_{field_name}_{row_id}"',
                field_html,
            )

            if selected_value and "<select" in field_html:
                if hasattr(selected_value, "pk"):
                    selected_value = selected_value.pk

                field_html = re.sub(r' selected="selected"', "", field_html)
                field_html = re.sub(r" selected", "", field_html)

                field_html = re.sub(
                    rf'(<option value="{re.escape(str(selected_value))}"[^>]*?)>',
                    r"\1 selected>",
                    field_html,
                )

            elif selected_value and "<input" in field_html:
                if hasattr(selected_value, "pk"):
                    selected_value = selected_value.pk

                field_html = re.sub(r' value="[^"]*"', "", field_html)
                field_html = re.sub(
                    r"(<input[^>]*?)>", rf'\1 value="{selected_value}">', field_html
                )

        return mark_safe(field_html)

    return ""


@register.filter
def humanize_field_name(value):
    """Convert an underscored field name into a human-readable title."""
    if not value:
        return value
    # Split by underscore, capitalize each word, and join with spaces
    return " ".join(word.capitalize() for word in value.split("_"))


@register.filter
def getter(obj, attr):
    """Return attribute value from object or empty string if missing."""
    return getattr(obj, attr, "")


@register.filter
def get_user_pk(obj):
    """Get primary key from user object"""
    if hasattr(obj, "pk"):
        return obj.pk
    return obj


@register.filter
def get_field_verbose_name(component_or_condition, model_name_or_field_name):
    """
    Get verbose name for a field in a model
    Usage in template:
    {% with field=component|get_field_verbose_name:component.grouping_field %}
        {{ field }}
    {% endwith %}
    """
    try:
        if hasattr(component_or_condition, "module"):
            model = apps.get_model("your_app_name", component_or_condition.module)
            field = model._meta.get_field(model_name_or_field_name)
        else:
            model = apps.get_model("your_app_name", model_name_or_field_name)
            field = model._meta.get_field(component_or_condition.field)
        return field.verbose_name.title()
    except Exception:
        field_name = getattr(component_or_condition, "field", model_name_or_field_name)
        return field_name.replace("_", " ").title()


@register.simple_tag(takes_context=True)
def unpack_context(context, data_dict):
    """
    Add each key/value from data_dict to the current template context.
    """
    if isinstance(data_dict, dict):
        for key, value in data_dict.items():
            context[key] = value
    return ""


@register.simple_tag(takes_context=True)
def is_active(context, *url_names):
    """
    Works with either:
    - A list of URLs: {% is_active item.active_urls %}
    - One or more URL strings: {% is_active "url_name1" "url_name2" %}
    """
    request = context.get("request")
    if not request or not request.resolver_match:
        return ""

    current_view = request.resolver_match.view_name
    current_path = request.path

    urls = []
    for arg in url_names:
        if isinstance(arg, (list, tuple)):
            urls.extend(arg)
        else:
            urls.append(arg)

    for url in urls:
        if current_view == url or current_path == url:
            return "text-primary-600"

    return ""


@register.simple_tag(takes_context=True)
def is_open(context, *url_names):
    """Return 'open' when the current request matches any of the provided URLs.

    The function accepts a mix of argument types:
    - Strings representing view names or path strings
    - Dicts with a 'url' key
    - Lists/tuples containing any of the above

    It normalizes inputs into a set and checks against the current view name
    and the current path (without trailing slash).
    """
    request = context.get("request")
    if not request or not request.resolver_match:
        return ""

    current_path = request.path
    current_view_name = request.resolver_match.view_name

    all_urls = set()

    for item in url_names:
        if isinstance(item, dict) and "url" in item:

            all_urls.add(item["url"].rstrip("/"))
        elif isinstance(item, (list, tuple)):
            for sub_item in item:
                if isinstance(sub_item, dict) and "url" in sub_item:
                    all_urls.add(sub_item["url"].rstrip("/"))
                elif isinstance(sub_item, str):
                    all_urls.add(sub_item)
        elif isinstance(item, str):
            all_urls.add(item)

    if current_view_name in all_urls or current_path.rstrip("/") in all_urls:
        return "open"
    return ""


@register.simple_tag(takes_context=True)
def is_open_collapse(context, *url_names):
    """
    Returns 'rotate-90' if the current view matches any given URL or view name.
    Handles both cases:
      1. A tuple of dictionaries containing 'url' keys
      2. A tuple of view name strings
    """
    request = context.get("request")
    if not request or not request.resolver_match:
        return ""

    current_view = request.resolver_match.view_name
    current_path = request.path

    urls_to_check = set()

    for item in url_names:
        if isinstance(item, (list, tuple)):
            for entry in item:
                if isinstance(entry, dict) and "url" in entry:
                    urls_to_check.add(entry["url"])
        elif isinstance(item, str):
            urls_to_check.add(item)

    return (
        "rotate-90"
        if current_view in urls_to_check or current_path in urls_to_check
        else ""
    )


@register.simple_tag(takes_context=True)
def has_perm(context, perm_name):
    """
    Usage: {% has_perm "horilla_core.view_horillauser" as can_view_horillauser %}
    """
    user = context["request"].user
    return user.has_perm(perm_name)


@register.filter
def has_super_user(user, perm_data):
    """
    Check if the user is superuser OR has the required permissions.

    - `perm_data` can be:
        - a single permission string
        - a list/tuple of permissions
        - a dict like {"perms": [...], "all_perms": True/False}

    Default behavior:
      - OR check: user needs **any one** of the permissions.
      - AND check: if all_perms=True, user must have **all** permissions.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if isinstance(perm_data, str):
        return user.has_perm(perm_data)

    if isinstance(perm_data, (list, tuple)):
        return any(user.has_perm(perm) for perm in perm_data)

    if isinstance(perm_data, dict):
        perms = perm_data.get("perms", [])
        all_perms = perm_data.get("all_perms", False)

        if not perms:
            return True

        if all_perms:
            return all(user.has_perm(perm) for perm in perms)

        return any(user.has_perm(perm) for perm in perms)
    return False


@register.simple_tag(takes_context=True)
def has_section_perm_url(context, user, section_name):
    """
    Check if the user can see at least one sub-item in a section.
    Returns the first accessible URL if permissions match.
    """
    if not user or not user.is_authenticated:
        return False

    request = context.get("request")
    sub_section_items = get_sub_section_menu(request).get(section_name, [])
    if not sub_section_items:
        return "/"

    for item in sub_section_items:
        perm_data = item.get("perm", {})

        if not perm_data or not perm_data.get("perms"):
            return item.get("url")

        perms = perm_data.get("perms", [])
        all_perms = perm_data.get("all_perms", False)

        if all_perms:
            if all(user.has_perm(perm) for perm in perms):
                return item.get("url")
        else:
            if any(user.has_perm(perm) for perm in perms):
                return item.get("url")

    return False


@register.simple_tag
def load_registered_js():
    """
    Retrieve all registered JavaScript file paths for inclusion in templates.

    Returns:
        list: List of static file paths for JavaScript files registered by apps.
    """
    return get_registered_js()


@register.simple_tag
def load_registered_html(slot, page="base"):
    """
    Template tag to retrieve all registered HTML template fragments
    for a given slot in the base layout.
    """
    return get_registered_html(slot, page)


@register.simple_tag
def display_field_value(obj, field_name, user):
    """
    Template tag to display field value with automatic currency formatting,
    datetime timezone conversion, and custom formatting

    Usage in template:
    {% display_field_value obj field_name request.user %}

    Works automatically if model has CURRENCY_FIELDS attribute
    Handles datetime fields with user's timezone and format preferences
    """
    # Check if it's a currency field - AUTOMATICALLY DETECTS!
    if (
        hasattr(obj.__class__, "CURRENCY_FIELDS")
        and field_name in obj.__class__.CURRENCY_FIELDS
    ):
        return get_currency_display_value(obj, field_name, user)

    # Check if object has a custom get_field_display method (optional)
    if hasattr(obj, "get_field_display"):
        return obj.get_field_display(field_name, user)

    # Default: just get the field value
    value = getattr(obj, field_name, None)

    if value is None:
        return ""

    _, _, company = _get_request_user_company()

    # Date/Time/DateTime via shared formatter (user else company, with timezone conversion)
    formatted = format_datetime_value(
        value, user=user, company=company, convert_timezone=True
    )
    if formatted is not None:
        return formatted

    # Handle ManyToMany fields
    if hasattr(value, "all"):
        related_objects = value.all()
        if related_objects.exists():
            return ", ".join(str(item) for item in related_objects)
        return ""

    # Handle choice fields automatically
    try:
        field = obj._meta.get_field(field_name)
        if hasattr(field, "choices") and field.choices:
            return dict(field.choices).get(value, value)
    except Exception:
        pass

    # Handle foreign keys and relations
    if hasattr(value, "__str__"):
        return str(value)

    return value


@register.filter
def format_currency(value, user):
    """
    Template filter for currency formatting
    """
    if not value:
        return ""

    user_currency = MultipleCurrency.get_user_currency(user)
    if user_currency:
        return user_currency.display_with_symbol(value)

    return str(value)


@register.filter
def remove_query_param(url, param):
    """
    Removes a query parameter from a URL string.
    Example: {{ request.get_full_path|remove_query_param:"section" }}
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query, keep_blank_values=True)
    query_params.pop(param, None)
    new_query = urlencode(query_params, doseq=True)
    cleaned_url = urlunparse(parsed_url._replace(query=new_query))
    return cleaned_url


@register.filter
def get_field_permission(field_permissions, field_name):
    """
    Get field permission from the permissions dict
    Returns the permission type or 'readwrite' as default
    """
    if not field_permissions:
        return "readwrite"
    return field_permissions.get(field_name, "readwrite")


def get_app_labels_from_context(related_obj, request, action=None):
    """
    Dynamically discover app labels from context.

    Args:
        related_obj: The related model instance
        request: The request object
        action: Optional action dict that may contain intermediate_app_label

    Returns:
        list: Ordered list of app labels to try (most likely first)
    """

    app_labels = []
    seen = set()  # To avoid duplicates while preserving order

    # 1. Explicit app label from action config (highest priority)
    if action and action.get("intermediate_app_label"):
        app_label = action.get("intermediate_app_label")
        if app_label not in seen:
            app_labels.append(app_label)
            seen.add(app_label)

    # 2. Related object's app label (very likely)
    if related_obj and hasattr(related_obj, "_meta"):
        app_label = related_obj._meta.app_label
        if app_label not in seen:
            app_labels.append(app_label)
            seen.add(app_label)

    # 3. Parent model's app from view class
    if request and hasattr(request, "resolver_match") and request.resolver_match:
        view_func = request.resolver_match.func
        if hasattr(view_func, "view_class"):
            view_class = view_func.view_class
            if hasattr(view_class, "model") and view_class.model:
                app_label = view_class.model._meta.app_label
                if app_label not in seen:
                    app_labels.append(app_label)
                    seen.add(app_label)

    # 4. App name from URL pattern
    if request and hasattr(request, "resolver_match") and request.resolver_match:
        url_name = request.resolver_match.url_name
        if url_name:
            # Extract app from URL pattern like "leads:detail"
            if ":" in url_name:
                app_name = url_name.split(":")[0]
                if app_name not in seen:
                    app_labels.append(app_name)
                    seen.add(app_name)
            # Extract from pattern like "leads_detail"
            elif "_" in url_name:
                app_name = url_name.split("_")[0]
                if app_name not in seen:
                    app_labels.append(app_name)
                    seen.add(app_name)

        # Also check namespace
        namespace = getattr(request.resolver_match, "namespace", None)
        if namespace and namespace not in seen:
            app_labels.append(namespace)
            seen.add(namespace)

    # 5. All installed apps as fallback (least priority)
    for app_config in apps.get_app_configs():
        if app_config.label not in seen:
            app_labels.append(app_config.label)
            seen.add(app_config.label)

    return app_labels


def get_intermediate_instance(action, related_obj, request):
    """
    Get the intermediate model instance based on action config.

    Args:
        action: Action dictionary with intermediate_model config
        related_obj: The related model instance (e.g., Campaign)
        request: The request object to get parent object ID

    Returns:
        The intermediate model instance or None
    """

    intermediate_model_name = action.get("intermediate_model")
    if not intermediate_model_name:
        return None

    try:
        # Get the parent object ID from the URL (e.g., Lead ID)
        parent_id = None
        if hasattr(request, "resolver_match") and request.resolver_match:
            parent_id = request.resolver_match.kwargs.get("pk")

        if not parent_id:
            return None

        # Get app labels to try dynamically
        app_labels_to_try = get_app_labels_from_context(related_obj, request, action)

        # Try to get the intermediate model
        intermediate_model = None
        for app_label in app_labels_to_try:
            try:
                intermediate_model = apps.get_model(app_label, intermediate_model_name)
                logger.debug(
                    "Found intermediate model '%s' in app '%s'",
                    intermediate_model_name,
                    app_label,
                )
                break
            except LookupError:
                continue

        if not intermediate_model:
            logger.warning(
                "Could not find intermediate model '%s' in any of these apps: %s",
                intermediate_model_name,
                app_labels_to_try[:5],  # Show first 5 for brevity
            )
            return None

        # Get field names from action config with defaults
        intermediate_field_name = action.get("intermediate_field")
        parent_field_name = action.get("parent_field")

        if not intermediate_field_name or not parent_field_name:
            logger.error(
                "Action missing 'intermediate_field' or 'parent_field' configuration"
            )
            return None

        # Build the filter kwargs
        filter_kwargs = {
            intermediate_field_name: related_obj,
            f"{parent_field_name}_id": parent_id,
        }

        # Get the intermediate instance
        intermediate_obj = intermediate_model.objects.filter(**filter_kwargs).first()

        if not intermediate_obj:
            logger.debug(
                "No %s found with filters: %s", intermediate_model_name, filter_kwargs
            )

        return intermediate_obj

    except Exception as e:
        logger.error("Error getting intermediate instance: %s", e, exc_info=True)
        return None


def has_action_permission(action, context):
    """
    Check if user has permission to perform an action on an object.
    Supports both direct object permissions and intermediate model permissions.

    Args:
        action: Action dict with permission config
        context: Dict with 'user', 'object', and optionally 'intermediate_object'

    Returns:
        bool: True if user has permission
    """
    user = context.get("user")
    obj = context.get("object")

    perm = action.get("permission")
    own_perm = action.get("own_permission")
    owner_field = action.get("owner_field")
    owner_method = action.get("owner_method")

    perms = action.get("permissions", [])
    perm_logic = action.get("permission_logic", "OR")

    if not perm and not own_perm and not owner_field or user.is_superuser:
        return True

    # Automatically detect if we should use intermediate model
    intermediate_config = action.get("intermediate_model")

    # If intermediate_model is specified, try to get the intermediate instance
    target_obj = obj
    if intermediate_config:
        intermediate_obj = context.get("intermediate_object")
        if intermediate_obj:
            target_obj = (
                intermediate_obj  # Use intermediate object for permission check
            )

    # Validation: own_permission requires owner_field or owner_method
    if own_perm and not owner_field and not owner_method:
        raise ValueError(
            f"Action '{action.get('action')}' must define BOTH "
            "'own_permission' and ('owner_field' OR 'owner_method')."
        )

    # Validation: cannot use both owner_field and owner_method
    if owner_field and owner_method:
        raise ValueError(
            f"Action '{action.get('action')}' cannot define BOTH "
            "'owner_field' AND 'owner_method'. Use only one."
        )

    # Check global permission first
    if perm and user.has_perm(perm):
        return True

    if perms:
        perm_checks = [user.has_perm(p) for p in perms]

        if perm_logic.upper() == "OR":
            # User needs ANY of the permissions
            if any(perm_checks):
                return True
        elif perm_logic.upper() == "AND":
            # User needs ALL of the permissions
            if all(perm_checks):
                return True
        else:
            raise ValueError(
                f"Invalid permission_logic '{perm_logic}'. Must be 'OR' or 'AND'."
            )

    # Check ownership-based permission
    if own_perm and target_obj:
        # Method-based ownership check
        if owner_method:
            if hasattr(target_obj, owner_method):
                method = getattr(target_obj, owner_method)
                if callable(method):
                    is_owner = method(user)
                    if is_owner and user.has_perm(own_perm):
                        return True
            else:
                raise ValueError(
                    f"Object {target_obj.__class__.__name__} does not have method '{owner_method}'"
                )

        elif owner_field:
            # Convert single field to list for uniform processing
            owner_fields = (
                owner_field if isinstance(owner_field, list) else [owner_field]
            )

            # Check if user matches ANY of the owner fields
            for field in owner_fields:
                owner = getattr(target_obj, field, None)
                if owner == user:
                    if user.has_perm(own_perm):
                        return True
                    break

    return False


@register.simple_tag(takes_context=True)
def filter_actions_by_permission(context, actions, data):
    """
    Filter actions based on user permissions.
    Supports intermediate model lookups automatically.

    Args:
        context: Template context
        actions: List of action dicts
        data: The object being acted upon

    Returns:
        list: Filtered list of actions user has permission for
    """
    request = context.get("request")
    user = request.user if request else None

    if not user:
        return []

    filtered_actions = []

    for action in actions:
        action_context = {
            "user": user,
            "object": data,
        }

        # Handle intermediate model lookup automatically
        intermediate_model_name = action.get("intermediate_model")
        if intermediate_model_name:
            # Try to get the intermediate instance
            intermediate_obj = get_intermediate_instance(action, data, request)
            if intermediate_obj:
                action_context["intermediate_object"] = intermediate_obj

        # Check permission
        if has_action_permission(action, action_context):
            filtered_actions.append(action)

    return filtered_actions


@register.simple_tag(takes_context=True)
def has_any_actions_for_queryset(context, actions, queryset):
    """
    Check if any object in the queryset has at least one allowed action.
    Used to determine if the Actions column should be shown in the table header.
    Supports intermediate model permission checks automatically.

    Args:
        context: template context with request
        actions: list of action dicts
        queryset: queryset of objects to check

    Returns:
        bool: True if at least one object has at least one allowed action
    """
    request = context.get("request")
    user = request.user if request else None

    if not user:
        return False

    if not actions:
        return False

    for action in actions:
        perm = action.get("permission")
        if perm and user.has_perm(perm):
            return True

    sample_size = min(10, queryset.count())
    sample_queryset = queryset[:sample_size]

    for obj in sample_queryset:
        action_context = {"user": user, "object": obj}

        for action in actions:
            # Handle intermediate model lookup automatically
            intermediate_model_name = action.get("intermediate_model")
            if intermediate_model_name:
                intermediate_obj = get_intermediate_instance(action, obj, request)
                if intermediate_obj:
                    action_context["intermediate_object"] = intermediate_obj

            if has_action_permission(action, action_context):
                return True  # Found at least one allowed action

    return False


@register.filter
def join_attr(manager_or_queryset, attr_name):
    """
    Get an attribute from all related objects and join with ", ".
    Use in mail/notification templates to show all reverse-relation values:
    {{ instance.department_set|join_attr:'department_name' }}
    """
    if manager_or_queryset is None:
        return ""
    if not hasattr(manager_or_queryset, "all"):
        return ""
    try:
        values = []
        for obj in manager_or_queryset.all():
            val = getattr(obj, attr_name, None)
            if val is not None and str(val).strip():
                values.append(str(val))
        return ", ".join(values)
    except Exception:
        return ""


@register.filter
def wrap_in_list(value):
    """
    Wrap a dict in a list so it can be passed to filter_actions_by_permission.
    This allows reusing the same permission logic for col_attrs.

    Usage: {{ col_attrs_for_field|wrap_in_list }}
    """
    if isinstance(value, dict):
        return [value]
    return value


@register.simple_tag
def get_user_model_meta():
    """
    Get the User model metadata
    Returns: dict with app_label, model_name, and model_name_original
    """
    return {
        "app_label": User._meta.app_label,
        "model_name": User._meta.model_name,
        "model_class_name": User.__name__,
    }
