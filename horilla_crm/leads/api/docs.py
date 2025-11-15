"""
Documentation for horilla_crm.leads API endpoints
"""

# Lead API documentation
LEAD_LIST_DOCS = """
List all leads with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?lead_source=website)
- Sort results using the 'ordering' parameter
"""

LEAD_DETAIL_DOCS = """
Retrieve, update or delete a lead instance.
"""

LEAD_CREATE_DOCS = """
Create a new lead with the provided data.
"""

LEAD_BY_STATUS_DOCS = """
List all leads filtered by a specific lead status.
"""

LEAD_BY_OWNER_DOCS = """
List all leads filtered by a specific lead owner.
"""

LEAD_BY_SOURCE_DOCS = """
List all leads filtered by a specific lead source.
"""

LEAD_CONVERT_DOCS = """
Convert a lead to account, contact, and opportunity.
"""

LEAD_HIGH_SCORE_DOCS = """
List leads with high lead scores (above specified threshold).
"""

# Lead Status API documentation
LEAD_STATUS_LIST_DOCS = """
List all lead statuses with optional filtering and search capabilities.
"""

LEAD_STATUS_DETAIL_DOCS = """
Retrieve, update or delete a lead status instance.
"""

LEAD_STATUS_CREATE_DOCS = """
Create a new lead status with the provided data.
"""

LEAD_STATUS_FINAL_STAGES_DOCS = """
List all lead statuses that are marked as final stages.
"""

LEAD_STATUS_REORDER_DOCS = """
Reorder lead statuses by updating their order values.
"""
