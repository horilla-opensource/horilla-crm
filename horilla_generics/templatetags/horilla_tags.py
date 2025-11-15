import json as json_module
import re
from datetime import date, datetime, time
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django import template
from django.apps import apps
from django.db import models
from django.db.models import Manager, QuerySet
from django.forms import BaseForm
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import NoReverseMatch, resolve, reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

from horilla.menu.sub_section_menu import get_sub_section_menu
from horilla.registry.js_registry import get_registered_js
from horilla_core.models import MultipleCurrency
from horilla_core.utils import get_currency_display_value
from horilla_utils.middlewares import _thread_local

register = template.Library()


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

        # Obtain the request/user from thread-local (same as you used elsewhere)
        request = getattr(_thread_local, "request", None)
        user = (
            request.user
            if request and hasattr(request, "user") and request.user.is_authenticated
            else None
        )

        final_field_name = parts[-1] if parts else None

        if (
            parent is not None
            and hasattr(parent.__class__, "CURRENCY_FIELDS")
            and final_field_name in getattr(parent.__class__, "CURRENCY_FIELDS", [])
        ):

            return get_currency_display_value(parent, final_field_name, user)

        # --- Date/Time formatting ---
        if isinstance(current, datetime):
            date_time_format = "%Y-%m-%d %H:%M:%S"
            if user and getattr(user, "date_time_format", None):
                date_time_format = user.date_time_format
            if timezone.is_aware(current):
                current = timezone.localtime(current)
            return current.strftime(date_time_format)

        elif isinstance(current, date):
            date_format = "%Y-%m-%d"
            if user and getattr(user, "date_format", None):
                date_format = user.date_format
            return current.strftime(date_format)

        elif isinstance(current, time):
            time_format = "%I:%M:%S %p"
            if user and getattr(user, "time_format", None):
                time_format = user.time_format
            return current.strftime(time_format)

        elif isinstance(current, bool):
            return "Yes" if current else "No"

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
    attrs = format(action.get("attrs", ""), obj).strip()
    tooltip = action.get("action", "")

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
                <button {attrs} class='group relative w-10 h-7 bg-[#f0f0f0] flex-1 flex justify-center border-r border-r-[white] hover:bg-[#e0e0e0] transition duration-300 items-center'>
                    <img src="{static_url}" alt="{tooltip}" width="16" class="{image_class}" />
                    <div class="min-w-max z-40 absolute h-auto py-[3px] px-[15px] right-[40px] top-0 bg-[#000000] text-[.7rem] rounded-[5px] text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                        <p>{tooltip}</p>
                    </div>
                </button>
        """
        )

    elif "icon" in action:
        icon_name = action.get("icon", "")
        icon_class = action.get("icon_class", "")
        button_class = action.get("class", "")
        return mark_safe(
            f'<button class="w-10 h-7 bg-[#f0f0f0] flex-1 flex justify-center border-r border-r-[white] hover:bg-[#e0e0e0] transition duration-300 items-center" {attrs} title="{tooltip}">'
            f'<i class="{icon_name} {icon_class}"></i>'
            f"</button>"
        )

    else:
        button_class = action.get("class", "")
        return mark_safe(
            f'<button class="{button_class}" {attrs} title="{tooltip}">{tooltip}</button>'
        )


@register.filter
def getattribute(obj, attr):
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
    return json.dumps(value)


@register.filter
def lookup(dictionary, key):
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
        elif hasattr(field, "choices") and field.choices:
            display_method = getattr(obj, f"get_{field_name}_display", None)
            if display_method:
                return display_method()
            return str(value) if value else ""

        # Handle Boolean fields
        elif isinstance(field, models.BooleanField):
            if value is True:
                return "Yes"
            elif value is False:
                return "No"
            return ""

        # Handle Date/DateTime fields
        elif isinstance(field, models.DateTimeField):
            return value.strftime("%Y-%m-%d %H:%M") if value else ""
        elif isinstance(field, models.DateField):
            return value.strftime("%Y-%m-%d") if value else ""

        # Handle Decimal fields
        elif isinstance(field, models.DecimalField):
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
    except:
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
    except:
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
        except:
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
        except:
            return view_all_url
    return ""


@register.simple_tag
def safe_url(viewname, *args, **kwargs):
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
    except:
        return field_name.replace("_", " ").title()


def display_fk(value):
    if hasattr(value, "__str__"):
        return str(value)
    return value


numeric_test = re.compile(r"^\d+$")

date_format_mapping = {
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD.MM.YYYY": "%d.%m.%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MMMM D, YYYY": "%B %d, %Y",
    "DD MMMM, YYYY": "%d %B, %Y",
    "MMM. D, YYYY": "%b. %d, %Y",
    "D MMM. YYYY": "%d %b. %Y",
    "dddd, MMMM D, YYYY": "%A, %B %d, %Y",
}

time_format_mapping = {
    "hh:mm A": "%I:%M %p",
    "HH:mm": "%H:%M",
}


@register.filter(name="selected_format")
def selected_format(value, company=None) -> str:
    if not value:
        return ""

    if company and (company.date_format or company.time_format):
        if isinstance(value, date):
            fmt = company.date_format
            format_str = date_format_mapping.get(fmt, fmt)
            return value.strftime(format_str)
        elif isinstance(value, time):
            fmt = company.time_format
            format_str = time_format_mapping.get(fmt, fmt)
            return value.strftime(format_str)

    return value


@register.filter
def is_image_file(filename):
    """
    Django template filter to check if a given filename is an image file.
    """
    return filename.lower().endswith((".png", ".jpg", ".jpeg", ".svg"))


@register.filter
def to_json(value):
    return json_module.dumps(value, ensure_ascii=False)


@register.simple_tag
def render_field_with_name(form, field_name, row_id=None, selected_value=None):
    """
    Custom template tag to render form field with modified name and id attributes.
    Usage: {% render_field_with_name form field_name row_id selected_value %}
    """
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
    if not value:
        return value
    # Split by underscore, capitalize each word, and join with spaces
    return " ".join(word.capitalize() for word in value.split("_"))


@register.filter
def getter(obj, attr):
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
    Usage: {% has_perm "leads.view_lead" as can_view_leads %}
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
        else:
            return any(user.has_perm(perm) for perm in perms)

    return False


@register.simple_tag
def has_section_perm_url(user, section_name):
    """
    Check if the user can see at least one sub-item in a section.
    Returns the first accessible URL if permissions match.
    """
    if not user or not user.is_authenticated:
        return False

    sub_section_items = get_sub_section_menu().get(section_name, [])
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
def display_field_value(obj, field_name, user):
    """
    Template tag to display field value with automatic currency formatting

    Usage in template:
    {% display_field_value obj field_name request.user %}

    Works automatically if model has CURRENCY_FIELDS attribute
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

    # Handle choice fields automatically
    try:
        field = obj._meta.get_field(field_name)
        if hasattr(field, "choices") and field.choices:
            return dict(field.choices).get(value, value)
    except:
        pass

    # Handle foreign keys and relations
    if hasattr(value, "__str__"):
        return str(value)

    return value


@register.filter
def format_currency(value, user):
    """
    Template filter for currency formatting

    Usage: {{ opportunity.amount|format_currency:request.user }}
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
