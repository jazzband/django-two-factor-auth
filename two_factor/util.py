# coding=utf8
from base64 import b32encode
from binascii import hexlify, unhexlify
import random
from urllib import urlencode

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
