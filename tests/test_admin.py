from binascii import unhexlify

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django_otp.oath import totp

from two_factor.admin import patch_admin, unpatch_admin

from .utils import UserMixin, method_registry


@override_settings(ROOT_URLCONF='tests.urls_admin')
class AdminPatchTest(TestCase):

    def setUp(self):
        patch_admin()

    def tearDown(self):
        unpatch_admin()

    def test(self):
        response = self.client.get('/admin/', follow=True)
        redirect_to = '%s?next=/admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)

    @override_settings(LOGIN_URL='two_factor:login')
    def test_named_url(self):
        response = self.client.get('/admin/', follow=True)
        redirect_to = '%s?next=/admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)


@override_settings(ROOT_URLCONF='tests.urls_admin')
class AdminSiteTest(UserMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_superuser()
        self.login_user()

    def test_default_admin(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)


@override_settings(ROOT_URLCONF='tests.urls_otp_admin')
class OTPAdminSiteTest(UserMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.user = self.create_superuser()

    def test_otp_admin_without_otp(self):
        self.login_user()
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?next=/otp_admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)

    @override_settings(LOGIN_URL='two_factor:login')
    def test_otp_admin_without_otp_named_url(self):
        self.login_user()
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?next=/otp_admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)

    def test_otp_admin_with_otp(self):
        self.enable_otp()
        self.login_user()
        response = self.client.get('/otp_admin/')
        self.assertEqual(response.status_code, 200)

    @method_registry(['generator'])
    def test_otp_admin_login_redirect_without_otp(self):
        # Open URL that is protected
        #  assert go to login page
        #  assert the next param not in the session (but still in url)
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?next=/otp_admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)
        self.assertEqual(self.client.session.get('next'), None)

        # Log in given the last redirect
        #  assert redirect to setup
        response = self.client.post(
            redirect_to,
            {'auth-username': 'bouke@example.com', 'auth-password': 'secret', 'login_view-current_step': 'auth'},
        )
        self.assertRedirects(response, reverse('two_factor:setup'))
        self.assertEqual(self.client.session.get('next'), '/otp_admin/')

        # Setup the device accordingly
        #  assert redirect to setup completed
        #  assert button for redirection to the original page
        response = self.client.post(reverse('two_factor:setup'), data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'autofocus="autofocus"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'autocomplete="one-time-code"')

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator', 'generator-token': totp(bin_key)},
            follow=True,
        )

        self.assertRedirects(response, '/otp_admin/')
