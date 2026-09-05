"""
Tests for the custom_fields app.
"""

from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from horilla.contrib.core.models import Company, HorillaContentType
from horilla.contrib.utils.middlewares import _thread_local
from horilla_crm.leads.models import Lead, LeadStatus
from horilla_crm.leads.forms import LeadFormClass, LeadSingleForm
from horilla_crm.opportunities.forms import OpportunityFormClass

from custom_fields.integration import (
    CustomFieldMultiStepMixin,
    CustomFieldSingleFormMixin,
)
from custom_fields.models import CustomFieldDefinition, CustomFieldValue
from custom_fields.utils import (
    build_custom_form_fields,
    load_custom_field_values,
    save_custom_field_values,
)


class CustomFieldDefinitionModelTests(TestCase):
    """Tests for CustomFieldDefinition model."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")

    def test_create_small_text_field(self):
        defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Industry Notes",
            field_type="small_text",
            is_required=False,
            company=self.company,
        )
        self.assertEqual(str(defn), "Industry Notes")
        self.assertTrue(defn.is_active)

    def test_create_choice_field_with_choices(self):
        defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Priority",
            field_type="choice",
            choices="Low, Medium, High",
            company=self.company,
        )
        self.assertEqual(defn.get_choices_list(), ["Low", "Medium", "High"])

    def test_unique_together_per_company(self):
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Field A",
            field_type="small_text",
            company=self.company,
        )
        with self.assertRaises(Exception):
            CustomFieldDefinition.objects.create(
                content_type=self.ct_lead,
                name="Field A",
                field_type="number",
                company=self.company,
            )


class CustomFieldValueModelTests(TestCase):
    """Tests for CustomFieldValue storage and retrieval."""

    def setUp(self):
        _thread_local.request = None
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        self.defn_text = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Notes",
            field_type="large_text",
            company=self.company,
        )
        self.defn_number = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Budget",
            field_type="number",
            company=self.company,
        )

    def test_set_and_get_text_value(self):
        cfv = CustomFieldValue(
            field_definition=self.defn_text,
            content_type=self.ct_lead,
            object_id=1,
            company=self.company,
        )
        cfv.set_value("Some long text")
        self.assertEqual(cfv.get_value(), "Some long text")
        self.assertEqual(cfv.value_text, "Some long text")

    def test_set_and_get_number_value(self):
        cfv = CustomFieldValue(
            field_definition=self.defn_number,
            content_type=self.ct_lead,
            object_id=1,
            company=self.company,
        )
        cfv.set_value("1234.56")
        self.assertEqual(cfv.get_value(), Decimal("1234.56"))
        self.assertEqual(cfv.value_number, Decimal("1234.56"))
        self.assertEqual(cfv.value_text, "")


class BuildCustomFormFieldsTests(TestCase):
    """Tests for building Django form fields from definitions."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        self._set_active_company(self.company)

    def _set_active_company(self, company):
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = company
        _thread_local.request = request

    def test_builds_fields_for_all_types(self):
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Small",
            field_type="small_text",
            company=self.company,
        )
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Large",
            field_type="large_text",
            company=self.company,
        )
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Num",
            field_type="number",
            is_required=True,
            company=self.company,
        )
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Choice",
            field_type="choice",
            choices="A, B, C",
            company=self.company,
        )

        fields = build_custom_form_fields(Lead)
        self.assertEqual(len(fields), 4)
        for key in fields:
            self.assertTrue(key.startswith("cf_"))

    def test_company_filtering(self):
        """Definitions from other companies should not appear."""
        other_company = Company.objects.create(name="Other Co")
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="My Field",
            field_type="small_text",
            company=self.company,
        )
        CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Other Field",
            field_type="small_text",
            company=other_company,
        )
        fields = build_custom_form_fields(Lead)
        labels = [f.label for f in fields.values()]
        self.assertIn("My Field", labels)
        self.assertNotIn("Other Field", labels)


