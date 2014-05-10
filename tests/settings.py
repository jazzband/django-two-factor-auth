import os
from django.core.urlresolvers import reverse_lazy

try:
    import otp_yubikey
except ImportError:
    otp_yubikey = None

BASE_DIR = os.path.dirname(__file__)

SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'tests',
]

if otp_yubikey:
    INSTALLED_APPS += ['otp_yubikey']

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'two_factor.middleware.threadlocals.ThreadLocals',
)

ROOT_URLCONF = 'tests.urls'

LOGOUT_URL = reverse_lazy('logout')
LOGIN_URL = reverse_lazy('two_factor:login')
LOGIN_REDIRECT_URL = reverse_lazy('two_factor:profile')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)


TWO_FACTOR_PATCH_ADMIN = False

AUTH_USER_MODEL = os.environ.get('AUTH_USER_MODEL', 'auth.User')
