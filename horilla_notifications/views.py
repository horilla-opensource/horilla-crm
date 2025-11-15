from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from horilla_core.decorators import htmx_required

from .models import Notification


class MarkNotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
            notif.read = True
            notif.save()
        except Notification.DoesNotExist:
            pass
        return HttpResponse(status=200)


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, "All notifications marked as read.")
        unread_notifications = Notification.objects.filter(
            user=request.user, read=False
        )
        return render(
            request,
            "notification_list.html",
            {
                "unread_notifications": unread_notifications,
            },
        )


class DeleteNotification(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
            notif.delete()
        except Notification.DoesNotExist:
            pass
        messages.success(request, "Notification Deleted.")
        response = HttpResponse(status=200)
        return response


class DeleteAllNotification(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user).delete()
        messages.success(request, f"All notifications cleared.")
        return render(request, "sidebar_list.html", {"request": request})


@method_decorator(htmx_required, name="dispatch")
class OpenNotificationView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
            notif.is_read = True
            notif.save()

            response = HttpResponse()
            response["HX-Redirect"] = notif.url
            return response

        except Notification.DoesNotExist:
            return render(request, "error/403.html", status=404)
