from unittest import mock
from urllib.parse import parse_qsl, urlparse

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django_otp.util import random_hex
from phonenumber_field.phonenumber import PhoneNumber

from two_factor.plugins.phonenumber.models import PhoneDevice
from two_factor.plugins.phonenumber.utils import (
    backup_phones, format_phone_number, mask_phone_number,
)
from two_factor.utils import (
    USER_DEFAULT_DEVICE_ATTR_NAME, default_device, get_otpauth_url,
    totp_digits,
)
from two_factor.views.utils import (
    get_remember_device_cookie, validate_remember_device_cookie,
)

from tests.utils import UserMixin


class UtilsTest(UserMixin, TestCase):
    def test_default_device(self):
        user = self.create_user()
        self.assertEqual(default_device(user), None)

        user.phonedevice_set.create(name='backup', number='+12024561111')
        self.assertEqual(default_device(user), None)

        default = user.phonedevice_set.create(name='default', number='+12024561111')
        self.assertEqual(default_device(user).pk, default.pk)
        self.assertEqual(getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME).pk, default.pk)

        # double check we're actually caching
        PhoneDevice.objects.all().delete()
        self.assertEqual(default_device(user).pk, default.pk)
        self.assertEqual(getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME).pk, default.pk)

    def assertEqualUrl(self, lhs, rhs):
        """
        Asserts whether the URLs are canonically equal.
        """
        lhs = urlparse(lhs)
        rhs = urlparse(rhs)
        self.assertEqual(lhs.scheme, rhs.scheme)
        self.assertEqual(lhs.netloc, rhs.netloc)
        self.assertEqual(lhs.path, rhs.path)
        self.assertEqual(lhs.fragment, rhs.fragment)

        # We used parse_qs before, but as query parameter order became
        # significant with Microsoft Authenticator and possibly other
        # authenticator apps, we've switched to parse_qsl.
        self.assertEqual(parse_qsl(lhs.query), parse_qsl(rhs.query))

    def test_get_totp_digits(self):
        # test that the default is 6 if TWO_FACTOR_TOTP_DIGITS is not set
        self.assertEqual(totp_digits(), 6)

        for no_digits in (6, 8):
            with self.settings(TWO_FACTOR_TOTP_DIGITS=no_digits):
                self.assertEqual(totp_digits(), no_digits)

    def test_wrong_device_hash(self):
        user = mock.Mock()
        user.pk = 123
        user.password = make_password("xx")

        cookie_value = get_remember_device_cookie(
            user=user, otp_device_id="SomeModel/33"
        )
        validation_result = validate_remember_device_cookie(
            cookie=cookie_value,
            user=user,
            otp_device_id="SomeModel/34",
        )
        self.assertFalse(validation_result)


class PhoneUtilsTests(UserMixin, TestCase):
    def test_backup_phones(self):
        gateway = 'two_factor.gateways.fake.Fake'
        user = self.create_user()
        user.phonedevice_set.create(name='default', number='+12024561111')
        backup = user.phonedevice_set.create(name='backup', number='+12024561111')

        parameters = [
            # with_gateway, with_user, expected_output
            (True, True, [backup.pk]),
            (True, False, []),
            (False, True, []),
            (False, False, [])
        ]

        for with_gateway, with_user, expected_output in parameters:
            gateway_param = gateway if with_gateway else None
            user_param = user if with_user else None

            with self.subTest(with_gateway=with_gateway, with_user=with_user), \
                 self.settings(TWO_FACTOR_CALL_GATEWAY=gateway_param):

                phone_pks = [phone.pk for phone in backup_phones(user_param)]
                self.assertEqual(phone_pks, expected_output)

    def test_mask_phone_number(self):
        self.assertEqual(mask_phone_number('+41 524 204 242'), '+41 *** *** *42')
        self.assertEqual(
            mask_phone_number(PhoneNumber.from_string('+41524204242')),
            '+41 ** *** ** 42'
        )

    def test_format_phone_number(self):
        self.assertEqual(format_phone_number('+41524204242'), '+41 52 420 42 42')
        self.assertEqual(
            format_phone_number(PhoneNumber.from_string('+41524204242')),
            '+41 52 420 42 42'
        )