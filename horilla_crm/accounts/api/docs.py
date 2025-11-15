"""
Documentation for horilla_crm.accounts API endpoints
"""

# Account API documentation
ACCOUNT_LIST_DOCS = """
List all accounts with optional filtering and search capabilities.

You can:
- Search across multiple fields using the 'search' parameter
- Filter by specific fields using query parameters (e.g., ?account_type=customer_direct)
- Sort results using the 'ordering' parameter
"""

ACCOUNT_DETAIL_DOCS = """
Retrieve, update or delete an account instance.
"""

ACCOUNT_CREATE_DOCS = """
Create a new account with the provided data.
"""

ACCOUNT_PARTNER_ACCOUNTS_DOCS = """
List all accounts that are marked as partners.
"""

ACCOUNT_CHILD_ACCOUNTS_DOCS = """
List all child accounts for a specific parent account.
"""

# Partner Account Relationship API documentation
PARTNER_RELATIONSHIP_LIST_DOCS = """
List all partner account relationships with optional filtering and search capabilities.
"""

PARTNER_RELATIONSHIP_DETAIL_DOCS = """
Retrieve, update or delete a partner account relationship instance.
"""

PARTNER_RELATIONSHIP_CREATE_DOCS = """
Create a new partner account relationship with the provided data.
"""

PARTNER_RELATIONSHIP_BY_ACCOUNT_DOCS = """
List all partner relationships for a specific account.
"""

PARTNER_RELATIONSHIP_BY_PARTNER_DOCS = """
List all partner relationships where the specified account is the partner.
"""
