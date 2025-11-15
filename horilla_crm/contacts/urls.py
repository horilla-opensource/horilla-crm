"""
URL configuration for the Contacts app.
"""

from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("contacts-view/", views.ContactView.as_view(), name="contacts_view"),
    path("contacts-navbar/", views.ContactNavbar.as_view(), name="contacts_navbar"),
    path(
        "contact-list-view/", views.ContactListView.as_view(), name="contact_list_view"
    ),
    path(
        "contact-kanban-view/",
        views.ContactKanbanView.as_view(),
        name="contact_kanban_view",
    ),
    path(
        "contact-create-form/",
        views.ContactFormView.as_view(),
        name="contact_create_form",
    ),
    path(
        "related-account-contact-create-form/",
        views.RelatedContactFormView.as_view(),
        name="related_account_contact_create_form",
    ),
    path(
        "contact-delete/<int:pk>/",
        views.ContactDeleteView.as_view(),
        name="contact_delete",
    ),
    path(
        "contact-update-form/<int:pk>/",
        views.ContactFormView.as_view(),
        name="contact_update_form",
    ),
    path(
        "contact-change-owner/<int:pk>/",
        views.ContactChangeOwnerFormView.as_view(),
        name="contact_change_owner",
    ),
    path(
        "contact-detail-view/<int:pk>/",
        views.ContactDetailView.as_view(),
        name="contact_detail_view",
    ),
    path(
        "contact-notes-attachments/<int:pk>/",
        views.ContactsNotesAndAttachments.as_view(),
        name="contacts_notes_attachements",
    ),
    path(
        "contact-detail-view-tabs/",
        views.ContactDetailViewTabs.as_view(),
        name="contact_detail_view_tabs",
    ),
    path(
        "contact-details-tab/<int:pk>/",
        views.ContactDetailTab.as_view(),
        name="contact_details_tab",
    ),
    path(
        "contact-activity-tab/<int:pk>/",
        views.ContactActivityTab.as_view(),
        name="contact_activity_tab",
    ),
    path(
        "contact-history-tab/<int:pk>/",
        views.ContactHistorytab.as_view(),
        name="contact_history_tab",
    ),
    path(
        "contact-related-list-tab/<int:pk>/",
        views.ContactRelatedListsTab.as_view(),
        name="contact_related_list_tab",
    ),
    path(
        "create-contact-account-relation/",
        views.AddRelatedAccountsFormView.as_view(),
        name="create_contact_account_relation",
    ),
    path(
        "update-contact-account-relation/<int:pk>/",
        views.AddRelatedAccountsFormView.as_view(),
        name="edit_contact_account_relation",
    ),
    path(
        "create-child-contact/",
        views.AddChildContactFormView.as_view(),
        name="create_child_contact",
    ),
    path(
        "delete-child-contacts/<int:pk>/",
        views.ChildContactDeleteView.as_view(),
        name="delete_child_contacts",
    ),
    path(
        "delete-related-accounts/<int:pk>/",
        views.RelatedContactDeleteView.as_view(),
        name="delete_related_accounts",
    ),
]
