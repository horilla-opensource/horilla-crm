"""
Defines URL patterns for campaign-related views, including creation, update, and deletion.
Supports child campaigns, members, and contact management routes.
Integrates with HTMX for dynamic campaign interactions.
"""

from django.urls import path

from . import views

app_name = "campaigns"

urlpatterns = [
    path("campaign-view/", views.CampaignView.as_view(), name="campaign_view"),
    path(
        "campaign-nav-view/", views.CampaignNavbar.as_view(), name="campaign_nav_view"
    ),
    path(
        "campaign-list-view/",
        views.CampaignListView.as_view(),
        name="campaign_list_view",
    ),
    path(
        "campaign-kanban-view/",
        views.CampaignKanbanView.as_view(),
        name="campaign_kanban_view",
    ),
    path("campaign-create/", views.CampaignFormView.as_view(), name="campaign_create"),
    path(
        "campaign-delete/<int:pk>/",
        views.CampaignDeleteView.as_view(),
        name="campaign_delete",
    ),
    path(
        "campaign-edit/<int:pk>/",
        views.CampaignFormView.as_view(),
        name="campaign_edit",
    ),
    path(
        "campaign-change-owner/<int:pk>/",
        views.CampaignChangeOwnerForm.as_view(),
        name="campaign_change_owner",
    ),
    path(
        "campaign-detail-view/<int:pk>/",
        views.CampaignDetailView.as_view(),
        name="campaign_detail_view",
    ),
    path(
        "campaign-detail-view-tabs/",
        views.CampaignDetailViewTabs.as_view(),
        name="campaign_detail_view_tabs",
    ),
    path(
        "campaign-details-tab-view/<int:pk>/",
        views.CampaignDetailsTab.as_view(),
        name="campaign_details_tab_view",
    ),
    path(
        "campaign-notes-attachments/<int:pk>/",
        views.CampaignNotesAndAttachments.as_view(),
        name="campaign_notes_attachments",
    ),
    path(
        "campaign-activity-tab-view/<int:pk>/",
        views.CampaignActivityTab.as_view(),
        name="campaign_activity_tab_view",
    ),
    path(
        "campaign-related-list-tab-view/<int:pk>/",
        views.CampaignRelatedListsTab.as_view(),
        name="campaign_related_list_tab_view",
    ),
    path(
        "campaign-history-tab-view/<int:pk>/",
        views.CampaignHistoryTab.as_view(),
        name="campaign_history_tab_view",
    ),
    path(
        "add-to-campaign/",
        views.AddToCampaignFormview.as_view(),
        name="add_to_campaign",
    ),
    path(
        "edit-campaign-member/<int:pk>/",
        views.AddToCampaignFormview.as_view(),
        name="edit_campaign_member",
    ),
    path(
        "add-campaign-members/",
        views.AddCampaignMemberFormview.as_view(),
        name="add_campaign_members",
    ),
    path(
        "edit-added-campaign-members/<int:pk>/",
        views.AddCampaignMemberFormview.as_view(),
        name="edit_added_campaign_members",
    ),
    path(
        "delete-campaign-member/<int:pk>/",
        views.CampaignMemberDeleteView.as_view(),
        name="delete_campaign_member",
    ),
    path(
        "add-contact-to-campaign/",
        views.AddContactToCampaignFormView.as_view(),
        name="add_contact_to_campaign",
    ),
    path(
        "edit-contact-to-campaign/<int:pk>/",
        views.AddContactToCampaignFormView.as_view(),
        name="edit_contact_to_campaign",
    ),
    path(
        "delete-campaign-contact-member/<int:pk>/",
        views.CampaignContactMemberDeleteView.as_view(),
        name="delete_campaign_contact_member",
    ),
    path(
        "create-child-campaign/",
        views.AddChildCampaignFormView.as_view(),
        name="create_child_campaign",
    ),
    path(
        "delete-child-campaign/<int:pk>/",
        views.ChildCampaignDeleteView.as_view(),
        name="delete_child_campaign",
    ),
]
