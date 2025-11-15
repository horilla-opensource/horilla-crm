import json
import logging

from dateutil.parser import parse
from django.apps import apps
from django.db import models, transaction
from django.db.models import QuerySet

from horilla_core.models import MultipleCurrency, RecycleBin, ScoringRule

logger = logging.getLogger(__name__)


def restore_recycle_bin_records(request, recycle_objs):
    """
    Restore one or more RecycleBin records to their original models using the exact logic from RecycleRestoreView.

    Args:
        request: The Django request object for messaging.
        recycle_objs: A single RecycleBin object, a QuerySet, or a list of RecycleBin objects.

    Returns:
        tuple: (restored_count, failed_records)
            - restored_count: Number of successfully restored records.
            - failed_records: List of strings describing failed restorations.
    """
    from multiselectfield.db.fields import MultiSelectField  # Add this import

    restored_count = 0
    failed_records = []

    if isinstance(recycle_objs, QuerySet):
        recycle_objs = recycle_objs
    elif not isinstance(recycle_objs, (list, tuple)):
        recycle_objs = [recycle_objs]

    for recycle_obj in recycle_objs:
        try:
            with transaction.atomic():
                app_label, model_name = recycle_obj.model_name.split(".")
                ModelClass = apps.get_model(app_label, model_name)

                if ModelClass.objects.filter(pk=recycle_obj.record_id).exists():
                    failed_records.append(
                        f"{recycle_obj.record_name()}: Record with ID {recycle_obj.record_id} already exists in {model_name}"
                    )
                    continue

                data = json.loads(recycle_obj.data)
                processed_data = {}

                for field in ModelClass._meta.fields:
                    field_name = field.name

                    if field.auto_created or field.primary_key:
                        continue

                    if field_name in data:
                        field_value = data[field_name]

                        # Handle MultiSelectField BEFORE checking for empty values
                        if isinstance(field, MultiSelectField):
                            # MultiSelectField stores as comma-separated string
                            if field_value in ["[]", "", "null", None, []]:
                                # Empty multiselect should be empty string
                                processed_data[field_name] = ""
                            elif isinstance(field_value, list):
                                # If it's already a list, join with commas
                                processed_data[field_name] = ",".join(
                                    str(v) for v in field_value
                                )
                            elif (
                                isinstance(field_value, str)
                                and field_value.startswith("[")
                                and field_value.endswith("]")
                            ):
                                # Handle string representation of list like "['monday','tuesday']"
                                try:
                                    parsed_list = json.loads(
                                        field_value.replace("'", '"')
                                    )
                                    processed_data[field_name] = (
                                        ",".join(str(v) for v in parsed_list)
                                        if parsed_list
                                        else ""
                                    )
                                except:
                                    # If parsing fails, treat as comma-separated string
                                    processed_data[field_name] = field_value
                            else:
                                # Already a comma-separated string
                                processed_data[field_name] = str(field_value)
                            continue

                        if (
                            field_value == ""
                            or field_value == "null"
                            or field_value is None
                        ):
                            if field.null:
                                processed_data[field_name] = None
                            elif field.blank:
                                processed_data[field_name] = ""
                            else:
                                if (
                                    hasattr(field, "default")
                                    and field.default != models.NOT_PROVIDED
                                ):
                                    processed_data[field_name] = field.default
                                else:
                                    if hasattr(field, "get_internal_type"):
                                        field_type = field.get_internal_type()
                                        if field_type in [
                                            "CharField",
                                            "TextField",
                                            "EmailField",
                                        ]:
                                            processed_data[field_name] = ""
                                        else:
                                            continue
                            continue

                        if hasattr(field, "get_internal_type"):
                            field_type = field.get_internal_type()

                            try:
                                if field_type == "DateTimeField":
                                    if isinstance(field_value, str):
                                        field_value = parse(field_value)
                                elif field_type == "DateField":
                                    if isinstance(field_value, str):
                                        field_value = parse(field_value).date()
                                elif field_type == "BooleanField":
                                    field_value = (
                                        bool(field_value)
                                        if field_value not in ["", "null", None]
                                        else False
                                    )
                                elif field_type in [
                                    "IntegerField",
                                    "BigIntegerField",
                                    "SmallIntegerField",
                                    "PositiveIntegerField",
                                ]:
                                    if str(field_value).strip() != "":
                                        field_value = int(field_value)
                                    else:
                                        if field.null:
                                            field_value = None
                                        else:
                                            field_value = 0
                                elif field_type in ["FloatField", "DecimalField"]:
                                    if str(field_value).strip() != "":
                                        field_value = float(field_value)
                                    else:
                                        if field.null:
                                            field_value = None
                                        else:
                                            field_value = 0.0
                                elif field_type == "ForeignKey":
                                    if field_value and str(field_value).strip() not in [
                                        "",
                                        "null",
                                        "None",
                                    ]:
                                        try:
                                            related_model = field.related_model
                                            related_obj = related_model.objects.get(
                                                pk=int(field_value)
                                            )
                                            field_value = related_obj
                                        except (
                                            related_model.DoesNotExist,
                                            ValueError,
                                            TypeError,
                                        ) as e:
                                            logger.warning(
                                                f"ForeignKey error for field {field_name} in {recycle_obj.record_name()}: {str(e)}"
                                            )
                                            if field.null:
                                                field_value = None
                                            else:
                                                # Assign the first available related object
                                                default_obj = (
                                                    related_model.objects.first()
                                                )
                                                if default_obj:
                                                    field_value = default_obj
                                                    logger.info(
                                                        f"Assigned default {related_model.__name__} ID {default_obj.pk} to {recycle_obj.record_name()} for field {field_name}"
                                                    )
                                                else:
                                                    failed_records.append(
                                                        f"{recycle_obj.record_name()}: No available {related_model.__name__} for required field {field_name}"
                                                    )
                                                    raise ValueError(
                                                        f"No available {related_model.__name__} for required field {field_name}"
                                                    )
                                    else:
                                        field_value = None
                                elif field_type in ["CharField", "TextField"]:
                                    if field_value == "null":
                                        field_value = None if field.null else ""
                                    else:
                                        field_value = str(field_value)
                                elif field_type == "EmailField":
                                    if field_value in ["", "null", None]:
                                        field_value = None if field.null else ""
                                    else:
                                        field_value = str(field_value)

                            except (ValueError, TypeError) as e:
                                logger.warning(
                                    f"Error processing field {field_name} in {recycle_obj.record_name()}: {str(e)}"
                                )
                                if field.null:
                                    field_value = None
                                else:
                                    continue

                        processed_data[field_name] = field_value

                restored_instance = ModelClass(**processed_data)
                restored_instance.save()
                recycle_obj.delete()
                restored_count += 1
        except Exception as e:
            failed_records.append(f"{recycle_obj.record_name()}: {str(e)}")
            logger.error(f"Failed to restore {recycle_obj.record_name()}: {str(e)}")

    return restored_count, failed_records


