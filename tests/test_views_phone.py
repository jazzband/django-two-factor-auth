from unittest import mock

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import resolve_url
from django.template import Context, Template
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, reverse_lazy
from django_otp.oath import totp
from django_otp.util import random_hex
from freezegun import freeze_time

from two_factor.plugins.phonenumber.models import PhoneDevice
from two_factor.plugins.phonenumber.utils import backup_phones
from two_factor.plugins.phonenumber.validators import (
    validate_international_phonenumber,
)
from two_factor.plugins.phonenumber.views import (
    PhoneDeleteView, PhoneSetupView,
)

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

        # When no methods are configured, redirect to login.
        with self.settings(TWO_FACTOR_SMS_GATEWAY=None, TWO_FACTOR_CALL_GATEWAY=None):
            response = self.client.get(reverse('two_factor:phone_create'))
            self.assertRedirects(response, reverse(settings.LOGIN_REDIRECT_URL))

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
        self.assertContains(response, 'autofocus="autofocus"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'autocomplete="one-time-code"')
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

    def test_url_generation(self):
        url_name = 'two_factor:phone_create'
        expected_url = '/account/two_factor/phone/register/'
        self.assertEqual(reverse(url_name), expected_url)


class PhoneDeleteTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.backup = self.user.phonedevice_set.create(name='backup', method='sms', number='+12024561111')
        self.default = self.user.phonedevice_set.create(name='default', method='call', number='+12024561111')
        self.login_user()

    @override_settings(TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake')
    def test_delete(self):
        self.assertEqual(len(backup_phones(self.user)), 1)
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.backup.pk]))
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(backup_phones(self.user), [])

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

    def test_url_generation(self):
        url_name = 'two_factor:phone_delete'
        expected_url = '/account/two_factor/phone/unregister/42/'
        self.assertEqual(reverse(url_name, args=(42,)), expected_url)


class PhoneDeviceTest(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    def test_clean(self):
        device = PhoneDevice(key='xyz', method='sms')
        with self.assertRaises(ValidationError) as ctxt:
            device.full_clean()
        # The 'b' prefix might be a bug to be solved in django_otp.
        self.assertIn("b'xyz' is not valid hex-encoded data.", str(ctxt.exception))

    def test_verify(self):
        for no_digits in (6, 8):
            with freeze_time("2023-01-01") as frozen_time:
                with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                    device = PhoneDevice(key=random_hex(), user=self.user)
                    self.assertFalse(device.verify_token(-1))
                    frozen_time.tick(1)
                    self.assertFalse(device.verify_token('foobar'))
                    frozen_time.tick(10)
                    self.assertTrue(device.verify_token(totp(device.bin_key, digits=no_digits)))

    def test_verify_token_as_string(self):
        """
        The field used to read the token may be a CharField,
        so the PhoneDevice must be able to validate tokens
        read as strings
        """
        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                device = PhoneDevice(key=random_hex(), user=self.user)
                self.assertTrue(device.verify_token(str(totp(device.bin_key, digits=no_digits))))

    def test_unicode(self):
        device = PhoneDevice(name='unknown')
        self.assertEqual('unknown (None)', str(device))

        device.user = self.user
        self.assertEqual('unknown (bouke@example.com)', str(device))

    def test_template_tags(self):
        def render_template(string, context=None):
            context = context or {}
            context = Context(context)
            return Template(string).render(context)

        rendered = render_template(
            '{% load phonenumber %}'
            '{{ number|format_phone_number }}',
            context={'number': '+41524204242'}
        )
        self.assertEqual(rendered, '+41 52 420 42 42')

        rendered = render_template(
            '{% load phonenumber %}'
            '{{ number|mask_phone_number }}',
            context={'number': '+41524204242'}
        )
        self.assertEqual(rendered, '+41*******42')

        device1 = PhoneDevice(method='sms', number='+12024561111')
        device2 = PhoneDevice(method='call', number='+12024561112')
        rendered = render_template(
            '{% load phonenumber %}'
            '{{ device|device_action }}',
            context={'device': device1}
        )
        self.assertEqual(rendered, 'Send text message to +1 ***-***-**11')
        rendered = render_template(
            '{% load phonenumber %}'
            '{{ device|device_action }}',
            context={'device': device2}
        )
        self.assertEqual(rendered, 'Call number +1 ***-***-**12')
