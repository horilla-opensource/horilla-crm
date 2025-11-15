"""
This view handles the methods for regional Formating view
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from horilla_core.forms import RegionalFormattingForm


class ReginalFormatingView(LoginRequiredMixin, FormView):
    """
    Template view for Big deal alert page
    """

    template_name = "regional_formating/formating_view.html"
    form_class = RegionalFormattingForm

    def get(self, request, *args, **kwargs):
        form = RegionalFormattingForm(instance=request.user)
        context = {
            "form": form,
            "view_id": "regional-formating-view",
        }
        return render(request, self.template_name, context)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, _("Your preferences have been updated successfully.")
        )
        context = {
            "form": RegionalFormattingForm(instance=self.request.user),
            "view_id": "regional-formating-view",
        }
        return render(self.request, self.template_name, context)

    def form_invalid(self, form):
        messages.error(self.request, _("There was an error updating your preferences."))
        return self.render_to_response(self.get_context_data(form=form))
