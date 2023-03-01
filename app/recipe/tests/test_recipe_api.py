from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient
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


def create_user(**params):
    return get_user_model().objects.create_user(**params)


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
        self.user = create_user(
            email='user@example.com',
            password='testpassword1234',
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
        other_user = create_user(
            email='otheruser@example.com',
            password='testpass1234',
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

    def test_partial_update(self):
        """
        Successful partial update
        should only update the concern field
        """
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title="Sample Recipe Title",
            link=original_link,
        )
        payload = {
            'title': "New Recipe Title"
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """
        Successful updates in all fields
        should update all the fields, except the user
        """
        recipe = create_recipe(
            user=self.user,
            title="Sample Recipe Title",
            link='https://example.com/recipe.pdf',
            description="Sample Recipe Description",
        )
        payload = {
            'title': "New Recipe Title",
            'link': 'https://example.com/new_recipe.pdf',
            'description': "New Recipe Description",
            'price': Decimal('2.50'),
            'time_minutes': 15,
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_attempt_update_user(self):
        """
        User can't update other user's recipe
        """
        new_user = create_user(
            email='new.user@example.com',
            password='newpassword1234',
        )
        recipe = create_recipe(user=self.user)
        payload = {
            'user': new_user,
        }
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """
        Successful deletion of recipe
        should return 204- No content
        """
        recipe = create_recipe(self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_recipe(self):
        """
        User can't delete other user's recipe
        """
        new_user = create_user(
            email='new.user@example.com',
            password='newpass1234',
        )
        recipe = create_recipe(user=new_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tag(self):
        """
        Creating a new recipe with new tag/s
        should return 201 - Created, and assign/create the
        new tags to the created recipe
        """
        payload = {
            'title': 'Chicken Curry',
            'time_minutes': 20,
            'price': Decimal(2.50),
            'tags': [{'name': 'Chicken'}, {'name': 'Dinner'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tags in payload['tags']:
            tag = recipe.tags.filter(
                name=tags['name'],
                user=self.user
            )
            self.assertTrue(tag.exists())

    def test_create_recipe_with_existing_tag(self):
        """
        Creating new recipe with existing tag and new tag
        should return 201 - Created and assigns the tags/s
        to newly created recipe
        """
        tag_chicken = Tag.objects.create(name='Chicken', user=self.user)
        payload = {
            'title': 'Chicken Curry',
            'time_minutes': 20,
            'price': Decimal(2.50),
            'tags': [{'name': 'Chicken'}, {'name': 'Dinner'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        self.assertIn(tag_chicken, recipe.tags.all())

        for tags in payload['tags']:
            tag = recipe.tags.filter(
                name=tags['name'],
                user=self.user
            )
            self.assertTrue(tag.exists())

    def test_create_tag_update(self):
        """
        Updating a recipe with a tag that does not exists
        should create that tag, and assign it to the recipe
        return 200 - OK
        """
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Dessert'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        dessert_tag = Tag.objects.get(user=self.user, name='Dessert')
        self.assertIn(dessert_tag, recipe.tags.all())

    def test_assign_existing_tag_update(self):
        """
        Updating a tag with existing tag
        should assign that tag to the recipe
        return 200 - OK
        """
        tag_dessert = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_dessert)

        tag_dinner = Tag.objects.create(user=self.user, name='Dinner')
        payload = {'tags': [{'name': 'Dinner'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_dinner, recipe.tags.all())
        self.assertNotIn(tag_dessert, recipe.tags.all())

    def test_remove_tags(self):
        """
        Clearing the tags of a recipe
        should return 200 - OK, and tags are removed
        """
        tag_dessert = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_dessert)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_ingredients(self):
        """
        Creating a recipe with new ingredients
        should create the recipe and the ingredients
        and return 201 - Created
        """
        payload = {
            'title': 'Adobo',
            'time_minutes': 35,
            'price': Decimal('3.50'),
            'ingredients': [
                {'name': 'Chicken'},
                {'name': 'Onion'},
                {'name': 'Vinegar'}
            ],
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes.first()
        self.assertEqual(recipe.ingredients.count(), 3)

        for ingredient in payload['ingredients']:
            item = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            )
            self.assertTrue(item.exists())

    def test_create_recipe_with_existing_ingredient(self):
        """
        Creating a recipe with existing ingredient
        should create a recipe and assign the existing ingredient
        should expect that there are no duplicated ingredient
        to the recipe created, and return 201 - Created
        """
        ingredient = Ingredient.objects.create(user=self.user, name='Onion')
        payload = {
            'title': 'Adobo',
            'time_minutes': 35,
            'price': Decimal('3.50'),
            'ingredients': [
                {'name': 'Chicken'},
                {'name': 'Onion'},
                {'name': 'Vinegar'}
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes.first()
        self.assertEqual(recipe.ingredients.count(), 3)
        self.assertIn(ingredient, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            item = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            )
            self.assertTrue(item.exists())
