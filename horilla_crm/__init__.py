"""
Horilla CRM Module Initialization.

This module customizes Horilla's default behavior at import time.

Purpose:
    Override the default home redirection after login to redirect users to
    the CRM dashboard instead of the standard profile page.
"""

from horilla import settings

settings.DEFAULT_HOME_REDIRECT = "/dashboards/?section=home"
