================================
Django Two-Factor Authentication
================================

.. image:: https://travis-ci.org/Bouke/django-two-factor-auth.png?branch=develop
    :alt: Build Status
    :target: https://travis-ci.org/Bouke/django-two-factor-auth

Complete Two-Factor Authentication for Django. Built on top of
``django.contrib.auth`` for providing the easiest integration into most Django
projects. Inspired by the user experience of Google's Two-Step Authentication,
allowing users to authenticate through call, text messages (SMS) or by using an
app like Google Authenticator.

The package is being prepared for version 0.3.0. This new version is a full
rewrite, taking advantage of the one-time password framework django-otp_. This
version is not yet released on PyPI, but is already feature-complete. It is
fully compatible with Django 1.6, although support for older versions is
planned.

I would love to hear your feedback on this package. If you run into
problems, please file an issue on GitHub, or contribute to the project by
forking the repository and sending some pull requests.

.. _django-otp: https://pypi.python.org/pypi/django-otp

Example
-------
The repository on GitHub includes a example app, which can be used for testing
purposes. Please have a look at this example app if you are thinking about
giving this app a spin.

Compatibility
-------------
Compatible with Django 1.4, 1.5 and 1.6 on Python 2.6, 2.7, 3.2 and 3.3.

Installation
============
Installation with ``pip``:
::

    $ pip install django-two-factor-auth

Add the following apps to the ``INSTALLED_APPS``
::

    INSTALLED_APPS = (
        ...
        'django_otp',
        'django_otp.plugins.otp_static',
        'django_otp.plugins.otp_totp',
        'two_factor',
    )

Configure the login url:
::

    from django.core.urlresolvers import reverse_lazy
    LOGIN_URL = reverse_lazy('two_factor:login')

Add the url routes:
::

    urlpatterns = patterns('',
        ...
        url(r'', include('two_factor.urls', 'two_factor')),
    )

Be sure to remove any other login routes, otherwise the two-factor
authentication might be circumvented. The admin interface should be
automatically patched to use the new login method.

Settings
========
``TWO_FACTOR_SMS_GATEWAY`` (default: ``None``)
    Which module should be used for sending text messages.

``TWO_FACTOR_CALL_GATEWAY`` (default: ``None``)
    Which module should be used for making calls.

Gateway ``two_factor.gateways.fake.Fake``
-----------------------------------------
Prints the tokens to the logger. You will have to set the message level of the
``two_factor`` logger to ``INFO`` for them to appear in the console. Useful for
local development.
::

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'two_factor': {
                'handlers': ['console'],
                'level': 'INFO',
            }
        }
    }

Gateway ``two_factor.gateways.twilio.Twilio``
---------------------------------------------
Gateways for sending text message and initiating calls trough Twilio_ come
prepackaged. All you need is your Twilio Account SID and Token, as shown in
your Twilio account dashboard.
::

    TWO_FACTOR_CALL_GATEWAY = 'two_factor.gateways.twilio.Twilio'
    TWO_FACTOR_SMS_GATEWAY = 'two_factor.gateways.twilio.Twilio'
    TWILIO_ACCOUNT_SID = '***'
    TWILIO_AUTH_TOKEN = '***'
    TWILIO_CALLER_ID = '[verified phone number]'

.. _Twilio: http://www.twilio.com/

Contributing
============
* Fork the repository on GitHub and start hacking.
* Run the tests.
* Send a pull request with your changes.
