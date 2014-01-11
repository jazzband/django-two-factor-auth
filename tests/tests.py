from binascii import unhexlify
from django.utils import translation
from two_factor.admin import patch_admin, unpatch_admin

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
try:
    from unittest.mock import patch, Mock, ANY, call
except ImportError:
    from mock import patch, Mock, ANY, call

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django_otp import DEVICE_ID_SESSION_KEY, devices_for_user
from django_otp.oath import totp
from django_otp.util import random_hex

from two_factor.gateways.fake import Fake
from two_factor.gateways.twilio import Twilio
from two_factor.models import PhoneDevice
from two_factor.utils import backup_phones, default_device


class UserMixin(object):
    def setUp(self):
        super(UserMixin, self).setUp()
        self.user = User.objects.create_user('bouke', None, 'secret')
        assert self.client.login(username='bouke', password='secret')


class OTPUserMixin(UserMixin):
    def setUp(self):
        super(OTPUserMixin, self).setUp()
        self.device = self.user.totpdevice_set.create(name='default')
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = self.device.persistent_id
        session.save()


class LoginTest(TestCase):
    def _post(self, data=None):
        return self.client.post(reverse('two_factor:login'), data=data)

    def test_form(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertContains(response, 'Username:')

    def test_invalid_login(self):
        response = self._post({'auth-username': 'unknown',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Please enter a correct username '
                                      'and password.')

    def test_valid_login(self):
        User.objects.create_user('bouke', None, 'secret')
        response = self._post({'auth-username': 'bouke',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

    def test_valid_login_with_custom_redirect(self):
        redirect_url = reverse('two_factor:setup')

        User.objects.create_user('bouke', None, 'secret')
        response = self.client.post(
            '%s?%s' % (reverse('two_factor:login'),
                       urlencode({'next': redirect_url})),
            {'auth-username': 'bouke',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_valid_login_with_redirect_field_name(self):
        redirect_url = reverse('two_factor:setup')

        User.objects.create_user('bouke', None, 'secret')
        response = self.client.post(
            '%s?%s' % (reverse('custom-login'),
                       urlencode({'next_page': redirect_url})),
            {'auth-username': 'bouke',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_with_generator(self):
        user = User.objects.create_user('bouke', None, 'secret')
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex().decode())

        response = self._post({'auth-username': 'bouke',
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

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_with_backup_phone(self, fake):
        user = User.objects.create_user('bouke', None, 'secret')
        user.totpdevice_set.create(name='default', key=random_hex().decode())
        device = user.phonedevice_set.create(name='backup', number='123456789',
                                             method='sms',
                                             key=random_hex().decode())

        # Backup phones should be listed on the login form
        response = self._post({'auth-username': 'bouke',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Send text message to 123****89')

        # Ask for challenge on invalid device
        response = self._post({'auth-username': 'bouke',
                               'auth-password': 'secret',
                               'challenge_device': 'MALICIOUS/INPUT/666'})
        self.assertContains(response, 'Send text message to 123****89')

        # Ask for SMS challenge
        response = self._post({'auth-username': 'bouke',
                               'auth-password': 'secret',
                               'challenge_device': device.persistent_id})
        self.assertContains(response, 'We sent you a text message')
        fake.return_value.send_sms.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))

        # Ask for phone challenge
        device.method = 'call'
        device.save()
        response = self._post({'auth-username': 'bouke',
                               'auth-password': 'secret',
                               'challenge_device': device.persistent_id})
        self.assertContains(response, 'We are calling your phone right now')
        fake.return_value.make_call.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))


class SetupTest(UserMixin, TestCase):
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
                         {'token': ['Please enter a valid token.']})

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
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertNotContains(response, 'call')

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_phone_call(self, fake):
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self._post(data={'setup_view-current_step': 'method',
                                    'method-method': 'call'})
        self.assertContains(response, 'Number:')

        response = self._post(data={'setup_view-current_step': 'call',
                                    'call-number': '+123456789'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We are calling your phone right now')

        # assert that the token was send to the gateway
        self.assertEqual(fake.return_value.method_calls,
                         [call.make_call(device=ANY, token=ANY)])

        # assert that tokens are verified
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid']})

        # submitting correct token should finish the setup
        token = fake.return_value.make_call.call_args[1]['token']
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number, '+123456789')
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
                                    'sms-number': '+123456789'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We sent you a text message')

        # assert that the token was send to the gateway
        self.assertEqual(fake.return_value.method_calls,
                         [call.send_sms(device=ANY, token=ANY)])

        # assert that tokens are verified
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid']})

        # submitting correct token should finish the setup
        token = fake.return_value.send_sms.call_args[1]['token']
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number, '+123456789')
        self.assertEqual(phones[0].method, 'sms')

    def test_already_setup(self):
        self.user.totpdevice_set.create(name='default')
        response = self.client.get(reverse('two_factor:setup'))
        self.assertRedirects(response, reverse('two_factor:setup_complete'))


class AdminPatchTest(TestCase):
    def setUp(self):
        patch_admin()

    def tearDown(self):
        unpatch_admin()

    def test(self):
        response = self.client.get('/admin/')
        redirect_to = '%s?%s' % (settings.LOGIN_URL,
                                 urlencode({'next': '/admin/'}))
        self.assertRedirects(response, redirect_to)


class AdminSiteTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('bouke', None, 'secret')
        self.client.login(username='bouke', password='secret')

    def test_default_admin(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_otp_admin_without_otp(self):
        response = self.client.get('/otp_admin/')
        redirect_to = '%s?%s' % (settings.LOGIN_URL,
                                 urlencode({'next': '/otp_admin/'}))
        self.assertRedirects(response, redirect_to)

    def test_otp_admin_with_otp(self):
        device = self.user.totpdevice_set.create()
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()
        response = self.client.get('/otp_admin/')
        self.assertEqual(response.status_code, 200)


class BackupTokensTest(OTPUserMixin, TestCase):
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


class PhoneSetupTest(OTPUserMixin, TestCase):
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
                               'setup-number': '+123456789',
                               'setup-method': 'call'})
        self.assertContains(response, 'We\'ve sent a token to your phone')
        device = response.context_data['wizard']['form'].device
        fake.return_value.make_call.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid']})

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': totp(device.bin_key)})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'backup')
        self.assertEqual(phones[0].number, '+123456789')
        self.assertEqual(phones[0].key, device.key)


class PhoneDeleteTest(OTPUserMixin, TestCase):
    def setUp(self):
        super(PhoneDeleteTest, self).setUp()
        self.backup = self.user.phonedevice_set.create(name='backup')
        self.default = self.user.phonedevice_set.create(name='default')

    def test_delete(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.backup.pk]))
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(backup_phones(self.user)), [])

    def test_cannot_delete_default(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.default.pk]))
        self.assertContains(response, 'was not found', status_code=404)


