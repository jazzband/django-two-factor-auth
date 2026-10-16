from django.test import TestCase

from tests.utils import method_registry
from two_factor.forms import AuthenticationTokenForm, MethodForm


class FormTests(TestCase):
    def test_auth_token_form(self):
        form = AuthenticationTokenForm(None, None, data={'otp_token': '005428'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['otp_token'], '005428')

    @method_registry([])
    def test_method_form_empty_registry(self):
        form = MethodForm()
        self.assertEqual(form.fields['method'].choices, [])
        self.assertIsNone(form.fields['method'].initial)
