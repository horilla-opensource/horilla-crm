"""
Serializers for horilla_keys models
"""

from rest_framework import serializers

from horilla_keys.models import ShortcutKey


class ShortcutKeySerializer(serializers.ModelSerializer):
    """Serializer for ShortcutKey model"""

    class Meta:
        model = ShortcutKey
        fields = "__all__"

    def validate(self, attrs):
        # Enforce unique_together (user, page) at the serializer level to avoid 500s
        user = attrs.get("user") or getattr(self.instance, "user", None)
        page = attrs.get("page") or getattr(self.instance, "page", None)

        if user and page:
            qs = ShortcutKey.objects.filter(user=user, page=page)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"page": "ShortcutKey for this user and page already exists."}
                )
        return attrs
