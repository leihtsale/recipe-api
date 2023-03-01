from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Ingredient
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='test@example.com', password='password1234'):
    """
    Helper function to create a user
    """
    return get_user_model().objects.create_user(email, password)


def create_ingredient(user, **kwargs):
    return Ingredient.objects.create(user=user, **kwargs)


class PublicIngredientsApiTests(TestCase):
    """
    Tests for unauthenticated API requests
    """
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_requests(self):
        """
        Unauthenticated requests on retrieving ingredients
        should return 401 - Unauthorized
        """
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """
    Test authenticated API requests
    """
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_authenticated_requests(self):
        """
        Authenticated requests on retrieving ingredients
        should return 200- OK and a list of ingredients
        """
        create_ingredient(self.user, name="potato")
        create_ingredient(self.user, name="carrot")
        ingredients = Ingredient.objects.all().order_by('-name')
        serialized = IngredientSerializer(ingredients, many=True)
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serialized.data)

    def test_authenticated_user_ingredients(self):
        """
        Authenticated requests for retrieving ingredients
        should only return the ingredients of the current
        authenticated user, and returns 200- OK
        """
        another_user = create_user(
            email='another@example.com',
            password='another1234'
        )
        # ingredient made by another user
        create_ingredient(another_user, name='garlic')

        # ingredient made by current authenticated user
        ingredient = create_ingredient(self.user, name="potato")

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """
        Updating ingredient details
        should return 200 - OK, and reflects on the database
        """
        ingredient = create_ingredient(self.user)
        payload = {'name': 'New name'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])
