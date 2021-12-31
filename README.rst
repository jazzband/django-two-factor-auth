================================
Django Two-Factor Authentication
================================

.. image:: https://jazzband.co/static/img/badge.svg
        :target: https://jazzband.co/
        :alt: Jazzband

.. image:: https://github.com/jazzband/django-two-factor-auth/workflows/build/badge.svg?branch=master
    :alt: Build Status
    :target: https://github.com/jazzband/django-two-factor-auth/actions

.. image:: https://codecov.io/gh/jazzband/django-two-factor-auth/branch/master/graph/badge.svg
    :alt: Test Coverage
    :target: https://codecov.io/gh/jazzband/django-two-factor-auth

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

If you run into problems, please file an issue on GitHub, or contribute to the
project by forking the repository and sending some pull requests. The package
is translated into English, Dutch and other languages. Please contribute your
own language using Transifex_.

Test drive this app through the online `example app`_, hosted by Heroku_. It
demos most features except the Twilio integration. The example also includes
django-user-sessions_ for providing Django sessions with a foreign key to the
user. Although the package is optional, it improves account security control
over ``django.contrib.sessions``.

Compatible with modern Django versions. At the moment of writing that's
including 2.2, 3.1, 3.2, and 4.0 on Python 3.5, 3.6, 3.7, 3.8 and 3.9.
Documentation is available at `readthedocs.org`_.


Installation
============
Refer to the `installation instructions`_ in the documentation.


Getting help
============

For general questions regarding this package, please hop over to `Stack Overflow`_.
If you think there is an issue with this package; check if the
issue is already listed (either open or closed), and file an issue if
it's not.


Contribute
==========
Read the `contribution guidelines`_.


See Also
========
Have a look at django-user-sessions_ for Django sessions with a foreign key to
the user. This package is also included in the online `example app`_.


License
=======
The project is licensed under the MIT license.

.. _`example app`: https://example-two-factor-auth.herokuapp.com
.. _django-otp: https://pypi.python.org/pypi/django-otp
.. _Transifex: https://www.transifex.com/projects/p/django-two-factor-auth/
.. _Twilio: https://www.twilio.com/
.. _Heroku: https://www.heroku.com
.. _contribution guidelines:
   https://github.com/jazzband/django-two-factor-auth/CONTRIBUTING.rst
.. _django-user-sessions: https://pypi.python.org/pypi/django-user-sessions
.. _readthedocs.org: https://django-two-factor-auth.readthedocs.org/
.. _`installation instructions`:
   https://django-two-factor-auth.readthedocs.io/en/stable/installation.html
.. _`Stack Overflow`:
   https://stackoverflow.com/questions/tagged/django-two-factor-auth
.. _Yubikey: https://www.yubico.com/products/yubikey-hardware/
