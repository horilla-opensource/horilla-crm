"""Web-to-lead form builder and public form views."""

# Standard library imports
import json
from urllib.parse import urlparse

# Third-party imports (Django)
from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.loader import render_to_string
from django.utils import translation
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, FormView, TemplateView

# First party imports (Horilla)
from horilla.auth.models import User
from horilla.shortcuts import render
from horilla.urls import reverse, reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HttpNotFound, HttpResponse, RedirectResponse

# Local imports
from horilla_crm.leads.models import Lead, LeadCaptureForm, LeadStatus


def get_preview_fields_data(selected_fields):
    """Build field metadata (verbose name, type, choices) for form preview rendering."""
    fields_data = []
    for field_name in selected_fields:
        try:
            field = Lead._meta.get_field(field_name)
            fields_data.append(
                {
                    "name": field_name,
                    "verbose_name": (
                        field.verbose_name
                        if hasattr(field, "verbose_name")
                        else field_name
                    ),
                    "required": (not field.blank if hasattr(field, "blank") else True),
                    "field_type": field.get_internal_type(),
                    "choices": (
                        field.choices
                        if hasattr(field, "choices") and field.choices
                        else None
                    ),
                }
            )
        except Exception:
            pass
    return fields_data


# Fields to exclude from web-to-lead form builder (avoid repeating in views)
exclude_fields = [
    "id",
    "is_active",
    "created_at",
    "updated_at",
    "is_convert",
    "additional_info",
    "created_by",
    "updated_by",
    "lead_score",
    "message_id",
    "lead_owner",
    "lead_status",
    "company",
    "lead_source",
    "requirements",
]


