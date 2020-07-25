from unittest.mock import Mock, patch
from urllib.parse import urlencode

from django.contrib.messages import get_messages
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import translation
from phonenumber_field.phonenumber import PhoneNumber

from two_factor.gateways.fake import Fake
from two_factor.gateways.twilio.gateway import Twilio
from two_factor.middleware.threadlocals import get_current_request


class TwilioGatewayTest(TestCase):
    def test_call_app(self):
        url = reverse('two_factor_twilio:call_app', args=['123456'])
        response = self.client.get(url)
        self.assertEqual(response.content,
                         b'<?xml version="1.0" encoding="UTF-8" ?>'
                         b'<Response>'
                         b'  <Gather timeout="15" numDigits="1" finishOnKey="">'
                         b'    <Say language="en">Hi, this is testserver calling. '
                         b'Press any key to continue.</Say>'
                         b'  </Gather>'
                         b'  <Say language="en">You didn\'t press any keys. Good bye.</Say>'
                         b'</Response>')

        url = reverse('two_factor_twilio:call_app', args=['123456'])
        response = self.client.post(url)
        self.assertEqual(response.content,
                         b'<?xml version="1.0" encoding="UTF-8" ?>'
                         b'<Response>'
                         b'  <Say language="en">Your token is 1. 2. 3. 4. 5. 6. '
                         b'Repeat: 1. 2. 3. 4. 5. 6. Good bye.</Say>'
                         b'</Response>')

        # there is a en-gb voice
        response = self.client.get('%s?%s' % (url, urlencode({'locale': 'en-gb'})))
        self.assertContains(response, '<Say language="en-gb">')

        # there is no Frysian voice
        response = self.client.get('%s?%s' % (url, urlencode({'locale': 'fy-nl'})))
        self.assertContains(response, '<Say language="en">')

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.gateway.Client')
    def test_gateway(self, client):
        twilio = Twilio()
        client.assert_called_with('SID', 'TOKEN')

        for code in ['654321', '054321', '87654321', '07654321']:
            twilio.make_call(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
            client.return_value.calls.create.assert_called_with(
                from_='+456', to='+123', method='GET', timeout=15,
                url='http://testserver/twilio/inbound/two_factor/%s/?locale=en-us' % code)

            twilio.send_sms(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
            client.return_value.messages.create.assert_called_with(
                to='+123', body='Your authentication token is %s' % code, from_='+456')

            client.return_value.calls.create.reset_mock()
            with translation.override('en-gb'):
                twilio.make_call(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
                client.return_value.calls.create.assert_called_with(
                    from_='+456', to='+123', method='GET', timeout=15,
                    url='http://testserver/twilio/inbound/two_factor/%s/?locale=en-gb' % code)

            client.return_value.calls.create.reset_mock()
            with translation.override('en-gb'):
                twilio.make_call(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
                client.return_value.calls.create.assert_called_with(
                    from_='+456', to='+123', method='GET', timeout=15,
                    url='http://testserver/twilio/inbound/two_factor/%s/?locale=en-gb' % code)

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
        TWILIO_ERROR_MESSAGE='Error sending SMS'
    )
    @patch('two_factor.gateways.twilio.gateway.Client')
    def test_gateway_error_handled(self, client):
        twilio = Twilio()
        client.assert_called_with('SID', 'TOKEN')

        client.return_value.messages.create.side_effect = Mock(side_effect=Exception('Test'))
        code = '123456'
        twilio.send_sms(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
        request = get_current_request()
        storage = get_messages(request)
        assert 'Error sending SMS' in [str(message) for message in storage]

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.gateway.Client')
    def test_gateway_error_not_handled(self, client):
        twilio = Twilio()
        client.assert_called_with('SID', 'TOKEN')

        client.return_value.messages.create.side_effect = Mock(side_effect=Exception('Test'))
        with self.assertRaises(Exception):
            code = '123456'
            twilio.send_sms(device=Mock(number=PhoneNumber.from_string('+123')), token=code)

    @override_settings(
        TWILIO_ACCOUNT_SID='SID',
        TWILIO_AUTH_TOKEN='TOKEN',
        TWILIO_CALLER_ID='+456',
    )
    @patch('two_factor.gateways.twilio.gateway.Client')
    def test_invalid_twilio_language(self, client):
        # This test assumes an invalid twilio voice language being present in
        # the Arabic translation. Might need to create a faux translation when
        # the translation is fixed.

        url = reverse('two_factor_twilio:call_app', args=['123456'])
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

        for code in ['654321', '87654321']:
            fake.make_call(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
            logger.info.assert_called_with(
                'Fake call to %s: "Your token is: %s"', '+123', code)

            fake.send_sms(device=Mock(number=PhoneNumber.from_string('+123')), token=code)
            logger.info.assert_called_with(
                'Fake SMS to %s: "Your token is: %s"', '+123', code)
