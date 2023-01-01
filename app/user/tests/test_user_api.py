"""
Test for the user API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')


def create_user(**kwargs):
    """
    Helper function to create and return a new user
    """
    return get_user_model().objects.create_user(**kwargs)


class PublicUserApiTests(TestCase):
    """
    Tests for all the functionalities of user API
    that doesn't require authentication
    """

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """
        Successful user creation
        should return an OK response
        """
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """
        Trying to create a user with the same email
        should return a bad request
        """
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """
        Password with less than 5 characters
        should return a bad request
        """
        payload = {
            'email': 'test@example.com',
            'password': 'test',
            'name': 'Test Name',
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # The user should not exists after the bad request
        is_user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()

        self.assertFalse(is_user_exists)

    def test_create_token_for_user(self):
        """
        Submitting valid credentials
        should generate token
        """
        user_details = {
            'name': 'Test Name',
            'email': 'test@example.com',
            'password': 'testpass123',
        }

        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password'],
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """
        Submitting bad/wrong credentials
        should return a bad request
        """
        create_user(email='test@example.com', password='testpass1234')

        payload = {
            'email': 'test@example.com',
            'password': 'wrongpass1234',
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_empty_password(self):
        """
        Submitting with empty/blank password
        should return a bad request
        """
        payload = {
            'email': 'test@example.com',
            'password': '',
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
