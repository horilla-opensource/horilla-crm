"""
Management command to recalculate all existing forecasts
This will fix any inconsistencies from past data changes

Usage:
python manage.py recalculate_forecasts

Options:
python manage.py recalculate_forecasts --user-id=123  # Specific user
python manage.py recalculate_forecasts --fiscal-year-id=5  # Specific fiscal year
python manage.py recalculate_forecasts --forecast-type-id=2  # Specific forecast type
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from horilla_crm.forecast.models import Forecast
from horilla_crm.forecast.utils import ForecastCalculator


class Command(BaseCommand):
    help = "Recalculate all existing forecasts to fix any inconsistencies"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            help="Recalculate forecasts for specific user only",
        )
        parser.add_argument(
            "--fiscal-year-id",
            type=int,
            help="Recalculate forecasts for specific fiscal year only",
        )
        parser.add_argument(
            "--forecast-type-id",
            type=int,
            help="Recalculate forecasts for specific forecast type only",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without actually updating",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        fiscal_year_id = options.get("fiscal_year_id")
        forecast_type_id = options.get("forecast_type_id")
        dry_run = options.get("dry_run")

        self.stdout.write(self.style.SUCCESS("Starting forecast recalculation..."))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be saved")
            )

        # Build query for existing forecasts
        forecast_query = Q()

        if user_id:
            forecast_query &= Q(owner_id=user_id)
            self.stdout.write(f"Filtering by user ID: {user_id}")

        if fiscal_year_id:
            forecast_query &= Q(fiscal_year_id=fiscal_year_id)
            self.stdout.write(f"Filtering by fiscal year ID: {fiscal_year_id}")

        if forecast_type_id:
            forecast_query &= Q(forecast_type_id=forecast_type_id)
            self.stdout.write(f"Filtering by forecast type ID: {forecast_type_id}")

        # Get all forecasts to recalculate
        forecasts = (
            Forecast.objects.filter(forecast_query)
            .select_related(
                "owner", "forecast_type", "period", "quarter", "fiscal_year"
            )
            .order_by("owner__id", "period__period_number")
        )

        total_forecasts = forecasts.count()
        self.stdout.write(f"Found {total_forecasts} forecasts to recalculate")

        if total_forecasts == 0:
            self.stdout.write(self.style.WARNING("No forecasts found to recalculate"))
            return

        updated_count = 0
        error_count = 0

        # Group forecasts by user and fiscal year for efficient processing
        forecast_groups = {}
        for forecast in forecasts:
            key = (forecast.owner_id, forecast.fiscal_year_id)
            if key not in forecast_groups:
                forecast_groups[key] = []
            forecast_groups[key].append(forecast)

        self.stdout.write(
            f"Processing {len(forecast_groups)} user/fiscal-year combinations...\n"
        )

        for (owner_id, fiscal_year_id), user_forecasts in forecast_groups.items():
            try:
                owner = user_forecasts[0].owner
                fiscal_year = user_forecasts[0].fiscal_year

                self.stdout.write(
                    f"Processing forecasts for: {owner.get_full_name()} ({owner.email})"
                )
                self.stdout.write(f"  Fiscal Year: {fiscal_year.name}")

                calculator = ForecastCalculator(user=owner, fiscal_year=fiscal_year)

                # Group by forecast type and period
                for forecast in user_forecasts:
                    try:
                        self.stdout.write(f"  - Recalculating: {forecast.name}")

                        # Calculate new values
                        calculated_data = calculator.calculate_forecast_values(
                            owner, forecast.period, forecast.forecast_type
                        )

                        # Show what would change
                        if forecast.forecast_type.is_quantity_based:
                            old_values = {
                                "pipeline": forecast.pipeline_quantity,
                                "best_case": forecast.best_case_quantity,
                                "commit": forecast.commit_quantity,
                                "closed": forecast.closed_quantity,
                                "actual": forecast.actual_quantity,
                            }
                        else:
                            old_values = {
                                "pipeline": forecast.pipeline_amount,
                                "best_case": forecast.best_case_amount,
                                "commit": forecast.commit_amount,
                                "closed": forecast.closed_amount,
                                "actual": forecast.actual_amount,
                            }

                        # Check if values changed
                        has_changes = False
                        for key in [
                            "pipeline",
                            "best_case",
                            "commit",
                            "closed",
                            "actual",
                        ]:
                            if old_values[key] != calculated_data[key]:
                                has_changes = True
                                self.stdout.write(
                                    f"    {key}: {old_values[key]} → {calculated_data[key]}"
                                )

                        if not has_changes:
                            self.stdout.write(
                                self.style.SUCCESS("    No changes needed")
                            )
                        else:
                            if not dry_run:
                                # Update forecast with new values
                                if forecast.forecast_type.is_quantity_based:
                                    forecast.pipeline_quantity = calculated_data[
                                        "pipeline"
                                    ]
                                    forecast.best_case_quantity = calculated_data[
                                        "best_case"
                                    ]
                                    forecast.commit_quantity = calculated_data["commit"]
                                    forecast.closed_quantity = calculated_data["closed"]
                                    forecast.actual_quantity = calculated_data["actual"]
                                else:
                                    forecast.pipeline_amount = calculated_data[
                                        "pipeline"
                                    ]
                                    forecast.best_case_amount = calculated_data[
                                        "best_case"
                                    ]
                                    forecast.commit_amount = calculated_data["commit"]
                                    forecast.closed_amount = calculated_data["closed"]
                                    forecast.actual_amount = calculated_data["actual"]

                                forecast.save()
                                self.stdout.write(self.style.SUCCESS("    ✓ Updated"))
                            else:
                                self.stdout.write(
                                    self.style.WARNING("    (Would update)")
                                )

                        updated_count += 1

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f"    ✗ Error: {str(e)}"))

                self.stdout.write("")  # Empty line between users

            except Exception as e:
                error_count += len(user_forecasts)
                self.stdout.write(
                    self.style.ERROR(f"Error processing user {owner_id}: {str(e)}\n")
                )

        # Summary
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 50))
        self.stdout.write(self.style.SUCCESS("Recalculation Complete!"))
        self.stdout.write(f"Total forecasts processed: {updated_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors encountered: {error_count}"))
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No actual changes were made")
            )
        self.stdout.write(self.style.SUCCESS("=" * 50))