class SaveLoadCustomFieldValuesTests(TestCase):
    """Tests for save/load utility functions."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Priority",
            field_type="choice",
            choices="Low, High",
            company=self.company,
        )

    def test_save_and_load_roundtrip(self):
        data = {f"cf_{self.defn.pk}": "High"}
        save_custom_field_values(Lead, 42, data, company=self.company)
        loaded = load_custom_field_values(Lead, 42)
        self.assertEqual(loaded[f"cf_{self.defn.pk}"], "High")

    def test_update_existing_value(self):
        data = {f"cf_{self.defn.pk}": "Low"}
        save_custom_field_values(Lead, 42, data, company=self.company)
        data = {f"cf_{self.defn.pk}": "High"}
        save_custom_field_values(Lead, 42, data, company=self.company)
        loaded = load_custom_field_values(Lead, 42)
        self.assertEqual(loaded[f"cf_{self.defn.pk}"], "High")
        self.assertEqual(
            CustomFieldValue.objects.filter(object_id=42).count(), 1
        )


class FormIntegrationTests(TestCase):
    """Tests that custom fields are injected into Lead/Opportunity forms."""

    def setUp(self):
        _thread_local.request = None
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request

        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Custom Note",
            field_type="small_text",
            is_required=True,
            company=self.company,
        )

    def test_multi_step_mixin_injected(self):
        self.assertIn(CustomFieldMultiStepMixin, LeadFormClass.__mro__)

    def test_single_form_mixin_injected(self):
        self.assertIn(CustomFieldSingleFormMixin, LeadSingleForm.__mro__)

    def test_custom_fields_visible_on_last_step(self):
        from django import forms as django_forms

        form = LeadFormClass(step=4)
        cf_key = f"cf_{self.defn.pk}"
        self.assertIn(cf_key, form.fields)
        self.assertFalse(
            isinstance(form.fields[cf_key].widget, django_forms.HiddenInput)
        )
        self.assertTrue(form.fields[cf_key].required)

    def test_custom_fields_hidden_on_other_steps(self):
        from django import forms as django_forms

        form = LeadFormClass(step=1)
        cf_key = f"cf_{self.defn.pk}"
        self.assertIn(cf_key, form.fields)
        self.assertTrue(
            isinstance(form.fields[cf_key].widget, django_forms.HiddenInput)
        )

    def test_custom_fields_in_single_form(self):
        form = LeadSingleForm()
        cf_key = f"cf_{self.defn.pk}"
        self.assertIn(cf_key, form.fields)
        self.assertEqual(form.fields[cf_key].label, "Custom Note")

    def test_opportunity_form_integration(self):
        ct_opp = HorillaContentType.objects.get(
            app_label="opportunities", model="opportunity"
        )
        CustomFieldDefinition.objects.create(
            content_type=ct_opp,
            name="Deal Size",
            field_type="number",
            company=self.company,
        )
        form = OpportunityFormClass(step=3)
        cf_keys = [k for k in form.fields if k.startswith("cf_")]
        self.assertEqual(len(cf_keys), 1)

    def test_html_required_attribute_is_disabled(self):
        """Last-step Save must not be blocked by native browser validation."""
        form = LeadFormClass(step=4)
        self.assertFalse(form.use_required_attribute)
        cf_key = f"cf_{self.defn.pk}"
        html = str(form[cf_key])
        self.assertNotIn("required", html)

    def test_save_m2m_persists_custom_fields(self):
        from horilla.auth.models import User
        from horilla_crm.leads.models import LeadStatus

        owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="x"
        )
        owner.company = self.company
        owner.save()
        status = LeadStatus.objects.create(
            name="New", order=1, probability=10, company=self.company
        )
        cf_key = f"cf_{self.defn.pk}"
        data = {
            "title": "Acme Lead",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "lead_owner": owner.pk,
            "lead_source": "website",
            "lead_status": status.pk,
            "lead_company": "Acme",
            "industry": "finance",
            "country": "US",
            "requirements": "Need a demo",
            cf_key: "Must follow up Friday",
        }
        form = LeadFormClass(data=data, step=4, form_data=data)
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save(commit=False)
        instance.company = self.company
        instance.save()
        form.save_m2m()
        loaded = load_custom_field_values(Lead, instance.pk)
        self.assertEqual(loaded[cf_key], "Must follow up Friday")


class CustomFieldListActionTests(TestCase):
    """List-view action attrs must survive str.format() placeholder replacement."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Follow-up Date",
            field_type="small_text",
            company=self.company,
        )

    def test_delete_action_attrs_format_without_keyerror(self):
        from horilla.contrib.generics.templatetags.horilla_tags.field_filters import (
            render_action_button,
        )

        from custom_fields.views import CustomFieldListView

        delete_action = CustomFieldListView.actions[1]
        html = render_action_button(delete_action, self.defn)
        self.assertIn("check_dependencies", html)
        self.assertIn(str(self.defn.get_delete_url()), html)


