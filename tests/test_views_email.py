from unittest import mock

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django_otp.oath import totp

from .utils import UserMixin


@override_settings(
    TWO_FACTOR_EMAIL_GATEWAY='two_factor.gateways.fake.Fake'
)
class EmailSetupTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    def test_form(self):
        response = self.client.get(reverse('two_factor:email_create'))
        self.assertContains(response, 'Email:')

    def _post(self, data=None):
        return self.client.post(reverse('two_factor:email_create'), data=data)

    @mock.patch('two_factor.gateways.fake.Fake')
    def test_setup(self, fake):
        response = self._post({'email_setup_view-current_step': 'setup',
                               'setup-email': ''})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'email': ['This field is required.']})

        response = self._post({'email_setup_view-current_step': 'setup',
                               'setup-email': 'test@example.com'})
        self.assertContains(response, 'We\'ve sent a token to your email')
        device = response.context_data['wizard']['form'].device
        fake.return_value.send_email.assert_called_with(
            device=mock.ANY, token='%06d' % totp(device.bin_key))

        args, kwargs = fake.return_value.send_email.call_args
        submitted_device = kwargs['device']
        self.assertEqual(submitted_device.email, device.email)
        self.assertEqual(submitted_device.key, device.key)

        response = self._post({'email_setup_view-current_step': 'validation',
                               'validation-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        response = self._post({'email_setup_view-current_step': 'validation',
                               'validation-token': totp(device.bin_key)})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        emails = self.user.emaildevice_set.all()
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].name, 'backup')
        self.assertEqual(emails[0].email, 'test@example.com')


class EmailDeleteTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.backup = self.user.emaildevice_set.create(name='backup', email='backup@example.com')
        self.default = self.user.emaildevice_set.create(name='default', email='default@example.com')
        self.login_user()

    def test_delete(self):
        response = self.client.post(reverse('two_factor:email_delete',
                                            args=[self.backup.pk]))
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(self.user.emaildevice_set.filter(name='backup')), [])

    def test_cannot_delete_default(self):
        response = self.client.post(reverse('two_factor:email_delete',
                                            args=[self.default.pk]))
        self.assertContains(response, 'was not found', status_code=404)
