from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from decimal import Decimal

from core.models import Ingredient, Recipe
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
        ingredient = create_ingredient(self.user, name='Sample')
        payload = {'name': 'New name'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """
        Deleting an ingredient
        should return 204 - No content, and remove the ingredient
        from the database
        """
        ingredient = create_ingredient(self.user, name='Sample')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """
        Listing ingredients with filter "assigned_only" = 1
        should only return a list of ingredients
        that are assigned to a recipe/s
        """
        onion = create_ingredient(user=self.user, name='Onion')
        garlic = create_ingredient(user=self.user, name='Garlic')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Adobo',
            time_minutes=30,
            price=Decimal('4.50'),
        )
        recipe.ingredients.add(onion)

        query_params = {'assigned_only': 1}
        res = self.client.get(INGREDIENTS_URL, query_params)

        serialized_onion = IngredientSerializer(onion)
        serialized_garlic = IngredientSerializer(garlic)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serialized_onion.data, res.data)
        self.assertNotIn(serialized_garlic.data, res.data)

    def test_unique_filtered_ingredients(self):
        """
        Listing ingredients with filter "assigned_only" = 1
        should only return a list of distinct ingredients
        that are assigned to a recipe/s
        This test just make sure that the list have no duplicated ingredients
        returned in the list.
        """
        onion = Ingredient.objects.create(user=self.user, name='Onion')
        Ingredient.objects.create(user=self.user, name='Garlic')
        recipe_adobo = Recipe.objects.create(
            user=self.user,
            title='Adobo',
            time_minutes=30,
            price=Decimal('4.50'),
        )
        recipe_tinola = Recipe.objects.create(
            user=self.user,
            title='Tinola',
            time_minutes=45,
            price=Decimal('5.50'),
        )
        recipe_adobo.ingredients.add(onion)
        recipe_tinola.ingredients.add(onion)

        query_params = {'assigned_only': 1}
        res = self.client.get(INGREDIENTS_URL, query_params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
