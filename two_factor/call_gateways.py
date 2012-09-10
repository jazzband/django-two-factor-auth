# coding=utf8
from django.conf import settings
from django.utils.importlib import import_module

def load_gateway(path):
    module, attr = path.rsplit('.', 1)
    mod = import_module(module)
    cls = getattr(mod, attr)
    return cls()

def get_gateway():
    path = getattr(settings, 'TF_CALL_GATEWAY', 'two_factor.call_gateways.Fake')
    return load_gateway(path)

def call(to, body):
    get_gateway().send(to=to, body=body)


class Fake(object):
    def send(self, to, body):
        print 'Fake call to %s: "%s"' % (to, body)
