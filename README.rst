================================
Django Two-Factor Authentication
================================

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
====

The repository on GitHub includes a demo app, which can be used for testing
purposes. Please have a look at this demo app if you are thinking about giving
this app a spin.

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
* More extensive documentation
* Different security levels, only requiring two-factor authentication for very
  sensitive parts of applications

Contributing
============

* Fork the repository on GitHub and start hacking
* Send a pull request with your changes
