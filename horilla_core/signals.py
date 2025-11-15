"""
This module contains signal handlers and utility functions for Horilla's core
models such as Company, FiscalYear, MultipleCurrency, ScoringRule, and related
models.

Features implemented in this module include:
- Automatic fiscal year configuration when a company is created or updated.
- Default currency initialization and handling of multi-currency configurations.
- Custom permission creation during migrations (e.g., 'can_import', 'view_own').
- Dynamic scoring mechanism for CRM entities such as leads, opportunities, accounts, and contacts.
- Automatic recalculation of scores when scoring rules, criteria, or conditions change.
- Helper utilities to dynamically discover models and build filter queries.

This ensures automation, consistency, and configurable scoring logic across the Horilla ERP system.
"""

from decimal import Decimal
from venv import logger

from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import Case, F, IntegerField, Q, When
from django.db.models.signals import post_migrate, post_save, pre_delete
from django.dispatch import Signal, receiver

from horilla_core.models import (
    Company,
    FiscalYear,
    HorillaUser,
    MultipleCurrency,
    Role,
    ScoringCondition,
    ScoringCriterion,
    ScoringRule,
)
from horilla_core.services.fiscal_year_service import FiscalYearService
from horilla_keys.models import ShortcutKey
from horilla_utils.middlewares import _thread_local

company_currency_changed = Signal()


@receiver(post_save, sender="horilla_core.Company")
def create_company_fiscal_config(sender, instance, created, **kwargs):
    """
    Handle fiscal year configuration when a company is created
    """
    if created:
        try:
            config = FiscalYear.objects.get(company=instance)
        except FiscalYear.DoesNotExist:
            config = FiscalYearService.get_or_create_company_configuration(instance)

        # Generate fiscal years for this config
        FiscalYearService.generate_fiscal_years(config)


@receiver(post_save, sender="horilla_core.FiscalYear")
def generate_fiscal_years_on_config_save(sender, instance, created, **kwargs):
    """
    Generate fiscal years when configuration is saved.
    Uses transaction.on_commit to avoid database locking issues.
    """
    if not created and instance.company:  # Only run on updates, not creation
        transaction.on_commit(lambda: FiscalYearService.generate_fiscal_years(instance))


@receiver(post_save, sender=Company)
def create_default_currency(sender, instance, created, **kwargs):
    """
    Create default currency for new companies and update conversion rates.
    """
    if created and instance.currency:
        try:
            with transaction.atomic():
                if not MultipleCurrency.objects.filter(
                    company=instance, currency=instance.currency
                ).exists():
                    new_currency = MultipleCurrency.objects.create(
                        company=instance,
                        currency=instance.currency,
                        is_default=True,
                        conversion_rate=Decimal("1.00"),
                        decimal_places=2,
                        format="western_format",
                        created_at=instance.created_at,
                        updated_at=instance.updated_at,
                        created_by=instance.created_by,
                        updated_by=instance.updated_by,
                    )
                    all_currencies = MultipleCurrency.objects.filter(
                        company=instance
                    ).exclude(pk=new_currency.pk)
                    if all_currencies.exists():
                        for curr in all_currencies:
                            curr.is_default = False
                            curr.save()
        except Exception as e:
            logger.error(
                f"Error creating default currency for company {instance.id}: {str(e)}"
            )


def add_custom_permissions(sender, **kwargs):
    """
    Add custom permissions ('can_import' and 'view_own') for models
    that define default Django permissions.
    """
    for model in apps.get_models():
        opts = model._meta

        # Skip models that don't use default permissions
        if opts.default_permissions == ():
            continue

        content_type = ContentType.objects.get_for_model(model)

        add_import = (
            "can_import" in opts.default_permissions
            or opts.default_permissions == ("add", "change", "delete", "view")
        )

        add_view_own = (
            "view_own" in opts.default_permissions
            or opts.default_permissions == ("add", "change", "delete", "view")
        )

        custom_perms = []
        if add_import:
            custom_perms.append(("can_import", f"Can import {opts.verbose_name_raw}"))

        if add_view_own:
            custom_perms.append(("view_own", f"Can view own {opts.verbose_name_raw}"))

        for code_prefix, name in custom_perms:
            codename = f"{code_prefix}_{opts.model_name}"
            if not Permission.objects.filter(
                codename=codename, content_type=content_type
            ).exists():
                Permission.objects.create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )


