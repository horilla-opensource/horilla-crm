from django.urls import path

from . import views

app_name = "horilla_notifications"

urlpatterns = [
    path(
        "notifications-read/<int:pk>/",
        views.MarkNotificationReadView.as_view(),
        name="mark_read",
    ),
    path(
        "notifications-all-read/",
        views.MarkAllNotificationsReadView.as_view(),
        name="mark_all_read",
    ),
    path(
        "notification-delete/<int:pk>/",
        views.DeleteNotification.as_view(),
        name="notification_delete",
    ),
    path(
        "notification-all-delete/",
        views.DeleteAllNotification.as_view(),
        name="notification_all_delete",
    ),
    path(
        "open-notification/<int:pk>/",
        views.OpenNotificationView.as_view(),
        name="open_notification",
    ),
]
