import json
from importlib import import_module
from time import sleep
from unittest import mock, skipUnless

from django.conf import settings
from django.core.signing import BadSignature
from django.shortcuts import resolve_url
from django.test import RequestFactory, TestCase
from django.test.utils import modify_settings, override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
from django_otp.util import random_hex
from freezegun import freeze_time

from two_factor.views.core import LoginView

from .utils import UserMixin, totp_str

try:
    from django.contrib.auth.middleware import LoginRequiredMiddleware  # NOQA
    has_login_required_middleware = True
except ImportError:
    # Django < 5.1
    has_login_required_middleware = False


class LoginTest(UserMixin, TestCase):
    def _post(self, data=None):
        return self.client.post(reverse('two_factor:login'), data=data)

    def test_get_to_login(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertContains(response, 'Password:')

    @skipUnless(has_login_required_middleware, 'LoginRequiredMiddleware needs Django 5.1+')
    @modify_settings(
        MIDDLEWARE={'append': 'django.contrib.auth.middleware.LoginRequiredMiddleware'}
    )
    def test_get_to_login_with_loginrequiredmiddleware(self):
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

    def test_valid_login_non_class_based_redirect(self):
        redirect_url = reverse('plain')
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
                                   key=random_hex())

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
                                   key=random_hex())

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
                                            key=random_hex())

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

        response = self._post({'token-otp_token': totp_str(device.bin_key),
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
                                            key=random_hex())

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

        response = self._post({'token-otp_token': totp_str(device.bin_key),
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
                                            key=random_hex())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'autofocus="autofocus"')
        self.assertContains(response, 'pattern="[0-9]*"')
        self.assertContains(response, 'autocomplete="one-time-code"')

        response = self._post({'token-otp_token': '123456',
                               'login_view-current_step': 'token'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': ['Invalid token. Please make sure you '
                                      'have entered it correctly.']})

        # reset throttle because we're not testing that
        device.throttle_reset()

        response = self._post({'token-otp_token': totp_str(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY, user=user, device=device)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    @override_settings(OTP_TOTP_THROTTLE_FACTOR=10)
    def test_throttle_with_generator(self, mock_signal):
        with freeze_time("2023-01-01") as frozen_time:
            user = self.create_user()
            device = user.totpdevice_set.create(name='default',
                                                key=random_hex())

            self._post({'auth-username': 'bouke@example.com',
                        'auth-password': 'secret',
                        'login_view-current_step': 'auth'})

            # throttle device
            device.throttle_increment()

            response = self._post({'token-otp_token': totp_str(device.bin_key),
                                   'login_view-current_step': 'token'})
            self.assertEqual(response.context_data['wizard']['form'].errors,
                             {'__all__': ['Verification temporarily disabled because of 1 failed attempt, please '
                                          'try again soon.']})

            # Successful login after waiting for the appropriate time
            frozen_time.tick(10)
            response = self._post({'token-otp_token': totp_str(device.bin_key),
                                   'login_view-current_step': 'token'})
            self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    @override_settings(
        TWO_FACTOR_PHONE_THROTTLE_FACTOR=10,
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake'
    )
    def test_throttle_with_phone_sms(self, mock_signal):
        with freeze_time("2023-01-01") as frozen_time:
            user = self.create_user()
            device = user.phonedevice_set.create(name='default', number='+31101234567', method='sms', key=random_hex())

            self._post({'auth-username': 'bouke@example.com',
                        'auth-password': 'secret',
                        'login_view-current_step': 'auth'})

            # throttle device
            device.throttle_increment()

            response = self._post({'token-otp_token': totp_str(device.bin_key),
                                   'login_view-current_step': 'token'})
            self.assertEqual(response.context_data['wizard']['form'].errors,
                             {'__all__': ['Verification temporarily disabled because of 1 failed attempt, please '
                                          'try again soon.']})

            # Successful login after waiting for the appropriate time
            frozen_time.tick(10)
            response = self._post({'token-otp_token': totp_str(device.bin_key),
                                   'login_view-current_step': 'token'})
            self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

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
                user.totpdevice_set.create(name='default', key=random_hex(),
                                           digits=no_digits)
                device = user.phonedevice_set.create(name='backup', number='+31101234567',
                                                     method='sms',
                                                     key=random_hex())

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

                test_call_kwargs = fake.return_value.send_sms.call_args[1]
                self.assertEqual(test_call_kwargs['device'], device)
                self.assertIn(test_call_kwargs['token'],
                              [str(totp(device.bin_key, digits=no_digits, drift=i)).zfill(no_digits)
                               for i in [-1, 0]])

                # Ask for phone challenge
                device.method = 'call'
                device.save()
                response = self._post({'auth-username': 'bouke@example.com',
                                       'auth-password': 'secret',
                                       'challenge_device': device.persistent_id})
                self.assertContains(response, 'We are calling your phone right now')

                test_call_kwargs = fake.return_value.make_call.call_args[1]
                self.assertEqual(test_call_kwargs['device'], device)
                self.assertIn(test_call_kwargs['token'],
                              [str(totp(device.bin_key, digits=no_digits, drift=i)).zfill(no_digits)
                               for i in [-1, 0]])

            # Valid token should be accepted.
            response = self._post({'token-otp_token': totp_str(device.bin_key),
                                   'login_view-current_step': 'token'})
            self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
            self.assertEqual(device.persistent_id,
                             self.client.session.get(DEVICE_ID_SESSION_KEY))

            # Check that the signal was fired.
            mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY, user=user, device=device)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_with_backup_token(self, mock_signal):
        user = self.create_user()
        user.totpdevice_set.create(name='default', key=random_hex())
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

    def test_totp_token_does_not_impact_backup_token(self):
        """
        Ensures that successfully authenticating with a TOTP token does not
        inadvertently increase the throttling count of the backup token device.

        Addresses issue #473, where correct TOTP token usage was unintentionally
        affecting the throttling count of backup tokens, potentially leading to
        their invalidation.
        """
        user = self.create_user()
        backup_device = user.staticdevice_set.create(name='backup')
        backup_device.token_set.create(token='abcdef123')
        totp_device = user.totpdevice_set.create(name='default', key=random_hex())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        backup_device.refresh_from_db()
        self.assertEqual(backup_device.throttling_failure_count, 0)
        response = self._post({'token-otp_token': totp_str(totp_device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))

        backup_device.refresh_from_db()
        self.assertEqual(backup_device.throttling_failure_count, 0)

    def test_wrong_token_does_not_affect_other_device_throttling(self):
        """
        Tests that entering an incorrect backup token increases the throttling count
        of the backup device, but does not affect the TOTP device's throttling count (and other way around).

        This addresses issue #473 where TOTP token submissions were incorrectly
        impacting the backup device's throttling count.
        """
        # Setup: Create a user, backup device, and TOTP device.
        user = self.create_user()
        backup_device = user.staticdevice_set.create(user=user, name='backup')
        backup_token = 'abcdef123'
        backup_device.token_set.create(token=backup_token)
        totp_device = user.totpdevice_set.create(
            user=user, name='default', confirmed=True,
            key=random_hex()
        )

        # Simulate login process: username and password step.
        response = self._post({
            'auth-username': user.get_username(),
            'auth-password': 'secret',
            'login_view-current_step': 'auth',
        })
        self.assertContains(response, 'Token:')

        # Attempt login with incorrect backup token and check response.
        response = self._post({
            'backup-otp_token': 'WRONG',
            'login_view-current_step': 'backup',
        })
        expected_error = 'Invalid token. Please make sure you have entered it correctly.'
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': [expected_error]})

        # Verify that incorrect backup token submission throttles backup device.
        backup_device.refresh_from_db()
        self.assertEqual(backup_device.throttling_failure_count, 1)

        # Ensure TOTP device is not affected by the incorrect backup token submission.
        totp_device.refresh_from_db()
        self.assertEqual(totp_device.throttling_failure_count, 0)

        # Attempt login with incorrect TOTP token and check response.
        response = self._post({
            'token-otp_token': "123456",
            'login_view-current_step': 'token'
        })
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': [expected_error]})

        # Backup device's throttling count should remain unchanged after TOTP token submission.
        backup_device.refresh_from_db()
        self.assertEqual(backup_device.throttling_failure_count, 1)

        # Incorrect TOTP token submission should throttle TOTP device.
        totp_device.refresh_from_db()
        self.assertEqual(totp_device.throttling_failure_count, 1)

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

    def test_login_different_user_with_otp_on_existing_session(self):
        self.create_user()
        vedran_user = self.create_user(username='vedran@example.com')
        device = vedran_user.totpdevice_set.create(name='default', key=random_hex())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        response = self._post({'auth-username': 'vedran@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')
        response = self._post({'token-otp_token': totp_str(device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.assertRedirects(response,
                             resolve_url(settings.LOGIN_REDIRECT_URL))

    def test_login_view_is_step_visible(self):
        request = RequestFactory().get(reverse('login'))
        engine = import_module(settings.SESSION_ENGINE)
        request.session = engine.SessionStore(None)
        login_view = LoginView(**LoginView.get_initkwargs())
        login_view.setup(request)
        login_view.dispatch(request)

        # Initially, any step is visible
        for step, form_class in login_view.form_list.items():
            self.assertTrue(login_view.is_step_visible(step, form_class))
        login_view.storage.validated_step_data['auth'] = {'username': 'joe', 'password': 'any'}
        login_view.storage.validated_step_data['token'] = {'otp_token': '123456'}
        # Once token was entered, the token step is no longer visible
        for step, form_class in login_view.form_list.items():
            if step == 'token':
                self.assertFalse(login_view.is_step_visible(step, form_class))
            else:
                self.assertTrue(login_view.is_step_visible(step, form_class))


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

    def test_no_cancel_url(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('cancel_url', response.context.keys())

    @override_settings(LOGOUT_REDIRECT_URL='custom-field-name-login')
    def test_cancel_redirects_to_logout_redirect_url(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cancel_url'], reverse('custom-field-name-login'))

    @override_settings(LOGOUT_URL='custom-field-name-login')
    def test_logout_url_warning_raised(self):
        with self.assertWarns(DeprecationWarning):
            response = self.client.get(reverse('two_factor:login'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cancel_url'], reverse('custom-field-name-login'))


@override_settings(ROOT_URLCONF='tests.urls_admin')
class RememberLoginTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.device = self.user.totpdevice_set.create(name='default', key=random_hex())

    def _post(self, data=None):
        return self.client.post(reverse('two_factor:login'), data=data)

    def set_invalid_remember_cookie(self):
        for cookie in self.client.cookies:
            if cookie.startswith("remember-cookie_"):
                self._restore_remember_cookie_data = dict(name=cookie, value=self.client.cookies[cookie].value)
                self.client.cookies[cookie] = self.client.cookies[cookie].value[:-5] + "0" * 5  # an invalid key

    def restore_remember_cookie(self):
        self.client.cookies[self._restore_remember_cookie_data['name']] = self._restore_remember_cookie_data['value']

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60)
    def test_with_remember(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': totp_str(self.device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.assertRedirects(response, reverse('two_factor:profile'), fetch_redirect_response=False)
        self.assertEqual(1, len([cookie for cookie in response.cookies if cookie.startswith('remember-cookie_')]))

        # Logout
        self.client.post(reverse('logout'))
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

        # Login without token
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})

        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 200)

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 3)
    def test_with_remember_label_3_min(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'ask again on this device for 3 minutes')

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60 * 4)
    def test_with_remember_label_4_hours(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'ask again on this device for 4 hours')

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60 * 24 * 5)
    def test_with_remember_label_5_days(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'ask again on this device for 5 days')

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60)
    def test_without_remember(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': totp_str(self.device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertEqual(0, len([cookie for cookie in response.cookies if cookie.startswith('remember-cookie_')]))

        # Logout
        self.client.post(reverse('logout'))
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})

        self.assertContains(response, 'Token:')

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=1)
    def test_expired(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': totp_str(self.device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.assertEqual(1, len([cookie for cookie in response.cookies if cookie.startswith('remember-cookie_')]))

        # Logout
        self.client.post(reverse('logout'))
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

        # Wait to expire
        sleep(1)

        # Login but expired remember cookie
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})

        self.assertContains(response, 'Token:')
        self.assertFalse(any(
            key.startswith('remember-cookie_') and cookie.value
            for key, cookie in self.client.cookies.items()
        ))

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60)
    def test_wrong_signature(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': totp_str(self.device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.assertEqual(1, len([cookie for cookie in response.cookies if cookie.startswith('remember-cookie_')]))

        # Logout
        self.client.post(reverse('logout'))
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

        self.set_invalid_remember_cookie()

        # Login but expire remember cookie
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})

        self.assertContains(response, 'Token:')

    @override_settings(
        TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60,
        OTP_HOTP_THROTTLE_FACTOR=60 * 60,
        OTP_TOTP_THROTTLE_FACTOR=60 * 60,
    )
    def test_remember_token_throttling(self):
        # Login
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        # Enter token
        response = self._post({'token-otp_token': totp_str(self.device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.assertEqual(1, len([cookie for cookie in response.cookies if cookie.startswith('remember-cookie_')]))

        # Logout
        self.client.post(reverse('logout'))

        # Login having an invalid remember cookie
        self.set_invalid_remember_cookie()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        # Login with valid remember cookie but throttled
        self.client = self.client_class()
        self.restore_remember_cookie()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        # Reset throttling
        self.device.throttle_reset()

        # Login with valid remember cookie
        self.client = self.client_class()
        self.restore_remember_cookie()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, reverse(settings.LOGIN_REDIRECT_URL), fetch_redirect_response=False)

    @mock.patch('two_factor.gateways.fake.Fake')
    @mock.patch('two_factor.views.core.signals.user_verified.send')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60,
    )
    def test_phonedevice_with_remember_cookie(self, mock_signal, fake):
        self.user.totpdevice_set.first().delete()
        device = self.user.phonedevice_set.create(name='default', number='+31101234567', method='sms')

        # Ask for SMS challenge
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'We sent you a text message')

        test_call_kwargs = fake.return_value.send_sms.call_args[1]
        self.assertEqual(test_call_kwargs['device'], device)

        # Valid token should be accepted.
        response = self._post({'token-otp_token': totp_str(device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        # Logout
        self.client.post(reverse('logout'))

        # Ask for SMS challenge
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})

        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

    @override_settings(TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60)
    def test_remember_cookie_with_device_without_throttle(self):
        self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})

        self._post({'token-otp_token': totp_str(self.device.bin_key),
                               'login_view-current_step': 'token',
                               'token-remember': 'on'})
        self.client.post(reverse('logout'))

        # mock device_for_user
        with mock.patch("two_factor.views.core.devices_for_user") as devices_for_user_mock, \
                mock.patch("two_factor.views.core.validate_remember_device_cookie") as validate_mock:
            device_mock = mock.Mock(spec=["verify_is_allowed", "persistent_id", "user_id"])
            device_mock.persistent_id = 1
            device_mock.verify_is_allowed.return_value = [True, {}]
            devices_for_user_mock.return_value = [device_mock]
            validate_mock.return_value = True
            response = self._post({'auth-username': 'bouke@example.com',
                                   'auth-password': 'secret',
                                   'login_view-current_step': 'auth'})
            self.assertRedirects(response, reverse(settings.LOGIN_REDIRECT_URL), fetch_redirect_response=False)
            self.client.post(reverse('logout'))
            validate_mock.side_effect = BadSignature()
            response = self._post({'auth-username': 'bouke@example.com',
                                   'auth-password': 'secret',
                                   'login_view-current_step': 'auth'})
            self.assertContains(response, 'Token:')
