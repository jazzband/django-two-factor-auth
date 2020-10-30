from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY, devices_for_user

from .utils import UserMixin


class DisableTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    def test_get(self):
        response = self.client.get(reverse('two_factor:disable'))
        self.assertContains(response, 'Yes, I am sure')

    def test_post_no_data(self):
        response = self.client.post(reverse('two_factor:disable'))
        self.assertEqual(response.context_data['form'].errors,
                         {'understand': ['This field is required.']})

    def test_post_success(self):
        response = self.client.post(reverse('two_factor:disable'),
                                    {'understand': '1'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(devices_for_user(self.user)), [])

    def test_cannot_disable_twice(self):
        [i.delete() for i in devices_for_user(self.user)]
        response = self.client.get(reverse('two_factor:disable'))
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

    def test_cannot_disable_without_verified(self):
        # remove OTP data from session
        session = self.client.session
        del session[DEVICE_ID_SESSION_KEY]
        session.save()
        response = self.client.get(reverse('two_factor:disable'))
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