class CustomFieldDetailViewTests(TestCase):
    """Custom fields must appear on Lead/Opportunity detail pages."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Follow-up Date",
            field_type="small_text",
            company=self.company,
        )

    def test_detail_context_includes_custom_fields(self):
        from custom_fields.integration import apply_custom_fields_to_detail_context
        from horilla_crm.leads.models import Lead

        lead = Lead(pk=77)
        save_custom_field_values(
            Lead,
            77,
            {f"cf_{self.defn.pk}": "September 10"},
            company=self.company,
        )
        context = {
            "body": [("First Name", "first_name")],
            "non_editable_fields": ["id"],
        }
        apply_custom_fields_to_detail_context(context, lead)
        self.assertIn(("Follow-up Date", f"cf_{self.defn.pk}"), context["body"])
        self.assertEqual(getattr(lead, f"cf_{self.defn.pk}"), "September 10")
        self.assertNotIn(f"cf_{self.defn.pk}", context["non_editable_fields"])
        self.assertEqual(context["non_editable_fields"], ["id"])

    def test_detail_mixins_injected(self):
        from custom_fields.integration import CustomFieldDetailMixin
        from horilla_crm.leads.views.core import LeadDetailView
        from horilla_crm.leads.views.detail_tabs import LeadsDetailTab
        from horilla_crm.opportunities.views.core.detail import (
            OpportunityDetailTab,
            OpportunityDetailView,
        )

        self.assertIn(CustomFieldDetailMixin, LeadDetailView.__mro__)
        self.assertIn(CustomFieldDetailMixin, LeadsDetailTab.__mro__)
        self.assertIn(CustomFieldDetailMixin, OpportunityDetailView.__mro__)
        self.assertIn(CustomFieldDetailMixin, OpportunityDetailTab.__mro__)

    def test_saved_visibility_hides_removed_custom_fields(self):
        from horilla.auth.models import User
        from horilla.contrib.core.models import DetailFieldVisibility
        from horilla_crm.leads.models import Lead
        from horilla_crm.leads.views.detail_tabs import LeadsDetailTab

        from custom_fields.integration import apply_custom_fields_to_detail_context

        user = User.objects.create_user(
            username="picker", email="picker@test.com", password="x"
        )
        DetailFieldVisibility.all_objects.create(
            user=user,
            app_label="leads",
            model_name="lead",
            url_name="lead_detail",
            header_fields=[["First Name", "first_name"]],
            details_fields=[["First Name", "first_name"]],
        )
        lead = Lead(pk=77)
        request = RequestFactory().get("/x/?detail_url_name=lead_detail")
        request.user = user
        context = {"body": [("First Name", "first_name")]}
        apply_custom_fields_to_detail_context(
            context, lead, request=request, view=LeadsDetailTab()
        )
        body_names = [row[1] for row in context["body"]]
        self.assertNotIn(f"cf_{self.defn.pk}", body_names)

    def test_saved_visibility_inserts_custom_field_in_order(self):
        from horilla.auth.models import User
        from horilla.contrib.core.models import DetailFieldVisibility
        from horilla_crm.leads.models import Lead
        from horilla_crm.leads.views.detail_tabs import LeadsDetailTab

        from custom_fields.integration import apply_custom_fields_to_detail_context

        user = User.objects.create_user(
            username="picker2", email="picker2@test.com", password="x"
        )
        cf_key = f"cf_{self.defn.pk}"
        DetailFieldVisibility.all_objects.create(
            user=user,
            app_label="leads",
            model_name="lead",
            url_name="lead_detail",
            header_fields=[["First Name", "first_name"]],
            details_fields=[
                ["First Name", "first_name"],
                ["Follow-up Date", cf_key],
                ["Email", "email"],
            ],
        )
        lead = Lead(pk=88)
        request = RequestFactory().get("/x/?detail_url_name=lead_detail")
        request.user = user
        context = {
            "body": [("First Name", "first_name"), ("Email", "email")],
        }
        apply_custom_fields_to_detail_context(
            context, lead, request=request, view=LeadsDetailTab()
        )
        self.assertEqual(
            [row[1] for row in context["body"]],
            ["first_name", cf_key, "email"],
        )


class CustomFieldSelectorTests(TestCase):
    """Custom fields must appear in the Change Detail View Fields modal."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Industry Notes",
            field_type="small_text",
            company=self.company,
        )

    def test_injects_into_available_lists(self):
        from custom_fields.detail_hooks import (
            inject_custom_fields_into_selector_context,
        )

        cf_key = f"cf_{self.defn.pk}"
        context = {
            "app_label": "leads",
            "model_name": "lead",
            "header_fields": [["First Name", "first_name"]],
            "details_fields": [["Email", "email"]],
            "header_available": [["Title", "title"]],
            "details_available": [["Phone", "phone"]],
        }
        inject_custom_fields_into_selector_context(context)
        self.assertIn([self.defn.name, cf_key], context["header_available"])
        self.assertIn([self.defn.name, cf_key], context["details_available"])
        self.assertNotIn(cf_key, [row[1] for row in context["header_fields"]])
        self.assertNotIn(cf_key, [row[1] for row in context["details_fields"]])

    def test_relabels_selected_custom_fields(self):
        from custom_fields.detail_hooks import (
            inject_custom_fields_into_selector_context,
        )

        cf_key = f"cf_{self.defn.pk}"
        context = {
            "app_label": "leads",
            "model_name": "lead",
            "header_fields": [["Cf 5", cf_key]],
            "details_fields": [],
            "header_available": [],
            "details_available": [["Title", "title"]],
        }
        inject_custom_fields_into_selector_context(context)
        self.assertEqual(context["header_fields"][0], [self.defn.name, cf_key])
        self.assertNotIn(cf_key, [row[1] for row in context["header_available"]])
        self.assertIn([self.defn.name, cf_key], context["details_available"])

    def test_defaults_include_custom_fields_in_details(self):
        from custom_fields.detail_hooks import append_custom_fields_to_defaults

        header, details = append_custom_fields_to_defaults(
            Lead, [["Title", "title"]], [["Email", "email"]]
        )
        self.assertEqual(header, [["Title", "title"]])
        self.assertIn([self.defn.name, f"cf_{self.defn.pk}"], details)

    def test_selector_response_html_includes_custom_field(self):
        from horilla.auth.models import User
        from horilla.contrib.generics.views.helpers.detail_field import (
            DetailFieldSelectorView,
        )

        user = User.objects.create_user(
            username="selector", email="selector@test.com", password="x"
        )
        user.company = self.company
        user.save()
        request = RequestFactory().get(
            "/generics/detail-field-selector/",
            {
                "app_label": "leads",
                "model_name": "lead",
                "url_name": "leads_detail",
            },
            HTTP_HX_REQUEST="true",
        )
        request.user = user
        request.active_company = self.company
        _thread_local.request = request
        response = DetailFieldSelectorView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Industry Notes", html)
        self.assertIn(f"cf_{self.defn.pk}", html)


