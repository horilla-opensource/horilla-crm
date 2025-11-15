import calendar as cal_module
from calendar import monthcalendar
from datetime import datetime, timedelta

from horilla_core.models import HorillaUser


class CompanyFilterMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        company = getattr(self.request, "active_company", None)
        if company:
            qs = qs.filter(company=company)
        return qs


class FiscalYearCalendarMixin:
    def get_calendar_data(
        self,
        fiscal_year_data,
        start_date_month,
        start_date_day,
        week_start_day,
        current_year=None,
    ):
        if current_year is None:
            current_year = datetime.now().year

        # Extract fiscal year attributes
        fiscal_year_type = fiscal_year_data.get("fiscal_year_type", "standard")
        format_type = fiscal_year_data.get("format_type", "")
        year_based_format = fiscal_year_data.get("year_based_format", "")
        quarter_based_format = fiscal_year_data.get("quarter_based_format", "")
        number_weeks_by = fiscal_year_data.get("number_weeks_by", "year")
        period_display_option = fiscal_year_data.get(
            "period_display_option", "number_by_year"
        )

        # Month mapping for handling month names and abbreviations
        month_mapping = {
            "january": 0,
            "jan": 0,
            "february": 1,
            "feb": 1,
            "march": 2,
            "mar": 2,
            "april": 3,
            "apr": 3,
            "may": 4,
            "june": 5,
            "jun": 5,
            "july": 6,
            "jul": 6,
            "august": 7,
            "aug": 7,
            "september": 8,
            "sep": 8,
            "october": 9,
            "oct": 9,
            "november": 10,
            "nov": 10,
            "december": 11,
            "dec": 11,
        }

        # Get month index using the mapping
        month_index = month_mapping.get(
            start_date_month.lower(), 0
        )  # Default to January
        start_date = datetime(current_year, month_index + 1, start_date_day)

        # Define days of the week and order them based on week_start_day
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        if week_start_day in days:
            start_index = days.index(week_start_day)
            ordered_days = days[start_index:] + days[:start_index]
        else:
            ordered_days = days

        current_date = start_date

        def create_week_data(
            week_number, start_date, days_in_week, week_start_day_index
        ):
            week_rows = []
            current_week_date = start_date
            days_added = 0

            while days_added < days_in_week:
                current_day_of_week = current_week_date.weekday()
                if week_start_day == "monday":
                    start_day_index = current_day_of_week
                elif week_start_day == "sunday":
                    start_day_index = (current_day_of_week + 1) % 7
                else:
                    days_mapping = {
                        "monday": 0,
                        "tuesday": 1,
                        "wednesday": 2,
                        "thursday": 3,
                        "friday": 4,
                        "saturday": 5,
                        "sunday": 6,
                    }
                    week_start_index = days_mapping[week_start_day]
                    start_day_index = (current_day_of_week - week_start_index) % 7

                row_days = [None] * 7  # Initialize with None for empty cells
                row_months = []

                days_in_this_row = min(7 - start_day_index, days_in_week - days_added)
                for i in range(days_in_this_row):
                    day_index = start_day_index + i
                    row_days[day_index] = current_week_date.day
                    row_months.append(current_week_date.strftime("%b"))
                    current_week_date += timedelta(days=1)
                    days_added += 1

                unique_months = []
                for month in row_months:
                    if month not in unique_months:
                        unique_months.append(month)

                month_display = (
                    unique_months[0]
                    if len(unique_months) == 1
                    else "/".join(unique_months)
                )
                week_rows.append(
                    {
                        "week_number": week_number,
                        "month": month_display,
                        "days": row_days,
                    }
                )

                if days_added < days_in_week:
                    start_day_index = 0

            return week_rows, current_week_date

        calendar_data = []
        period_counter = 1
        week_counter = 1

        if fiscal_year_type == "standard":
            fiscal_months = []
            start_month = month_index + 1
            for i in range(12):
                month_num = ((start_month - 1 + i) % 12) + 1
                year = current_year if (start_month + i - 1) < 12 else current_year + 1
                fiscal_months.append((year, month_num))

            for quarter in range(1, 5):
                quarter_periods = []
                quarter_start_idx = (quarter - 1) * 3
                for p in range(3):
                    month_idx = quarter_start_idx + p
                    year, month_num = fiscal_months[month_idx]
                    month_name = datetime(year, month_num, 1).strftime("%B")

                    if week_start_day == "sunday":
                        cal_module.setfirstweekday(6)
                        cal = cal_module.monthcalendar(year, month_num)
                        cal_module.setfirstweekday(0)
                    else:
                        cal = monthcalendar(year, month_num)

                    weeks = [
                        [day if day != 0 else None for day in week] for week in cal
                    ]
                    quarter_periods.append(
                        {
                            "period_number": p + 1,
                            "weeks": weeks,
                            "month_name": month_name,
                            "is_standard": True,
                        }
                    )
                calendar_data.append(
                    {"quarter_number": quarter, "periods": quarter_periods}
                )

        elif (
            fiscal_year_type == "custom"
            and format_type == "year_based"
            and year_based_format
        ):
            periods_per_quarter = [int(p) for p in year_based_format.split("-")]
            for quarter, num_periods in enumerate(periods_per_quarter, 1):
                quarter_periods = []
                quarter_week_counter = 1
                for p in range(num_periods):
                    weeks = []
                    period_week_counter = 1
                    for w in range(1, 5):
                        week_number = (
                            week_counter
                            if number_weeks_by == "year"
                            else (
                                quarter_week_counter
                                if number_weeks_by == "quarter"
                                else period_week_counter
                            )
                        )
                        week_start_day_index = days.index(week_start_day)
                        week_rows, current_date = create_week_data(
                            week_number, current_date, 7, week_start_day_index
                        )
                        weeks.extend(week_rows)
                        week_counter += 1
                        quarter_week_counter += 1
                        period_week_counter += 1
                    period_number = (
                        period_counter
                        if period_display_option == "number_by_year"
                        else p + 1
                    )
                    quarter_periods.append(
                        {
                            "period_number": period_number,
                            "weeks": weeks,
                            "is_standard": False,
                        }
                    )
                    period_counter += 1
                calendar_data.append(
                    {"quarter_number": quarter, "periods": quarter_periods}
                )

        elif (
            fiscal_year_type == "custom"
            and format_type == "quarter_based"
            and quarter_based_format
        ):
            weeks_per_period = [int(w) for w in quarter_based_format.split("-")]
            for quarter in range(1, 5):
                quarter_periods = []
                quarter_week_counter = 1
                for p, num_weeks in enumerate(weeks_per_period, 1):
                    weeks = []
                    period_week_counter = 1
                    for w in range(1, num_weeks + 1):
                        week_number = (
                            week_counter
                            if number_weeks_by == "year"
                            else (
                                quarter_week_counter
                                if number_weeks_by == "quarter"
                                else period_week_counter
                            )
                        )
                        week_start_day_index = days.index(week_start_day)
                        week_rows, current_date = create_week_data(
                            week_number, current_date, 7, week_start_day_index
                        )
                        weeks.extend(week_rows)
                        week_counter += 1
                        quarter_week_counter += 1
                        period_week_counter += 1
                    period_number = (
                        period_counter
                        if period_display_option == "number_by_year"
                        else p
                    )
                    quarter_periods.append(
                        {
                            "period_number": period_number,
                            "weeks": weeks,
                            "is_standard": False,
                        }
                    )
                    period_counter += 1
                calendar_data.append(
                    {"quarter_number": quarter, "periods": quarter_periods}
                )

        return {
            "calendar_data": calendar_data,
            "ordered_days": [day[:3].capitalize() for day in ordered_days],
            "number_weeks_by": number_weeks_by,
            "period_display_option": period_display_option,
            "fiscal_year_type": fiscal_year_type,
        }


