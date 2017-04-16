================================
Django Two-Factor Authentication
================================

.. image:: https://travis-ci.org/Bouke/django-two-factor-auth.svg?branch=master
    :alt: Build Status
    :target: https://travis-ci.org/Bouke/django-two-factor-auth

.. image:: https://coveralls.io/repos/Bouke/django-two-factor-auth/badge.svg?branch=master
    :alt: Test Coverage
    :target: https://coveralls.io/r/Bouke/django-two-factor-auth?branch=master

.. image:: https://badge.fury.io/py/django-two-factor-auth.svg
    :alt: PyPI
    :target: https://pypi.python.org/pypi/django-two-factor-auth

Complete Two-Factor Authentication for Django. Built on top of the one-time
password framework django-otp_ and Django's built-in authentication framework
``django.contrib.auth`` for providing the easiest integration into most Django
projects. Inspired by the user experience of Google's Two-Step Authentication,
allowing users to authenticate through call, text messages (SMS), by using a
token generator app like Google Authenticator or a YubiKey_ hardware token
generator (optional).

I would love to hear your feedback on this package. If you run into
problems, please file an issue on GitHub, or contribute to the project by
forking the repository and sending some pull requests. The package is
translated into English, Dutch and other languages. Please contribute your own
language using Transifex_.

Test drive this app through the online `example app`_, hosted by Heroku_. It
demos most features except the Twilio integration. The example also includes
django-user-sessions_ for providing Django sessions with a foreign key to the
user. Although the package is optional, it improves account security control
over ``django.contrib.sessions``.

Compatible with all supported Django versions. At the moment of writing that's
including 1.8, 1.10 and 1.11 on Python 2.7, 3.4, 3.5 and 3.6. Documentation
is available at `readthedocs.org`_.


Installation
============
Installation with ``pip``::

    $ pip install django-two-factor-auth

Setup
=====
Add the following apps to the ``INSTALLED_APPS``::

    INSTALLED_APPS = (
        ...
        'django_otp',
        'django_otp.plugins.otp_static',
        'django_otp.plugins.otp_totp',
        'two_factor',
    )

Add ``django_otp.middleware.OTPMiddleware`` to ``MIDDLEWARE_CLASSES``. It must
be installed *after* ``AuthenticationMiddleware``::

    MIDDLEWARE_CLASSES = [
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django_otp.middleware.OTPMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ]

Configure a few urls in settings.py::

    from django.core.urlresolvers import reverse_lazy
    LOGIN_URL = 'two_factor:login'

Add the url routes to the project in urls.py::

    urlpatterns = [
        url(r'', include('two_factor.urls', 'two_factor')),
    ]

Be sure to remove any other login routes, otherwise the two-factor
authentication might be circumvented. The admin interface should be
automatically patched to use the new login method.

Support for YubiKey_ is disabled by default, but enabling is easy. Please
refer to the documentation for instructions.


Contribute
==========
* Submit issues to the `issue tracker`_ on Github.
* Fork the `source code`_ at Github.
* Write some code and make sure it is covered with unit tests.
* Send a pull request with your changes.
* Provide a translation using Transifex_.

Running tests
-------------
This project aims for full code-coverage, this means that your code should be
well-tested. Also test branches for hardened code. You can run the full test
suite with::

    make test

Or run a specific test with::

    make test TARGET=tests.tests.TwilioGatewayTest

For Python compatibility, tox_ is used. You can run the full test suite,
covering all supported Python and Django version with::

    tox

Releasing
---------
The following actions are required to push a new version:

* Update release notes
* If any new translations strings were added, push the new source language to
  Transifex_. Make sure translators have sufficient time to translate those
  new strings::

    make tx-push

* Add migrations::

    python example/manage.py makemigrations two_factor
    git commit two_factor/migrations -m "Added migrations"

* Update translations::

    make tx-pull

* Package and upload::

    bumpversion [major|minor|patch]
    git push && git push --tags
    python setup.py sdist bdist_wheel
    twine upload dist/*


See Also
========
Have a look at django-user-sessions_ for Django sessions with a foreign key to
the user. This package is also included in the online `example app`_.


License
=======
The project is licensed under the MIT license.

.. _`example app`: http://example-two-factor-auth.herokuapp.com
.. _django-otp: https://pypi.python.org/pypi/django-otp
.. _Transifex: https://www.transifex.com/projects/p/django-two-factor-auth/
.. _Twilio: http://www.twilio.com/
.. _Heroku: https://www.heroku.com
.. _django-user-sessions: https://pypi.python.org/pypi/django-user-sessions
.. _tox: https://testrun.org/tox/latest/
.. _issue tracker: https://github.com/Bouke/django-two-factor-auth/issues
.. _source code: https://github.com/Bouke/django-two-factor-auth
.. _readthedocs.org: http://django-two-factor-auth.readthedocs.org/
.. _Yubikey: https://www.yubico.com/products/yubikey-hardware/
.. _`Hynek's Sharing Your Labor of Love: PyPI Quick And Dirty`:
   https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