class CustomFieldInlineEditTests(TestCase):
    """Pen-icon inline edit must work for custom fields."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Priority",
            field_type="choice",
            choices="Low, High",
            company=self.company,
        )

    def test_build_custom_field_info_for_choice(self):
        from custom_fields.detail_hooks import build_custom_field_info
        from horilla_crm.leads.models import Lead

        lead = Lead(pk=9)
        save_custom_field_values(
            Lead, 9, {f"cf_{self.defn.pk}": "High"}, company=self.company
        )
        info = build_custom_field_info(self.defn, lead)
        self.assertEqual(info["name"], f"cf_{self.defn.pk}")
        self.assertEqual(info["field_type"], "select")
        self.assertEqual(info["value"], "High")
        self.assertFalse(info["use_select2"])
        values = [choice["value"] for choice in info["choices"]]
        self.assertIn("Low", values)
        self.assertIn("High", values)

    def test_view_extensions_registered(self):
        from horilla.contrib.generics.views.helpers.edit_field import (
            CancelEditView,
            EditFieldView,
            UpdateFieldView,
        )
        from horilla.extension.view.resolve import resolve_view_class

        edit_cls = resolve_view_class(EditFieldView)
        update_cls = resolve_view_class(UpdateFieldView)
        cancel_cls = resolve_view_class(CancelEditView)
        self.assertTrue(hasattr(edit_cls, "get"))
        self.assertNotEqual(edit_cls, EditFieldView)
        self.assertNotEqual(update_cls, UpdateFieldView)
        self.assertNotEqual(cancel_cls, CancelEditView)

    def test_inline_update_persists_value(self):
        from horilla.auth.models import User
        from horilla_crm.leads.models import Lead, LeadStatus

        from custom_fields.detail_hooks import handle_custom_field_update_post

        owner = User.objects.create_user(
            username="editor", email="editor@test.com", password="x"
        )
        owner.company = self.company
        owner.is_superuser = True
        owner.save()
        status = LeadStatus.objects.create(
            name="New", order=1, probability=10, company=self.company
        )
        lead = Lead.objects.create(
            title="Acme",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            lead_owner=owner,
            lead_source="website",
            lead_status=status,
            lead_company="Acme",
            industry="finance",
            country="US",
            company=self.company,
        )
        cf_key = f"cf_{self.defn.pk}"
        request = RequestFactory().post(
            "/", {cf_key: "Low"}, HTTP_HX_REQUEST="true"
        )
        request.user = owner
        response = handle_custom_field_update_post(
            request,
            lead.pk,
            cf_key,
            lead._meta.app_label,
            lead._meta.model_name,
        )
        self.assertEqual(response.status_code, 200)
        loaded = load_custom_field_values(Lead, lead.pk)
        self.assertEqual(loaded[cf_key], "Low")

    def test_edit_get_renders_pen_editor_partial(self):
        from horilla.auth.models import User
        from horilla.contrib.generics.views.helpers.edit_field import EditFieldView
        from horilla.extension.view.resolve import resolve_view_class
        from horilla_crm.leads.models import Lead, LeadStatus

        owner = User.objects.create_user(
            username="pen", email="pen@test.com", password="x"
        )
        owner.company = self.company
        owner.is_superuser = True
        owner.save()
        status = LeadStatus.objects.create(
            name="New", order=1, probability=10, company=self.company
        )
        lead = Lead.objects.create(
            title="Acme",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            lead_owner=owner,
            lead_source="website",
            lead_status=status,
            lead_company="Acme",
            industry="finance",
            country="US",
            company=self.company,
        )
        cf_key = f"cf_{self.defn.pk}"
        request = RequestFactory().get(
            f"/generics/edit/{lead.pk}/{cf_key}/leads/lead/",
            HTTP_HX_REQUEST="true",
        )
        request.user = owner
        request.active_company = self.company
        _thread_local.request = request
        view = resolve_view_class(EditFieldView).as_view()
        response = view(
            request,
            pk=lead.pk,
            field_name=cf_key,
            app_label=lead._meta.app_label,
            model_name=lead._meta.model_name,
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Priority", html)
        self.assertIn(cf_key, html)
        self.assertIn("Low", html)
        self.assertIn("High", html)
        self.assertIn(f'id="field-{cf_key}"', html)


class CustomFieldMultiStepCleanTests(TestCase):
    """Last-step clean must handle cf_* without editing Horilla multi_step.py."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Crash Check",
            field_type="small_text",
            is_required=True,
            company=self.company,
        )

    def test_last_step_clean_does_not_crash_for_custom_fields(self):
        form = LeadFormClass(data={"title": "x"}, step=4)
        try:
            form.is_valid()
        except AttributeError as exc:
            self.fail(f"last-step clean crashed on custom fields: {exc}")
        cf_key = f"cf_{self.defn.pk}"
        self.assertIn(cf_key, form.errors)

    def test_horilla_multistep_source_unpatched(self):
        from pathlib import Path

        text = Path("horilla/contrib/generics/forms/multi_step.py").read_text()
        self.assertNotIn(
            "from django.core.exceptions import FieldDoesNotExist", text
        )
        self.assertIn("except models.FieldDoesNotExist:", text)


