from unittest import mock

from binascii import unhexlify
from django.test import TestCase
from django.conf import settings
from django.shortcuts import resolve_url
from django.test.utils import modify_settings, override_settings
from django.urls import reverse
from django_otp.oath import totp

from .utils import UserMixin
from two_factor.models import random_hex_str


class SetupTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.login_user()

    def _post_phone_or_yubikey(self, data):
        return self.client.post(reverse('two_factor:setup_reset_phone_or_yubikey'), data=data)

    def _post_generator_or_yubikey(self, data):
        return self.client.post(reverse('two_factor:setup_reset_generator_or_yubikey'), data=data)

    def _post_phone_or_generator(self, data):
        return self.client.post(reverse('two_factor:setup_reset_phone_or_generator'), data=data)

    @mock.patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_first_generator_switch_to_phone_sms(self, mock_signal):
        # First assume that Generator was used
        self.user.totpdevice_set.create(name='default',
                                   key=random_hex_str())

        totp_device = self.user.totpdevice_set.all()
        self.assertEqual(len(totp_device), 1)
        self.assertEqual(totp_device[0].name, 'default')

        # Go To reset and check that we can choose another method here
        response = self._post_phone_or_yubikey(
            data={'reset_setup_phone_or_yubikey_view-current_step': 'method'})
        self.assertContains(response, 'Method:')

        # Go for phone method -- SMS
        response = self._post_phone_or_yubikey(
            data={'reset_setup_phone_or_yubikey_view-current_step': 'method',
                  'method-method': 'sms'})
        self.assertContains(response, 'Number:')

        response = self._post_phone_or_yubikey(
            data={'reset_setup_phone_or_yubikey_view-current_step': 'sms',
                  'sms-number': '+31101234567'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We sent you a text message')

        # assert that the token was send to the gateway
        self.assertEqual(
            mock_signal.return_value.method_calls,
            [mock.call.send_sms(device=mock.ANY, token=mock.ANY)]
        )
        # assert that tokens are verified
        response = self._post_phone_or_yubikey(data={'reset_setup_phone_or_yubikey_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        # submitting correct token should finish the setup
        token = mock_signal.return_value.send_sms.call_args[1]['token']
        response = self._post_phone_or_yubikey(data={'reset_setup_phone_or_yubikey_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number.as_e164, '+31101234567')
        self.assertEqual(phones[0].method, 'sms')

        # Now totpdevice should be deleted
        totp_device = self.user.totpdevice_set.all()
        self.assertEqual(len(totp_device), 0)

    @mock.patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_first_generator_switch_to_phone_call(self, mock_signal):
        # First assume that Generator was used
        self.user.totpdevice_set.create(name='default',
                                   key=random_hex_str())

        totp_device = self.user.totpdevice_set.all()
        self.assertEqual(len(totp_device), 1)
        self.assertEqual(totp_device[0].name, 'default')

        # Go To reset and check that we can choose another method here
        response = self._post_phone_or_yubikey(
            data={'reset_setup_phone_or_yubikey_view-current_step': 'method'})
        self.assertContains(response, 'Method:')

        response = self._post_phone_or_yubikey(data={'reset_setup_phone_or_yubikey_view-current_step': 'method',
                                    'method-method': 'call'})
        self.assertContains(response, 'Number:')

        response = self._post_phone_or_yubikey(data={'reset_setup_phone_or_yubikey_view-current_step': 'call',
                                    'call-number': '+31101234567'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We are calling your phone right now')

        # assert that the token was send to the gateway
        self.assertEqual(
            mock_signal.return_value.method_calls,
            [mock.call.make_call(device=mock.ANY, token=mock.ANY)]
        )

        # assert that tokens are verified
        response = self._post_phone_or_yubikey(data={'reset_setup_phone_or_yubikey_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        # submitting correct token should finish the setup
        token = mock_signal.return_value.make_call.call_args[1]['token']
        response = self._post_phone_or_yubikey(data={'reset_setup_phone_or_yubikey_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number.as_e164, '+31101234567')
        self.assertEqual(phones[0].method, 'call')

        # Now totpdevice should be deleted
        totp_device = self.user.totpdevice_set.all()
        self.assertEqual(len(totp_device), 0)

    @modify_settings(INSTALLED_APPS={
        'remove': ['otp_yubikey'],
    })
    def test_setup_first_phone_call_switch_to_generator(self):
        # First assume that phone call was used
        self.user.phonedevice_set.create(name='default', number='+12024561111', method='call')

        phone_device = self.user.phonedevice_set.all()
        self.assertEqual(len(phone_device), 1)
        self.assertEqual(phone_device[0].name, 'default')

        # Go To reset and check that we can choose another method here
        response = self._post_generator_or_yubikey(
            data={'reset_setup_generator_or_yubikey_view-current_step': 'method'})
        self.assertContains(response, 'Method:')

        # Go for generator
        response = self._post_generator_or_yubikey(
            data={'reset_setup_generator_or_yubikey_view-current_step': 'method',
                  'method-method': 'generator'})

        self.assertContains(response, 'Token:')
        session = self.client.session
        self.assertIn('django_two_factor-qr_secret_key', session.keys())

        # assert that tokens are verified
        response = self._post_generator_or_yubikey(data={'reset_setup_generator_or_yubikey_view-current_step': 'generator',
                                                         'generator-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self._post_generator_or_yubikey(
            data={'reset_setup_generator_or_yubikey_view-current_step': 'generator',
                  'generator-token': totp(bin_key)})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(1, self.user.totpdevice_set.count())

        # Now phonedevice should be deleted
        phone_device = self.user.phonedevice_set.all()
        self.assertEqual(len(phone_device), 0)

    @modify_settings(INSTALLED_APPS={
        'remove': ['otp_yubikey'],
    })
    def test_setup_first_phone_sms_switch_to_generator(self):
        # First assume that phone sms was used
        self.user.phonedevice_set.create(name='default', number='+12024561111', method='sms')

        phone_device = self.user.phonedevice_set.all()
        self.assertEqual(len(phone_device), 1)
        self.assertEqual(phone_device[0].name, 'default')

        # Go To reset and check that we can choose another method here
        response = self._post_generator_or_yubikey(
            data={'reset_setup_generator_or_yubikey_view-current_step': 'method'})
        self.assertContains(response, 'Method:')

        # Go for generator
        response = self._post_generator_or_yubikey(
            data={'reset_setup_generator_or_yubikey_view-current_step': 'method',
                  'method-method': 'generator'})

        self.assertContains(response, 'Token:')
        session = self.client.session
        self.assertIn('django_two_factor-qr_secret_key', session.keys())

        # assert that tokens are verified
        response = self._post_generator_or_yubikey(data={'reset_setup_generator_or_yubikey_view-current_step': 'generator',
                                                         'generator-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self._post_generator_or_yubikey(
            data={'reset_setup_generator_or_yubikey_view-current_step': 'generator',
                  'generator-token': totp(bin_key)})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(1, self.user.totpdevice_set.count())

        # Now phonedevice should be deleted
        phone_device = self.user.phonedevice_set.all()
        self.assertEqual(len(phone_device), 0)
