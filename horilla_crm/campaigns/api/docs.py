"""
Documentation for horilla_crm.campaigns API endpoints
"""

# Campaign API documentation
CAMPAIGN_LIST_DOCS = """
List all campaigns with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?status=planned)
- Sort results using the 'ordering' parameter (if configured globally)
"""

CAMPAIGN_DETAIL_DOCS = """
Retrieve, update or delete a campaign instance.
"""

CAMPAIGN_CREATE_DOCS = """
Create a new campaign with the provided data.
"""

CAMPAIGN_CHILD_CAMPAIGNS_DOCS = """
List all child campaigns for a specific parent campaign.
"""
