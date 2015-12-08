# encoding=UTF8
from __future__ import unicode_literals
from binascii import unhexlify
import os
import sys

try:
    # Try StringIO first, as Python 2.7 also includes an unicode-strict
    # io.StringIO.
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    from urllib.parse import urlencode, urlparse, parse_qsl
except ImportError:
    from urllib import urlencode
    from urlparse import urlparse, parse_qsl

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from unittest.mock import patch, Mock, ANY, call
except ImportError:
    from mock import patch, Mock, ANY, call

from django import forms
from django.conf import settings
from django.core.management import call_command, CommandError
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import six

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

from django_otp import DEVICE_ID_SESSION_KEY, devices_for_user
from django_otp.oath import totp
from django_otp.util import random_hex

try:
    from otp_yubikey.models import ValidationService, RemoteYubikeyDevice
except ImportError:
    ValidationService = RemoteYubikeyDevice = None

import qrcode.image.svg

from two_factor.admin import patch_admin, unpatch_admin
from two_factor.models import PhoneDevice
from two_factor.utils import backup_phones, default_device, get_otpauth_url, totp_digits
from two_factor.validators import validate_international_phonenumber


class UserMixin(object):
    def setUp(self):
        super(UserMixin, self).setUp()
        self._passwords = {}

    def create_user(self, username='bouke@example.com',
                    password='secret', **kwargs):
        user = User.objects.create_user(username=username, email=username,
                                        password=password, **kwargs)
        self._passwords[user] = password
        return user

    def create_superuser(self, username='bouke@example.com',
                         password='secret', **kwargs):
        user = User.objects.create_superuser(username=username, email=username,
                                             password=password, **kwargs)
        self._passwords[user] = password
        return user

    def login_user(self, user=None):
        if not user:
            user = list(self._passwords.keys())[0]
        try:
            username = user.get_username()
        except AttributeError:
            username = user.username
        assert self.client.login(username=username,
                                 password=self._passwords[user])
        if default_device(user):
            session = self.client.session
            session[DEVICE_ID_SESSION_KEY] = default_device(user).persistent_id
            session.save()

    def enable_otp(self, user=None):
        if not user:
            user = list(self._passwords.keys())[0]
        return user.totpdevice_set.create(name='default')


