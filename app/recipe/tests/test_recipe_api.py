from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """
    Helper function to return the recipe detail url
    """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """
    Helper function for creating a recipe
    return the recipe
    """
    defaults = {
        'title': "Sample Recipe Title",
        'time_minutes': 2,
        'price': Decimal('5.25'),
        'description': "Sample Description",
        'link': 'http://example.com/recipe.pdf'
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)

    return recipe


class PublicRecipeApiTests(TestCase):
    """
    Test unauthenticated API requests
    """
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_requests(self):
        """
        Unauthenticated requests on recipe API
        should return 401- Unauthorized
        """
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """
    Test authenticated API requests
    """
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpassword1234',
        )
        self.client.force_authenticate(self.user)

    def test_authenticated_requests(self):
        """
        Authenticated requests on recipe API
        should return 200- OK and a list of recipes
        """
        # creating sample recipes,
        # to make sure that it returns all the recipes
        create_recipe(self.user)
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_authenticated_user_recipes(self):
        """
        Authenticated requests on recipe API
        should return only the recipes of the current
        authenticated user, and returns 200- OK
        """
        other_user = get_user_model().objects.create_user(
            'otheruser@example.com',
            'testpass1234',
        )

        # create recipe for the other user
        create_recipe(other_user)

        # create recipe for the current user
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """
        Check if the detail for a specific recipe is correct
        should return 200-OK and the recipe details
        """
        recipe = create_recipe(user=self.user)
        recipe_url = detail_url(recipe.id)

        res = self.client.get(recipe_url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """
        Successful creation of recipe
        should return 201- Created
        """
        payload = {
            'title': "Sample recipe",
            'time_minutes': 45,
            'price': Decimal('8.50')
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)
