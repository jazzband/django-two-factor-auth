================================
Django Two-Factor Authentication
================================

.. image:: https://travis-ci.org/Bouke/django-two-factor-auth.png?branch=master
    :alt: Build Status
    :target: https://travis-ci.org/Bouke/django-two-factor-auth

.. image:: https://coveralls.io/repos/Bouke/django-two-factor-auth/badge.png?branch=master
    :alt: Test Coverage
    :target: https://coveralls.io/r/Bouke/django-two-factor-auth?branch=master

.. image:: https://badge.fury.io/py/django-two-factor-auth.png
    :alt: PyPI
    :target: https://pypi.python.org/pypi/django-two-factor-auth

Complete Two-Factor Authentication for Django. Built on top of the one-time
password framework django-otp_ and Django's built-in authentication framework
``django.contrib.auth`` for providing the easiest integration into most Django
projects. Inspired by the user experience of Google's Two-Step Authentication,
allowing users to authenticate through call, text messages (SMS) or by using a
token generator app like Google Authenticator.

I would love to hear your feedback on this package. If you run into
problems, please file an issue on GitHub, or contribute to the project by
forking the repository and sending some pull requests. The package is currently
translated into English, Dutch, Hebrew and Arabic. Please contribute your own
language using Transifex_.

Example
=======
Test drive this app through the online `example app`_, hosted by Heroku_. It
demos most features except the Twilio integration. It also includes
django-user-sessions_ for providing Django sessions with a foreign key to the
user. Although the package is optional, it provides better account security
control over ``django.contrib.sessions``.

Compatibility
=============
Compatible with Django 1.4, 1.5 and 1.6 on Python 2.6, 2.7, 3.2 and 3.3.

Installation
============
Installation with ``pip``::

    $ pip install django-two-factor-auth

Add the following apps to the ``INSTALLED_APPS``::

    INSTALLED_APPS = (
        ...
        'django_otp',
        'django_otp.plugins.otp_static',
        'django_otp.plugins.otp_totp',
        'two_factor',
    )

Configure a few urls::

    from django.core.urlresolvers import reverse_lazy
    LOGIN_URL = reverse_lazy('two_factor:login')

    # this one is optional
    LOGIN_REDIRECT_URL = reverse_lazy('two_factor:profile')

Add the url routes::

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
    The module that should be used for sending text messages.

``TWO_FACTOR_CALL_GATEWAY`` (default: ``None``)
    The module that should be used for making calls.

``TWO_FACTOR_PATCH_ADMIN`` (default: ``True``)
    Whether the admin should be patched to use the two-factor authentication
    method. Disabling this setting would allow circumventing two-factor
    authentication.

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

See Also
========
* Have a look at django-user-sessions_ for Django sessions with a foreign key
  to the user. This package is also included in the demo app.

Release Notes
=============

0.2.3
-----
* Two new translations: Hebrew and Arabic

0.2.2
-----
* Allow changing Twilio call language.

0.2.1
-----
* Allow overriding instructions in the template.
* Allow customization of the redirect query parameter.
* Faster backup token generating.

0.2.0
-----
This is a major upgrade, as the package has been rewritten completely. Upgrade
to this version with care and make backups of your database before running the
South migrations. See installation instructions for installing the new version;
update your template customizations and run the database migrations.

Development
===========
This project aims for full code-coverage, this means that your code should be
well-tested. Also test branches for hardened code.

Running tests
-------------
You can run the full test suite with::

    make test

Or run a specific test with::

    make test TARGET=tests.tests.TwilioGatewayTest

For Python compatibility, tox_ is used. You can run the full test suite with::

    tox


Contributing
============
* Fork the repository on GitHub and start hacking.
* Run the tests.
* Send a pull request with your changes.
* Provide a translation using Transifex_.

.. _`example app`: http://example-two-factor-auth.herokuapp.com
.. _django-otp: https://pypi.python.org/pypi/django-otp
.. _Transifex: https://www.transifex.com/projects/p/django-two-factor-auth/
.. _Twilio: http://www.twilio.com/
.. _Heroku: https://www.heroku.com
.. _django-user-sessions: https://pypi.python.org/pypi/django-user-sessions
.. _tox: https://testrun.org/tox/latest/
