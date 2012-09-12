from django.conf import settings
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