class OwnerQuerysetMixin:
    """
    Mixin to dynamically filter any ForeignKey or ManyToManyField
    whose related model is `HorillaUser`, based on the current user.

    - For superusers: Shows all users.
    - For non-superusers: Shows the current user + their subordinates (recursive via subroles).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("request") or getattr(self, "request", None)
        user = request.user if request else None

        if not (user and hasattr(self, "fields")):
            return

        if user.is_superuser:
            allowed_users = HorillaUser.objects.all()
        else:
            user_role = getattr(user, "role", None)
            if user_role:

                def get_subordinate_roles(role):
                    sub_roles = role.subroles.all()
                    all_sub_roles = []
                    for sub_role in sub_roles:
                        all_sub_roles.append(sub_role)
                        all_sub_roles.extend(get_subordinate_roles(sub_role))
                    return all_sub_roles

                subordinate_roles = get_subordinate_roles(user_role)
                # all_roles = [user_role] + subordinate_roles

                subordinate_users = HorillaUser.objects.filter(
                    role__in=subordinate_roles
                ).distinct()
                allowed_users = HorillaUser.objects.filter(
                    id__in=[user.id]
                    + list(subordinate_users.values_list("id", flat=True))
                )
            else:
                allowed_users = HorillaUser.objects.filter(id=user.id)

        for field_name, field in self.fields.items():
            model_field = self._meta.model._meta.get_field(field_name)

            if model_field.is_relation and model_field.related_model == HorillaUser:
                field.queryset = allowed_users


class OwnerFiltersetMixin:
    """
    Mixin to dynamically filter `HorillaUser`-related filters
    in a Django FilterSet.

    Usage:
        class EmployeeFilter(OwnerFiltersetMixin, HorillaFilterSet):
            class Meta:
                model = Employee
                fields = ['manager', 'created_by', 'user']
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get request object
        request = getattr(self, "request", None)
        if not request and hasattr(self, "data") and hasattr(self.data, "_request"):
            request = self.data._request

        user = getattr(request, "user", None)
        if not (user and hasattr(self, "filters")):
            return

        # Determine allowed users
        if user.is_superuser:
            allowed_users = HorillaUser.objects.all()
        else:
            user_role = getattr(user, "role", None)
            if user_role:

                def get_subordinate_roles(role):
                    sub_roles = role.subroles.all()
                    all_sub_roles = []
                    for sub_role in sub_roles:
                        all_sub_roles.append(sub_role)
                        all_sub_roles.extend(get_subordinate_roles(sub_role))
                    return all_sub_roles

                subordinate_roles = get_subordinate_roles(user_role)
                subordinate_users = HorillaUser.objects.filter(
                    role__in=subordinate_roles
                ).distinct()
                allowed_users = HorillaUser.objects.filter(
                    id__in=[user.id]
                    + list(subordinate_users.values_list("id", flat=True))
                )
            else:
                allowed_users = HorillaUser.objects.filter(id=user.id)

        # Restrict queryset for filters that reference HorillaUser
        for field_name, filter_obj in self.filters.items():
            try:
                model_field = self._meta.model._meta.get_field(field_name)
                if model_field.is_relation and model_field.related_model == HorillaUser:
                    if hasattr(filter_obj, "field") and hasattr(
                        filter_obj.field, "queryset"
                    ):
                        filter_obj.field.queryset = allowed_users
            except Exception:
                continue
