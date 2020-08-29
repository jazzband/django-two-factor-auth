from datetime import timedelta
from doctest import DocTestSuite
import pickle
import unittest

from freezegun import freeze_time

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import RequestFactory
from django.test import TestCase as DjangoTestCase
from django.urls import reverse

from django_otp import DEVICE_ID_SESSION_KEY, oath, util
from django_otp.middleware import OTPMiddleware
from django_otp.models import VerifyNotAllowed


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()

    suite.addTests(tests)
    suite.addTest(DocTestSuite(util))
    suite.addTest(DocTestSuite(oath))

    return suite


class TestCase(DjangoTestCase):
    """
    Utilities for dealing with custom user models.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.User = get_user_model()
        cls.USERNAME_FIELD = cls.User.USERNAME_FIELD

    def create_user(self, username, password, **kwargs):
        """
        Try to create a user, honoring the custom user model, if any.

        This may raise an exception if the user model is too exotic for our
        purposes.
        """
        return self.User.objects.create_user(username, password=password, **kwargs)


class ThrottlingTestMixin:
    """
    Generic tests for throttled devices.

    Any concrete device implementation that uses throttling should define a
    TestCase subclass that includes this as a base class. This will help verify
    a correct integration of ThrottlingMixin.

    Subclasses are responsible for populating self.device with a device to test
    as well as implementing methods to generate tokens to test with.

    """
    def setUp(self):
        self.device = None

    def valid_token(self):
        """ Returns a valid token to pass to our device under test. """
        raise NotImplementedError()

    def invalid_token(self):
        """ Returns an invalid token to pass to our device under test. """
        raise NotImplementedError()

    #
    # Tests
    #

    def test_delay_imposed_after_fail(self):
        verified1 = self.device.verify_token(self.invalid_token())
        self.assertFalse(verified1)
        verified2 = self.device.verify_token(self.valid_token())
        self.assertFalse(verified2)

    def test_delay_after_fail_expires(self):
        verified1 = self.device.verify_token(self.invalid_token())
        self.assertFalse(verified1)
        with freeze_time() as frozen_time:
            # With default settings initial delay is 1 second
            frozen_time.tick(delta=timedelta(seconds=1.1))
            verified2 = self.device.verify_token(self.valid_token())
            self.assertTrue(verified2)

    def test_throttling_failure_count(self):
        self.assertEqual(self.device.throttling_failure_count, 0)
        for i in range(0, 5):
            self.device.verify_token(self.invalid_token())
            # Only the first attempt will increase throttling_failure_count,
            # the others will all be within 1 second of first
            # and therefore not count as attempts.
            self.assertEqual(self.device.throttling_failure_count, 1)

    def test_verify_is_allowed(self):
        # Initially should be allowed
        verify_is_allowed1, data1 = self.device.verify_is_allowed()
        self.assertEqual(verify_is_allowed1, True)
        self.assertEqual(data1, None)

        # After failure, verify is not allowed
        self.device.verify_token(self.invalid_token())
        verify_is_allowed2, data2 = self.device.verify_is_allowed()
        self.assertEqual(verify_is_allowed2, False)
        self.assertEqual(data2, {'reason': VerifyNotAllowed.N_FAILED_ATTEMPTS,
                                 'failure_count': 1})

        # After a successful attempt, should be allowed again
        with freeze_time() as frozen_time:
            frozen_time.tick(delta=timedelta(seconds=1.1))
            self.device.verify_token(self.valid_token())

            verify_is_allowed3, data3 = self.device.verify_is_allowed()
            self.assertEqual(verify_is_allowed3, True)
            self.assertEqual(data3, None)


class OTPMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        try:
            self.alice = self.create_user('alice', 'password')
            self.bob = self.create_user('bob', 'password')
        except IntegrityError:
            self.skipTest("Unable to create a test user.")
        else:
            for user in [self.alice, self.bob]:
                device = user.staticdevice_set.create()
                device.token_set.create(token=user.get_username())

        self.middleware = OTPMiddleware(lambda r: None)

    def test_verified(self):
        request = self.factory.get('/')
        request.user = self.alice
        device = self.alice.staticdevice_set.get()
        request.session = {
            DEVICE_ID_SESSION_KEY: device.persistent_id
        }

        self.middleware(request)

        self.assertTrue(request.user.is_verified())

    def test_verified_legacy_device_id(self):
        request = self.factory.get('/')
        request.user = self.alice
        device = self.alice.staticdevice_set.get()
        request.session = {
            DEVICE_ID_SESSION_KEY: '{}.{}/{}'.format(
                device.__module__, device.__class__.__name__, device.id
            )
        }

        self.middleware(request)

        self.assertTrue(request.user.is_verified())

    def test_unverified(self):
        request = self.factory.get('/')
        request.user = self.alice
        request.session = {}

        self.middleware(request)

        self.assertFalse(request.user.is_verified())

    def test_no_device(self):
        request = self.factory.get('/')
        request.user = self.alice
        request.session = {
            DEVICE_ID_SESSION_KEY: 'otp_static.staticdevice/0',
        }

        self.middleware(request)

        self.assertFalse(request.user.is_verified())

    def test_no_model(self):
        request = self.factory.get('/')
        request.user = self.alice
        request.session = {
            DEVICE_ID_SESSION_KEY: 'otp_bogus.bogusdevice/0',
        }

        self.middleware(request)

        self.assertFalse(request.user.is_verified())

    def test_wrong_user(self):
        request = self.factory.get('/')
        request.user = self.alice
        device = self.bob.staticdevice_set.get()
        request.session = {
            DEVICE_ID_SESSION_KEY: device.persistent_id
        }

        self.middleware(request)

        self.assertFalse(request.user.is_verified())

    def test_pickling(self):
        request = self.factory.get('/')
        request.user = self.alice
        device = self.alice.staticdevice_set.get()
        request.session = {
            DEVICE_ID_SESSION_KEY: device.persistent_id
        }

        self.middleware(request)

        # Should not raise an exception.
        pickle.dumps(request.user)


class LoginViewTestCase(TestCase):
    def setUp(self):
        try:
            self.alice = self.create_user('alice', 'password')
            self.bob = self.create_user('bob', 'password', is_staff=True)
        except IntegrityError:
            self.skipTest("Unable to create a test user.")
        else:
            for user in [self.alice, self.bob]:
                device = user.staticdevice_set.create()
                device.token_set.create(token=user.get_username())

    def test_admin_login_template(self):
        response = self.client.get(reverse('otpadmin:login'))
        self.assertContains(response, 'Username:')
        self.assertContains(response, 'Password:')
        self.assertNotContains(response, 'OTP Device:')
        self.assertContains(response, 'OTP Token:')
        response = self.client.post(reverse('otpadmin:login'), data={
            'username': self.bob.get_username(),
            'password': 'password',
        })
        self.assertContains(response, 'Username:')
        self.assertContains(response, 'Password:')
        self.assertContains(response, 'OTP Device:')
        self.assertContains(response, 'OTP Token:')

        device = self.bob.staticdevice_set.get()
        token = device.token_set.get()
        response = self.client.post(reverse('otpadmin:login'), data={
            'username': self.bob.get_username(),
            'password': 'password',
            'otp_device': device.persistent_id,
            'otp_token': token.token,
            'next': '/',
        })
        self.assertRedirects(response, '/')

    def test_authenticate(self):
        device = self.alice.staticdevice_set.get()
        token = device.token_set.get()

        params = {
            'username': self.alice.get_username(),
            'password': 'password',
            'otp_device': device.persistent_id,
            'otp_token': token.token,
            'next': '/',
        }

        response = self.client.post('/login/', params)
        self.assertRedirects(response, '/')

        response = self.client.get('/')
        self.assertContains(response, self.alice.get_username())

    def test_verify(self):
        device = self.alice.staticdevice_set.get()
        token = device.token_set.get()

        params = {
            'otp_device': device.persistent_id,
            'otp_token': token.token,
            'next': '/',
        }

        self.client.login(username=self.alice.get_username(), password='password')

        response = self.client.post('/login/', params)
        self.assertRedirects(response, '/')

        response = self.client.get('/')
        self.assertContains(response, self.alice.get_username())
