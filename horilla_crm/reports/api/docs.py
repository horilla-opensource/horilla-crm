"""
Documentation for horilla_crm.reports API endpoints
"""

# Report Folder API documentation
REPORT_FOLDER_LIST_DOCS = """
List all report folders with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?is_favourite=true)
- Sort results using the 'ordering' parameter (if configured globally)
"""

REPORT_FOLDER_DETAIL_DOCS = """
Retrieve, update or delete a report folder instance.
"""

REPORT_FOLDER_CREATE_DOCS = """
Create a new report folder with the provided data.
"""


# Report API documentation
REPORT_LIST_DOCS = """
List all reports with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters
- Sort results using the 'ordering' parameter (if configured globally)
"""

REPORT_DETAIL_DOCS = """
Retrieve, update or delete a report instance.
"""

REPORT_CREATE_DOCS = """
Create a new report with the provided data.
"""
