"""Signals to keep forecasts in sync with Opportunity changes."""

import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from horilla_core.models import HorillaUser, Period
from horilla_core.signals import company_currency_changed
from horilla_crm.forecast.models import Forecast, ForecastType
from horilla_crm.forecast.utils import ForecastCalculator
from horilla_crm.opportunities.models import Opportunity
from horilla_keys.models import ShortcutKey


@receiver(company_currency_changed)
def update_forecast_on_currency_change(sender, **kwargs):
    """
    Updates Forecast revenue amounts when a company's currency changes.
    """
    company = kwargs.get("company")
    conversion_rate = kwargs.get("conversion_rate")

    if not company or not conversion_rate:
        return

    forecasts_to_update = []

    revenue_fields = [
        "target_amount",
        "pipeline_amount",
        "best_case_amount",
        "commit_amount",
        "closed_amount",
        "actual_amount",
    ]

    forecasts = Forecast.objects.filter(owner__company=company).only(
        "id", *revenue_fields
    )

    for forecast in forecasts:
        needs_update = False

        for field in revenue_fields:
            value = getattr(forecast, field)
            if value is not None:
                setattr(forecast, field, value * conversion_rate)
                needs_update = True

        if needs_update:
            forecasts_to_update.append(forecast)

    if forecasts_to_update:
        Forecast.objects.bulk_update(
            forecasts_to_update,
            revenue_fields,
            batch_size=500,
        )


@receiver(pre_save, sender=Opportunity)
def track_opportunity_changes(sender, instance, **kwargs):
    """
    Track the old values before saving to handle all changes that affect forecasts
    """
    if instance.pk:  # Only for existing records
        try:
            old_instance = Opportunity.objects.get(pk=instance.pk)
            instance._old_owner = old_instance.owner
            instance._old_close_date = old_instance.close_date
            instance._old_amount = old_instance.amount
            instance._old_expected_revenue = old_instance.expected_revenue
            instance._old_forecast_category = old_instance.forecast_category
            instance._old_stage_type = (
                old_instance.stage.stage_type if old_instance.stage else None
            )
        except Opportunity.DoesNotExist:
            instance._old_owner = None
            instance._old_close_date = None
            instance._old_amount = None
            instance._old_expected_revenue = None
            instance._old_forecast_category = None
            instance._old_stage_type = None
    else:
        # New record - no old values
        instance._old_owner = None
        instance._old_close_date = None
        instance._old_amount = None
        instance._old_expected_revenue = None
        instance._old_forecast_category = None
        instance._old_stage_type = None


