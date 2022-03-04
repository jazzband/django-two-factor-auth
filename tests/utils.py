from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import resolve_url
from django.test.utils import TestContextDecorator
from django_otp import DEVICE_ID_SESSION_KEY

from two_factor.plugins.registry import registry
from two_factor.utils import default_device


class UserMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login_url = resolve_url(settings.LOGIN_URL)
        cls.User = get_user_model()

    def setUp(self):
        super().setUp()
        self._passwords = {}

    def create_user(self, username='bouke@example.com', password='secret', **kwargs):
        user = self.User.objects.create_user(username=username, email=username, password=password, **kwargs)
        self._passwords[user] = password
        return user

    def create_superuser(self, username='bouke@example.com', password='secret', **kwargs):
        user = self.User.objects.create_superuser(username=username, email=username, password=password, **kwargs)
        self._passwords[user] = password
        return user

    def login_user(self):
        user = list(self._passwords.keys())[0]
        username = user.get_username()
        assert self.client.login(username=username, password=self._passwords[user])
        if default_device(user):
            session = self.client.session
            session[DEVICE_ID_SESSION_KEY] = default_device(user).persistent_id
            session.save()

    def enable_otp(self, user=None):
        if user is None:
            user = list(self._passwords.keys())[0]
        return user.totpdevice_set.create(name='default')


class method_registry(TestContextDecorator):
    def __init__(self, method_codes):
        self.codes = method_codes
        super().__init__()

    def enable(self):
        # We count on the fact that initially registry._methods is full (default test settings)
        self.old_methods = registry._methods
        registry._methods = [m for m in self.old_methods if m.code in self.codes]

    def disable(self):
        registry._methods = self.old_methods
