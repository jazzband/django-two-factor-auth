from unittest import mock

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, reverse_lazy
from django_otp.oath import totp

from two_factor.models import PhoneDevice, random_hex_str
from two_factor.utils import backup_phones
from two_factor.validators import validate_international_phonenumber
from two_factor.views.core import PhoneDeleteView, PhoneSetupView

from .utils import UserMixin


@override_settings(
    TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
    TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
)
class PhoneSetupTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_otp()
        self.login_user()

    def test_form(self):
        response = self.client.get(reverse('two_factor:phone_create'))
        self.assertContains(response, 'Number:')

    def _post(self, data=None):
        return self.client.post(reverse('two_factor:phone_create'), data=data)

    @mock.patch('two_factor.gateways.fake.Fake')
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
            device=mock.ANY, token='%06d' % totp(device.bin_key))

        args, kwargs = fake.return_value.make_call.call_args
        submitted_device = kwargs['device']
        self.assertEqual(submitted_device.number, device.number)
        self.assertEqual(submitted_device.key, device.key)
        self.assertEqual(submitted_device.method, device.method)

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid.']})

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': totp(device.bin_key)})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'backup')
        self.assertEqual(phones[0].number.as_e164, '+31101234567')
        self.assertEqual(phones[0].key, device.key)

    @mock.patch('two_factor.gateways.fake.Fake')
    def test_number_validation(self, fake):
        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '123',
                               'setup-method': 'call'})
        self.assertEqual(
            response.context_data['wizard']['form'].errors,
            {'number': [str(validate_international_phonenumber.message)]})

    @mock.patch('formtools.wizard.views.WizardView.get_context_data')
    def test_success_url_as_url(self, get_context_data):
        url = '/account/two_factor/'
        view = PhoneSetupView()
        view.success_url = url

        def return_kwargs(form, **kwargs):
            return kwargs
        get_context_data.side_effect = return_kwargs

        context = view.get_context_data(None)
        self.assertIn('cancel_url', context)
        self.assertEqual(url, context['cancel_url'])

    @mock.patch('formtools.wizard.views.WizardView.get_context_data')
    def test_success_url_as_named_url(self, get_context_data):
        url_name = 'two_factor:profile'
        url = reverse(url_name)
        view = PhoneSetupView()
        view.success_url = url_name

        def return_kwargs(form, **kwargs):
            return kwargs
        get_context_data.side_effect = return_kwargs

        context = view.get_context_data(None)
        self.assertIn('cancel_url', context)
        self.assertEqual(url, context['cancel_url'])

    @mock.patch('formtools.wizard.views.WizardView.get_context_data')
    def test_success_url_as_reverse_lazy(self, get_context_data):
        url_name = 'two_factor:profile'
        url = reverse(url_name)
        view = PhoneSetupView()
        view.success_url = reverse_lazy(url_name)

        def return_kwargs(form, **kwargs):
            return kwargs
        get_context_data.side_effect = return_kwargs

        context = view.get_context_data(None)
        self.assertIn('cancel_url', context)
        self.assertEqual(url, context['cancel_url'])

    def test_missing_management_data(self):
        # missing management data
        response = self._post({'setup-number': '123',
                               'setup-method': 'call'})

        # view should return HTTP 400 Bad Request
        self.assertEqual(response.status_code, 400)


class PhoneDeleteTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.backup = self.user.phonedevice_set.create(name='backup', method='sms', number='+12024561111')
        self.default = self.user.phonedevice_set.create(name='default', method='call', number='+12024561111')
        self.login_user()

    def test_delete(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.backup.pk]))
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(backup_phones(self.user)), [])

    def test_cannot_delete_default(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.default.pk]))
        self.assertContains(response, 'was not found', status_code=404)

    def test_success_url_as_url(self):
        url = '/account/two_factor/'
        view = PhoneDeleteView()
        view.success_url = url
        self.assertEqual(view.get_success_url(), url)

    def test_success_url_as_named_url(self):
        url_name = 'two_factor:profile'
        url = reverse(url_name)
        view = PhoneDeleteView()
        view.success_url = url_name
        self.assertEqual(view.get_success_url(), url)

    def test_success_url_as_reverse_lazy(self):
        url_name = 'two_factor:profile'
        url = reverse(url_name)
        view = PhoneDeleteView()
        view.success_url = reverse_lazy(url_name)
        self.assertEqual(view.get_success_url(), url)


class PhoneDeviceTest(UserMixin, TestCase):
    def test_verify(self):
        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                device = PhoneDevice(key=random_hex_str())
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
                device = PhoneDevice(key=random_hex_str())
                self.assertTrue(device.verify_token(str(totp(device.bin_key, digits=no_digits))))

    def test_unicode(self):
        device = PhoneDevice(name='unknown')
        self.assertEqual('unknown (None)', str(device))

        device.user = self.create_user()
        self.assertEqual('unknown (bouke@example.com)', str(device))
