Django Two-Factor Authentication Documentation
==============================================

Complete Two-Factor Authentication for Django. Built on top of the one-time
password framework django-otp_ and Django's built-in authentication framework
``django.contrib.auth`` for providing the easiest integration into most Django
projects. Inspired by the user experience of Google's Two-Step Authentication,
allowing users to authenticate through call, text messages (SMS) or by using a
token generator app like Google Authenticator.

Contents:

.. toctree::
   :maxdepth: 2

   requirements
   installation
   configuration
   implementing
   management-commands
   class-reference
   release-notes

I would love to hear your feedback on this application. If you run into
problems, please file an issue on GitHub_, or contribute to the project by
forking the repository and sending some pull requests.

This application is currently translated into English, Dutch, Hebrew, Arabic,
German, Chinese and Spanish. Please contribute your own language using
Transifex_.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _django-otp: https://pypi.python.org/pypi/django-otp
.. _Transifex: https://www.transifex.com/projects/p/django-two-factor-auth/
.. _GitHub: https://github.com/Bouke/django-two-factor-auth/issues
