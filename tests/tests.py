from binascii import unhexlify
import qrcode.image.svg

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
try:
    from unittest.mock import patch, Mock, ANY, call
except ImportError:
    from mock import patch, Mock, ANY, call

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation, six
from django_otp import DEVICE_ID_SESSION_KEY, devices_for_user
from django_otp.oath import totp
from django_otp.util import random_hex

from two_factor.admin import patch_admin, unpatch_admin
from two_factor.gateways.fake import Fake
from two_factor.gateways.twilio.gateway import Twilio
from two_factor.models import PhoneDevice, phone_number_validator
from two_factor.utils import backup_phones, default_device, get_otpauth_url


class UserMixin(object):
    def setUp(self):
        super(UserMixin, self).setUp()
        self.user = User.objects.create_user('bouke', None, 'secret')
        assert self.client.login(username='bouke', password='secret')

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    Permission,
    UserManager,
    BaseUserManager,
    )
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    # Implementation based on:
    # https://github.com/django/django/blob/a9093dd3763df6b2045a08b0520f248bda708723/django/contrib/auth/models.py#L162
    # But with the 'username' field dropped ('email' is used as username field)

    def _create_user(self, email, password,
                     is_staff, **extra_fields):
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email,
                          is_staff=is_staff, is_active=True,
                          last_login=now,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return self._create_user(email, password, False,
                                 **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email, password, True,
                                 **extra_fields)


