"""Admin configuration for the Campaign module."""

from django.contrib import admin

from .models import Campaign, CampaignMember

# Register your campaigns models here.

admin.site.register(Campaign)
admin.site.register(CampaignMember)
