from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _


class CustomFieldsConfig(AppLauncher):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "custom_fields"
    verbose_name = _("Custom Fields")

    url_prefix = "custom-fields/"
    url_module = "custom_fields.urls"
    url_namespace = "custom_fields"
    auto_import_modules = ["menu", "view_extensions"]

    def ready(self):
        super().ready()
        self._patch_lead_forms()
        self._patch_opportunity_forms()
        self._patch_detail_views()
        self._patch_detail_field_selector()
        self._patch_list_column_selector()

    def _patch_lead_forms(self):
        """Inject CustomField mixins into Lead form classes."""
        try:
            from custom_fields.integration import (
                CustomFieldMultiStepMixin,
                CustomFieldSingleFormMixin,
            )
            from horilla_crm.leads.forms import LeadFormClass, LeadSingleForm

            _inject_mixin(LeadFormClass, CustomFieldMultiStepMixin)
            _inject_mixin(LeadSingleForm, CustomFieldSingleFormMixin)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "custom_fields: could not patch Lead forms: %s", exc
            )

    def _patch_opportunity_forms(self):
        """Inject CustomField mixins into Opportunity form classes."""
        try:
            from custom_fields.integration import (
                CustomFieldMultiStepMixin,
                CustomFieldSingleFormMixin,
            )
            from horilla_crm.opportunities.forms import (
                OpportunityFormClass,
                OpportunitySingleForm,
            )

            _inject_mixin(OpportunityFormClass, CustomFieldMultiStepMixin)
            _inject_mixin(OpportunitySingleForm, CustomFieldSingleFormMixin)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "custom_fields: could not patch Opportunity forms: %s", exc
            )

    def _patch_detail_views(self):
        """Show custom fields on Lead and Opportunity detail pages."""
        try:
            from custom_fields.integration import CustomFieldDetailMixin
            from horilla_crm.leads.views.core import LeadDetailView
            from horilla_crm.leads.views.detail_tabs import LeadsDetailTab
            from horilla_crm.opportunities.views.core.detail import (
                OpportunityDetailTab,
                OpportunityDetailView,
            )

            _inject_mixin(LeadDetailView, CustomFieldDetailMixin)
            _inject_mixin(LeadsDetailTab, CustomFieldDetailMixin)
            _inject_mixin(OpportunityDetailView, CustomFieldDetailMixin)
            _inject_mixin(OpportunityDetailTab, CustomFieldDetailMixin)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "custom_fields: could not patch detail views: %s", exc
            )

    def _patch_detail_field_selector(self):
        """Inject custom fields into Horilla's Change Detail View Fields modal."""
        try:
            import custom_fields.view_extensions  # noqa: F401  # register ViewExtensions
            from custom_fields.detail_hooks import install_detail_field_patches

            install_detail_field_patches()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "custom_fields: could not patch detail field selector: %s", exc
            )

    def _patch_list_column_selector(self):
        """Inject custom fields into Horilla's Add Column to List modal."""
        try:
            from custom_fields.list_hooks import install_list_column_patches

            install_list_column_patches()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "custom_fields: could not patch list column selector: %s", exc
            )


def _inject_mixin(target_class, mixin_class):
    """
    Prepend mixin_class to target_class.__bases__ if not already there.
    This is safe to do once in AppConfig.ready().
    """
    if mixin_class in target_class.__mro__:
        return
    target_class.__bases__ = (mixin_class,) + target_class.__bases__
