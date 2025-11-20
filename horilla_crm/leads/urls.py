"""URL configurations for the leads app."""

from django.urls import path
from django.views.generic import TemplateView

from horilla_crm.leads import mail_to_lead, web_to_lead

from . import lead_stage, views

app_name = "leads"

urlpatterns = [
    path("leads-view/", views.LeadView.as_view(), name="leads_view"),
    path("leads-nav/", views.LeadNavbar.as_view(), name="leads_nav"),
    path("leads-list/", views.LeadListView.as_view(), name="leads_list"),
    path("leads-delete/<int:pk>/", views.LeadDeleteView.as_view(), name="leads_delete"),
    path("leads-kanban/", views.LeadKanbanView.as_view(), name="leads_kanban"),
    path("leads-create/", views.LeadFormView.as_view(), name="leads_create"),
    path("leads-detail/<int:pk>/", views.LeadDetailView.as_view(), name="leads_detail"),
    path(
        "leads-details-tab/<int:pk>/",
        views.LeadsDetailTab.as_view(),
        name="leads_details_tab",
    ),
    path(
        "lead-detail-view-tabs/",
        views.LeadsDetailViewTabView.as_view(),
        name="lead_detail_view_tabs",
    ),
    path(
        "lead-activity-detail-view/<int:pk>/",
        views.LeadsActivityTabView.as_view(),
        name="lead_activity_detail_view",
    ),
    path(
        "lead-related-lists/<int:pk>/",
        views.LeadRelatedLists.as_view(),
        name="lead_related_lists",
    ),
    path("leads-edit/<int:pk>/", views.LeadFormView.as_view(), name="leads_edit"),
    path(
        "leads-create-single/",
        views.LeadsSingleFormView.as_view(),
        name="leads_create_single",
    ),
    path(
        "leads-edit-single/<int:pk>/",
        views.LeadsSingleFormView.as_view(),
        name="leads_edit_single",
    ),
    path(
        "lead-history-tab-view/<int:pk>/",
        views.LeadsHistoryTabView.as_view(),
        name="leads_history_tab_view",
    ),
    path(
        "convert-lead/<int:pk>/",
        views.LeadConversionView.as_view(),
        name="convert_lead",
    ),
    path(
        "lead-change-owner/<int:pk>/",
        views.LeadChangeOwnerForm.as_view(),
        name="lead_change_owner",
    ),
    path(
        "lead-stage-view/", lead_stage.LeadsStageView.as_view(), name="lead_stage_view"
    ),
    path(
        "lead-stage-nav-view/",
        lead_stage.LeadStageNavbar.as_view(),
        name="lead_stage_nav_view",
    ),
    path(
        "lead-stage-list-view/",
        lead_stage.LeadStageListView.as_view(),
        name="lead_stage_list_view",
    ),
    path(
        "change-lead-stage-final/<int:pk>/",
        lead_stage.ChangeFinalStage.as_view(),
        name="change_lead_stage_final",
    ),
    path(
        "edit-lead-stage/<int:pk>/",
        lead_stage.CreateLeadStage.as_view(),
        name="edit_lead_stage",
    ),
    path(
        "create-lead-stage/",
        lead_stage.CreateLeadStage.as_view(),
        name="create_lead_stage",
    ),
    path(
        "toggle-order-field/",
        lead_stage.ToggleOrderFieldView.as_view(),
        name="toggle_order_field",
    ),
    path(
        "delete-lead-stage/<int:pk>/",
        lead_stage.LeadStatusDeleteView.as_view(),
        name="delete_lead_stage",
    ),
    path(
        "update-lead-stage-order/",
        lead_stage.UpdateLeadStageOrderView.as_view(),
        name="update_lead_stage_order",
    ),
    path(
        "company/<int:company_id>/load-lead-stages/",
        lead_stage.LoadLeadStagesView.as_view(),
        name="load_lead_stages",
    ),
    path(
        "company/<int:pk>/create-stage-group/",
        lead_stage.CreateStageGroupView.as_view(),
        name="create_stage_group",
    ),
    path(
        "company/<int:company_id>/custom-stages-form/",
        lead_stage.CustomStagesFormView.as_view(),
        name="custom_stages_form",
    ),
    path(
        "company/<int:company_id>/save-custom-stages/",
        lead_stage.SaveCustomStagesView.as_view(),
        name="save_custom_stages",
    ),
    path(
        "company/<int:company_id>/add-stage/",
        lead_stage.AddStageView.as_view(),
        name="add_stage",
    ),
    path(
        "company/<int:company_id>/remove-stage/",
        lead_stage.RemoveStageView.as_view(),
        name="remove_stage",
    ),
    path(
        "initialize-lead-stages/",
        lead_stage.InitializeDatabaseLeadStages.as_view(),
        name="initialize_lead_stages",
    ),
    path(
        "leads-notes-attachments/<int:pk>/",
        views.LeadsNotesAndAttachments.as_view(),
        name="leads_notes_attachments",
    ),
    path(
        "mail-to-lead-view/",
        mail_to_lead.MailToLeadView.as_view(),
        name="mail_to_lead_view",
    ),
    path(
        "mail-to-lead-nav-bar/",
        mail_to_lead.MailToLeadNavbar.as_view(),
        name="mail_to_lead_nav_bar",
    ),
    path(
        "mail-to-lead-list-view/",
        mail_to_lead.MailToLeadListView.as_view(),
        name="mail_to_lead_list_view",
    ),
    path(
        "mail-to-lead-create-view/",
        mail_to_lead.MailToLeadFormView.as_view(),
        name="mail_to_lead_create_view",
    ),
    path(
        "mail-to-lead-upadte-view/<int:pk>/",
        mail_to_lead.MailToLeadFormView.as_view(),
        name="mail_to_lead_update_view",
    ),
    path(
        "mail-to-lead-delete-view/<int:pk>/",
        mail_to_lead.EmailToLeadConfigDeleteView.as_view(),
        name="mail_to_lead_delete_view",
    ),
    path(
        "form-builder/", web_to_lead.LeadFormBuilderView.as_view(), name="form_builder"
    ),
    # HTMX endpoints
    path(
        "form-builder/add-field/", web_to_lead.AddFieldView.as_view(), name="add_field"
    ),
    path(
        "form-builder/remove-field/",
        web_to_lead.RemoveFieldView.as_view(),
        name="remove_field",
    ),
    path(
        "form-builder/preview/",
        web_to_lead.UpdateFormPreviewView.as_view(),
        name="update_preview",
    ),
    path(
        "form-builder/save/", web_to_lead.SaveLeadFormView.as_view(), name="save_form"
    ),
    path(
        "update-heading/",
        web_to_lead.UpdateFormHeadingView.as_view(),
        name="update_heading",
    ),
    path(
        "toggle-return-url/",
        web_to_lead.ToggleReturnUrlView.as_view(),
        name="toggle_return_url",
    ),
    path(
        "capture/<int:form_id>/",
        web_to_lead.PublicLeadFormView.as_view(),
        name="public_lead_form",
    ),
]