def delete_recycle_bin_records(request, recycle_objs):
    """
    Delete one or more RecycleBin records.

    Args:
        request: The Django request object for messaging.
        recycle_objs: A single RecycleBin object, a QuerySet, or a list of RecycleBin objects.

    Returns:
        tuple: (deleted_count, failed_records)
            - deleted_count: Number of successfully deleted records.
            - failed_records: List of strings describing failed deletions.
    """
    deleted_count = 0
    failed_records = []

    # Convert input to iterable
    if isinstance(recycle_objs, QuerySet):
        recycle_objs = recycle_objs
    elif not isinstance(recycle_objs, (list, tuple)):
        recycle_objs = [recycle_objs]

    for recycle_obj in recycle_objs:
        try:
            with transaction.atomic():
                if not RecycleBin.objects.filter(pk=recycle_obj.pk).exists():
                    failed_records.append(
                        f"{recycle_obj.record_name()}: Record with ID {recycle_obj.pk} does not exist"
                    )
                    continue

                recycle_obj.delete()
                deleted_count += 1
        except Exception as e:
            failed_records.append(f"{recycle_obj.record_name()}: {str(e)}")
            logger.error(f"Failed to delete {recycle_obj.record_name()}: {str(e)}")

    return deleted_count, failed_records


def compute_score(instance):
    """
    Compute the score for a given instance (Lead, Opportunity, Account, or Contact)
    based on active ScoringRules for the instance's module.

    Args:
        instance: A model instance (e.g., Lead, Opportunity) to score.

    Returns:
        int: The computed score (sum of points from matching criteria).

    Logic:
        - Filters active rules for the instance's module (e.g., 'lead').
        - For each rule, evaluates criteria in order.
        - If a criterion's conditions are met, adds/subtracts points based on operation_type.
        - Returns the total score.
    """
    module = instance._meta.model_name  # e.g., 'lead', 'opportunity'
    rules = ScoringRule.objects.filter(module=module, is_active=True)
    score = 0

    for rule in rules:
        for criterion in rule.criteria.all().order_by("order"):
            if criterion.evaluate_conditions(instance):
                points = criterion.points
                if criterion.operation_type == "sub":
                    points = -points
                score += points

    return score


def get_currency_display_value(obj, field_name, user):
    """
    Generic helper to format currency fields with user's preferred currency

    Args:
        obj: The model instance
        field_name: Name of the field to display
        user: Current user

    Returns:
        Formatted currency string like "USD 100.00" or "EUR 85.00 (USD 100.00)"
    """
    value = getattr(obj, field_name, None)

    if value is None or value == "":
        return ""

    company = getattr(obj, "company", None)
    if not company and hasattr(user, "company"):
        company = user.company

    if not company:
        return str(value)

    # Get currencies
    default_currency = MultipleCurrency.get_default_currency(company)
    user_currency = MultipleCurrency.get_user_currency(user)

    if not default_currency:
        return str(value)

    # If user currency is same as default or not set, just show default
    if not user_currency or user_currency.pk == default_currency.pk:
        return default_currency.display_with_symbol(value)

    converted_amount = user_currency.convert_from_default(value)
    user_display = user_currency.display_with_symbol(converted_amount)
    default_display = default_currency.display_with_symbol(value)

    return f"{default_display} ({user_display})"
