from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from horilla_core.change_password import ChangePasswordFormView, ChangePasswordView
from horilla_core.forgot_password import ForgotPasswordView, PasswordResetConfirmView

from . import branches as branches_views
from . import customer_role as customer_role_views
from . import departments as department_views
from . import export_data as export_data_views
from . import fiscal_year as fiscal_year_views
from . import groups_and_permissions as permission_views
from . import import_data, initialiaze_database, load_data
from . import multiple_currency as multiple_currency_views
from . import partner_role as partner_role_views
from . import recycle_bin as recycle_bin_views
from . import regional_formating as regional_formating_views
from . import roles as roles_views
from . import scoring_rule as scoring_rule_views
from . import team_role as team_role_views
from . import user_holidays as user_holidays_views
from . import user_login_history as user_login_history_views
from . import users as user_views
from . import views

app_name = "horilla_core"
urlpatterns = [
    # Include API URLs
    re_path(r"^media/(?P<path>.*)$", views.protected_media, name="protected_media"),
    path("api/", include("horilla_core.api.urls")),
    path("", views.HomePageView.as_view(), name="home_view"),
    path("login/", views.LoginUserView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("active-tab/", views.SaveActiveTabView.as_view(), name="active_tab"),
    path(
        "favicon.ico", RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"))
    ),
    path("settings-view/", views.SettingView.as_view(), name="settings_view"),
    path("my-settings-view/", views.MySettingView.as_view(), name="my_settings_view"),
    path(
        "company-details-tab/",
        views.CompanyDetailsTab.as_view(),
        name="company_details_tab",
    ),
    path(
        "company-information/",
        views.ConmpanyInformationView.as_view(),
        name="company_information",
    ),
    path(
        "company-tab-view/",
        views.ConmpanyInformationTabView.as_view(),
        name="company_tab_view",
    ),
    path(
        "company-fiscal-year-tab/",
        views.CompanyFiscalYearTab.as_view(),
        name="company_fiscal_year_tab",
    ),
    path(
        "edit-company/<int:pk>/", views.CompanyFormView.as_view(), name="edit_company"
    ),
    path("create-company/", views.CompanyFormView.as_view(), name="create_company"),
    path(
        "switch-company/<int:company_id>/",
        views.SwitchCompanyView.as_view(),
        name="switch_company",
    ),
    # Holiday Urls
    path(
        "holiday-list-view/", views.HolidayListView.as_view(), name="holiday_list_view"
    ),
    path("holiday-view/", views.HolidayView.as_view(), name="holiday_view"),
    path(
        "holiday-create-form/",
        views.HolidayFormView.as_view(),
        name="holiday_create_form",
    ),
    path(
        "holiday-update-form/<int:pk>/",
        views.HolidayFormView.as_view(),
        name="holiday_update_form",
    ),
    path(
        "holiday-delete-view/<int:pk>/",
        views.HolidayDeleteView.as_view(),
        name="holiday_delete_view",
    ),
    path(
        "holiday-detail-view/<int:pk>/",
        views.HolidayDetailView.as_view(),
        name="holiday_detail_view",
    ),
    # Fiscal Year Urls
    path(
        "fiscal-year-form/",
        fiscal_year_views.FiscalYearFormView.as_view(),
        name="fiscal_year_form",
    ),
    path(
        "fiscal-year-form/<int:pk>/",
        fiscal_year_views.FiscalYearFormView.as_view(),
        name="fiscal_year_form_edit",
    ),
    path(
        "fiscal-year-fields/",
        fiscal_year_views.FiscalYearFieldsView.as_view(),
        name="fiscal_year_fields",
    ),
    path(
        "fiscal-year-calendar-preview/",
        fiscal_year_views.FiscalYearCalendarPreviewView.as_view(),
        name="fiscal_year_calendar_preview",
    ),
    path(
        "fiscal-year-calendar/<int:pk>/",
        fiscal_year_views.FiscalYearCalendarView.as_view(),
        name="fiscal_year_calendar",
    ),
    path(
        "calculate-week-start-day/",
        fiscal_year_views.CalculateWeekStartDayView.as_view(),
        name="calculate_week_start_day",
    ),
    # Multiple Currency Urls
    path(
        "multiple-currency/",
        views.CompanyMultipleCurrency.as_view(),
        name="multiple_currency",
    ),
    path(
        "currency-list-view/",
        multiple_currency_views.CurrencyListView.as_view(),
        name="currency_list_view",
    ),
    path(
        "change-default-currency/<int:pk>/",
        multiple_currency_views.ChangeDefaultCurrencyView.as_view(),
        name="change_default_currency",
    ),
    path(
        "add-currency/",
        multiple_currency_views.AddCurrencyView.as_view(),
        name="add_currency",
    ),
    path(
        "edit-currency/<int:pk>/",
        multiple_currency_views.AddCurrencyView.as_view(),
        name="edit_currency",
    ),
    path(
        "change-default-currency-form/",
        multiple_currency_views.ChangeDefaultCurrencyFormView.as_view(),
        name="change_default_currency_view",
    ),
    path(
        "change-conversion-rate-view/",
        multiple_currency_views.ConversionRateFormView.as_view(),
        name="conversion_rate_view",
    ),
    path(
        "dated-conversion-rates/",
        multiple_currency_views.DatedConversionRateFormView.as_view(),
        name="dated_conversion_rate_view",
    ),
    path(
        "dated-currency-list-view/",
        multiple_currency_views.DatedCurrencyListView.as_view(),
        name="dated_currency_list_view",
    ),
    path(
        "delete-currency/<int:pk>/",
        multiple_currency_views.CurrencyDeleteView.as_view(),
        name="delete_currency",
    ),
    # Business Hour urls
    path(
        "business-hour-view/",
        views.BusinessHourView.as_view(),
        name="business_hour_view",
    ),
    path(
        "business-hour-list-view/",
        views.BusinessHourListView.as_view(),
        name="business_hour_list_view",
    ),
    path(
        "business-hour-create-form/",
        views.BusinessHourFormView.as_view(),
        name="business_hour_create_form",
    ),
    path(
        "business-hour-update-form/<int:pk>/",
        views.BusinessHourFormView.as_view(),
        name="business_hour_update_form",
    ),
    path(
        "business-hour-delete-view/<int:pk>/",
        views.BusinessHourDeleteView.as_view(),
        name="business_hour_delete_view",
    ),
    path(
        "business-hour-detail-view/<int:pk>/",
        views.BusinessHourDetailView.as_view(),
        name="business_hour_detail_view",
    ),
    # User urls
    path("user-view/", user_views.UserView.as_view(), name="user_view"),
    path("user-nav-view/", user_views.UserNavbar.as_view(), name="user_nav_view"),
    path("user-list-view/", user_views.UserListView.as_view(), name="user_list_view"),
    path(
        "user-kanban-view/",
        user_views.UserKanbanView.as_view(),
        name="user_kanban_view",
    ),
    path(
        "user-create-form/", user_views.UserFormView.as_view(), name="user_create_form"
    ),
    path(
        "user-edit-form/<int:pk>/",
        user_views.UserFormView.as_view(),
        name="user_edit_form",
    ),
    path(
        "user-delete-view/<int:pk>/",
        user_views.UserDeleteView.as_view(),
        name="user_delete_view",
    ),
    path(
        "user-detail-view/<int:pk>/",
        user_views.UserDetailView.as_view(),
        name="user_detail_view",
    ),
    path(
        "my-profile-view/",
        user_views.MyProfileView.as_view(),
        name="my_profile_view",
    ),
    path(
        "login-history-list/",
        user_views.LoginHistoryListView.as_view(),
        name="login_history_list",
    ),
    path(
        "login-history-navbar/",
        user_views.LoginHistoryNavbar.as_view(),
        name="login_history_navbar",
    ),
    path(
        "login-history-view/",
        user_views.LoginHistoryView.as_view(),
        name="login_history_view",
    ),
    path(
        "get-country-subdivisions/",
        views.GetCountrySubdivisionsView.as_view(),
        name="get_country_subdivisions",
    ),
    # role urls
    path("roles-view/", views.RolesView.as_view(), name="roles_view"),
    path("create-roles-view/", roles_views.AddRole.as_view(), name="create_roles_view"),
    path(
        "edit-roles-view/<int:pk>/",
        roles_views.AddRole.as_view(),
        name="edit_roles_view",
    ),
    path(
        "add-user-to-roles-view/",
        roles_views.AddUserToRole.as_view(),
        name="add_user_to_roles_view",
    ),
    path(
        "delete-user-from-role/<int:pk>/",
        roles_views.DeleteUserFromRole.as_view(),
        name="delete_user_from_role",
    ),
    path(
        "delete-role/<int:pk>/",
        roles_views.RoleDeleteView.as_view(),
        name="delete_role",
    ),
    path(
        "view-user-in-role/",
        roles_views.UsersInRoleView.as_view(),
        name="view_user_in_role",
    ),
    path(
        "view-user-in-role-list-view/",
        roles_views.RoleUsersListView.as_view(),
        name="view_user_in_role_list_view",
    ),
    path(
        "view-user-in-role-nav-view/",
        roles_views.RoleUsersNavView.as_view(),
        name="view_user_in_role_nav_view",
    ),
    # path('edit-roles-view/<int:pk>/',roles_views.AddRole.as_view(),name="edit_roles_view"),
    # branches urls
    path("branches-view/", branches_views.BranchesView.as_view(), name="branches_view"),
    path(
        "branches-nav-view/",
        branches_views.BranchNavbar.as_view(),
        name="branches_nav_view",
    ),
    path(
        "branches-list-view/",
        branches_views.BranchListView.as_view(),
        name="branches_list_view",
    ),
    path(
        "branch-detail-view/<int:pk>/",
        branches_views.BranchDetailView.as_view(),
        name="branch_detail_view",
    ),
    path(
        "branch-delete/<int:pk>/",
        branches_views.BranchDeleteView.as_view(),
        name="branch_delete",
    ),
    # Department urls
    path(
        "department-view/",
        department_views.DepartmentView.as_view(),
        name="department_view",
    ),
    path(
        "department-nav-view/",
        department_views.DepartmentNavbar.as_view(),
        name="department_nav_view",
    ),
    path(
        "department-list-view/",
        department_views.DepartmentListView.as_view(),
        name="department_list_view",
    ),
    path(
        "department-create-form/",
        department_views.DepartmentFormView.as_view(),
        name="department_create_form",
    ),
    path(
        "department-update-form/<int:pk>/",
        department_views.DepartmentFormView.as_view(),
        name="department_update_form",
    ),
    path(
        "department-delete-view/<int:pk>/",
        department_views.DepartmentDeleteView.as_view(),
        name="department_delete_view",
    ),
    # Team role urls
    path(
        "team-role-view/", team_role_views.TeamRoleView.as_view(), name="team_role_view"
    ),
    path(
        "team-role-nav-view/",
        team_role_views.TeamRoleNavbar.as_view(),
        name="team_role_nav_view",
    ),
    path(
        "team-role-list-view/",
        team_role_views.TeamRoleListView.as_view(),
        name="team_role_list_view",
    ),
    path(
        "team-role-create-form/",
        team_role_views.TeamRoleFormView.as_view(),
        name="team_role_create_form",
    ),
    path(
        "team-role-update-form/<int:pk>/",
        team_role_views.TeamRoleFormView.as_view(),
        name="team_role_update_form",
    ),
    path(
        "team-role-delete-view/<int:pk>/",
        team_role_views.TeamRoleDeleteView.as_view(),
        name="team_role_delete_view",
    ),
    # Customer role urls
    path(
        "customer-role-view/",
        customer_role_views.CustomerRoleView.as_view(),
        name="customer_role_view",
    ),
    path(
        "customer-role-nav-view/",
        customer_role_views.CustomerRoleNavbar.as_view(),
        name="customer_role_nav_view",
    ),
    path(
        "customer-role-list-view/",
        customer_role_views.CustomerRoleListView.as_view(),
        name="customer_role_list_view",
    ),
    path(
        "customer-role-create-form/",
        customer_role_views.CustomerRoleFormView.as_view(),
        name="customer_role_create_form",
    ),
    path(
        "customer-role-update-form/<int:pk>/",
        customer_role_views.CustomerRoleFormView.as_view(),
        name="customer_role_update_form",
    ),
    path(
        "customer-role-delete-view/<int:pk>/",
        customer_role_views.CustomerRoleDeleteView.as_view(),
        name="customer_role_delete_view",
    ),
    # Partner role urls
    path(
        "partner-role-view/",
        partner_role_views.PartnerRoleView.as_view(),
        name="partner_role_view",
    ),
    path(
        "partner-role-nav-view/",
        partner_role_views.PartnerRoleNavbar.as_view(),
        name="partner_role_nav_view",
    ),
    path(
        "partner-role-list-view/",
        partner_role_views.PartnerRoleListView.as_view(),
        name="partner_role_list_view",
    ),
    path(
        "partner-role-create-form/",
        partner_role_views.PartnerRoleFormView.as_view(),
        name="partner_role_create_form",
    ),
    path(
        "partner-role-update-form/<int:pk>/",
        partner_role_views.PartnerRoleFormView.as_view(),
        name="partner_role_update_form",
    ),
    path(
        "partner-role-delete-view/<int:pk>/",
        partner_role_views.PartnerRoleDeleteView.as_view(),
        name="partner_role_delete_view",
    ),
    # scoring rule urls
    path(
        "scoring-rule-view/",
        scoring_rule_views.ScoringRuleView.as_view(),
        name="scoring_rule_view",
    ),
    path(
        "scoring-rule-nav-view/",
        scoring_rule_views.ScoringRuleNavbar.as_view(),
        name="scoring_rule_nav_view",
    ),
    path(
        "scoring-rule-list-view/",
        scoring_rule_views.ScoringRuleListView.as_view(),
        name="scoring_rule_list_view",
    ),
    path(
        "scoring-rule-create-form/",
        scoring_rule_views.ScoringRuleFormView.as_view(),
        name="scoring_rule_create_form",
    ),
    path(
        "scoring-rule-update-form/<int:pk>/",
        scoring_rule_views.ScoringRuleFormView.as_view(),
        name="scoring_rule_update_form",
    ),
    path(
        "scoring-rule-delete-view/<int:pk>/",
        scoring_rule_views.ScoringRuleDeleteView.as_view(),
        name="scoring_rule_delete_view",
    ),
    path(
        "scoring-rule-detail-view/<int:pk>/",
        scoring_rule_views.ScoringRuleDetailView.as_view(),
        name="scoring_rule_detail_view",
    ),
    path(
        "scoring-rule-detail-nav-view/",
        scoring_rule_views.ScoringRuleDetailNavbar.as_view(),
        name="scoring_rule_detail_nav_view",
    ),
    path(
        "scoring-rule-criteria-create-form/",
        scoring_rule_views.ScoringCriterionCreateUpdateView.as_view(),
        name="scoring_rule_criteria_create_form",
    ),
    path(
        "scoring-rule-criteria-edit-form/<int:pk>/",
        scoring_rule_views.ScoringCriterionCreateUpdateView.as_view(),
        name="scoring_rule_criteria_edit_form",
    ),
    path(
        "scoring-rule-criteria-delete/<int:pk>/",
        scoring_rule_views.ScoringCriteriaDeleteView.as_view(),
        name="scoring_rule_criteria_delete",
    ),
    path(
        "scoring-rule-activate/<int:pk>/",
        scoring_rule_views.ScroringActiveToggleView.as_view(),
        name="scoring_rule_activate",
    ),
    # Recyclebin urls
    path(
        "recycle-bin-view/",
        recycle_bin_views.RecycleBinView.as_view(),
        name="recycle_bin_view",
    ),
    path(
        "recycle-bin-navbar/",
        recycle_bin_views.RecycleBinNavbar.as_view(),
        name="recycle_bin_navbar",
    ),
    path(
        "recycle-bin-list-view/",
        recycle_bin_views.RecycleBinListView.as_view(),
        name="recycle_bin_list_view",
    ),
    path(
        "recycle-bin-delete/<int:pk>/",
        recycle_bin_views.RecycleDeleteView.as_view(),
        name="recycle_bin_delete",
    ),
    path(
        "recycle-bin-restore/<int:pk>/",
        recycle_bin_views.RecycleRestoreView.as_view(),
        name="recycle_bin_restore",
    ),
    path(
        "recycle-bin-empty/",
        recycle_bin_views.EmptyRecycleBinView.as_view(),
        name="recycle_bin_empty",
    ),
    path(
        "bulk-recycle-bin-restore/",
        recycle_bin_views.BulkRestoreRecycleView.as_view(),
        name="bulk_recycle_bin_restore",
    ),
    path(
        "bulk-recycle-bin-delete/",
        recycle_bin_views.BulkDeleteRecycleBinView.as_view(),
        name="bulk_recycle_bin_delete",
    ),
    path(
        "recycle-bin-policy-view/",
        recycle_bin_views.BinPolicyView.as_view(),
        name="recycle_bin_policy_view",
    ),
    # my settings holidays urls
    path(
        "user-holiday-view/",
        user_holidays_views.UserHolidayView.as_view(),
        name="user_holiday_view",
    ),
    path(
        "user-holiday-nav/",
        user_holidays_views.UserHolidayNavbar.as_view(),
        name="user_holiday_nav",
    ),
    path(
        "user-holiday-list/",
        user_holidays_views.UserHolidayListView.as_view(),
        name="user_holiday_list",
    ),
    path(
        "user-holiday-detail/<int:pk>/",
        user_holidays_views.UserHolidayDetailView.as_view(),
        name="user_holiday_detail",
    ),
    # my settings user login history urls
    path(
        "user-login-history-view/",
        user_login_history_views.UserLoginHistoryView.as_view(),
        name="user_login_history_view",
    ),
    path(
        "user-login-history-nav/",
        user_login_history_views.UserLoginHistoryNavbar.as_view(),
        name="user_login_history_nav",
    ),
    path(
        "user-login-history-list/",
        user_login_history_views.UserloginHistoryListView.as_view(),
        name="user_login_history_list",
    ),
    # Regional Formating urls
    path(
        "regional-formating-view/",
        regional_formating_views.ReginalFormatingView.as_view(),
        name="regional_formating_view",
    ),
    path("reload-messages/", views.ReloadMessages.as_view(), name="reload_messages"),
    path("import-view/", import_data.ImportView.as_view(), name="import_view"),
    path(
        "import-tab-view/", import_data.ImportTabView.as_view(), name="import_tab_view"
    ),
    path("import-data/", import_data.ImportDataView.as_view(), name="import_data"),
    path("step1/", import_data.ImportStep1View.as_view(), name="import_step1"),
    path("step2/", import_data.ImportStep2View.as_view(), name="import_step2"),
    path("step3/", import_data.ImportStep3View.as_view(), name="import_step3"),
    path("step4/", import_data.ImportStep4View.as_view(), name="import_step4"),
    path(
        "get-fields/", import_data.GetModelFieldsView.as_view(), name="get_model_fields"
    ),
    path(
        "get-unique-values/",
        import_data.GetUniqueValuesView.as_view(),
        name="get_unique_values",
    ),
    path(
        "update-field-status/",
        import_data.UpdateFieldStatusView.as_view(),
        name="update_field_status",
    ),
    path(
        "update-value-mapping-status/",
        import_data.UpdateValueMappingStatusView.as_view(),
        name="update_value_mapping_status",
    ),
    path(
        "download-errors/",
        import_data.DownloadErrorFileView.as_view(),
        name="download_error_file",
    ),
    path(
        "download-imported-file/",
        import_data.DownloadImportedFileView.as_view(),
        name="download_imported_file",
    ),
    path(
        "import-history-view/",
        import_data.ImportHistoryView.as_view(),
        name="import_history_view",
    ),
    # Permission urls
    path(
        "group-permission-view/",
        permission_views.GroupPermissionView.as_view(),
        name="group_permission_view",
    ),
    path(
        "group-permission-tab/",
        permission_views.GroupPermissionTabView.as_view(),
        name="group_permission_tab",
    ),
    path("group-tab/", permission_views.GroupTab.as_view(), name="group_tab"),
    path(
        "permission-tab/",
        permission_views.PermissionTab.as_view(),
        name="permission_tab",
    ),
    path(
        "roles-permissions/<int:role_id>/",
        permission_views.RolePermissionsView.as_view(),
        name="role_permissions_view",
    ),
    path(
        "groups-role-members/<int:role_id>/",
        permission_views.RoleMembersView.as_view(),
        name="role_members_view",
    ),
    path(
        "roles-update-permissions/<int:role_id>/",
        permission_views.UpdateRolePermissionsView.as_view(),
        name="update_role_permissions",
    ),
    path(
        "load-more-users/",
        permission_views.LoadMoreUsersView.as_view(),
        name="load_more_users",
    ),
    path(
        "load-user-permissions/<int:user_id>/",
        permission_views.LoadUserPermissionsView.as_view(),
        name="load_user_permissions",
    ),
    path(
        "assign-users-perm/",
        permission_views.AssignUsersView.as_view(),
        name="assign_users_perm",
    ),
    path(
        "update-user-permissions/<int:user_id>/",
        permission_views.UpdateUserPermissionsView.as_view(),
        name="update_user_permissions",
    ),
    path(
        "update-role-model-permissions/<int:role_id>/",
        permission_views.UpdateRoleModelPermissionsView.as_view(),
        name="update_role_model_permissions",
    ),
    path(
        "role-permissions-all/<int:role_id>/",
        permission_views.UpdateRoleAllPermissionsView.as_view(),
        name="update_role_all_permissions",
    ),
    path(
        "user-update-model-permissions/<int:user_id>/",
        permission_views.UpdateUserModelPermissionsView.as_view(),
        name="update_user_model_permissions",
    ),
    path(
        "user-update-all-permissions/<int:user_id>/",
        permission_views.UpdateUserAllPermissionsView.as_view(),
        name="update_user_all_permissions",
    ),
    path(
        "bulk-update-user-model-permissions/",
        permission_views.BulkUpdateUserModelPermissionsView.as_view(),
        name="bulk_update_user_model_permissions",
    ),
    path(
        "bulk-update-user-all-permissions/",
        permission_views.BulkUpdateUserAllPermissionsView.as_view(),
        name="bulk_update_user_all_permissions",
    ),
    path(
        "super-user-tab/",
        permission_views.SuperUserTab.as_view(),
        name="super_user_tab",
    ),
    path(
        "super-user-status/<int:pk>/",
        permission_views.ToggleSuperuserView.as_view(),
        name="super_user_status",
    ),
    path(
        "search-role-models/<int:role_id>/",
        permission_views.SearchRoleModelsView.as_view(),
        name="search_role_models",
    ),
    path(
        "search-user-models/<int:user_id>/",
        permission_views.SearchUserModelsView.as_view(),
        name="search_user_models",
    ),
    path(
        "search-assign-models/",
        permission_views.SearchAssignModelsView.as_view(),
        name="search_assign_models",
    ),
    path(
        "initialize-database/",
        initialiaze_database.InitializeDatabase.as_view(),
        name="initialize_database",
    ),
    path(
        "initialize-database-user/",
        initialiaze_database.InitializeDatabaseUser.as_view(),
        name="initialize_database_user",
    ),
    path(
        "initialize-database-role/",
        initialiaze_database.InitializeRoleView.as_view(),
        name="initialize_database_role",
    ),
    path(
        "initialize-database-company/",
        initialiaze_database.InitializeDatabaseCompany.as_view(),
        name="initialize_database_company",
    ),
    path(
        "sign-up-user/",
        initialiaze_database.SignUpFormView.as_view(),
        name="sign_up_user",
    ),
    path(
        "initialize-company-form/",
        initialiaze_database.InitializeCompanyFormView.as_view(),
        name="initialize_company_form",
    ),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path(
        "reset-password/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "change-password-view/",
        ChangePasswordView.as_view(),
        name="change_password_view",
    ),
    path(
        "change-password-form/",
        ChangePasswordFormView.as_view(),
        name="change_password_form",
    ),
    # Load Data
    path("load-data/", load_data.LoadDatabase.as_view(), name="load_data"),
    path(
        "load-demo-data/", load_data.LoadDemoDatabase.as_view(), name="load_demo_data"
    ),
    path(
        "configure-demo-data/",
        load_data.ConfigureDemoData.as_view(),
        name="configure_demo_data",
    ),
    # Export
    path("export-view/", export_data_views.ExportView.as_view(), name="export_view"),
    path(
        "schedule-modal/",
        export_data_views.ExportScheduleModalView.as_view(),
        name="schedule_modal",
    ),
    path(
        "schedule-create/",
        export_data_views.ExportScheduleCreateView.as_view(),
        name="schedule_create",
    ),
    path(
        "schedule-export-list/",
        export_data_views.ScheduleExportListView.as_view(),
        name="schedule_export_list",
    ),
    path(
        "schedule-export-delete/<int:pk>/",
        export_data_views.ScheduleExportDeleteView.as_view(),
        name="schedule_export_delete",
    ),
]
