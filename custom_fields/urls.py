from django.urls import path

from . import views

app_name = "custom_fields"

urlpatterns = [
    path("", views.CustomFieldView.as_view(), name="view"),
    path("navbar/", views.CustomFieldNavbar.as_view(), name="navbar"),
    path("list/", views.CustomFieldListView.as_view(), name="list"),
    path("create/", views.CustomFieldFormView.as_view(), name="create"),
    path("edit/<int:pk>/", views.CustomFieldFormView.as_view(), name="edit"),
    path("delete/<int:pk>/", views.CustomFieldDeleteView.as_view(), name="delete"),
]