class CustomUser(AbstractBaseUser):
    """
    Some of this was copied from:
    https://github.com/django/django/blob/master/django/contrib/auth/models.py#L353
    """
    first_name = models.CharField(max_length=255, blank=True)

    last_name = models.CharField(max_length=255, blank=True)

    title = models.CharField(max_length=255, blank=True)

    email = models.EmailField('email address', max_length=255,
                              blank=True, unique=True)

    is_staff = models.BooleanField('staff status', default=False,
                help_text='Designates whether the user can log into this admin '
                          'site.')

    is_active = models.BooleanField('active', default=True,
                help_text='Designates whether this user should be treated as '
                          'active. Unselect this instead of deleting accounts.')

    date_joined = models.DateTimeField('date joined', default=timezone.now)

    permissions = models.ManyToManyField(Permission,
                                         related_name="auth_user_set",
                                         blank=True)

    is_demo = models.BooleanField(default=False, verbose_name='Demo Account?')

    phone_number = models.CharField(max_length=255, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        app_label = 'tests'
        abstract = False

    def has_perm(self, perm, obj=None):
        print "has_perm: {}, {}".format(perm, obj)

        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff

    def get_full_name(self):
        return u"{} {}".format(self.first_name, self.last_name)

    def get_short_name(self):
        return self.get_full_name()


class CustomAdminUserMixin(object):
    def setUp(self):
        from django.conf import settings
        self.old_auth_user_model = settings.AUTH_USER_MODEL
        settings.AUTH_USER_MODEL = "tests.CustomUser"

        super(CustomAdminUserMixin, self).setUp()

        self.user = CustomUser.objects.create_superuser('bouke@example.com', 'secret')
        login = self.client.login(email='bouke@example.com', password='secret')
        assert login

    def tearDown(self):
        from django.conf import settings
        settings.AUTH_USER_MODEL = self.old_auth_user_model


class CustomUserMixin(object):
    def setUp(self):
        from django.conf import settings
        self.old_auth_user_model = settings.AUTH_USER_MODEL
        settings.AUTH_USER_MODEL = "tests.CustomUser"

        super(CustomUserMixin, self).setUp()

        self.user = CustomUser.objects.create_user('bouke@example.com', 'secret')
        login = self.client.login(email='bouke@example.com', password='secret')
        assert login

    def tearDown(self):
        from django.conf import settings
        settings.AUTH_USER_MODEL = self.old_auth_user_model


class OTPUserMixin(CustomUserMixin):
    def setUp(self):
        super(OTPUserMixin, self).setUp()
        self.device = self.user.totpdevice_set.create(name='default')
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = self.device.persistent_id
        session.save()


class LoginTest(TestCase):
    def _post(self, data=None):
        return self.client.post(reverse('two_factor:login'), data=data)

    def test_form(self):
        response = self.client.get(reverse('two_factor:login'))
        self.assertContains(response, 'Username:')

    def test_invalid_login(self):
        response = self._post({'auth-username': 'unknown',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Please enter a correct username '
                                      'and password.')

    def test_valid_login(self):
        # User.objects.create_user('bouke', None, 'secret')
        CustomUser.objects.create_user('bouke@example.com', 'secret')

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

    def test_valid_login_with_custom_redirect(self):
        redirect_url = reverse('two_factor:setup')

        # User.objects.create_user('bouke', None, 'secret')
        CustomUser.objects.create_user('bouke@example.com', 'secret')
        response = self.client.post(
            '%s?%s' % (reverse('two_factor:login'),
                       urlencode({'next': redirect_url})),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_valid_login_with_redirect_field_name(self):
        redirect_url = reverse('two_factor:setup')

        # User.objects.create_user('bouke', None, 'secret')
        CustomUser.objects.create_user('bouke@example.com', 'secret')

        response = self.client.post(
            '%s?%s' % (reverse('custom-login'),
                       urlencode({'next_page': redirect_url})),
            {'auth-username': 'bouke@example.com',
             'auth-password': 'secret',
             'login_view-current_step': 'auth'})
        self.assertRedirects(response, redirect_url)

    def test_with_generator(self):
        # user = User.objects.create_user('bouke', None, 'secret')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')

        device = user.totpdevice_set.create(name='default',
                                            key=random_hex().decode())

        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Token:')

        response = self._post({'token-otp_token': '123456',
                               'login_view-current_step': 'token'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'__all__': ['Please enter your OTP token']})

        response = self._post({'token-otp_token': totp(device.bin_key),
                               'login_view-current_step': 'token'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))

        self.assertEqual(device.persistent_id,
                         self.client.session.get(DEVICE_ID_SESSION_KEY))

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_with_backup_phone(self, fake):
        # user = User.objects.create_user('bouke', None, 'secret')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')

        user.totpdevice_set.create(name='default', key=random_hex().decode())
        device = user.phonedevice_set.create(name='backup', number='123456789',
                                             method='sms',
                                             key=random_hex().decode())

        # Backup phones should be listed on the login form
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Send text message to 123****89')

        # Ask for challenge on invalid device
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'challenge_device': 'MALICIOUS/INPUT/666'})
        self.assertContains(response, 'Send text message to 123****89')

        # Ask for SMS challenge
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'challenge_device': device.persistent_id})
        self.assertContains(response, 'We sent you a text message')
        fake.return_value.send_sms.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))

        # Ask for phone challenge
        device.method = 'call'
        device.save()
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'challenge_device': device.persistent_id})
        self.assertContains(response, 'We are calling your phone right now')
        fake.return_value.make_call.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))

    def test_with_backup_token(self):
        # user = User.objects.create_user('bouke', None, 'secret')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')

        user.totpdevice_set.create(name='default', key=random_hex().decode())
        device = user.staticdevice_set.create(name='backup')
        device.token_set.create(token='abcdef123')

        # Backup phones should be listed on the login form
        response = self._post({'auth-username': 'bouke@example.com',
                               'auth-password': 'secret',
                               'login_view-current_step': 'auth'})
        self.assertContains(response, 'Backup Token')

        # Should be able to go to backup tokens step in wizard
        response = self._post({'wizard_goto_step': 'backup'})
        self.assertContains(response, 'backup tokens')

        # Wrong codes should not be accepted
        response = self._post({'backup-otp_token': 'WRONG',
                               'login_view-current_step': 'backup'})
        self.assertContains(response, 'Please enter your OTP token')

        # Valid code should be accepted
        response = self._post({'backup-otp_token': 'abcdef123',
                               'login_view-current_step': 'backup'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))


