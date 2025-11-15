import threading

_thread_local = threading.local()


class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the request in thread local storageE
        _thread_local.request = request

        # Process the request
        response = self.get_response(request)

        # Clean up after the request is processed
        if hasattr(_thread_local, "request"):
            del _thread_local.request

        return response


# Helper function to get the current request
def get_current_request():
    return getattr(_thread_local, "request", None)


from django.conf import settings

# middleware.py
from django.utils import translation


class LanguageSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Priority order:
        # 1. Session language (when user actively changes language)
        # 2. User's preferred language (from profile)
        # 3. Default language from settings

        lang = None

        # First check if there's a session language (user actively selected)
        session_lang = request.session.get("django_language")

        if session_lang:
            # User has actively selected a language, use it
            lang = session_lang
        elif request.user.is_authenticated:
            # No session language, check user's profile preference
            user_lang = getattr(request.user, "language", None)
            if user_lang:
                lang = user_lang
                # Save user's preference to session for consistency
                request.session["django_language"] = lang

        # If no language found, fall back to settings default
        if not lang:
            lang = settings.LANGUAGE_CODE

        # Activate the language
        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        response = self.get_response(request)
        return response
