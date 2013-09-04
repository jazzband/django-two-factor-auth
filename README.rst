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

This project is in alpha state. Although there are no known problems, the
project has not yet received a lot of real life experience. If you run into
problems, please file an issue on GitHub, or contribute to the project by
forking the repository and sending some pull requests.

Demo
----
The repository on GitHub includes a demo app, which can be used for testing
purposes. Please have a look at this demo app if you are thinking about giving
this app a spin.

Compatibility
-------------
Compatible with Django 1.4 and 1.5.

Installation
============
Installation with ``pip``:
::

    $ pip install django-two-factor-auth

Add ``'two_factor'`` to the ``INSTALLED_APPS``
::

    INSTALLED_APPS = (
        ...
        'two_factor',
    )

Configure the authentication backends like so:
::

    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'two_factor.auth_backends.TokenBackend',
        'two_factor.auth_backends.VerifiedComputerBackend',
    )

Configure the login url:
::

    from django.core.urlresolvers import reverse_lazy
    LOGIN_URL = reverse_lazy('tf:login')

Add the url routes:
::

    urlpatterns = patterns('',
        ...
        url(r'^tf/', include('two_factor.urls', 'tf')),
    )

Be sure to remove any other login routes, otherwise the two-factor
authentication might be circumvented. The admin interface should be
automatically patched to use the new login method.

Settings
========
``TF_SMS_GATEWAY``
    Which module should be used to send text messages. It defaults to
    ``two_factor.sms_gateways.Fake``, which echoes the text messages to the
    console. A gateway for Twilio comes prepackaged, see the settings below.

``TF_CALL_GATEWAY``
    Which module should be used for calls. It defaults to
    ``two_factor.call_gateways.Fake``, which echoes the call message to the
    console. A gateway for Twilio comes prepackaged, see the settings below.

``TF_VERIFICATION_WINDOW``
    Number of seconds that the signed user verification is valid for.
    Defaults to 60.

Twilio
------
Gateways for sending text message and initiating calls trough Twilio_ come
prepackaged. All you need is your Twilio Account SID and Token, as shown in
your Twilio account dashboard.
::

    TF_CALL_GATEWAY = 'two_factor.call_gateways.Twilio'
    TF_SMS_GATEWAY = 'two_factor.sms_gateways.Twilio'
    TWILIO_ACCOUNT_SID = '***'
    TWILIO_AUTH_TOKEN = '***'
    TWILIO_CALLER_ID = '[verified phone number]'
    TWILIO_SMS_CALLER_ID = '[verified phone number]'

.. _Twilio: http://www.twilio.com/

Todo / Wish List
================
* Test suite
* Extensive documentation
* Different security levels, only requiring two-factor authentication for very
  sensitive parts of applications

Contributing
============
* Fork the repository on GitHub and start hacking
* Send a pull request with your changes

Testing
-------
To run the test suite simply run ``python demo/manage.py test``. This project
uses ``django-discover-runner`` to discover the tests located in ``tests/``.

The goals is to have a extensive test suite to validate cover all security
aspects. When contributing, please make sure your code is properly tested.
