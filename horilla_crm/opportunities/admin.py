"""Django admin configuration for opportunities app."""

from django.contrib import admin

from horilla_crm.opportunities.models import (
    BigDealAlert,
    DefaultOpportunityMember,
    Opportunity,
    OpportunityContactRole,
    OpportunitySettings,
    OpportunitySplitType,
    OpportunityStage,
    OpportunityTeam,
    OpportunityTeamMember,
)

admin.site.register(Opportunity)
admin.site.register(OpportunityStage)
admin.site.register(OpportunityContactRole)
admin.site.register(OpportunityTeamMember)
admin.site.register(BigDealAlert)
admin.site.register(DefaultOpportunityMember)
admin.site.register(OpportunityTeam)
admin.site.register(OpportunitySettings)
admin.site.register(OpportunitySplitType)
