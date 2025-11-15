""" "URL configuration for the timeline app."""

from django.urls import path

from . import views

app_name = "timeline"

urlpatterns = [
    # Define your URL patterns here
    path("calendar-view/", views.CalendarView.as_view(), name="calendar_view"),
    path(
        "calendar-save-preference/",
        views.SaveCalendarPreferencesView.as_view(),
        name="save_calendar_preferences",
    ),
    path(
        "calendar-events/",
        views.GetCalendarEventsView.as_view(),
        name="get_calendar_events",
    ),
    path("mark-completed/", views.MarkCompletedView.as_view(), name="mark_completed"),
    path(
        "mark-unavailability/",
        views.UserAvailabilityFormView.as_view(),
        name="mark_unavailability",
    ),
    path(
        "update-mark-unavailability/<int:pk>/",
        views.UserAvailabilityFormView.as_view(),
        name="update_mark_unavailability",
    ),
    path(
        "delete-mark-availability/<int:pk>/",
        views.UserAvailabilityDeleteView.as_view(),
        name="delete_mark_unavailability",
    ),
]
