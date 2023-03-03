from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer

from decimal import Decimal


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """
    Create and return a tag detail url
    """
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='test@example.com', password='password1234'):
    """
    Helper function to create a user
    """
    return get_user_model().objects.create_user(email, password)


def create_tag(user, name="Sample Tag"):
    """
    Helper function to create a tag
    """
    return Tag.objects.create(user=user, name=name)


class PublicTagsApiTests(TestCase):
    """
    Tests for unauthenticated API requests
    """
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_requests(self):
        """
        Unauthenticated requests on Tags API
        should return 401- Unauthorized
        """
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """
    Test authenticated API requests
    """
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_authenticated_requests(self):
        """
        Authenticated requests on Tags API
        should return 200- OK and a list of tags
        """
        create_tag(user=self.user)
        create_tag(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_authenticated_user_tags(self):
        """
        Authenticated requests on tags API
        should return only the tags of the current
        authenticated user, and returns 200- OK
        """
        # create other user
        other_user = create_user(
            email='other@example.com',
            password='other1234'
        )

        # create tag for other user
        create_tag(user=other_user, name='Veggies')

        # create tag for current user
        create_tag(user=self.user)

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.filter(user=self.user)
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_update_tag(self):
        """
        Updating a tag by authenticated user
        should return 200 - OK, and reflects on the database
        """
        tag = create_tag(user=self.user, name='After Dinner')

        payload = {
            'name': 'Dessert',
        }
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)
        tag.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """
        Deleting a tag by authenticated user
        should return 204 - No Content, and
        tag is removed in the database
        """
        tag = create_tag(user=self.user, name='Breakfast')
        url = detail_url(tag.id)
        res = self.client.delete(url)
        tags = Tag.objects.filter(user=self.user)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """
        Listing ingredients with filter "assigned_only" = 1
        should only return a list of tags
        that are assigned to a recipe/s
        """
        lunch = create_tag(user=self.user, name='Lunch')
        dinner = create_tag(user=self.user, name='Dinner')
        recipe = Recipe.objects.create(
            user=self.user,
            title='Adobo',
            time_minutes=30,
            price=Decimal('4.50'),
        )
        recipe.tags.add(lunch)

        query_params = {'assigned_only': 1}
        res = self.client.get(TAGS_URL, query_params)

        serialized_lunch = TagSerializer(lunch)
        serialized_dinner = TagSerializer(dinner)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serialized_lunch.data, res.data)
        self.assertNotIn(serialized_dinner.data, res.data)

    def test_unique_filtered_tags(self):
        """
        Listing ingredients with filter "assigned_only" = 1
        should only return a list of distinct ingredients
        that are assigned to a recipe/s
        This test just make sure that the list have no duplicated tags
        returned in the list.
        """
        lunch = create_tag(user=self.user, name='Lunch')
        create_tag(user=self.user, name='Dinner')
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
        recipe_adobo.tags.add(lunch)
        recipe_tinola.tags.add(lunch)

        query_params = {'assigned_only': 1}
        res = self.client.get(TAGS_URL, query_params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
