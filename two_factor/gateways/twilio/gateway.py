from __future__ import absolute_import

from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils import translation
from django.utils.translation import pgettext, ugettext
from twilio.rest import Client

from two_factor.middleware.threadlocals import get_current_request

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


# Supported voice languages, see http://bit.ly/187I5cr
VOICE_LANGUAGES = ('en', 'en-gb', 'es', 'fr', 'it', 'de', 'da-DK', 'de-DE',
                   'en-AU', 'en-CA', 'en-GB', 'en-IN', 'en-US', 'ca-ES',
                   'es-ES', 'es-MX', 'fi-FI', 'fr-CA', 'fr-FR', 'it-IT',
                   'ja-JP', 'ko-KR', 'nb-NO', 'nl-NL', 'pl-PL', 'pt-BR',
                   'pt-PT', 'ru-RU', 'sv-SE', 'zh-CN', 'zh-HK', 'zh-TW')


class Twilio(object):
    """
    Gateway for sending text messages and making phone calls using Twilio_.

    All you need is your Twilio Account SID and Token, as shown in your Twilio
    account dashboard.

    ``TWILIO_ACCOUNT_SID``
      Should be set to your account's SID.

    ``TWILIO_AUTH_TOKEN``
      Should be set to your account's authorization token.

    ``TWILIO_CALLER_ID``
      Should be set to a verified phone number. Twilio_ differentiates between
      numbers verified for making phone calls and sending text messages.

    Optionally you may set an error message to be displayed incase of error.

    ``TWILIO_ERROR_MESSAGE``
      Should be set to a string with a custom text.

    .. _Twilio: http://www.twilio.com/
    """
    def __init__(self):
        self.client = Client(getattr(settings, 'TWILIO_ACCOUNT_SID'),
                             getattr(settings, 'TWILIO_AUTH_TOKEN'))

    def make_call(self, device, token):
        locale = translation.get_language()
        validate_voice_locale(locale)

        request = get_current_request()
        url = reverse('two_factor_twilio:call_app', kwargs={'token': token})
        url = '%s?%s' % (url, urlencode({'locale': locale}))
        uri = request.build_absolute_uri(url)
        self.client.calls.create(to=device.number.as_e164,
                                 from_=getattr(settings, 'TWILIO_CALLER_ID'),
                                 url=uri, method='GET', timeout=15)

    def send_sms(self, device, token):
        body = ugettext('Your authentication token is %s') % token
        try:
            self.client.messages.create(
                to=device.number.as_e164,
                from_=getattr(settings, 'TWILIO_CALLER_ID'),
                body=body)
        except Exception:
            twilio_error_message = getattr(settings, 'TWILIO_ERROR_MESSAGE', None)
            if twilio_error_message:
                request = get_current_request()
                messages.add_message(request, messages.ERROR, twilio_error_message)
            else:
                raise


def validate_voice_locale(locale):
    with translation.override(locale):
        voice_locale = pgettext('twilio_locale', 'en')
        if voice_locale not in VOICE_LANGUAGES:
            raise NotImplementedError('The language "%s" is not '
                                      'supported by Twilio' % voice_locale)
