from django.contrib import admin

from . import models

# Register your reports models here.


admin.site.register(models.ReportFolder)
admin.site.register(models.Report)
