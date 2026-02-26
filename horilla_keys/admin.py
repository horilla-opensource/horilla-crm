"""
Admin registration for the horilla_keys app
"""

from django.contrib import admin

from .models import ShortcutKey

# Register your horilla_keys models here.

admin.site.register(ShortcutKey)
