import os

try:
    import otp_yubikey
except ImportError:
    otp_yubikey = None

try:
    import webauthn
except ImportError:
    webauthn = None

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
    'django_otp.plugins.otp_email',
    'two_factor',
    'two_factor.plugins.email',
    'two_factor.plugins.phonenumber',
    'tests',
]

if otp_yubikey:
    INSTALLED_APPS.extend(['otp_yubikey', 'two_factor.plugins.yubikey'])

if webauthn:
    INSTALLED_APPS.extend(['two_factor.plugins.webauthn'])

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'two_factor.middleware.threadlocals.ThreadLocals',
)

ROOT_URLCONF = 'tests.urls'

STATIC_URL = '/static/'

LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = 'two_factor:profile'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TWO_FACTOR_PATCH_ADMIN = False

TWO_FACTOR_WEBAUTHN_RP_NAME = 'Test Server'

AUTH_USER_MODEL = os.environ.get('AUTH_USER_MODEL', 'auth.User')
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'test@test.org'

TWO_FACTOR_PHONE_THROTTLE_FACTOR = 10
OTP_TOTP_THROTTLE_FACTOR = 10

OTP_EMAIL_COOLDOWN_DURATION = 0
