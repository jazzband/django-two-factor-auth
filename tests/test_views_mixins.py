from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase

from .utils import UserMixin


class OTPRequiredMixinTest(UserMixin, TestCase):

    def test_unauthenticated_redirect(self):
        url = '/secure/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % (resolve_url(settings.LOGIN_URL), 'next=' + url)
        self.assertRedirects(response, redirect_to)

    def test_unauthenticated_raise(self):
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

    def test_unverified_redirect(self):
        self.create_user()
        self.login_user()
        url = '/secure/redirect_unverified/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % ('/account/login/', 'next=' + url)
        self.assertRedirects(response, redirect_to)

    def test_unverified_raise(self):
        self.create_user()
        self.login_user()
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

    def test_unverified_explanation(self):
        self.create_user()
        self.login_user()
        response = self.client.get('/secure/')
        self.assertContains(response, 'Permission Denied', status_code=403)
        self.assertContains(response, 'Enable Two-Factor Authentication', status_code=403)

    def test_unverified_need_login(self):
        self.create_user()
        self.login_user()
        self.enable_otp()  # create OTP after login, so not verified
        url = '/secure/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % (resolve_url(settings.LOGIN_URL), 'next=' + url)
        self.assertRedirects(response, redirect_to)

    def test_verified(self):
        self.create_user()
        self.enable_otp()  # create OTP before login, so verified
        self.login_user()
        response = self.client.get('/secure/')
        self.assertEqual(response.status_code, 200)
