from django.test import TestCase

from two_factor.forms import AuthenticationTokenForm


class FormTests(TestCase):
    def test_auth_token_form(self):
        form = AuthenticationTokenForm(None, None, data={'otp_token': '005428'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['otp_token'], '005428')
