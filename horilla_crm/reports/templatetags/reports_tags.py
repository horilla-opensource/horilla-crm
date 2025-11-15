from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary using key."""
    if not dictionary or not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter
def dict_sum(value):
    """Sum the values in a dictionary."""
    if not value or not isinstance(value, dict):
        return 0
    return sum(
        v for v in value.values() if v is not None and isinstance(v, (int, float))
    )


@register.filter
def column_sum(pivot_table, column):
    """Sum the values for a specific column across all rows."""
    if not pivot_table or not isinstance(pivot_table, dict):
        return 0
    total = 0
    for row in pivot_table.values():
        if row and isinstance(row, dict):
            value = row.get(column, 0)
            if isinstance(value, (int, float)):
                total += value
    return total


@register.filter
def total_sum(pivot_table):
    """Sum all values in the pivot table."""
    if not pivot_table or not isinstance(pivot_table, dict):
        return 0
    return sum(dict_sum(row) for row in pivot_table.values() if row)


@register.filter
def get_column_subtotal(group_items, column_name):
    """Calculate subtotal for a specific column within a group"""
    total = 0
    for item in group_items:
        if isinstance(item, dict):
            values = item.get("values", {})
            if isinstance(values, dict):
                value = values.get(column_name, 0)
                if isinstance(value, (int, float)):
                    total += value
    return total


@register.filter
def get_grand_column_total(hierarchical_data, column_name):
    """Calculate grand total for a specific column across all groups"""
    total = 0
    if isinstance(hierarchical_data, dict):
        groups = hierarchical_data.get("groups", [])
        for group in groups:
            if isinstance(group, dict):
                items = group.get("items", [])
                total += get_column_subtotal(items, column_name)
    return total


@register.filter
def zip_lists(value, arg):
    """
    Zip two iterables together for use in template loops.
    """
    if not hasattr(value, "__iter__") or not hasattr(arg, "__iter__"):
        return []
    return list(zip(value, arg))


@register.filter
def attr(obj, attr_name):
    """Dynamically access an attribute of an object by name."""
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        return None


@register.filter
def split(value, delimiter):
    """Split a string by delimiter."""
    if not value:
        return []
    return str(value).split(delimiter)


@register.filter
def mul(value, multiplier):
    """Multiply a value by a multiplier."""
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0


@register.filter
def add(value, arg):
    """Add arg to value."""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def divide(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage of value from total."""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.filter
def format_number(value, decimal_places=2):
    """Format number with specified decimal places."""
    try:
        return floatformat(float(value), decimal_places)
    except (ValueError, TypeError):
        return value


@register.filter
def is_first(value, loop_info):
    """Check if this is the first item in a loop."""
    return getattr(loop_info, "first", False)


@register.filter
def is_last(value, loop_info):
    """Check if this is the last item in a loop."""
    return getattr(loop_info, "last", False)


@register.filter
def get_level1_rowspan(level1_group):
    """Calculate rowspan for level 1 group in 3-level hierarchy."""
    if not isinstance(level1_group, dict):
        return 1

    level2_groups = level1_group.get("level2_groups", [])
    total_rows = 0

    for level2_group in level2_groups:
        if isinstance(level2_group, dict):
            level3_items = level2_group.get("level3_items", [])
            total_rows += len(level3_items) + 1  # +1 for level2 subtotal

    return total_rows + 1  # +1 for level1 total


@register.filter
def get_level2_rowspan(level2_group):
    """Calculate rowspan for level 2 group in 3-level hierarchy."""
    if not isinstance(level2_group, dict):
        return 1

    level3_items = level2_group.get("level3_items", [])
    return len(level3_items)


@register.filter
def count_items_in_group(group):
    """Count total items in a hierarchical group."""
    if not isinstance(group, dict):
        return 0

    items = group.get("items", [])
    return len(items)


@register.filter
def group_by_level1(column_hierarchy):
    """Group column hierarchy by level 1."""
    if not column_hierarchy:
        return []

    grouped = {}
    for item in column_hierarchy:
        if isinstance(item, dict):
            level1 = item.get("level1")
            if level1 not in grouped:
                grouped[level1] = []
            grouped[level1].append(item)

    return [{"grouper": k, "list": v} for k, v in grouped.items()]


@register.filter
def get_colspan(level1_items):
    """Get colspan for level 1 header."""
    return len(level1_items) if level1_items else 1


@register.simple_tag
def calculate_three_level_rowspan(
    level1_group, current_level2_index, current_level3_index
):
    """Calculate rowspan for three-level hierarchy."""
    if current_level2_index == 0 and current_level3_index == 0:
        # This is the first item in level1 group
        total_items = 0
        level2_groups = level1_group.get("level2_groups", [])
        for level2_group in level2_groups:
            level3_items = level2_group.get("level3_items", [])
            total_items += len(level3_items) + 1  # +1 for subtotal row
        return total_items + 1  # +1 for grand total row
    return None


