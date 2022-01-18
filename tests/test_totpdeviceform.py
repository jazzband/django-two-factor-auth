from binascii import unhexlify
from unittest.mock import patch

import django_otp.oath
from django.test import TestCase

from two_factor.forms import TOTPDeviceForm

# Use this as the Unix time for all TOTPs.  It is chosen arbitrarily
# as 3 Jan 2022
TEST_TIME = 1641194517


@patch('django_otp.oath.time', return_value=TEST_TIME)
class TOTPDeviceFormTest(TestCase):
    """
    This class tests how the TOTPDeviceForm validator handles drift between its clock
    and the TOTP device.

    If there is a drift in the range [-tolerance, +tolerance], (tolerance is hardcoded
    to 1), then the TOTP should be accepted.  Outside this range, it should be rejected.
    """

    key = '12345678901234567890'

    def setUp(self):
        super().setUp()
        self.bin_key = unhexlify(TOTPDeviceFormTest.key.encode())
        self.empty_form = TOTPDeviceForm(TOTPDeviceFormTest.key, None)

    def totp_with_offset(self, offset):
        return django_otp.oath.totp(
            self.bin_key, self.empty_form.step,
            self.empty_form.t0, self.empty_form.digits, self.empty_form.drift + offset
        )

    def test_offset_0(self, mock_test):
        device_totp = self.totp_with_offset(0)
        form = TOTPDeviceForm(TOTPDeviceFormTest.key, None, data={'token': device_totp})
        self.assertTrue(form.is_valid())

    def test_offset_minus1(self, mock_test):
        device_totp = self.totp_with_offset(-1)
        form = TOTPDeviceForm(TOTPDeviceFormTest.key, None, data={'token': device_totp})
        self.assertTrue(form.is_valid())

    def test_offset_plus1(self, mock_test):
        device_totp = self.totp_with_offset(1)
        form = TOTPDeviceForm(TOTPDeviceFormTest.key, None, data={'token': device_totp})
        self.assertTrue(form.is_valid())

    def test_offset_minus2(self, mock_test):
        device_totp = self.totp_with_offset(-2)
        form = TOTPDeviceForm(TOTPDeviceFormTest.key, None, data={'token': device_totp})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['token'][0], TOTPDeviceForm.error_messages['invalid_token'])

    def test_offset_plus2(self, mock_test):
        device_totp = self.totp_with_offset(2)
        form = TOTPDeviceForm(TOTPDeviceFormTest.key, None, data={'token': device_totp})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['token'][0], TOTPDeviceForm.error_messages['invalid_token'])