@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class LeadFormBuilderView(LoginRequiredMixin, TemplateView):
    """View for building lead capture forms"""

    template_name = "web_to_lead/lead_form_builder.html"
    action = None  # allow parameter

    def get_context_data(self, **kwargs):
        """Build form-builder context with lead fields and available owners."""
        context = super().get_context_data(**kwargs)

        # Get all Lead model fields
        lead_fields = []
        for field in Lead._meta.get_fields():
            if (
                field.concrete
                and not field.auto_created
                and field.name not in exclude_fields
            ):
                field_info = {
                    "name": field.name,
                    "verbose_name": getattr(field, "verbose_name", field.name),
                    "required": not getattr(field, "blank", False),
                    "field_type": field.get_internal_type(),
                }
                lead_fields.append(field_info)
        context["lead_fields"] = lead_fields
        context["lead_owners"] = User.objects.filter(is_active=True)

        saved_form = LeadCaptureForm.objects.filter(
            company=self.request.active_company, is_active=True
        ).first()
        if saved_form:
            context["saved_form"] = saved_form
            context["form_url"] = self.request.build_absolute_uri(
                reverse("leads:public_lead_form", kwargs={"form_id": saved_form.id})
            )

            if self.request.GET.get("edit"):
                selected_fields = json.loads(saved_form.selected_fields)
                context["form_data"] = {
                    "form_name": saved_form.form_name,
                    "return_url_enable": saved_form.return_url_enable,
                    "return_url": saved_form.return_url,
                    "success_message": saved_form.success_message,
                    "success_description": saved_form.success_description,
                    "language": saved_form.language,
                    "color": saved_form.header_color,
                    "selected_fields": selected_fields,
                    "lead_owner": saved_form.lead_owner_id,
                }
                context["preview_fields"] = get_preview_fields_data(selected_fields)
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class UpdateFormHeadingView(LoginRequiredMixin, TemplateView):
    """HTMX view to update form heading"""

    template_name = "web_to_lead/form_heading.html"

    def post(self, request, *args, **kwargs):
        """Handle POST request to update form heading."""
        form_name = request.POST.get("form_name", "").strip()
        color = request.POST.get("color", "")

        language = request.POST.get("language", "en")  # Add language

        context = {
            "form_name": form_name if form_name else "Contact Us",
            "color": color,
            "language": language,  # Pass to template
        }

        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class UpdateFormPreviewView(LoginRequiredMixin, TemplateView):
    """HTMX view to update form preview"""

    template_name = "web_to_lead/form_preview.html"

    def post(self, request, *args, **kwargs):
        """Handle POST request to update form preview."""

        selected_fields = request.POST.getlist("selected_fields[]")
        form_name = request.POST.get("form_name", "").strip()
        color = request.POST.get("color")
        language = request.POST.get("language", "en")
        translation.activate(language)

        fields_data = get_preview_fields_data(selected_fields)

        context = {
            "fields": fields_data,
            "color": color,
            "form_name": form_name,
            "language": language,
        }

        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class SaveLeadFormView(LoginRequiredMixin, FormView):
    """View to save lead capture form configuration - one per company"""

    model = LeadCaptureForm
    fields = [
        "form_name",
        "return_url_enable",
        "return_url",
        "success_message",
        "success_description",
        "enable_recaptcha",
        "language",
        "header_color",
    ]
    success_url = reverse_lazy("leads:form_builder")
    template_name = "web_to_lead/lead_form_builder.html"

    def get_form_class(self):
        """Dynamically create the form class."""
        from django.forms import ModelForm

        class LeadCaptureFormForm(ModelForm):
            """Form for lead capture form configuration."""

            class Meta:
                """Meta options for LeadCaptureFormForm."""

                model = LeadCaptureForm
                fields = self.fields

        return LeadCaptureFormForm

    def form_valid(self, form):
        """Validate, save, and generate embed HTML for lead capture form config."""
        # Validate lead owner
        lead_owner = self.request.POST.get("lead_owner")
        if not lead_owner:
            form.add_error("lead_owner", _("Lead Owner is required."))
            return self.form_invalid(form)

        # Validate selected fields
        selected_fields = self.request.POST.getlist("selected_fields[]")
        if not selected_fields:
            form.add_error(None, _("Select at least one field."))
            return self.form_invalid(form)

        # Validate return URL requirements
        return_url_enable = self.request.POST.get("return_url_enable") == "on"

        if return_url_enable:
            return_url = form.cleaned_data.get("return_url")
            if not return_url:
                form.add_error("return_url", _("Return URL is required when enabled."))
                return self.form_invalid(form)
        else:
            success_message = form.cleaned_data.get("success_message")
            success_description = form.cleaned_data.get("success_description")
            if not success_message:
                form.add_error("success_message", _("Success message is required."))
                return self.form_invalid(form)
            if not success_description:
                form.add_error(
                    "success_description", _("Success description is required.")
                )
                return self.form_invalid(form)

        # Get or create the LeadCaptureForm instance
        obj, _created = LeadCaptureForm.objects.get_or_create(
            company=self.request.active_company,
            defaults={
                "created_by": self.request.user,
                "lead_owner_id": lead_owner,
                "form_name": form.cleaned_data.get("form_name", "Contact Us"),
                "language": form.cleaned_data.get("language", "en"),
                "header_color": self.request.POST.get("color", ""),
            },
        )

        # Update the instance with form data
        obj.form_name = form.cleaned_data.get("form_name")
        obj.language = form.cleaned_data.get("language")
        obj.enable_recaptcha = form.cleaned_data.get("enable_recaptcha", False)
        obj.created_by = self.request.user
        obj.lead_owner_id = lead_owner
        obj.selected_fields = json.dumps(selected_fields)
        obj.header_color = self.request.POST.get("color")
        obj.return_url_enable = return_url_enable

        if return_url_enable:
            obj.return_url = form.cleaned_data.get("return_url")
            obj.success_message = None
            obj.success_description = None
        else:
            obj.success_message = form.cleaned_data.get("success_message")
            obj.success_description = form.cleaned_data.get("success_description")
            obj.return_url = None

        # Activate selected language for form generation
        selected_language = obj.language
        translation.activate(selected_language)

        obj.save()
        self.object = obj

        # Parse selected fields for form generation
        parsed_fields = []
        for field_name in selected_fields:
            try:
                field = Lead._meta.get_field(field_name)
                field_info = {
                    "name": field_name,
                    "verbose_name": str(getattr(field, "verbose_name", field_name)),
                    "required": not getattr(field, "blank", False),
                    "field_type": field.get_internal_type(),
                    "choices": getattr(field, "choices", None),
                }
                parsed_fields.append(field_info)
            except Exception:
                pass

        # Generate HTML code
        html_code = render_to_string(
            "web_to_lead/public_lead_form.html",
            {
                "form_obj": self.object,
                "selected_fields_parsed": parsed_fields,
                "form_id": self.object.id,
                "view": {"kwargs": {"form_id": self.object.id}},
            },
        )

        self.object.generated_html = html_code
        self.object.save()

        translation.deactivate()

        # Return response
        if self.request.headers.get("HX-Request"):
            response = HttpResponse()
            response["HX-Redirect"] = reverse("leads:form_builder")
            return response

        return RedirectResponse(request=self.request, redirect_to=self.success_url)

    def form_invalid(self, form):
        """Re-render builder with errors, preserving submitted data for HTMX."""
        if self.request.headers.get("HX-Request"):
            # Get lead fields for the form builder
            lead_fields = []
            for field in Lead._meta.get_fields():
                if (
                    field.concrete
                    and not field.auto_created
                    and field.name not in exclude_fields
                ):
                    field_info = {
                        "name": field.name,
                        "verbose_name": getattr(field, "verbose_name", field.name),
                        "required": not getattr(field, "blank", False),
                        "field_type": field.get_internal_type(),
                    }
                    lead_fields.append(field_info)

            # Preserve form data for re-rendering
            form_data = {
                "form_name": self.request.POST.get("form_name", "Contact Us"),
                "return_url_enable": self.request.POST.get("return_url_enable") == "on",
                "return_url": self.request.POST.get("return_url", ""),
                "success_message": self.request.POST.get("success_message", ""),
                "success_description": self.request.POST.get("success_description", ""),
                "language": self.request.POST.get("language", "en"),
                "color": self.request.POST.get("color", ""),
                "selected_fields": self.request.POST.getlist("selected_fields[]"),
                "lead_owner": self.request.POST.get("lead_owner"),
            }

            context = {
                "form": form,
                "errors": form.errors,
                "lead_fields": lead_fields,
                "form_data": form_data,
                "lead_owners": User.objects.filter(is_active=True),
            }

            response = render(self.request, self.template_name, context)
            response["HX-Reselect"] = "#formBuilderForm"
            return response
        return super().form_invalid(form)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class AddFieldView(LoginRequiredMixin, TemplateView):
    """HTMX view to add a field to selected list"""

    template_name = "web_to_lead/selected_field.html"

    def post(self, request, *args, **kwargs):
        """Handle POST request to add a field to selected list."""
        field_name = request.POST.get("field_name")
        field_verbose = request.POST.get("field_verbose")
        form_name = request.POST.get("form_name")
        language = request.POST.get("language", "en")  # Add language

        context = {
            "field_name": field_name,
            "field_verbose": field_verbose,
            "form_name": form_name,
            "language": language,  # Pass to template
        }

        # Trigger preview update after field is added
        response = render(request, self.template_name, context)
        response["HX-Trigger"] = "updatePreview"
        return response


