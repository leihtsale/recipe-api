from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class UserManger(BaseUserManager):
    """
    Manager for users
    """
    def create_user(self, email, password=None, **kwargs):
        """
        Create, save, and return a new user
        **kwargs - For extra fields
        """
        user = self.model(email=self.normalize_email(email), **kwargs)

        # password is set here for hashing
        user.set_password(password)

        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    User in the system
    """
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    objects = UserManger()

    # Defined field for user authentication
    USERNAME_FIELD = 'email'
