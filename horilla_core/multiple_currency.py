import logging
from decimal import Decimal
from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.edit import FormView

from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_core.forms import ConversionRateForm, CurrencyForm, DatedConversionRateForm
from horilla_generics.views import (
    HorillaListView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
)

from .models import DatedConversionRate, MultipleCurrency

logger = logging.getLogger(__name__)
from django.utils.decorators import method_decorator


@method_decorator(htmx_required, name="dispatch")
class CurrencyListView(LoginRequiredMixin, HorillaListView):
    """
    List View for currency list.
    """

    model = MultipleCurrency
    view_id = "currency-list-view"
    table_width = False
    bulk_select_option = False
    clear_session_button_enabled = False
    table_height = False
    table_height_as_class = "h-[400px]"
    search_url = reverse_lazy("horilla_core:currency_list_view")
    main_url = reverse_lazy("horilla_core:currency_list_view")
    enable_sorting = False

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.GET.get("sort"):
            return queryset
        return queryset.order_by("-is_default")

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (_("Currency Code"), "currency"),
            (instance._meta.get_field("currency").verbose_name, "get_currency_display"),
            (instance._meta.get_field("is_default").verbose_name, "is_default_col"),
            (instance._meta.get_field("format").verbose_name, "get_format_display"),
            (
                instance._meta.get_field("conversion_rate").verbose_name,
                "conversion_rate",
            ),
            (instance._meta.get_field("is_active").verbose_name, "is_active"),
            (instance._meta.get_field("decimal_places").verbose_name, "decimal_places"),
        ]

    @cached_property
    def actions(self):
        """
        Return list of actions for the detail view
        """
        actions = []
        show_actions = self.request.user.is_superuser or self.request.user.has_perm(
            "horilla_core.change_multiplecurrency"
        )

        if show_actions:
            actions.extend(
                [
                    {
                        "action": "Edit",
                        "src": "assets/icons/edit.svg",
                        "img_class": "w-4 h-4 flex gap-4",
                        "attrs": """
                hx-get="{get_edit_url}"
                hx-target="#modalBox"
                hx-swap="innerHTML"
                onclick="openModal()"
            """,
                    },
                ]
            )
            if self.request.user.has_perm("horilla_core.delete_multiplecurrency"):
                actions.append(
                    {
                        "action": "Delete",
                        "src": "assets/icons/a4.svg",
                        "img_class": "w-4 h-4",
                        "attrs": """
                hx-post="{get_delete_url}"
                hx-target="#modalBox"
                hx-swap="innerHTML"
                hx-trigger="click"
                onclick="openModal()"
            """,
                    }
                )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["horilla_core.change_multiplecurrency", "horilla_core.change_company"],
        modal=True,
    ),
    name="dispatch",
)
class ChangeDefaultCurrencyView(LoginRequiredMixin, View):
    """
    View to change the default currency for a company and update conversion rates.
    """

    def post(self, request, *args, **kwargs):
        currency_id = kwargs.get("pk")
        if not currency_id:
            return HttpResponseBadRequest("Currency ID is required.")

        try:
            company = getattr(request, "active_company", None) or request.user.company
            new_default_currency = MultipleCurrency.objects.get(
                id=currency_id, company=company
            )
            with transaction.atomic():
                current_default = MultipleCurrency.objects.filter(
                    company=company, is_default=True
                ).first()

                if current_default and current_default.id == new_default_currency.id:
                    messages.info(request, "Currency is already the default.")
                    return HttpResponse(
                        "<script>htmx.trigger('#tab-currency-view','click')</script>"
                    )

                original_new_default_rate = (
                    new_default_currency.conversion_rate or Decimal("1.0")
                )

                all_currencies = MultipleCurrency.objects.filter(company=company)
                for curr in all_currencies:
                    if curr.id == new_default_currency.id:
                        curr.conversion_rate = Decimal("1.0")
                        curr.is_default = True
                    else:
                        current_rate = curr.conversion_rate or Decimal("1.0")
                        curr.conversion_rate = current_rate / original_new_default_rate
                        curr.is_default = False
                    curr.save()

                new_default_dated_rates = {}
                existing_dated_rates = DatedConversionRate.objects.filter(
                    company=company, currency=new_default_currency
                )
                for rate in existing_dated_rates:
                    new_default_dated_rates[rate.start_date] = rate.conversion_rate

                DatedConversionRate.objects.filter(
                    company=company, currency=new_default_currency
                ).delete()

                dated_rates = DatedConversionRate.objects.filter(company=company)
                if current_default:
                    start_dates = dated_rates.values("start_date").distinct()

                    for start_date in start_dates:
                        start_date_value = start_date["start_date"]

                        old_default_new_rate = new_default_dated_rates.get(
                            start_date_value, original_new_default_rate
                        )
                        old_default_new_rate = 1 / old_default_new_rate

                        existing_rate = DatedConversionRate.objects.filter(
                            company=company,
                            currency=current_default,  # Use MultipleCurrency object
                            start_date=start_date_value,
                        ).first()
                        if existing_rate:
                            existing_rate.conversion_rate = old_default_new_rate
                            existing_rate.save()
                        else:
                            DatedConversionRate.objects.create(
                                company=company,
                                currency=current_default,
                                conversion_rate=old_default_new_rate,
                                start_date=start_date_value,
                                created_by=self.request.user,
                                updated_by=self.request.user,
                            )

                for rate in dated_rates:
                    if rate.currency != current_default:
                        current_rate = rate.conversion_rate or Decimal("1.0")
                        divisor_rate = new_default_dated_rates.get(
                            rate.start_date, original_new_default_rate
                        )
                        rate.conversion_rate = current_rate / divisor_rate
                        rate.save()

                company.currency = new_default_currency.currency
                company.save()

            messages.success(request, "Default currency changed successfully.")
            return HttpResponse(
                "<script>htmx.trigger('#tab-currency-view','click')</script>"
            )

        except MultipleCurrency.DoesNotExist:
            messages.error(
                self.request,
                "Invalid currency ID or currency doesn't belong to your company.",
            )
            return HttpResponse("<script>$('#reloadButton').click();</script>")
        except ValueError as e:
            messages.error(self.request, "Failed to update conversion rates")
            return HttpResponse("<script>$('#reloadButton').click();</script>")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["horilla_core.change_multiplecurrency", "horilla_core.change_company"],
        modal=True,
    ),
    name="dispatch",
)
class ChangeDefaultCurrencyFormView(LoginRequiredMixin, FormView):
    """
    HTMX endpoint to change the default currency and update conversion rates.
    """

    model = MultipleCurrency
    template_name = "settings/change_default_currency.html"
    form_class = CurrencyForm
    success_url = reverse_lazy("settings:currency_list")

    def get_form_kwargs(self):
        """Pass the current company to the form."""
        kwargs = super().get_form_kwargs()
        company = getattr(self.request, "active_company", None)
        kwargs["company"] = company if company else self.request.user.company
        return kwargs

    def form_valid(self, form):
        """Handle the form submission to update the default currency and conversion rates."""
        currency = form.cleaned_data["currency"]
        company = (
            getattr(self.request, "active_company", None) or self.request.user.company
        )

        try:
            new_default_currency = MultipleCurrency.objects.get(
                pk=currency.pk, company=company
            )

            with transaction.atomic():
                current_default = MultipleCurrency.objects.filter(
                    company=company, is_default=True
                ).first()

                if current_default and current_default.id == new_default_currency.id:
                    messages.info(self.request, "Currency is already the default.")
                    return HttpResponse(
                        "<script>htmx.trigger('#tab-currency-view','click');closeModal();</script>"
                    )

                original_new_default_rate = (
                    new_default_currency.conversion_rate or Decimal("1.0")
                )

                all_currencies = MultipleCurrency.objects.filter(company=company)
                for curr in all_currencies:
                    if curr.id == new_default_currency.id:
                        curr.conversion_rate = Decimal("1.0")
                        curr.is_default = True
                    else:
                        current_rate = curr.conversion_rate or Decimal("1.0")
                        curr.conversion_rate = current_rate / original_new_default_rate
                        curr.is_default = False
                    curr.save()

                new_default_dated_rates = {}
                existing_dated_rates = DatedConversionRate.objects.filter(
                    company=company,
                    currency=new_default_currency,  # Use MultipleCurrency object
                )
                for rate in existing_dated_rates:
                    new_default_dated_rates[rate.start_date] = rate.conversion_rate

                DatedConversionRate.objects.filter(
                    company=company,
                    currency=new_default_currency,  # Use MultipleCurrency object
                ).delete()

                dated_rates = DatedConversionRate.objects.filter(company=company)
                if current_default:
                    start_dates = dated_rates.values("start_date").distinct()
                    for start_date in start_dates:
                        start_date_value = start_date["start_date"]
                        old_default_new_rate = new_default_dated_rates.get(
                            start_date_value, original_new_default_rate
                        )
                        old_default_new_rate = 1 / old_default_new_rate

                        existing_rate = DatedConversionRate.objects.filter(
                            company=company,
                            currency=current_default,
                            start_date=start_date_value,
                        ).first()
                        if existing_rate:
                            existing_rate.conversion_rate = old_default_new_rate
                            existing_rate.save()
                        else:
                            DatedConversionRate.objects.create(
                                company=company,
                                currency=current_default,
                                conversion_rate=old_default_new_rate,
                                start_date=start_date_value,
                                created_by=self.request.user,
                                updated_by=self.request.user,
                            )

                for rate in dated_rates:
                    if rate.currency != current_default:
                        current_rate = rate.conversion_rate or Decimal("1.0")
                        divisor_rate = new_default_dated_rates.get(
                            rate.start_date, original_new_default_rate
                        )
                        rate.conversion_rate = current_rate / divisor_rate
                        rate.save()

                company.currency = new_default_currency.currency
                company.save()
            messages.success(self.request, "Default currency changed successfully.")
            return HttpResponse(
                "<script>htmx.trigger('#tab-currency-view','click');closeModal();</script>"
            )

        except MultipleCurrency.DoesNotExist:
            return HttpResponseBadRequest(
                "Invalid currency ID or currency doesn't belong to your company."
            )
        except ValueError as e:
            logger.error(f"Error updating DatedConversionRate: {e}")
            return HttpResponseBadRequest(f"Failed to update conversion rates: {e}")

    def form_invalid(self, form):
        """Handle invalid form submission."""
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Provide context data for the template."""
        context = super().get_context_data(**kwargs)
        company = (
            getattr(self.request, "active_company", None) or self.request.user.company
        )
        currencies = MultipleCurrency.objects.filter(company=company)
        context["currencies"] = currencies.filter(is_default=False)
        context["current_currency"] = currencies.filter(is_default=True).first()
        return context


@method_decorator(htmx_required, name="dispatch")
class AddCurrencyView(LoginRequiredMixin, HorillaSingleFormView):
    """
    View to add a new currency.
    """

    model = MultipleCurrency
    form_title = _("Add Currency")
    modal_height = False
    fields = ["currency", "conversion_rate", "decimal_places", "format", "company"]
    hidden_fields = ["company"]

    def dispatch(self, request, *args, **kwargs):
        """
        Adjust fields based on whether editing or adding a currency before form creation.
        """
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            self.fields = ["conversion_rate", "decimal_places", "format", "company"]
            self.form_title = _("Edit Currency Information")
            self.full_width_fields = ["format"]
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["company"] = getattr(self.request, "active_company", None)
        if not initial["company"]:
            initial["company"] = self.request.user.company
        return initial

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_core:edit_currency", kwargs={"pk": pk})
        return reverse_lazy("horilla_core:add_currency")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.change_multiplecurrency", modal=True),
    name="dispatch",
)
class ConversionRateFormView(LoginRequiredMixin, FormView):
    template_name = "settings/conversion_rates.html"
    form_class = ConversionRateForm
    success_url = reverse_lazy("settings:currency_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        company = getattr(self.request, "active_company", None)
        kwargs["company"] = company if company else self.request.user.company
        return kwargs

    def form_valid(self, form):
        company = getattr(self.request, "active_company", None)
        new_default = form.cleaned_data.get("new_default_currency")

        if new_default:
            MultipleCurrency.objects.filter(company=company).update(is_default=False)
            new_default_instance = MultipleCurrency.objects.get(
                pk=new_default.pk, company=company
            )
            new_default_instance.is_default = True
            new_default_instance.save()

        current_default = MultipleCurrency.objects.filter(
            company=company, is_default=True
        ).first()
        for currency in MultipleCurrency.objects.filter(company=company).exclude(
            pk=current_default.pk
        ):
            field_name = f"conversion_rate_{currency.currency}"
            if field_name in form.cleaned_data:
                currency.conversion_rate = form.cleaned_data[field_name]
                currency.save()

        if company and current_default:
            company.currency = current_default.currency
            company.save()

        return HttpResponse(
            "<script>htmx.trigger('#tab-currency-view','click');closeModal();</script>"
        )

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "active_company", None)
        if company:
            context["current_default"] = MultipleCurrency.objects.filter(
                company=company, is_default=True
            ).first()
            context["other_currencies"] = MultipleCurrency.objects.filter(
                company=company
            ).exclude(is_default=True)
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_datedconversionrate", modal=True),
    name="dispatch",
)
class DatedConversionRateFormView(LoginRequiredMixin, FormView):
    template_name = "settings/dated_conversion_rates.html"
    form_class = DatedConversionRateForm
    success_url = reverse_lazy("settings:dated_conversion_rate_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        company = getattr(self.request, "active_company", None)
        kwargs["company"] = company if company else self.request.user.company
        return kwargs

    def form_valid(self, form):
        company = (
            getattr(self.request, "active_company", None) or self.request.user.company
        )
        start_date = form.cleaned_data["start_date"]

        # Save dated conversion rates for each non-default currency
        current_default = MultipleCurrency.objects.filter(
            company=company, is_default=True
        ).first()
        for currency in MultipleCurrency.objects.filter(company=company).exclude(
            is_default=True
        ):
            field_name = f"conversion_rate_{currency.currency}"
            if field_name in form.cleaned_data:
                DatedConversionRate.objects.create(
                    company=company,
                    currency=currency,  # Use the MultipleCurrency object
                    conversion_rate=form.cleaned_data[field_name],
                    start_date=start_date,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )

        return HttpResponse(
            "<script>htmx.trigger('#tab-currency-view','click');closeModal();</script>"
        )

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = (
            getattr(self.request, "active_company", None) or self.request.user.company
        )
        context["current_default"] = MultipleCurrency.objects.filter(
            company=company, is_default=True
        ).first()
        context["other_currencies"] = MultipleCurrency.objects.filter(
            company=company
        ).exclude(is_default=True)
        context["dated_rates"] = DatedConversionRate.objects.filter(
            company=company
        ).order_by("currency", "start_date")
        return context


@method_decorator(htmx_required, name="dispatch")
class DatedCurrencyListView(LoginRequiredMixin, HorillaListView):
    """
    List View for currency list.
    """

    model = DatedConversionRate
    view_id = "dated-currency-list-view"
    table_width = False
    bulk_select_option = False
    clear_session_button_enabled = False
    search_url = reverse_lazy("horilla_core:dated_currency_list_view")
    main_url = reverse_lazy("horilla_core:dated_currency_list_view")
    enable_sorting = False

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (_("Currency Code"), "currency__currency"),
            (
                instance._meta.get_field("currency").verbose_name,
                "currency__get_currency_display",
            ),
            (instance._meta.get_field("start_date").verbose_name, "start_date"),
            (
                instance._meta.get_field("conversion_rate").verbose_name,
                "conversion_rate",
            ),
        ]

    def get_queryset(self):
        """
        Filter queryset based on the selected start_date from GET parameters.
        """
        queryset = super().get_queryset()
        start_date = self.request.GET.get("start_date", None)
        if start_date:
            queryset = queryset.filter(start_date=start_date)
        return queryset


@method_decorator(htmx_required, name="dispatch")
class CurrencyDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = MultipleCurrency

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_default:
            messages.error(self.request, "Default Currency can not delete")
            response = HttpResponse(
                "<script>$('#reloadButton').click();closeModal();</script>"
            )
            response["HX-Retarget"] = "#currency-list-view"
            return response
        return super().delete(request, *args, **kwargs)

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>$('#reloadButton').click();closeDeleteModeModal();</script>"
        )