class LoginTest(UserMixin, TestCase):
    def _post(self, data=None):
        return self.client.post(reverse('two_factor:login'), data=data)

    def test_form(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertContains(response, 'Password:')

    def test_invalid_login(self):
        response = self._post({'auth-username': 'unknown',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Please enter a correct')
        self.assertContains(response, 'and password.')

    @patch('two_factor.views.core.signals.user_verified.send')
    def test_valid_login(self, mock_signal):
        self.create_user()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

        # No signal should be fired for non-verified user logins.
        self.assertFalse(mock_signal.called)

    def test_valid_login_with_custom_redirect(self):
        redirect_url = reverse('two_factor:setup')
        self.create_user()
        response = self.client.post(
            '%s?%s' % (reverse('two_factor:login'),
                       urlencode({'next': redirect_url})),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_valid_login_with_redirect_field_name(self):
        redirect_url = reverse('two_factor:setup')
        self.create_user()
        response = self.client.post(
            '%s?%s' % (reverse('custom-login'),
                       urlencode({'next_page': redirect_url})),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    @patch('two_factor.views.core.signals.user_verified.send')
    def test_with_generator(self, mock_signal):
        user = self.create_user()
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex().decode())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': '123456',
                               'login_view-current_step': 'token'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': ['Please enter your OTP token']})

        response = self._post({'token-otp_token': totp(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=ANY, request=ANY, user=user, device=device)

    @patch('two_factor.gateways.fake.Fake')
    @patch('two_factor.views.core.signals.user_verified.send')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_with_backup_phone(self, mock_signal, fake):
        user = self.create_user()
        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                user.totpdevice_set.create(name='default', key=random_hex().decode(),
                                           digits=no_digits)
                device = user.phonedevice_set.create(name='backup', number='+31101234567',
                                                     method='sms',
                                                     key=random_hex().decode())

                # Backup phones should be listed on the login form
                response = self._post({'auth-username': 'bouke@example.com',
                                       'auth-password': 'secret',
                                       'login_view-current_step': 'auth'})
                self.assertContains(response, 'Send text message to +31 ** *** **67')

                # Ask for challenge on invalid device
                response = self._post({'auth-username': 'bouke@example.com',
                                       'auth-password': 'secret',
                                       'challenge_device': 'MALICIOUS/INPUT/666'})
                self.assertContains(response, 'Send text message to +31 ** *** **67')

                # Ask for SMS challenge
                response = self._post({'auth-username': 'bouke@example.com',
                                       'auth-password': 'secret',
                                       'challenge_device': device.persistent_id})
                self.assertContains(response, 'We sent you a text message')
                fake.return_value.send_sms.assert_called_with(
                    device=device,
                    token=str(totp(device.bin_key, digits=no_digits)).zfill(no_digits))

                # Ask for phone challenge
                device.method = 'call'
                device.save()
                response = self._post({'auth-username': 'bouke@example.com',
                                       'auth-password': 'secret',
                                       'challenge_device': device.persistent_id})
                self.assertContains(response, 'We are calling your phone right now')
                fake.return_value.make_call.assert_called_with(
                    device=device,
                    token=str(totp(device.bin_key, digits=no_digits)).zfill(no_digits))

            # Valid token should be accepted.
            response = self._post({'token-otp_token': totp(device.bin_key),
                                   'login_view-current_step': 'token'})
            self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
            self.assertEqual(device.persistent_id,
                             self.client.session.get(DEVICE_ID_SESSION_KEY))

            # Check that the signal was fired.
            mock_signal.assert_called_with(sender=ANY, request=ANY, user=user, device=device)

    @patch('two_factor.views.core.signals.user_verified.send')
    def test_with_backup_token(self, mock_signal):
        user = self.create_user()
        user.totpdevice_set.create(name='default', key=random_hex().decode())
        device = user.staticdevice_set.create(name='backup')
        device.token_set.create(token='abcdef123')

        # Backup phones should be listed on the login form
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Backup Token')

        # Should be able to go to backup tokens step in wizard
        response = self._post({'wizard_goto_step': 'backup'})
        self.assertContains(response, 'backup tokens')

        # Wrong codes should not be accepted
        response = self._post({'backup-otp_token': 'WRONG',
                               'login_view-current_step': 'backup'})
        self.assertContains(response, 'Please enter your OTP token')

        # Valid token should be accepted.
        response = self._post({'backup-otp_token': 'abcdef123',
                               'login_view-current_step': 'backup'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=ANY, request=ANY, user=user, device=device)

    @patch('two_factor.views.utils.logger')
    def test_change_password_in_between(self, mock_logger):
        """
        When the password of the user is changed while trying to login, should
        not result in errors. Refs #63.
        """
        user = self.create_user()
        self.enable_otp()

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        # Now, the password is changed. When the form is submitted, the
        # credentials should be checked again. If that's the case, the
        # login form should note that the credentials are invalid.
        user.set_password('secret2')
        user.save()
        response = self._post({'login_view-current_step': 'token'})
        self.assertContains(response, 'Please enter a correct')
        self.assertContains(response, 'and password.')

        # Check that a message was logged.
        mock_logger.warning.assert_called_with(
            "Current step '%s' is no longer valid, returning to last valid "
            "step in the wizard.",
            'token')

    @patch('two_factor.views.utils.logger')
    def test_reset_wizard_state(self, mock_logger):
        self.create_user()
        self.enable_otp()

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        # A GET request resets the state of the wizard...
        self.client.get(reverse('two_factor:login'))

        # ...so there is no user in this request anymore. As the login flow
        # depends on a user being present, this should be handled gracefully.
        response = self._post({'token-otp_token': '123456',
                               'login_view-current_step': 'token'})
        self.assertContains(response, 'Password:')

        # Check that a message was logged.
        mock_logger.warning.assert_called_with(
            "Requested step '%s' is no longer valid, returning to last valid "
            "step in the wizard.",
            'token')


class SetupTest(UserMixin, TestCase):
    def setUp(self):
        super(SetupTest, self).setUp()
        self.user = self.create_user()
        self.login_user()

    def test_form(self):
        response = self.client.get(reverse('two_factor:setup'))
        self.assertContains(response, 'Follow the steps in this wizard to '
                                      'enable two-factor')

    def test_setup_generator(self):
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'method',
                  'method-method': 'generator'})
        self.assertContains(response, 'Token:')
        session = self.client.session
        self.assertIn('django_two_factor-qr_secret_key', session.keys())

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['This field is required.']})

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': totp(bin_key)})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))
        self.assertEqual(1, self.user.totpdevice_set.count())

    def _post(self, data):
        return self.client.post(reverse('two_factor:setup'), data=data)

    def test_no_phone(self):
        with self.settings(TWO_FACTOR_CALL_GATEWAY=None):
            response = self._post(data={'setup_view-current_step': 'welcome'})
            self.assertNotContains(response, 'call')

        with self.settings(TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake'):
            response = self._post(data={'setup_view-current_step': 'welcome'})
            self.assertContains(response, 'call')

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_phone_call(self, fake):
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self._post(data={'setup_view-current_step': 'method',
                                    'method-method': 'call'})
        self.assertContains(response, 'Number:')

        response = self._post(data={'setup_view-current_step': 'call',
                                    'call-number': '+31101234567'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We are calling your phone right now')

        # assert that the token was send to the gateway
        self.assertEqual(fake.return_value.method_calls,
                         [call.make_call(device=ANY, token=ANY)])

        # assert that tokens are verified
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        # submitting correct token should finish the setup
        token = fake.return_value.make_call.call_args[1]['token']
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number.as_e164, '+31101234567')
        self.assertEqual(phones[0].method, 'call')

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_phone_sms(self, fake):
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self._post(data={'setup_view-current_step': 'method',
                                    'method-method': 'sms'})
        self.assertContains(response, 'Number:')

        response = self._post(data={'setup_view-current_step': 'sms',
                                    'sms-number': '+31101234567'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We sent you a text message')

        # assert that the token was send to the gateway
        self.assertEqual(fake.return_value.method_calls,
                         [call.send_sms(device=ANY, token=ANY)])

        # assert that tokens are verified
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        # submitting correct token should finish the setup
        token = fake.return_value.send_sms.call_args[1]['token']
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number.as_e164, '+31101234567')
        self.assertEqual(phones[0].method, 'sms')

    def test_already_setup(self):
        self.enable_otp()
        self.login_user()
        response = self.client.get(reverse('two_factor:setup'))
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

    def test_no_double_login(self):
        """
        Activating two-factor authentication for ones account, should
        automatically mark the session as being OTP verified. Refs #44.
        """
        self.test_setup_generator()
        device = self.user.totpdevice_set.all()[0]

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

    def test_suggest_backup_number(self):
        """
        Finishing the setup wizard should suggest to add a phone number, if
        a phone method is available. Refs #49.
        """
        self.enable_otp()
        self.login_user()

        with self.settings(TWO_FACTOR_SMS_GATEWAY=None):
            response = self.client.get(reverse('two_factor:setup_complete'))
            self.assertNotContains(response, 'Add Phone Number')

        with self.settings(TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake'):
            response = self.client.get(reverse('two_factor:setup_complete'))
            self.assertContains(response, 'Add Phone Number')


class OTPRequiredMixinTest(UserMixin, TestCase):
    def test_unauthenticated_redirect(self):
        url = '/secure/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % (settings.LOGIN_URL, urlencode({'next': url}))
        self.assertRedirects(response, redirect_to)

    def test_unauthenticated_raise(self):
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

    def test_unverified_redirect(self):
        self.create_user()
        self.login_user()
        url = '/secure/redirect_unverified/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % ('/account/login/', urlencode({'next': url}))
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
        self.assertContains(response, 'Enable Two-Factor Authentication',
                            status_code=403)

    def test_unverified_need_login(self):
        self.create_user()
        self.login_user()
        self.enable_otp()  # create OTP after login, so not verified
        url = '/secure/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % (settings.LOGIN_URL, urlencode({'next': url}))
        self.assertRedirects(response, redirect_to)

    def test_verified(self):
        self.create_user()
        self.enable_otp()  # create OTP before login, so verified
        self.login_user()
        response = self.client.get('/secure/')
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF='tests.urls_admin')
class AdminPatchTest(TestCase):

    def setUp(self):
        patch_admin()

    def tearDown(self):
        unpatch_admin()

    def test(self):
        response = self.client.get('/admin/', follow=True)
        redirect_to = '%s?%s' % (settings.LOGIN_URL,
                                 urlencode({'next': '/admin/'}))
        self.assertRedirects(response, redirect_to)


@override_settings(ROOT_URLCONF='tests.urls_admin')
class AdminSiteTest(UserMixin, TestCase):

    def setUp(self):
        super(AdminSiteTest, self).setUp()
        self.user = self.create_superuser()
        self.login_user()

    def test_default_admin(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF='tests.urls_otp_admin')
class OTPAdminSiteTest(UserMixin, TestCase):

    def setUp(self):
        super(OTPAdminSiteTest, self).setUp()
        self.user = self.create_superuser()
        self.login_user()

    def test_otp_admin_without_otp(self):
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?%s' % (settings.LOGIN_URL,
                                 urlencode({'next': '/otp_admin/'}))
        self.assertRedirects(response, redirect_to)

    def test_otp_admin_with_otp(self):
        self.enable_otp()
        self.login_user()
        response = self.client.get('/otp_admin/')
        self.assertEqual(response.status_code, 200)


class BackupTokensTest(UserMixin, TestCase):
    def setUp(self):
        super(BackupTokensTest, self).setUp()
        self.create_user()
        self.enable_otp()
        self.login_user()

    def test_empty(self):
        response = self.client.get(reverse('two_factor:backup_tokens'))
        self.assertContains(response, 'You don\'t have any backup codes yet.')

    def test_generate(self):
        url = reverse('two_factor:backup_tokens')

        response = self.client.post(url)
        self.assertRedirects(response, url)

        response = self.client.get(url)
        first_set = set([token.token for token in
                        response.context_data['device'].token_set.all()])
        self.assertNotContains(response, 'You don\'t have any backup codes '
                                         'yet.')
        self.assertEqual(10, len(first_set))

        # Generating the tokens should give a fresh set
        self.client.post(url)
        response = self.client.get(url)
        second_set = set([token.token for token in
                         response.context_data['device'].token_set.all()])
        self.assertNotEqual(first_set, second_set)


class PhoneSetupTest(UserMixin, TestCase):
    def setUp(self):
        super(PhoneSetupTest, self).setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    def test_form(self):
        response = self.client.get(reverse('two_factor:phone_create'))
        self.assertContains(response, 'Number:')

    def _post(self, data=None):
        return self.client.post(reverse('two_factor:phone_create'), data=data)

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_setup(self, fake):
        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '',
                               'setup-method': ''})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'method': ['This field is required.'],
                          'number': ['This field is required.']})

        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '+31101234567',
                               'setup-method': 'call'})
        self.assertContains(response, 'We\'ve sent a token to your phone')
        device = response.context_data['wizard']['form'].device
        fake.return_value.make_call.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': totp(device.bin_key)})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'backup')
        self.assertEqual(phones[0].number.as_e164, '+31101234567')
        self.assertEqual(phones[0].key, device.key)

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_number_validation(self, fake):
        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '123',
                               'setup-method': 'call'})
        self.assertEqual(
            response.context_data['wizard']['form'].errors,
            {'number': [six.text_type(validate_international_phonenumber.message)]})


