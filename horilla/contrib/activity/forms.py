"""
Forms module for Activity-related operations including Meetings,
Calls, Events, and general Activity creation.
"""

# Standard library imports
from collections import OrderedDict

# Third-party imports (Django)
from django import forms
from django.forms import ValidationError

from horilla.auth.models import User
from horilla.contrib.core.mixins import OwnerQuerysetMixin
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.forms import HorillaModelForm

# First party imports (Horilla)
from horilla.db.models import Q
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .models import Activity


class MeetingsForm(OwnerQuerysetMixin, HorillaModelForm):
    """Form for filtering meetings"""

    meeting_provider = forms.ChoiceField(
        choices=[],
        required=False,
        label=_("Meeting Provider"),
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-primary-500",
                "data-online-field": "true",
                "id": "id_meeting_provider",
            }
        ),
    )

    field_order = [
        "object_id",
        "content_type",
        "title",
        "subject",
        "status",
        "owner",
        "start_datetime",
        "end_datetime",
        "participants",
        "meeting_host",
        "is_all_day",
        "is_online",
        "location",
        "meeting_provider",
        "reminder",
        "mail_template",
        "activity_type",
    ]

    class Meta:
        """
        Meta class for MeetingsForm
        """

        model = Activity
        fields = "__all__"
        exclude = [
            "description",
            "assigned_to",
            "task_priority",
            "due_datetime",
            "recipient_email",
            "call_duration_display",
            "call_duration_seconds",
            "call_type",
            "call_purpose",
            "notes",
            "google_event_id",
            "meeting_url",
            "external_participants",
        ]

        widgets = {
            "is_all_day": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "hx-trigger": "click",
                    "hx-swap": "outerHTML",
                    "hx-select": "#activity-form-view",
                    "hx-include": "#activity-form-view",
                    "hx-target": "#activity-form-view",
                }
            ),
            "is_online": forms.CheckboxInput(
                attrs={
                    "onchange": "toggleMeetingUrlField(this)",
                    "hx-trigger": "change",
                    "hx-swap": "outerHTML",
                    "hx-select": "#activity-form-view",
                    "hx-include": "#activity-form-view",
                    "hx-target": "#activity-form-view",
                    "hx-vals": '{"_toggle_field": "is_online"}',
                }
            ),
            "reminder": forms.Select(
                attrs={
                    "class": "w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-primary-500",
                }
            ),
            "object_id": forms.HiddenInput(),
            "content_type": forms.HiddenInput(),
            "activity_type": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Determine is_online before all-day handling (online meetings need start/end times)
        is_online = self.data.get("is_online") if self.data else None
        if is_online is None:
            if self.instance.pk:
                is_online = self.instance.is_online
            else:
                is_online = self.initial.get("is_online", False)
        is_online = is_online in ("on", True, "true", "True")

        if self.instance.pk:
            online_hx = f"/activity/meeting-update-form/{self.instance.pk}/"
            self.fields["is_all_day"].widget.attrs.update(
                {
                    "hx-get": (
                        f"/activity/meeting-update-form/{self.instance.pk}/"
                        "?toggle_is_all_day=true"
                    )
                }
            )
        else:
            online_hx = "/activity/meeting-create-form/"
            self.fields["is_all_day"].widget.attrs.update(
                {"hx-get": "/activity/meeting-create-form/"}
            )
        self.fields["is_online"].widget.attrs.update({"hx-post": online_hx})

        if is_online:
            self.fields["is_all_day"].widget = forms.HiddenInput()
            self.fields["is_all_day"].required = False
            self.initial["is_all_day"] = False
            self.fields["location"].widget = forms.HiddenInput()
            self.fields["location"].required = False
        else:
            self.fields["location"].required = True
            is_all_day = (
                self.data.get("is_all_day", False)
                if self.data
                else self.initial.get("is_all_day")
            )
            if is_all_day == "on":
                is_all_day = True
            elif is_all_day in ("off", False):
                is_all_day = False

            if is_all_day:
                self.fields["start_datetime"].widget = forms.HiddenInput()
                self.initial["start_datetime"] = None
                self.fields["end_datetime"].widget = forms.HiddenInput()
                self.initial["end_datetime"] = None

        # Build provider choices from connected accounts
        user = getattr(self._request, "user", None) if self._request else None
        provider_choices = self._get_provider_choices(user)
        self.fields["meeting_provider"].choices = provider_choices
        self.fields["meeting_provider"].required = False

        # Show/hide provider dropdown with is_online toggle
        self.fields["meeting_provider"].widget.attrs.update(
            {"data-online-field": "true"}
        )
        if not is_online:
            self.fields["meeting_provider"].widget.attrs.update(
                {"data-initially-hidden": "true"}
            )

        # Limit mail_template choices to templates linked to Activity or with no content type
        try:
            from horilla.contrib.mail.models import HorillaMailTemplate

            activity_ct = HorillaContentType.objects.filter(
                app_label="activity", model="activity"
            ).first()
            if activity_ct:
                self.fields["mail_template"].queryset = (
                    HorillaMailTemplate.objects.filter(
                        Q(content_type=activity_ct) | Q(content_type__isnull=True)
                    )
                )
            else:
                self.fields["mail_template"].queryset = (
                    HorillaMailTemplate.objects.filter(content_type__isnull=True)
                )
        except Exception:
            pass
        self.fields["mail_template"].help_text = (
            "Optional. Select a template to override the default invitation email design."
        )

    def _get_provider_choices(self, user):
        choices = [("", "— Select Provider —")]
        if not user:
            return choices
        try:
            from horilla.contrib.calendar.models import GoogleCalendarConfig
            from horilla.contrib.meeting.models import (
                MeetingIntegrationSetting,
                MicrosoftTeamsOAuthConfig,
                ZoomOAuthConfig,
            )

            company = getattr(user, "company", None)
            if not company or not MeetingIntegrationSetting.user_can_access(
                user, company
            ):
                return choices
            if ZoomOAuthConfig.objects.filter(
                user=user, token__has_key="access_token"
            ).exists():
                choices.append(("zoom", "Zoom"))
            gcal = GoogleCalendarConfig.objects.filter(user=user).first()
            from horilla.contrib.meeting.models import UserMeetingConfig

            meet_enabled = UserMeetingConfig.objects.filter(
                user=user, provider="google_meet"
            ).exists()
            if gcal and gcal.is_connected() and meet_enabled:
                choices.append(("google_meet", "Google Meet"))
            if MicrosoftTeamsOAuthConfig.objects.filter(
                user=user, token__has_key="access_token"
            ).exists():
                choices.append(("ms_teams", "Microsoft Teams"))
        except Exception:
            pass
        return choices

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        is_all_day = cleaned_data.get("is_all_day")
        if cleaned_data.get("is_online"):
            cleaned_data["is_all_day"] = False
            is_all_day = False
            cleaned_data["location"] = ""
        else:
            loc = (cleaned_data.get("location") or "").strip()
            cleaned_data["location"] = loc
            if not loc and "location" not in self.errors:
                self.add_error(
                    "location",
                    ValidationError(
                        "In-person meetings require a location (room, building, or address)."
                    ),
                )

        # Read the hidden email list posted by the pills widget
        raw = ""
        if self.data:
            raw = self.data.get("external_participants_email", "") or ""
        emails = [e.strip().lower() for e in raw.split(",") if e.strip()]
        cleaned_data["external_participants"] = emails

        if not is_all_day and start_datetime and end_datetime:
            if start_datetime.date() == end_datetime.date():
                if start_datetime.time() >= end_datetime.time():
                    raise ValidationError(
                        {
                            "end_datetime": (
                                "End time must be later than start time "
                                "on the same date."
                            )
                        }
                    )
            elif end_datetime <= start_datetime:
                # Different dates: validate full datetime
                raise ValidationError(
                    {
                        "end_datetime": "End date and time must be later than start date and time."
                    }
                )
        return cleaned_data


