"""Admin configuration for the leads app in Horilla CRM."""

from auditlog.models import LogEntry
from django.contrib import admin

from .models import EmailToLeadConfig, Lead, LeadStatus

admin.site.register(Lead)
admin.site.register(LeadStatus)
admin.site.unregister(LogEntry)
admin.site.register(EmailToLeadConfig)


@admin.register(LogEntry)
class CustomLogEntryAdmin(admin.ModelAdmin):
    """Custom admin for LogEntry to display relevant fields."""

    list_display = ("object_repr", "content_type", "action", "actor", "timestamp")
    list_filter = ("content_type", "action", "actor", "timestamp")
    search_fields = ("object_repr", "changes", "actor__username")
