from django import template

register = template.Library()


@register.filter(name="get_custom_fields")
def get_custom_fields(form):
    """Return bound fields whose name starts with 'cf_'."""
    cf_prefix = "cf_"
    result = []
    for name in form.fields:
        if name.startswith(cf_prefix):
            result.append(form[name])
    return result


@register.filter(name="has_custom_fields")
def has_custom_fields(form):
    """Return True if form has any custom fields."""
    return any(name.startswith("cf_") for name in form.fields)
