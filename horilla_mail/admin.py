from django.contrib import admin

from horilla_mail.models import (
    HorillaMail,
    HorillaMailAttachment,
    HorillaMailConfiguration,
    HorillaMailTemplate,
)

# Register your horilla_mail models here.

admin.site.register(HorillaMailConfiguration)
admin.site.register(HorillaMail)
admin.site.register(HorillaMailAttachment)
admin.site.register(HorillaMailTemplate)
