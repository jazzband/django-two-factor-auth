import random
from base64 import b32encode
from binascii import hexlify, unhexlify
from urllib import urlencode
from django.utils.decorators import method_decorator

def generate_seed(length=10):
    return hexlify(''.join([chr(random.randint(0,255)) for i in range(length)]))

def get_otpauth_url(alias, seed):
    seed_b32 = b32encode(unhexlify(seed))
    return  'otpauth://totp/%s?secret=%s' % (alias, seed_b32)

def get_qr_url(alias, seed):
    return "https://chart.googleapis.com/chart?" + urlencode({
        "chs": "200x200",
        "chld": "M|0",
        "cht": "qr",
        "chl": get_otpauth_url(alias, seed)
    })

#@from http://stackoverflow.com/a/8429311/58107
def class_view_decorator(function_decorator):
    """Convert a function based decorator into a class based decorator usable
    on class based Views.

    Can't subclass the `View` as it breaks inheritance (super in particular),
    so we monkey-patch instead.
    """
    def simple_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View
    return simple_decorator
