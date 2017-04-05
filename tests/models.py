from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, UserManager as BaseUserManager,
)
from django.db import models

# Only define these classes when we're testing a custom user model. Otherwise
# we'll get SystemCheckError "fields.E304".
if settings.AUTH_USER_MODEL == "tests.User":
    class UserManager(BaseUserManager):
        def _create_user(self, username, email, password,
                         is_staff, is_superuser, **extra_fields):
            """
            Creates and saves a User with the given email and password.
            """
            email = self.normalize_email(email)
            user = self.model(email=email, is_staff=is_staff,
                              is_superuser=is_superuser, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            return user

        def create_user(self, username, email=None, password=None, **extra_fields):
            return self._create_user(username, email, password, False, False, **extra_fields)

        def create_superuser(self, username, email, password, **extra_fields):
            return self._create_user(username, email, password, True, True, **extra_fields)


    class User(AbstractBaseUser, PermissionsMixin):
        """
        Custom User model inheriting from AbstractBaseUser. Should be admin site
        compatible.

        Email and password are required. Other fields are optional.
        """
        email = models.EmailField(blank=True, unique=True)
        is_staff = models.BooleanField(default=False)

        objects = UserManager()

        USERNAME_FIELD = 'email'

        def get_short_name(self):
            return self.email.split('@')[0]
