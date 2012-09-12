from django.conf import settings
from django.utils.importlib import import_module

GATEWAY = getattr(settings, 'TF_CALL_GATEWAY', 'two_factor.call_gateways.Fake')

def load_gateway(path):
    module, attr = path.rsplit('.', 1)
    mod = import_module(module)
    cls = getattr(mod, attr)
    return cls()

def get_gateway():
    return GATEWAY and load_gateway(GATEWAY)

def call(to, body):
    get_gateway().send(to=to, body=body)


class Fake(object):
    def send(self, to, body):
        print 'Fake call to %s: "%s"' % (to, body)
