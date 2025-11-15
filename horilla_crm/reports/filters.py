import django_filters
from django.forms import JSONField

from horilla_crm.reports.models import Report
from horilla_generics.filters import HorillaFilterSet

from .models import Report  # Ensure your Report model is imported


class ReportFilter(HorillaFilterSet):
    class Meta:
        model = Report
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
