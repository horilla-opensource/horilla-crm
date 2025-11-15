# horilla_core/registry.py

from collections import defaultdict

FEATURE_REGISTRY = defaultdict(list)


def feature_enabled(
    *,
    all=False,
    import_data=False,
    export_data=False,
    mail_template=False,
    global_search=False,
    dashboard_component=False,
    exclude=None,
):
    """
    Decorator to register models for specific features.
    Automatically adds models to global FEATURE_REGISTRY groups.
    """

    def decorator(model_class):
        nonlocal import_data, export_data, mail_template, global_search, dashboard_component, exclude

        if exclude is None:
            exclude = []

        if all:
            import_data = "import_data" not in exclude
            export_data = "export_data" not in exclude
            mail_template = "mail_template" not in exclude
            global_search = "global_search" not in exclude
            dashboard_component = "dashboard_component" not in exclude

        if import_data and model_class not in FEATURE_REGISTRY["import_models"]:
            FEATURE_REGISTRY["import_models"].append(model_class)

        if export_data and model_class not in FEATURE_REGISTRY["export_models"]:
            FEATURE_REGISTRY["export_models"].append(model_class)

        if (
            mail_template
            and model_class not in FEATURE_REGISTRY["mail_template_models"]
        ):
            FEATURE_REGISTRY["mail_template_models"].append(model_class)

        if (
            global_search
            and model_class not in FEATURE_REGISTRY["global_search_models"]
        ):
            FEATURE_REGISTRY["global_search_models"].append(model_class)

        if (
            dashboard_component
            and model_class not in FEATURE_REGISTRY["dashboard_component_models"]
        ):
            FEATURE_REGISTRY["dashboard_component_models"].append(model_class)

        return model_class

    return decorator
