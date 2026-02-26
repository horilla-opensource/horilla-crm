from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class HorillaAiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_ai"
    verbose_name = _("AI Assistant")

    def get_api_paths(self):
        return [
            {
                "pattern": "ai/",
                "view_or_include": "horilla_ai.urls",
                "name": "horilla_ai_api",
                "namespace": "horilla_ai_api",
            }
        ]

    def ready(self):
        try:
            from django.urls import include, path
            from horilla.urls import urlpatterns
            
            if not any(getattr(p, "namespace", None) == "horilla_ai" for p in urlpatterns):
                urlpatterns.append(
                    path("ai/", include("horilla_ai.urls", namespace="horilla_ai"))
                )
            
            __import__("horilla_ai.menu")
        except Exception as e:
            import logging
            logging.warning("HorillaAiConfig.ready failed: %s", e)
        super().ready()
