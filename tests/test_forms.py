from django.test import TestCase

from two_factor.forms import AuthenticationTokenForm, TOTPDeviceForm

from .utils import UserMixin


class FormTests(TestCase):
    def test_auth_token_form(self):
        form = AuthenticationTokenForm(None, None, data={'otp_token': '005428'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['otp_token'], '005428')


class TOTPDeviceFormSaveTests(UserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    def _form(self):
        return TOTPDeviceForm(key='1234567890abcdef', user=self.user)

    def test_defaults_to_default_name(self):
        self.assertEqual(self._form().save().name, 'default')

    def test_saves_with_given_name(self):
        self.assertEqual(self._form().save(name='sms').name, 'sms')