class PhoneDeleteTest(UserMixin, TestCase):
    def setUp(self):
        super(PhoneDeleteTest, self).setUp()
        self.user = self.create_user()
        self.backup = self.user.phonedevice_set.create(name='backup', method='sms', number='+1')
        self.default = self.user.phonedevice_set.create(name='default', method='call', number='+1')
        self.login_user()

    def test_delete(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.backup.pk]))
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(backup_phones(self.user)), [])

    def test_cannot_delete_default(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.default.pk]))
        self.assertContains(response, 'was not found', status_code=404)


class QRTest(UserMixin, TestCase):
    test_secret = 'This is a test secret for an OTP Token'
    test_img = 'This is a test string that represents a QRCode'

    def setUp(self):
        super(QRTest, self).setUp()
        self.user = self.create_user(username='ⓑỚ𝓾⒦ȩ')
        self.login_user()

    def test_without_secret(self):
        response = self.client.get(reverse('two_factor:qr'))
        self.assertEquals(response.status_code, 404)

    @patch('qrcode.make')
    def test_with_secret(self, mockqrcode):
        # Setup the mock data
        def side_effect(resp):
            resp.write(self.test_img)
        mockimg = Mock()
        mockimg.save.side_effect = side_effect
        mockqrcode.return_value = mockimg

        # Setup the session
        session = self.client.session
        session['django_two_factor-qr_secret_key'] = self.test_secret
        session.save()

        # Get default image factory
        default_factory = qrcode.image.svg.SvgPathImage

        # Get the QR code
        response = self.client.get(reverse('two_factor:qr'))

        # Check things went as expected
        mockqrcode.assert_called_with(
            get_otpauth_url(accountname=self.user.get_username(),
                            secret=self.test_secret, issuer="testserver"),
            image_factory=default_factory)
        mockimg.save.assert_called_with(ANY)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content.decode('utf-8'), self.test_img)
        self.assertEquals(response['Content-Type'], 'image/svg+xml; charset=utf-8')


