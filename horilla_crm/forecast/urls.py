"""
URL configuration for the forecast app.
"""

from django.urls import path

from . import forecast_target, forecast_type, views

app_name = "forecast"

urlpatterns = [
    path("forecast-view/", views.ForecastView.as_view(), name="forecast_view"),
    path(
        "forecast-navbar-view/",
        views.ForecastNavbarView.as_view(),
        name="forecast_navbar_view",
    ),
    path(
        "forecast-tab-view/", views.ForecastTabView.as_view(), name="forecast_tab_view"
    ),
    path(
        "forecast-type-view/<int:pk>/",
        views.ForecastTypeView.as_view(),
        name="forecast_type_view",
    ),
    path(
        "opportunities/<str:forecast_id>/<str:opportunity_type>/",
        views.ForecastOpportunitiesView.as_view(),
        name="forecast_opportunities",
    ),
    path(
        "forecast-target-view/",
        forecast_target.ForecastTargetView.as_view(),
        name="forecast_target_view",
    ),
    path(
        "forecast-target-nav-view/",
        forecast_target.ForecastTargetNavbar.as_view(),
        name="forecast_target_nav_view",
    ),
    path(
        "forecast-target-filters-view/",
        forecast_target.ForecastTargetFiltersView.as_view(),
        name="forecast_target_filters_view",
    ),
    path(
        "forecast-target-list-view/",
        forecast_target.ForecastTargetListView.as_view(),
        name="forecast_target_list_view",
    ),
    path(
        "forecast-target-form-view/",
        forecast_target.ForecastTargetFormView.as_view(),
        name="forecast_target_form_view",
    ),
    path(
        "toggle-role-based/",
        forecast_target.ToggleRoleBasedView.as_view(),
        name="toggle_role_based",
    ),
    path(
        "toggle-condition-fields/",
        forecast_target.ToggleConditionFieldsView.as_view(),
        name="toggle_condition_fields",
    ),
    path(
        "update-target-help-text/",
        forecast_target.UpdateTargetHelpTextView.as_view(),
        name="update_target_help_text",
    ),
    path(
        "forecast-target-update-form-view/<int:pk>/",
        forecast_target.UpdateForecastTarget.as_view(),
        name="forecast_target_update_form_view",
    ),
    path(
        "forecast-target-delete-view/<int:pk>/",
        forecast_target.ForecastTargetDeleteView.as_view(),
        name="forecast_target_delete_view",
    ),
    path(
        "forecast-type-view/",
        forecast_type.ForecastTypeView.as_view(),
        name="forecast_type_view",
    ),
    path(
        "forecast-type-nav-view/",
        forecast_type.ForecastTypeNavbar.as_view(),
        name="forecast_type_nav_view",
    ),
    path(
        "forecast-type-list-view/",
        forecast_type.ForecastTypeListView.as_view(),
        name="forecast_type_list_view",
    ),
    path(
        "forecast-type-create-form-view/",
        forecast_type.ForecastTypeFormView.as_view(),
        name="forecast_type_create_form_view",
    ),
    path(
        "forecast-type-update-form-view/<int:pk>/",
        forecast_type.ForecastTypeFormView.as_view(),
        name="forecast_type_update_form_view",
    ),
    path(
        "forecast-type-delete-view/<int:pk>/",
        forecast_type.ForecastTypeDeleteView.as_view(),
        name="forecast_type_delete_view",
    ),
]
