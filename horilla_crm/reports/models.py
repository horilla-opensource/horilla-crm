import json

from django.conf import settings
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.registry.feature import feature_enabled
from horilla_core.models import HorillaContentType, HorillaCoreModel
from horilla_utils.methods import render_template


@feature_enabled(import_data=True, export_data=True, global_search=True)
class ReportFolder(HorillaCoreModel):
    name = models.CharField(max_length=200, verbose_name=_("Folder Name"))
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_("Folder"),
    )
    is_favourite = models.BooleanField(default=False)
    report_folder_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_folders",
        verbose_name=_("Folder Owner"),
    )

    OWNER_FIELDS = ["report_folder_owner"]

    def __str__(self):
        return self.name

    def get_item_type(self):
        return "Folder"

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """
        return reverse_lazy("reports:report_folder_detail", kwargs={"pk": self.pk})

    def actions(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="reports/folder_actions.html",
            context={"instance": self},
        )

    def actions_detail(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="reports/folder_actions_detail.html",
            context={"instance": self},
        )


@feature_enabled(import_data=True, export_data=True, global_search=True)
class Report(HorillaCoreModel):
    """Model to represent a report in the system."""

    CHART_TYPES = [
        ("column", _("Column Chart")),
        ("line", _("Line Chart")),
        ("pie", _("Pie Chart")),
        ("funnel", _("Funnel")),
        ("bar", _("Bar Chart")),
        ("donut", _("Donut")),
        ("stacked_vertical", _("Stacked Vertical Chart")),
        ("stacked_horizontal", _("Stacked Horizontal Chart")),
        ("scatter", _("Scatter Chart")),
    ]
    report_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports",
        verbose_name=_("Report Owner"),
    )

    name = models.CharField(max_length=200, verbose_name="Report Name")
    module = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Module"),
        limit_choices_to={
            "model__in": [
                "account",
                "contact",
                "lead",
                "campaign",
                "opportunity",
            ]
        },
    )
    folder = models.ForeignKey(
        ReportFolder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Folder"),
    )

    selected_columns = models.TextField(blank=True)
    row_groups = models.TextField(blank=True)
    column_groups = models.TextField(blank=True)
    aggregate_columns = models.TextField(blank=True)
    filters = models.TextField(blank=True)

    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, default="bar")
    chart_field = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Chart Field")
    )
    chart_field_stacked = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Secondary Field")
    )

    is_favourite = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_reports"
    )

    OWNER_FIELDS = ["report_owner"]

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return self.name

    def get_item_type(self):
        return "Report"

    @property
    def model_class(self):
        """Get the actual model class from ContentType"""
        return self.module.model_class()

    @property
    def module_verbose_name(self):
        """Return the verbose name of the module's model"""
        model = self.model_class
        return model._meta.verbose_name.title()

    @property
    def selected_columns_list(self):
        """Get selected columns as list"""
        if self.selected_columns:
            return [
                col.strip() for col in self.selected_columns.split(",") if col.strip()
            ]
        return []

    @property
    def row_groups_list(self):
        """Get row groups as list"""
        if self.row_groups:
            return [
                group.strip() for group in self.row_groups.split(",") if group.strip()
            ]
        return []

    @property
    def column_groups_list(self):
        """Get column groups as list"""
        if self.column_groups:
            return [
                group.strip()
                for group in self.column_groups.split(",")
                if group.strip()
            ]
        return []

    @property
    def aggregate_columns_dict(self):
        """Get aggregate columns as a list of dictionaries with validated structure"""
        if not self.aggregate_columns:
            return []

        try:
            data = json.loads(self.aggregate_columns)
            # Convert single dict to list for backward compatibility
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                return []

            # Validate each item has 'field' and 'aggfunc' keys
            validated_data = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                # Ensure 'field' and 'aggfunc' exist, provide defaults if missing
                if "field" not in item or not item["field"]:
                    continue  # Skip invalid entries
                item.setdefault(
                    "aggfunc", "sum"
                )  # Default to 'sum' if 'aggfunc' missing
                validated_data.append(item)

            return validated_data
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def filters_dict(self):
        """Get filters as dictionary"""
        if self.filters:
            try:
                return json.loads(self.filters)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def get_available_fields(self):
        """Get all non-JSON fields from the selected model"""
        if not self.model_class:
            return []

        fields_info = []
        excluded_field_types = [
            "JSONField",
            "TextField",
            "BinaryField",
            "FileField",
            "ImageField",
        ]

        for field in self.model_class._meta.get_fields():
            # Skip reverse relations and excluded field types
            if hasattr(field, "related_model") and field.related_model:
                continue

            field_type = field.__class__.__name__
            if field_type in excluded_field_types:
                continue

            if hasattr(field, "verbose_name"):
                fields_info.append(
                    {
                        "name": field.name,
                        "verbose_name": str(field.verbose_name),
                        "type": field_type,
                        "is_relation": hasattr(field, "related_model"),
                        "is_numeric": field_type
                        in [
                            "IntegerField",
                            "FloatField",
                            "DecimalField",
                            "BigIntegerField",
                        ],
                        "choices": getattr(field, "choices", None),
                    }
                )

        return fields_info

    def get_available_columns_choices(self):
        """Get available columns as choices for the multiple select field"""
        fields = self.get_available_fields()
        return [
            (field["name"], f"{field['verbose_name']} ({field['name']})")
            for field in fields
        ]

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """

        return reverse_lazy("reports:report_detail", kwargs={"pk": self.pk})

    def get_field_choices(self, field_name):
        """Get choices for a choice field or related objects for a foreign key."""
        try:
            field = self.model_class._meta.get_field(field_name)
            if hasattr(field, "choices") and field.choices:
                return [
                    {"value": value, "display": display}
                    for value, display in field.choices
                ]
            elif hasattr(field, "related_model") and field.related_model:
                related_objects = field.related_model.objects.all()
                return [
                    {"value": obj.pk, "display": str(obj)} for obj in related_objects
                ]
            return []
        except:
            return []

    def is_choice_or_foreign_key_field(self, field_name):
        """Check if a field is a choice field or foreign key."""
        try:
            field = self.model_class._meta.get_field(field_name)
            return (hasattr(field, "choices") and field.choices) or (
                hasattr(field, "related_model") and field.related_model
            )
        except:
            return False

    def actions(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="reports/actions.html",
            context={"instance": self},
        )

    def actions_detail(self):
        """
        This method for get custom column for action.
        """

        return render_template(
            path="reports/report_actions_detail.html",
            context={"instance": self},
        )
