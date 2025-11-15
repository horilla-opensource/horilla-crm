from django.utils.html import format_html
from django.utils.timezone import localtime
from login_history.models import LoginHistory


def user_status(self):
    if self.is_logged_in == True:
        return "Login"
    else:
        return "Logout"


def short_user_agent(self):
    """
    Returns only the first part of the user agent (up to the first closing parenthesis).
    """
    if self.user_agent:
        end = self.user_agent.find(")") + 1  # Find first closing bracket
        if end > 0:
            return self.user_agent[:end]
    return self.user_agent


def formatted_datetime(self):
    local_dt = localtime(self.date_time)
    return (
        local_dt.strftime("%d %b %Y, %I:%M %p")
        .lower()
        .replace("am", "a.m.")
        .replace("pm", "p.m.")
    )


def is_login_icon(self):
    if self.is_logged_in:
        # Green check icon
        return format_html(
            '<span class="flex justify-center items-center inline-block text-green-600"><i class="fas fa-check-circle fa-lg"></i></span>'
        )
    else:
        # Red cross icon
        return format_html(
            '<span class=" flex justify-center items-center inline-block text-red-600"><i class="fas fa-times-circle fa-lg"></i></span>'
        )


LoginHistory.user_status = user_status
LoginHistory.short_user_agent = short_user_agent
LoginHistory.formatted_datetime = formatted_datetime
LoginHistory.is_login_icon = is_login_icon
