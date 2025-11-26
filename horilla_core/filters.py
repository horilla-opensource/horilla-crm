from horilla_core.models import (
    Company,
    CustomerRole,
    Department,
    Holiday,
    HorillaUser,
    PartnerRole,
    ScoringRule,
    TeamRole,
)
from horilla_generics.filters import HorillaFilterSet


class UserFilter(HorillaFilterSet):
    class Meta:
        model = HorillaUser
        fields = "__all__"
        exclude = ["profile"]
        search_fields = ["first_name", "email", "last_name"]


class CompanyFilter(HorillaFilterSet):
    class Meta:
        model = Company
        fields = "__all__"
        exclude = ["icon"]
        search_fields = ["name"]


class DepartmentFilter(HorillaFilterSet):
    class Meta:
        model = Department
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["department_name"]


class TeamRoleFilter(HorillaFilterSet):
    class Meta:
        model = TeamRole
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["team_role_name"]


class CustomerRoleFilter(HorillaFilterSet):
    class Meta:
        model = CustomerRole
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["customer_role_name"]


class PartnerRoleFilter(HorillaFilterSet):
    class Meta:
        model = PartnerRole
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["customer_role_name"]


class ScoringRuleFilter(HorillaFilterSet):
    class Meta:
        model = ScoringRule
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["customer_role_name"]


class HolidayFilter(HorillaFilterSet):
    class Meta:
        model = Holiday
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
