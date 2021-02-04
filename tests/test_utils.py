from unittest import mock
from urllib.parse import parse_qsl, urlparse

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django_otp.util import random_hex

from two_factor.utils import (
    backup_devices, backup_phones, default_device, get_otpauth_url,
    totp_digits,
)
from two_factor.views.utils import (
    get_remember_device_cookie, salted_hmac_sha256,
    validate_remember_device_cookie,
)

from .utils import UserMixin


class UtilsTest(UserMixin, TestCase):
    def test_default_device(self):
        user = self.create_user()
        self.assertEqual(default_device(user), None)

        user.phonedevice_set.create(name='backup', number='+12024561111')
        self.assertEqual(default_device(user), None)

        default = user.phonedevice_set.create(name='default', number='+12024561111')
        self.assertEqual(default_device(user).pk, default.pk)

    def test_backup_phones(self):
        self.assertQuerysetEqual(list(backup_phones(None)), [])
        user = self.create_user()
        user.phonedevice_set.create(name='default', number='+12024561111')
        backup = user.phonedevice_set.create(name='backup', number='+12024561111')
        phones = backup_phones(user)

        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].pk, backup.pk)

    def test_backup_devices(self):
        self.assertListEqual(backup_devices(None), [])

        user = self.create_user()
        user.phonedevice_set.create(name='default', number='+12024561111')
        backup_phone = user.phonedevice_set.create(name='backup', number='+12024561111')
        backup_email = user.emaildevice_set.create(name='backup', email='test@email.com')
        devices = backup_devices(user)

        self.assertCountEqual([d.id for d in devices], [backup_phone.pk, backup_email.pk])

    def test_get_otpauth_url(self):
        for num_digits in (6, 8):
            self.assertEqualUrl(
                'otpauth://totp/bouke%40example.com?secret=abcdef123&digits=' + str(num_digits),
                get_otpauth_url(accountname='bouke@example.com', secret='abcdef123',
                                digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/Bouke%20Haarsma?secret=abcdef123&digits=' + str(num_digits),
                get_otpauth_url(accountname='Bouke Haarsma', secret='abcdef123',
                                digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/example.com%3A%20bouke%40example.com?'
                'secret=abcdef123&digits=' + str(num_digits) + '&issuer=example.com',
                get_otpauth_url(accountname='bouke@example.com', issuer='example.com',
                                secret='abcdef123', digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/My%20Site%3A%20bouke%40example.com?'
                'secret=abcdef123&digits=' + str(num_digits) + '&issuer=My+Site',
                get_otpauth_url(accountname='bouke@example.com', issuer='My Site',
                                secret='abcdef123', digits=num_digits))

            self.assertEqualUrl(
                'otpauth://totp/%E6%B5%8B%E8%AF%95%E7%BD%91%E7%AB%99%3A%20'
                '%E6%88%91%E4%B8%8D%E6%98%AF%E9%80%97%E6%AF%94?'
                'secret=abcdef123&digits=' + str(num_digits) + '&issuer=测试网站',
                get_otpauth_url(accountname='我不是逗比',
                                issuer='测试网站',
                                secret='abcdef123', digits=num_digits))

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

    def test_random_hex(self):
        # test that returned random_hex is string
        h = random_hex()
        self.assertIsInstance(h, str)
        # hex string must be 40 characters long. If cannot be longer, because CharField max_length=40
        self.assertEqual(len(h), 40)

    @override_settings(
        TWO_FACTOR_REMEMBER_COOKIE_AGE=60 * 60,
    )
    def test_create_and_validate_remember_cookie(self):
        user = mock.Mock()
        user.pk = 123
        user.password = make_password("xx")
        cookie_value = get_remember_device_cookie(
            user=user, otp_device_id="SomeModel/33"
        )
        self.assertEqual(len(cookie_value.split(':')), 3)
        validation_result = validate_remember_device_cookie(
            cookie=cookie_value,
            user=user,
            otp_device_id="SomeModel/33",
        )
        self.assertTrue(validation_result)

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

    def test_salted_hmac_sha256(self):
        hmac_with_secret = salted_hmac_sha256("blah", "blah", "my-new-secret")
        hmac_without_secret = salted_hmac_sha256("blah", "blah")
        self.assertNotEqual(hmac_with_secret, hmac_without_secret)
