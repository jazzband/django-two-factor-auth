from django.conf import settings
from django.utils.importlib import import_module
from django.utils.translation import ugettext

GATEWAY = getattr(settings, 'TF_SMS_GATEWAY', 'two_factor.sms_gateways.Fake')

def load_gateway(path):
    module, attr = path.rsplit('.', 1)
    mod = import_module(module)
    cls = getattr(mod, attr)
    return cls()

def get_gateway():
    return GATEWAY and load_gateway(GATEWAY)

def send(to, token, **kwargs):
    get_gateway().send(to=to, token=token, **kwargs)


class Fake(object):
    def send(self, to, token, **kwargs):
        print 'Fake SMS to %s: "Your token is: %s"' % (to, token)


class Twilio(object):
    def __init__(self, account=None, token=None, caller_id=None):
        if not account:
            account = getattr(settings, 'TWILIO_ACCOUNT_SID')
        if not token:
            token = getattr(settings, 'TWILIO_AUTH_TOKEN')
        if not caller_id:
            self.caller_id = getattr(settings, 'TWILIO_SMS_CALLER_ID')

        from twilio.rest import TwilioRestClient
        self.client = TwilioRestClient(account, token)

    def send(self, to, token, **kwargs):
        body = ugettext('Your authorization token is %s' % token)
        self.client.sms.messages.create(to=to, from_=self.caller_id, body=body)