@receiver(post_save, sender=Opportunity)
def update_forecast_on_opportunity_save(sender, instance, created, **kwargs):
    """
    Automatically update forecasts when an opportunity is saved
    Handles all scenarios:
    1. New opportunity created
    2. Owner changed
    3. Close date changed (moved to different period)
    4. Amount/expected_revenue changed
    5. Forecast category changed
    6. Stage changed
    """

    try:
        owners_to_update = set()
        periods_to_update = {}  # {owner: set(periods)}

        # Scenario 1: New opportunity - update current owner's current period
        if created:
            if instance.owner and instance.close_date:
                owners_to_update.add(instance.owner)
                period = Period.objects.filter(
                    start_date__lte=instance.close_date,
                    end_date__gte=instance.close_date,
                ).first()
                if period:
                    if instance.owner not in periods_to_update:
                        periods_to_update[instance.owner] = set()
                    periods_to_update[instance.owner].add(period)

        # Scenario 2: Owner changed - update both old and new owner
        else:  # Existing record
            owner_changed = (
                hasattr(instance, "_old_owner")
                and instance._old_owner
                and instance._old_owner != instance.owner
            )

            if owner_changed:

                # Old owner - remove from their forecast
                if (
                    instance._old_owner
                    and hasattr(instance, "_old_close_date")
                    and instance._old_close_date
                ):
                    owners_to_update.add(instance._old_owner)
                    old_period = Period.objects.filter(
                        start_date__lte=instance._old_close_date,
                        end_date__gte=instance._old_close_date,
                    ).first()
                    if old_period:
                        if instance._old_owner not in periods_to_update:
                            periods_to_update[instance._old_owner] = set()
                        periods_to_update[instance._old_owner].add(old_period)

                # New owner - add to their forecast
                if instance.owner and instance.close_date:
                    owners_to_update.add(instance.owner)
                    new_period = Period.objects.filter(
                        start_date__lte=instance.close_date,
                        end_date__gte=instance.close_date,
                    ).first()
                    if new_period:
                        if instance.owner not in periods_to_update:
                            periods_to_update[instance.owner] = set()
                        periods_to_update[instance.owner].add(new_period)

            # Scenario 3: Close date changed - update both old and new period for same owner
            close_date_changed = (
                hasattr(instance, "_old_close_date")
                and instance._old_close_date
                and instance._old_close_date != instance.close_date
            )

            if close_date_changed and not owner_changed:

                if instance.owner:
                    owners_to_update.add(instance.owner)

                    # Old period
                    old_period = Period.objects.filter(
                        start_date__lte=instance._old_close_date,
                        end_date__gte=instance._old_close_date,
                    ).first()
                    if old_period:
                        if instance.owner not in periods_to_update:
                            periods_to_update[instance.owner] = set()
                        periods_to_update[instance.owner].add(old_period)

                    # New period
                    new_period = Period.objects.filter(
                        start_date__lte=instance.close_date,
                        end_date__gte=instance.close_date,
                    ).first()
                    if new_period:
                        if instance.owner not in periods_to_update:
                            periods_to_update[instance.owner] = set()
                        periods_to_update[instance.owner].add(new_period)

            # Scenario 4, 5, 6: Amount, category, or stage changed - update current owner/period
            value_changed = (
                (
                    hasattr(instance, "_old_amount")
                    and instance._old_amount != instance.amount
                )
                or (
                    hasattr(instance, "_old_expected_revenue")
                    and instance._old_expected_revenue != instance.expected_revenue
                )
                or (
                    hasattr(instance, "_old_forecast_category")
                    and instance._old_forecast_category != instance.forecast_category
                )
                or (
                    hasattr(instance, "_old_stage_type")
                    and instance.stage
                    and instance._old_stage_type != instance.stage.stage_type
                )
            )

            if value_changed and not owner_changed and not close_date_changed:
                if instance.owner and instance.close_date:
                    owners_to_update.add(instance.owner)
                    period = Period.objects.filter(
                        start_date__lte=instance.close_date,
                        end_date__gte=instance.close_date,
                    ).first()
                    if period:
                        if instance.owner not in periods_to_update:
                            periods_to_update[instance.owner] = set()
                        periods_to_update[instance.owner].add(period)

        # Update forecasts for all affected owners and periods
        if owners_to_update:
            for owner in owners_to_update:
                if owner in periods_to_update:
                    # Get fiscal year from one of the periods
                    sample_period = list(periods_to_update[owner])[0]
                    fiscal_year = sample_period.quarter.fiscal_year

                    calculator = ForecastCalculator(user=owner, fiscal_year=fiscal_year)

                    # Update specific periods or all periods for the fiscal year
                    for period in periods_to_update[owner]:
                        # Get all forecast types
                        forecast_types = ForecastType.objects.filter(is_active=True)
                        for forecast_type in forecast_types:
                            calculator.create_or_update_period_forecast(
                                owner, forecast_type, period
                            )
                else:
                    # Fallback - update all forecasts for user
                    period = Period.objects.filter(
                        start_date__lte=instance.close_date,
                        end_date__gte=instance.close_date,
                    ).first()
                    if period:
                        calculator = ForecastCalculator(
                            user=owner, fiscal_year=period.quarter.fiscal_year
                        )
                        calculator.generate_forecasts_for_user(owner)

    except AttributeError as e:
        logging.error("Error updating forecast on opportunity save: %s", e)
    except Exception as e:
        logging.error("Unexpected error updating forecast: %s", e)
    finally:
        # Clean up temporary attributes
        for attr in [
            "_old_owner",
            "_old_close_date",
            "_old_amount",
            "_old_expected_revenue",
            "_old_forecast_category",
            "_old_stage_type",
        ]:
            if hasattr(instance, attr):
                delattr(instance, attr)


@receiver(post_delete, sender=Opportunity)
def update_forecast_on_opportunity_delete(sender, instance, **kwargs):
    """
    Update forecasts when an opportunity is deleted
    Need to remove it from the owner's forecast
    """

    try:
        if instance.owner and instance.close_date:
            period = Period.objects.filter(
                start_date__lte=instance.close_date, end_date__gte=instance.close_date
            ).first()

            if period:
                calculator = ForecastCalculator(
                    user=instance.owner, fiscal_year=period.quarter.fiscal_year
                )

                # Update forecasts for the deleted opportunity's period
                forecast_types = ForecastType.objects.filter(is_active=True)
                for forecast_type in forecast_types:
                    calculator.create_or_update_period_forecast(
                        instance.owner, forecast_type, period
                    )

    except Exception as e:
        logging.error("Error updating forecast on opportunity delete: %s", e)


@receiver(post_save, sender=HorillaUser)
def create_forecast_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/forecast/forecast-view/", "key": "F", "command": "alt"},
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
