from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.db import transaction
from django.utils import timezone

from horilla_core.models import FiscalYear


class FiscalYearService:
    """
    Service class for handling fiscal year operations including:
    - Creating default configurations
    - Generating fiscal years, quarters, and periods
    - Managing fiscal year transitions
    """

    @staticmethod
    def get_or_create_company_configuration(company):
        """
        Safely get or create fiscal year configuration
        """
        try:
            return FiscalYear.objects.get(company=company)
        except FiscalYear.DoesNotExist:
            config = FiscalYear(
                company=company,
                fiscal_year_type="standard",
                start_date_month="january",
                start_date_day=1,
                display_year_based_on="starting_year",
            )
            config.save()
            return config

    @staticmethod
    def generate_fiscal_years(config, years_ahead=1):
        """
        Generate current and next fiscal years based on configuration
        """
        FiscalYearInstance = apps.get_model("horilla_core", "FiscalYearInstance")
        Quarter = apps.get_model("horilla_core", "Quarter")
        Period = apps.get_model("horilla_core", "Period")

        current_year = timezone.now().year
        years_to_generate = [current_year, current_year + 1]

        FiscalYearInstance.objects.filter(company=config.company).delete()

        month_number = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }.get(config.start_date_month.lower(), 1)

        with transaction.atomic():
            previous_end_date = None

            for i, year in enumerate(years_to_generate):
                # For the first year, use the configured start date
                if i == 0:
                    start_date = datetime(
                        year, month_number, config.start_date_day
                    ).date()
                else:
                    # For subsequent years, start the day after the previous year ends
                    start_date = previous_end_date + timedelta(days=1)

                if config.fiscal_year_type == "standard":
                    end_date = start_date + relativedelta(years=1) - timedelta(days=1)
                else:
                    end_date = start_date + relativedelta(years=1) - timedelta(days=2)

                if config.display_year_based_on == "starting_year":
                    name = f"FY {year}"
                else:
                    name = f"FY {year + 1}"

                fiscal_year, created = FiscalYearInstance.objects.get_or_create(
                    company=config.company,
                    fiscal_year_config=config,
                    start_date=start_date,
                    defaults={
                        "end_date": end_date,
                        "name": name,
                        "is_current": year == current_year,
                        "is_active": True,
                    },
                )

                if not created:
                    fiscal_year.company = config.company
                    fiscal_year.end_date = end_date
                    fiscal_year.name = name
                    fiscal_year.is_current = year == current_year
                    fiscal_year.save()

                # Store the end date for the next iteration
                previous_end_date = end_date

                # Generate quarters
                FiscalYearService._generate_quarters(config, fiscal_year)

    @staticmethod
    def _generate_quarters(config, fiscal_year):
        """
        Generate quarters for a fiscal year
        """
        Quarter = apps.get_model("horilla_core", "Quarter")

        periods_info = config.get_periods_by_format()
        quarter_durations = FiscalYearService._calculate_quarter_dates(
            fiscal_year.start_date, fiscal_year.end_date, config, periods_info
        )

        for i, (q_start, q_end) in enumerate(quarter_durations, start=1):
            quarter_name = f"Q{i}"

            quarter, created = Quarter.objects.get_or_create(
                company=fiscal_year.company,
                fiscal_year=fiscal_year,
                quarter_number=i,
                defaults={
                    "name": quarter_name,
                    "start_date": q_start,
                    "end_date": q_end,
                    "is_active": True,
                },
            )

            if not created:
                quarter.company = fiscal_year.company
                quarter.start_date = q_start
                quarter.end_date = q_end
                quarter.save()

            # Generate periods for this quarter
            FiscalYearService._generate_periods(config, quarter, periods_info)

    @staticmethod
    def _calculate_quarter_dates(start_date, end_date, config=None, periods_info=None):
        """
        Calculate quarter dates based on fiscal year configuration
        """
        quarters = []

        if config and config.format_type == "quarter_based":
            quarter_duration = 91  # 13 weeks * 7 days
            current_start = start_date

            for i in range(4):
                if i < 3:
                    current_end = current_start + timedelta(days=quarter_duration - 1)
                else:
                    current_end = end_date

                quarters.append((current_start, current_end))
                current_start = current_end + timedelta(days=1)

        elif config and config.format_type == "year_based":
            if periods_info:
                current_start = start_date

                for quarter_num in range(1, 5):
                    quarter_periods = FiscalYearService._get_quarter_periods(
                        config, quarter_num, periods_info
                    )

                    # Each period in year-based is 4 weeks = 28 days
                    quarter_days = quarter_periods * 28

                    if quarter_num < 4:
                        current_end = current_start + timedelta(days=quarter_days - 1)
                    else:
                        # Last quarter ends at fiscal year end
                        current_end = end_date

                    quarters.append((current_start, current_end))
                    current_start = current_end + timedelta(days=1)

        else:
            current_start = start_date

            for i in range(4):
                if i < 3:
                    current_end = (
                        current_start + relativedelta(months=3) - timedelta(days=1)
                    )
                else:
                    current_end = end_date

                quarters.append((current_start, current_end))
                current_start = current_end + timedelta(days=1)

        return quarters

    @staticmethod
    def _generate_periods(config, quarter, periods_info):
        """
        Generate periods for a quarter based on configuration
        """
        Period = apps.get_model("horilla_core", "Period")

        if (
            config.format_type == "quarter_based"
            and "weeks_per_period_pattern" in periods_info
        ):
            weeks_pattern = periods_info["weeks_per_period_pattern"]
            current_start = quarter.start_date

            for i, weeks in enumerate(weeks_pattern, 1):
                period_days = weeks * 7
                current_end = current_start + timedelta(days=period_days - 1)

                if i == len(weeks_pattern):
                    current_end = quarter.end_date

                period_name = f"P{i}"

                period, created = Period.objects.get_or_create(
                    company=quarter.company,
                    quarter=quarter,
                    period_number=i,
                    defaults={
                        "name": period_name,
                        "start_date": current_start,
                        "end_date": current_end,
                        "is_active": True,
                    },
                )

                if not created:
                    period.company = quarter.company
                    period.start_date = current_start
                    period.end_date = current_end
                    period.save()

                current_start = current_end + timedelta(days=1)

        else:
            # Year-based or standard: Calculate periods based on format
            quarter_periods = FiscalYearService._get_quarter_periods(
                config, quarter.quarter_number, periods_info
            )

            if config.format_type == "year_based":
                # For year-based, each period is 4 weeks = 28 days
                period_duration = 28
            else:
                # For standard, divide quarter equally
                quarter_duration = (quarter.end_date - quarter.start_date).days + 1
                period_duration = quarter_duration // quarter_periods

            current_start = quarter.start_date

            for i in range(1, quarter_periods + 1):
                if i < quarter_periods:
                    current_end = current_start + timedelta(days=period_duration - 1)
                else:
                    current_end = quarter.end_date

                period_name = f"P{i}"

                period, created = Period.objects.get_or_create(
                    company=quarter.company,
                    quarter=quarter,
                    period_number=i,
                    defaults={
                        "name": period_name,
                        "start_date": current_start,
                        "end_date": current_end,
                        "is_active": True,
                    },
                )

                if not created:
                    period.company = quarter.company
                    period.start_date = current_start
                    period.end_date = current_end
                    period.save()

                current_start = current_end + timedelta(days=1)

    @staticmethod
    def _get_quarter_periods(config, quarter_number, periods_info):
        """
        Get the number of periods for a specific quarter
        """
        # Use the property methods or direct calculation
        if quarter_number == 1:
            return periods_info["quarter_1_periods"]
        elif quarter_number == 2:
            return periods_info["quarter_2_periods"]
        elif quarter_number == 3:
            return periods_info["quarter_3_periods"]
        elif quarter_number == 4:
            return periods_info["quarter_4_periods"]
        else:
            return 3  # Default fallback

    @staticmethod
    def get_current_fiscal_year(company):
        """
        Get the current fiscal year for a company
        """
        FiscalYearInstance = apps.get_model("horilla_core", "FiscalYearInstance")
        try:
            return FiscalYearInstance.objects.get(company=company, is_current=True)
        except FiscalYearInstance.DoesNotExist:
            return None

    @staticmethod
    def get_current_quarter(company):
        """
        Get the current quarter for a company
        """
        Quarter = apps.get_model("horilla_core", "Quarter")
        current_date = timezone.now().date()

        try:
            return Quarter.objects.get(
                company=company,
                start_date__lte=current_date,
                end_date__gte=current_date,
            )
        except Quarter.DoesNotExist:
            return None

    @staticmethod
    def get_current_period(company):
        """
        Get the current period for a company
        """
        Period = apps.get_model("horilla_core", "Period")
        current_date = timezone.now().date()

        try:
            return Period.objects.get(
                company=company,
                start_date__lte=current_date,
                end_date__gte=current_date,
            )
        except Period.DoesNotExist:
            return None

    @staticmethod
    def regenerate_fiscal_years(config):
        """
        Regenerate all fiscal years for a configuration
        Useful when format changes
        """
        FiscalYearInstance = apps.get_model("horilla_core", "FiscalYearInstance")

        # Delete existing instances and related data
        FiscalYearInstance.objects.filter(fiscal_year_config=config).delete()

        # Regenerate
        FiscalYearService.generate_fiscal_years(config)

    @staticmethod
    def validate_fiscal_year_config(config):
        """
        Validate fiscal year configuration
        """
        errors = []

        if config.fiscal_year_type == "custom":
            if not config.format_type:
                errors.append("Format type is required for custom fiscal year")

            if config.format_type == "year_based" and not config.year_based_format:
                errors.append(
                    "Year based format is required when format type is year_based"
                )

            if (
                config.format_type == "quarter_based"
                and not config.quarter_based_format
            ):
                errors.append(
                    "Quarter based format is required when format type is quarter_based"
                )

        if not config.start_date_month:
            errors.append("Start date month is required")

        if (
            not config.start_date_day
            or config.start_date_day < 1
            or config.start_date_day > 31
        ):
            errors.append("Start date day must be between 1 and 31")

        return errors
