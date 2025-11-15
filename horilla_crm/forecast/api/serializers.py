"""
Serializers for horilla_crm.forecast models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.forecast.models import (
    Forecast,
    ForecastTarget,
    ForecastTargetUser,
    ForecastType,
)


class ForecastTypeSerializer(serializers.ModelSerializer):
    """Serializer for ForecastType model"""

    class Meta:
        model = ForecastType
        fields = "__all__"


class ForecastSerializer(serializers.ModelSerializer):
    """Serializer for Forecast model"""

    owner_details = HorillaUserSerializer(source="owner", read_only=True)
    forecast_type_details = ForecastTypeSerializer(
        source="forecast_type", read_only=True
    )

    class Meta:
        model = Forecast
        fields = "__all__"


class ForecastTargetSerializer(serializers.ModelSerializer):
    """Serializer for ForecastTarget model"""

    assigned_to_details = HorillaUserSerializer(source="assigned_to", read_only=True)
    forcasts_type_details = ForecastTypeSerializer(
        source="forcasts_type", read_only=True
    )

    class Meta:
        model = ForecastTarget
        fields = "__all__"


class ForecastTargetUserSerializer(serializers.ModelSerializer):
    """Serializer for ForecastTargetUser model"""

    user_details = HorillaUserSerializer(source="user", read_only=True)
    forecast_target_details = ForecastTargetSerializer(
        source="forecast_target", read_only=True
    )

    class Meta:
        model = ForecastTargetUser
        fields = "__all__"
