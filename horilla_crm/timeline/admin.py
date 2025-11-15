"""Admin configuration for timeline app."""

from django.contrib import admin

from .models import UserAvailability, UserCalendarPreference

admin.site.register(UserCalendarPreference)
admin.site.register(UserAvailability)
