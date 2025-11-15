from django.urls import path

from horilla_generics import horilla_support_views as view
from horilla_generics.global_search import GlobalSearchView

from . import views

app_name = "horilla_generics"

urlpatterns = [
    path(
        "update-kanban-item/<str:app_label>/<str:model_name>/",
        views.HorillaKanbanView.as_view(),
        name="update_kanban_item",
    ),
    path(
        "update-kanban-column-order/<str:app_label>/<str:model_name>/",
        views.HorillaKanbanView.as_view(),
        name="update_kanban_column_order",
    ),
    path(
        "kanban-load-more/<str:app_label>/<str:model_name>/",
        view.KanbanLoadMoreView.as_view(),
        name="kanban_load_more",
    ),
    path(
        "create-kanban-group/",
        view.HorillaKanbanGroupByView.as_view(),
        name="create_kanban_group",
    ),
    path(
        "column-selector/",
        view.ListColumnSelectFormView.as_view(),
        name="column_selector",
    ),
    path("move-field/", view.MoveFieldView.as_view(), name="move_field"),
    path(
        "save-filter-list/", view.SaveFilterListView.as_view(), name="save_filter_list"
    ),
    path("pin-view/", view.PinView.as_view(), name="pin_view"),
    path(
        "delete-saved-list/",
        view.DeleteSavedListView.as_view(),
        name="delete_saved_list",
    ),
    path(
        "update-pipeline/<int:pk>/",
        views.HorillaDetailView.as_view(),
        name="update_pipeline",
    ),
    path(
        "edit/<int:pk>/<str:field_name>/<str:app_label>/<str:model_name>/",
        view.EditFieldView.as_view(),
        name="edit_field",
    ),
    path(
        "cancel/<int:pk>/<str:field_name>/<str:app_label>/<str:model_name>/",
        view.CancelEditView.as_view(),
        name="cancel_edit",
    ),
    path(
        "update/<int:pk>/<str:field_name>/<str:app_label>/<str:model_name>/",
        view.UpdateFieldView.as_view(),
        name="update_field",
    ),
    path(
        "dynamic-create/<str:app_label>/<str:model_name>/",
        views.HorillaDynamicCreateView.as_view(),
        name="dynamic_create",
    ),
    path(
        "related-list-content/<int:pk>/",
        views.HorillaRelatedListContentView.as_view(),
        name="related_list_content",
    ),
    path(
        "<str:app_label>/<str:model_name>/select2/",
        view.HorillaSelect2DataView.as_view(),
        name="model_select2",
    ),
    path("search/", GlobalSearchView.as_view(), name="global_search"),
    path(
        "remove-condition-row/<str:row_id>/",
        view.RemoveConditionRowView.as_view(),
        name="remove_condition_row",
    ),
    path(
        "get-field-value-widget/",
        view.GetFieldValueWidgetView.as_view(),
        name="get_field_value_widget",
    ),
    path(
        "notes-attachment-create/",
        views.HorillaNotesAttachmentCreateView.as_view(),
        name="notes_attachment_create",
    ),
    path(
        "notes-attachment-edit/<int:pk>/",
        views.HorillaNotesAttachmentCreateView.as_view(),
        name="notes_attachment_edit",
    ),
    path(
        "notes-attachment-view/<int:pk>/",
        views.HorillaNotesAttachementDetailView.as_view(),
        name="notes_attachment_view",
    ),
    path(
        "notes-attachment-delete/<int:pk>/",
        views.HorillaNotesAttachmentDeleteView.as_view(),
        name="notes_attachment_delete",
    ),
]
