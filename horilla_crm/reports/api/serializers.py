"""
Serializers for horilla_crm.reports models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.reports.models import Report, ReportFolder


class ReportFolderSerializer(serializers.ModelSerializer):
    """Serializer for ReportFolder model"""

    report_folder_owner_details = HorillaUserSerializer(
        source="report_folder_owner", read_only=True
    )

    class Meta:
        model = ReportFolder
        fields = "__all__"


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model"""

    report_owner_details = HorillaUserSerializer(source="report_owner", read_only=True)
    folder_details = ReportFolderSerializer(source="folder", read_only=True)

    class Meta:
        model = Report
        fields = """__all__"""