class LogCallForm(OwnerQuerysetMixin, HorillaModelForm):
    """Form for filtering log calls"""

    field_order = [
        "object_id",
        "content_type",
        "subject",
        "owner",
        "call_purpose",
        "call_type",
        "status",
        "notes",
        "activity_type",
    ]

    class Meta:
        """
        Meta class for LogCallForm
        """

        model = Activity
        fields = "__all__"
        exclude = [
            "description",
            "title",
            "start_datetime",
            "end_datetime",
            "location",
            "is_online",
            "meeting_provider",
            "meeting_url",
            "is_all_day",
            "assigned_to",
            "participants",
            "meeting_host",
            "task_priority",
            "due_datetime",
            "recipient_email",
            "call_duration_display",
            "call_duration_seconds",
            "google_event_id",
            "external_participants",
            "reminder",
            "mail_template",
        ]
        widgets = {
            "object_id": forms.HiddenInput(),
            "content_type": forms.HiddenInput(),
            "activity_type": forms.HiddenInput(),
        }


class EventForm(OwnerQuerysetMixin, HorillaModelForm):
    """Form for filtering meetings"""

    field_order = [
        "object_id",
        "content_type",
        "title",
        "subject",
        "owner",
        "start_datetime",
        "end_datetime",
        "location",
        "assigned_to",
        "status",
        "is_all_day",
        "activity_type",
    ]

    class Meta:
        """
        Meta class for EventForm
        """

        model = Activity
        fields = "__all__"
        exclude = [
            "description",
            "call_purpose",
            "call_type",
            "call_duration_display",
            "call_duration_seconds",
            "notes",
            "task_priority",
            "due_datetime",
            "recipient_email",
            "is_online",
            "meeting_provider",
            "meeting_url",
            "participants",
            "meeting_host",
            "google_event_id",
            "external_participants",
            "reminder",
            "mail_template",
        ]

        widgets = {
            "is_all_day": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                    "hx-trigger": "click",
                    "hx-swap": "outerHTML",
                    "hx-select": "#activity-form-view",
                    "hx-include": "#activity-form-view",
                    "hx-target": "#activity-form-view",
                }
            ),
            "object_id": forms.HiddenInput(),
            "content_type": forms.HiddenInput(),
            "activity_type": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["is_all_day"].widget.attrs.update(
                {
                    "hx-get": (
                        f"/activity/event-update-form/{self.instance.pk}/"
                        "?toggle_is_all_day=true"
                    )
                }
            )
        else:
            self.fields["is_all_day"].widget.attrs.update(
                {"hx-get": "/activity/event-create-form/"}
            )

        is_all_day = (
            self.data.get("is_all_day", False)
            if self.data
            else self.initial.get("is_all_day")
        )
        if is_all_day == "on":  # Checkbox returns 'on' when checked
            is_all_day = True
        elif is_all_day in ("off", False):
            is_all_day = False

        # Update widget visibility based on current is_all_day value
        if is_all_day:
            self.fields["start_datetime"].widget = forms.HiddenInput()
            self.initial["start_datetime"] = None
            self.fields["end_datetime"].widget = forms.HiddenInput()
            self.initial["end_datetime"] = None

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        is_all_day = cleaned_data.get("is_all_day")

        if not is_all_day and start_datetime and end_datetime:
            if start_datetime.date() == end_datetime.date():
                if start_datetime.time() >= end_datetime.time():
                    raise ValidationError(
                        {
                            "end_datetime": (
                                "End time must be later than start time "
                                "on the same date."
                            )
                        }
                    )
            elif end_datetime <= start_datetime:
                # Different dates: validate full datetime
                raise ValidationError(
                    {
                        "end_datetime": "End date and time must be later than start date and time."
                    }
                )
        return cleaned_data


