"""
Defines URL patterns for the Activity app, mapping various activity-related views
such as list, detail, create, update, delete, and Kanban views to their respective endpoints.
"""

from django.urls import path

from . import views

app_name = "activity"

urlpatterns = [
    path("activity-view/", views.ActivityView.as_view(), name="activity_view"),
    path(
        "activity-list-view/",
        views.AllActivityListView.as_view(),
        name="activity_list_view",
    ),
    path(
        "activity-nav-view/", views.ActivityNavbar.as_view(), name="activity_nav_view"
    ),
    path(
        "activity-kanban-view/",
        views.AcivityKanbanView.as_view(),
        name="activity_kanban_view",
    ),
    path("task-create-form/", views.TaskCreateForm.as_view(), name="task_create_form"),
    path(
        "task-update-form/<int:pk>/",
        views.TaskCreateForm.as_view(),
        name="task_update_form",
    ),
    path(
        "meeting-create-form/",
        views.MeetingsCreateForm.as_view(),
        name="meeting_create_form",
    ),
    path(
        "meeting-update-form/<int:pk>/",
        views.MeetingsCreateForm.as_view(),
        name="meeting_update_form",
    ),
    path(
        "call-create-form/",
        views.CallCreateForm.as_view(),
        name="call_create_form",
    ),
    path(
        "call-update-form/<int:pk>/",
        views.CallCreateForm.as_view(),
        name="call_update_form",
    ),
    path(
        "event-create-form/",
        views.EventCreateForm.as_view(),
        name="event_create_form",
    ),
    path(
        "event-update-form/<int:pk>/",
        views.EventCreateForm.as_view(),
        name="event_update_form",
    ),
    path(
        "tasks/<int:object_id>/",
        views.TaskListView.as_view(),
        name="task_list",
    ),
    path(
        "meetings/<int:object_id>/",
        views.MeetingListView.as_view(),
        name="meeting_list",
    ),
    path(
        "calls/<int:object_id>/",
        views.CallListView.as_view(),
        name="call_list",
    ),
    path(
        "emails/<int:object_id>/",
        views.EmailListView.as_view(),
        name="email_list",
    ),
    path(
        "events/<int:object_id>/",
        views.EventListView.as_view(),
        name="event_list",
    ),
    path(
        "delete-activity/<int:pk>/",
        views.ActivityDeleteView.as_view(),
        name="delete_activity",
    ),
    path(
        "activity-create-form/",
        views.ActivityCreateView.as_view(),
        name="activity_create_form",
    ),
    path(
        "activity-edit-form/<int:pk>/",
        views.ActivityCreateView.as_view(),
        name="activity_edit_form",
    ),
    path(
        "activity-detail/<int:pk>/",
        views.ActivityDetailView.as_view(),
        name="activity_detail",
    ),
    path(
        "activity-details-tab/<int:pk>/",
        views.ActivityDetailTab.as_view(),
        name="activity_details_tab",
    ),
    path(
        "activity-detail-view-tabs/",
        views.ActivityDetailViewTabView.as_view(),
        name="activity_detail_view_tabs",
    ),
    path(
        "activity-history-tab-view/<int:pk>/",
        views.ActivityHistoryTabView.as_view(),
        name="activity_history_tab_view",
    ),
    path(
        "activity-notes-attachments/<int:pk>/",
        views.ActivitynNotesAndAttachments.as_view(),
        name="activity_notes_attachments",
    ),
]
