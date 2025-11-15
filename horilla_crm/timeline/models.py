"""Models for user calendar preferences and availability in Horilla CRM."""

from django.conf import settings
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from horilla_core.models import HorillaCoreModel


class UserCalendarPreference(HorillaCoreModel):
    """Model to store user calegit ndar preferences."""

    CALENDAR_TYPES = (
        ("task", _("Task")),
        ("event", _("Event")),
        ("meeting", _("Meeting")),
        ("unavailability", _("Un Availability")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="calendar_preferences",
        verbose_name=_("User"),
    )
    calendar_type = models.CharField(
        max_length=20, choices=CALENDAR_TYPES, verbose_name=_("Calendar Type")
    )
    color = models.CharField(max_length=10, verbose_name=_("Color"))
    is_selected = models.BooleanField(default=True, verbose_name=_("Is Selected"))

    class Meta:
        """Meta class for UserCalendarPreference model."""

        unique_together = (
            "user",
            "calendar_type",
            "company",
        )  # One preference per user per calendar type
        verbose_name = _("User Calendar Preference")
        verbose_name_plural = _("User Calendar Preferences")

    def __str__(self):
        return f"{self.user.username} - {self.calendar_type} - {self.color} (Selected: {self.is_selected})"


class UserAvailability(HorillaCoreModel):
    """Model to store user availability periods."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="unavailable_periods",
        verbose_name=_("User"),
    )
    from_datetime = models.DateTimeField(verbose_name=_("From"))
    to_datetime = models.DateTimeField(verbose_name=_("To"))
    reason = models.CharField(max_length=255, verbose_name=_("Reason"))

    class Meta:
        """Meta class for UserAvailability model."""

        verbose_name = _("User Unavailability")
        verbose_name_plural = _("User Unavailabilities")
        ordering = ["-from_datetime"]
        indexes = [
            models.Index(fields=["user", "from_datetime", "to_datetime"]),
        ]

    def __str__(self):
        return (
            f"{self.user} unavailable from {self.from_datetime} to {self.to_datetime}"
        )

    def is_currently_unavailable(self):
        """Check if the user is currently unavailable."""

        now = timezone.now()
        return self.from_datetime <= now <= self.to_datetime

    def update_mark_unavailability_url(self):
        """Generate URL for updating this unavailability record."""
        return reverse_lazy(
            "timeline:update_mark_unavailability", kwargs={"pk": self.pk}
        )

    def delete_mark_unavailability_url(self):
        """Generate URL for deleting this unavailability record."""
        return reverse_lazy(
            "timeline:delete_mark_unavailability", kwargs={"pk": self.pk}
        )
