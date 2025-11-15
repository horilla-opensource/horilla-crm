"""Django admin configuration for accounts app."""

from django.contrib import admin

from horilla_crm.accounts.models import Account, PartnerAccountRelationship

# Register your accounts models here.
admin.site.register(Account)
admin.site.register(PartnerAccountRelationship)
