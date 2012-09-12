from django.conf import settings
from django.utils.importlib import import_module

def load_gateway(path):
    module, attr = path.rsplit('.', 1)
    mod = import_module(module)
    cls = getattr(mod, attr)
    return cls()

def get_gateway():
    path = getattr(settings, 'TF_SMS_GATEWAY', 'two_factor.sms_gateways.Fake')
    return load_gateway(path)

def send(to, body):
    get_gateway().send(to=to, body=body)


class Fake(object):
    def send(self, to, body):
        print 'Fake sending SMS message to %s: "%s"' % (to, body)


class Twilio(object):
    def __init__(self, account=None, token=None, sender=None):
        if not account:
            account = getattr(settings, 'TWILIO_ACCOUNT_SID')
        if not token:
            token = getattr(settings, 'TWILIO_AUTH_TOKEN')
        if not sender:
            self.sender = getattr(settings, 'SMS_SENDER')

        from twilio.rest import TwilioRestClient
        self.client = TwilioRestClient(account, token)

    def send(self, to, body):
        self.client.sms.messages.create(to=to, from_=self.sender, body=body)
