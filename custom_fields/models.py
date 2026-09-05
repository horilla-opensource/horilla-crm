from horilla.contrib.core.models import HorillaContentType, HorillaCoreModel
from horilla.db import models
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _


class CustomFieldDefinition(HorillaCoreModel):
    """
    Defines a user-created custom field attached to a specific model
    (currently Lead or Opportunity).
    """

    FIELD_TYPES = [
        ("small_text", _("Small Text")),
        ("large_text", _("Large Text")),
        ("number", _("Number")),
        ("choice", _("Multiple Choice")),
    ]

    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Model"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Field Name"))
    field_type = models.CharField(
        max_length=20, choices=FIELD_TYPES, verbose_name=_("Field Type")
    )
    is_required = models.BooleanField(default=False, verbose_name=_("Required"))
    choices = models.TextField(
        blank=True,
        help_text=_("Comma-separated list of choices (only for Multiple Choice type)"),
        verbose_name=_("Choices"),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))

    class Meta:
        ordering = ["order", "pk"]
        unique_together = [("content_type", "name", "company")]
        verbose_name = _("Custom Field")
        verbose_name_plural = _("Custom Fields")

    def __str__(self):
        return self.name

    def get_edit_url(self):
        return reverse_lazy("custom_fields:edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("custom_fields:delete", kwargs={"pk": self.pk})

    def get_choices_list(self):
        if not self.choices:
            return []
        return [c.strip() for c in self.choices.split(",") if c.strip()]


class CustomFieldValue(HorillaCoreModel):
    """
    Stores the value of a custom field for a specific object instance.
    """

    field_definition = models.ForeignKey(
        CustomFieldDefinition,
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name=_("Field Definition"),
    )
    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Model"),
    )
    object_id = models.PositiveIntegerField(verbose_name=_("Object ID"))

    value_text = models.TextField(blank=True, default="", verbose_name=_("Value"))
    value_number = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Numeric Value"),
    )

    class Meta:
        unique_together = [("field_definition", "content_type", "object_id")]
        verbose_name = _("Custom Field Value")
        verbose_name_plural = _("Custom Field Values")

    def __str__(self):
        return f"{self.field_definition.name}: {self.get_value()}"

    def get_value(self):
        if self.field_definition.field_type == "number":
            return self.value_number
        return self.value_text

    def set_value(self, val):
        if self.field_definition.field_type == "number":
            from decimal import Decimal, InvalidOperation

            try:
                self.value_number = Decimal(str(val)) if val not in (None, "") else None
            except (InvalidOperation, ValueError):
                self.value_number = None
            self.value_text = ""
        else:
            self.value_text = str(val) if val is not None else ""
            self.value_number = None