class DisableTest(OTPUserMixin, TestCase):
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


class TwilioGatewayTest(TestCase):
    def test_call_app(self):
        url = reverse('two_factor:twilio_call_app', args=['123456'])
        response = self.client.get(url)
        self.assertEqual(response.content,
                         b'<?xml version="1.0" encoding="UTF-8" ?><Response>'
                         b'<Say language="en">Hi, this is testserver calling. '
                         b'Please enter the following code on your screen: 1. '
                         b'2. 3. 4. 5. 6. Repeat: 1. 2. 3. 4. 5. 6.</Say>'
                         b'</Response>')

        # there is a en-gb voice
        response = self.client.get('%s?%s' % (url, urlencode({'locale': 'en-gb'})))
        self.assertContains(response, '<Say language="en-gb">')

        # there is no nl voice
        response = self.client.get('%s?%s' % (url, urlencode({'locale': 'nl-nl'})))
        self.assertContains(response, '<Say language="en">')

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.TwilioRestClient')
    def test_gateway(self, client):
        twilio = Twilio()
        client.assert_called_with('SID', 'TOKEN')

        twilio.make_call(device=Mock(number='+123'), token='654321')
        client.return_value.calls.create.assert_called_with(
            from_='+456', to='+123', method='GET',
            url='http://testserver/twilio/inbound/two_factor/654321/?locale=en-us')

        twilio.send_sms(device=Mock(number='+123'), token='654321')
        client.return_value.sms.messages.create.assert_called_with(
            to='+123', body='Your authentication token is 654321', from_='+456')

        client.return_value.calls.create.reset_mock()
        with translation.override('en-gb'):
            twilio.make_call(device=Mock(number='+123'), token='654321')
            client.return_value.calls.create.assert_called_with(
                from_='+456', to='+123', method='GET',
                url='http://testserver/twilio/inbound/two_factor/654321/?locale=en-gb')

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.TwilioRestClient')
    def test_invalid_twilio_language(self, client):
        # This test assumes an invalid twilio voice language being present in
        # the Arabic translation. Might need to create a faux translation when
        # the translation is fixed.

        url = reverse('two_factor:twilio_call_app', args=['123456'])
        with self.assertRaises(NotImplementedError):
            self.client.get('%s?%s' % (url, urlencode({'locale': 'ar'})))

        # make_call doesn't use the voice_language, but it should raise early
        # to ease debugging.
        with self.assertRaises(NotImplementedError):
            twilio = Twilio()
            with translation.override('ar'):
                twilio.make_call(device=Mock(number='+123'), token='654321')


class FakeGatewayTest(TestCase):
    @patch('two_factor.gateways.fake.logger')
    def test_gateway(self, logger):
        fake = Fake()

        fake.make_call(device=Mock(number='+123'), token='654321')
        logger.info.assert_called_with(
            'Fake call to %s: "Your token is: %s"', '+123', '654321')

        fake.send_sms(device=Mock(number='+123'), token='654321')
        logger.info.assert_called_with(
            'Fake SMS to %s: "Your token is: %s"', '+123', '654321')


class PhoneDeviceTest(TestCase):
    def test_verify(self):
        device = PhoneDevice(key=random_hex().decode())
        self.assertFalse(device.verify_token(-1))
        self.assertTrue(device.verify_token(totp(device.bin_key)))

    def test_unicode(self):
        device = PhoneDevice(name='unknown')
        self.assertEqual('unknown (None)', str(device))

        user = User.objects.create_user('bouke')
        device.user = user
        self.assertEqual('unknown (bouke)', str(device))


class UtilsTest(TestCase):
    def test_default_device(self):
        user = User.objects.create_user('bouke')
        self.assertEqual(default_device(user), None)

        user.phonedevice_set.create(name='backup')
        self.assertEqual(default_device(user), None)

        default = user.phonedevice_set.create(name='default')
        self.assertEqual(default_device(user).pk, default.pk)

    def test_backup_phones(self):
        self.assertQuerysetEqual(list(backup_phones(None)),
                                 list(PhoneDevice.objects.none()))

        user = User.objects.create_user('bouke')
        user.phonedevice_set.create(name='default')
        backup = user.phonedevice_set.create(name='backup')
        phones = backup_phones(user)

        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].pk, backup.pk)
