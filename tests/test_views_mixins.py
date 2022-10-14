from binascii import unhexlify

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import totp

from .utils import UserMixin, method_registry


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

    @method_registry(['generator'])
    def test_valid_login_with_redirect_field_name_without_device(self):
        self.create_user()
        protected_url = '/secure/'

        # Open URL that is protected
        #  assert go to login page
        #  assert the next param not in the session (but still in url)
        response = self.client.get(protected_url)
        redirect_url = "%s?%s%s" % (reverse('two_factor:login'), 'next=', protected_url)
        self.assertRedirects(response, redirect_url)
        self.assertEqual(self.client.session.get('next'), None)

        # Log in given the last redirect
        #  assert redirect to setup
        response = self.client.post(
            redirect_url,
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, reverse('two_factor:setup'))
        self.assertEqual(self.client.session.get('next'), protected_url)

        # Setup the device accordingly
        #  assert redirect to setup completed
        #  assert button for redirection to the original page
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'autofocus="autofocus"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'autocomplete="one-time-code"')

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': totp(bin_key)},
            follow=True,
        )

        self.assertRedirects(response, protected_url)
