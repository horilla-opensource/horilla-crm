"""
Tests for horilla_notifications API
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from horilla_core.models import HorillaUser
from horilla_notifications.models import Notification


class NotificationAPITests(APITestCase):
    """Test case for Notification API"""

    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user1 = HorillaUser.objects.create_user(
            username="testuser1", email="test1@example.com", password="password123"
        )
        self.user2 = HorillaUser.objects.create_user(
            username="testuser2", email="test2@example.com", password="password123"
        )

        # Create test notifications
        self.notification1 = Notification.objects.create(
            user=self.user1,
            message="Test notification 1",
            sender=self.user2,
            url="/test/url/1",
        )
        self.notification2 = Notification.objects.create(
            user=self.user1,
            message="Test notification 2",
            sender=self.user2,
            url="/test/url/2",
        )

        # Set up client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

        # URLs
        self.list_url = reverse("notification-list")
        self.detail_url = reverse("notification-detail", args=[self.notification1.id])
        self.mark_read_url = reverse(
            "notification-mark-as-read", args=[self.notification1.id]
        )
        self.mark_all_read_url = reverse("notification-mark-all-as-read")
        self.unread_count_url = reverse("notification-unread-count")

    def test_list_notifications(self):
        """Test listing notifications"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_notification(self):
        """Test creating a notification"""
        data = {
            "user": self.user1.id,
            "message": "New test notification",
            "sender": self.user2.id,
            "url": "/test/url/new",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Notification.objects.count(), 3)

    def test_retrieve_notification(self):
        """Test retrieving a notification"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Test notification 1")

    def test_update_notification(self):
        """Test updating a notification"""
        data = {"message": "Updated notification"}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification1.refresh_from_db()
        self.assertEqual(self.notification1.message, "Updated notification")

    def test_delete_notification(self):
        """Test deleting a notification"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Notification.objects.count(), 1)

    def test_mark_as_read(self):
        """Test marking a notification as read"""
        response = self.client.post(self.mark_read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification1.refresh_from_db()
        self.assertTrue(self.notification1.read)

    def test_mark_all_as_read(self):
        """Test marking all notifications as read"""
        response = self.client.post(self.mark_all_read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification1.refresh_from_db()
        self.notification2.refresh_from_db()
        self.assertTrue(self.notification1.read)
        self.assertTrue(self.notification2.read)

    def test_unread_count(self):
        """Test getting unread notification count"""
        response = self.client.get(self.unread_count_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

        # Mark one as read
        self.notification1.read = True
        self.notification1.save()

        response = self.client.get(self.unread_count_url)
        self.assertEqual(response.data["count"], 1)

    def test_search_filter(self):
        """Test search functionality"""
        response = self.client.get(f"{self.list_url}?search=notification 1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_filter_by_read_status(self):
        """Test filtering by read status"""
        self.notification1.read = True
        self.notification1.save()

        response = self.client.get(f"{self.list_url}?read=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        response = self.client.get(f"{self.list_url}?read=false")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
