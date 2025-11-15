from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.contenttypes.models import ContentType

from .models import *

admin.site.register(KanbanGroupBy)
admin.site.register(ListColumnVisibility)
admin.site.register(PinnedView)
admin.site.register(SavedFilterList)
admin.site.register(MultipleCurrency)
admin.site.register(ActiveTab)
admin.site.register(ContentType)
admin.site.register(Company)
admin.site.register(FiscalYear)
admin.site.register(Holiday)
admin.site.register(FiscalYearInstance)
admin.site.register(Quarter)
admin.site.register(Period)
admin.site.register(DatedConversionRate)
admin.site.register(BusinessHour)
admin.site.register(Department)
admin.site.register(Role)
admin.site.register(RecycleBin)
admin.site.register(PartnerRole)
admin.site.register(CustomerRole)
admin.site.register(TeamRole)
admin.site.register(ScoringRule)
admin.site.register(ScoringCriterion)
admin.site.register(ScoringCondition)
admin.site.register(RecycleBinPolicy)
admin.site.register(RecentlyViewed)
admin.site.register(ImportHistory)
admin.site.register(HorillaAttachment)
admin.site.register(ExportSchedule)


@admin.register(HorillaUser)
class HorillaUserAdmin(UserAdmin):
    model = HorillaUser
    list_display = ["username", "email", "is_active", "is_staff"]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "profile",
                    "contact_number",
                    "city",
                    "state",
                    "country",
                    "zip_code",
                )
            },
        ),
        ("Work Info", {"fields": ("company", "department", "role")}),
        (
            "Preferences",
            {
                "fields": (
                    "language",
                    "time_zone",
                    "currency",
                    "time_format",
                    "date_format",
                    "number_grouping",
                    "date_time_format",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "email",
                    "city",
                    "state",
                    "country",
                    "zip_code",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )
