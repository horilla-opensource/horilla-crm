"""Django admin configuration for contacts app."""

from django.contrib import admin

from .models import Contact, ContactAccountRelationship

admin.site.register(Contact)
admin.site.register(ContactAccountRelationship)