class CustomFieldListColumnTests(TestCase):
    """Custom fields must appear in the Add Column to List modal."""

    def setUp(self):
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware
        from horilla.auth.models import User

        from custom_fields.list_hooks import install_list_column_patches

        install_list_column_patches()
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request
        self.defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Industry Notes",
            field_type="small_text",
            company=self.company,
        )
        self.user = User.objects.create_user(
            username="cols", email="cols@test.com", password="x"
        )
        self.user.company = self.company
        self.user.is_superuser = True
        self.user.save()
        request.user = self.user
        _thread_local.request = request
        self._session_middleware = SessionMiddleware(lambda r: None)
        self._FallbackStorage = FallbackStorage

    def tearDown(self):
        _thread_local.request = None
        super().tearDown()

    def _htmx_request(self, method="get", data=None):
        path = "/generics/column-selector/"
        if method == "post":
            request = RequestFactory().post(
                path, data=data or {}, HTTP_HX_REQUEST="true"
            )
        else:
            request = RequestFactory().get(
                path, data=data or {}, HTTP_HX_REQUEST="true"
            )
        self._session_middleware.process_request(request)
        request.session.save()
        request._messages = self._FallbackStorage(request)
        request.user = self.user
        request.active_company = self.company
        _thread_local.request = request
        return request

    def test_injects_into_available_list(self):
        from custom_fields.list_hooks import (
            inject_custom_fields_into_column_selector,
        )

        cf_key = f"cf_{self.defn.pk}"
        context = {
            "app_label": "leads",
            "model_name": "Lead",
            "visible_fields": [["Title", "title"]],
            "available_fields": [["Email", "email"]],
        }
        inject_custom_fields_into_column_selector(context)
        self.assertIn([self.defn.name, cf_key], context["available_fields"])
        self.assertNotIn(cf_key, [row[1] for row in context["visible_fields"]])

    def test_relabels_selected_custom_fields(self):
        from custom_fields.list_hooks import (
            inject_custom_fields_into_column_selector,
        )

        cf_key = f"cf_{self.defn.pk}"
        context = {
            "app_label": "leads",
            "model_name": "Lead",
            "visible_fields": [["Cf 5", cf_key]],
            "available_fields": [["Email", "email"]],
        }
        inject_custom_fields_into_column_selector(context)
        self.assertEqual(context["visible_fields"][0], [self.defn.name, cf_key])
        self.assertNotIn(cf_key, [row[1] for row in context["available_fields"]])

    def test_selector_response_html_includes_custom_field(self):
        from horilla.contrib.generics.views.helpers.list_column import (
            ListColumnSelectFormView,
        )

        request = self._htmx_request(
            "get",
            {
                "app_label": "leads",
                "model_name": "Lead",
                "url_name": "leads_list",
            },
        )
        response = ListColumnSelectFormView.as_view()(request)
        if hasattr(response, "render"):
            response.render()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Industry Notes", html)
        self.assertIn(f"cf_{self.defn.pk}", html)

    def test_column_form_accepts_custom_field_choice(self):
        from horilla.contrib.generics.forms import ColumnSelectionForm

        cf_key = f"cf_{self.defn.pk}"
        form = ColumnSelectionForm(
            model=Lead,
            app_label="leads",
            model_name="Lead",
            path_context="leads",
            user=self.user,
            url_name="leads_list",
        )
        choice_values = [choice[0] for choice in form.fields["visible_fields"].choices]
        self.assertIn(cf_key, choice_values)

    def test_saving_column_relabels_custom_field(self):
        from horilla.contrib.core.models import ListColumnVisibility
        from horilla.contrib.generics.views.helpers.list_column import (
            ListColumnSelectFormView,
        )

        cf_key = f"cf_{self.defn.pk}"
        request = self._htmx_request(
            "post",
            {
                "app_label": "leads",
                "model_name": "leads.Lead",
                "url_name": "leads_list",
                "visible_fields": ["title", cf_key],
            },
        )
        response = ListColumnSelectFormView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        saved = ListColumnVisibility.all_objects.filter(
            user=self.user, app_label="leads", model_name="Lead"
        ).first()
        self.assertIsNotNone(saved)
        names = [row[1] for row in saved.visible_fields]
        self.assertIn(cf_key, names)
        label = next(row[0] for row in saved.visible_fields if row[1] == cf_key)
        self.assertEqual(label, self.defn.name)

    def test_attach_values_to_list_objects(self):
        from horilla_crm.leads.models import Lead, LeadStatus

        from custom_fields.list_hooks import attach_custom_field_values_to_objects

        status = LeadStatus.objects.create(
            name="New", order=1, probability=10, company=self.company
        )
        lead = Lead.objects.create(
            title="Acme",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            lead_owner=self.user,
            lead_source="website",
            lead_status=status,
            lead_company="Acme",
            industry="finance",
            country="US",
            company=self.company,
        )
        cf_key = f"cf_{self.defn.pk}"
        save_custom_field_values(
            Lead, lead.pk, {cf_key: "Aerospace"}, company=self.company
        )
        attach_custom_field_values_to_objects(Lead, [lead])
        self.assertEqual(getattr(lead, cf_key), "Aerospace")


