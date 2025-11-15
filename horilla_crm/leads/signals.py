"""
Signal handlers for leads in Horilla CRM.
Handles automatic updates when company-related events occur, e.g., currency change.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from horilla_core.models import HorillaUser
from horilla_core.signals import company_currency_changed
from horilla_crm.leads.models import Lead
from horilla_keys.models import ShortcutKey

# Define your leads signals here

# @receiver(post_save, sender=Company)
# def create_default_lead_stages(sender, instance, created, **kwargs):
#     """
#     Automatically create default lead stages for a company when it is created.
#     """
#     if created:
#         default_stages = [
#             {"name": "New", "order": 1,  "probability": 10, "is_final": False},
#             {"name": "Contacted", "order": 2, "probability": 30, "is_final": False},
#             {"name": "Qualified", "order": 3, "probability": 60, "is_final": False},
#             {"name": "Proposal", "order": 4,  "probability": 80, "is_final": False},
#             {"name": "Lost", "order": 5, "probability": 0, "is_final": False},
#             {"name": "Won", "order": 6,  "probability": 100, "is_final": True},
#         ]

#         for stage in default_stages:
#             LeadStatus.objects.create(
#                 company=instance,
#                 name=stage["name"],
#                 order=stage["order"],
#                 probability=stage["probability"],
#                 is_final=stage["is_final"],
#             )


@receiver(company_currency_changed)
def update_crm_on_currency_change(sender, **kwargs):
    """
    Updates Lead amounts when a company's currency changes.
    """
    company = kwargs.get("company")
    conversion_rate = kwargs.get("conversion_rate")

    leads_to_update = []
    leads = (
        Lead.objects.filter(company=company)
        .select_related()
        .only("id", "annual_revenue")
    )

    for lead in leads:
        if lead.annual_revenue is not None:
            lead.annual_revenue = lead.annual_revenue * conversion_rate
            leads_to_update.append(lead)

    if leads_to_update:
        Lead.objects.bulk_update(leads_to_update, ["annual_revenue"], batch_size=1000)


@receiver(post_save, sender=HorillaUser)
def create_leads_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/leads/leads-view/", "key": "E", "command": "alt"},
    ]

    for item in predefined:
        if not ShortcutKey.objects.filter(user=instance, page=item["page"]).exists():
            ShortcutKey.objects.create(
                user=instance,
                page=item["page"],
                key=item["key"],
                command=item["command"],
                company=instance.company,
            )
