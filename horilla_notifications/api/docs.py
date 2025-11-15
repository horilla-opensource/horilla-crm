"""
Documentation for horilla_notifications API
"""

# API endpoint documentation with examples
NOTIFICATION_API_DOCS = {
    "list": {
        "description": "List all notifications for the current user with pagination, filtering, and search capabilities.",
        "example_request": "GET /notifications/notifications/",
        "example_response": {
            "count": 2,
            "next": "http://example.com/api/notifications/?page=2",
            "previous": None,
            "results": [
                {
                    "id": 1,
                    "user": 1,
                    "user_details": {
                        "id": 1,
                        "username": "john.doe",
                        "email": "john.doe@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                    },
                    "message": "You have a new task assigned",
                    "sender": 2,
                    "sender_details": {
                        "id": 2,
                        "username": "jane.smith",
                        "email": "jane.smith@example.com",
                        "first_name": "Jane",
                        "last_name": "Smith",
                    },
                    "url": "/tasks/123/",
                    "created_at": "2023-06-15T10:30:00Z",
                    "read": False,
                }
            ],
        },
    },
    "create": {
        "description": "Create a new notification.",
        "example_request": {
            "method": "POST",
            "url": "/notifications/notifications/",
            "body": {
                "user": 1,
                "message": "New notification message",
                "sender": 2,
                "url": "/some/path/",
            },
        },
        "example_response": {
            "id": 3,
            "user": 1,
            "message": "New notification message",
            "sender": 2,
            "url": "/some/path/",
            "created_at": "2023-06-15T14:45:00Z",
            "read": False,
        },
    },
    "retrieve": {
        "description": "Retrieve a specific notification by ID.",
        "example_request": "GET /notifications/notifications/1/",
        "example_response": {
            "id": 1,
            "user": 1,
            "user_details": {
                "id": 1,
                "username": "john.doe",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
            },
            "message": "You have a new task assigned",
            "sender": 2,
            "sender_details": {
                "id": 2,
                "username": "jane.smith",
                "email": "jane.smith@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
            },
            "url": "/tasks/123/",
            "created_at": "2023-06-15T10:30:00Z",
            "read": False,
        },
    },
    "update": {
        "description": "Update a notification (partial update supported).",
        "example_request": {
            "method": "PATCH",
            "url": "/notifications/notifications/1/",
            "body": {"read": True},
        },
        "example_response": {
            "id": 1,
            "user": 1,
            "message": "You have a new task assigned",
            "sender": 2,
            "url": "/tasks/123/",
            "created_at": "2023-06-15T10:30:00Z",
            "read": True,
        },
    },
    "delete": {
        "description": "Delete a notification.",
        "example_request": "DELETE /notifications/notifications/1/",
        "example_response": "HTTP 204 No Content",
    },
    "mark_as_read": {
        "description": "Mark a specific notification as read.",
        "example_request": "POST /notifications/notifications/1/mark_as_read/",
        "example_response": {
            "status": "success",
            "message": "Notification marked as read",
        },
    },
    "mark_all_as_read": {
        "description": "Mark all notifications as read for the current user.",
        "example_request": "POST /notifications/notifications/mark_all_as_read/",
        "example_response": {
            "status": "success",
            "message": "All notifications marked as read",
        },
    },
    "unread_count": {
        "description": "Get count of unread notifications for the current user.",
        "example_request": "GET /notifications/notifications/unread_count/",
        "example_response": {"count": 5},
    },
    "bulk_update": {
        "description": "Update multiple notifications in a single request.",
        "example_request": {
            "method": "POST",
            "url": "/notifications/notifications/bulk_update/",
            "body": {"ids": [1, 2, 3], "data": {"read": True}},
        },
        "example_response": {
            "status": "success",
            "updated_count": 3,
            "message": "3 notifications updated successfully",
        },
    },
    "bulk_delete": {
        "description": "Delete multiple notifications in a single request.",
        "example_request": {
            "method": "POST",
            "url": "/notifications/notifications/bulk_delete/",
            "body": {"ids": [1, 2, 3]},
        },
        "example_response": {
            "status": "success",
            "deleted_count": 3,
            "message": "3 notifications deleted successfully",
        },
    },
}