class ActivityCreateForm(OwnerQuerysetMixin, HorillaModelForm):
    """
    Activity creation and update form
    """

    field_order = [
        "activity_type",
        "subject",
        "title",
        "content_type",
        "object_id",
        "owner",
        "status",
        "start_datetime",
        "end_datetime",
        "is_all_day",
        "is_online",
        "location",
        "meeting_provider",
        "meeting_host",
        "assigned_to",
        "participants",
        "task_priority",
        "due_datetime",
        "call_type",
        "call_purpose",
        "reminder",
        "mail_template",
        "description",
        "notes",
    ]

    class Meta:
        """
        meta class for ActivityCreateForm
        """

        model = Activity
        fields = "__all__"
        exclude = [
            "meeting_url",
            "external_participants",
            "call_duration_display",
            "call_duration_seconds",
            "google_event_id",
        ]
        widgets = {
            "activity_type": forms.Select(
                attrs={
                    "hx-target": "#activity-form-view-container",
                    "hx-swap": "outerHTML",
                    "data-placeholder": _("Select Activity Type"),
                    # Preserve already-entered values (e.g. start/end datetime from calendar click)
                    # when re-rendering fields after activity type changes.
                    "hx-include": "#activity-form-view",
                    "id": "id_activity_type",
                }
            ),
            "is_all_day": forms.CheckboxInput(
                attrs={
                    "hx-target": "#activity-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#activity-form-view",
                    "id": "id_is_all_day",
                }
            ),
            "content_type": forms.Select(
                attrs={
                    "hx-target": "#activity-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#activity-form-view",
                    "id": "id_content_type",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Optional list of fields that should remain visible;
        # other fields will be hidden by this form.
        visible_fields = kwargs.pop("visible_fields", None)
        super().__init__(*args, **kwargs)

        excluded_activity_types = []
        if self.request and self.request.GET.get("view") == "calendar":
            excluded_activity_types.extend(["log_call", "email"])
        if excluded_activity_types:
            self.fields["activity_type"].choices = [
                (value, label)
                for value, label in self.fields["activity_type"].choices
                if value not in excluded_activity_types
            ]

        # Get activity_type from initial, submitted data, or instance
        activity_type = (
            self.data.get("activity_type")
            if self.data
            else self.initial.get("activity_type")
            or (self.instance.activity_type if self.instance.pk else None)
        )

        # Base URL for hx-get
        base_url = (
            f"/activity/activity-edit-form/{self.instance.pk}/?toggle_is_all_day=true"
            if self.instance.pk
            else "/activity/activity-create-form/"
        )
        if self.request and self.request.GET.get("view") == "calendar":
            separator = "&" if "?" in base_url else "?"
            base_url = f"{base_url}{separator}view=calendar"

        current_content_type_id = (
            self.data.get("content_type")
            if self.data
            else self.initial.get("content_type")
        )
        if not current_content_type_id and self.instance.pk:
            current_content_type_id = self.instance.content_type_id

        if current_content_type_id and "content_type" in self.fields:
            resolved_content_type_id = (
                current_content_type_id.id
                if hasattr(current_content_type_id, "id")
                else current_content_type_id
            )
            self.initial["content_type"] = resolved_content_type_id
            self.fields["content_type"].initial = resolved_content_type_id
            self.fields["content_type"].widget.attrs["data-initial"] = str(
                resolved_content_type_id
            )

        # Update widget attributes for fields that are always present
        self.fields["activity_type"].widget.attrs.update({"hx-get": base_url})
        self.fields["content_type"].widget.attrs.update({"hx-get": base_url})

        # Handle is_all_day for event and meeting only
        if activity_type in ["event", "meeting"]:
            if "is_all_day" in self.fields:
                self.fields["is_all_day"].widget.attrs.update({"hx-get": base_url})

                is_all_day = (
                    self.data.get("is_all_day", False)
                    if self.data
                    else self.initial.get("is_all_day", False)
                )
                if isinstance(is_all_day, str):
                    is_all_day = is_all_day.strip().lower() in {
                        "on",
                        "true",
                        "1",
                        "yes",
                    }
                else:
                    is_all_day = bool(is_all_day)

                if activity_type == "meeting":
                    ion = self.data.get("is_online") if self.data else None
                    if ion is None:
                        if self.instance.pk:
                            ion = self.instance.is_online
                        else:
                            ion = self.initial.get("is_online", False)
                    if ion in ("on", True, "true", "True"):
                        is_all_day = False

                if is_all_day:
                    for field_name in ["start_datetime", "end_datetime"]:
                        if field_name in self.fields:
                            self.fields[field_name].widget = forms.HiddenInput()
                            self.initial[field_name] = None
                            self.fields[field_name].widget.attrs[
                                "data-hidden-label"
                            ] = "true"
        else:
            # Explicitly hide start_datetime and end_datetime for other activity types
            for field_name in ["start_datetime", "end_datetime", "is_all_day"]:
                if field_name in self.fields:
                    self.fields[field_name].widget = forms.HiddenInput()
                    self.fields[field_name].required = False

        if hasattr(self, "initial") and "activity_type" in self.initial:
            self.fields["activity_type"].initial = self.initial["activity_type"]

        content_type_id = current_content_type_id
        field_name = "object_id"
        submitted_values = self.data.getlist(field_name) if self.data else None
        initial_value = self.initial.get(field_name, None)

        object_id_attrs = {
            "id": f"id_{field_name}",
            "data-placeholder": _("Select Related Object"),
            "class": "select2-pagination w-full text-sm",
            "data-field-name": field_name,
        }

        if content_type_id:
            try:
                content_type = HorillaContentType.objects.get(id=content_type_id)
                app_label = content_type.app_label
                model_name = content_type.model
                object_id_attrs["data-url"] = reverse_lazy(
                    "generics:model_select2",
                    kwargs={"app_label": app_label, "model_name": model_name},
                )
                if submitted_values or initial_value:
                    object_id_attrs["data-initial"] = ",".join(
                        map(str, submitted_values or [initial_value])
                    )
                model_class = content_type.model_class()
                if model_class:
                    objects = model_class.objects.all()[:100]
                    self.fields["object_id"].choices = [
                        ("", "Select Related Object")
                    ] + [(obj.id, str(obj)) for obj in objects]
            except HorillaContentType.DoesNotExist:
                object_id_attrs["data-url"] = ""
                self.fields["object_id"].choices = [("", "Select Related Object")]
        else:
            object_id_attrs["data-url"] = ""
            self.fields["object_id"].choices = [("", "Select Related Object")]

        self.fields["object_id"].widget = forms.Select(attrs=object_id_attrs)

        if activity_type == "meeting":
            self._configure_activity_meeting_fields(base_url)

        if visible_fields is not None:
            ordered_fields = OrderedDict()
            # Add visible fields in requested order
            for name in visible_fields:
                if name in self.fields:
                    ordered_fields[name] = self.fields[name]
            # Append any remaining fields (typically hidden/meta fields)
            for name, field in self.fields.items():
                if name not in ordered_fields:
                    ordered_fields[name] = field
            self.fields = ordered_fields

            # Hide non-visible fields
            for name, field in self.fields.items():
                if name not in visible_fields:
                    field.required = False
                    if isinstance(field, forms.ModelMultipleChoiceField):
                        # A single HiddenInput is invalid for M2M (POST is not a list of PKs),
                        # which surfaces as "Enter a list of values" on save.
                        field.widget = forms.MultipleHiddenInput()
                        if self.instance.pk:
                            related = getattr(self.instance, name)
                            field.initial = list(related.values_list("pk", flat=True))
                    else:
                        field.widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get("start_datetime")
        end_datetime = cleaned_data.get("end_datetime")
        is_all_day = cleaned_data.get("is_all_day")
        content_type = cleaned_data.get("content_type")
        object_id = cleaned_data.get("object_id")

        # Validate object_id against content_type with owner filtration
        if content_type and object_id:
            try:
                model_class = content_type.model_class()

                # Apply owner filtration validation
                if self.request and self.request.user:
                    user = self.request.user

                    # Get fresh filtered queryset
                    queryset = model_class.objects.all()

                    if model_class is User:
                        allowed_user_ids = self._get_allowed_user_ids(user)
                        queryset = queryset.filter(id__in=allowed_user_ids)
                    elif (
                        hasattr(model_class, "OWNER_FIELDS")
                        and model_class.OWNER_FIELDS
                    ):
                        allowed_user_ids = self._get_allowed_user_ids(user)
                        if allowed_user_ids:
                            query = Q()
                            for owner_field in model_class.OWNER_FIELDS:
                                query |= Q(
                                    **{f"{owner_field}__id__in": allowed_user_ids}
                                )
                            queryset = queryset.filter(query)
                        else:
                            queryset = queryset.none()

                    # Check if the selected object exists in the filtered queryset
                    if not queryset.filter(id=object_id).exists():
                        raise ValidationError(
                            {
                                "object_id": (
                                    "Select a valid choice. That choice is not "
                                    "one of the available choices."
                                )
                            }
                        )

            except ValidationError:
                raise
            except Exception as exc:
                raise ValidationError(
                    {"object_id": "Invalid object selection."}
                ) from exc

        activity_type = cleaned_data.get("activity_type")
        if activity_type == "meeting":
            raw = self.data.get("external_participants_email", "") if self.data else ""
            emails = [e.strip().lower() for e in raw.split(",") if e.strip()]
            cleaned_data["external_participants"] = emails
            if cleaned_data.get("is_online"):
                cleaned_data["is_all_day"] = False
                is_all_day = False
                cleaned_data["location"] = ""
            else:
                loc = (cleaned_data.get("location") or "").strip()
                cleaned_data["location"] = loc
                if not loc and "location" not in self.errors:
                    self.add_error(
                        "location",
                        ValidationError(
                            "In-person meetings require a location "
                            "(room, building, or address)."
                        ),
                    )
            is_all_day = cleaned_data.get("is_all_day")

        # Existing date/time validation
        if not is_all_day and start_datetime and end_datetime:
            if start_datetime.date() == end_datetime.date():
                if start_datetime.time() >= end_datetime.time():
                    raise ValidationError(
                        {
                            "end_datetime": (
                                "End time must be later than start time "
                                "on the same date."
                            )
                        }
                    )
            elif end_datetime <= start_datetime:
                raise ValidationError(
                    {
                        "end_datetime": "End date and time must be later than start date and time."
                    }
                )
        return cleaned_data

    def _meeting_provider_choices(self, user):
        choices = [("", "— Select Provider —")]
        if not user:
            return choices
        try:
            from horilla.contrib.calendar.models import GoogleCalendarConfig
            from horilla.contrib.meeting.models import (
                MeetingIntegrationSetting,
                MicrosoftTeamsOAuthConfig,
                ZoomOAuthConfig,
            )

            company = getattr(user, "company", None)
            if not company or not MeetingIntegrationSetting.user_can_access(
                user, company
            ):
                return choices
            if ZoomOAuthConfig.objects.filter(
                user=user, token__has_key="access_token"
            ).exists():
                choices.append(("zoom", "Zoom"))
            gcal = GoogleCalendarConfig.objects.filter(user=user).first()
            from horilla.contrib.meeting.models import UserMeetingConfig

            meet_enabled = UserMeetingConfig.objects.filter(
                user=user, provider="google_meet"
            ).exists()
            if gcal and gcal.is_connected() and meet_enabled:
                choices.append(("google_meet", "Google Meet"))
            if MicrosoftTeamsOAuthConfig.objects.filter(
                user=user, token__has_key="access_token"
            ).exists():
                choices.append(("ms_teams", "Microsoft Teams"))
        except Exception:
            pass
        return choices

    def _configure_activity_meeting_fields(self, base_url):
        """Apply MeetingsForm-style widgets and rules while keeping HTMX on activity URLs."""
        if "is_online" in self.fields:
            self.fields["is_online"].widget.attrs.update(
                {
                    "hx-post": base_url,
                    "hx-trigger": "change",
                    "hx-swap": "outerHTML",
                    "hx-select": "#activity-form-view",
                    "hx-include": "#activity-form-view",
                    "hx-target": "#activity-form-view",
                    "hx-vals": '{"_toggle_field": "is_online"}',
                    "onchange": "toggleMeetingUrlField(this)",
                }
            )
            # HorillaModelForm sets sr-only peer so single_form_view shows one toggle, not a second checkbox.
            self.fields["is_online"].widget.attrs["class"] = "sr-only peer"
        user = self.request.user if self.request else None
        provider_choices = self._meeting_provider_choices(user)
        prev_label = (
            self.fields["meeting_provider"].label
            if "meeting_provider" in self.fields
            else "Meeting Provider"
        )
        self.fields["meeting_provider"] = forms.ChoiceField(
            choices=provider_choices,
            required=False,
            label=prev_label,
            widget=forms.Select(
                attrs={
                    "class": (
                        "js-example-basic-single headselect w-full border border-gray-300 "
                        "rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-primary-500"
                    ),
                    "data-online-field": "true",
                    "data-placeholder": _("Select Provider"),
                    "id": "id_meeting_provider",
                }
            ),
        )

        is_online = self.data.get("is_online") if self.data else None
        if is_online is None:
            if self.instance.pk:
                is_online = self.instance.is_online
            else:
                is_online = self.initial.get("is_online", False)
        is_online = is_online in ("on", True, "true", "True")

        if is_online:
            if "is_all_day" in self.fields:
                self.fields["is_all_day"].widget = forms.HiddenInput()
                self.fields["is_all_day"].required = False
                self.initial["is_all_day"] = False
            if "location" in self.fields:
                self.fields["location"].widget = forms.HiddenInput()
                self.fields["location"].required = False
        elif "location" in self.fields:
            self.fields["location"].required = True

        self.fields["meeting_provider"].widget.attrs.update(
            {"data-online-field": "true"}
        )
        if not is_online:
            self.fields["meeting_provider"].widget.attrs.update(
                {"data-initially-hidden": "true"}
            )

    def _get_allowed_user_ids(self, user):
        """Get list of allowed user IDs (self + subordinates)"""
        from horilla.contrib.core.utils import get_allowed_user_ids

        if not user or not user.is_authenticated:
            return []

        if user.is_superuser:
            return list(User.objects.values_list("id", flat=True))

        return list(get_allowed_user_ids(user))
