from django.conf import settings
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.utils.http import urlencode
from django.utils.importlib import import_module

GATEWAY = getattr(settings, 'TF_CALL_GATEWAY', 'two_factor.call_gateways.Fake')

def load_gateway(path):
    module, attr = path.rsplit('.', 1)
    mod = import_module(module)
    cls = getattr(mod, attr)
    return cls()

def get_gateway():
    return GATEWAY and load_gateway(GATEWAY)

def call(to, token, **kwargs):
    get_gateway().call(to=to, token=token, **kwargs)


class Fake(object):
    def call(self, to, token, **kwargs):
        print 'Fake call to %s: "Your token is: %s"' % (to, token)


class Twilio(object):
    def __init__(self, account=None, token=None, caller_id=None):
        if not account:
            account = getattr(settings, 'TWILIO_ACCOUNT_SID')
        if not token:
            token = getattr(settings, 'TWILIO_AUTH_TOKEN')
        if not caller_id:
            self.caller_id = getattr(settings, 'TWILIO_CALLER_ID')

        from twilio.rest import TwilioRestClient
        self.client = TwilioRestClient(account, token)

    def call(self, to, token, request, **kwargs):
        signer = Signer()
        url = request.build_absolute_uri(reverse('tf:twilio_call_app')) + \
                '?' + urlencode({'token': signer.sign(token)})
        self.client.calls.create(to=to, from_=self.caller_id, url=url)
