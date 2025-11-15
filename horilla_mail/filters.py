import django_filters

from horilla_generics.filters import HorillaFilterSet
from horilla_mail.models import HorillaMailConfiguration, HorillaMailTemplate

# Define your horilla_mail filters here


class HorillaMailServerFilter(HorillaFilterSet):
    class Meta:
        model = HorillaMailConfiguration
        fields = "__all__"
        exclude = ["additional_info", "token"]
        search_fields = ["host", "username"]


class HorillaMailTemplateFilter(HorillaFilterSet):
    class Meta:
        model = HorillaMailTemplate
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["title"]
