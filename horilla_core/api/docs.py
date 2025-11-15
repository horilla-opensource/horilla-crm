"""
Documentation for the enhanced API features
"""

# Search and Filter Documentation
SEARCH_FILTER_DOCS = """
## Search and Filtering

### Search
You can search across multiple fields using the `search` query parameter:

```
GET /api/core/companies/?search=example
```

This will search for "example" in all searchable fields (name, description, email, etc.)

### Filtering
Filter records by specific fields using query parameters:

```
GET /api/core/companies/?name=Example&is_active=true
```

This will return companies with name "Example" that are active.
"""

# Bulk Update Documentation
BULK_UPDATE_DOCS = """
## Bulk Update

Update multiple records at once by sending a POST request to the bulk_update endpoint:

### Update by IDs
```
POST /api/core/companies/bulk_update/
{
    "ids": [1, 2, 3],
    "data": {
        "is_active": true,
        "description": "Updated description"
    }
}
```

This will update the is_active and description fields for companies with IDs 1, 2, and 3.

### Update by Filters
```
POST /api/core/companies/bulk_update/
{
    "filters": {
        "is_active": true,
        "name__contains": "Corp"
    },
    "data": {
        "description": "Updated all active corporations"
    }
}
```

This will update all active companies with "Corp" in their name.

### Combined Approach
```
POST /api/core/companies/bulk_update/
{
    "ids": [1, 2, 3],
    "filters": {
        "is_active": true
    },
    "data": {
        "description": "Updated selected active companies"
    }
}
```

This will update only active companies from the specified IDs.
"""

# Bulk Delete Documentation
BULK_DELETE_DOCS = """
## Bulk Delete

Delete multiple records at once:

### Delete by IDs
```
POST /api/core/companies/bulk_delete/
{
    "ids": [1, 2, 3]
}
```

### Delete by Filters
```
POST /api/core/companies/bulk_delete/
{
    "filters": {
        "is_active": false,
        "created_at__lt": "2023-01-01"
    }
}
```

This will delete all inactive companies created before 2023.

### Combined Approach
```
POST /api/core/companies/bulk_delete/
{
    "ids": [1, 2, 3],
    "filters": {
        "is_active": false
    }
}
```

This will delete only inactive companies from the specified IDs.

Delete multiple records at once by sending a POST request to the bulk_delete endpoint:

```
POST /api/core/companies/bulk_delete/
{
    "ids": [1, 2, 3]
}
```

This will delete companies with IDs 1, 2, and 3.
"""
