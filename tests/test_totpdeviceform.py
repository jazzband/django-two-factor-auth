from binascii import unhexlify

import django_otp.oath
from django.test import TestCase

from two_factor.forms import TOTPDeviceForm

from .utils import UserMixin

# Use this as the Unix time for all TOTPs.  It is chosen arbitrarily
# as 3 Jan 2022
TEST_TIME = 1641194517


# This class test how the TOTPDeviceForm validator handles drift between its clock
# and the TOTP device.  If there is a drift in the range [-tolerance, +tolerance],
# where tolerance is hardcoded to 1, then the TOTP should be accepted.  Outside this
# range, it should be rejected.
class TOTPDeviceFormTest(UserMixin, TestCase):
    key = '12345678901234567890'

    def fix_time_for_totp(self):
        # Override constructor for TOTP class to set a fixed time.  This will
        # prevent it from calling time(), which would make the unittest unpredictable
        old_TOTP_init = django_otp.oath.TOTP.__init__
        self.old_TOTP_init = old_TOTP_init

        def new_TOTP_init(self, key, step=30, t0=0, digits=6, drift=0):
            old_TOTP_init(self, key, step, t0, digits, drift)
            self.time = TEST_TIME
        django_otp.oath.TOTP.__init__ = new_TOTP_init

    def restore_time_for_totp(self):
        django_otp.oath.TOTP.__init__ = self.old_TOTP_init

    def setUp(self):
        super().setUp()
        self.fix_time_for_totp()
        self.bin_key = unhexlify(TOTPDeviceFormTest.key.encode())
        self.empty_form = TOTPDeviceForm(TOTPDeviceFormTest.key, None)

    def tearDown(self):
        super().tearDown()
        self.restore_time_for_totp()

    def totp_with_offset(self, offset):
        return django_otp.oath.totp(self.bin_key, self.empty_form.step,
            self.empty_form.t0, self.empty_form.digits, self.empty_form.drift + offset)

    def test_offset_0(self):
        device_totp = self.totp_with_offset(0)
        self.form = TOTPDeviceForm(TOTPDeviceFormTest.key, None,
            data={'token': device_totp})
        self.assertTrue(self.form.is_valid())

    def test_offset_minus1(self):
        device_totp = self.totp_with_offset(-1)
        self.form = TOTPDeviceForm(TOTPDeviceFormTest.key, None,
            data={'token': device_totp})
        self.assertTrue(self.form.is_valid())

    def test_offset_plus1(self):
        device_totp = self.totp_with_offset(1)
        self.form = TOTPDeviceForm(TOTPDeviceFormTest.key, None,
            data={'token': device_totp})
        self.assertTrue(self.form.is_valid())

    def test_offset_minus2(self):
        device_totp = self.totp_with_offset(-2)
        self.form = TOTPDeviceForm(TOTPDeviceFormTest.key, None,
            data={'token': device_totp})
        self.assertFalse(self.form.is_valid())

    def test_offset_plus2(self):
        device_totp = self.totp_with_offset(2)
        self.form = TOTPDeviceForm(TOTPDeviceFormTest.key, None,
            data={'token': device_totp})
        self.assertFalse(self.form.is_valid())
