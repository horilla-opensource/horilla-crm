# templatetags/forecast_filters.py
from django import template

register = template.Library()


@register.filter
def sum_amounts(opportunities):
    """
    Sum the amounts of all opportunities
    """
    if not opportunities:
        return 0

    total = 0
    for opp in opportunities:
        if hasattr(opp, "amount") and opp.amount:
            total += opp.amount

    return total
