"""
Forms for the Accounts app.

Includes forms for creating/editing accounts and assigning child accounts,
with validation and dynamic queryset setup to prevent circular references.
"""

from django import forms
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla_core.mixins import OwnerQuerysetMixin
from horilla_crm.accounts.models import Account
from horilla_generics.forms import HorillaMultiStepForm


class AccountFormClass(OwnerQuerysetMixin, HorillaMultiStepForm):
    """Multi-step form for creating or editing an Account."""

    class Meta:
        """Meta options for the Account form."""

        model = Account
        fields = "__all__"

    step_fields = {
        1: [
            "account_owner",
            "name",
            "account_source",
            "account_type",
            "rating",
            "phone",
            "parent_account",
            "fax",
            "account_number",
            "website",
            "site",
        ],
        2: [
            "billing_city",
            "billing_state",
            "billing_district",
            "billing_zip",
            "shipping_city",
            "shipping_state",
            "shipping_district",
            "shipping_zip",
        ],
        3: [
            "annual_revenue",
            "is_partner",
            "industry",
            "number_of_employees",
            "ownership",
        ],
        4: ["description"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.current_step < len(self.step_fields):
            self.fields["created_by"].required = False
            self.fields["updated_by"].required = False

            self.fields["is_partner"].required = False
            if self.instance and self.instance.pk and "is_partner" not in self.initial:
                self.initial["is_partner"] = self.instance.is_partner


class AddChildAccountForm(forms.Form):
    """
    Form to select an existing account and assign it as a child account.
    """

    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),  # Will be set in __init__
        label=_("Select Account"),
        widget=forms.Select(
            attrs={
                "class": "select2-pagination w-full text-sm",
                "data-placeholder": "Select Account",
                "data-url": reverse_lazy(
                    "horilla_generics:model_select2",
                    kwargs={"app_label": "accounts", "model_name": "Account"},
                ),
                "data-field-name": "account",
                "id": "id_account",
            }
        ),
        help_text=_("Select the account to assign as a child account."),
    )

    parent_account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        widget=forms.HiddenInput(),  # Make this a hidden field
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)

        generic_attrs = ["full_width_fields", "dynamic_create_fields", "hidden_fields"]
        for attr in generic_attrs:
            kwargs.pop(attr, None)

        super().__init__(*args, **kwargs)

        self.setup_account_queryset()

    def setup_account_queryset(self):
        """
        Set up the account queryset based on the request parameters.
        """
        if not self.request:
            self.fields["account"].queryset = Account.objects.all()
            return

        parent_id = self.request.GET.get("id")
        if not parent_id:
            self.fields["account"].queryset = Account.objects.all()
            return

        try:
            parent_account = Account.objects.get(pk=parent_id)

            queryset = Account.objects.all()
            queryset = queryset.exclude(id=parent_id)

            queryset = queryset.filter(parent_account__isnull=True)
            descendant_ids = self.get_descendant_ids(parent_account)
            if descendant_ids:
                queryset = queryset.exclude(id__in=descendant_ids)

            self.fields["account"].queryset = queryset

        except Account.DoesNotExist:
            # If parent doesn't exist, show all accounts without parents
            self.fields["account"].queryset = Account.objects.filter(
                parent_account__isnull=True
            )

    def get_descendant_ids(self, account):
        """
        Get all descendant IDs of an account to prevent circular references.
        """
        descendant_ids = []
        children = Account.objects.filter(parent_account=account)
        for child in children:
            descendant_ids.append(child.id)
            descendant_ids.extend(self.get_descendant_ids(child))
        return descendant_ids

    def clean_account(self):
        """
        Validate the selected account.
        """
        account = self.cleaned_data.get("account")
        if not account:
            raise forms.ValidationError(_("Please select an account."))

        # Check if account already has a parent
        if account.parent_account:
            raise forms.ValidationError(
                _("This account already has a parent account assigned.")
            )

        # Get parent from hidden field instead of request
        parent_account = self.cleaned_data.get("parent_account")
        if parent_account and str(account.id) == str(parent_account.id):
            raise forms.ValidationError(_("An account cannot be its own parent."))

        return account

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get("account")

        if not account:
            raise forms.ValidationError(_("Please select a valid account."))

        return cleaned_data
