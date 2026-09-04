"""
This module defines the configurable field requiredness model.

A ``FieldRequirement`` row overrides whether one field of one model is required
on its forms, for one company. It exists so an installation can adapt a form to
its own process -- for example not demanding an email address on a lead --
without editing the model definition.
"""

# Third-party imports (Django)
from django.conf import settings

# First party imports (Horilla)
from horilla.contrib.core.models import Company, HorillaContentType, HorillaCoreModel
from horilla.core.exceptions import FieldDoesNotExist, ValidationError
from horilla.db import models
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .registry import (
    can_relax_requirement,
    get_excluded_fields,
    is_requirement_configurable,
    limit_content_types,
)


class FieldRequirement(HorillaCoreModel):
    """
    Per-company override for whether a model field is required on its forms.

    Only affects form validation. The underlying column is never altered, so a
    field can be relaxed only when the database already has a way to store an
    empty value for it -- enforced by :meth:`clean`.

    Reverse accessors include the app label so they do not clash with another
    model of the same class name (HorillaCoreModel defaults to ``%(class)s_*``).
    """

    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        limit_choices_to=limit_content_types,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("Model"),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("Company"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name=_("Created By"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name=_("Updated By"),
    )
    field_name = models.CharField(max_length=255, verbose_name=_("Field"))
    is_required = models.BooleanField(
        default=True,
        verbose_name=_("Required"),
        help_text=_(
            "When enabled the field must be filled in. When disabled the field "
            "becomes optional on create and edit forms."
        ),
    )

    class Meta:
        """
        Meta options for the FieldRequirement model.
        """

        verbose_name = _("Field Requirement")
        verbose_name_plural = _("Field Requirements")
        unique_together = (("content_type", "field_name", "company"),)
        ordering = ["content_type__model", "field_name"]

    def __str__(self):
        return f"{self.model_label} - {self.field_label}"

    @property
    def model_class(self):
        """Return the target model class, or None when it can no longer resolve."""
        if not self.content_type_id:
            return None
        return self.content_type.model_class()

    @property
    def model_label(self):
        """Return the target model's human-readable name.

        Falls back to the content type's own label when the model class can no
        longer be resolved, so a row for an uninstalled app still lists.
        """
        model = self.model_class
        if model is not None:
            return str(model._meta.verbose_name)
        if self.content_type_id:
            return str(self.content_type)
        return ""

    @property
    def model_field(self):
        """Return the target model field, or None when it no longer exists."""
        model = self.model_class
        if model is None or not self.field_name:
            return None
        try:
            return model._meta.get_field(self.field_name)
        except FieldDoesNotExist:
            return None

    @property
    def field_label(self):
        """Return the target field's human-readable name."""
        field = self.model_field
        if field is None:
            return self.field_name
        return str(field.verbose_name)

    @property
    def requirement_label(self):
        """Return a display label for the configured requiredness."""
        return _("Required") if self.is_required else _("Optional")

    def get_edit_url(self):
        """Return the URL for editing this override in the settings modal."""
        return reverse_lazy(
            "field_requirements:field_requirement_update_form",
            kwargs={"pk": self.pk},
        )

    def get_delete_url(self):
        """Return the URL for deleting this override from the settings page."""
        return reverse_lazy(
            "field_requirements:field_requirement_delete_view",
            kwargs={"pk": self.pk},
        )

    def clean(self):
        """Reject overrides that target unknown fields or would break saves."""
        super().clean()

        model = self.model_class
        if model is None:
            raise ValidationError({"content_type": _("Select a valid model.")})

        if not is_requirement_configurable(model):
            raise ValidationError(
                {
                    "content_type": _(
                        "%(model)s does not support configurable field requirements."
                    )
                    % {"model": model._meta.verbose_name}
                }
            )

        field = self.model_field
        if field is None:
            raise ValidationError(
                {
                    "field_name": _("%(field)s is not a field on %(model)s.")
                    % {"field": self.field_name, "model": model._meta.verbose_name}
                }
            )

        if self.field_name in get_excluded_fields(model):
            raise ValidationError({"field_name": _("This field cannot be configured.")})

        if not self.is_required and not can_relax_requirement(field):
            raise ValidationError(
                {
                    "is_required": _(
                        "%(field)s cannot be made optional because the database "
                        "has no way to store an empty value for it. Allow null "
                        "values on the field first."
                    )
                    % {"field": field.verbose_name}
                }
            )