@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class RemoveFieldView(LoginRequiredMixin, View):
    """HTMX view to remove a field from selected list."""

    def post(self, request, *args, **kwargs):
        """Handle POST request to remove a field from selected list."""
        field_name = request.POST.get("field_name")
        # Escape for safe embedding in JavaScript (prevents XSS)
        field_name_escaped = json.dumps(field_name) if field_name is not None else '""'
        context = {"field_name_escaped": field_name_escaped}
        response = render(request, "web_to_lead/remove_field_script.html", context)
        response["HX-Trigger"] = "updatePreview"
        return response


@method_decorator(xframe_options_exempt, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class PublicLeadFormView(CreateView):
    """Public view for lead submission with HTMX support"""

    model = Lead
    template_name = "web_to_lead/public_lead_form.html"

    def get_form_class(self):
        """Get form class for public lead form based on form configuration."""
        form_id = self.kwargs.get("form_id")
        try:
            form_config = LeadCaptureForm.objects.get(id=form_id, is_active=True)

            # Activate the form's language
            translation.activate(form_config.language)

            selected_fields = json.loads(form_config.selected_fields)

            class DynamicLeadForm(forms.ModelForm):
                """Dynamically generated form based on selected fields."""

                class Meta:
                    """Meta options for DynamicLeadForm."""

                    model = Lead
                    fields = selected_fields

            return DynamicLeadForm
        except LeadCaptureForm.DoesNotExist as e:
            raise HttpNotFound(
                str(e), template="web_to_lead/web_to_lead_404.html"
            ) from e

    def get_context_data(self, **kwargs):
        """Populate public form context from stored lead-capture configuration."""
        context = super().get_context_data(**kwargs)
        form_id = self.kwargs.get("form_id")

        try:
            form_config = LeadCaptureForm.objects.get(id=form_id, is_active=True)

            # Activate the form's language
            translation.activate(form_config.language)

            context["form_obj"] = form_config
            context["form_config"] = form_config

            # Parse selected fields for template
            selected_fields = json.loads(form_config.selected_fields)
            parsed_fields = []

            for field_name in selected_fields:
                try:
                    field = Lead._meta.get_field(field_name)
                    field_type = field.get_internal_type()
                    field_info = {
                        "name": field_name,
                        "verbose_name": str(getattr(field, "verbose_name", field_name)),
                        "required": not getattr(field, "blank", False),
                        "field_type": field_type,
                    }

                    # Handle choice fields
                    if hasattr(field, "choices") and field.choices:
                        field_info["choices"] = list(field.choices)
                    # Handle ForeignKey and OneToOneField
                    elif field_type in ("ForeignKey", "OneToOneField"):
                        related_model = field.related_model
                        field_info["choices"] = [
                            (obj.pk, str(obj)) for obj in related_model.objects.all()
                        ]
                    else:
                        field_info["choices"] = None

                    parsed_fields.append(field_info)
                except Exception:
                    pass

            context["selected_fields_parsed"] = parsed_fields

        except LeadCaptureForm.DoesNotExist as e:
            raise HttpNotFound(
                str(e), template="web_to_lead/web_to_lead_404.html"
            ) from e

        return context

    def form_valid(self, form):
        """Create a lead and return HTMX redirect or success fragment."""
        form_id = self.kwargs.get("form_id")
        form_config = LeadCaptureForm.objects.get(id=form_id)
        form.instance.lead_owner = form_config.lead_owner
        form.instance.company = form_config.company
        form.instance.lead_source = "website"
        try:
            form.instance.lead_status = LeadStatus.objects.first()
        except Exception:
            pass

        self.object = form.save()

        # Check if this is an HTMX request
        if self.request.headers.get("HX-Request"):
            # Check if return URL exists
            if form_config.return_url and form_config.return_url.strip():
                return_url = form_config.return_url.strip()

                # Parse the URL to check if it's external
                parsed_url = urlparse(return_url)

                # If no scheme is present, add https://
                if not parsed_url.scheme:
                    if return_url.startswith("/"):
                        # It's a relative URL on the same domain
                        response = HttpResponse()
                        response["HX-Redirect"] = return_url
                        return response
                    return_url = "https://" + return_url

                # External redirect via HTMX
                response = HttpResponse()
                response["HX-Redirect"] = return_url
                return response

            header_color = form_config.header_color or "hsl(8, 77%, 56%)"
            success_message = (
                form_config.success_message
                if form_config.success_message
                else "Thank you!"
            )
            success_description = (
                form_config.success_description
                if form_config.success_description
                else "We have received your information and will get back to you soon."
            )

            return render(
                self.request,
                "web_to_lead/form_success.html",
                {
                    "header_color": header_color,
                    "success_message": success_message,
                    "success_description": success_description,
                },
            )
        return ""

    def form_invalid(self, form):
        """Handle invalid form submission for HTMX and non-HTMX requests."""
        # For HTMX requests, return the form with errors
        if self.request.headers.get("HX-Request"):
            return self.render_to_response(self.get_context_data(form=form))

        # Non-HTMX fallback
        return super().form_invalid(form)


@method_decorator(
    permission_required_or_denied("leads.add_leadcaptureform"), name="dispatch"
)
class ToggleReturnUrlView(LoginRequiredMixin, View):
    """Toggle between return URL and success message fields"""

    def post(self, request, *args, **kwargs):
        """Handle POST request to toggle return URL fields."""
        return_url_enabled = request.POST.get("return_url_enable") == "on"

        context = {"return_url_enabled": return_url_enabled}
        return render(request, "web_to_lead/conditional_fields.html", context)