class SetupTest(CustomUserMixin, TestCase):
    def test_form(self):
        response = self.client.get(reverse('two_factor:setup'))
        self.assertContains(response, 'Follow the steps in this wizard to '
                                      'enable two-factor')

    def test_setup_generator(self):
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'method',
                  'method-method': 'generator'})
        self.assertContains(response, 'Token:')
        session = self.client.session
        self.assertIn('django_two_factor-qr_secret_key', session.keys())

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['This field is required.']})

        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Please enter a valid token.']})

        key = response.context_data['keys'].get('generator')
        bin_key = unhexlify(key.encode())
        response = self.client.post(
            reverse('two_factor:setup'),
            data={'setup_view-current_step': 'generator',
                  'generator-token': totp(bin_key)})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))
        self.assertEqual(1, self.user.totpdevice_set.count())

    def _post(self, data):
        return self.client.post(reverse('two_factor:setup'), data=data)

    def test_no_phone(self):
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertNotContains(response, 'call')

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_phone_call(self, fake):
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self._post(data={'setup_view-current_step': 'method',
                                    'method-method': 'call'})
        self.assertContains(response, 'Number:')

        response = self._post(data={'setup_view-current_step': 'call',
                                    'call-number': '+123456789'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We are calling your phone right now')

        # assert that the token was send to the gateway
        self.assertEqual(fake.return_value.method_calls,
                         [call.make_call(device=ANY, token=ANY)])

        # assert that tokens are verified
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid']})

        # submitting correct token should finish the setup
        token = fake.return_value.make_call.call_args[1]['token']
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number, '+123456789')
        self.assertEqual(phones[0].method, 'call')

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake')
    def test_setup_phone_sms(self, fake):
        response = self._post(data={'setup_view-current_step': 'welcome'})
        self.assertContains(response, 'Method:')

        response = self._post(data={'setup_view-current_step': 'method',
                                    'method-method': 'sms'})
        self.assertContains(response, 'Number:')

        response = self._post(data={'setup_view-current_step': 'sms',
                                    'sms-number': '+123456789'})
        self.assertContains(response, 'Token:')
        self.assertContains(response, 'We sent you a text message')

        # assert that the token was send to the gateway
        self.assertEqual(fake.return_value.method_calls,
                         [call.send_sms(device=ANY, token=ANY)])

        # assert that tokens are verified
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': '666'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid']})

        # submitting correct token should finish the setup
        token = fake.return_value.send_sms.call_args[1]['token']
        response = self._post(data={'setup_view-current_step': 'validation',
                                    'validation-token': token})
        self.assertRedirects(response, reverse('two_factor:setup_complete'))

        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'default')
        self.assertEqual(phones[0].number, '+123456789')
        self.assertEqual(phones[0].method, 'sms')

    def test_already_setup(self):
        self.user.totpdevice_set.create(name='default')
        response = self.client.get(reverse('two_factor:setup'))
        self.assertRedirects(response, reverse('two_factor:setup_complete'))


