from django.conf import settings
from django.shortcuts import resolve_url
from django.test import TestCase
from django.test.utils import override_settings

from two_factor.admin import patch_admin, unpatch_admin

from .utils import UserMixin


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
        self.login_user()

    def test_otp_admin_without_otp(self):
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?next=/otp_admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)

    @override_settings(LOGIN_URL='two_factor:login')
    def test_otp_admin_without_otp_named_url(self):
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?next=/otp_admin/' % resolve_url(settings.LOGIN_URL)
        self.assertRedirects(response, redirect_to)

    def test_otp_admin_with_otp(self):
        self.enable_otp()
        self.login_user()
        response = self.client.get('/otp_admin/')
        self.assertEqual(response.status_code, 200)
