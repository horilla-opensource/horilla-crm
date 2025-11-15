"""
Filters for the Accounts app.

This module defines filter classes used to search and filter Account records.
"""

from horilla_crm.accounts.models import Account
from horilla_generics.filters import HorillaFilterSet


# Define your accounts filters here
class AccountFilter(HorillaFilterSet):
    """
    Filter configuration for Account model.
    Allows searching and filtering on specific fields.
    """

    class Meta:
        """Filter options for the Account model."""

        model = Account
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
