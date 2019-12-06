from django import forms
from django.test import TestCase

from two_factor.validators import validate_international_phonenumber


class ValidatorsTest(TestCase):
    def test_phone_number_validator_on_form_valid(self):
        class TestForm(forms.Form):
            number = forms.CharField(validators=[validate_international_phonenumber])

        form = TestForm({
            'number': '+31101234567',
        })

        self.assertTrue(form.is_valid())

    def test_phone_number_validator_on_form_invalid(self):
        class TestForm(forms.Form):
            number = forms.CharField(validators=[validate_international_phonenumber])

        form = TestForm({
            'number': '+3110123456',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('number', form.errors)

        self.assertEqual(form.errors['number'],
                         [str(validate_international_phonenumber.message)])
