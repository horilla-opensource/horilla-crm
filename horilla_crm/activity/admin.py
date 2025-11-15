"""
Admin configuration for Activity models in Horilla CRM.
"""

from django.contrib import admin

from .models import Activity

# Register your activity models here.

admin.site.register(Activity)
