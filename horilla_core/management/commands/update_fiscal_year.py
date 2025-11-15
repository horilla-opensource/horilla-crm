from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from horilla_core.models import FiscalYear, FiscalYearInstance


class Command(BaseCommand):
    help = "Updates fiscal year instances by checking current status and creating next fiscal year"

    def handle(self, *args, **kwargs):
        fiscal_configs = FiscalYear.objects.all()

        for config in fiscal_configs:
            current_fy = FiscalYearInstance.objects.filter(
                fiscal_year_config=config, is_current=True
            ).first()

            if not current_fy:
                self.stdout.write(
                    self.style.WARNING(
                        f"No current fiscal year found for config {config}"
                    )
                )
                continue

            current_date = timezone.now().date()

            if current_date > current_fy.end_date:
                current_fy.is_current = False
                current_fy.save()

                next_fy = (
                    FiscalYearInstance.objects.filter(
                        fiscal_year_config=config, start_date__gt=current_fy.end_date
                    )
                    .order_by("start_date")
                    .first()
                )

                if next_fy:
                    next_fy.is_current = True
                    next_fy.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated current fiscal year to {next_fy}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No next fiscal year found for config {config}"
                        )
                    )

                self.create_next_fiscal_year(config, current_fy.end_date)

            next_fy_exists = FiscalYearInstance.objects.filter(
                fiscal_year_config=config, start_date__gt=current_fy.end_date
            ).exists()

            if not next_fy_exists:
                self.create_next_fiscal_year(config, current_fy.end_date)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created new next fiscal year for config {config}"
                    )
                )

    def create_next_fiscal_year(self, config, current_end_date):
        """Create a new fiscal year instance based on the configuration"""
        new_start_date = current_end_date + timedelta(days=1)
        new_end_date = new_start_date + relativedelta(years=1) - timedelta(days=1)

        if config.display_year_based_on == "starting_year":
            year_name = new_start_date.year
        else:
            year_name = new_end_date.year

        fiscal_year_name = f"{config.get_start_date_month_display()} {config.start_date_day} {year_name}"

        FiscalYearInstance.objects.create(
            fiscal_year_config=config,
            start_date=new_start_date,
            end_date=new_end_date,
            name=fiscal_year_name,
            is_current=False,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Created fiscal year instance: {fiscal_year_name}")
        )
