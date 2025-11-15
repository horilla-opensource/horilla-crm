"""
Documentation for horilla_crm.timeline API endpoints
"""

# User Calendar Preference API documentation
USER_CALENDAR_PREFERENCE_LIST_DOCS = """
List all user calendar preferences with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?calendar_type=event)
- Sort results using the 'ordering' parameter
"""

USER_CALENDAR_PREFERENCE_DETAIL_DOCS = """
Retrieve, update or delete a user calendar preference instance.
"""

USER_CALENDAR_PREFERENCE_CREATE_DOCS = """
Create a new user calendar preference with the provided data.
"""


# User Availability API documentation
USER_AVAILABILITY_LIST_DOCS = """
List all user availability records with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?user=<id>)
- Sort results using the 'ordering' parameter
"""

USER_AVAILABILITY_DETAIL_DOCS = """
Retrieve, update or delete a user availability instance.
"""

USER_AVAILABILITY_CREATE_DOCS = """
Create a new user availability with the provided data.
"""

USER_AVAILABILITY_CURRENT_DOCS = """
List current unavailability periods for a given user.
"""
