"""
Signal handlers for Opportunities in Horilla CRM.
Handles automatic updates when company-related events occur, e.g., currency change.
"""

import threading
from decimal import Decimal

from django.apps import apps
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from horilla_core.models import HorillaUser
from horilla_core.signals import company_currency_changed
from horilla_crm.opportunities.models import (
    Opportunity,
    OpportunityContactRole,
    OpportunitySettings,
    OpportunitySplit,
    OpportunitySplitType,
    OpportunityTeamMember,
)
from horilla_keys.models import ShortcutKey

_thread_locals = threading.local()


@receiver(company_currency_changed)
def update_crm_on_currency_change(sender, **kwargs):
    """
    Updates Opportunity amounts when a company's currency changes.
    """
    company = kwargs.get("company")
    conversion_rate = kwargs.get("conversion_rate")

    opportunities_to_update = []
    opportunities = (
        Opportunity.objects.filter(company=company)
        .select_related()
        .only("id", "amount", "expected_revenue")
    )

    for opportunity in opportunities:
        needs_update = False

        if opportunity.amount is not None:
            opportunity.amount = opportunity.amount * conversion_rate
            needs_update = True

        if opportunity.expected_revenue is not None:
            opportunity.expected_revenue = (
                opportunity.expected_revenue * conversion_rate
            )
            needs_update = True

        if needs_update:
            opportunities_to_update.append(opportunity)

    if opportunities_to_update:
        Opportunity.objects.bulk_update(
            opportunities_to_update,
            ["amount", "expected_revenue"],
            batch_size=1000,
        )


@receiver(post_save, sender=HorillaUser)
def create_opportunity_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/opportunities/opportunities-view/", "key": "O", "command": "alt"},
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


@receiver(pre_save, sender=Opportunity)
def track_owner_change(sender, instance, **kwargs):
    """
    Track owner changes before save to handle updates properly.
    Store old owner in instance for comparison in post_save.
    """
    if instance.pk:
        try:
            old_instance = Opportunity.objects.get(pk=instance.pk)
            instance._old_owner_id = old_instance.owner_id
        except Opportunity.DoesNotExist:
            instance._old_owner_id = None
    else:
        instance._old_owner_id = None


@receiver(post_save, sender=Opportunity)
def sync_opportunity_owner(sender, instance, created, **kwargs):
    """
    Signal handler to sync opportunity owner to team members and splits.
    This runs after the opportunity is saved.
    """
    # Only proceed if team selling is enabled
    if not OpportunitySettings.is_team_selling_enabled(instance.company):
        return

    # Get old and new owner
    old_owner_id = getattr(instance, "_old_owner_id", None)
    new_owner = instance.owner
    owner_changed = old_owner_id and old_owner_id != new_owner.id

    # Create/update team member for new owner
    team_member, tm_created = OpportunityTeamMember.objects.update_or_create(
        opportunity=instance,
        user=new_owner,
        defaults={
            "team_role": "Opportunity Owner",
            "opportunity_access": "Read/Write",
            "company": instance.company,
        },
    )

    # Handle splits if enabled
    if not OpportunitySettings.is_split_enabled(instance.company):
        return

    # Get active revenue split types (totals_100_percent=True)
    revenue_split_types = OpportunitySplitType.objects.filter(
        company=instance.company, is_active=True, totals_100_percent=True
    )

    for split_type in revenue_split_types:
        # Check if new owner has a split
        existing_split = OpportunitySplit.objects.filter(
            opportunity=instance, user=new_owner, split_type=split_type
        ).first()

        if not existing_split:
            if owner_changed:
                # Owner changed - create new owner with 0% and 0 amount
                OpportunitySplit.objects.create(
                    opportunity=instance,
                    user=new_owner,
                    split_type=split_type,
                    split_percentage=Decimal("0"),
                    split_amount=Decimal("0"),
                    company=instance.company,
                )
            else:
                # New opportunity or owner not changed - give remaining percentage
                # Calculate remaining percentage
                total_percentage = OpportunitySplit.objects.filter(
                    opportunity=instance, split_type=split_type
                ).exclude(user=new_owner).aggregate(
                    total=models.Sum("split_percentage")
                )[
                    "total"
                ] or Decimal(
                    "0"
                )

                if total_percentage < Decimal("100"):
                    remaining_percentage = Decimal("100") - total_percentage

                    # Get the field value to split
                    split_field_value = getattr(
                        instance, split_type.split_field
                    ) or Decimal("0")
                    split_amount = (
                        split_field_value * remaining_percentage / Decimal("100")
                    )

                    OpportunitySplit.objects.create(
                        opportunity=instance,
                        user=new_owner,
                        split_type=split_type,
                        split_percentage=remaining_percentage,
                        split_amount=split_amount,
                        company=instance.company,
                    )
                elif total_percentage == Decimal("0"):
                    # No splits exist yet, create 100% for owner
                    split_field_value = getattr(
                        instance, split_type.split_field
                    ) or Decimal("0")

                    OpportunitySplit.objects.create(
                        opportunity=instance,
                        user=new_owner,
                        split_type=split_type,
                        split_percentage=Decimal("100"),
                        split_amount=split_field_value,
                        company=instance.company,
                    )


def set_opportunity_contact_id(contact_id, company):
    """Store contact_id in thread-local storage"""
    _thread_locals.opportunity_contact_id = contact_id
    _thread_locals.opportunity_company = company


def get_and_clear_opportunity_contact_id():
    """Get and clear contact_id from thread-local storage"""
    contact_id = getattr(_thread_locals, "opportunity_contact_id", None)
    company = getattr(_thread_locals, "opportunity_company", None)

    if hasattr(_thread_locals, "opportunity_contact_id"):
        delattr(_thread_locals, "opportunity_contact_id")
    if hasattr(_thread_locals, "opportunity_company"):
        delattr(_thread_locals, "opportunity_company")

    return contact_id, company


@receiver(post_save, sender=Opportunity)
def create_opportunity_contact_role(sender, instance, created, **kwargs):
    """
    Automatically create OpportunityContactRole when an Opportunity is created.
    """
    if created:
        contact_id, company = get_and_clear_opportunity_contact_id()

        if contact_id is not None:
            Contact = apps.get_model("contacts", "Contact")
            try:
                contact = Contact.objects.get(pk=contact_id)

                role, created_role = OpportunityContactRole.objects.get_or_create(
                    contact=contact,
                    opportunity=instance,
                    company=company or getattr(instance, "company", None),
                )
            except Contact.DoesNotExist:
                print(f"Contact with id {contact_id} does not exist")