post_migrate.connect(add_custom_permissions)


def get_score_field(model):
    score_fields = {
        "lead": "lead_score",
        "opportunity": "opportunity_score",
        "account": "account_score",
        "contact": "contact_score",
    }
    return score_fields.get(model._meta.model_name)


def get_models_for_module(module):
    """
    Dynamically find models matching a module name (e.g., 'lead') across installed apps.
    Only includes models that have a corresponding score field.
    """
    models = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if model._meta.model_name == module:
                score_field = get_score_field(model)
                if score_field and score_field in [f.name for f in model._meta.fields]:
                    models.append(model)
    return models


def build_query_from_conditions(criterion, Model):
    """
    Build a Django ORM query to filter instances that match a criterion's conditions.

    Args:
        criterion: ScoringCriterion instance.
        Model: The Django model class (e.g., Lead).

    Returns:
        Q object representing the combined conditions.
    """
    query = Q()
    for condition in criterion.conditions.all().order_by("order"):
        field = condition.field
        operator = condition.operator
        value = condition.value
        logical_operator = condition.logical_operator

        try:
            Model._meta.get_field(field)
            if operator == "equals":
                if Model._meta.get_field(field).get_internal_type() == "ForeignKey":
                    condition_query = Q(**{f"{field}_id__exact": value})
                else:
                    condition_query = Q(**{f"{field}__exact": value})
            elif operator == "not_equals":
                if Model._meta.get_field(field).get_internal_type() == "ForeignKey":
                    condition_query = ~Q(**{f"{field}_id__exact": value})
                else:
                    condition_query = ~Q(**{f"{field}__exact": value})
            elif operator == "contains":
                condition_query = Q(**{f"{field}__icontains": value})
            elif operator == "not_contains":
                condition_query = ~Q(**{f"{field}__icontains": value})
            elif operator == "starts_with":
                condition_query = Q(**{f"{field}__istartswith": value})
            elif operator == "ends_with":
                condition_query = Q(**{f"{field}__iendswith": value})
            elif operator == "greater_than":
                try:
                    condition_query = Q(**{f"{field}__gt": float(value)})
                except (ValueError, TypeError):
                    condition_query = Q(pk__in=[])
            elif operator == "greater_than_equal":
                try:
                    condition_query = Q(**{f"{field}__gte": float(value)})
                except (ValueError, TypeError):
                    condition_query = Q(pk__in=[])
            elif operator == "less_than":
                try:
                    condition_query = Q(**{f"{field}__lt": float(value)})
                except (ValueError, TypeError):
                    condition_query = Q(pk__in=[])
            elif operator == "less_than_equal":
                try:
                    condition_query = Q(**{f"{field}__lte": float(value)})
                except (ValueError, TypeError):
                    condition_query = Q(pk__in=[])
            elif operator == "is_empty":
                condition_query = Q(**{field: None}) | Q(**{f"{field}__exact": ""})
            elif operator == "is_not_empty":
                condition_query = ~Q(**{field: None}) & ~Q(**{f"{field}__exact": ""})
            else:
                logger.warning(f"Unsupported operator {operator} for field {field}")
                condition_query = Q(pk__in=[])
            if logical_operator == "and":
                query &= condition_query
            else:
                query |= condition_query
        except FieldDoesNotExist:
            logger.warning(f"Field {field} does not exist on {Model._meta.model_name}")
            query &= Q(pk__in=[])

    return query


def update_all_scores_for_module(module):
    """
    Update score fields for instances matching active scoring rules' conditions
    using direct database UPDATE queries.

    Args:
        module: String (e.g., 'lead', 'opportunity') indicating the module.
    """
    models = get_models_for_module(module)
    for Model in models:
        score_field = get_score_field(Model)
        if not score_field:
            continue

        with transaction.atomic():
            try:
                Model.objects.update(**{score_field: 0})
                logger.info(
                    f"Reset {score_field} to 0 for all {Model._meta.model_name} instances"
                )
            except Exception as e:
                logger.error(
                    f"Error resetting {score_field} for {Model._meta.model_name}: {e}"
                )
                raise

            rules = ScoringRule.objects.filter(module=module, is_active=True)
            if not rules.exists():
                continue

            for rule in rules:
                for criterion in rule.criteria.all().order_by("order"):
                    query = build_query_from_conditions(criterion, Model)
                    if not query:
                        continue

                    points = criterion.points
                    if criterion.operation_type == "sub":
                        points = -points

                    try:
                        Model.objects.filter(query).update(
                            **{
                                score_field: Case(
                                    When(query, then=F(score_field) + points),
                                    default=F(score_field),
                                    output_field=IntegerField(),
                                )
                            }
                        )
                        logger.info(
                            f"Updated {score_field} for {Model._meta.model_name} instances matching criterion {criterion.id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error updating {score_field} for {Model._meta.model_name} with criterion {criterion.id}: {e}"
                        )
                        raise