@register.simple_tag
def calculate_level2_rowspan(level2_group, current_level3_index):
    """Calculate rowspan for level 2 in three-level hierarchy."""
    if current_level3_index == 0:
        level3_items = level2_group.get("level3_items", [])
        return len(level3_items)
    return None


@register.filter
def default_if_none(value, default):
    """Return default if value is None."""
    return default if value is None else value


@register.filter
def safe_int(value):
    """Safely convert value to int."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


@register.filter
def safe_float(value):
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


@register.filter
def display_value(value):
    """Display value with proper formatting."""
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        if value == 0:
            return "0"
        return floatformat(value, 2) if value != int(value) else str(int(value))
    return str(value)


@register.filter
def is_numeric(value):
    """Check if value is numeric."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


@register.filter
def sum_list(value_list):
    """Sum a list of values."""
    if not value_list:
        return 0
    total = 0
    for value in value_list:
        if isinstance(value, (int, float)):
            total += value
    return total


# @register.filter
# def zip_lists(value, arg):
#     """
#     Zip two iterables together for use in template loops.
#     """
#     if not hasattr(value, '__iter__') or not hasattr(arg, '__iter__'):
#         return []
#     return list(zip(value, arg))


@register.filter
def in_list(value, arg):
    """Check if a value is in a comma-separated list."""
    return value in arg.split(",")


@register.filter
def get_field_verbose_name(field_name, model_class):
    """Get verbose name for a field"""
    try:
        field = model_class._meta.get_field(field_name)
        return field.verbose_name.title()
    except:
        return field_name.replace("_", " ").title()


@register.filter
def total_sum_excluding_aggregate(pivot_table, aggregate_column_name):
    total = 0
    for row, values in pivot_table.items():
        total += values.get("total", 0)  # Use precomputed total
    return total


@register.filter
def sum_aggregate(items, aggregate_column_name):
    """
    Compute aggregate for a list of items based on aggregate_column.function.
    """
    if not items or not aggregate_column_name:
        return "-"
    # Assuming items is a list of objects with an 'aggregate' field
    # and aggregate_column is passed from the context with 'function'
    aggregate_column = items[0].get("aggregate_column", {}) if items else {}
    agg_func = (
        aggregate_column.get("function", "sum")
        if isinstance(aggregate_column, dict)
        else "sum"
    )

    values = [item.aggregate for item in items if item.aggregate is not None]
    if not values:
        return "-"

    if agg_func == "sum":
        return sum(values)
    elif agg_func == "max":
        return max(values)
    elif agg_func == "min":
        return min(values)
    elif agg_func == "count":
        return len(values)
    return "-"


@register.filter
def sum_level2_aggregate(level2_groups, aggregate_column_name):
    """
    Compute aggregate for level 2 groups.
    """
    if not level2_groups or not aggregate_column_name:
        return "-"
    aggregate_column = (
        level2_groups[0].get("aggregate_column", {}) if level2_groups else {}
    )
    agg_func = (
        aggregate_column.get("function", "sum")
        if isinstance(aggregate_column, dict)
        else "sum"
    )

    values = []
    for group in level2_groups:
        for item in group.level3_items:
            if item.aggregate is not None:
                values.append(item.aggregate)

    if not values:
        return "-"

    if agg_func == "sum":
        return sum(values)
    elif agg_func == "max":
        return max(values)
    elif agg_func == "min":
        return min(values)
    elif agg_func == "count":
        return len(values)
    return "-"


@register.filter
def sum_level1_aggregate(level1_groups, aggregate_column_name):
    """
    Compute aggregate for level 1 groups.
    """
    if not level1_groups or not aggregate_column_name:
        return "-"
    aggregate_column = (
        level1_groups[0].get("aggregate_column", {}) if level1_groups else {}
    )
    agg_func = (
        aggregate_column.get("function", "sum")
        if isinstance(aggregate_column, dict)
        else "sum"
    )

    values = []
    for group in level1_groups:
        for level2_group in group.level2_groups:
            for item in level2_group.level3_items:
                if item.aggregate is not None:
                    values.append(item.aggregate)

    if not values:
        return "-"

    if agg_func == "sum":
        return sum(values)
    elif agg_func == "max":
        return max(values)
    elif agg_func == "min":
        return min(values)
    elif agg_func == "count":
        return len(values)
    return "-"


@register.filter
def aggregate_names(aggregate_columns):
    return [agg["name"] for agg in aggregate_columns]


@register.filter
def is_choice_or_foreign(report, field_name):
    return report.is_choice_or_foreign_key_field(field_name)


@register.filter
def get_field_choices(report, field_name):
    return report.get_field_choices(field_name)
