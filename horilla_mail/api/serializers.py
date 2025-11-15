"""
Serializers for horilla_mail models, consistent with horilla_core conventions
"""

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from horilla_mail.models import (
    HorillaMail,
    HorillaMailAttachment,
    HorillaMailConfiguration,
    HorillaMailTemplate,
)


class HorillaMailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorillaMailConfiguration
        fields = "__all__"

    def validate(self, attrs):
        # Ensure only one primary configuration per system
        is_primary = attrs.get(
            "is_primary", getattr(self.instance, "is_primary", False)
        )
        if is_primary:
            qs = HorillaMailConfiguration.objects.exclude(
                pk=getattr(self.instance, "pk", None)
            ).filter(is_primary=True)
            if qs.exists():
                raise serializers.ValidationError(
                    {"is_primary": "Another primary mail configuration already exists."}
                )
        return attrs


class HorillaMailSerializer(serializers.ModelSerializer):
    related_model = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = HorillaMail
        fields = "__all__"

    def validate(self, attrs):
        # Validate content_type and object_id for related_to
        content_type = attrs.get("content_type") or getattr(
            self.instance, "content_type", None
        )
        object_id = attrs.get("object_id") or getattr(self.instance, "object_id", None)
        if content_type and object_id is not None:
            try:
                model_class = ContentType.objects.get(pk=content_type.pk).model_class()
                if not model_class.objects.filter(pk=object_id).exists():
                    raise serializers.ValidationError(
                        {
                            "object_id": "Related object does not exist for the given content type."
                        }
                    )
            except ContentType.DoesNotExist:
                raise serializers.ValidationError(
                    {"content_type": "Invalid content type provided."}
                )
        return attrs


class HorillaMailAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorillaMailAttachment
        fields = "__all__"


class HorillaMailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorillaMailTemplate
        fields = "__all__"

    def validate(self, attrs):
        # Enforce unique_together (title, company)
        title = attrs.get("title") or getattr(self.instance, "title", None)
        company = attrs.get("company") or getattr(self.instance, "company", None)
        if title and company:
            qs = HorillaMailTemplate.objects.filter(title=title, company=company)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "title": "Mail template with this title already exists for the company."
                    }
                )
        return attrs