class OTPRequiredMixinTest(TestCase):
    @override_settings(LOGIN_URL=None)
    def test_not_configured(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.get('/secure/')

    def test_unauthenticated_redirect(self):
        url = '/secure/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % (settings.LOGIN_URL, urlencode({'next': url}))
        self.assertRedirects(response, redirect_to)

    def test_unauthenticated_raise(self):
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

    def test_unverified_redirect(self):
        # User.objects.create_superuser('bouke', None, 'secret')
        CustomUser.objects.create_user('bouke@example.com', 'secret')

        self.client.login(email='bouke@example.com', password='secret')
        url = '/secure/redirect_unverified/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % ('/account/login/', urlencode({'next': url}))
        self.assertRedirects(response, redirect_to)

    def test_unverified_raise(self):
        # User.objects.create_superuser('bouke', None, 'secret')
        CustomUser.objects.create_user('bouke@example.com', 'secret')

        self.client.login(email='bouke@example.com', password='secret')
        response = self.client.get('/secure/raises/')
        self.assertEqual(response.status_code, 403)

    def test_unverified_explanation(self):
        # User.objects.create_superuser('bouke', None, 'secret')
        CustomUser.objects.create_user('bouke@example.com', 'secret')

        self.client.login(email='bouke@example.com', password='secret')
        response = self.client.get('/secure/')
        self.assertContains(response, 'Permission Denied', status_code=403)
        self.assertContains(response, 'Enable Two-Factor Authentication',
                            status_code=403)

    def test_unverified_need_login(self):
        # user = User.objects.create_superuser('bouke', None, 'secret')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')
        self.client.login(email='bouke@example.com', password='secret')
        user.totpdevice_set.create(name='default')
        url = '/secure/'
        response = self.client.get(url)
        redirect_to = '%s?%s' % (settings.LOGIN_URL, urlencode({'next': url}))
        self.assertRedirects(response, redirect_to)

    def test_verified(self):
        # user = User.objects.create_superuser('bouke', None, 'secret')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')
        self.client.login(email='bouke@example.com', password='secret')
        device = user.totpdevice_set.create(name='default')
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

        response = self.client.get('/secure/')
        self.assertEqual(response.status_code, 200)


class AdminPatchTest(TestCase):
    def setUp(self):
        patch_admin()

    def tearDown(self):
        unpatch_admin()

    def test(self):
        response = self.client.get('/admin/', follow=True)
        redirect_to = '%s?%s' % (settings.LOGIN_URL,
                                 urlencode({'next': '/admin/'}))
        self.assertRedirects(response, redirect_to)


class AdminSiteTest(CustomAdminUserMixin, TestCase):
    def setUp(self):
        super(AdminSiteTest, self).setUp()
        pass
        # self.user = User.objects.create_superuser('bouke', None, 'secret')
        # self.client.login(username='bouke', password='secret')

    def test_default_admin(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_otp_admin_without_otp(self):
        response = self.client.get('/otp_admin/', follow=True)
        redirect_to = '%s?%s' % (settings.LOGIN_URL,
                                 urlencode({'next': '/otp_admin/'}))
        self.assertRedirects(response, redirect_to)

    def test_otp_admin_with_otp(self):
        device = self.user.totpdevice_set.create()
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()
        response = self.client.get('/otp_admin/')
        self.assertEqual(response.status_code, 200)


class BackupTokensTest(OTPUserMixin, TestCase):
    def test_empty(self):
        response = self.client.get(reverse('two_factor:backup_tokens'))
        self.assertContains(response, 'You don\'t have any backup codes yet.')

    def test_generate(self):
        url = reverse('two_factor:backup_tokens')

        response = self.client.post(url)
        self.assertRedirects(response, url)

        response = self.client.get(url)
        first_set = set([token.token for token in
                        response.context_data['device'].token_set.all()])
        self.assertNotContains(response, 'You don\'t have any backup codes '
                                         'yet.')
        self.assertEqual(10, len(first_set))

        # Generating the tokens should give a fresh set
        self.client.post(url)
        response = self.client.get(url)
        second_set = set([token.token for token in
                         response.context_data['device'].token_set.all()])
        self.assertNotEqual(first_set, second_set)


class PhoneSetupTest(OTPUserMixin, TestCase):
    def test_form(self):
        response = self.client.get(reverse('two_factor:phone_create'))
        self.assertContains(response, 'Number:')

    def _post(self, data=None):
        return self.client.post(reverse('two_factor:phone_create'), data=data)

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_setup(self, fake):
        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '',
                               'setup-method': ''})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'method': ['This field is required.'],
                          'number': ['This field is required.']})

        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '+123456789',
                               'setup-method': 'call'})
        self.assertContains(response, 'We\'ve sent a token to your phone')
        device = response.context_data['wizard']['form'].device
        fake.return_value.make_call.assert_called_with(
            device=device, token='%06d' % totp(device.bin_key))

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': '123456'})
        self.assertEqual(response.context_data['wizard']['form'].errors,
                         {'token': ['Entered token is not valid']})

        response = self._post({'phone_setup_view-current_step': 'validation',
                               'validation-token': totp(device.bin_key)})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        phones = self.user.phonedevice_set.all()
        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].name, 'backup')
        self.assertEqual(phones[0].number, '+123456789')
        self.assertEqual(phones[0].key, device.key)

    @patch('two_factor.gateways.fake.Fake')
    @override_settings(
        TWO_FACTOR_SMS_GATEWAY='two_factor.gateways.fake.Fake',
        TWO_FACTOR_CALL_GATEWAY='two_factor.gateways.fake.Fake',
    )
    def test_number_validation(self, fake):
        response = self._post({'phone_setup_view-current_step': 'setup',
                               'setup-number': '123',
                               'setup-method': 'call'})
        self.assertEqual(
            response.context_data['wizard']['form'].errors,
            {'number': [six.text_type(phone_number_validator.message)]})


