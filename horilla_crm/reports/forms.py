from django import forms
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy

from horilla_crm.reports.models import Report, ReportFolder
from horilla_generics.forms import HorillaModelForm


# Define your reports forms here
class ReportForm(HorillaModelForm):

    class Meta:
        model = Report
        fields = ["name", "module", "folder", "selected_columns", "report_owner"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.request.user.is_superuser:
            self.fields["folder"].queryset = ReportFolder.objects.all()
        else:
            self.fields["folder"].queryset = ReportFolder.objects.filter(
                report_folder_owner=self.request.user
            )
        self.fields["module"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("reports:get_module_columns_htmx"),
                "hx-target": "#id_columns",
                "hx-trigger": "change",
                "hx-swap": "outerHTML",
                "hx-include": "[name='module']",
            }
        )

        self.fields["selected_columns"].widget = forms.SelectMultiple(
            attrs={
                "class": "js-example-basic-multiple headselect w-full",
                "id": "id_columns",
                "name": "selected_columns",
                "tabindex": "-1",
                "aria-hidden": "true",
                "multiple": True,
                "required": True,
            }
        )

    def clean_selected_columns(self):
        """Convert the list to comma-separated string and validate that at least one column is selected"""
        selected = self.cleaned_data.get("selected_columns", [])

        if isinstance(selected, str):
            if selected.startswith("[") and selected.endswith("]"):
                try:
                    import ast

                    selected = ast.literal_eval(selected)
                except:
                    selected = [
                        item.strip().strip("'\"")
                        for item in selected.strip("[]").split(",")
                        if item.strip()
                    ]
            else:
                selected = [selected] if selected.strip() else []

        if isinstance(selected, list):
            filtered_selected = [item for item in selected if item.strip()]
            if not filtered_selected:
                raise forms.ValidationError("At least one column must be selected.")
            return ",".join(filtered_selected)

        raise forms.ValidationError("At least one column must be selected.")
