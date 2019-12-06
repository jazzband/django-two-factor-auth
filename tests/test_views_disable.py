from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse
from django_otp import devices_for_user

from .utils import UserMixin


class DisableTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    def test(self):
        response = self.client.get(reverse('two_factor:disable'))
        self.assertContains(response, 'Yes, I am sure')

        response = self.client.post(reverse('two_factor:disable'))
        self.assertEqual(response.context_data['form'].errors,
                         {'understand': ['This field is required.']})

        response = self.client.post(reverse('two_factor:disable'),
                                    {'understand': '1'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(devices_for_user(self.user)), [])

        # cannot disable twice
        response = self.client.get(reverse('two_factor:disable'))
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
