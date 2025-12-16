from unittest.mock import patch

from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Customer
from .tokens import customer_token_generator


class CustomerTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="oldpassword123",  # This will be hashed by save()
            phone="1234567890",
        )
        self.customer.set_password(
            "oldpassword123"
        )  # Set raw password for initial login check
        self.customer.save()  # This hashes it

    def test_customer_flow(self):
        # 1. Register
        register_url = reverse("customer-register")
        customer_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "oldpassword123",
            "phone": "1234567890",
        }
        # This registration should fail because the customer already exists from setUp
        response = self.client.post(register_url, customer_data)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )  # Assuming email uniqueness

        # 2. Login with existing customer
        login_url = reverse("customer-login")
        login_data = {"email": "john@example.com", "password": "oldpassword123"}
        response = self.client.post(login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tokens = response.data["tokens"]
        access_token = tokens["access"]

        # 3. Get Details
        detail_url = reverse("customer-detail")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "john@example.com")

        # 4. Change Password
        change_password_url = reverse("customer-change-password")
        change_password_data = {
            "old_password": "oldpassword123",
            "new_password": "newpassword123",
        }
        response = self.client.post(change_password_url, change_password_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Verify new password by logging in again
        login_data_new = {"email": "john@example.com", "password": "newpassword123"}
        # Reset credentials to test login without token (though login shouldn't need token)
        self.client.credentials()
        response = self.client.post(login_url, login_data_new)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 6. Verify old password fails
        response = self.client.post(login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="0987654321",
        )
        self.customer.set_password("password123")
        # Ensure password is hashed
        self.customer.save()

    @patch("customer.views.resend.Emails.send")
    def test_password_reset_flow(self, mock_send):
        mock_send.return_value = {"id": "123"}

        # 1. Request Password Reset
        request_url = reverse("customer-password-reset-request")
        response = self.client.post(request_url, {"email": "jane@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ensure email was "sent"
        self.assertTrue(mock_send.called)

        # 2. Generate valid UID and Token manually (since we can't intercept the email content easily)
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = customer_token_generator.make_token(self.customer)

        # 3. Confirm Password Reset
        confirm_url = reverse("customer-password-reset-confirm")
        new_password = "newstrongpassword456"
        confirm_data = {"uid": uid, "token": token, "password": new_password}
        response = self.client.post(confirm_url, confirm_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Verify Login with new password
        login_url = reverse("customer-login")
        login_data = {"email": "jane@example.com", "password": new_password}
        response = self.client.post(login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Verify old password fails
        login_data_old = {"email": "jane@example.com", "password": "password123"}
        response = self.client.post(login_url, login_data_old)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("customer.views.resend.Emails.send")
    def test_password_reset_invalid_email(self, mock_send):
        url = reverse("customer-password-reset-request")
        response = self.client.post(url, {"email": "nonexistent@example.com"})
        # Should return 200 to avoid enumeration, but NOT send email
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Need to check if logic avoids sending email.
        # My implementation fetches user, if DoesNotExist returns 200.
        # So mock_send should NOT be called.
        # Wait, in the view:
        # try: customer = Customer.objects.get(email=email)
        # except DoesNotExist: return Response(200...)
        # So yes, email sending is skipped.
        self.assertFalse(mock_send.called)

    def test_password_reset_invalid_token(self):
        url = reverse("customer-password-reset-confirm")
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        confirm_data = {"uid": uid, "token": "invalid-token", "password": "newpassword"}
        response = self.client.post(url, confirm_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
