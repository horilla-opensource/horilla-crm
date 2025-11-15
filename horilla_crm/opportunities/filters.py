"""
Filters for the Opportunities module.

Provides filtering and search capabilities for Opportunity-related models
using HorillaFilterSet. Each filter class allows filtering all fields
(except 'additional_info') and provides specific search fields.
"""

from horilla_crm.opportunities.models import (
    BigDealAlert,
    DefaultOpportunityMember,
    Opportunity,
    OpportunityStage,
    OpportunityTeam,
)
from horilla_generics.filters import HorillaFilterSet


class OpportunityFilter(HorillaFilterSet):
    """Filter for Opportunity model with search on 'name'."""

    class Meta:
        """Meta options for OpportunityFilter."""

        model = Opportunity
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]


class OpportunityStageFilter(HorillaFilterSet):
    """Filter for OpportunityStage model with search on 'name'."""

    class Meta:
        """Meta options for OpportunityStageFilter."""

        model = OpportunityStage
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]


class OpportunityTeamFilter(HorillaFilterSet):
    """Filter for OpportunityTeam model with search on 'team_name'."""

    class Meta:
        """Meta options for OpportunityTeamFilter."""

        model = OpportunityTeam
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["team_name"]


class OpportunityTeamMembersFilter(HorillaFilterSet):
    """Filter for DefaultOpportunityMember model with search on user names."""

    class Meta:
        """Meta options for OpportunityTeamMembersFilter."""

        model = DefaultOpportunityMember
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["user__first_name", "user__last_name"]


class BigDealAlertFilter(HorillaFilterSet):
    """Filter for BigDealAlert model with search on 'alert_name'."""

    class Meta:
        """Meta options for BigDealAlertFilter."""

        model = BigDealAlert
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["alert_name"]
