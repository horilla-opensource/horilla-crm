# horilla/api_urls.py
import logging

from django.apps import apps
from django.conf import settings
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

logger = logging.getLogger(__name__)


def collect_api_paths():
    """
    Dynamically collect API paths from all installed apps.

    This function scans all installed Django apps for a get_api_paths() method
    in their AppConfig class and collects the returned path patterns.

    Returns:
        list: A list of Django URL path objects for API endpoints

    Raises:
        Exception: Logs errors for apps with invalid path definitions
    """
    api_paths = []
    path_registry = {}  # Track paths to detect conflicts

    for app_config in apps.get_app_configs():
        try:
            # Check if the app has a get_api_paths method
            if hasattr(app_config, "get_api_paths"):
                app_paths = app_config.get_api_paths()

                if not isinstance(app_paths, list):
                    logger.error(
                        f"App {app_config.name}: get_api_paths() must return a list"
                    )
                    continue

                for path_info in app_paths:
                    if not isinstance(path_info, dict):
                        logger.error(
                            f"App {app_config.name}: Each path must be a dictionary"
                        )
                        continue

                    required_keys = {"pattern", "view_or_include"}
                    if not required_keys.issubset(path_info.keys()):
                        logger.error(
                            f"App {app_config.name}: Path missing required keys: {required_keys}"
                        )
                        continue

                    pattern = path_info["pattern"]
                    view_or_include = path_info["view_or_include"]
                    name = path_info.get("name")
                    namespace = path_info.get("namespace", app_config.name)

                    # Normalize pattern to ensure single trailing slash
                    if not isinstance(pattern, str):
                        logger.error(
                            f"App {app_config.name}: 'pattern' must be a string"
                        )
                        continue

                    normalized = pattern.strip("/") + "/"

                    # Check for path conflicts (relative to api/ mountpoint)
                    full_pattern = normalized
                    if full_pattern in path_registry:
                        logger.warning(
                            f"Path conflict detected: 'api/{full_pattern}' defined in both "
                            f"{path_registry[full_pattern]} and {app_config.name}"
                        )
                        continue

                    path_registry[full_pattern] = app_config.name

                    # Create the path object (mounted under /api/ via project urls)
                    if isinstance(view_or_include, str):
                        # It's an include string
                        api_path = path(
                            full_pattern, include(view_or_include), name=name
                        )
                    else:
                        # It's a view function/class
                        api_path = path(full_pattern, view_or_include, name=name)

                    api_paths.append(api_path)
                    logger.debug(
                        f"Registered API path: api/{full_pattern} from {app_config.name}"
                    )

        except Exception as e:
            logger.error(f"Error collecting API paths from {app_config.name}: {e}")
            continue

    logger.info(f"Collected {len(api_paths)} API paths from {len(path_registry)} apps")
    return api_paths


def get_dynamic_api_patterns():
    """
    Get dynamically collected API patterns for schema generation.

    Returns:
        list: List of URL patterns for API documentation
    """
    try:
        return collect_api_paths()
    except Exception as e:
        logger.error(f"Failed to collect dynamic API patterns: {e}")
        # Fallback to empty list to prevent schema generation failure
        return []


# Custom generator to force Swagger base path to '/api/' regardless of host/port
class ApiPrefixSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        # Ensure examples and "Request URL" use '/api/' as base path
        schema.base_path = "/api/"
        return schema


# Schema view for API documentation with dynamic pattern collection
# Get server URL from request in view instead of hardcoding
schema_view = get_schema_view(
    openapi.Info(
        title="HORILLA CRM API",
        default_version="v1",
        description="API documentation for HORILLA CRM system",
        terms_of_service="https://www.horilla.com/terms/",
        contact=openapi.Contact(email="contact@horilla.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    generator_class=ApiPrefixSchemaGenerator,
    patterns=get_dynamic_api_patterns(),
)


urlpatterns = [
    # API documentation with Swagger/OpenAPI
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
] + collect_api_paths()  # Add dynamically collected API paths
