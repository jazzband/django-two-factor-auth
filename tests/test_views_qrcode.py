from unittest import mock

import qrcode.image.svg
from django.test import RequestFactory, TestCase
from django.urls import reverse

from two_factor.utils import get_otpauth_url
from two_factor.views.core import QRGeneratorView

from .utils import UserMixin


class CustomQRView(QRGeneratorView):
    def get_issuer(self):
        return "Custom Test Issuer"


class QRTest(UserMixin, TestCase):
    test_secret = 'This is a test secret for an OTP Token'
    test_img = 'This is a test string that represents a QRCode'

    def setUp(self):
        super().setUp()
        self.user = self.create_user(username='ⓑỚ𝓾⒦ȩ')
        self.login_user()

    def test_without_secret(self):
        response = self.client.get(reverse('two_factor:qr'))
        self.assertEquals(response.status_code, 404)

    @mock.patch('qrcode.make')
    def test_with_secret(self, mockqrcode):
        # Setup the mock data
        def side_effect(resp):
            resp.write(self.test_img)
        mockimg = mock.Mock()
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
            get_otpauth_url(accountname=self.user.get_username(),
                            secret=self.test_secret, issuer="testserver"),
            image_factory=default_factory)
        mockimg.save.assert_called_with(mock.ANY)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content.decode('utf-8'), self.test_img)
        self.assertEquals(response['Content-Type'], 'image/svg+xml; charset=utf-8')

    @mock.patch('qrcode.make')
    def test_custom_issuer(self, mockqrcode):
        # Setup the mock data
        def side_effect(resp):
            resp.write(self.test_img)
        mockimg = mock.Mock()
        mockimg.save.side_effect = side_effect
        mockqrcode.return_value = mockimg

        # Setup the session
        session = self.client.session
        session['django_two_factor-qr_secret_key'] = self.test_secret
        session.save()

        # Get default image factory
        default_factory = qrcode.image.svg.SvgPathImage

        # Get the QR code
        factory = RequestFactory()
        request = factory.get(reverse('two_factor:qr'))
        request.user = self.user
        request.session = session
        response = CustomQRView.as_view()(request)

        # Check things went as expected
        mockqrcode.assert_called_with(
            get_otpauth_url(accountname=self.user.get_username(),
                            secret=self.test_secret, issuer="Custom Test Issuer"),
            image_factory=default_factory)
        mockimg.save.assert_called_with(mock.ANY)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content.decode('utf-8'), self.test_img)
        self.assertEquals(response['Content-Type'], 'image/svg+xml; charset=utf-8')
