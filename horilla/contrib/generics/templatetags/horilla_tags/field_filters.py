"""Template filters for object/field lookups, formatting, and model helpers."""

# Standard library imports
import json as json_module
import re

# Third-party imports (Django)
from django.forms import BaseForm
from django.forms import ImageField as FormImageField
from django.templatetags.static import static
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

from horilla.apps import apps
from horilla.contrib.core.utils import get_currency_display_value

# First party imports (Horilla)
from horilla.db import models
from horilla.db.models import Manager, QuerySet
from horilla.urls import reverse
from horilla.utils.html import escape, format_html
from horilla.utils.translation import gettext_lazy as _

# Local imports
from ._registry import register
from ._shared import _get_request_user_company, display_fk, format_datetime_value


def _format_string(string, instance):
    """Format a string by replacing {attr} placeholders with instance attributes."""
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
            parent = current
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
def format_filter(string: str, instance: object):
    """
    Formats a string by replacing placeholders with attributes from an instance
    get methods from model.
    """
    return _format_string(string, instance)


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
def is_image_field(field):
    """Return True if the bound field's underlying Field is a Django ImageField."""
    return isinstance(getattr(field, "field", field), FormImageField)


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

    If `disabled_if` is a callable that returns True for the given obj, the
    button is rendered as disabled (grayed out, no HTMX attrs).
    """
    hidden_if = action.get("hidden_if")
    if callable(hidden_if) and hidden_if(obj):
        return mark_safe("")

    disabled_if = action.get("disabled_if")
    is_disabled = callable(disabled_if) and disabled_if(obj)

    if is_disabled:
        attrs = ""
        disabled_attr = mark_safe("disabled")
        disabled_classes = "opacity-50 cursor-not-allowed"
        fallback = action.get("action", "")
        if callable(fallback):
            fallback = fallback(obj)
        tooltip = _(action.get("disabled_title", fallback))
    else:
        attrs = _format_string(action.get("attrs", ""), obj).strip()
        disabled_attr = mark_safe("")
        disabled_classes = ""
        action_label = action.get("action", "")
        if callable(action_label):
            action_label = action_label(obj)
        tooltip = _(action_label)

    if "src" in action:
        img_class = action.get("img_class", "")
        src = action.get("src", "")
        if callable(src):
            src = src(obj)
        static_url = static(src)
        classes = img_class.split()
        size_classes = [c for c in classes if c.startswith("w-") or c.startswith("h-")]
        other_classes = [c for c in classes if c not in size_classes]
        image_class = " ".join(other_classes)

        # action_tooltip.js reads title for pill text (fixed; not clipped by overflow-hidden)
        return format_html(
            "<button {} {} class='w-10 h-7 bg-dark-25 flex-1 flex justify-center border-r border-r-[white] hover:bg-dark-50 transition duration-300 items-center {}' title='{}' aria-label='{}'>"
            '<img src="{}" alt="" width="16" class="{}" />'
            "</button>",
            mark_safe(attrs),
            disabled_attr,
            disabled_classes,
            escape(tooltip),
            escape(tooltip),
            escape(static_url),
            escape(image_class),
        )

    if "icon" in action:
        icon_name = action.get("icon", "")
        icon_class = action.get("icon_class", "")
        return format_html(
            '<button class="w-10 h-7 bg-dark-25 flex-1 flex justify-center border-r border-r-[white] hover:bg-dark-50 transition duration-300 items-center {}" aria-label="{}" {} {} title="{}">'
            '<i class="{} {}"></i>'
            "</button>",
            disabled_classes,
            escape(tooltip),
            mark_safe(attrs),
            disabled_attr,
            escape(tooltip),
            escape(icon_name),
            escape(icon_class),
        )

    button_class = action.get("class", "")
    return format_html(
        '<button class="{} {}" {} {} title="{}">{}</button>',
        escape(button_class),
        disabled_classes,
        mark_safe(attrs),
        disabled_attr,
        escape(tooltip),
        escape(tooltip),
    )


@register.filter
def getattribute(obj, attr):
    """Return attribute value from `obj` or empty string if missing."""
    return getattr(obj, attr, "")


@register.filter
def has_value(query_dict, key):
    """Returns True if the key exists in query_dict and has a non-empty value."""
    return bool(query_dict.get(key, ""))


@register.filter
def get_range(value):
    """Generate a range from 1 to value. Usage: {% for i in total_steps|get_range %}"""
    return range(1, int(value) + 1)


@register.filter
def get_fields_for_step(form, step):
    """Returns form fields for the given step"""
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
    return json_module.dumps(value)


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

        if hasattr(field, "choices") and field.choices:
            display_method = getattr(obj, f"get_{field_name}_display", None)
            if display_method:
                return display_method()
            return str(value) if value else ""

        if isinstance(field, models.BooleanField):
            if value is True:
                return "Yes"
            if value is False:
                return "No"
            return ""

        if getattr(field, "get_internal_type", lambda: "")() == "JSONField":
            if value is None:
                return ""
            if isinstance(value, (list, tuple)):
                return ", ".join(
                    str(v).strip() for v in value if v is not None and str(v).strip()
                )
            if isinstance(value, dict):
                if not value:
                    return ""
                return ", ".join(f"{k}: {v}" for k, v in value.items())
            return str(value)

        if isinstance(field, models.DateTimeField):
            return value.strftime("%Y-%m-%d %H:%M") if value else ""
        if isinstance(field, models.DateField):
            return value.strftime("%Y-%m-%d") if value else ""

        if isinstance(field, models.DecimalField):
            return f"{value:.2f}" if value is not None else ""

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
    """Get related objects for a field"""
    try:
        related_manager = getattr(obj, field_name)
        if hasattr(related_manager, "all"):
            return related_manager.all()
        return []
    except Exception:
        return []


@register.filter
def model_name(obj):
    """Get model name from object"""
    return obj.__class__.__name__


@register.filter
def model_verbose_name(obj):
    """Get model verbose name"""
    return obj._meta.verbose_name


@register.filter
def model_verbose_name_plural(obj):
    """Get model verbose name plural"""
    return obj._meta.verbose_name_plural


@register.simple_tag
def get_field_display(obj, field_name):
    """Get display value for any field type"""
    try:
        field = obj._meta.get_field(field_name)
        value = getattr(obj, field_name)

        if hasattr(field, "choices") and field.choices:
            display_method = getattr(obj, f"get_{field_name}_display", None)
            if display_method:
                return display_method()

        if isinstance(field, models.ForeignKey) and value:
            return display_fk(value)

        if isinstance(field, models.DateTimeField) and value:
            return value.strftime("%d/%m/%Y %H:%M")

        if isinstance(field, models.DateField) and value:
            return value.strftime("%d/%m/%Y")

        return str(value) if value is not None else ""
    except Exception:
        return str(getattr(obj, field_name, ""))


@register.filter
def can_add_related(related_list, obj):
    """Check if user can add related objects"""
    return related_list.get("can_add", True)


@register.filter
def get_add_url(obj, related_list):
    """Get URL for adding new related object"""
    add_url = related_list.get("add_url", "")
    if add_url:
        try:
            return reverse(add_url)
        except Exception:
            return str(add_url)
    return ""


@register.filter
def get_view_all_url(obj, related_list):
    """Get URL for viewing all related objects"""
    view_all_url = related_list.get("view_all_url", "")
    if view_all_url:
        try:
            return reverse(view_all_url) + f"?{obj._meta.model_name}={obj.pk}"
        except Exception:
            return view_all_url
    return ""


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


@register.filter
def is_image_file(filename):
    """Django template filter to check if a given filename is an image file."""
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
    if field_name == "value" and row_id is not None:
        value_widget_html_key = f"value_widget_html_{row_id}"
        value_widget_html = context.get(value_widget_html_key)
        if value_widget_html:
            return mark_safe(value_widget_html)
        if not form or field_name not in form.fields:
            return format_html(
                '<input type="text" '
                'name="value_{}" '
                'id="id_value_{}" '
                'class="text-color-820 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600" '
                'placeholder="{}" '
                'value="{}">',
                row_id,
                row_id,
                _("Enter Value"),
                selected_value or "",
                row_id,
                row_id,
            )

    if form and field_name in form.fields:
        field = form[field_name]
        field_html = str(field)

        if row_id:
            safe_name = escape(field_name)
            safe_row_id = escape(str(row_id))
            field_html = field_html.replace(
                f'name="{field_name}"',
                format_html('name="{}_{}"', safe_name, safe_row_id),
            )

            field_html = re.sub(
                rf'id="id_{re.escape(field_name)}(_\d*)?"',
                f'id="id_{safe_name}_{safe_row_id}"',
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

                safe_value = escape(str(selected_value))
                field_html = re.sub(r' value="[^"]*"', "", field_html)
                field_html = re.sub(
                    r"(<input[^>]*?)>",
                    format_html(r'\1 value="{}">', safe_value),
                    field_html,
                )

        return format_html("{}", mark_safe(field_html))

    return ""


@register.filter
def humanize_field_name(value):
    """Convert an underscored field name into a human-readable title."""
    if not value:
        return value
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
        return field.verbose_name
    except Exception:
        field_name = getattr(component_or_condition, "field", model_name_or_field_name)
        return field_name.replace("_", " ").title()


@register.filter
def get_field_permission(field_permissions, field_name):
    """
    Get field permission from the permissions dict
    Returns the permission type or 'readwrite' as default
    """
    if not field_permissions:
        return "readwrite"
    return field_permissions.get(field_name, "readwrite")


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
