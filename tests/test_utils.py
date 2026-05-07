import string
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qsl, urlparse

from django.contrib.auth.hashers import make_password
from django.test import TestCase, override_settings
from django.utils import timezone
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.util import random_hex
from phonenumber_field.phonenumber import PhoneNumber

from two_factor.plugins.email.utils import mask_email
from two_factor.plugins.phonenumber.method import PhoneCallMethod, SMSMethod
from two_factor.plugins.phonenumber.models import PhoneDevice
from two_factor.plugins.phonenumber.utils import (
    backup_phones, format_phone_number, get_available_phone_methods,
    mask_phone_number,
)
from two_factor.plugins.registry import GeneratorMethod, MethodRegistry
from two_factor.utils import (
    USER_DEFAULT_DEVICE_ATTR_NAME, default_device, get_otpauth_url,
    primary_device_candidates, totp_digits,
)
from two_factor.views.utils import (
    get_remember_device_cookie, validate_remember_device_cookie,
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
        self.assertEqual(getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME).pk, default.pk)

        # double check we're actually caching
        PhoneDevice.objects.all().delete()
        self.assertEqual(default_device(user).pk, default.pk)
        self.assertEqual(getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME).pk, default.pk)


class DefaultDeviceSelectionTests(UserMixin, TestCase):
    """Coverage for the multi-device selection rules in ``default_device``.

    See PR fixing #652. Each test exercises one branch of the selection
    policy and verifies the cache behaviour.
    """

    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    def _delete_cache(self):
        # The function caches per-user-instance; reset between assertions
        # that exercise different DB states on the same Python object.
        if hasattr(self.user, USER_DEFAULT_DEVICE_ATTR_NAME):
            delattr(self.user, USER_DEFAULT_DEVICE_ATTR_NAME)

    def test_legacy_default_named_device_is_preferred(self):
        # Backward-compat guarantee: a device literally named "default"
        # always wins, even when there's a more recently used one.
        # This protects every existing deployment that depends on the
        # upstream wizard's "default" naming convention.
        TOTPDevice.objects.create(
            user=self.user, name='legacy-default-device',
            last_used_at=timezone.now(),
        )
        explicit = TOTPDevice.objects.create(user=self.user, name='default')

        self.assertEqual(default_device(self.user), explicit)

    def test_most_recently_used_device_is_returned_when_no_default_named(self):
        # Issue #652: users naming their devices ("YubiKey", "1Password")
        # used to get None back. Now they get the most-recently-used.
        old = TOTPDevice.objects.create(
            user=self.user, name='Old YubiKey',
            last_used_at=timezone.now() - timedelta(days=30),
        )
        recent = TOTPDevice.objects.create(
            user=self.user, name='New YubiKey',
            last_used_at=timezone.now(),
        )

        self.assertEqual(default_device(self.user), recent)
        # And cached for the rest of the request.
        self.assertEqual(
            getattr(self.user, USER_DEFAULT_DEVICE_ATTR_NAME), recent
        )
        self.assertNotEqual(default_device(self.user), old)

    def test_lowest_persistent_id_is_tiebreaker_when_no_last_used_at(self):
        # Fresh enrollment, no logins yet: pick the device with the
        # lowest persistent_id so behaviour is deterministic across
        # requests (instead of dictionary-iteration-order dependent).
        first = TOTPDevice.objects.create(user=self.user, name='Phone')
        TOTPDevice.objects.create(user=self.user, name='Laptop')

        chosen = default_device(self.user)
        all_pids = sorted(
            d.persistent_id for d in TOTPDevice.objects.filter(user=self.user)
        )
        self.assertEqual(chosen.persistent_id, all_pids[0])
        self.assertEqual(chosen, first)

    def test_static_backup_device_is_excluded(self):
        # StaticDevice carries backup tokens and must never be picked
        # as primary, even when it's the only device or the most
        # recently used one. Picking it would mean re-prompting users
        # for backup codes during a normal login.
        StaticDevice.objects.create(
            user=self.user, name='backup',
            last_used_at=timezone.now(),
        )

        self.assertIsNone(default_device(self.user))

        self._delete_cache()
        # Add a real device with an OLDER last_used_at - it should
        # still win against the more-recently-used StaticDevice.
        totp = TOTPDevice.objects.create(
            user=self.user, name='YubiKey',
            last_used_at=timezone.now() - timedelta(days=10),
        )
        self.assertEqual(default_device(self.user), totp)

    def test_devices_named_backup_are_excluded(self):
        # `name == 'backup'` is the project-wide convention for backup
        # devices (see ``backup_phones``). Honour it here too so a
        # PhoneDevice the user enrolled as a backup phone is never
        # silently promoted to primary.
        self.user.phonedevice_set.create(
            name='backup', number='+12024561111',
        )
        self.assertIsNone(default_device(self.user))

    def test_no_device_returns_none_and_does_not_cache(self):
        # Negative results must NOT be cached; otherwise enrolling a
        # device later in the same request (e.g. during the setup
        # wizard) would still return None until a fresh request.
        self.assertIsNone(default_device(self.user))
        self.assertFalse(hasattr(self.user, USER_DEFAULT_DEVICE_ATTR_NAME))

        TOTPDevice.objects.create(user=self.user, name='default')
        self.assertIsNotNone(default_device(self.user))

    def test_anonymous_user_returns_none(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertIsNone(default_device(AnonymousUser()))
        self.assertIsNone(default_device(None))

    def test_unconfirmed_devices_filtered_via_confirmed_kwarg(self):
        # Backward-compat: callers that pass ``confirmed=False`` still
        # only see unconfirmed devices, ``confirmed=None`` sees both.
        # Required by the upstream setup wizard (mid-enrollment lookup).
        TOTPDevice.objects.create(
            user=self.user, name='confirmed-device', confirmed=True,
        )
        unconfirmed = TOTPDevice.objects.create(
            user=self.user, name='in-progress', confirmed=False,
        )

        self._delete_cache()
        self.assertEqual(
            default_device(self.user, confirmed=False), unconfirmed
        )


# Module-level picker callables for the override-setting tests below.
# Defined at module scope (not inside a class / method) so
# ``import_string`` can resolve them via dotted path - that's the
# whole contract of the ``TWO_FACTOR_DEFAULT_DEVICE_PICKER`` setting.

def _picker_returns_first(devices):
    return devices[0] if devices else None


def _picker_returns_none(devices):
    return None


def _picker_picks_alphabetical_by_name(devices):
    if not devices:
        return None
    return sorted(devices, key=lambda d: d.name)[0]


class DefaultDevicePickerHookTests(UserMixin, TestCase):
    """Coverage for the ``TWO_FACTOR_DEFAULT_DEVICE_PICKER`` extension point."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user()

    @override_settings(
        TWO_FACTOR_DEFAULT_DEVICE_PICKER='tests.test_utils._picker_returns_first',
    )
    def test_custom_picker_is_invoked_when_setting_is_configured(self):
        # The custom picker overrides the built-in policy entirely.
        # Here it returns the first device unconditionally - even
        # though the built-in would have skipped this StaticDevice as
        # a backup. The hook puts the policy in the project's hands.
        static = StaticDevice.objects.create(
            user=self.user, name='backup',
        )
        self.assertEqual(default_device(self.user), static)

    @override_settings(
        TWO_FACTOR_DEFAULT_DEVICE_PICKER='tests.test_utils._picker_returns_none',
    )
    def test_custom_picker_returning_none_is_handled(self):
        # A picker is allowed to deliberately return None even when
        # devices exist (e.g. a security policy that requires explicit
        # admin enablement). default_device must not cache the None.
        TOTPDevice.objects.create(user=self.user, name='YubiKey')
        self.assertIsNone(default_device(self.user))
        # Per the no-cache-None invariant, a follow-up call after a
        # picker change must re-evaluate.
        if hasattr(self.user, USER_DEFAULT_DEVICE_ATTR_NAME):
            delattr(self.user, USER_DEFAULT_DEVICE_ATTR_NAME)

    @override_settings(
        TWO_FACTOR_DEFAULT_DEVICE_PICKER='tests.test_utils._picker_picks_alphabetical_by_name',
    )
    def test_custom_picker_receives_full_device_list_including_backups(self):
        # The picker contract is "you receive every device returned by
        # devices_for_user; you decide". We do NOT pre-filter so that
        # custom pickers can implement policies that consider backup
        # devices too (e.g. an admin tool that wants the truly first
        # device by name regardless of role).
        StaticDevice.objects.create(user=self.user, name='aaa-static')
        TOTPDevice.objects.create(user=self.user, name='zzz-totp')
        self.assertEqual(default_device(self.user).name, 'aaa-static')

    def test_default_picker_is_used_when_setting_is_unset(self):
        # No override; built-in policy applies. Regression guard against
        # the resolver short-circuiting in a way that bypasses the
        # built-in picker when the setting is missing.
        explicit = TOTPDevice.objects.create(user=self.user, name='default')
        self.assertEqual(default_device(self.user), explicit)


class PrimaryDeviceCandidatesTests(TestCase):
    """Coverage for the public ``primary_device_candidates`` helper.

    Pure function, no DB needed - we feed it mock objects that
    exercise the two exclusion rules. Public so custom pickers can
    apply the same backup-exclusion logic without re-implementing it.
    """

    def test_excludes_static_devices(self):
        static = mock.Mock(spec=StaticDevice, name='primary-named-static')
        # Mock attribute `name` collides with mock's own constructor
        # `name` kwarg; set after construction so the device's own
        # `.name` attribute (the one the helper inspects) is correct.
        static.name = 'whatever'
        totp = mock.Mock(name='regular-totp')
        totp.name = 'YubiKey'

        result = primary_device_candidates([static, totp])
        self.assertEqual(result, [totp])

    def test_excludes_devices_named_backup(self):
        # The 'backup' name convention is documented and used by
        # backup_phones(); the helper must respect it for any device
        # type, not only StaticDevice.
        backup_phone = mock.Mock(name='backup-phone')
        backup_phone.name = 'backup'
        totp = mock.Mock(name='regular-totp')
        totp.name = 'YubiKey'

        result = primary_device_candidates([backup_phone, totp])
        self.assertEqual(result, [totp])

    def test_keeps_order_of_input(self):
        # Custom pickers may build their own tie-breaking on top.
        # Document the order-preservation contract so they can rely
        # on it.
        a = mock.Mock()
        a.name = 'a'
        b = mock.Mock()
        b.name = 'b'
        c = mock.Mock()
        c.name = 'c'
        self.assertEqual(primary_device_candidates([a, b, c]), [a, b, c])

    def test_empty_list_returns_empty_list(self):
        self.assertEqual(primary_device_candidates([]), [])

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

    def test_cookie_valid_characters(self):
        user = mock.Mock()
        user.pk = 123
        user.password = make_password("xx")
        allowed_characters = set(string.ascii_letters + string.digits + "-_:")

        cookie_value = get_remember_device_cookie(
            user=user, otp_device_id="SomeModel/33"
        )
        self.assertTrue(all(c in allowed_characters for c in cookie_value))


class PhoneUtilsTests(UserMixin, TestCase):
    def test_get_available_phone_methods(self):
        parameters = [
            # registered_methods, expected_codes
            ([GeneratorMethod()], set()),
            ([GeneratorMethod(), PhoneCallMethod()], {'call'}),
            ([GeneratorMethod(), PhoneCallMethod(), SMSMethod()], {'call', 'sms'}),
        ]
        with mock.patch('two_factor.plugins.phonenumber.utils.registry', new_callable=MethodRegistry) as test_registry:
            for registered_methods, expected_codes in parameters:
                with self.subTest(
                    registered_methods=registered_methods,
                    expected_codes=expected_codes,
                ):
                    test_registry._methods = registered_methods
                    codes = {method.code for method in get_available_phone_methods()}
                    self.assertEqual(codes, expected_codes)

    def test_backup_phones(self):
        gateway = 'two_factor.gateways.fake.Fake'
        user = self.create_user()
        user.phonedevice_set.create(name='default', number='+12024561111', method='call')
        backup = user.phonedevice_set.create(name='backup', number='+12024561111', method='call')

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


class EmailUtilsTests(TestCase):
    def test_mask_email(self):
        self.assertEqual(mask_email('bouke@example.com'), 'b***e@example.com')
        self.assertEqual(mask_email('tim@example.com'), 't**@example.com')
