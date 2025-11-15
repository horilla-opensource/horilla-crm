"""
Serializers for horilla_core models
"""

from rest_framework import serializers

from horilla_core.models import (
    BusinessHour,
    Company,
    CustomerRole,
    Department,
    Holiday,
    HorillaAttachment,
    HorillaUser,
    ImportHistory,
    PartnerRole,
    Role,
    ScoringCriterion,
    ScoringRule,
    TeamRole,
)


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model"""

    class Meta:
        model = Company
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model"""

    class Meta:
        model = Department
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model"""

    class Meta:
        model = Role
        fields = "__all__"


class HorillaUserSerializer(serializers.ModelSerializer):
    """Serializer for HorillaUser model"""

    class Meta:
        model = HorillaUser
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = HorillaUser.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if "password" in validated_data:
            password = validated_data.pop("password")
            instance.set_password(password)
        return super().update(instance, validated_data)


class BusinessHourSerializer(serializers.ModelSerializer):
    """Serializer for BusinessHour model"""

    class Meta:
        model = BusinessHour
        fields = "__all__"


class TeamRoleSerializer(serializers.ModelSerializer):
    """Serializer for TeamRole model"""

    class Meta:
        model = TeamRole
        fields = "__all__"


class CustomerRoleSerializer(serializers.ModelSerializer):
    """Serializer for CustomerRole model"""

    class Meta:
        model = CustomerRole
        fields = "__all__"


class PartnerRoleSerializer(serializers.ModelSerializer):
    """Serializer for PartnerRole model"""

    class Meta:
        model = PartnerRole
        fields = "__all__"


class ScoringRuleSerializer(serializers.ModelSerializer):
    """Serializer for ScoringRule model"""

    class Meta:
        model = ScoringRule
        fields = "__all__"


class ScoringCriterionSerializer(serializers.ModelSerializer):
    """Serializer for ScoringCriterion model"""

    class Meta:
        model = ScoringCriterion
        fields = "__all__"


class ImportHistorySerializer(serializers.ModelSerializer):
    """Serializer for ImportHistory model"""

    class Meta:
        model = ImportHistory
        fields = "__all__"


class HorillaAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for HorillaAttachment model"""

    class Meta:
        model = HorillaAttachment
        fields = "__all__"


class HolidaySerializer(serializers.ModelSerializer):
    """Serializer for Holiday model"""

    class Meta:
        model = Holiday
        fields = "__all__"