@receiver(post_save, sender=ScoringRule)
@receiver(pre_delete, sender=ScoringRule)
def handle_rule_change(sender, instance, **kwargs):
    """
    Signal handler triggered when a scoring rule is created, updated, or deleted.
    Automatically triggers recalculation of all scores for the associated module.
    """
    update_all_scores_for_module(instance.module)


@receiver(post_save, sender=ScoringCriterion)
@receiver(pre_delete, sender=ScoringCriterion)
def handle_criterion_change(sender, instance, **kwargs):
    """
    Signal handler triggered when a scoring criterion is created, updated, or deleted.
    Ensures scores are recalculated for all modules affected by this criterion.
    """
    update_all_scores_for_module(instance.rule.module)


@receiver(post_save, sender=ScoringCondition)
@receiver(pre_delete, sender=ScoringCondition)
def handle_condition_change(sender, instance, **kwargs):
    """
    Signal handler triggered when a scoring condition is created, updated, or deleted.
    Rebuilds and applies scoring rules to update scores for affected module instances.
    """
    update_all_scores_for_module(instance.criterion.rule.module)


@receiver(post_save, sender=HorillaUser)
def create_default_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/", "key": "H", "command": "alt"},
        {"page": "/my-profile-view/", "key": "P", "command": "alt"},
        {"page": "/regional-formating-view/", "key": "G", "command": "alt"},
        {"page": "/user-login-history-view/", "key": "L", "command": "alt"},
        {"page": "/user-holiday-view/", "key": "V", "command": "alt"},
        {"page": "/shortkeys/short-key-view/", "key": "K", "command": "alt"},
        {"page": "/user-view/", "key": "U", "command": "alt"},
        {"page": "/branches-view/", "key": "B", "command": "alt"},
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


@receiver(post_save, sender=HorillaUser)
def ensure_view_own_permissions(sender, instance, created, **kwargs):
    """
    Assign view_own permissions to newly created non-superuser users.
    """
    if not created or instance.is_superuser:
        return

    def assign_permissions():
        try:
            view_own_perms = Permission.objects.filter(codename__startswith="view_own_")
            if view_own_perms.exists():
                instance.user_permissions.add(*view_own_perms)
        except Exception as e:
            print(f"✗ Error assigning permissions to {instance.username}: {e}")

    transaction.on_commit(assign_permissions)


@receiver(post_save, sender=Role)
def ensure_role_view_own_permissions(sender, instance, created, **kwargs):
    """
    Assign view_own permissions to newly created or updated roles.
    Also assign these permissions to all members of the role.
    """

    def assign_permissions():
        try:
            view_own_perms = Permission.objects.filter(codename__startswith="view_own_")

            if not view_own_perms.exists():
                print(f"✗ No view_own permissions found")
                return

            existing_perm_ids = set(instance.permissions.values_list("id", flat=True))

            view_own_perm_ids = set(view_own_perms.values_list("id", flat=True))

            missing_perm_ids = view_own_perm_ids - existing_perm_ids

            if missing_perm_ids:
                missing_perms = Permission.objects.filter(id__in=missing_perm_ids)

                instance.permissions.add(*missing_perms)

                members = instance.users.all()
                for member in members:
                    member.user_permissions.add(*missing_perms)

                if created:
                    print(
                        f"✓ Assigned {len(missing_perm_ids)} view_own permissions to new role '{instance.role_name}'"
                    )
                else:
                    print(
                        f"✓ Updated {len(missing_perm_ids)} view_own permissions for role '{instance.role_name}'"
                    )

                if members.exists():
                    print(
                        f"  ✓ Updated {members.count()} members of role '{instance.role_name}'"
                    )

        except Exception as e:
            print(f"✗ Error assigning permissions to role '{instance.role_name}': {e}")

    transaction.on_commit(assign_permissions)
