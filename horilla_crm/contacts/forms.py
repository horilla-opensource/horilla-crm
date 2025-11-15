"""
Forms for the Contacts app.

Includes:
- Multi-step form for creating and updating contacts.
- Form for assigning child contacts while preventing circular references.
- Validation logic for parent–child relationships between contacts.
"""

from django import forms
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla_core.mixins import OwnerQuerysetMixin
from horilla_generics.forms import HorillaMultiStepForm

from .models import Contact


# Define your contacts forms here
class ContactFormClass(OwnerQuerysetMixin, HorillaMultiStepForm):
    """
    Form class for contact
    """

    class Meta:
        """Meta options for the Contact form."""

        model = Contact
        fields = "__all__"

    step_fields = {
        1: [
            "contact_owner",
            "title",
            "first_name",
            "last_name",
            "phone",
            "email",
            "secondary_phone",
            "birth_date",
            "assistant",
            "assistant_phone",
            "contact_source",
            "parent_contact",
            "is_primary",
        ],
        2: ["address_city", "address_state", "address_country", "address_zip"],
        3: ["languages", "description"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make created_by and updated_by optional in intermediate steps
        if self.current_step < len(self.step_fields):
            self.fields["created_by"].required = False
            self.fields["updated_by"].required = False
            self.fields["is_primary"].required = False


class ChildContactForm(forms.Form):
    """
    Form to select an existing Contact and assign it as a child camContactpaign.
    """

    contact = forms.ModelChoiceField(
        queryset=Contact.objects.none(),  # Will be set in __init__
        label=_("Select Contact"),
        widget=forms.Select(
            attrs={
                "class": "select2-pagination w-full text-sm",
                "data-placeholder": "Select Contact",
                "data-url": reverse_lazy(
                    "horilla_generics:model_select2",
                    kwargs={"app_label": "contacts", "model_name": "Contact"},
                ),
                "data-field-name": "contact",
                "id": "id_contact",
            }
        ),
        help_text=_("Select the contact to assign as a child contact."),
    )

    parent_contact = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        widget=forms.HiddenInput(),  # Make this a hidden field
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        # Remove any generic form attributes that might be passed
        generic_attrs = ["full_width_fields", "dynamic_create_fields", "hidden_fields"]
        for attr in generic_attrs:
            kwargs.pop(attr, None)

        super().__init__(*args, **kwargs)

        self.setup_contact_queryset()

    def setup_contact_queryset(self):
        """
        Set up the contact queryset based on the request parameters.
        """
        if not self.request:
            self.fields["contact"].queryset = Contact.objects.all()
            return

        parent_id = self.request.GET.get("id")
        if not parent_id:
            self.fields["contact"].queryset = Contact.objects.all()
            return

        try:
            parent_contact = Contact.objects.get(pk=parent_id)

            queryset = Contact.objects.all()
            queryset = queryset.exclude(id=parent_id)

            queryset = queryset.filter(parent_contact__isnull=True)
            descendant_ids = self.get_descendant_ids(parent_contact)
            if descendant_ids:
                queryset = queryset.exclude(id__in=descendant_ids)

            self.fields["contact"].queryset = queryset

        except Contact.DoesNotExist:
            # If parent doesn't exist, show all accounts without parents
            self.fields["contact"].queryset = Contact.objects.filter(
                parent_contact__isnull=True
            )

    def get_descendant_ids(self, contact):
        """
        Get all descendant IDs of an Contact to prevent circular references.
        """
        descendant_ids = []
        children = Contact.objects.filter(parent_contact=contact)
        for child in children:
            descendant_ids.append(child.id)
            descendant_ids.extend(self.get_descendant_ids(child))
        return descendant_ids

    def clean_contact(self):
        """
        Validate the selected contact.
        """
        contact = self.cleaned_data.get("contact")
        if not contact:
            raise forms.ValidationError(_("Please select contact."))

        # Check if contact already has a parent
        if contact.parent_contact:
            raise forms.ValidationError(
                _("This contact already has a parent contact assigned.")
            )

        # Get parent from hidden field instead of request
        parent_contact = self.cleaned_data.get("parent_contact")
        if parent_contact and str(contact.id) == str(parent_contact.id):
            raise forms.ValidationError(_("An contact cannot be its own parent."))

        return contact

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get("contact")

        if not contact:
            raise forms.ValidationError(_("Please select a valid contact."))

        return cleaned_data
