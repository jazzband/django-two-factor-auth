import json
from unittest import mock

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp

from two_factor.models import random_hex_str

from .utils import UserMixin


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

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_valid_login(self, mock_signal):
        self.create_user()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        # No signal should be fired for non-verified user logins.
        self.assertFalse(mock_signal.called)

    def test_valid_login_with_custom_redirect(self):
        redirect_url = reverse('two_factor:setup')
        self.create_user()
        response = self.client.post(
            '%s?%s' % (reverse('two_factor:login'), 'next=' + redirect_url),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_valid_login_with_custom_post_redirect(self):
        redirect_url = reverse('two_factor:setup')
        self.create_user()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth',
                               'next': redirect_url})
        self.assertRedirects(response, redirect_url)

    def test_valid_login_with_redirect_field_name(self):
        redirect_url = reverse('two_factor:setup')
        self.create_user()
        response = self.client.post(
            '%s?%s' % (reverse('custom-field-name-login'), 'next_page=' + redirect_url),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_valid_login_with_allowed_external_redirect(self):
        redirect_url = 'https://test.allowed-success-url.com'
        self.create_user()
        response = self.client.post(
            '%s?%s' % (reverse('custom-allowed-success-url-login'), 'next=' + redirect_url),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url, fetch_redirect_response=False)

    def test_valid_login_with_disallowed_external_redirect(self):
        redirect_url = 'https://test.disallowed-success-url.com'
        self.create_user()
        response = self.client.post(
            '%s?%s' % (reverse('custom-allowed-success-url-login'), 'next=' + redirect_url),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, reverse('two_factor:profile'), fetch_redirect_response=False)

    @mock.patch('two_factor.views.core.time')
    def test_valid_login_primary_key_stored(self, mock_time):
        mock_time.time.return_value = 12345.12
        user = self.create_user()
        user.totpdevice_set.create(name='default',
                                   key=random_hex_str())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(self.client.session['wizard_login_view']['user_pk'], str(user.pk))
        self.assertEqual(
            self.client.session['wizard_login_view']['user_backend'],
            'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session['wizard_login_view']['authentication_time'], 12345)

    @mock.patch('two_factor.views.core.time')
    def test_valid_login_post_auth_session_clear_of_form_data(self, mock_time):
        mock_time.time.return_value = 12345.12
        user = self.create_user()
        user.totpdevice_set.create(name='default',
                                   key=random_hex_str())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(self.client.session['wizard_login_view']['user_pk'], str(user.pk))
        self.assertEqual(self.client.session['wizard_login_view']['step'], 'token')
        self.assertEqual(self.client.session['wizard_login_view']['step_data'], {'auth': None})
        self.assertEqual(self.client.session['wizard_login_view']['step_files'], {'auth': {}})
        self.assertEqual(self.client.session['wizard_login_view']['validated_step_data'], {})

    @mock.patch('two_factor.views.core.logger')
    @mock.patch('two_factor.views.core.time')
    def test_valid_login_expired(self, mock_time, mock_logger):
        mock_time.time.return_value = 12345.12
        user = self.create_user()
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex_str())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(self.client.session['wizard_login_view']['user_pk'], str(user.pk))
        self.assertEqual(
            self.client.session['wizard_login_view']['user_backend'],
            'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session['wizard_login_view']['authentication_time'], 12345)

        mock_time.time.return_value = 20345.12

        response = self._post({'token-otp_token': totp(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Token:')
        self.assertContains(response, 'Password:')
        self.assertContains(response, 'Your session has timed out. Please login again.')

        # Check that a message was logged.
        mock_logger.info.assert_called_with(
            "User's authentication flow has timed out. The user "
            "has been redirected to the initial auth form.")

    @override_settings(TWO_FACTOR_LOGIN_TIMEOUT=0)
    @mock.patch('two_factor.views.core.time')
    def test_valid_login_no_timeout(self, mock_time):
        mock_time.time.return_value = 12345.12
        user = self.create_user()
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex_str())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(self.client.session['wizard_login_view']['user_pk'], str(user.pk))
        self.assertEqual(
            self.client.session['wizard_login_view']['user_backend'],
            'django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.session['wizard_login_view']['authentication_time'], 12345)

        mock_time.time.return_value = 20345.12

        response = self._post({'token-otp_token': totp(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))

    def test_valid_login_with_redirect_authenticated_user(self):
        user = self.create_user()
        response = self.client.get(
            reverse('custom-redirect-authenticated-user-login')
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_login(user)
        response = self.client.get(
            reverse('custom-redirect-authenticated-user-login')
        )
        self.assertRedirects(response, reverse('two_factor:profile'))

    def test_valid_login_with_redirect_authenticated_user_loop(self):
        redirect_url = reverse('custom-redirect-authenticated-user-login')
        user = self.create_user()
        self.client.force_login(user)
        with self.assertRaises(ValueError):
            self.client.get(
                '%s?%s' % (reverse('custom-redirect-authenticated-user-login'), 'next=' + redirect_url),
            )

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_with_generator(self, mock_signal):
        user = self.create_user()
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex_str())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': '123456',
                               'login_view-current_step': 'token'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': ['Invalid token. Please make sure you '
                                      'have entered it correctly.']})

        # reset throttle because we're not testing that
        device.throttle_reset()

        response = self._post({'token-otp_token': totp(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY, user=user, device=device)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_throttle_with_generator(self, mock_signal):
        user = self.create_user()
        device = user.totpdevice_set.create(name='default',
                                            key=random_hex_str())

        self._post({'auth-username': 'bouke@example.com',
                    'auth-password': 'secret',
                    'login_view-current_step': 'auth'})

        # throttle device
        device.throttle_increment()

        response = self._post({'token-otp_token': totp(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': ['Invalid token. Please make sure you '
                                      'have entered it correctly.']})

    @mock.patch('two_factor.gateways.fake.Fake')
    @mock.patch('two_factor.views.core.signals.user_verified.send')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_with_backup_phone(self, mock_signal, fake):
        user = self.create_user()
        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                user.totpdevice_set.create(name='default', key=random_hex_str(),
                                           digits=no_digits)
                device = user.phonedevice_set.create(name='backup', number='+31101234567',
                                                     method='sms',
                                                     key=random_hex_str())

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
            self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
            self.assertEqual(device.persistent_id,
                             self.client.session.get(DEVICE_ID_SESSION_KEY))

            # Check that the signal was fired.
            mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY, user=user, device=device)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_with_backup_token(self, mock_signal):
        user = self.create_user()
        user.totpdevice_set.create(name='default', key=random_hex_str())
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
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': ['Invalid token. Please make sure you '
                                      'have entered it correctly.']})
        # static devices are throttled
        device.throttle_reset()

        # Valid token should be accepted.
        response = self._post({'backup-otp_token': 'abcdef123',
                               'login_view-current_step': 'backup'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY, user=user, device=device)

    @mock.patch('two_factor.views.utils.logger')
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

    @mock.patch('two_factor.views.utils.logger')
    def test_login_different_user_on_existing_session(self, mock_logger):
        """
        This test reproduces the issue where a user is logged in and a different user
        attempts to login.
        """
        self.create_user()
        self.create_user(username='vedran@example.com')

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        response = self._post({'auth-username': 'vedran@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

    def test_missing_management_data(self):
        # missing management data
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret'})

        # view should return HTTP 400 Bad Request
        self.assertEqual(response.status_code, 400)

    def test_no_password_in_session(self):
        self.create_user()
        self.enable_otp()

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        session_contents = json.dumps(list(self.client.session.items()))

        self.assertNotIn('secret', session_contents)


class BackupTokensTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
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
