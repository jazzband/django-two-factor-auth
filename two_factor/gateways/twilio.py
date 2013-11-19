from __future__ import absolute_import

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext
from twilio.rest import TwilioRestClient

from two_factor.middleware.threadlocals import get_current_request


class Twilio(object):
    def __init__(self):
        self.client = TwilioRestClient(getattr(settings, 'TWILIO_ACCOUNT_SID'),
                                       getattr(settings, 'TWILIO_AUTH_TOKEN'))

    def make_call(self, device, token):
        request = get_current_request()
        url = reverse('two_factor:twilio_call_app', kwargs={'token': token})
        uri = request.build_absolute_uri(url)
        self.client.calls.create(to=device.number,
                                 from_=getattr(settings, 'TWILIO_CALLER_ID'),
                                 url=uri,
                                 method='GET')

    def send_sms(self, device, token):
        body = ugettext('Your authentication token is %s' % token)
        self.client.sms.messages.create(
            to=device.number,
            from_=getattr(settings, 'TWILIO_CALLER_ID'),
            body=body)