class DisableTest(UserMixin, TestCase):
    def setUp(self):
        super(DisableTest, self).setUp()
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
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(devices_for_user(self.user)), [])

        # cannot disable twice
        response = self.client.get(reverse('two_factor:disable'))
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))


class PhoneDeviceTest(UserMixin, TestCase):
    def test_verify(self):
        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                device = PhoneDevice(key=random_hex().decode())
                self.assertFalse(device.verify_token(-1))
                self.assertFalse(device.verify_token('foobar'))
                self.assertTrue(device.verify_token(totp(device.bin_key, digits=no_digits)))

    def test_verify_token_as_string(self):
        """
        The field used to read the token may be a CharField,
        so the PhoneDevice must be able to validate tokens
        read as strings
        """
        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                device = PhoneDevice(key=random_hex().decode())
                self.assertTrue(device.verify_token(str(totp(device.bin_key, digits=no_digits))))

    def test_unicode(self):
        device = PhoneDevice(name='unknown')
        self.assertEqual('unknown (None)', str(device))

        device.user = self.create_user()
        self.assertEqual('unknown (bouke@example.com)', str(device))


class UtilsTest(UserMixin, TestCase):
    def test_default_device(self):
        user = self.create_user()
        self.assertEqual(default_device(user), None)

        user.phonedevice_set.create(name='backup', number='+1')
        self.assertEqual(default_device(user), None)

        default = user.phonedevice_set.create(name='default', number='+1')
        self.assertEqual(default_device(user).pk, default.pk)

    def test_backup_phones(self):
        self.assertQuerysetEqual(list(backup_phones(None)),
                                 list(PhoneDevice.objects.none()))
        user = self.create_user()
        user.phonedevice_set.create(name='default', number='+1')
        backup = user.phonedevice_set.create(name='backup', number='+1')
        phones = backup_phones(user)

        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].pk, backup.pk)

    @unittest.skipIf((3, 2) <= sys.version_info < (3, 3), "Python 3.2's urlparse is broken")
    @unittest.skipIf(sys.version_info < (2, 7), "Python 2.6 not supported")
    def test_get_otpauth_url(self):
        for num_digits in (6, 8):
            self.assertEqualUrl(
                'otpauth://totp/bouke%40example.com?secret=abcdef123&digits=' + str(num_digits),
                get_otpauth_url(accountname='bouke@example.com', secret='abcdef123',
                                digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/Bouke%20Haarsma?secret=abcdef123&digits=' + str(num_digits),
                get_otpauth_url(accountname='Bouke Haarsma', secret='abcdef123',
                                digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/example.com%3A%20bouke%40example.com?'
                'secret=abcdef123&digits=' + str(num_digits) + '&issuer=example.com',
                get_otpauth_url(accountname='bouke@example.com', issuer='example.com',
                                secret='abcdef123', digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/My%20Site%3A%20bouke%40example.com?'
                'secret=abcdef123&digits=' + str(num_digits) + '&issuer=My+Site',
                get_otpauth_url(accountname='bouke@example.com', issuer='My Site',
                                secret='abcdef123', digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/%E6%B5%8B%E8%AF%95%E7%BD%91%E7%AB%99%3A%20'
                '%E6%88%91%E4%B8%8D%E6%98%AF%E9%80%97%E6%AF%94?'
                'secret=abcdef123&digits=' + str(num_digits) + '&issuer=测试网站',
                get_otpauth_url(accountname='我不是逗比',
                                issuer='测试网站',
                                secret='abcdef123', digits=num_digits))

    def assertEqualUrl(self, lhs, rhs):
        """
        Asserts whether the URLs are canonically equal.
        """
        if six.PY2:
            # See those Chinese characters above? Those are quite difficult
            # to match against the generated URLs in portable code. True,
            # this solution is not the nicest, but it works. And it's test
            # code after all.
            lhs = lhs.encode('utf8')

        lhs = urlparse(lhs)
        rhs = urlparse(rhs)
        self.assertEqual(lhs.scheme, rhs.scheme)
        self.assertEqual(lhs.netloc, rhs.netloc)
        self.assertEqual(lhs.path, rhs.path)
        self.assertEqual(lhs.fragment, rhs.fragment)

        # We used parse_qs before, but as query parameter order became
        # significant with Microsoft Authenticator and possibly other
        # authenticator apps, we've switched to parse_qsl.
        self.assertEqual(parse_qsl(lhs.query), parse_qsl(rhs.query))

    def test_get_totp_digits(self):
        # test that the default is 6 if TWO_FACTOR_TOTP_DIGITS is not set
        self.assertEqual(totp_digits(), 6)

        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                self.assertEqual(totp_digits(), no_digits)


class ValidatorsTest(TestCase):
    def test_phone_number_validator_on_form_valid(self):
        class TestForm(forms.Form):
            number = forms.CharField(validators=[validate_international_phonenumber])

        form = TestForm({
            'number': '+31101234567',
        })

        self.assertTrue(form.is_valid())

    def test_phone_number_validator_on_form_invalid(self):
        class TestForm(forms.Form):
            number = forms.CharField(validators=[validate_international_phonenumber])

        form = TestForm({
            'number': '+3110123456',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('number', form.errors)

        self.assertEqual(form.errors['number'],
                         [six.text_type(validate_international_phonenumber.message)])


class DisableCommandTest(UserMixin, TestCase):
    def _assert_raises(self, err_type, err_message):
        return self.assertRaisesMessage(err_type, err_message)

    def test_raises(self):
        stdout = six.StringIO()
        stderr = six.StringIO()
        with self._assert_raises(CommandError, 'User "some_username" does not exist'):
            call_command(
                'two_factor_disable', 'some_username',
                stdout=stdout, stderr=stderr)

        with self._assert_raises(CommandError, 'User "other_username" does not exist'):
            call_command(
                'two_factor_disable', 'other_username', 'some_username',
                stdout=stdout, stderr=stderr)

    def test_disable_single(self):
        user = self.create_user()
        self.enable_otp(user)
        call_command('two_factor_disable', 'bouke@example.com')
        self.assertEqual(list(devices_for_user(user)), [])

    def test_happy_flow_multiple(self):
        usernames = ['user%d@example.com' % i for i in range(0, 3)]
        users = [self.create_user(username) for username in usernames]
        [self.enable_otp(user) for user in users]
        call_command('two_factor_disable', *usernames[:2])
        self.assertEqual(list(devices_for_user(users[0])), [])
        self.assertEqual(list(devices_for_user(users[1])), [])
        self.assertNotEqual(list(devices_for_user(users[2])), [])


class StatusCommandTest(UserMixin, TestCase):
    def _assert_raises(self, err_type, err_message):
        return self.assertRaisesMessage(err_type, err_message)

    def setUp(self):
        super(StatusCommandTest, self).setUp()
        os.environ['DJANGO_COLORS'] = 'nocolor'

    def test_raises(self):
        stdout = six.StringIO()
        stderr = six.StringIO()
        with self._assert_raises(CommandError, 'User "some_username" does not exist'):
            call_command(
                'two_factor_status', 'some_username',
                stdout=stdout, stderr=stderr)

        with self._assert_raises(CommandError, 'User "other_username" does not exist'):
            call_command(
                'two_factor_status', 'other_username', 'some_username',
                stdout=stdout, stderr=stderr)

    def test_status_single(self):
        user = self.create_user()
        stdout = StringIO()
        call_command('two_factor_status', 'bouke@example.com', stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'bouke@example.com: disabled\n')

        stdout = StringIO()
        self.enable_otp(user)
        call_command('two_factor_status', 'bouke@example.com', stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'bouke@example.com: enabled\n')

    def test_status_mutiple(self):
        users = [self.create_user(n) for n in ['user0@example.com', 'user1@example.com']]
        self.enable_otp(users[0])
        stdout = StringIO()
        call_command('two_factor_status', 'user0@example.com', 'user1@example.com', stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'user0@example.com: enabled\n'
                                            'user1@example.com: disabled\n')
