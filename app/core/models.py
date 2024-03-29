from django.conf import settings
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
import uuid
import os


def recipe_image_file_path(image, filename):
    """
    Generate a UUID file path for an uploaded image
    """
    extension = os.path.splitext(filename)[1]
    filename = f'{uuid.uuid4()}{extension}'

    return os.path.join('uploads', 'recipe', filename)


class UserManger(BaseUserManager):
    """
    Manager for users
    """
    def create_user(self, email, password=None, **kwargs):
        """
        Create, save, and return a new user
        """
        if not email:
            raise ValueError('Email address is required.')

        user = self.model(email=self.normalize_email(email), **kwargs)

        # password is set here for hashing
        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """
        Create and return superuser
        """
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model
    """
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    objects = UserManger()

    # Defined field for user authentication
    USERNAME_FIELD = 'email'


class Recipe(models.Model):
    """
    Model for recipes
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    time_minutes = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2)
    link = models.CharField(max_length=255, blank=True)
    tags = models.ManyToManyField('Tag')
    ingredients = models.ManyToManyField('Ingredient')
    image = models.ImageField(null=True, upload_to=recipe_image_file_path)

    def __str__(self):
        return self.title


class Tag(models.Model):
    """
    Model for Tag which can be assigned to a recipe
    primarily used for filtering recipes
    """
    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Model for Ingredient, part of Recipe
    """
    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name
