from __future__ import absolute_import

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import translation
from django.utils.translation import ugettext, pgettext
from twilio.rest import TwilioRestClient
from two_factor.middleware.threadlocals import get_current_request

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

    .. _Twilio: http://www.twilio.com/
    """
    def __init__(self):
        self.client = TwilioRestClient(getattr(settings, 'TWILIO_ACCOUNT_SID'),
                                       getattr(settings, 'TWILIO_AUTH_TOKEN'))

    def make_call(self, device, token):
        locale = translation.get_language()
        validate_voice_locale(locale)

        request = get_current_request()
        url = reverse('two_factor:twilio_call_app', kwargs={'token': token})
        url = '%s?%s' % (url, urlencode({'locale': locale}))
        uri = request.build_absolute_uri(url)
        self.client.calls.create(to=device.number, from_=getattr(settings, 'TWILIO_CALLER_ID'),
                                 url=uri, method='GET', if_machine='Hangup', timeout=15)

    def send_sms(self, device, token):
        body = ugettext('Your authentication token is %s' % token)
        self.client.sms.messages.create(
            to=device.number,
            from_=getattr(settings, 'TWILIO_CALLER_ID'),
            body=body)


def validate_voice_locale(locale):
    with translation.override(locale):
        voice_locale = pgettext('twilio_locale', 'en')
        if voice_locale not in VOICE_LANGUAGES:
            raise NotImplementedError('The language "%s" is not '
                                      'supported by Twilio' % voice_locale)