class PhoneDeleteTest(OTPUserMixin, TestCase):
    def setUp(self):
        super(PhoneDeleteTest, self).setUp()
        self.backup = self.user.phonedevice_set.create(name='backup')
        self.default = self.user.phonedevice_set.create(name='default')

    def test_delete(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.backup.pk]))
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(backup_phones(self.user)), [])

    def test_cannot_delete_default(self):
        response = self.client.post(reverse('two_factor:phone_delete',
                                            args=[self.default.pk]))
        self.assertContains(response, 'was not found', status_code=404)


class QRTest(CustomUserMixin, TestCase):
    test_secret = 'This is a test secret for an OTP Token'
    test_img = 'This is a test string that represents a QRCode'

    def test_without_secret(self):
        response = self.client.get(reverse('two_factor:qr'))
        self.assertEquals(response.status_code, 404)

    @patch('qrcode.make')
    def test_with_secret(self, mockqrcode):
        # Setup the mock data
        def side_effect(resp):
            resp.write(self.test_img)
        mockimg = Mock()
        mockimg.save.side_effect = side_effect
        mockqrcode.return_value = mockimg

        # Setup the session
        session = self.client.session
        session['django_two_factor-qr_secret_key'] = self.test_secret
        session.save()

        # Get default image factory
        default_factory = qrcode.image.svg.SvgPathImage

        # Get the QR code
        response = self.client.get(reverse('two_factor:qr'))

        # Check things went as expected
        mockqrcode.assert_called_with(
            get_otpauth_url('bouke@testserver', self.test_secret),
            image_factory=default_factory)
        mockimg.save.assert_called()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content.decode('utf-8'), self.test_img)
        self.assertEquals(response['Content-Type'], 'image/svg+xml; charset=utf-8')


class DisableTest(OTPUserMixin, TestCase):
    def test(self):
        response = self.client.get(reverse('two_factor:disable'))
        self.assertContains(response, 'Yes, I am sure')

        response = self.client.post(reverse('two_factor:disable'))
        self.assertEqual(response.context_data['form'].errors,
                         {'understand': ['This field is required.']})

        response = self.client.post(reverse('two_factor:disable'),
                                    {'understand': '1'})
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))
        self.assertEqual(list(devices_for_user(self.user)), [])

        # cannot disable twice
        response = self.client.get(reverse('two_factor:disable'))
        self.assertRedirects(response, str(settings.LOGIN_REDIRECT_URL))


