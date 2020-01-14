import os
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django_otp import devices_for_user

from .utils import UserMixin


class DisableCommandTest(UserMixin, TestCase):
    def _assert_raises(self, err_type, err_message):
        return self.assertRaisesMessage(err_type, err_message)

    def test_raises(self):
        stdout = StringIO()
        stderr = StringIO()
        with self._assert_raises(CommandError, 'User "some_username" does not exist'):
            call_command(
                'two_factor_disable', 'some_username',
                stdout=stdout, stderr=stderr)

        with self._assert_raises(CommandError, 'User "other_username" does not exist'):
            call_command(
                'two_factor_disable', 'other_username', 'some_username',
                stdout=stdout, stderr=stderr)

    def test_disable_single(self):
        user = self.create_user()
        self.enable_otp(user)
        call_command('two_factor_disable', 'bouke@example.com')
        self.assertEqual(list(devices_for_user(user)), [])

    def test_happy_flow_multiple(self):
        usernames = ['user%d@example.com' % i for i in range(0, 3)]
        users = [self.create_user(username) for username in usernames]
        [self.enable_otp(user) for user in users]
        call_command('two_factor_disable', *usernames[:2])
        self.assertEqual(list(devices_for_user(users[0])), [])
        self.assertEqual(list(devices_for_user(users[1])), [])
        self.assertNotEqual(list(devices_for_user(users[2])), [])


class StatusCommandTest(UserMixin, TestCase):
    def _assert_raises(self, err_type, err_message):
        return self.assertRaisesMessage(err_type, err_message)

    def setUp(self):
        super().setUp()
        os.environ['DJANGO_COLORS'] = 'nocolor'

    def test_raises(self):
        stdout = StringIO()
        stderr = StringIO()
        with self._assert_raises(CommandError, 'User "some_username" does not exist'):
            call_command(
                'two_factor_status', 'some_username',
                stdout=stdout, stderr=stderr)

        with self._assert_raises(CommandError, 'User "other_username" does not exist'):
            call_command(
                'two_factor_status', 'other_username', 'some_username',
                stdout=stdout, stderr=stderr)

    def test_status_single(self):
        user = self.create_user()
        stdout = StringIO()
        call_command('two_factor_status', 'bouke@example.com', stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'bouke@example.com: disabled\n')

        stdout = StringIO()
        self.enable_otp(user)
        call_command('two_factor_status', 'bouke@example.com', stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'bouke@example.com: enabled\n')

    def test_status_mutiple(self):
        users = [self.create_user(n) for n in ['user0@example.com', 'user1@example.com']]
        self.enable_otp(users[0])
        stdout = StringIO()
        call_command('two_factor_status', 'user0@example.com', 'user1@example.com', stdout=stdout)
        self.assertEqual(stdout.getvalue(), 'user0@example.com: enabled\n'
                                            'user1@example.com: disabled\n')
