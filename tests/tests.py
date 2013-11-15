from binascii import unhexlify
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
from django_otp.util import random_hex


class LoginTest(TestCase):
    def test_form(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertContains(response, 'Username:')

    def test_invalid_login(self):
        response = self.client.post(
            reverse('two_factor:login'),
            data={'auth-username': 'unknown', 'auth-password': 'secret',
                  'login_view-current_step': 'auth'})
        self.assertContains(response, 'Please enter a correct username '
                                      'and password.')

    def test_valid_login(self):
        User.objects.create_user('bouke', None, 'secret')
        response = self.client.post(
            reverse('two_factor:login'),
            data={'auth-username': 'bouke', 'auth-password': 'secret',
                  'login_view-current_step': 'auth'})
        self.assertContains(response, '', status_code=302)

    def test_with_generator(self):
        user = User.objects.create_user('bouke', None, 'secret')
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex().decode())

        response = self.client.post(
            reverse('two_factor:login'),
            data={'auth-username': 'bouke', 'auth-password': 'secret',
                  'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self.client.post(
            reverse('two_factor:login'),
            data={'token-otp_token': '123456',
                  'login_view-current_step': 'token'})
        self.assertContains(response, 'Please enter your OTP token')

        response = self.client.post(
            reverse('two_factor:login'),
            data={'token-otp_token': totp(device.bin_key),
                  'login_view-current_step': 'token'})
        self.assertContains(response, '', status_code=302)

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))


class SetupTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('bouke', None, 'secret')
        assert self.client.login(username='bouke', password='secret')

    def test_form(self):
        response = self.client.get(reverse('two_factor:setup'))
        self.assertContains(response, 'Follow the steps in this wizard to '
                                      'enable two-factor')

    def test_setup_generator(self):
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'welcome'},
        )
        self.assertContains(response, 'Method:')

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'method',
                  'method-method': 'generator'},
        )
        self.assertContains(response, 'Token:')

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': '123456'},
        )
        self.assertContains(response, 'Please enter a valid token.')

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': totp(bin_key)},
        )
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        self.assertEqual(1, len(self.user.totpdevice_set.all()))