class CustomFieldChoicesVisibilityTests(TestCase):
    """Choices textarea is shown only for Multiple Choice fields."""

    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.ct_lead = HorillaContentType.objects.get(app_label="leads", model="lead")
        rf = RequestFactory()
        request = rf.get("/")
        request.active_company = self.company
        _thread_local.request = request

    def test_new_form_hides_choices(self):
        from custom_fields.forms import CustomFieldDefinitionForm

        form = CustomFieldDefinitionForm()
        self.assertEqual(
            form.fields["choices"].widget.attrs.get("container_style"),
            "display: none;",
        )
        field_html = str(form["field_type"])
        self.assertIn("choices_container", field_html)
        self.assertIn('value="choice"', field_html)
        self.assertIn("Multiple Choice", field_html)

    def test_choice_instance_shows_choices(self):
        from custom_fields.forms import CustomFieldDefinitionForm

        defn = CustomFieldDefinition.objects.create(
            content_type=self.ct_lead,
            name="Priority",
            field_type="choice",
            choices="Low, High",
            company=self.company,
        )
        form = CustomFieldDefinitionForm(instance=defn)
        self.assertNotEqual(
            form.fields["choices"].widget.attrs.get("container_style"),
            "display: none;",
        )

    def test_bound_choice_type_shows_choices(self):
        from custom_fields.forms import CustomFieldDefinitionForm

        form = CustomFieldDefinitionForm(
            data={
                "content_type": self.ct_lead.pk,
                "name": "Priority",
                "field_type": "choice",
                "choices": "Low, High",
                "order": 0,
            }
        )
        self.assertNotEqual(
            form.fields["choices"].widget.attrs.get("container_style"),
            "display: none;",
        )


