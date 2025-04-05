import re
from unittest import mock

from django.conf import settings
from django.core import mail
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_email.models import EmailDevice

from .utils import UserMixin, default_device


class EmailTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.login_user()

    def test_have_email_method(self):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'welcome'})
        self.assertContains(
            response,
            '<input type="radio" name="method-method" value="email" required id="id_method-method_1">',
            html=True
        )

    @mock.patch('django.db.models.signals.post_save.send')
    @override_settings(OTP_EMAIL_THROTTLE_FACTOR=0)
    def test_setup(self, signals):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')
        self.assertContains(response, 'Email')
        self.assertEqual(len(mail.outbox), 0)

        # Right now, the user does not have a default 2FA device.
        self.assertEqual(default_device(self.user), None)

        # assert that if user email not empty skip email form
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'method',
                                    'method-method': 'email'})
        self.assertContains(response, 'Token:')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertEqual(msg.subject, 'OTP token')

        # assert that if user email empty ask email
        self.user.email = ''
        self.user.save()
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'method',
                                    'method-method': 'email'})
        self.assertContains(response, 'Email address:')

        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'email'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'email': ['This field is required.']})

        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'email',
                                    'email-email': 'bouke'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'email': ['Enter a valid email address.']})

        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'email',
                                          'email-email': 'bouke@example.com'})

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertEqual(['bouke@example.com'], msg.to)
        self.assertEqual('OTP token', msg.subject)
        self.assertRegex(msg.body, r'[0-9]{6}')

        token = re.findall(r'[0-9]{6}', msg.body)[0]

        # assert that tokens are verified
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        # submitting correct token should finish the setup
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        # Now the user has a default 2FA device that is an EmailDevice.
        device = default_device(self.user)
        self.assertIsNotNone(device)
        self.assertIsInstance(device, EmailDevice)

        # Check save user on success.
        self.assertIn(
            mock.call(created=False,
                      instance=self.user,
                      raw=mock.ANY,
                      sender=self.User,
                      update_fields=frozenset({'email'}),
                      using=mock.ANY),
            signals.mock_calls)

    @override_settings(OTP_EMAIL_SUBJECT='Test subject')
    @override_settings(OTP_EMAIL_BODY_TEMPLATE='Test text')
    def test_subject_and_text(self):
        self.user.emaildevice_set.create(name='default')
        response = self.client.post(reverse('two_factor:login'),
                                    {'auth-username': 'bouke@example.com',
                                     'auth-password': 'secret',
                                     'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertIn('Test subject', msg.subject)
        self.assertIn('Test text', msg.body)

    @override_settings(TWO_FACTOR_EMAIL_HTML=False)
    def test_no_alternative(self):
        self.user.emaildevice_set.create(name='default')
        response = self.client.post(reverse('two_factor:login'),
                                    {'auth-username': 'bouke@example.com',
                                     'auth-password': 'secret',
                                     'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertEqual(len(msg.alternatives), 0)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    @override_settings(OTP_EMAIL_THROTTLE_FACTOR=0)
    def test_login(self, mock_signal):
        device = self.user.emaildevice_set.create(name='default', email='bouke@example.com')

        response = self.client.post(reverse('two_factor:login'),
                                    {'auth-username': 'bouke@example.com',
                                     'auth-password': 'secret',
                                     'login_view-current_step': 'auth'})

        self.assertContains(response, 'Token:')
        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertIn('OTP token', msg.subject)
        self.assertEqual(msg.recipients(), ['bouke@example.com'])
        self.assertEqual(msg.from_email, 'test@test.org')

        response = self.client.post(reverse('two_factor:login'),
                                    {'token-otp_token': 'a23456',
                                     'login_view-current_step': 'token'})

        self.assertEqual(
            response.context_data['wizard']['form'].errors['otp_token'],
            ['Enter a valid value.']
        )

        token = re.findall(r'[0-9]{6}', msg.body)[0]
        response = self.client.post(reverse('two_factor:login'),
                                    {'token-otp_token': token,
                                     'login_view-current_step': 'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY,
                                       user=self.user, device=device)

    def test_device_without_email(self):
        self.user.emaildevice_set.create(name="default")
        response = self.client.get(reverse("two_factor:profile"))
        self.assertNotContains(
            response,
            "AttributeError: 'NoneType' object has no attribute 'split'",
        )

    def test_device_user_without_email(self):
        self.user.email = ""
        self.user.save()
        self.test_device_without_email()


    def test_default_device_returns_only_confirmed(self):
        """Test that default_device(user) returns only confirmed devices."""
        # Create a confirmed default device
        confirmed_device = self.user.emaildevice_set.create(
            name='default',
            email='confirmed@example.com',
            confirmed=True
        )
        self.user.emaildevice_set.create(
            name='default',
            email='unconfirmed@example.com',
            confirmed=False
        )

        # Verify default_device only returns the confirmed device
        device = default_device(self.user)
        self.assertIsNotNone(device, "A confirmed default device should be returned")
        self.assertEqual(device.pk, confirmed_device.pk,
                         "The returned device should be the confirmed one")
        self.assertTrue(device.confirmed,
                        "The returned device should be confirmed")

    def test_default_device_includes_unconfirmed_when_flag_false(self):
        """Test that default_device(user, confirmed=False) returns unconfirmed devices."""
        # Create an unconfirmed default device only.
        unconfirmed_device = self.user.emaildevice_set.create(
            name="default",
            email="unconfirmed@example.com",
            confirmed=False
        )

        # When using the default (confirmed=True), no device should be returned because
        # the only default device is unconfirmed.
        self.assertIsNone(default_device(self.user),
                          "No device should be returned when only unconfirmed devices exist")

        # When passing confirmed=False, it should return the unconfirmed device.
        device = default_device(self.user, confirmed=False)
        self.assertIsNotNone(device)
        self.assertFalse(device.confirmed)
        self.assertEqual(device.pk, unconfirmed_device.pk)

    @override_settings(OTP_EMAIL_THROTTLE_FACTOR=0)
    def test_confirmed_email(self):
        # Setup
        self.client.post(reverse('two_factor:setup'),
                         data={'setup_view-current_step': 'welcome'})
        self.assertIsNone(
            default_device(self.user, confirmed=False),
            "User should not have a default device before setup"
        )
        # user has email, so we skip the email form.
        method_response = self.client.post(
            reverse('two_factor:setup'),
            data={
                'setup_view-current_step': 'method',
                'method-method': 'email'
            }
        )
        self.assertEqual(method_response.status_code, 200, "Method selection should succeed")

        # Now we look at the device, it should be unconfirmed.
        device = default_device(self.user, confirmed=False)
        self.assertIsNotNone(device)
        self.assertIsInstance(device, EmailDevice)
        self.assertFalse(device.confirmed)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        token = re.findall(r'[0-9]{6}', msg.body)[0]

        # Confirm the email
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'validation',
                                          'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))
        # Now the user has a confirmed default 2FA device that is an EmailDevice.
        device.refresh_from_db()
        self.assertTrue(device.confirmed, "Device should be confirmed after validation")

    @override_settings(OTP_EMAIL_THROTTLE_FACTOR=0)
    def test_unconfirmed_email(self):
        # Setup
        self.client.post(reverse('two_factor:setup'),
                         data={'setup_view-current_step': 'welcome'})
        # right now, the user does not have a default 2FA device.
        self.assertEqual(default_device(self.user), None)
        # user has email, so we skip the email form.
        self.client.post(reverse('two_factor:setup'),
                         data={'setup_view-current_step': 'method',
                               'method-method': 'email'})
        # Now we look at the device, it should be unconfirmed.
        device = default_device(self.user, confirmed=False)
        self.assertIsNotNone(device)
        self.assertIsInstance(device, EmailDevice)
        self.assertFalse(device.confirmed)
