from horilla.menu import floating_menu, main_section_menu, sub_section_menu
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

@main_section_menu.register
class AskAISection:
    section = "ai"
    name = _("Ask AI")
    icon = "assets/icons/chat.svg"
    position = 10

    def is_enabled(self, request=None):
        if request and request.user and request.user.is_authenticated:
            return getattr(request.user, "enable_ai", False)
        return False

@sub_section_menu.register
class AskAISubSection:
    section = "ai"
    verbose_name = _("Ask AI")
    icon = "assets/icons/chat.svg"
    url = reverse_lazy("horilla_ai:ask_ai")
    app_label = "ai"
    position = 1
    attrs = {
        "hx-boost": "true",
        "hx-target": "#mainContent",
        "hx-select": "#mainContent",
        "hx-swap": "outerHTML",
    }

    def is_enabled(self, request=None):
        if request and request.user and request.user.is_authenticated:
            return getattr(request.user, "enable_ai", False)
        return False

@floating_menu.register
class AskAIFloating:
    title = _("Ask AI")
    url = reverse_lazy("horilla_ai:ask_ai")
    icon = "assets/icons/chat.svg"
    
    def is_enabled(self, request=None):
        if request and request.user and request.user.is_authenticated:
            return getattr(request.user, "enable_ai", False)
        return False