class CustomFieldSettingsMenuTests(TestCase):
    """Settings sidebar section is Custom Field, not CRM."""

    def test_section_title_is_custom_field(self):
        from custom_fields.menu import CustomFieldsSettings

        self.assertEqual(str(CustomFieldsSettings.title), "Custom Field")
        self.assertNotEqual(str(CustomFieldsSettings.title), "CRM")

    def test_settings_icon_exists(self):
        from django.contrib.staticfiles import finders

        from custom_fields.menu import CustomFieldsSettings

        self.assertEqual(CustomFieldsSettings.icon, "/assets/icons/custom-field.svg")
        icon_path = (
            Path(__file__).resolve().parent
            / "static"
            / CustomFieldsSettings.icon.lstrip("/")
        )
        self.assertTrue(icon_path.is_file(), icon_path)
        svg = icon_path.read_text(encoding="utf-8")
        self.assertIn("viewBox", svg)
        self.assertIn("#e54f38", svg)
        self.assertIsNotNone(finders.find("assets/icons/custom-field.svg"))


class CustomFieldI18NTests(TestCase):
    """Locale catalogs match other apps and Persian strings are filled."""

    app_dir = Path(__file__).resolve().parent
    fa_po = app_dir / "locale" / "fa" / "LC_MESSAGES" / "django.po"

    def test_locale_languages_match_leads_app(self):
        leads_locale = Path(__file__).resolve().parents[1] / "horilla_crm" / "leads" / "locale"
        leads_langs = {p.name for p in leads_locale.iterdir() if p.is_dir()}
        our_langs = {p.name for p in (self.app_dir / "locale").iterdir() if p.is_dir()}
        self.assertTrue(leads_langs)
        self.assertEqual(leads_langs, our_langs)

    def test_fa_catalog_has_persian_translations(self):
        text = self.fa_po.read_text(encoding="utf-8")
        self.assertIn('Language: fa', text)
        expected = {
            "Custom Field": "فیلد سفارشی",
            "Custom Fields": "فیلدهای سفارشی",
            "Field Name": "نام فیلد",
            "Field Type": "نوع فیلد",
            "Small Text": "متن کوتاه",
            "Large Text": "متن بلند",
            "Multiple Choice": "چندگزینه‌ای",
            "Required": "الزامی",
            "Choices": "گزینه‌ها",
            "Display Order": "ترتیب نمایش",
        }
        for msgid, msgstr in expected.items():
            self.assertIn(f'msgid "{msgid}"', text)
            self.assertIn(f'msgstr "{msgstr}"', text)

    def test_fa_catalog_has_no_empty_msgstr(self):
        entries = _parse_po_entries(self.fa_po.read_text(encoding="utf-8"))
        self.assertGreater(len(entries), 10)
        empty = [msgid for msgid, msgstr in entries.items() if msgid and not msgstr]
        self.assertEqual(empty, [])

    def test_persian_gettext_loads_fa_catalog(self):
        import subprocess

        from django.utils.translation import gettext, override, trans_real

        mo = self.fa_po.with_suffix(".mo")
        subprocess.run(["msgfmt", "-o", str(mo), str(self.fa_po)], check=True)
        trans_real._translations.clear()
        try:
            with override("fa"):
                self.assertEqual(gettext("Custom Field"), "فیلد سفارشی")
                self.assertEqual(gettext("Custom Fields"), "فیلدهای سفارشی")
                self.assertEqual(gettext("Field Name"), "نام فیلد")
        finally:
            if mo.exists():
                mo.unlink()
            trans_real._translations.clear()


def _parse_po_entries(text):
    """Return {msgid: msgstr} for a simple django.po catalog."""
    entries = {}
    msgid = None
    msgstr = None
    in_msgid = False
    in_msgstr = False
    current = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("msgid "):
            if msgid is not None and msgstr is not None:
                entries[msgid] = msgstr
            msgid = _unwrap_po_string(line[len("msgid ") :])
            msgstr = None
            in_msgid = True
            in_msgstr = False
            current = msgid
        elif line.startswith("msgstr "):
            msgstr = _unwrap_po_string(line[len("msgstr ") :])
            in_msgid = False
            in_msgstr = True
            current = msgstr
        elif line.startswith('"') and (in_msgid or in_msgstr):
            current += _unwrap_po_string(line)
            if in_msgid:
                msgid = current
            else:
                msgstr = current
        elif not line or line.startswith("#"):
            continue
    if msgid is not None and msgstr is not None:
        entries[msgid] = msgstr
    return entries


def _unwrap_po_string(value):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value
