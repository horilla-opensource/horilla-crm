"""
Documentation for horilla_crm.activity API endpoints
"""

# Activity API documentation
ACTIVITY_LIST_DOCS = """
List all activities with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?activity_type=meeting)
- Sort results using the 'ordering' parameter
"""

ACTIVITY_DETAIL_DOCS = """
Retrieve, update or delete an activity instance.
"""

ACTIVITY_CREATE_DOCS = """
Create a new activity with the provided data.
"""

ACTIVITY_BY_RELATED_DOCS = """
List all activities related to a specific object via content type and object id.

Provide either 'content_type_id' or 'content_type' (app_label.model) along with 'object_id'.
"""

ACTIVITY_BY_OWNER_DOCS = """
List activities filtered by owner user ID.
"""

ACTIVITY_BY_ASSIGNED_DOCS = """
List activities where the given user ID is in assigned_to.
"""

ACTIVITY_BY_PARTICIPANT_DOCS = """
List activities where the given user ID is in participants.
"""

ACTIVITY_BY_TYPE_DOCS = """
List activities filtered by activity type (event, meeting, task, log_call).
"""

ACTIVITY_COMPLETED_DOCS = """
List activities marked as completed.
"""

ACTIVITY_PENDING_DOCS = """
List activities marked as pending.
"""

ACTIVITY_UPCOMING_DOCS = """
List upcoming activities based on start or due date.
"""