class TwilioGatewayTest(TestCase):
    def test_call_app(self):
        url = reverse('two_factor:twilio_call_app', args=['123456'])
        response = self.client.get(url)
        self.assertEqual(response.content,
                         b'<?xml version="1.0" encoding="UTF-8" ?><Response>'
                         b'<Say language="en">Hi, this is testserver calling. '
                         b'Please enter the following code on your screen: 1. '
                         b'2. 3. 4. 5. 6. Repeat: 1. 2. 3. 4. 5. 6.</Say>'
                         b'</Response>')

        # there is a en-gb voice
        response = self.client.get('%s?%s' % (url, urlencode({'locale': 'en-gb'})))
        self.assertContains(response, '<Say language="en-gb">')

        # there is no nl voice
        response = self.client.get('%s?%s' % (url, urlencode({'locale': 'nl-nl'})))
        self.assertContains(response, '<Say language="en">')

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.gateway.TwilioRestClient')
    def test_gateway(self, client):
        twilio = Twilio()
        client.assert_called_with('SID', 'TOKEN')

        twilio.make_call(device=Mock(number='+123'), token='654321')
        client.return_value.calls.create.assert_called_with(
            from_='+456', to='+123', method='GET',
            url='http://testserver/twilio/inbound/two_factor/654321/?locale=en-us')

        twilio.send_sms(device=Mock(number='+123'), token='654321')
        client.return_value.sms.messages.create.assert_called_with(
            to='+123', body='Your authentication token is 654321', from_='+456')

        client.return_value.calls.create.reset_mock()
        with translation.override('en-gb'):
            twilio.make_call(device=Mock(number='+123'), token='654321')
            client.return_value.calls.create.assert_called_with(
                from_='+456', to='+123', method='GET',
                url='http://testserver/twilio/inbound/two_factor/654321/?locale=en-gb')

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.gateway.TwilioRestClient')
    def test_invalid_twilio_language(self, client):
        # This test assumes an invalid twilio voice language being present in
        # the Arabic translation. Might need to create a faux translation when
        # the translation is fixed.

        url = reverse('two_factor:twilio_call_app', args=['123456'])
        with self.assertRaises(NotImplementedError):
            self.client.get('%s?%s' % (url, urlencode({'locale': 'ar'})))

        # make_call doesn't use the voice_language, but it should raise early
        # to ease debugging.
        with self.assertRaises(NotImplementedError):
            twilio = Twilio()
            with translation.override('ar'):
                twilio.make_call(device=Mock(number='+123'), token='654321')


class FakeGatewayTest(TestCase):
    @patch('two_factor.gateways.fake.logger')
    def test_gateway(self, logger):
        fake = Fake()

        fake.make_call(device=Mock(number='+123'), token='654321')
        logger.info.assert_called_with(
            'Fake call to %s: "Your token is: %s"', '+123', '654321')

        fake.send_sms(device=Mock(number='+123'), token='654321')
        logger.info.assert_called_with(
            'Fake SMS to %s: "Your token is: %s"', '+123', '654321')


class PhoneDeviceTest(TestCase):
    def test_verify(self):
        device = PhoneDevice(key=random_hex().decode())
        self.assertFalse(device.verify_token(-1))
        self.assertTrue(device.verify_token(totp(device.bin_key)))

    def test_unicode(self):
        device = PhoneDevice(name='unknown')
        self.assertEqual('unknown (None)', str(device))

        # user = User.objects.create_user('bouke')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')
        device.user = user
        self.assertEqual('unknown (bouke)', str(device))


class UtilsTest(TestCase):
    def test_default_device(self):
        # user = User.objects.create_user('bouke')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')
        self.assertEqual(default_device(user), None)

        user.phonedevice_set.create(name='backup')
        self.assertEqual(default_device(user), None)

        default = user.phonedevice_set.create(name='default')
        self.assertEqual(default_device(user).pk, default.pk)

    def test_backup_phones(self):
        self.assertQuerysetEqual(list(backup_phones(None)),
                                 list(PhoneDevice.objects.none()))

        # user = User.objects.create_user('bouke')
        user = CustomUser.objects.create_user('bouke@example.com', 'secret')
        user.phonedevice_set.create(name='default')
        backup = user.phonedevice_set.create(name='backup')
        phones = backup_phones(user)

        self.assertEqual(len(phones), 1)
        self.assertEqual(phones[0].pk, backup.pk)


class ValidatorsTest(TestCase):
    def test_phone_number_validator_on_form_valid(self):
        class TestForm(forms.Form):
            number = forms.CharField(validators=[phone_number_validator])

        form = TestForm({
            'number': '+1234567890',
        })

        self.assertTrue(form.is_valid())

    def test_phone_number_validator_on_form_invalid(self):
        class TestForm(forms.Form):
            number = forms.CharField(validators=[phone_number_validator])

        form = TestForm({
            'number': '123',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('number', form.errors)
        self.assertEqual(form.errors['number'],
                         [six.text_type(phone_number_validator.message)])
