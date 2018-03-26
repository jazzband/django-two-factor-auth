# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.core import mail
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
from django_otp.util import random_hex

from .utils import UserMixin

try:
    from unittest import mock
except ImportError:
    import mock


class EmailTest(UserMixin, TestCase):
    def setUp(self):
        super(EmailTest, self).setUp()
        self.user = self.create_user()
        self.login_user()

    @override_settings(TWO_FACTOR_EMAIL_ALLOW=False)
    def test_email_allow_false(self):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step':'welcome'})
        self.assertNotContains(response, 'Email message')

    @override_settings(EMAIL_BACKEND=None)
    def test_email_allow_false(self):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step':'welcome'})
        self.assertNotContains(response, 'Email message')

    @override_settings(DEFAULT_FROM_EMAIL=None)
    def test_email_allow_false(self):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step':'welcome'})
        self.assertNotContains(response, 'Email message')

    def test_have_email_method(self):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Email message')

    @mock.patch('django.db.models.signals.post_save.send')
    def test_setup(self, signals):
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step':'welcome'})
        self.assertContains(response, 'Method:')
        self.assertContains(response, 'Email message')

        # assert that if user email not empty skip email form
        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'method',
                                    'method-method': 'email'})
        self.assertContains(response, 'Token:')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)

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
                         {'email':['This field is required.']})

        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step': 'email',
                                    'email-email': 'bouke'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'email':['Enter a valid email address.']})

        response = self.client.post(reverse('two_factor:setup'),
                                    data={'setup_view-current_step':'email',
                                          'email-email':'bouke@example.com'})

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertIn('bouke@example.com', msg.to)
        self.assertIn('Authentication token email', msg.subject)
        self.assertIn('Authentication token for user', msg.body)
        self.assertRegex(msg.body, r'[0-9]{6}')
        self.assertRegex(msg.alternatives[0][0], r'[0-9]{6}')
        self.assertIn(str(self.user), msg.body)
        self.assertIn(str(self.user), msg.alternatives[0][0])

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

        # Check save user on success.
        self.assertIn(
            mock.call(created=False,
                      instance=self.user,
                      raw=mock.ANY,
                      sender=self.User,
                      update_fields=frozenset({'email'}),
                      using=mock.ANY),
            signals.mock_calls)

    @override_settings(TWO_FACTOR_EMAIL_SUBJECT='Test subject')
    @override_settings(TWO_FACTOR_EMAIL_TEXT='Test text')
    def test_subject_and_text(self):
        device = self.user.emaildevice_set.create(name='default',
                                                  key=random_hex().decode())
        response = self.client.post(reverse('two_factor:login'),
                                    {'auth-username':'bouke@example.com',
                                     'auth-password':'secret',
                                     'login_view-current_step':'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertIn('Test subject', msg.subject)
        self.assertIn('Test text', msg.body)

    @override_settings(TWO_FACTOR_EMAIL_HTML=False)
    def test_no_alternative(self):
        device = self.user.emaildevice_set.create(name='default',
                                                  key=random_hex().decode())
        response = self.client.post(reverse('two_factor:login'),
                                    {'auth-username':'bouke@example.com',
                                     'auth-password':'secret',
                                     'login_view-current_step':'auth'})
        self.assertContains(response, 'Token:')

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertEqual(len(msg.alternatives), 0)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_login(self, mock_signal):
        device = self.user.emaildevice_set.create(name='default',
                                                  key=random_hex().decode())
        token = totp(device.bin_key)

        response = self.client.post(reverse('two_factor:login'),
                                    {'auth-username':'bouke@example.com',
                                     'auth-password':'secret',
                                     'login_view-current_step':'auth'})

        self.assertContains(response, 'Token:')
        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox.pop(0)
        self.assertIn('Authentication token email', msg.subject)
        self.assertIn('Authentication token for user', msg.body)
        self.assertIn(str(self.user), msg.body)
        self.assertIn(str(self.user), msg.alternatives[0][0])
        self.assertIn(str(token), msg.body)
        self.assertIn(str(token), msg.alternatives[0][0])

        response = self.client.post(reverse('two_factor:login'),
                                    {'token-otp_token':'123456',
                                     'login_view-current_step':'token'})

        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__':['Invalid token. Please make sure you '
                                     'have entered it correctly.']})

        response = self.client.post(reverse('two_factor:login'),
                                    {'token-otp_token':token,
                                     'login_view-current_step':'token'})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

        # Check that the signal was fired.
        mock_signal.assert_called_with(sender=mock.ANY, request=mock.ANY,
                                       user=self.user, device=device)
