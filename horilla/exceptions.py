"""Custom exception classes for the Horilla application."""

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


class HorillaHttp404(Exception):
    """Custom 404 exception that renders a Horilla-specific error template."""

    def __init__(
        self,
        message=_(
            "The page you are looking for does not exist or may have been moved."
        ),
        context=None,
        template="error/404.html",
    ):
        """
        Initialize the HorillaHttp404 exception.

        Args:
            message (str): The error message to display.
            context (dict, optional): Additional context variables for the template.
            template (str, optional): Path to the error template.
        """
        self.message = message
        self.context = context or {}
        self.template = template
        super().__init__(message)

    def as_response(self, request):
        """
        Render the exception as an HTTP 404 response.

        Args:
            request (HttpRequest): The request that triggered the exception.

        Returns:
            HttpResponse: A rendered 404 response.
        """
        html = render_to_string(
            self.template,
            {**self.context, "error_message": self.message},
            request=request,
        )
        return HttpResponse(html, status=404)
