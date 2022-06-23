
from unittest import mock

from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import override_settings

from .utils import UserMixin


@override_settings(ROOT_URLCONF='tests.urls_admin')
class TwoFactorAdminSiteTest(UserMixin, TestCase):
    """
    otp_admin is admin console that needs OTP for access.
    Only admin users (is_staff and is_active)
        with OTP can access it.
    """

    def test_anonymous_get_admin_index_redirects_to_admin_login(self):
        index_url = reverse('admin:index')
        login_url = reverse('admin:login')
        response = self.client.get(index_url, follow=True)
        redirect_to = '%s?next=%s' % (login_url, index_url)
        self.assertRedirects(response, redirect_to)

    def test_anonymous_get_admin_logout_redirects_to_admin_index(self):
        # see: django.tests.admin_views.test_client_logout_url_can_be_used_to_login
        index_url = reverse('admin:index')
        logout_url = reverse('admin:logout')
        response = self.client.get(logout_url)
        self.assertEqual(
            response.status_code, 302
        )
        self.assertEqual(response.get('Location'), index_url)

    def test_anonymous_get_admin_login(self):
        login_url = reverse('admin:login')
        response = self.client.get(login_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_is_staff_not_verified_not_setup_get_admin_index_redirects_to_setup(self):
        """
        admins without MFA setup should be redirected to the setup page.
        """
        index_url = reverse('admin:index')
        setup_url = reverse('two_factor:setup')
        self.user = self.create_superuser()
        self.login_user()
        response = self.client.get(index_url, follow=True)
        redirect_to = '%s?next=%s' % (setup_url, index_url)
        self.assertRedirects(response, redirect_to)

    def test_is_staff_not_verified_not_setup_get_admin_login_redirects_to_setup(self):
        index_url = reverse('admin:index')
        login_url = reverse('admin:login')
        setup_url = reverse('two_factor:setup')
        self.user = self.create_superuser()
        self.login_user()
        response = self.client.get(login_url, follow=True)
        redirect_to = '%s?next=%s' % (setup_url, index_url)
        self.assertRedirects(response, redirect_to)

    def test_is_staff_is_verified_get_admin_index(self):
        index_url = reverse('admin:index')
        self.user = self.create_superuser()
        self.enable_otp(self.user)
        self.login_user()
        response = self.client.get(index_url)
        self.assertEqual(response.status_code, 200)

    def test_is_staff_is_verified_get_admin_password_change(self):
        password_change_url = reverse('admin:password_change')
        self.user = self.create_superuser()
        self.enable_otp(self.user)
        self.login_user()
        response = self.client.get(password_change_url)
        self.assertEqual(response.status_code, 200)

    def test_is_staff_is_verified_get_admin_login_redirects_to_admin_index(self):
        login_url = reverse('admin:login')
        index_url = reverse('admin:index')
        self.user = self.create_superuser()
        self.enable_otp(self.user)
        self.login_user()
        response = self.client.get(login_url)
        self.assertEqual(response.get('Location'), index_url)

    @mock.patch('two_factor.views.core.signals.user_verified.send')
    def test_valid_login(self, mock_signal):
        login_url = reverse('admin:login')
        self.user = self.create_user()
        self.enable_otp(self.user)
        data = {'auth-username': 'bouke@example.com',
                'auth-password': 'secret',
                'login_view-current_step': 'auth'}
        response = self.client.post(login_url, data=data)
        self.assertEqual(response.status_code, 200)

        # No signal should be fired for non-verified user logins.
        self.assertFalse(mock_signal.called)
