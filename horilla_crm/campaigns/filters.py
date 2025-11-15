"""
Defines filters for the Campaign model, enabling search and exclusion of specific fields.
"""

from horilla_generics.filters import HorillaFilterSet

from .models import Campaign


class CampaignFilter(HorillaFilterSet):
    """
    Campaign Filter
    """

    class Meta:
        """
        Meta class for CampaignFilter
        """

        model = Campaign
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["campaign_name"]
