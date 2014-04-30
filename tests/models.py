from django.conf import settings


if settings.AUTH_USER_MODEL == 'tests.User':
    from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager as BaseUserManager
    from django.db import models

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
