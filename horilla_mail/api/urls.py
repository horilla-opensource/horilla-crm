"""
URL patterns for horilla_mail API, consistent with horilla_core
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_mail.api.views import (
    HorillaMailAttachmentViewSet,
    HorillaMailConfigurationViewSet,
    HorillaMailTemplateViewSet,
    HorillaMailViewSet,
)

router = DefaultRouter()
router.register(r"mail-configurations", HorillaMailConfigurationViewSet)
router.register(r"mails", HorillaMailViewSet)
router.register(r"mail-attachments", HorillaMailAttachmentViewSet)
router.register(r"mail-templates", HorillaMailTemplateViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
