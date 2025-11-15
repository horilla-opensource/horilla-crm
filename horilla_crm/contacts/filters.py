"""
Filters for the contacts app.

This module defines filter classes used to search and filter contact records.
"""

from horilla_generics.filters import HorillaFilterSet

from .models import Contact


class ContactFilter(HorillaFilterSet):
    """
    Filter class for contact model
    """

    class Meta:
        """Filter options for the Contact model."""

        model = Contact
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["first_name", "last_name", "email"]
