import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from horilla_core.decorators import htmx_required

from .models import Report, ReportFolder

REPORTS_JSON_PATH = (
    Path(settings.BASE_DIR) / "horilla_crm" / "reports" / "load_data" / "reports.json"
)


@method_decorator(htmx_required, name="dispatch")
class LoadDefaultReportsModalView(LoginRequiredMixin, TemplateView):
    template_name = "reports/load_default_reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with open(REPORTS_JSON_PATH, "r") as f:
            data = json.load(f)

        # Only include "reports.report" entries
        reports = [
            {
                "pk": entry["pk"],
                "name": entry["fields"]["name"],
                "folder": entry["fields"]["folder"],
            }
            for entry in data
            if entry["model"] == "reports.report"
        ]

        context["reports"] = reports
        return context


@method_decorator(htmx_required, name="dispatch")
class CreateSelectedDefaultReportsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        selected_reports = request.POST.getlist("selected_reports")

        with open(REPORTS_JSON_PATH, "r") as f:
            data = json.load(f)

        all_reports = [
            entry["fields"] for entry in data if entry["model"] == "reports.report"
        ]
        folder_lookup = {
            entry["pk"]: entry["fields"]
            for entry in data
            if entry["model"] == "reports.reportfolder"
        }

        created_reports = []
        skipped_reports = []

        for report_data in all_reports:
            report_name = report_data["name"]
            if report_name not in selected_reports:
                continue

            # Check if report already exists
            if Report.objects.filter(name=report_name).exists():
                skipped_reports.append(report_name)
                continue

            folder = None
            folder_pk = report_data.get("folder")
            if folder_pk:
                folder_data = folder_lookup.get(folder_pk)
                if folder_data:
                    folder = self._ensure_folder(folder_data, folder_lookup, request)

            # 🔹 Resolve module dynamically from app_label and model
            module_info = report_data.get("module")
            module_ct = None
            if isinstance(module_info, dict):
                app_label = module_info.get("app_label")
                model_name = module_info.get("model")
                if app_label and model_name:
                    try:
                        module_ct = ContentType.objects.get(
                            app_label=app_label, model=model_name
                        )
                    except ContentType.DoesNotExist:
                        continue  # skip if invalid

            if module_ct:
                Report.objects.create(
                    name=report_name,
                    folder=folder,
                    company=getattr(
                        request,
                        "active_company",
                        getattr(request.user, "company", None),
                    ),
                    created_by=request.user,
                    updated_by=request.user,
                    report_owner=request.user,
                    is_active=True,
                    module=module_ct,
                    selected_columns=report_data.get("selected_columns", ""),
                    row_groups=report_data.get("row_groups", ""),
                    column_groups=report_data.get("column_groups", ""),
                    aggregate_columns=report_data.get("aggregate_columns", ""),
                    filters=report_data.get("filters", ""),
                    chart_type=report_data.get("chart_type", ""),
                )
                created_reports.append(report_name)

        # Show appropriate messages
        if created_reports and skipped_reports:
            message = f"{len(created_reports)} report(s) loaded successfully. {len(skipped_reports)} report(s) already exist and were skipped."
            messages.success(self.request, message)
        elif created_reports:
            messages.success(self.request, "Reports loaded successfully")
        elif skipped_reports:
            messages.warning(self.request, "All selected reports already exist")
        else:
            messages.info(self.request, "No reports were processed")

        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")

    def _ensure_folder(self, folder_data, folder_lookup, request):
        """Create folder and parent if not exists (no pk dependency)."""
        folder_name = folder_data["name"]
        parent = None
        parent_pk = folder_data.get("parent")

        if parent_pk:
            parent_data = folder_lookup.get(parent_pk)
            if parent_data:
                parent = self._ensure_folder(parent_data, folder_lookup, request)

        folder, created = ReportFolder.objects.get_or_create(
            name=folder_name,
            defaults={
                "company": getattr(
                    request, "active_company", getattr(request.user, "company", None)
                ),
                "created_by": request.user,
                "updated_by": request.user,
                "report_folder_owner": request.user,
                "is_active": True,
                "parent": parent,
            },
        )
        return folder
