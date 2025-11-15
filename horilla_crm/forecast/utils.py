"""
ForecastCalculator Utility for Horilla CRM

Provides automatic calculation, creation, and updating of forecasts
(amount, expected revenue, or quantity) for users and periods based on
opportunity data and forecast targets.

Features:
- Automatic generation and update of forecasts per user/period.
- Supports bulk operations for performance.
- Handles dynamic conditions with logical AND/OR grouping.
- Computes pipeline, best case, commit, closed, and actual values.
- Fetches and applies targets automatically.
- Caches condition queries for efficiency.
"""

from django.db.models import Q, Sum

from horilla_core.models import FiscalYearInstance, HorillaUser, Period
from horilla_crm.forecast.models import Forecast, ForecastTarget, ForecastType
from horilla_crm.opportunities.models import Opportunity


class ForecastCalculator:
    """
    utility class to automatically calculate and create/update forecasts
    Enhanced to support all forecast types with bulk operations for better performance
    """

    def __init__(self, user=None, fiscal_year=None):
        self.user = user
        self.fiscal_year = fiscal_year or self.get_current_fiscal_year()
        self._conditions_cache = {}  # Cache for forecast conditions

    def get_current_fiscal_year(self):
        """Get current active fiscal year"""
        return FiscalYearInstance.objects.filter(is_current=True).first()

    def bulk_create_missing_forecasts(self, forecast_type, missing_combinations):
        """
        Bulk create missing forecasts instead of individual creation
        """
        if not missing_combinations:
            return

        # Get all required data in bulk
        user_ids = list(set(combo[0] for combo in missing_combinations))
        period_ids = list(set(combo[1] for combo in missing_combinations))

        users_map = {u.id: u for u in HorillaUser.objects.filter(id__in=user_ids)}
        periods_map = {
            p.id: p
            for p in Period.objects.filter(id__in=period_ids).select_related("quarter")
        }

        # Get targets in bulk
        targets = ForecastTarget.objects.filter(
            assigned_to_id__in=user_ids,
            period_id__in=period_ids,
            forcasts_type=forecast_type,
            is_active=True,
        ).select_related("assigned_to", "period")

        targets_map = {(t.assigned_to_id, t.period_id): t for t in targets}

        # Prepare forecasts for bulk creation
        forecasts_to_create = []
        for user_id, period_id in missing_combinations:
            user = users_map.get(user_id)
            period = periods_map.get(period_id)

            if not user or not period:
                continue

            target = targets_map.get((user_id, period_id))
            target_amount = target.target_amount if target else 0

            forecast = Forecast(
                company=getattr(self.user, "company", None) if self.user else None,
                owner=user,
                forecast_type=forecast_type,
                period=period,
                quarter=period.quarter,
                fiscal_year=period.quarter.fiscal_year,
                name=f"{forecast_type.name} - {period.name}",
                target_amount=(
                    target_amount if not forecast_type.is_quantity_based else 0
                ),
                target_quantity=target_amount if forecast_type.is_quantity_based else 0,
                # Initialize other fields to 0
                pipeline_amount=0 if not forecast_type.is_quantity_based else None,
                best_case_amount=0 if not forecast_type.is_quantity_based else None,
                commit_amount=0 if not forecast_type.is_quantity_based else None,
                closed_amount=0 if not forecast_type.is_quantity_based else None,
                actual_amount=0 if not forecast_type.is_quantity_based else None,
                pipeline_quantity=0 if forecast_type.is_quantity_based else None,
                best_case_quantity=0 if forecast_type.is_quantity_based else None,
                commit_quantity=0 if forecast_type.is_quantity_based else None,
                closed_quantity=0 if forecast_type.is_quantity_based else None,
                actual_quantity=0 if forecast_type.is_quantity_based else None,
            )
            forecasts_to_create.append(forecast)

        # Bulk create forecasts
        if forecasts_to_create:
            created_forecasts = Forecast.objects.bulk_create(
                forecasts_to_create, batch_size=1000
            )

            # Now calculate values for the created forecasts in bulk
            self.bulk_calculate_forecast_values(created_forecasts, forecast_type)

    def bulk_calculate_forecast_values(self, forecasts, forecast_type):
        """
        Calculate forecast values for multiple forecasts in bulk
        """
        if not forecasts:
            return

        # Group forecasts by user and period for efficient querying
        user_period_forecasts = {}
        for forecast in forecasts:
            key = (forecast.owner_id, forecast.period_id)
            user_period_forecasts[key] = forecast

        # Get all opportunities for all users/periods in single query
        user_ids = list(set(f.owner_id for f in forecasts))
        period_data = {}
        for forecast in forecasts:
            if forecast.period_id not in period_data:
                period_data[forecast.period_id] = {
                    "start_date": forecast.period.start_date,
                    "end_date": forecast.period.end_date,
                }

        # Build conditions query once and cache it
        conditions_query = self.get_cached_conditions_query(forecast_type)

        # Get all relevant opportunities in bulk
        opportunities_query = Q(owner_id__in=user_ids)

        # Add date range conditions for all periods
        date_conditions = Q()
        for period_info in period_data.values():
            date_conditions |= Q(
                close_date__range=[period_info["start_date"], period_info["end_date"]]
            )
        opportunities_query &= date_conditions

        if conditions_query:
            opportunities_query &= conditions_query

        opportunities = Opportunity.objects.filter(opportunities_query).values(
            "id",
            "owner_id",
            "close_date",
            "amount",
            "expected_revenue",
            "forecast_category",
            "stage__stage_type",
        )

        # Group opportunities by user and period
        user_period_opportunities = {}
        for opp in opportunities:
            # Find which period this opportunity belongs to
            for forecast in forecasts:
                if (
                    forecast.owner_id == opp["owner_id"]
                    and forecast.period.start_date
                    <= opp["close_date"]
                    <= forecast.period.end_date
                ):

                    key = (opp["owner_id"], forecast.period_id)
                    if key not in user_period_opportunities:
                        user_period_opportunities[key] = []
                    user_period_opportunities[key].append(opp)
                    break

        # Calculate values for each forecast
        forecasts_to_update = []
        for forecast in forecasts:
            key = (forecast.owner_id, forecast.period_id)
            user_opportunities = user_period_opportunities.get(key, [])

            values = self.calculate_values_from_opportunities(
                user_opportunities, forecast_type
            )

            # Update forecast fields based on type
            if forecast_type.is_quantity_based:
                forecast.pipeline_quantity = values["pipeline"]
                forecast.best_case_quantity = values["best_case"]
                forecast.commit_quantity = values["commit"]
                forecast.closed_quantity = values["closed"]
                forecast.actual_quantity = values["actual"]
            else:
                forecast.pipeline_amount = values["pipeline"]
                forecast.best_case_amount = values["best_case"]
                forecast.commit_amount = values["commit"]
                forecast.closed_amount = values["closed"]
                forecast.actual_amount = values["actual"]

            forecasts_to_update.append(forecast)

        # Bulk update forecasts
        if forecasts_to_update:
            fields_to_update = []
            if forecast_type.is_quantity_based:
                fields_to_update = [
                    "pipeline_quantity",
                    "best_case_quantity",
                    "commit_quantity",
                    "closed_quantity",
                    "actual_quantity",
                ]
            else:
                fields_to_update = [
                    "pipeline_amount",
                    "best_case_amount",
                    "commit_amount",
                    "closed_amount",
                    "actual_amount",
                ]

            Forecast.objects.bulk_update(
                forecasts_to_update, fields_to_update, batch_size=1000
            )

    def get_cached_conditions_query(self, forecast_type):
        """
        Cache conditions query to avoid rebuilding for each forecast
        """
        cache_key = f"conditions_{forecast_type.id}"
        if cache_key not in self._conditions_cache:
            self._conditions_cache[cache_key] = self.build_conditions_query(
                forecast_type
            )
        return self._conditions_cache[cache_key]

    def calculate_values_from_opportunities(self, opportunities, forecast_type):
        """
        Calculate values from pre-fetched opportunity data
        """

        if forecast_type.is_quantity_based:
            return self._calculate_quantity_values_from_data(
                opportunities, forecast_type
            )
        elif forecast_type.is_revenue_expected_based:
            return self._calculate_expected_amount_values_from_data(
                opportunities, forecast_type
            )
        else:
            return self._calculate_amount_values_from_data(opportunities, forecast_type)

    def _calculate_quantity_values_from_data(self, opportunities, forecast_type):
        """Calculate quantity values from opportunity data"""
        values = {
            "pipeline": 0,
            "best_case": 0,
            "commit": 0,
            "closed": 0,
            "actual": 0,
        }

        for opp in opportunities:
            if (
                forecast_type.include_pipeline
                and opp["forecast_category"] == "pipeline"
            ):
                values["pipeline"] += 1
            if (
                forecast_type.include_best_case
                and opp["forecast_category"] == "best_case"
            ):
                values["best_case"] += 1
            if forecast_type.include_commit and opp["forecast_category"] == "commit":
                values["commit"] += 1
            if forecast_type.include_closed and opp["forecast_category"] == "closed":
                values["closed"] += 1
            if opp["stage__stage_type"] == "won":
                values["actual"] += 1

        return values

    def _calculate_expected_amount_values_from_data(self, opportunities, forecast_type):
        """Calculate expected amount values from opportunity data"""
        values = {
            "pipeline": 0,
            "best_case": 0,
            "commit": 0,
            "closed": 0,
            "actual": 0,
        }

        for opp in opportunities:
            expected_revenue = opp["expected_revenue"] or 0
            if (
                forecast_type.include_pipeline
                and opp["forecast_category"] == "pipeline"
            ):
                values["pipeline"] += expected_revenue
            if (
                forecast_type.include_best_case
                and opp["forecast_category"] == "best_case"
            ):
                values["best_case"] += expected_revenue
            if forecast_type.include_commit and opp["forecast_category"] == "commit":
                values["commit"] += expected_revenue
            if forecast_type.include_closed and opp["forecast_category"] == "closed":
                values["closed"] += expected_revenue
            if opp["stage__stage_type"] == "won":
                values["actual"] += expected_revenue

        return values

    def _calculate_amount_values_from_data(self, opportunities, forecast_type):
        """Calculate amount values from opportunity data"""
        values = {
            "pipeline": 0,
            "best_case": 0,
            "commit": 0,
            "closed": 0,
            "actual": 0,
        }

        for opp in opportunities:
            amount = opp["amount"] or 0
            if (
                forecast_type.include_pipeline
                and opp["forecast_category"] == "pipeline"
            ):
                values["pipeline"] += amount
            if (
                forecast_type.include_best_case
                and opp["forecast_category"] == "best_case"
            ):
                values["best_case"] += amount
            if forecast_type.include_commit and opp["forecast_category"] == "commit":
                values["commit"] += amount
            if forecast_type.include_closed and opp["forecast_category"] == "closed":
                values["closed"] += amount
            if opp["stage__stage_type"] == "won":
                values["actual"] += amount

        return values

    # Keep the rest of your existing methods but with optimizations
    def generate_forecasts_for_user(self, user=None, forecast_type=None):
        """Generate/update forecasts for a specific user based on their opportunities"""
        target_user = user or self.user
        if not target_user or not self.fiscal_year:
            return

        if forecast_type:
            forecast_types = [forecast_type]
        else:
            forecast_types = ForecastType.objects.filter(is_active=True)

        periods = Period.objects.filter(quarter__fiscal_year=self.fiscal_year).order_by(
            "period_number"
        )

        for forecast_type_obj in forecast_types:
            for period in periods:
                self.create_or_update_period_forecast(
                    target_user, forecast_type_obj, period
                )

    def create_or_update_period_forecast(self, user, forecast_type, period):
        """Create or update forecast for a specific period automatically"""
        forecast, created = Forecast.objects.get_or_create(
            company=getattr(user, "company", None),
            owner=user,
            forecast_type=forecast_type,
            period=period,
            quarter=period.quarter,
            fiscal_year=period.quarter.fiscal_year,
            defaults={
                "name": f"{forecast_type.name} - {period.name}",
                "target_amount": self.get_target_for_period(user, period, "amount"),
                "target_quantity": self.get_target_for_period(user, period, "quantity"),
            },
        )

        calculated_data = self.calculate_forecast_values(user, period, forecast_type)

        if forecast_type.is_quantity_based:
            forecast.pipeline_quantity = calculated_data["pipeline"]
            forecast.best_case_quantity = calculated_data["best_case"]
            forecast.commit_quantity = calculated_data["commit"]
            forecast.closed_quantity = calculated_data["closed"]
            forecast.actual_quantity = calculated_data["actual"]

            if not forecast.target_quantity:
                forecast.target_quantity = self.get_target_for_period(
                    user, period, "quantity"
                )
        else:
            forecast.pipeline_amount = calculated_data["pipeline"]
            forecast.best_case_amount = calculated_data["best_case"]
            forecast.commit_amount = calculated_data["commit"]
            forecast.closed_amount = calculated_data["closed"]
            forecast.actual_amount = calculated_data["actual"]

            if not forecast.target_amount:
                forecast.target_amount = self.get_target_for_period(
                    user, period, "amount"
                )

        forecast.save()
        return forecast

    def calculate_forecast_values(self, user, period, forecast_type):
        """Calculate forecast values based on opportunities in the period"""
        base_query = Q(
            owner=user, close_date__range=[period.start_date, period.end_date]
        )

        conditions_query = self.get_cached_conditions_query(forecast_type)
        if conditions_query:
            base_query &= conditions_query

        opportunities = Opportunity.objects.filter(base_query)

        if forecast_type.is_quantity_based:
            return self._calculate_quantity_values(opportunities, forecast_type)
        elif forecast_type.is_revenue_expected_based:
            return self._calculate_expected_amount_values(opportunities, forecast_type)
        else:
            return self._calculate_amount_values(opportunities, forecast_type)

    def build_conditions_query(self, forecast_type):
        """Build Django Q object from horilla_crm.forecastCondition records"""
        conditions = forecast_type.conditions.filter(is_active=True).order_by("order")

        if not conditions.exists():
            return None

        main_query = Q()
        current_group = []
        current_logical_op = "and"

        for condition in conditions:
            condition_q = self.build_single_condition_query(condition)

            if not current_group:
                current_group.append(condition_q)
                current_logical_op = condition.logical_operator
            elif condition.logical_operator == current_logical_op:
                current_group.append(condition_q)
            else:
                if current_group:
                    if current_logical_op == "and":
                        group_query = Q()
                        for cq in current_group:
                            group_query &= cq
                    else:
                        group_query = Q()
                        for cq in current_group:
                            group_query |= cq

                    if not main_query.children and not main_query.negated:
                        main_query = group_query
                    else:
                        main_query &= group_query

                current_group = [condition_q]
                current_logical_op = condition.logical_operator

        if current_group:
            if current_logical_op == "and":
                group_query = Q()
                for cq in current_group:
                    group_query &= cq
            else:
                group_query = Q()
                for cq in current_group:
                    group_query |= cq

            if not main_query.children and not main_query.negated:
                main_query = group_query
            else:
                main_query &= group_query

        return main_query

    def build_single_condition_query(self, condition):
        """Build a single condition query based on field, operator, and value"""
        field = condition.field
        operator = condition.operator
        value = condition.value

        operator_map = {
            "equals": {field: value},
            "not_equals": {field: value},
            "contains": {f"{field}__icontains": value},
            "not_contains": {f"{field}__icontains": value},
            "starts_with": {f"{field}__istartswith": value},
            "ends_with": {f"{field}__iendswith": value},
            "greater_than": {f"{field}__gt": self.convert_value(value, field)},
            "greater_than_equal": {f"{field}__gte": self.convert_value(value, field)},
            "less_than": {f"{field}__lt": self.convert_value(value, field)},
            "less_than_equal": {f"{field}__lte": self.convert_value(value, field)},
            "is_empty": {f"{field}__isnull": True},
            "is_not_empty": {f"{field}__isnull": True},
        }

        if operator in ["not_equals", "not_contains"]:
            return ~Q(**operator_map[operator.replace("not_", "")])
        elif operator == "is_empty":
            return Q(**{f"{field}__isnull": True}) | Q(**{field: ""})
        elif operator == "is_not_empty":
            return ~(Q(**{f"{field}__isnull": True}) | Q(**{field: ""}))
        else:
            return Q(**operator_map.get(operator, {field: value}))

    def convert_value(self, value, _field):
        """Convert string value to appropriate type based on field"""
        try:
            if "." in str(value):
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            return value

    def _calculate_quantity_values(self, opportunities, forecast_type):
        """Calculate quantity values (count of deals) by forecast category"""
        values = {
            "pipeline": 0,
            "best_case": 0,
            "commit": 0,
            "closed": 0,
            "actual": 0,
        }

        # Use database aggregation instead of Python loops for better performance
        if forecast_type.include_pipeline:
            values["pipeline"] = opportunities.filter(
                forecast_category="pipeline"
            ).count()
        if forecast_type.include_best_case:
            values["best_case"] = opportunities.filter(
                forecast_category="best_case"
            ).count()
        if forecast_type.include_commit:
            values["commit"] = opportunities.filter(forecast_category="commit").count()
        if forecast_type.include_closed:
            values["closed"] = opportunities.filter(forecast_category="closed").count()

        values["actual"] = opportunities.filter(stage__stage_type="won").count()

        return values

    def _calculate_expected_amount_values(self, opportunities, forecast_type):
        """Calculate expected amount values using expected_revenue field"""
        values = {
            "pipeline": 0,
            "best_case": 0,
            "commit": 0,
            "closed": 0,
            "actual": 0,
        }

        if forecast_type.include_pipeline:
            values["pipeline"] = (
                opportunities.filter(forecast_category="pipeline").aggregate(
                    total=Sum("expected_revenue")
                )["total"]
                or 0
            )

        if forecast_type.include_best_case:
            values["best_case"] = (
                opportunities.filter(forecast_category="best_case").aggregate(
                    total=Sum("expected_revenue")
                )["total"]
                or 0
            )

        if forecast_type.include_commit:
            values["commit"] = (
                opportunities.filter(forecast_category="commit").aggregate(
                    total=Sum("expected_revenue")
                )["total"]
                or 0
            )

        if forecast_type.include_closed:
            values["closed"] = (
                opportunities.filter(forecast_category="closed").aggregate(
                    total=Sum("expected_revenue")
                )["total"]
                or 0
            )

        values["actual"] = (
            opportunities.filter(stage__stage_type="won").aggregate(
                total=Sum("expected_revenue")
            )["total"]
            or 0
        )

        return values

    def _calculate_amount_values(self, opportunities, forecast_type):
        """Calculate actual amount values using amount field"""
        values = {
            "pipeline": 0,
            "best_case": 0,
            "commit": 0,
            "closed": 0,
            "actual": 0,
        }

        if forecast_type.include_pipeline:
            values["pipeline"] = (
                opportunities.filter(forecast_category="pipeline").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

        if forecast_type.include_best_case:
            values["best_case"] = (
                opportunities.filter(forecast_category="best_case").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

        if forecast_type.include_commit:
            values["commit"] = (
                opportunities.filter(forecast_category="commit").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

        if forecast_type.include_closed:
            values["closed"] = (
                opportunities.filter(forecast_category="closed").aggregate(
                    total=Sum("amount")
                )["total"]
                or 0
            )

        values["actual"] = (
            opportunities.filter(stage__stage_type="won").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        return values

    def get_target_for_period(self, user, period, target_type="amount"):
        """Get target amount or quantity for user in specific period"""
        target = ForecastTarget.objects.filter(
            assigned_to=user, period=period, is_active=True
        ).first()

        if target_type == "quantity":
            return getattr(target, "quantity_target", 0) if target else 0
        else:
            return target.target_amount if target else 0

    def bulk_generate_forecasts(self, users=None, periods=None):
        """Bulk generate forecasts for multiple users and periods"""
        if not users:
            users = HorillaUser.objects.filter(is_active=True)

        if not periods:
            periods = Period.objects.filter(quarter__fiscal_year=self.fiscal_year)

        forecast_types = ForecastType.objects.filter(is_active=True)

        for user in users:
            for forecast_type in forecast_types:
                for period in periods:
                    self.create_or_update_period_forecast(user, forecast_type, period)
